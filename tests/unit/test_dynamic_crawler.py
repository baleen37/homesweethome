from typing import Any
from unittest.mock import Mock, patch

from crawler.config import CrawlerConfig
from crawler.crawlers.dynamic import DynamicCrawler


def test_dynamic_crawler_fetch_uses_playwright() -> None:
    config = CrawlerConfig(headless=True, timeout=30)
    crawler = DynamicCrawler(config)

    mock_page = Mock()
    mock_page.content.return_value = "<html><body>Dynamic Content</body></html>"
    mock_browser = Mock()
    mock_browser.new_page.return_value = mock_page
    mock_playwright = Mock()
    mock_playwright.chromium.launch.return_value = mock_browser

    with patch("crawler.crawlers.dynamic.sync_playwright") as mock_sync:
        mock_sync.return_value.__enter__.return_value = mock_playwright

        html = crawler.fetch("https://example.com")

        mock_playwright.chromium.launch.assert_called_once_with(headless=True)
        mock_page.goto.assert_called_once_with(
            "https://example.com", timeout=30000
        )
        mock_page.wait_for_load_state.assert_called_once_with("networkidle")
        assert html == "<html><body>Dynamic Content</body></html>"


def test_dynamic_crawler_parse_extracts_data() -> None:
    config = CrawlerConfig()
    crawler = DynamicCrawler(config)

    html = """
    <html>
        <body>
            <div class="item">
                <span class="title">Dynamic Item</span>
                <span class="price">500</span>
            </div>
        </body>
    </html>
    """

    results = crawler.parse(html)

    assert len(results) == 1
    assert results[0]["title"] == "Dynamic Item"
    assert results[0]["price"] == "500"
