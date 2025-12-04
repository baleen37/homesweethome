from crawler.config import CrawlerConfig
from crawler.crawlers.base import BaseCrawler


class TestCrawler(BaseCrawler):
    def get_url(self) -> str:
        return "https://example.com"

    def fetch(self, url: str) -> str:
        return "<html><body>Test</body></html>"

    def parse(self, html: str) -> list[dict]:
        return [{"data": "test"}]


def test_base_crawler_has_config():
    config = CrawlerConfig()
    crawler = TestCrawler(config)
    assert crawler.config == config


def test_base_crawler_has_logger():
    config = CrawlerConfig()
    crawler = TestCrawler(config)
    assert crawler.logger is not None


def test_base_crawler_crawl_calls_methods():
    config = CrawlerConfig()
    crawler = TestCrawler(config)

    results = crawler.crawl()

    assert results == [{"data": "test"}]
