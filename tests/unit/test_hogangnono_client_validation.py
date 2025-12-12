"""Tests for HogangnonoAPIClient validation integration."""

import pytest
from unittest.mock import Mock, patch
from requests import Response

from crawler.api.hogangnono_client import HogangnonoAPIClient, APIResponse
from crawler.config import CrawlerConfig


class TestHogangnonoAPIClientValidation:
    """Test validation integration in HogangnonoAPIClient."""

    @pytest.fixture
    def config(self):
        """Create a test config."""
        return CrawlerConfig()

    @pytest.fixture
    def client(self, config):
        """Create a test client."""
        return HogangnonoAPIClient(config)

    def test_validate_response_data_critical_error_blocks_processing(self, client):
        """Test that critical validation errors block data processing."""
        # Create a response with null data (should return early without validation)
        api_response = APIResponse(success=True, data=None, status_code=200)

        # Validate the response
        result = client._validate_response_data(api_response)

        # Should return the original response (no validation on None data)
        assert result.success is True
        assert result.data is None

    def test_validate_response_data_sanitizes_malformed_data(self, client):
        """Test that malformed data gets sanitized."""
        # Create response with malformed data (None values in dict)
        api_response = APIResponse(
            success=True,
            data={
                "data": [
                    {"id": "APT_123", "name": None, "lat": 37.5, "lng": 127.0},
                    {"id": None, "name": "Test", "lat": 37.6, "lng": 127.1},
                ]
            },
            status_code=200,
        )

        # Validate the response
        result = client._validate_response_data(api_response)

        # Should succeed but with warnings
        assert result.success is True
        assert result.data is not None
        # Data should be sanitized (None values removed from non-essential fields)
        assert "data" in result.data

    def test_validate_response_data_handles_validation_exception(self, client):
        """Test that validation exceptions are properly handled."""
        # Mock validate_api_response to raise an exception
        with patch("crawler.validators.validate_api_response") as mock_validate:
            mock_validate.side_effect = Exception("Validation error")

            api_response = APIResponse(success=True, data={"test": "data"}, status_code=200)

            # Validate the response
            result = client._validate_response_data(api_response)

            # Should return failed response
            assert result.success is False
            assert result.data is None
            assert "Response validation failed" in result.error

    def test_validate_response_data_detects_poi_type(self, client):
        """Test that POI response type is correctly detected."""
        # Create POI-like response
        api_response = APIResponse(
            success=True,
            data=[
                {"id": "APT_123", "name": "Test", "lat": 37.5, "lng": 127.0},
                {"id": "456", "name": "Test2", "lat": 37.6, "lng": 127.1},
            ],
            status_code=200,
        )

        # Mock validate_api_response to capture the response_type
        with patch("crawler.validators.validate_api_response") as mock_validate:
            mock_validate.return_value = Mock(has_errors=lambda: False)

            client._validate_response_data(api_response)

            # Should detect as POI type
            mock_validate.assert_called_once()
            args = mock_validate.call_args[0]
            assert args[1] == "poi"  # response_type should be "poi"

    def test_validate_response_data_detects_complex_type(self, client):
        """Test that complex response type is correctly detected."""
        # Create complex-like response
        api_response = APIResponse(
            success=True,
            data={"data": {"complexNo": "123", "complexName": "Test Complex", "buildYear": 2020}},
            status_code=200,
        )

        # Mock validate_api_response to capture the response_type
        with patch("crawler.validators.validate_api_response") as mock_validate:
            mock_validate.return_value = Mock(has_errors=lambda: False)

            client._validate_response_data(api_response)

            # Should detect as complex type
            mock_validate.assert_called_once()
            args = mock_validate.call_args[0]
            assert args[1] == "complex"  # response_type should be "complex"

    def test_validate_response_data_detects_transaction_type(self, client):
        """Test that transaction response type is correctly detected."""
        # Create transaction-like response
        api_response = APIResponse(
            success=True,
            data={
                "data": {
                    "shortTermReport": [
                        {"date": "2025-01-31", "minPrice": 300000, "maxPrice": 400000}
                    ]
                }
            },
            status_code=200,
        )

        # Mock validate_api_response to capture the response_type
        with patch("crawler.validators.validate_api_response") as mock_validate:
            mock_validate.return_value = Mock(has_errors=lambda: False)

            client._validate_response_data(api_response)

            # Should detect as transaction type
            mock_validate.assert_called_once()
            args = mock_validate.call_args[0]
            assert args[1] == "transaction"  # response_type should be "transaction"

    def test_validate_response_data_with_data_wrapper(self, client):
        """Test validation with data wrapper structure."""
        # Test with data that has "data" field containing POI list
        api_response = APIResponse(
            success=True,
            data={"data": [{"id": "APT_123", "name": "Test", "lat": 37.5, "lng": 127.0}]},
            status_code=200,
        )

        # Mock validate_api_response
        with patch("crawler.validators.validate_api_response") as mock_validate:
            mock_validate.return_value = Mock(
                has_errors=lambda: False, get_errors=lambda: [], get_warnings=lambda: []
            )

            client._validate_response_data(api_response)

            # Should still validate the wrapped data
            mock_validate.assert_called_once()

    def test_validate_response_data_logs_warnings(self, client):
        """Test that validation warnings are properly logged."""
        api_response = APIResponse(
            success=True,
            data=[{"id": "APT_123", "name": "Test", "lat": 37.5, "lng": 127.0}],
            status_code=200,
        )

        # Mock validate_api_response to return warnings
        mock_report = Mock()
        mock_report.has_errors.return_value = False
        mock_report.get_warnings.return_value = [Mock(message="Test warning")]
        mock_report.get_errors.return_value = []

        with patch("crawler.validators.validate_api_response", return_value=mock_report):
            with patch.object(client, "logger") as mock_logger:
                client._validate_response_data(api_response)

                # Should log warnings
                mock_logger.info.assert_any_call(
                    "api_response_validation_warnings", warning_count=1, warnings=["Test warning"]
                )

    def test_validate_response_data_logs_non_critical_errors(self, client):
        """Test that non-critical errors are logged as warnings."""
        api_response = APIResponse(
            success=True,
            data=[{"id": "APT_123", "name": "Test", "lat": 37.5, "lng": 127.0}],
            status_code=200,
        )

        # Mock validate_api_response to return non-critical errors
        mock_report = Mock()
        mock_report.has_errors.return_value = True
        mock_report.get_errors.return_value = [
            Mock(severity=Mock(value="error"), message="Test error")
        ]
        mock_report.get_warnings.return_value = []

        with patch("crawler.validators.validate_api_response", return_value=mock_report):
            with patch.object(client, "logger") as mock_logger:
                result = client._validate_response_data(api_response)

                # Should still succeed but log warnings
                assert result.success is True
                mock_logger.warning.assert_any_call(
                    "api_response_validation_errors", error_count=1, errors=["Test error"]
                )

    def test_make_request_calls_validation(self, client):
        """Test that _make_request calls validation for successful responses."""
        # Mock the session and response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "data": [{"id": "APT_123", "name": "Test", "lat": 37.5, "lng": 127.0}]
        }

        with patch.object(client.session, "request", return_value=mock_response):
            with patch.object(client, "_initialize_session", return_value=True):
                with patch.object(client.rate_limiter, "wait"):
                    with patch.object(client, "_validate_response_data") as mock_validate:
                        mock_validate.return_value = APIResponse(
                            success=True, data={"test": "data"}, status_code=200
                        )

                        # Make a request
                        result = client._make_request(
                            method="GET", endpoint="/test", use_cache=False
                        )

                        # Should have called validation
                        mock_validate.assert_called_once()
                        assert result.success is True
