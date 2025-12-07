"""Enhanced retry mechanisms with exponential backoff and jitter.

This module provides robust retry logic for handling transient failures
in API calls and other operations.
"""

from __future__ import annotations

import random
import time
from enum import Enum
from typing import Any, Callable, TypeVar

import structlog

logger = structlog.get_logger()

T = TypeVar("T")


# Alias for backward compatibility
BackoffStrategy = Enum(
    "BackoffStrategy",
    {"EXPONENTIAL": "exponential", "LINEAR": "linear", "FIXED": "fixed", "FIBONACCI": "fibonacci"},
)


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(
        self,
        message: str,
        attempts: int,
        last_exception: Exception,
        total_time: float,
    ) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.last_exception = last_exception
        self.total_time = total_time


class RetryState:
    """Tracks state during retry attempts."""

    def __init__(
        self,
        max_attempts: int,
        base_delay: float,
        max_delay: float,
        strategy: BackoffStrategy,
        jitter: bool,
    ) -> None:
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.strategy = strategy
        self.jitter = jitter

        self.attempts = 0
        self.start_time = time.time()
        self.last_exception: Exception | None = None

    @property
    def should_retry(self) -> bool:
        """Check if we should retry."""
        return self.attempts < self.max_attempts

    @property
    def elapsed_time(self) -> float:
        """Time elapsed since first attempt."""
        return time.time() - self.start_time


class Retryable:
    """
    Enhanced retry mechanism with configurable backoff and jitter.

    Features:
    - Multiple backoff strategies (exponential, linear, fixed, fibonacci)
    - Jitter to prevent thundering herd
    - Per-exception retry policies
    - Detailed logging and metrics
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
        jitter: bool = True,
        exponential_base: float = 2.0,
        retry_on: type[Exception] | tuple[type[Exception], ...] = Exception,
        retry_on_predicate: Callable[[Exception], bool] | None = None,
        stop_on: type[Exception] | tuple[type[Exception], ...] | None = None,
    ) -> None:
        """
        Initialize retry mechanism.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Initial delay between retries
            max_delay: Maximum delay between retries
            strategy: Backoff strategy to use
            jitter: Whether to add random jitter to delays
            exponential_base: Base for exponential backoff
            retry_on: Exception types that should trigger retry
            retry_on_predicate: Custom function to determine if exception is retryable
            stop_on: Exception types that should not trigger retry
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.strategy = strategy
        self.jitter = jitter
        self.exponential_base = exponential_base
        self.retry_on = retry_on
        self.retry_on_predicate = retry_on_predicate
        self.stop_on = stop_on

        self.logger = structlog.get_logger().bind(
            retryable=id(self),
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            strategy=strategy.value,
        )

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to wrap a function with retry logic."""

        def wrapper(*args: Any, **kwargs: Any) -> T:
            return self.execute(func, *args, **kwargs)

        return wrapper

    def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Result of func(*args, **kwargs)

        Raises:
            RetryError: If all attempts fail
            Exception: Non-retryable exception
        """
        state = RetryState(
            max_attempts=self.max_attempts,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            strategy=self.strategy,
            jitter=self.jitter,
        )

        while state.should_retry:
            state.attempts += 1

            try:
                result = func(*args, **kwargs)

                # For browser operations that return dict, check for errors
                if isinstance(result, dict) and result.get("error"):
                    error_msg = result.get("error", "Unknown browser error")
                    # Convert browser error to exception for retry logic
                    browser_error = Exception(f"Browser operation failed: {error_msg}")
                    state.last_exception = browser_error

                    # Check if browser error is retryable
                    if self._is_browser_error_retryable(error_msg):
                        if state.should_retry:
                            delay = self._calculate_delay(state.attempts - 1)
                            self.logger.warning(
                                "browser_error_retry",
                                error=error_msg,
                                attempt=state.attempts,
                                max_attempts=self.max_attempts,
                                delay=delay,
                                elapsed_time=state.elapsed_time,
                            )
                            time.sleep(delay)
                            continue
                        else:
                            self.logger.error(
                                "browser_error_exhausted",
                                error=error_msg,
                                attempts=state.attempts,
                                elapsed_time=state.elapsed_time,
                            )
                    raise browser_error

                if state.attempts > 1:
                    self.logger.info(
                        "retry_success",
                        attempts=state.attempts,
                        elapsed_time=state.elapsed_time,
                    )
                return result

            except Exception as e:
                state.last_exception = e

                # Check if we should stop immediately
                if self.stop_on and isinstance(e, self.stop_on):
                    self.logger.error(
                        "non_retryable_exception",
                        exception_type=type(e).__name__,
                        exception_message=str(e),
                        attempts=state.attempts,
                    )
                    raise

                # Check if exception is retryable
                is_retryable = isinstance(e, self.retry_on) and (
                    self.retry_on_predicate is None or self.retry_on_predicate(e)
                )

                if not is_retryable:
                    self.logger.error(
                        "non_retryable_exception",
                        exception_type=type(e).__name__,
                        exception_message=str(e),
                        attempts=state.attempts,
                    )
                    raise

                # Log retry attempt
                if state.should_retry:
                    delay = self._calculate_delay(state.attempts - 1)
                    self.logger.warning(
                        "retry_attempt",
                        exception_type=type(e).__name__,
                        exception_message=str(e),
                        attempt=state.attempts,
                        max_attempts=self.max_attempts,
                        delay=delay,
                        elapsed_time=state.elapsed_time,
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(
                        "retry_exhausted",
                        exception_type=type(e).__name__,
                        exception_message=str(e),
                        attempts=state.attempts,
                        elapsed_time=state.elapsed_time,
                    )

        # All attempts failed
        assert state.last_exception is not None  # for mypy
        raise RetryError(
            f"All {self.max_attempts} retry attempts failed",
            attempts=state.attempts,
            last_exception=state.last_exception,
            total_time=state.elapsed_time,
        )

    def _is_browser_error_retryable(self, error_msg: str) -> bool:
        """Check if a browser error is retryable."""
        error_msg = error_msg.lower()
        # Check for rate limiting or temporary errors
        return (
            "429" in error_msg
            or "too many requests" in error_msg
            or "network error" in error_msg
            or "timeout" in error_msg
            or "connection" in error_msg
            or "temporary" in error_msg
            or "502" in error_msg
            or "503" in error_msg
            or "504" in error_msg
        )

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        if self.strategy == BackoffStrategy.EXPONENTIAL:
            delay = self.base_delay * (self.exponential_base**attempt)
        elif self.strategy == BackoffStrategy.LINEAR:
            delay = self.base_delay * (attempt + 1)
        elif self.strategy == BackoffStrategy.FIXED:
            delay = self.base_delay
        elif self.strategy == BackoffStrategy.FIBONACCI:
            delay = self.base_delay * self._fibonacci(attempt + 1)
        else:
            delay = self.base_delay

        # Apply maximum delay limit
        delay = min(delay, self.max_delay)

        # Add jitter if enabled
        if self.jitter:
            # Add up to +/- 25% random jitter
            jitter_amount = delay * 0.25
            delay += random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay)  # Ensure non-negative

        return delay

    def _fibonacci(self, n: int) -> int:
        """Calculate nth Fibonacci number."""
        if n <= 0:
            return 0
        elif n == 1:
            return 1
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b


