"""Tests for SimpleErrorHandler."""

import pytest
from unittest.mock import Mock, patch
from crawler.utils.simple_error_handler import SimpleErrorHandler


class TestSimpleErrorHandler:
    """Test cases for SimpleErrorHandler."""

    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = SimpleErrorHandler(max_retries=3, retry_delay=0.1)

    def test_mark_apartment_invalid(self):
        """Test marking an apartment as invalid."""
        assert not self.error_handler.is_apartment_invalid("12345")

        self.error_handler.mark_apartment_invalid("12345")

        assert self.error_handler.is_apartment_invalid("12345")
        assert not self.error_handler.is_apartment_invalid("67890")

    def test_should_skip_apartment(self):
        """Test checking if apartment should be skipped."""
        # Initially should not skip
        assert not self.error_handler.should_skip_apartment("12345")

        # After marking as invalid, should skip
        self.error_handler.mark_apartment_invalid("12345")
        assert self.error_handler.should_skip_apartment("12345")

    def test_execute_with_retry_success(self):
        """Test successful execution without retries."""
        mock_func = Mock(return_value="success")

        result = self.error_handler.execute_with_retry(mock_func, apartment_id="12345")

        assert result == "success"
        mock_func.assert_called_once()

    def test_execute_with_retry_404_marks_invalid(self):
        """Test that 404 responses mark apartment as invalid."""
        # Mock response object with 404 status
        mock_response = Mock()
        mock_response.status_code = 404
        mock_func = Mock(return_value=mock_response)

        result = self.error_handler.execute_with_retry(mock_func, apartment_id="12345")

        assert result == mock_response
        assert self.error_handler.is_apartment_invalid("12345")

    def test_execute_with_retry_exception_404_marks_invalid(self):
        """Test that 404 exceptions mark apartment as invalid."""
        mock_func = Mock(side_effect=Exception("404 Not Found"))

        with pytest.raises(Exception, match="404 Not Found"):
            self.error_handler.execute_with_retry(mock_func, apartment_id="12345")

        assert self.error_handler.is_apartment_invalid("12345")

    def test_execute_with_retry_non_404_exception(self):
        """Test that non-404 exceptions don't mark apartment as invalid."""
        mock_func = Mock(side_effect=Exception("Connection timeout"))

        with pytest.raises(Exception, match="Connection timeout"):
            self.error_handler.execute_with_retry(mock_func, apartment_id="12345")

        assert not self.error_handler.is_apartment_invalid("12345")

    @patch("time.sleep")
    def test_execute_with_retry_retries_on_failure(self, mock_sleep):
        """Test that retries happen on failure."""
        # Fail twice, then succeed
        mock_func = Mock(side_effect=[Exception("Error"), Exception("Error"), "success"])

        result = self.error_handler.execute_with_retry(mock_func, apartment_id="12345")

        assert result == "success"
        assert mock_func.call_count == 3
        # Should have slept twice (after first two failures)
        assert mock_sleep.call_count == 2

    @patch("time.sleep")
    def test_execute_with_retry_max_retries_exceeded(self, mock_sleep):
        """Test behavior when max retries are exceeded."""
        mock_func = Mock(side_effect=Exception("Persistent error"))

        with pytest.raises(Exception, match="Persistent error"):
            self.error_handler.execute_with_retry(mock_func, apartment_id="12345")

        # Should have attempted 4 times (1 initial + 3 retries)
        assert mock_func.call_count == 4
        # Should have slept 3 times
        assert mock_sleep.call_count == 3

    def test_response_with_success_attribute(self):
        """Test handling of response objects with success attribute."""
        # Mock response with success=True
        mock_response = Mock()
        mock_response.success = True
        mock_response.data = {"key": "value"}
        mock_func = Mock(return_value=mock_response)

        result = self.error_handler.execute_with_retry(mock_func)

        assert result == mock_response

    def test_response_with_success_false(self):
        """Test handling of response objects with success=False."""
        # Mock response with success=False and 404 status
        mock_response = Mock()
        mock_response.success = False
        mock_response.status_code = 404
        mock_func = Mock(return_value=mock_response)

        result = self.error_handler.execute_with_retry(mock_func, apartment_id="12345")

        assert result == mock_response
        assert self.error_handler.is_apartment_invalid("12345")
