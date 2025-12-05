"""Tests for the enhanced retry mechanism."""

import time
import unittest
from unittest.mock import MagicMock, patch

from crawler.utils.retry import (
    BackoffStrategy,
    RetryError,
    Retryable,
    retry,
    retry_transient_errors,
    retry_rate_limit,
)


class TestRetryable(unittest.TestCase):
    """Test cases for Retryable class."""

    def test_success_no_retries(self) -> None:
        """Test successful operation doesn't retry."""
        retryable = Retryable(max_attempts=3)
        func = MagicMock(return_value="success")

        result = retryable.execute(func)

        self.assertEqual(result, "success")
        self.assertEqual(func.call_count, 1)

    def test_retry_until_success(self) -> None:
        """Test retries until success."""
        retryable = Retryable(max_attempts=3)
        func = MagicMock(side_effect=[ValueError("fail"), ValueError("fail"), "success"])

        result = retryable.execute(func)

        self.assertEqual(result, "success")
        self.assertEqual(func.call_count, 3)

    def test_exhaust_all_retries(self) -> None:
        """Test raises RetryError after exhausting retries."""
        retryable = Retryable(max_attempts=3)
        func = MagicMock(side_effect=ValueError("always fails"))

        with self.assertRaises(RetryError) as cm:
            retryable.execute(func)

        self.assertEqual(func.call_count, 3)
        self.assertEqual(cm.exception.attempts, 3)
        self.assertIsInstance(cm.exception.last_exception, ValueError)

    def test_exponential_backoff(self) -> None:
        """Test exponential backoff delay calculation."""
        retryable = Retryable(
            strategy=BackoffStrategy.EXPONENTIAL,
            base_delay=1.0,
            max_delay=10.0,
            jitter=False,  # Disable for deterministic test
        )

        # 1st retry (attempt=0): 1.0 * 2^0 = 1.0
        self.assertEqual(retryable._calculate_delay(0), 1.0)
        # 2nd retry (attempt=1): 1.0 * 2^1 = 2.0
        self.assertEqual(retryable._calculate_delay(1), 2.0)
        # 3rd retry (attempt=2): 1.0 * 2^2 = 4.0
        self.assertEqual(retryable._calculate_delay(2), 4.0)
        # Max delay cap
        self.assertEqual(retryable._calculate_delay(10), 10.0)

    def test_linear_backoff(self) -> None:
        """Test linear backoff delay calculation."""
        retryable = Retryable(
            strategy=BackoffStrategy.LINEAR,
            base_delay=1.0,
            jitter=False,
        )

        # attempt + 1 * base_delay
        self.assertEqual(retryable._calculate_delay(0), 1.0)
        self.assertEqual(retryable._calculate_delay(1), 2.0)
        self.assertEqual(retryable._calculate_delay(2), 3.0)

    def test_fixed_backoff(self) -> None:
        """Test fixed backoff delay calculation."""
        retryable = Retryable(
            strategy=BackoffStrategy.FIXED,
            base_delay=2.0,
            jitter=False,
        )

        self.assertEqual(retryable._calculate_delay(0), 2.0)
        self.assertEqual(retryable._calculate_delay(1), 2.0)
        self.assertEqual(retryable._calculate_delay(2), 2.0)

    def test_jitter(self) -> None:
        """Test jitter is added to delays."""
        # Run multiple times to ensure jitter effect
        delays = []
        retryable = Retryable(
            base_delay=10.0,
            jitter=True,
        )

        # Calculate delay multiple times
        for _ in range(100):
            delay = retryable._calculate_delay(0)
            delays.append(delay)

        # With jitter, we should see variation
        # Some delays should be different from base delay
        has_variation = any(abs(d - 10.0) > 0.1 for d in delays)
        self.assertTrue(has_variation, "No variation detected with jitter enabled")

        # All delays should be reasonable
        for delay in delays:
            self.assertGreaterEqual(delay, 0)
            self.assertLessEqual(delay, 20.0)  # Should not exceed 2x base + jitter

    def test_retry_predicate(self) -> None:
        """Test custom retry predicate."""
        def is_retryable(e: Exception) -> bool:
            return "retry" in str(e).lower()

        retryable = Retryable(
            max_attempts=2,
            retry_on=ValueError,  # Only retry ValueError
            retry_on_predicate=is_retryable,
        )

        # Should retry
        func1 = MagicMock(side_effect=ValueError("please retry"))
        with self.assertRaises(RetryError):
            retryable.execute(func1)
        self.assertEqual(func1.call_count, 2)

        # Should not retry - use a different exception type to bypass retry_on
        retryable2 = Retryable(
            max_attempts=2,
            retry_on=ValueError,  # Only retry ValueError
            retry_on_predicate=is_retryable,
        )
        func2 = MagicMock(side_effect=TypeError("do not retry"))
        with self.assertRaises(TypeError):
            retryable2.execute(func2)
        self.assertEqual(func2.call_count, 1)

    def test_stop_on_exception(self) -> None:
        """Test stop_on prevents retry for specific exceptions."""
        retryable = Retryable(
            max_attempts=3,
            retry_on=ValueError,  # Only retry ValueError
            stop_on=RuntimeError,
        )

        func = MagicMock(side_effect=[ValueError("retry me"), RuntimeError("stop here")])

        with self.assertRaises(RuntimeError):
            retryable.execute(func)

        # Should only be called twice (once for ValueError, stop on RuntimeError)
        self.assertEqual(func.call_count, 2)


