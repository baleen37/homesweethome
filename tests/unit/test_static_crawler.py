from unittest.mock import Mock, patch

from crawler.config import CrawlerConfig
from crawler.crawlers.static import StaticCrawler


def test_static_crawler_fetch_returns_html():
    config = CrawlerConfig()
    crawler = StaticCrawler(config)

    mock_response = Mock()
    mock_response.text = "<html><body>Test</body></html>"
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response) as mock_get:
        html = crawler.fetch("https://example.com")

        mock_get.assert_called_once_with("https://example.com", timeout=30)
        assert html == "<html><body>Test</body></html>"


def test_static_crawler_parse_extracts_data():
    config = CrawlerConfig()
    crawler = StaticCrawler(config)

    html = """
    <html>
        <body>
            <div class="item">
                <span class="title">Item 1</span>
                <span class="price">100</span>
            </div>
            <div class="item">
                <span class="title">Item 2</span>
                <span class="price">200</span>
            </div>
        </body>
    </html>
    """

    results = crawler.parse(html)

    assert len(results) == 2
    assert results[0]["title"] == "Item 1"
    assert results[0]["price"] == "100"
    assert results[1]["title"] == "Item 2"
    assert results[1]["price"] == "200"
