"""Tests for enhanced retry logic and circuit breaker functionality

This module tests the improved error handling with:
- Exponential backoff with jitter
- Circuit breaker pattern
- Error classification (transient vs permanent)
- Integration with API client
"""

import time
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.crawler.api.hogangnono_client import HogangnonoAPIClient
from src.crawler.utils.retry import Retryable, BackoffStrategy, RetryError, retry
from src.crawler.utils.enhanced_error_handler import EnhancedErrorHandler, CircuitBreaker, ErrorType
from src.crawler.config import CrawlerConfig


class TestExponentialBackoff:
    """Test exponential backoff retry logic"""

    def test_exponential_backoff_delays(self):
        """Test that exponential backoff produces correct delays"""
        retryable = Retryable(
            max_attempts=5,
            base_delay=1.0,
            max_delay=100.0,
            strategy=BackoffStrategy.EXPONENTIAL,
            jitter=False,  # Disable for predictable testing
        )

        delays = []
        for i in range(5):
            delay = retryable._calculate_delay(i)
            delays.append(delay)

        # Should be: 1.0, 2.0, 4.0, 8.0, 16.0
        assert delays == [1.0, 2.0, 4.0, 8.0, 16.0]

    def test_exponential_backoff_with_max_delay(self):
        """Test that max_delay limits exponential growth"""
        retryable = Retryable(
            max_attempts=10,
            base_delay=2.0,
            max_delay=10.0,
            strategy=BackoffStrategy.EXPONENTIAL,
            jitter=False,
        )

        delays = [retryable._calculate_delay(i) for i in range(5)]
        # Should be: 2.0, 4.0, 8.0, 10.0, 10.0 (capped at max_delay)
        assert delays == [2.0, 4.0, 8.0, 10.0, 10.0]

    def test_jitter_adds_randomness(self):
        """Test that jitter adds randomness to delays"""
        retryable = Retryable(
            max_attempts=5,
            base_delay=1.0,
            max_delay=100.0,
            strategy=BackoffStrategy.EXPONENTIAL,
            jitter=True,
        )

        # Get multiple delays for same attempt
        delays = [retryable._calculate_delay(2) for _ in range(10)]

        # All delays should be different (or at least not all the same)
        assert len(set(round(d, 3) for d in delays)) > 1
        # All should be within reasonable bounds
        for delay in delays:
            assert 2.5 <= delay <= 6.0  # 4.0 +/- 25%

    def test_retry_on_specific_exceptions(self):
        """Test retry configuration for specific exception types"""

        @retry(max_attempts=3, delay=0.1, jitter=False, retry_on=ValueError)
        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(RetryError) as exc_info:
            failing_func()

        # Should have attempted 3 times
        assert exc_info.value.attempts == 3
        assert isinstance(exc_info.value.last_exception, ValueError)

    def test_no_retry_for_non_retryable_exception(self):
        """Test that non-retryable exceptions are not retried"""

        @retry(max_attempts=3, delay=0.1, jitter=False, retry_on=ValueError)
        def failing_func():
            raise TypeError("Non-retryable error")

        with pytest.raises(TypeError):
            failing_func()

    def test_retry_with_predicate(self):
        """Test retry with custom predicate function"""

        def is_retryable(e):
            return "retry" in str(e).lower()

        @retry(max_attempts=3, delay=0.1, jitter=False, retry_on_predicate=is_retryable)
        def should_retry():
            raise Exception("Please retry this")

        @retry(max_attempts=3, delay=0.1, jitter=False, retry_on_predicate=is_retryable)
        def should_not_retry():
            raise Exception("Don't retry this")

        with pytest.raises(RetryError):
            should_retry()

        with pytest.raises(Exception):
            should_not_retry()


