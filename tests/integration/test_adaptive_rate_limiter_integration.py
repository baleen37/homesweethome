"""Integration tests for AdaptiveRateLimiter with realistic scenarios."""

from unittest.mock import patch


from crawler.rate_limiter import AdaptiveRateLimiter


class TestAdaptiveRateLimiterIntegration:
    """Integration tests for AdaptiveRateLimiter in realistic scenarios."""

    def test_api_call_simulation_with_successes(self):
        """Test rate limiter behavior during successful API calls."""
        limiter = AdaptiveRateLimiter()

        with (
            patch("time.sleep") as mock_sleep,
            patch("time.time", return_value=0),
            patch("crawler.rate_limiter.logger.info"),
        ):  # Mock structlog to avoid interference
            # Simulate 15 successful API calls
            for _ in range(15):
                # Each API call starts with waiting
                limiter.wait()

                # API call succeeds
                limiter.on_success()

            # Check sleep calls
            sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]

            # We should have exactly 15 sleep calls
            assert len(sleep_calls) == 15, f"Expected 15 sleep calls, got {len(sleep_calls)}"

            # First 10 calls should be 2.5 seconds each
            assert sleep_calls[:10] == [2.5] * 10

            # After 10 successes, delay should reduce to 2.25 (10% less)
            assert sleep_calls[10] == 2.25
            assert sleep_calls[11:] == [2.25] * 4  # Adjusted expectation

    def test_api_call_simulation_with_429_errors(self):
        """Test rate limiter behavior with HTTP 429 errors."""
        limiter = AdaptiveRateLimiter()

        with (
            patch("time.sleep") as mock_sleep,
            patch("crawler.rate_limiter.logger.info"),
        ):  # Mock structlog
            with patch("time.time", return_value=0):  # Mock time to be constant
                # Start with some successes
                for _ in range(5):
                    limiter.wait()
                    limiter.on_success()

                # First sleep calls
                assert mock_sleep.call_count == 5
                for call in mock_sleep.call_args_list[:5]:
                    assert call[0][0] == 2.5

                # Now encounter 429 error
                limiter.wait()
                limiter.on_rate_limit_error()

                # Next wait should be doubled (5 seconds)
                limiter.wait()
                # Check the 7th call (index 6) should be 5.0
                assert mock_sleep.call_args_list[6][0][0] == 5.0

                # Another 429 error
                limiter.on_rate_limit_error()
                limiter.wait()
                # Check the 8th call (index 7) should be 10.0
                assert mock_sleep.call_args_list[7][0][0] == 10.0  # Max delay

    def test_mixed_scenario_with_recovery(self):
        """Test realistic mixed scenario with errors and recovery."""
        limiter = AdaptiveRateLimiter()

        with (
            patch("time.sleep") as mock_sleep,
            patch("crawler.rate_limiter.logger.info"),
        ):  # Mock structlog
            with patch("time.time", return_value=0):  # Mock time to be constant
                # Phase 1: Initial successes
                for _ in range(5):
                    limiter.wait()
                    limiter.on_success()

                # Phase 2: Hit rate limit
                limiter.wait()
                limiter.on_rate_limit_error()

                # Phase 3: Retry with exponential backoff
                retry_delay = limiter.get_retry_delay(0)
                assert retry_delay == 2
                # Check we have 6 calls total (5 initial + 1 after rate limit)
                assert mock_sleep.call_count == 6
                # The 6th call (index 5) should still be 2.5 (before rate limit takes effect)
                assert mock_sleep.call_args_list[5][0][0] == 2.5

                # Next wait should be doubled (5 seconds) - 7th call
                limiter.wait()
                assert mock_sleep.call_args_list[6][0][0] == 5.0

                # Phase 4: Recover and continue with successes
                # Need 10 consecutive successes to reduce delay
                for _ in range(10):
                    limiter.wait()
                    limiter.on_success()

                # After recovery and 10 successes, delay should reduce
                # from 5.0 to 4.5 (10% reduction)
                # The 10th success reduced the delay, but the 10th wait()
                # call used the old delay. One more wait() should use 4.5
                limiter.wait()
                assert mock_sleep.call_args_list[-1][0][0] == 4.5

    def test_edge_case_max_delay_reached(self):
        """Test behavior when max delay is reached."""
        limiter = AdaptiveRateLimiter()
        limiter.current_delay = 10.0  # Start at max delay

        with patch("time.sleep") as mock_sleep, patch("time.time", return_value=0):
            # Even with 429 errors, delay shouldn't exceed max
            for _ in range(3):
                limiter.wait()
                limiter.on_rate_limit_error()

            # All calls should be at max delay (10.0)
            for call in mock_sleep.call_args_list:
                assert call[0][0] == 10.0

    def test_edge_case_min_delay_reached(self):
        """Test behavior when min delay is reached."""
        limiter = AdaptiveRateLimiter()
        limiter.current_delay = 1.5  # Start at min delay

        with patch("time.sleep") as mock_sleep, patch("time.time", return_value=0):
            # Even with many successes, delay shouldn't go below min
            for _ in range(20):  # Two cycles of 10 successes
                limiter.wait()
                limiter.on_success()

            # All calls should be at min delay (1.5)
            for call in mock_sleep.call_args_list:
                assert call[0][0] == 1.5

    def test_reset_during_session(self):
        """Test resetting rate limiter during active session."""
        limiter = AdaptiveRateLimiter()

        with (
            patch("time.sleep"),
            patch("time.time", return_value=0),
            patch("crawler.rate_limiter.logger.info"),
        ):  # Mock structlog
            # Build up some state
            for _ in range(15):
                limiter.wait()
                limiter.on_success()

            limiter.on_rate_limit_error()

            # After 15 successes, delay reduced to 2.25, then doubled to 4.5
            assert limiter.current_delay == 4.5  # Doubled from 2.25, not 5.0
            assert limiter._last_wait_time is not None

            # Reset
            limiter.reset()

            # Check everything is back to initial
            assert limiter.current_delay == 2.5
            assert limiter.success_count == 0
            assert limiter.error_count == 0
            assert limiter._last_wait_time is None

    def test_realistic_api_workflow(self):
        """Test a realistic API workflow similar to actual usage."""
        limiter = AdaptiveRateLimiter()

        call_results = []

        with patch("time.sleep") as mock_sleep, patch("time.time", return_value=0):
            # Simulate fetching data with varying success rates
            scenarios = [
                ("batch1", "success", 8),  # 8 successes
                ("batch2", "rate_limit", 1),  # 1 rate limit error
                ("batch3", "success", 12),  # 12 successes
                ("batch4", "error", 2),  # 2 general errors
                ("batch5", "success", 5),  # 5 more successes
            ]

            for batch_name, result_type, count in scenarios:
                for _ in range(count):
                    limiter.wait()

                    if result_type == "success":
                        limiter.on_success()
                        call_results.append("success")
                    elif result_type == "rate_limit":
                        limiter.on_rate_limit_error()
                        call_results.append("429")
                    else:
                        limiter.on_error()
                        call_results.append("error")

            # Verify the delays were appropriate
            delays = [call[0][0] for call in mock_sleep.call_args_list]

            # Should have consistent pattern based on successes/errors
            assert len(delays) == 28  # 8 + 1 + 12 + 2 + 5 = 28 total calls

            # First 8 calls at initial delay
            assert delays[:8] == [2.5] * 8

            # After 8 successes (not yet 10), still 2.5
            assert delays[8] == 2.5  # The 429 error call

            # After 429, delay doubles to 5.0
            assert delays[9] == 5.0  # First call after 429

            # After 10 successes from the 12 in batch3, delay reduces
            # The 10th success in batch3 is at index 18 (8+1+9)
            # So delay should reduce from 5.0 to 4.5 at index 19
            assert delays[18] == 5.0  # Before 10th success
            assert delays[19] == 4.5  # After 10th success (10% reduction)
