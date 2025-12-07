#!/usr/bin/env python3
"""동작구 사당동 테스트 크롤링 스크립트"""

import sys
from pathlib import Path

# src 디렉토리를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler


def main():
    print("동작구 사당동 테스트 크롤링 시작...")

    # 출력 파일 설정
    output_file = "output/test_sadang_sample.csv"

    try:
        # CrawlerConfig 생성 (환경 변수에서 설정)
        config = CrawlerConfig.from_env(output_file=output_file)

        # 크롤러 초기화
        crawler = NaverRealEstateCrawler(config)

        # 동작구 필터링
        district_filter = ["동작구"]

        print("크롤링을 시작합니다 (2분 후 자동 중단)...")

        # 타이머 설정 (2분 후 중단)
        def timeout_handler():
            print("\n2분 경과 - 크롤링을 중단합니다.")
            sys.exit(0)

        import threading

        timer = threading.Timer(120, timeout_handler)
        timer.start()

        # 크롤링 실행
        stats = crawler.crawl(district_filter=district_filter)

        timer.cancel()

        print("\n크롤링 결과:")
        print(f"- 처리된 동: {stats.get('dongs_processed', 0)}")
        print(f"- 처리된 단지: {stats.get('total_complexes_processed', 0)}")
        print(f"- 수집된 거래내역: {stats.get('total_transactions_collected', 0)}건")

        # 파일 확인
        if Path("output/transactions.csv").exists():
            size = Path("output/transactions.csv").stat().st_size
            print(f"\ntransactions.csv 파일 크기: {size} bytes")

        if Path("output/complexes.csv").exists():
            size = Path("output/complexes.csv").stat().st_size
            print(f"complexes.csv 파일 크기: {size} bytes")

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
