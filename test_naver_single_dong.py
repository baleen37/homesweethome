#!/usr/bin/env python3
"""네이버 크롤러 테스트 스크립트 - 단일 동 테스트"""

from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.abspath("."))

import structlog
from src.crawler.crawlers.naver import NaverRealEstateCrawler
from src.crawler.config import CrawlerConfig

# 로깅 설정
structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)


def test_naver_crawler():
    """네이버 크롤러 테스트"""
    config = CrawlerConfig()

    # 커스텀 로거 설정
    logger = structlog.get_logger()

    crawler = NaverRealEstateCrawler(config)

    # 강남구 데이터만 필터링
    filtered_districts = crawler.filter_districts(["강남구"])

    # 첫 번째 동만 테스트
    if filtered_districts and filtered_districts[0].get("dongs"):
        test_dong = filtered_districts[0]["dongs"][0]  # 개포동
        logger.info(
            "테스트 동", dong_name=test_dong.get("dong_name"), cortar_no=test_dong.get("cortarNo")
        )

        # dong_complexes 생성
        dong_complexes = [
            {
                "dong_code": test_dong.get("cortarNo", ""),
                "dong_name": test_dong.get("dong_name", ""),
                "complexes": crawler.fetch_dong_with_retry(test_dong),
            }
        ]

        logger.info("수집된 단지 수", count=len(dong_complexes[0]["complexes"]))

        if dong_complexes[0]["complexes"]:
            # coordinator를 직접 테스트
            from src.crawler.coordinator import CrawlCoordinator

            coordinator = CrawlCoordinator(
                output_dir=Path("output"),
                checkpoint_path=Path("output/checkpoint.json"),
                enable_progress_tracking=True,
            )

            # 래퍼 함수 정의
            def fetch_complex_detail_wrapper(complex_id):
                return crawler.fetch_complex_detail(complex_id)

            def fetch_transaction_history_wrapper(complex_id, pyeong_type, trade_type):
                return crawler.fetch_transaction_history(complex_id, pyeong_type, trade_type)

            # 첫 3개 단지만 테스트
            dong_complexes[0]["complexes"] = dong_complexes[0]["complexes"][:3]

            result = coordinator.crawl_multiple_dongs(
                dong_complexes=dong_complexes,
                fetch_complex_detail=fetch_complex_detail_wrapper,
                fetch_transaction_history=fetch_transaction_history_wrapper,
                resume=False,
            )

            logger.info("처리 결과", **result)

            # CSV 파일 확인
            complexes_file = Path("output/complexes.csv")
            transactions_file = Path("output/transactions.csv")

            if complexes_file.exists():
                with open(complexes_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    print(f"complexes.csv: {len(lines)}행 (헤더 포함)")

            if transactions_file.exists():
                with open(transactions_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    print(f"transactions.csv: {len(lines)}행 (헤더 포함)")
        else:
            logger.error("단지 데이터가 없습니다")
    else:
        logger.error("강남구 데이터가 없습니다")


if __name__ == "__main__":
    test_naver_crawler()
