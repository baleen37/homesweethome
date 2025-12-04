from typing import Any

from crawler.config import CrawlerConfig
from crawler.crawlers.base import BaseCrawler


class ConcreteCrawler(BaseCrawler):
    def get_url(self) -> str:
        return "https://example.com"

    def fetch(self, url: str) -> str:
        return "<html><body>Test</body></html>"

    def parse(self, html: str) -> list[dict[str, Any]]:
        return [{"data": "test"}]


def test_base_crawler_has_config() -> None:
    config = CrawlerConfig()
    crawler = ConcreteCrawler(config)
    assert crawler.config == config


def test_base_crawler_has_logger() -> None:
    config = CrawlerConfig()
    crawler = ConcreteCrawler(config)
    assert crawler.logger is not None


def test_base_crawler_crawl_calls_methods() -> None:
    config = CrawlerConfig()
    crawler = ConcreteCrawler(config)

    results = crawler.crawl()

    assert results == [{"data": "test"}]
