"""BaseCrawler 추상 클래스 테스트"""

from abc import ABC

import pytest

# 이 import는 BaseCrawler가 존재하지 않으므로 실패할 것입니다 (Red Phase)
from crawler.base import BaseCrawler


class TestBaseCrawlerIsAbstract:
    """BaseCrawler가 추상 클래스인지 검증"""

    def test_base_crawler_is_abstract(self):
        """BaseCrawler는 ABC를 상속받는 추상 클래스여야 함"""
        assert issubclass(BaseCrawler, ABC)
        # 추상 클래스는 직접 인스턴스화할 수 없어야 함
        with pytest.raises(TypeError):
            BaseCrawler()  # type: ignore


class TestBaseCrawlerHasAbstractMethods:
    """BaseCrawler가 필수 추상 메서드를 가지고 있는지 검증"""

    def test_has_get_url_abstract_method(self):
        """get_url() 추상 메서드가 존재해야 함"""
        assert hasattr(BaseCrawler, "get_url")
        assert getattr(BaseCrawler.get_url, "__isabstractmethod__", False)

    def test_has_fetch_abstract_method(self):
        """fetch() 추상 메서드가 존재해야 함"""
        assert hasattr(BaseCrawler, "fetch")
        assert getattr(BaseCrawler.fetch, "__isabstractmethod__", False)

    def test_has_parse_abstract_method(self):
        """parse() 추상 메서드가 존재해야 함"""
        assert hasattr(BaseCrawler, "parse")
        assert getattr(BaseCrawler.parse, "__isabstractmethod__", False)


class TestBaseCrawlerTemplateMethod:
    """crawl() 템플릿 메서드 동작 검증"""

    def test_crawl_method_exists(self):
        """crawl() 메서드가 존재해야 함"""
        assert hasattr(BaseCrawler, "crawl")

    def test_crawl_calls_get_url_fetch_parse(self):
        """crawl()은 get_url() -> fetch() -> parse() 순서로 호출해야 함"""

        # 구체적인 구현체로 테스트
        class ConcreteCrawler(BaseCrawler):
            def __init__(self):
                self.call_log = []

            def get_url(self) -> str:
                self.call_log.append("get_url")
                return "http://example.com"

            def fetch(self, url: str) -> str:
                self.call_log.append(("fetch", url))
                return "<html>content</html>"

            def parse(self, content: str) -> list[dict]:
                self.call_log.append(("parse", content))
                return [{"data": "test"}]

        crawler = ConcreteCrawler()
        result = crawler.crawl()

        # 호출 순서와 파라미터 검증
        assert crawler.call_log[0] == "get_url"
        assert crawler.call_log[1] == ("fetch", "http://example.com")
        assert crawler.call_log[2] == ("parse", "<html>content</html>")
        assert result == [{"data": "test"}]
