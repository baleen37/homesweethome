"""BaseCrawler 추상 클래스"""

from abc import ABC, abstractmethod
from typing import Any


class BaseCrawler(ABC):
    """모든 크롤러의 추상 베이스 클래스"""

    @abstractmethod
    def get_url(self) -> str:
        """크롤링할 URL 반환"""
        pass

    @abstractmethod
    def fetch(self, url: str) -> str:
        """HTML/JSON 가져오기"""
        pass

    @abstractmethod
    def parse(self, content: str) -> list[dict[str, Any]]:
        """컨텐츠 파싱하여 데이터 추출"""
        pass

    def crawl(self) -> list[dict[str, Any]]:
        """템플릿 메서드: fetch + parse 실행"""
        url = self.get_url()
        content = self.fetch(url)
        return self.parse(content)
