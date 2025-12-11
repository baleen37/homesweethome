import pytest
import time

# Import test setup to configure path and mocks

from crawler.rate_limiter import AdaptiveRateLimiter


def test_rate_limiter_adapts_to_real_api_responses(integration_test_dir):
    """Test that rate limiter adapts to actual API responses"""

    limiter = AdaptiveRateLimiter()
    limiter.current_delay = 5.0  # Start with 5 second delay

    # Simulate successful requests
    for i in range(10):
        limiter.on_success()
        start_time = time.time()
        limiter.wait()
        wait_time = time.time() - start_time

        # After 10 successes, delay should decrease
        # Note: the delay only reduces AFTER the 10th success
        if i >= 9:
            # The 11th wait (after 10 successes) should be shorter
            limiter.on_success()  # One more to trigger reduction
            start_time = time.time()
            limiter.wait()
            wait_time = time.time() - start_time
            assert wait_time < 5.0, f"Delay should decrease after successes, got {wait_time}"
            break

    # Reset and test rate limit error
    limiter.reset()
    limiter.current_delay = 5.0

    # Simulate rate limit error
    limiter.on_rate_limit_error()

    # Delay should increase significantly
    start_time = time.time()
    limiter.wait()
    wait_time = time.time() - start_time

    assert wait_time > 5.0, f"Delay should increase after rate limit, got {wait_time}"


def test_rate_limiting_with_real_api_calls(integration_test_dir):
    """Test rate limiting behavior with actual API calls"""
    try:
        import requests
        from crawler.rate_limiter import AdaptiveRateLimiter
    except ImportError as e:
        pytest.fail(f"Required modules not implemented: {e}")

    limiter = AdaptiveRateLimiter()
    limiter.current_delay = 2.0

    # Make multiple rapid requests to test adaptation
    response_times = []
    for i in range(5):
        start_time = time.time()
        try:
            response = requests.get("https://hogangnono.com/api/v2/ranks/rolling", timeout=5)

            if response.status_code == 200:
                limiter.on_success()
            elif response.status_code == 429:
                limiter.on_rate_limit_error()
            else:
                limiter.on_error()
        except Exception:
            limiter.on_error()

        limiter.wait()
        total_time = time.time() - start_time
        response_times.append(total_time)

    # Verify rate limiting is working (requests should be spaced out)
    assert all(t > 1.5 for t in response_times), "Rate limiting should enforce minimum delays"


def test_rate_limiter_boundary_conditions(integration_test_dir):
    """Test rate limiter handles boundary conditions"""
    try:
        from crawler.rate_limiter import AdaptiveRateLimiter
    except ImportError as e:
        pytest.fail(f"AdaptiveRateLimiter not implemented: {e}")

    limiter = AdaptiveRateLimiter()

    # Test minimum delay boundary
    limiter.current_delay = 1.5  # Set to minimum
    for i in range(20):  # Many successes
        limiter.on_success()

    # Delay should not go below min_delay (1.5)
    assert limiter.current_delay >= 1.5, (
        f"Delay should not go below minimum, got {limiter.current_delay}"
    )

    # Test maximum delay boundary
    limiter.current_delay = 10.0  # Set to maximum
    for i in range(10):  # Many rate limit errors
        limiter.on_rate_limit_error()

    # Delay should not exceed max_delay (10.0)
    assert limiter.current_delay <= 10.0, (
        f"Delay should not exceed maximum, got {limiter.current_delay}"
    )


def test_rate_limiter_statistics_tracking(integration_test_dir):
    """Test that rate limiter tracks statistics correctly"""
    try:
        from crawler.rate_limiter import AdaptiveRateLimiter
    except ImportError as e:
        pytest.fail(f"AdaptiveRateLimiter not implemented: {e}")

    limiter = AdaptiveRateLimiter()

    # Check initial state
    assert limiter.success_count == 0
    assert limiter.error_count == 0
    assert limiter.current_delay == 5.0

    # Record various events
    for i in range(15):
        limiter.on_success()

    # Success count should reset after 10 consecutive successes
    assert limiter.success_count == 5  # 15 - 10 = 5
    # Delay should have decreased
    assert limiter.current_delay < 5.0

    # Reset for error tests
    limiter.reset()

    for i in range(3):
        limiter.on_rate_limit_error()

    assert limiter.error_count == 3
    assert limiter.success_count == 0
    # Delay should have increased
    assert limiter.current_delay > 5.0
