import requests
from typing import Any

from bs4 import BeautifulSoup

from crawler.crawlers.base import BaseCrawler


class StaticCrawler(BaseCrawler):
    def get_url(self) -> str:
        return "https://example.com"

    def fetch(self, url: str) -> str:
        """requests로 HTML 가져오기"""
        self.logger.info("fetching_url", url=url)
        response = requests.get(url, timeout=self.config.timeout)
        response.raise_for_status()
        return response.text

    def parse(self, html: str) -> list[dict[str, Any]]:
        """BeautifulSoup으로 파싱"""
        soup = BeautifulSoup(html, "lxml")

        items = soup.select(".item")
        results = []

        for item in items:
            title_elem = item.select_one(".title")
            price_elem = item.select_one(".price")

            if title_elem and price_elem:
                results.append(
                    {
                        "title": title_elem.text.strip(),
                        "price": price_elem.text.strip(),
                    }
                )

        self.logger.info("parsed_items", count=len(results))
        return results
