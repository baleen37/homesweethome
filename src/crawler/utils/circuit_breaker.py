"""Circuit breaker pattern implementation for handling repeated failures.

This module implements the Circuit Breaker pattern to prevent cascading failures
when external dependencies (APIs, databases, etc.) are experiencing issues.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Callable, TypeVar

import structlog

logger = structlog.get_logger()

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Fail fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


class CircuitBreaker:
    """
    Circuit breaker that wraps callable operations.

    The circuit breaker monitors failures and temporarily stops calling
    the operation when the failure threshold is reached.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] | tuple[type[Exception], ...] = Exception,
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again (half-open state)
            expected_exception: Exception types that count as failures
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = CircuitState.CLOSED

        self.logger = structlog.get_logger().bind(
            circuit_breaker=id(self),
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to wrap a function with circuit breaker."""
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return self.call(func, *args, **kwargs)
        return wrapper

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute the protected operation.

        Args:
            func: The operation to protect
            *args: Arguments to pass to func
            **kwargs: Keyword arguments to pass to func

        Returns:
            Result of func(*args, **kwargs)

        Raises:
            Exception: The original exception if in CLOSED state
            CircuitOpenError: If circuit is OPEN
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.logger.info("circuit_half_open", failure_count=self.failure_count)
            else:
                self.logger.warning(
                    "circuit_open_preventing_call",
                    last_failure_time=self.last_failure_time,
                    timeout_remaining=self._timeout_remaining(),
                )
                raise CircuitOpenError(
                    f"Circuit breaker is OPEN. Last failure: {self.last_failure_time}. "
                    f"Timeout remaining: {self._timeout_remaining():.1f}s"
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout

    def _timeout_remaining(self) -> float:
        """Calculate remaining timeout before half-open state."""
        if self.last_failure_time is None:
            return 0.0
        elapsed = time.time() - self.last_failure_time
        return max(0.0, self.recovery_timeout - elapsed)

    def _on_success(self) -> None:
        """Handle successful operation."""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.logger.info("circuit_closed_after_success")
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success in closed state
            if self.failure_count > 0:
                self.failure_count = 0
                self.logger.debug("circuit_failure_count_reset")

    def _on_failure(self) -> None:
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.warning(
                "circuit_opened",
                failure_count=self.failure_count,
                threshold=self.failure_threshold,
            )
        else:
            self.logger.warning(
                "circuit_failure_incremented",
                failure_count=self.failure_count,
                threshold=self.failure_threshold,
            )

    def force_open(self) -> None:
        """Force circuit to open state (for testing)."""
        self.state = CircuitState.OPEN
        self.failure_count = self.failure_threshold  # Ensure it meets threshold
        self.last_failure_time = time.time()
        self.logger.info("circuit_forced_open")

    def force_close(self) -> None:
        """Force circuit to closed state (for testing/recovery)."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0
        self.logger.info("circuit_forced_closed")

    def get_state(self) -> dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time,
            "recovery_timeout": self.recovery_timeout,
            "timeout_remaining": self._timeout_remaining() if self.state == CircuitState.OPEN else None,
        }


class CircuitOpenError(Exception):
    """Raised when circuit breaker prevents operation execution."""
    pass


# Pre-configured circuit breakers for different services
class NaverAPIBreaker(CircuitBreaker):
    """Circuit breaker optimized for Naver API calls."""

    def __init__(self) -> None:
        # Naver API can be aggressive with rate limiting
        super().__init__(
            failure_threshold=10,  # More failures before opening
            recovery_timeout=120.0,  # 2 minutes to recover
            expected_exception=(ConnectionError, TimeoutError, Exception),
        )


class DatabaseBreaker(CircuitBreaker):
    """Circuit breaker for database operations."""

    def __init__(self) -> None:
        super().__init__(
            failure_threshold=5,
            recovery_timeout=30.0,
            expected_exception=(ConnectionError, TimeoutError),
        )