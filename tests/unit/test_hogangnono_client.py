"""Unit tests for HogangnonoClient."""

from crawler.api.hogangnono_client import HogangnonoClient
from crawler.config import CrawlerConfig


def test_required_headers_always_present():
    """All API requests must include required headers per API guide."""
    client = HogangnonoClient(CrawlerConfig())
    headers = client._get_api_headers()

    required_headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://hogangnono.com/",
        "Origin": "https://hogangnono.com",
    }

    for key, value in required_headers.items():
        assert key in headers, f"Missing required header: {key}"
        assert headers[key] == value, f"Incorrect {key}: expected {value}, got {headers[key]}"
