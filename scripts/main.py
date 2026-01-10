from typing import Any

from crawler.base import BaseCrawler


class ExampleCrawler(BaseCrawler):
    """BaseCrawler 사용 예시"""

    def get_url(self) -> str:
        """예제 URL 반환"""
        return "https://example.com"

    def fetch(self, url: str) -> str:
        """HTML/JSON 가져오기"""
        raise NotImplementedError("fetch() must be implemented")

    def parse(self, content: str) -> list[dict[str, Any]]:
        """컨텐츠 파싱하여 데이터 추출"""
        return []

if __name__ == "__main__":
    crawler = ExampleCrawler()
    results = crawler.crawl()
    print(results)