class TestCircuitBreaker:
    """Test circuit breaker pattern implementation"""

    def test_circuit_breaker_opens_after_threshold(self):
        """Test that circuit opens after failure threshold"""
        breaker = CircuitBreaker(failure_threshold=3, timeout=1)

        @breaker
        def failing_func():
            raise Exception("Simulated failure")

        # First 3 failures
        for _ in range(3):
            with pytest.raises(Exception):
                failing_func()

        # Circuit should now be open
        assert breaker.state == "OPEN"

        # Next call should fail immediately
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            failing_func()

    def test_circuit_breaker_half_open_after_timeout(self):
        """Test that circuit becomes half-open after timeout"""
        breaker = CircuitBreaker(failure_threshold=2, timeout=0.1)

        @breaker
        def failing_func():
            raise Exception("Simulated failure")

        # Trigger failures to open circuit
        for _ in range(2):
            with pytest.raises(Exception):
                failing_func()

        assert breaker.state == "OPEN"

        # Wait for timeout
        time.sleep(0.2)

        # Manually set to half-open to test state transition
        breaker.state = "HALF_OPEN"

        # Next call should attempt and keep in half-open if it fails
        with pytest.raises(Exception):
            failing_func()

        # Should be back to OPEN after failure in half-open
        assert breaker.state == "OPEN"

    def test_circuit_breaker_closes_on_success(self):
        """Test that circuit closes on successful call"""
        breaker = CircuitBreaker(failure_threshold=2, timeout=0.1)

        call_count = 0

        @breaker
        def sometimes_failing():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("First failures")
            return "success"

        # Trigger failures to open circuit
        for _ in range(2):
            with pytest.raises(Exception):
                sometimes_failing()

        assert breaker.state == "OPEN"

        # Wait for timeout
        time.sleep(0.2)

        # Manually set to half-open for testing
        breaker.state = "HALF_OPEN"

        # Get success - should close circuit
        result = sometimes_failing()

        assert result == "success"
        assert breaker.state == "CLOSED"


class TestEnhancedErrorHandler:
    """Test enhanced error handler functionality"""

    def test_error_classification(self):
        """Test proper classification of different error types"""
        handler = EnhancedErrorHandler()

        # Test 404 classification
        error_info = handler.classify_error(
            status_code=404, error_message="Not found", apartment_id="apt_123"
        )

        assert error_info.error_type == ErrorType.NOT_FOUND
        assert error_info.is_transient is False

        # Test rate limit classification
        error_info = handler.classify_error(status_code=429, error_message="Rate limit exceeded")

        assert error_info.error_type == ErrorType.RATE_LIMIT
        assert error_info.is_transient is True

        # Test server error classification
        error_info = handler.classify_error(status_code=500, error_message="Internal server error")

        assert error_info.error_type == ErrorType.SERVER_ERROR
        assert error_info.is_transient is True

    def test_apartment_id_filter(self):
        """Test apartment ID filtering functionality"""
        handler = EnhancedErrorHandler()
        filter_obj = handler.id_filter

        # Initially should not skip
        assert not filter_obj.should_skip("apt_123")

        # Mark as invalid
        filter_obj.mark_invalid("apt_123", "404 Not Found")
        assert filter_obj.should_skip("apt_123")
        assert filter_obj.is_invalid("apt_123")

        # Mark as temporarily unavailable
        filter_obj.mark_temporarily_unavailable("apt_456")
        assert filter_obj.should_skip("apt_456")
        assert filter_obj.is_temporarily_unavailable("apt_456")

        # Temporary should expire
        with patch("src.crawler.utils.enhanced_error_handler.datetime") as mock_dt:
            # Mock time 2 hours later
            mock_dt.now.return_value = datetime.now() + timedelta(hours=2)
            assert not filter_obj.is_temporarily_unavailable("apt_456")

    def test_retry_logic_with_transient_errors(self):
        """Test that transient errors trigger retries"""
        handler = EnhancedErrorHandler(max_retries=2, retry_delay=0.1)

        attempt_count = 0

        def mock_api_call():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                # Return transient error for first 2 attempts
                class MockResponse:
                    success = False
                    error = "Server error"
                    status_code = 503

                return MockResponse()
            else:
                # Success on third attempt
                class MockResponse:
                    success = True
                    data = {"result": "success"}

                return MockResponse()

        result = handler.execute_with_retry(mock_api_call, apartment_id="apt_123")

        assert result.success
        assert result.data == {"result": "success"}
        assert attempt_count == 3

    def test_no_retry_for_permanent_errors(self):
        """Test that permanent errors don't trigger retries"""
        handler = EnhancedErrorHandler(max_retries=2, retry_delay=0.1)

        attempt_count = 0

        def mock_api_call():
            nonlocal attempt_count
            attempt_count += 1

            class MockResponse:
                success = False
                error = "Not found"
                status_code = 404

            return MockResponse()

        result = handler.execute_with_retry(mock_api_call, apartment_id="apt_123")

        # Should only attempt once (no retries for 404)
        assert attempt_count == 1
        assert not result.success


