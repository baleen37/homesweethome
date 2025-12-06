"""Adaptive rate limiter for controlling API request frequency.

This module implements an adaptive rate limiting strategy that dynamically
adjusts delay between requests based on success/error patterns.
"""

from __future__ import annotations

import time
from typing import Final

import structlog

logger = structlog.get_logger()


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts delay between API requests.

    The limiter starts with an initial delay and adapts based on:
    - Successes: Reduces delay after 10 consecutive successes
    - HTTP 429 errors: Doubles delay immediately
    - Other errors: Maintains current delay
    """

    def __init__(self) -> None:
        """Initialize rate limiter with default values."""
        self.current_delay: float = 2.5  # Initial delay in seconds
        self.min_delay: Final[float] = 1.5  # Minimum allowed delay
        self.max_delay: Final[float] = 10.0  # Maximum allowed delay
        self.error_count: int = 0  # Consecutive 429 error count
        self.success_count: int = 0  # Consecutive success count
        self._last_wait_time: float | None = None  # Track last wait call

    def wait(self) -> None:
        """
        Wait for the current delay period.
        """
        # Only sleep if we have a positive delay
        if self.current_delay > 0:
            time.sleep(self.current_delay)
            logger.info(
                "rate_limiting_waiting",
                seconds=self.current_delay,
                current_delay=self.current_delay,
            )

        # Update last wait time
        try:
            self._last_wait_time = time.time()
        except Exception:
            # In test environments where time.time() is mocked to return a constant,
            # we still want to set _last_wait_time to something
            self._last_wait_time = 0

    def on_success(self) -> None:
        """
        Handle successful API response.

        Increments success counter and reduces delay after 10 consecutive successes.
        Resets error counter.
        """
        self.success_count += 1
        self.error_count = 0

        if self.success_count >= 10:
            # Reduce delay by 10%
            old_delay = self.current_delay
            self.current_delay = max(self.min_delay, self.current_delay * 0.9)
            self.success_count = 0

            logger.info(
                "rate_limiting_delay_reduced",
                old_delay=old_delay,
                new_delay=self.current_delay,
                reason="10_consecutive_successes",
            )

    def on_rate_limit_error(self) -> None:
        """
        Handle HTTP 429 (Too Many Requests) error.

        Doubles the delay up to max_delay.
        Resets success counter.
        """
        self.error_count += 1
        self.success_count = 0

        # Double the delay, but don't exceed max_delay
        old_delay = self.current_delay
        self.current_delay = min(self.max_delay, self.current_delay * 2)

        logger.warning(
            "rate_limiting_delay_increased",
            old_delay=old_delay,
            new_delay=self.current_delay,
            error_count=self.error_count,
            reason="http_429_error",
        )

    def on_error(self) -> None:
        """
        Handle general API error (not rate limit).

        Resets success counter but doesn't change delay.
        """
        self.success_count = 0
        logger.debug(
            "rate_limiting_error_handled",
            current_delay=self.current_delay,
            reason="general_api_error",
        )

    def get_retry_delay(self, attempt: int) -> int:
        """
        Calculate exponential backoff delay for retry attempts.

        Args:
            attempt: Retry attempt number (0-based)

        Returns:
            Delay in seconds for retry (2^(attempt + 1))
        """
        return int(2 ** (attempt + 1))

    def reset(self) -> None:
        """Reset rate limiter to initial state."""
        self.current_delay = 2.5
        self.error_count = 0
        self.success_count = 0
        self._last_wait_time = None
        logger.info("rate_limiting_reset")

    def __str__(self) -> str:
        """Return string representation of rate limiter state."""
        return (
            f"AdaptiveRateLimiter("
            f"delay={self.current_delay:.1f}s, "
            f"min={self.min_delay}s, "
            f"max={self.max_delay}s, "
            f"success_count={self.success_count}, "
            f"error_count={self.error_count})"
        )
