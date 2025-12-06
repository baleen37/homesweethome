#!/usr/bin/env python3
"""네이버 크롤러 테스트 스크립트"""

from pathlib import Path
import structlog
from src.crawler.crawlers.naver import NaverCrawler
from src.crawler.config import CrawlerConfig

# 로깅 설정
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

def test_naver_crawler():
    """네이버 크롤러 테스트"""
    config = CrawlerConfig()

    # 강남구만 필터링하여 테스트
    district_filter = ["강남구"]

    crawler = NaverCrawler(config)
    result = crawler.crawl(district_filter=district_filter)

    print(f"크롤링 결과: {len(result)}개 단지 수집")

    # CSV 파일 확인
    complexes_file = Path("output/complexes.csv")
    transactions_file = Path("output/transactions.csv")

    if complexes_file.exists():
        with open(complexes_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"complexes.csv: {len(lines)}행 (헤더 포함)")

    if transactions_file.exists():
        with open(transactions_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"transactions.csv: {len(lines)}행 (헤더 포함)")

if __name__ == "__main__":
    test_naver_crawler()
