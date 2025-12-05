"""Tests for AdaptiveRateLimiter class."""

import time
from unittest.mock import patch


from crawler.rate_limiter import AdaptiveRateLimiter


class TestAdaptiveRateLimiter:
    """Test cases for AdaptiveRateLimiter."""

    def test_initial_state(self):
        """Test initial state of rate limiter."""
        limiter = AdaptiveRateLimiter()

        assert limiter.current_delay == 2.5
        assert limiter.min_delay == 1.5
        assert limiter.max_delay == 10.0
        assert limiter.error_count == 0
        assert limiter.success_count == 0

    def test_wait_without_previous_call(self):
        """Test wait() when called first time."""
        limiter = AdaptiveRateLimiter()

        start_time = time.time()
        limiter.wait()
        elapsed = time.time() - start_time

        # Should wait approximately current_delay (2.5 seconds)
        assert 2.4 <= elapsed <= 2.6

    def test_wait_with_previous_call(self):
        """Test wait() tracks last call time."""
        limiter = AdaptiveRateLimiter()

        # Test that _last_wait_time is set after wait()
        assert limiter._last_wait_time is None

        with patch('time.sleep'):
            limiter.wait()

        # After first wait, _last_wait_time should be set
        assert limiter._last_wait_time is not None

        # Second call should use the tracking logic
        with patch('time.sleep'):
            limiter.wait()

        # _last_wait_time should still be set
        assert limiter._last_wait_time is not None

    def test_on_success_increments_counter(self):
        """Test on_success increments success counter."""
        limiter = AdaptiveRateLimiter()

        for i in range(5):
            limiter.on_success()
            assert limiter.success_count == i + 1
            assert limiter.error_count == 0

    def test_on_success_resets_error_count(self):
        """Test on_success resets error counter."""
        limiter = AdaptiveRateLimiter()

        # Simulate some errors first
        limiter.error_count = 3

        limiter.on_success()

        assert limiter.success_count == 1
        assert limiter.error_count == 0

    def test_on_success_reduces_delay_after_10_consecutive(self):
        """Test delay reduces by 10% after 10 consecutive successes."""
        limiter = AdaptiveRateLimiter()

        # Simulate 10 consecutive successes
        for _ in range(10):
            limiter.on_success()

        # Delay should be reduced by 10%: 2.5 * 0.9 = 2.25
        assert limiter.current_delay == 2.25
        assert limiter.success_count == 0  # Should reset after reducing delay

    def test_on_success_does_not_reduce_below_min_delay(self):
        """Test delay doesn't go below min_delay."""
        limiter = AdaptiveRateLimiter()
        limiter.current_delay = 1.6  # Just above min_delay

        # Simulate 10 consecutive successes
        for _ in range(10):
            limiter.on_success()

        # Delay should be min_delay (1.5), not lower
        assert limiter.current_delay == 1.5

    def test_on_rate_limit_error_increments_error_count(self):
        """Test on_rate_limit_error increments error counter."""
        limiter = AdaptiveRateLimiter()

        limiter.on_rate_limit_error()

        assert limiter.error_count == 1
        assert limiter.success_count == 0

    def test_on_rate_limit_error_doubles_delay(self):
        """Test on_rate_limit_error doubles the delay."""
        limiter = AdaptiveRateLimiter()
        initial_delay = limiter.current_delay

        limiter.on_rate_limit_error()

        assert limiter.current_delay == initial_delay * 2
        assert limiter.error_count == 1

    def test_on_rate_limit_error_does_not_exceed_max_delay(self):
        """Test delay doesn't exceed max_delay."""
        limiter = AdaptiveRateLimiter()
        limiter.current_delay = 6.0  # Half of max_delay

        limiter.on_rate_limit_error()

        # Should double to max_delay (10.0), not exceed it
        assert limiter.current_delay == 10.0

    def test_on_rate_limit_error_at_max_delay(self):
        """Test delay stays at max_delay when already at max."""
        limiter = AdaptiveRateLimiter()
        limiter.current_delay = 10.0  # Already at max

        limiter.on_rate_limit_error()

        # Should stay at max_delay
        assert limiter.current_delay == 10.0

    def test_on_error_resets_success_count(self):
        """Test on_error resets success counter."""
        limiter = AdaptiveRateLimiter()
        limiter.success_count = 5

        limiter.on_error()

        assert limiter.success_count == 0
        assert limiter.error_count == 0  # on_error doesn't increment error_count

    def test_on_error_does_not_change_delay(self):
        """Test on_error doesn't change delay."""
        limiter = AdaptiveRateLimiter()
        initial_delay = limiter.current_delay

        limiter.on_error()

        assert limiter.current_delay == initial_delay

    def test_mixed_success_and_errors(self):
        """Test mixed scenario of successes and errors."""
        limiter = AdaptiveRateLimiter()

        # 5 successes
        for _ in range(5):
            limiter.on_success()
        assert limiter.success_count == 5

        # 1 error resets success count
        limiter.on_rate_limit_error()
        assert limiter.success_count == 0
        assert limiter.current_delay == 5.0  # 2.5 * 2

        # 10 more successes should reduce delay
        for _ in range(10):
            limiter.on_success()
        assert limiter.current_delay == 4.5  # 5.0 * 0.9
        assert limiter.success_count == 0

    def test_get_retry_delay_exponential_backoff(self):
        """Test get_retry_delay returns exponential backoff values."""
        limiter = AdaptiveRateLimiter()

        # First attempt
        assert limiter.get_retry_delay(0) == 2

        # Second attempt
        assert limiter.get_retry_delay(1) == 4

        # Third attempt
        assert limiter.get_retry_delay(2) == 8

    def test_reset(self):
        """Test reset restores initial state."""
        limiter = AdaptiveRateLimiter()

        # Change state
        limiter.current_delay = 5.0
        limiter.error_count = 3
        limiter.success_count = 7

        # Reset
        limiter.reset()

        # Check initial state restored
        assert limiter.current_delay == 2.5
        assert limiter.error_count == 0
        assert limiter.success_count == 0

    def test_str_representation(self):
        """Test string representation of rate limiter."""
        limiter = AdaptiveRateLimiter()

        # Change some values
        limiter.current_delay = 3.7
        limiter.success_count = 5

        str_repr = str(limiter)

        assert "AdaptiveRateLimiter" in str_repr
        assert "3.7" in str_repr
        assert "success_count=5" in str_repr