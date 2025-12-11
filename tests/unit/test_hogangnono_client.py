"""Unit tests for HogangnonoAPIClient."""

from crawler.api.hogangnono_client import HogangnonoAPIClient
from crawler.config import CrawlerConfig


def test_required_headers_always_present():
    """All API requests must include required headers per API guide."""
    client = HogangnonoAPIClient(CrawlerConfig())
    headers = client._get_api_headers()

    required_headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://hogangnono.com/",
        "Origin": "https://hogangnono.com",
    }

    for key, value in required_headers.items():
        assert key in headers, f"Missing required header: {key}"
        assert headers[key] == value, f"Incorrect {key}: expected {value}, got {headers[key]}"


def test_session_recovery_on_401():
    """Should automatically reinitialize session on 401/403 errors."""
    import requests_mock
    from unittest.mock import patch, MagicMock

    config = CrawlerConfig()

    # Mock the AdaptiveRateLimiter import
    with patch("crawler.rate_limiter.AdaptiveRateLimiter") as mock_rate_limiter:
        mock_rate_limiter.return_value = MagicMock()
        mock_rate_limiter.return_value.wait = MagicMock()
        mock_rate_limiter.return_value.on_success = MagicMock()
        mock_rate_limiter.return_value.on_error = MagicMock()
        mock_rate_limiter.return_value.on_rate_limit_error = MagicMock()

        client = HogangnonoAPIClient(config)

        with requests_mock.Mocker() as m:
            # First call returns 401
            m.get(
                "https://hogangnono.com/api/v2/regions",
                status_code=401,
                json={"error": "Unauthorized"},
            )

            # Session reinitialization
            m.get("https://hogangnono.com/", status_code=200)

            # Second call after reinit succeeds
            m.get(
                "https://hogangnono.com/api/v2/regions",
                status_code=200,
                json={"data": {"regionList": []}, "status": "success"},
            )

            # Should succeed after auto-recovery
            response = client.get_regions()
            assert response.success
            assert client._session_initialized
