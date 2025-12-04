from abc import ABC, abstractmethod
from typing import Any

import structlog

from crawler.config import CrawlerConfig


class BaseCrawler(ABC):
    def __init__(self, config: CrawlerConfig) -> None:
        self.config = config
        self.logger = structlog.get_logger()

    @abstractmethod
    def fetch(self, url: str) -> str:
        """HTML 가져오기"""
        pass

    @abstractmethod
    def parse(self, html: str) -> list[dict[str, Any]]:
        """HTML 파싱 - 사이트별 구현"""
        pass

    @abstractmethod
    def get_url(self) -> str:
        """크롤링할 URL 반환"""
        pass

    def crawl(self) -> list[dict[str, Any]]:
        """크롤링 + 파싱"""
        url = self.get_url()
        html = self.fetch(url)
        return self.parse(html)