class TestRetryDecorators(unittest.TestCase):
    """Test cases for retry decorators."""

    def test_retry_decorator(self) -> None:
        """Test simple retry decorator."""
        attempts = 0

        @retry(max_attempts=3, delay=0.01)
        def failing_func() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ValueError("fail")
            return "success"

        result = failing_func()
        self.assertEqual(result, "success")
        self.assertEqual(attempts, 3)

    @patch('time.sleep')
    def test_retry_transient_errors(self, mock_sleep: MagicMock) -> None:
        """Test retry_transient_errors decorator."""
        @retry_transient_errors(max_attempts=3, base_delay=0.01)
        def api_call() -> str:
            raise ConnectionError("connection timeout")

        with self.assertRaises(RetryError):
            api_call()

        # Should have slept between retries
        self.assertEqual(mock_sleep.call_count, 2)

    @patch('time.sleep')
    def test_retry_rate_limit(self, mock_sleep: MagicMock) -> None:
        """Test retry_rate_limit decorator."""
        @retry_rate_limit(max_attempts=3, base_delay=0.01)
        def api_call() -> str:
            raise Exception("HTTP 429 Too Many Requests")

        with self.assertRaises(RetryError):
            api_call()

        # Should have slept between retries
        self.assertEqual(mock_sleep.call_count, 2)


class TestBackoffStrategy(unittest.TestCase):
    """Test backoff strategy calculations."""

    def test_fibonacci_backoff(self) -> None:
        """Test Fibonacci backoff calculation."""
        retryable = Retryable(
            strategy=BackoffStrategy.FIBONACCI,
            base_delay=1.0,
            jitter=False,
        )

        # Fibonacci sequence: 1, 1, 2, 3, 5, 8, ...
        self.assertEqual(retryable._calculate_delay(0), 1.0)  # F(1) = 1
        self.assertEqual(retryable._calculate_delay(1), 1.0)  # F(2) = 1
        self.assertEqual(retryable._calculate_delay(2), 2.0)  # F(3) = 2
        self.assertEqual(retryable._calculate_delay(3), 3.0)  # F(4) = 3
        self.assertEqual(retryable._calculate_delay(4), 5.0)  # F(5) = 5


if __name__ == "__main__":
    unittest.main()