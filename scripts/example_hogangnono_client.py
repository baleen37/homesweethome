#!/usr/bin/env python3
"""호갱노노 API 클라이언트 사용 예시

호갱노노 API 클라이언트의 기본 사용법을 보여줍니다.
"""

import sys
from pathlib import Path

# ruff: noqa: E402
# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from crawler.api import HogangnonoAPIClient, SearchParams
from crawler.config import CrawlerConfig


def main():
    """메인 함수"""
    # 설정 로드
    config = CrawlerConfig.from_env()

    # 클라이언트 생성
    with HogangnonoAPIClient(config) as client:
        print("=== 네이버 부동산 API 클라이언트 예시 ===\n")

        # 1. 단지 목록 조회
        print("1. 단지 목록 조회 (법정동 코드)")
        response = client.get_complex_list(
            cortar_no="1168010600",  # 강남구 삼성동
            bounds="37.513194:127.047996:37.525361:127.061923",
        )
        if response.success:
            print(f"   성공: {response.data}")
        else:
            print(f"   실패: {response.error}")
        print()

        # 2. 아파트 목록 조회 (Bounding box)
        print("2. 아파트 목록 조회 (Bounding box)")
        search_params = SearchParams(
            bbox=(126.9, 37.5, 127.0, 37.6),  # (lng_min, lat_min, lng_max, lat_max)
            level=17,
            tradeType=0,  # 매매
            aptType=-1,  # 전체
        )
        response = client.get_apartments_bounding(search_params)
        if response.success:
            print(f"   성공: {response.data}")
        else:
            print(f"   실패: {response.error}")
        print()

        # 3. 특정 조건으로 아파트 검색
        print("3. 특정 조건으로 아파트 검색 (전세, 30-40평)")
        search_params = SearchParams(
            bbox=(126.945, 37.515, 126.955, 37.525),  # 강남구 특정 영역
            level=17,
            tradeType=1,  # 전세
            areaFrom=99.17,  # 30평 (㎡)
            areaTo=132.23,  # 40평 (㎡)
            aptType=1,  # 아파트
        )
        response = client.get_apartments_bounding(search_params)
        if response.success:
            print(f"   성공: {response.data}")
        else:
            print(f"   실패: {response.error}")
        print()

        # 4. 가격대별 검색
        print("4. 가격대별 검색 (매매 10억-20억)")
        search_params = SearchParams(
            bbox=(127.045, 37.515, 127.055, 37.525),  # (lng_min, lat_min, lng_max, lat_max)
            level=17,
            tradeType=0,  # 매매
            priceFrom=100000,  # 10억 (만원)
            priceTo=200000,  # 20억 (만원)
            aptType=-1,  # 전체
        )
        response = client.get_apartments_bounding(search_params)
        if response.success:
            print(f"   성공: {response.data}")
        else:
            print(f"   실패: {response.error}")
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback

        traceback.print_exc()