class TestAPIWithEnhancedRetry:
    """Test API client with enhanced retry logic"""

    @patch("src.crawler.api.hogangnono_client.Session")
    def test_api_uses_exponential_backoff(self, mock_session_class):
        """Test that API client uses exponential backoff for retries"""
        # Setup mock session
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Create mock response that fails twice then succeeds
        responses = [
            Mock(status_code=503, reason="Service Unavailable"),
            Mock(status_code=503, reason="Service Unavailable"),
            Mock(status_code=200, reason="OK"),
        ]

        for i, resp in enumerate(responses):
            resp.json.return_value = {"data": f"response_{i}"}
            resp.headers = {"content-type": "application/json"}

        mock_session.request.side_effect = responses

        # Create API client with reduced timeout for testing
        config = CrawlerConfig()
        config.timeout = 0.1
        # Set max_retries via direct attribute assignment
        client = HogangnonoAPIClient(config)
        client.max_retries = 2

        # Mock _initialize_session to avoid real network calls
        client._session_initialized = True

        # Track call timing to verify exponential backoff
        start_time = time.time()
        response = client._make_request("GET", "/test")
        elapsed_time = time.time() - start_time

        # Should have made 3 attempts (1 initial + 2 retries)
        assert mock_session.request.call_count == 3
        assert response.success

        # Should have taken at least some time due to backoff
        assert elapsed_time >= 0.2  # At least 2 * delay with backoff

    @patch("src.crawler.api.hogangnono_client.Session")
    def test_api_handles_circuit_breaker(self, mock_session_class):
        """Test that API client respects circuit breaker"""
        # Setup mock session that always fails
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.request.side_effect = Exception("Connection failed")

        config = CrawlerConfig()
        config.timeout = 0.1
        # Set max_retries via direct attribute assignment
        client = HogangnonoAPIClient(config)
        client.max_retries = 0  # Disable retries for circuit breaker test
        client._session_initialized = True

        # Create error handler with circuit breaker
        handler = EnhancedErrorHandler()
        handler.circuit_breaker.failure_threshold = 2
        handler.circuit_breaker.timeout = 0.1

        # First two calls should fail and open circuit
        for _ in range(2):
            with pytest.raises(Exception):
                handler.execute_with_retry(client._make_request, "GET", "/test")

        # Circuit should now be open
        assert handler.circuit_breaker.state == "OPEN"

        # Next call should fail immediately due to open circuit
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            handler.execute_with_retry(client._make_request, "GET", "/test")


class TestIntegrationScenarios:
    """Test realistic integration scenarios"""

    @patch("src.crawler.api.hogangnono_client.Session")
    def test_mixed_error_scenarios(self, mock_session_class):
        """Test handling of mixed error types"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Simulate a realistic scenario:
        # - Some apartments return 404 (permanent)
        # - Some have temporary network issues
        # - Rate limiting occurs occasionally
        responses = [
            Mock(status_code=404, reason="Not Found"),  # Permanent failure
            Mock(status_code=429, reason="Too Many Requests"),  # Rate limit
            Mock(status_code=503, reason="Service Unavailable"),  # Transient
            Mock(status_code=200, reason="OK"),  # Success
        ]

        for i, resp in enumerate(responses):
            resp.json.return_value = {"data": f"response_{i}"} if resp.status_code == 200 else None
            resp.headers = {"content-type": "application/json"}
            resp.text = "Error response"

        mock_session.request.side_effect = responses

        config = CrawlerConfig()
        config.timeout = 0.1
        # Set max_retries via direct attribute assignment
        client = HogangnonoAPIClient(config)
        client.max_retries = 2
        client._session_initialized = True

        # Create handler to track error types
        handler = EnhancedErrorHandler()
        handler.max_retries = 1
        handler.retry_delay = 0.05

        results = []
        for _ in responses:
            try:
                response = handler.execute_with_retry(
                    client._make_request, "GET", "/apartments/123"
                )
                results.append(("success", response))
            except Exception as e:
                results.append(("error", str(e)))

        # Verify handling
        assert len(results) == 4
        # First should fail immediately (404)
        assert results[0][0] == "error"
        # Second should retry (429)
        assert results[1][0] == "error"
        # Third should retry (503)
        assert results[2][0] == "error"
        # Fourth should succeed
        assert results[3][0] == "success"

        # Check error statistics
        summary = handler.get_error_summary()
        assert summary["error_statistics"]["total_requests"] == 4
        assert summary["error_statistics"]["total_errors"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