# Convenience decorators for common retry patterns
def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    jitter: bool = True,
    retry_on: type[Exception] | tuple[type[Exception], ...] = Exception,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Simple retry decorator."""
    retryable = Retryable(
        max_attempts=max_attempts,
        base_delay=delay,
        max_delay=delay * 10,  # Default max_delay
        strategy=strategy,
        jitter=jitter,
        retry_on=retry_on,
    )
    return retryable


def retry_transient_errors(
    max_attempts: int = 5,
    base_delay: float = 2.0,
    max_delay: float = 30.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry decorator optimized for transient network errors."""

    def is_transient(e: Exception) -> bool:
        # Check if error message indicates transient failure
        msg = str(e).lower()
        return (
            "timeout" in msg
            or "connection" in msg
            or "network" in msg
            or "temporary" in msg
            or "429" in msg  # Rate limit
            or "502" in msg  # Bad gateway
            or "503" in msg  # Service unavailable
            or "504" in msg  # Gateway timeout
        )

    retryable = Retryable(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        strategy=BackoffStrategy.EXPONENTIAL,
        jitter=True,
        retry_on=(ConnectionError, TimeoutError, Exception),
        retry_on_predicate=is_transient,
    )
    return retryable


def retry_rate_limit(
    max_attempts: int = 10,
    base_delay: float = 5.0,
    max_delay: float = 120.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry decorator optimized for rate limit errors."""

    def is_rate_limit(e: Exception) -> bool:
        msg = str(e).lower()
        return "429" in msg or "too many requests" in msg

    retryable = Retryable(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        strategy=BackoffStrategy.EXPONENTIAL,
        jitter=True,
        exponential_base=2.0,  # More aggressive for rate limits
        retry_on=Exception,
        retry_on_predicate=is_rate_limit,
    )
    return retryable


# Browser-specific retry configuration
BROWSER_RETRY_CONFIG = Retryable(
    max_attempts=5,
    base_delay=2.0,
    max_delay=60.0,
    strategy=BackoffStrategy.EXPONENTIAL,
    jitter=True,
    exponential_base=2.0,
    retry_on=Exception,
)
