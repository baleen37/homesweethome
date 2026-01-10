from crawler.base import BaseCrawler

class ExampleCrawler(BaseCrawler):
    def get_url(self) -> str:
        return "https://example.com"

    def fetch(self, url: str) -> str:
        # 구현
        pass

    def parse(self, content: str) -> list[dict]:
        return []

if __name__ == "__main__":
    crawler = ExampleCrawler()
    results = crawler.crawl()
    print(results)
