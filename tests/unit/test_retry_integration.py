"""Test integration of retry logic in NaverRealEstateCrawler.

This test ensures that NaverRealEstateCrawler uses the Retryable class
from src/crawler/utils/retry.py instead of custom retry logic.
"""

import unittest.mock as mock

import pytest

from crawler.crawlers.naver import NaverRealEstateCrawler
from crawler.utils.retry import Retryable


@mock.patch('crawler.crawlers.naver.BROWSER_RETRY_CONFIG')
def test_naver_crawler_uses_retryable_class(mock_browser_retry_config):
    """Test that NaverRealEstateCrawler uses Retryable class for retry logic.

    After refactoring, this test verifies that BROWSER_RETRY_CONFIG is used.
    """
    # Create a NaverRealEstateCrawler instance
    config = mock.MagicMock()
    crawler = NaverRealEstateCrawler(config)

    # Mock the page.evaluate method to return a success response
    mock_page = mock.MagicMock()
    mock_page.evaluate.return_value = {"success": True}

    # Mock the retry execute method
    mock_browser_retry_config.execute.return_value = {"success": True}

    # Call the method
    result = crawler._fetch_endpoint_with_retry(
        mock_page,
        "https://example.com/api",
        "test_endpoint",
        max_retries=3
    )

    # Verify the result
    assert result == {"success": True}

    # Verify that BROWSER_RETRY_CONFIG.execute was called
    mock_browser_retry_config.execute.assert_called_once()

    # Get the function passed to execute
    call_args = mock_browser_retry_config.execute.call_args
    assert callable(call_args[0][0])  # First argument should be the fetch_endpoint function