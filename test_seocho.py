#!/usr/bin/env python3
"""서초구 크롤링 테스트"""

import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from crawler.crawlers.hogangnono import HogangnonoCrawler
from crawler.config import CrawlerConfig


def main():
    # Load config from environment
    config = CrawlerConfig.from_env()

    # 서초구 좌표
    # 서초 대략적 경계 좌표
    SEOCHO_BOUNDS = (
        37.4664,  # 남쪽 위도
        126.9449,  # 서쪽 경도
        37.5145,  # 북쪽 위도
        127.0435,  # 동쪽 경도
    )

    # Create crawler
    output_dir = Path("output/test_seocho")
    output_dir.mkdir(parents=True, exist_ok=True)

    crawler = HogangnonoCrawler(config=config, output_dir=output_dir, region_bounds=SEOCHO_BOUNDS)

    print("=== 서초구 크롤링 테스트 시작 ===")
    print(f"경계 좌표: {SEOCHO_BOUNDS}")

    # Crawl data
    start_time = time.time()
    complexes, transactions = crawler.crawl_region()
    end_time = time.time()

    print("\n=== 크롤링 완료 ===")
    print(f"소요 시간: {end_time - start_time:.2f}초")
    print(f"수집된 단지 수: {len(complexes)}")
    print(f"수집된 거래 수: {len(transactions)}")

    if complexes:
        print("\n=== 단지 정보 샘플 ===")
        for i, complex in enumerate(complexes[:3]):
            print(
                f"{i+1}. {complex.get('complex_name', 'N/A')} (ID: {complex.get('complex_id', 'N/A')})"
            )

    if transactions:
        print("\n=== 거래 정보 샘플 ===")
        for i, trans in enumerate(transactions[:3]):
            print(
                f"{i+1}. {trans.get('complex_name', 'N/A')} - {trans.get('trade_type_name', 'N/A')}: {trans.get('price', 'N/A')}"
            )

    # Save to CSV
    crawler.save_to_csv(complexes, transactions)
    print(f"\n데이터 저장 완료: {output_dir}")


if __name__ == "__main__":
    main()
