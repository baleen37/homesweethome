from typing import Any

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from crawler.crawlers.base import BaseCrawler


class DynamicCrawler(BaseCrawler):
    def get_url(self) -> str:
        return "https://example.com"

    def fetch(self, url: str) -> str:
        """Playwright로 JavaScript 실행 후 HTML 가져오기"""
        self.logger.info("fetching_dynamic_url", url=url)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.config.headless)
            page = browser.new_page()
            page.goto(url, timeout=self.config.timeout * 1000)
            page.wait_for_load_state("networkidle")
            html = page.content()
            browser.close()
            return html

    def parse(self, html: str) -> list[dict[str, Any]]:
        """BeautifulSoup으로 파싱"""
        soup = BeautifulSoup(html, "lxml")

        items = soup.select(".item")
        results = []

        for item in items:
            title_elem = item.select_one(".title")
            price_elem = item.select_one(".price")

            if title_elem and price_elem:
                results.append({
                    "title": title_elem.text.strip(),
                    "price": price_elem.text.strip(),
                })

        self.logger.info("parsed_items", count=len(results))
        return results
