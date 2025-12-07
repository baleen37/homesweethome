#!/usr/bin/env python3
"""pyeong_types 데이터 구조 디버깅"""

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler
import json


def debug_pyeong_types():
    """pyeong_types 데이터 구조 확인"""
    config = CrawlerConfig.from_env()
    crawler = NaverRealEstateCrawler(config)

    test_complex_id = "112581"

    print(f"단지 ID {test_complex_id}의 pyeong_types 구조 확인...")

    try:
        # 단지 상세 정보 조회
        detail = crawler.fetch_complex_detail(test_complex_id)

        print("\n상세 정보 키:", list(detail.keys()))

        if "pyeong_types" in detail:
            print("\npyeong_types 타입:", type(detail["pyeong_types"]))
            print("pyeong_types 내용:")
            print(json.dumps(detail["pyeong_types"], indent=2, ensure_ascii=False))

        if "pyeong_info" in detail:
            print("\npyeong_info 타입:", type(detail["pyeong_info"]))
            print("pyeong_info 내용:")
            print(json.dumps(detail["pyeong_info"], indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    debug_pyeong_types()
