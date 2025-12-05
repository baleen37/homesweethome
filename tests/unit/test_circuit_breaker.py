"""Tests for the CircuitBreaker pattern implementation."""

import time
import unittest
from unittest.mock import MagicMock, patch

from crawler.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    NaverAPIBreaker,
)


class TestCircuitBreaker(unittest.TestCase):
    """Test cases for CircuitBreaker."""

    def setUp(self) -> None:
        self.breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1.0,
        )

    def test_initial_state(self) -> None:
        """Test circuit breaker starts in closed state."""
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)
        self.assertEqual(self.breaker.failure_count, 0)
        self.assertIsNone(self.breaker.last_failure_time)

    def test_successful_call_resets_failure_count(self) -> None:
        """Test successful calls reset failure count."""
        # Simulate some failures
        for _ in range(2):
            try:
                self.breaker.call(lambda: 1/0)
            except ZeroDivisionError:
                pass

        self.assertEqual(self.breaker.failure_count, 2)

        # Successful call
        result = self.breaker.call(lambda: 42)
        self.assertEqual(result, 42)
        self.assertEqual(self.breaker.failure_count, 0)

    def test_opens_after_threshold(self) -> None:
        """Test circuit opens after failure threshold is reached."""
        # Fail 3 times (threshold)
        for i in range(3):
            with self.assertRaises(ZeroDivisionError):
                self.breaker.call(lambda: 1/0)

        self.assertEqual(self.breaker.state, CircuitState.OPEN)
        self.assertEqual(self.breaker.failure_count, 3)

    def test_prevents_calls_when_open(self) -> None:
        """Test circuit prevents calls when open."""
        # Open the circuit
        for _ in range(3):
            try:
                self.breaker.call(lambda: 1/0)
            except ZeroDivisionError:
                pass

        # Should raise CircuitOpenError instead of executing
        with self.assertRaises(CircuitOpenError):
            self.breaker.call(lambda: 42)

    def test_half_open_after_timeout(self) -> None:
        """Test circuit enters half-open state after recovery timeout."""
        # Open the circuit
        for _ in range(3):
            try:
                self.breaker.call(lambda: 1/0)
            except ZeroDivisionError:
                pass

        self.assertEqual(self.breaker.state, CircuitState.OPEN)

        # Wait for recovery timeout
        time.sleep(1.1)

        # Next call should go through (half-open state)
        result = self.breaker.call(lambda: 42)
        self.assertEqual(result, 42)
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)

    def test_reopens_on_half_open_failure(self) -> None:
        """Test circuit reopens if call fails in half-open state."""
        # Open the circuit
        for _ in range(3):
            try:
                self.breaker.call(lambda: 1/0)
            except ZeroDivisionError:
                pass

        # Wait for recovery timeout
        time.sleep(1.1)

        # Fail in half-open state
        with self.assertRaises(ZeroDivisionError):
            self.breaker.call(lambda: 1/0)

        # Should be open again
        self.assertEqual(self.breaker.state, CircuitState.OPEN)

    def test_decorator_usage(self) -> None:
        """Test circuit breaker as decorator."""
        @self.breaker
        def failing_function() -> int:
            raise ValueError("Test error")

        # Fail threshold times
        for _ in range(3):
            with self.assertRaises(ValueError):
                failing_function()

        # Should now raise CircuitOpenError
        with self.assertRaises(CircuitOpenError):
            failing_function()

    def test_force_states(self) -> None:
        """Test forcing circuit states."""
        # Force open
        self.breaker.force_open()
        self.assertEqual(self.breaker.state, CircuitState.OPEN)

        # Should prevent calls
        with self.assertRaises(CircuitOpenError):
            self.breaker.call(lambda: 42)

        # Force close
        self.breaker.force_close()
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)
        self.assertEqual(self.breaker.failure_count, 0)

        # Should allow calls
        result = self.breaker.call(lambda: 42)
        self.assertEqual(result, 42)

    def test_get_state(self) -> None:
        """Test getting circuit state information."""
        # Fail once
        try:
            self.breaker.call(lambda: 1/0)
        except ZeroDivisionError:
            pass

        state = self.breaker.get_state()
        self.assertEqual(state["state"], CircuitState.CLOSED.value)
        self.assertEqual(state["failure_count"], 1)
        self.assertEqual(state["failure_threshold"], 3)
        self.assertIsNotNone(state["last_failure_time"])

    def test_custom_exception_types(self) -> None:
        """Test circuit breaker with custom exception types."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            expected_exception=ValueError,
        )

        # Should not count non-ValueError exceptions
        with self.assertRaises(ZeroDivisionError):
            breaker.call(lambda: 1/0)
        self.assertEqual(breaker.failure_count, 0)

        # Should count ValueError exceptions
        with self.assertRaises(ValueError):
            breaker.call(lambda: (_ for _ in ()).throw(ValueError("test")))
        self.assertEqual(breaker.failure_count, 1)

        # Second ValueError should open circuit
        with self.assertRaises(ValueError):
            breaker.call(lambda: (_ for _ in ()).throw(ValueError("test")))
        self.assertEqual(breaker.state, CircuitState.OPEN)


class TestNaverAPIBreaker(unittest.TestCase):
    """Test cases for NaverAPIBreaker."""

    def test_configuration(self) -> None:
        """Test NaverAPIBreaker has correct configuration."""
        breaker = NaverAPIBreaker()
        self.assertEqual(breaker.failure_threshold, 10)
        self.assertEqual(breaker.recovery_timeout, 120.0)


if __name__ == "__main__":
    unittest.main()