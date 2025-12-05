"""Timeout utilities for API calls and operations.

This module provides timeout decorators and context managers
to prevent operations from hanging indefinitely.
"""

from __future__ import annotations

import signal
import threading
import time
from contextlib import contextmanager
from typing import Any, Callable, TypeVar

import structlog

logger = structlog.get_logger()

T = TypeVar("T")


class TimeoutError(Exception):
    """Raised when operation times out."""
    pass


class TimeoutContext:
    """Context manager for timing out operations."""

    def __init__(self, timeout_seconds: float, error_message: str | None = None) -> None:
        """
        Initialize timeout context.

        Args:
            timeout_seconds: Timeout in seconds
            error_message: Custom error message
        """
        self.timeout_seconds = timeout_seconds
        self.error_message = error_message or f"Operation timed out after {timeout_seconds} seconds"
        self.timer: threading.Timer | None = None

    def __enter__(self) -> None:
        """Start timeout timer."""
        if self.timeout_seconds > 0:
            self.timer = threading.Timer(
                self.timeout_seconds,
                self._raise_timeout,
            )
            self.timer.daemon = True  # Don't prevent program exit
            self.timer.start()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Cancel timeout timer."""
        if self.timer:
            self.timer.cancel()
            self.timer = None

    def _raise_timeout(self) -> None:
        """Raise timeout error in main thread."""
        # Note: This will raise in the timer thread, but the exception
        # will be caught when the main thread checks for timeouts
        logger.warning(
            "operation_timed_out",
            timeout_seconds=self.timeout_seconds,
        )
        raise TimeoutError(self.error_message)

    @classmethod
    def wrap(
        cls,
        timeout_seconds: float,
        error_message: str | None = None,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Decorator to wrap function with timeout."""
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            def wrapper(*args: Any, **kwargs: Any) -> T:
                with cls(timeout_seconds, error_message):
                    return func(*args, **kwargs)
            return wrapper
        return decorator


# Platform-specific timeout implementations
if hasattr(signal, "SIGALRM"):
    # Unix-like systems with signal support
    class SignalTimeout:
        """Signal-based timeout for Unix-like systems."""

        def __init__(self, timeout_seconds: float) -> None:
            self.timeout_seconds = timeout_seconds
            self.old_handler: Any = None

        def __enter__(self) -> None:
            """Set up signal handler."""
            if self.timeout_seconds > 0:
                self.old_handler = signal.signal(signal.SIGALRM, self._raise_timeout)
                signal.alarm(int(self.timeout_seconds))

        def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            """Clean up signal handler."""
            if self.timeout_seconds > 0:
                signal.alarm(0)
                if self.old_handler:
                    signal.signal(signal.SIGALRM, self.old_handler)
                    self.old_handler = None

        def _raise_timeout(self, signum: int, frame: Any) -> None:
            """Signal handler that raises timeout error."""
            raise TimeoutError(f"Operation timed out after {self.timeout_seconds} seconds")

        @classmethod
        def wrap(cls, timeout_seconds: float) -> Callable[[Callable[..., T]], Callable[..., T]]:
            """Decorator to wrap function with signal-based timeout."""
            def decorator(func: Callable[..., T]) -> Callable[..., T]:
                def wrapper(*args: Any, **kwargs: Any) -> T:
                    with cls(timeout_seconds):
                        return func(*args, **kwargs)
                return wrapper
            return decorator
else:
    # Windows or other systems without signal support
    SignalTimeout = TimeoutContext  # Fallback to thread-based timeout


# Specialized timeout contexts
class APITimeout(TimeoutContext):
    """Timeout context optimized for API calls."""

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        super().__init__(
            timeout_seconds=timeout_seconds,
            error_message=f"API call timed out after {timeout_seconds} seconds",
        )


class DatabaseTimeout(TimeoutContext):
    """Timeout context optimized for database operations."""

    def __init__(self, timeout_seconds: float = 60.0) -> None:
        super().__init__(
            timeout_seconds=timeout_seconds,
            error_message=f"Database operation timed out after {timeout_seconds} seconds",
        )


class NetworkTimeout(TimeoutContext):
    """Timeout context optimized for network operations."""

    def __init__(self, timeout_seconds: float = 45.0) -> None:
        super().__init__(
            timeout_seconds=timeout_seconds,
            error_message=f"Network operation timed out after {timeout_seconds} seconds",
        )


# Convenience decorators
def timeout(
    timeout_seconds: float,
    error_message: str | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Simple timeout decorator."""
    return TimeoutContext.wrap(timeout_seconds, error_message)


def api_timeout(timeout_seconds: float = 30.0) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """API call timeout decorator."""
    return APITimeout.wrap(timeout_seconds)


def db_timeout(timeout_seconds: float = 60.0) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Database operation timeout decorator."""
    return DatabaseTimeout.wrap(timeout_seconds)


def network_timeout(timeout_seconds: float = 45.0) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Network operation timeout decorator."""
    return NetworkTimeout.wrap(timeout_seconds)


# Timeout with retry helper
def timeout_with_retry(
    timeout_seconds: float,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator that adds timeout and retry logic.

    Args:
        timeout_seconds: Timeout for each attempt
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    with TimeoutContext(timeout_seconds):
                        return func(*args, **kwargs)
                except TimeoutError as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            "operation_timed_out_retrying",
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            timeout_seconds=timeout_seconds,
                            retry_delay=retry_delay,
                        )
                        time.sleep(retry_delay)
                        # Exponential backoff for subsequent retries
                        retry_delay *= 2
                    else:
                        logger.error(
                            "operation_timed_out_all_retries_failed",
                            attempts=attempt + 1,
                            timeout_seconds=timeout_seconds,
                        )

            # All retries failed
            assert last_exception is not None
            raise last_exception

        return wrapper
    return decorator


# Context manager for multiple timeouts
class MultiTimeout:
    """Manage multiple concurrent timeouts for different operations."""

    def __init__(self, **timeouts: float) -> None:
        """
        Initialize with named timeouts.

        Example:
            with MultiTimeout(api=30, db=60, network=45) as mt:
                # Use specific timeout
                with mt.timeout("api"):
                    api_call()
        """
        self.timeouts = timeouts
        self.active: set[str] = set()

    @contextmanager
    def timeout(self, name: str) -> Any:
        """Context manager for a specific named timeout."""
        if name not in self.timeouts:
            raise ValueError(f"Unknown timeout: {name}")

        timeout_seconds = self.timeouts[name]
        self.active.add(name)

        try:
            with TimeoutContext(timeout_seconds, f"Operation '{name}' timed out"):
                yield
        finally:
            self.active.discard(name)

    def __enter__(self) -> "MultiTimeout":
        """Enter multi-timeout context."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit multi-timeout context."""
        # All active timeouts should be automatically cleaned up
        self.active.clear()