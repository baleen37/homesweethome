"""Tests for HogangnonoCrawler implementation."""

from unittest.mock import Mock, patch

import pytest

from crawler.config import CrawlerConfig
from crawler.crawlers.hogangnono import HogangnonoCrawler


@pytest.fixture
def config():
    """Create test config for HogangnonoCrawler."""
    return CrawlerConfig(
        site="hogangnono",
        timeout=30,
        headless=True,
        hogangnono={
            "rate_limit_delay": 1.0,
            "page_size": 20,
        },
    )


@pytest.fixture
def crawler(config):
    """Create HogangnonoCrawler instance."""
    return HogangnonoCrawler(config)


class TestHogangnonoCrawler:
    """Test cases for HogangnonoCrawler."""

    def test_init(self, crawler):
        """Test crawler initialization."""
        assert crawler is not None
        assert crawler.config.site == "hogangnono"
        assert hasattr(crawler, "browser_manager")
        assert hasattr(crawler, "logger")
        assert crawler.base_url == "https://hogangnono.com"

    def test_get_url(self, crawler):
        """Test get_url method returns correct URL."""
        url = crawler.get_url()
        assert url == "https://hogangnono.com"

    @patch("crawler.crawlers.hogangnono.BrowserManager")
    def test_fetch_with_browser(self, mock_browser_manager_class, crawler):
        """Test fetch method uses BrowserManager correctly."""
        # Mock browser manager and page
        mock_browser_manager = Mock()
        mock_page = Mock()

        # Create a proper context manager mock
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_page)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_browser_manager.managed_browser.return_value = mock_context_manager
        mock_browser_manager_class.return_value = mock_browser_manager

        # Recreate crawler with mocked BrowserManager
        crawler = HogangnonoCrawler(crawler.config)

        # Mock page.goto and content
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None
        mock_page.content.return_value = "<html>test</html>"

        # Test fetch
        result = crawler.fetch("https://hogangnono.com")

        assert result == "<html>test</html>"
        mock_page.goto.assert_called_once_with("https://hogangnono.com")
        mock_page.wait_for_load_state.assert_called_once_with("networkidle")
        mock_page.content.assert_called_once()

    def test_parse_empty_html(self, crawler):
        """Test parse method with empty HTML."""
        result = crawler.parse("")
        assert result == []

    def test_parse_with_mock_html(self, crawler):
        """Test parse method with mock HTML structure."""
        mock_html = """
        <html>
            <body>
                <div data-testid="real-estate-item">
                    <div class="price">12억 5,000만</div>
                    <div class="area">84.85㎡</div>
                    <div class="floor">3/15층</div>
                    <div class="date">24.12.01</div>
                    <div class="complex-name">테스트단지</div>
                    <div class="address">서울시 강남구 테스트동</div>
                </div>
                <div data-testid="real-estate-item">
                    <div class="price">8억 3,000만</div>
                    <div class="area">75.32㎡</div>
                    <div class="floor">5/20층</div>
                    <div class="date">24.11.28</div>
                    <div class="complex-name">테스트단지2</div>
                    <div class="address">서울시 서초구 테스트동</div>
                </div>
            </body>
        </html>
        """

        result = crawler.parse(mock_html)

        assert len(result) == 2
        assert result[0]["price"] == "12억 5,000만"
        assert result[0]["area"] == "84.85㎡"
        assert result[0]["floor"] == "3/15층"
        assert result[0]["date"] == "24.12.01"
        assert result[0]["complex_name"] == "테스트단지"
        assert result[0]["address"] == "서울시 강남구 테스트동"

    def test_parse_with_alternative_selectors(self, crawler):
        """Test parse method with alternative CSS selectors."""
        html_with_property_items = """
        <html>
            <body>
                <div class="property-item">
                    <div class="price">5억</div>
                    <div class="area">59.5㎡</div>
                    <div class="complex-name">오피스텔</div>
                </div>
                <li class="search-item">
                    <div class="price">3억</div>
                    <div class="area">33.2㎡</div>
                    <div class="complex-name">원룸</div>
                </li>
            </body>
        </html>
        """

        with patch("crawler.crawlers.hogangnono.BeautifulSoup") as mock_bs:
            mock_soup = Mock()
            mock_bs.return_value = mock_soup

            # Mock items with get_text method
            mock_item1 = Mock()
            mock_item1.find.side_effect = [
                Mock(get_text=Mock(return_value="5억")),  # price
                Mock(get_text=Mock(return_value="59.5㎡")),  # area
                Mock(get_text=Mock(return_value="")),  # floor
                Mock(get_text=Mock(return_value="")),  # date
                Mock(get_text=Mock(return_value="오피스텔")),  # complex_name
                Mock(get_text=Mock(return_value="")),  # address
            ]

            # First find_all returns empty, second attempt returns items
            mock_soup.find_all.side_effect = [
                [],  # No data-testid items
                [mock_item1],  # property-item found
            ]

            result = crawler.parse(html_with_property_items)

            assert isinstance(result, list)
            mock_bs.assert_called_once_with(html_with_property_items, "html.parser")

    def test_extract_listing_data(self, crawler):
        """Test _extract_listing_data method."""
        # Create mock item element
        mock_item = Mock()

        # Mock find method for each class
        mock_item.find.side_effect = [
            Mock(get_text=Mock(return_value="10억 5,000만")),  # price
            Mock(get_text=Mock(return_value="84.95㎡")),  # area
            Mock(get_text=Mock(return_value="5/15층")),  # floor
            Mock(get_text=Mock(return_value="24.12.01")),  # date
            Mock(get_text=Mock(return_value="테스트아파트")),  # complex_name
            Mock(get_text=Mock(return_value="서울시 강남구")),  # address
        ]

        result = crawler._extract_listing_data(mock_item)

        assert result is not None
        assert result["price"] == "10억 5,000만"
        assert result["area"] == "84.95㎡"
        assert result["floor"] == "5/15층"
        assert result["date"] == "24.12.01"
        assert result["complex_name"] == "테스트아파트"
        assert result["address"] == "서울시 강남구"

    def test_extract_listing_data_no_price_or_name(self, crawler):
        """Test _extract_listing_data returns None when no price or name."""
        mock_item = Mock()
        mock_item.find.side_effect = [
            Mock(get_text=Mock(return_value="")),  # empty price
            Mock(get_text=Mock(return_value="84.95㎡")),
            Mock(get_text=Mock(return_value="5/15층")),
            Mock(get_text=Mock(return_value="24.12.01")),
            Mock(get_text=Mock(return_value="")),  # empty complex_name
            Mock(get_text=Mock(return_value="서울시 강남구")),
        ]

        result = crawler._extract_listing_data(mock_item)

        assert result is None

    @patch("crawler.crawlers.hogangnono.BrowserManager")
    def test_crawl_region(self, mock_browser_manager_class, crawler):
        """Test crawl_region method."""
        # Mock browser manager and page
        mock_browser_manager = Mock()
        mock_page = Mock()

        # Create a proper context manager mock
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_page)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_browser_manager.managed_browser.return_value = mock_context_manager
        mock_browser_manager_class.return_value = mock_browser_manager

        # Recreate crawler with mocked BrowserManager
        crawler = HogangnonoCrawler(crawler.config)

        # Mock page operations
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None
        mock_page.locator.return_value.count.return_value = 1  # search input found
        mock_page.locator.return_value.fill = Mock()
        mock_page.keyboard.press = Mock()
        mock_page.wait_for_timeout.return_value = None
        mock_page.content.return_value = "<html>test</html>"

        # Mock parse result
        with patch.object(crawler, "parse") as mock_parse:
            mock_parse.return_value = [
                {
                    "price": "10억",
                    "complex_name": "테스트",
                    "area": "84㎡",
                    "floor": "5/15층",
                    "date": "24.12.01",
                    "address": "서울시 강남구",
                }
            ]

            result = crawler.crawl_region("강남구", "개포동")

            assert len(result) == 1
            assert result[0]["price"] == "10억"
            mock_page.goto.assert_called_once_with("https://hogangnono.com")
            mock_page.locator.return_value.fill.assert_called_once_with("강남구 개포동")
            mock_page.keyboard.press.assert_called_once_with("Enter")
            mock_parse.assert_called_once_with("<html>test</html>")

    @patch("crawler.crawlers.hogangnono.BrowserManager")
    def test_crawl_with_pagination(self, mock_browser_manager_class, crawler):
        """Test crawl_with_pagination method."""
        # Mock browser manager and page
        mock_browser_manager = Mock()
        mock_page = Mock()

        # Create a proper context manager mock
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_page)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_browser_manager.managed_browser.return_value = mock_context_manager
        mock_browser_manager_class.return_value = mock_browser_manager

        # Recreate crawler with mocked BrowserManager
        crawler = HogangnonoCrawler(crawler.config)

        # Mock page operations
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None
        mock_page.locator.return_value.count.return_value = 1  # search input found
        mock_page.locator.return_value.fill = Mock()
        mock_page.keyboard.press = Mock()
        mock_page.wait_for_timeout.return_value = None

        # Mock page.content to return different results for each call
        mock_page.content.side_effect = [
            "<html>page1</html>",  # First page
            "<html>page2</html>",  # After more button click
            "<html>page2</html>",  # No new items
        ]

        # Mock parse results
        with patch.object(crawler, "parse") as mock_parse:
            mock_parse.side_effect = [
                [{"complex_name": "아파트1", "area": "84㎡", "price": "10억"}],  # First page
                [{"complex_name": "아파트2", "area": "75㎡", "price": "8억"}],  # Second page
                [{"complex_name": "아파트2", "area": "75㎡", "price": "8억"}],  # No new items
            ]

            # Mock more button (visible on first iteration, hidden on second)
            mock_more_button = Mock()
            mock_more_button.count.return_value = 1
            mock_more_button.is_visible.return_value = True
            mock_more_button.click = Mock()

            mock_page.locator.side_effect = [
                Mock(count=Mock(return_value=1), fill=Mock()),  # search input
                mock_more_button,  # more button on first iteration
                Mock(count=Mock(return_value=0)),  # no more button
            ]

            result = crawler.crawl_with_pagination("강남구", max_pages=3)

            assert len(result) == 2  # Both unique apartments
            assert result[0]["complex_name"] == "아파트1"
            assert result[1]["complex_name"] == "아파트2"

    @patch("crawler.crawlers.hogangnono.BrowserManager")
    def test_crawl_integration(self, mock_browser_manager_class, crawler):
        """Test crawl method integrates fetch and parse correctly."""
        # Mock browser manager and page
        mock_browser_manager = Mock()
        mock_page = Mock()

        # Create a proper context manager mock
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_page)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_browser_manager.managed_browser.return_value = mock_context_manager
        mock_browser_manager_class.return_value = mock_browser_manager

        # Recreate crawler with mocked BrowserManager
        crawler = HogangnonoCrawler(crawler.config)

        # Mock page operations
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None
        mock_page.content.return_value = "<html>test</html>"

        # Mock parse result
        with patch.object(crawler, "parse") as mock_parse:
            mock_parse.return_value = [
                {
                    "price": "12억",
                    "area": "84㎡",
                    "floor": "3/15층",
                    "date": "24.12.01",
                    "complex_name": "테스트",
                    "address": "서울시 강남구",
                }
            ]

            result = crawler.crawl()

            assert len(result) == 1
            assert result[0]["price"] == "12억"
            mock_parse.assert_called_once_with("<html>test</html>")

    def test_crawl_with_exception_handling(self, crawler):
        """Test crawl method handles exceptions properly."""
        with patch.object(crawler, "fetch", side_effect=Exception("Network error")):
            with pytest.raises(Exception, match="Network error"):
                crawler.crawl()

    @patch("crawler.crawlers.hogangnono.BrowserManager")
    def test_browser_manager_integration(self, mock_browser_manager_class, config):
        """Test BrowserManager is properly integrated."""
        mock_browser_manager = Mock()
        mock_browser_manager_class.return_value = mock_browser_manager

        # Create crawler
        crawler = HogangnonoCrawler(config)

        # Verify BrowserManager was initialized with config
        mock_browser_manager_class.assert_called_once_with(config)
        assert crawler.browser_manager == mock_browser_manager
