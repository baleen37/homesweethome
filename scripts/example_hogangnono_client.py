#!/usr/bin/env python3
"""호갱노노 API 클라이언트 사용 예시

호갱노노 API 클라이언트의 기본 사용법을 보여줍니다.
"""

import sys
from pathlib import Path

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
        print("=== 호갱노노 API 클라이언트 예시 ===\n")

        # 1. 랭킹 조회
        print("1. 랭킹 조회 (일간)")
        response = client.get_ranking(rank_type="daily", limit=10)
        if response.success:
            print(f"   성공: {response.data}")
        else:
            print(f"   실패: {response.error}")
        print()

        # 2. 최근 조회 목록
        print("2. 최근 조회 목록 (아파트)")
        response = client.get_recent_visits(apt_type="apart", limit=5)
        if response.success:
            print(f"   성공: {response.data}")
        else:
            print(f"   실패: {response.error}")
        print()

        # 3. 지역 정보 조회
        print("3. 지역 정보 조회 (강남구)")
        response = client.get_region_info(lat=37.5172, lng=127.0473, zoom=14)
        if response.success:
            print(f"   성공: {response.data}")
        else:
            print(f"   실패: {response.error}")
        print()

        # 4. POI 정보 조회 (Bounding box)
        print("4. POI 정보 조회 (Bounding box)")
        search_params = SearchParams(
            bbox=(37.5, 126.9, 37.6, 127.0),
            zoom=14,
            limit=20,
        )
        response = client.get_pois_bounding(search_params)
        if response.success:
            print(f"   성공: {response.data}")
        else:
            print(f"   실패: {response.error}")
        print()

        # 5. 아파트 목록 조회 (Bounding box)
        print("5. 아파트 목록 조회 (Bounding box)")
        search_params = SearchParams(
            bbox=(37.5, 126.9, 37.6, 127.0),
            zoom=14,
            filters={"trade_type": "sale", "min_price": 50000},
            limit=20,
        )
        response = client.get_apartments_bounding(
            search_params,
            apt_type="apart",
            trade_type="sale",
        )
        if response.success:
            print(f"   성공: {response.data}")
        else:
            print(f"   실패: {response.error}")
        print()

        # 6. 아파트 검색
        print("6. 아파트 검색")
        response = client.search_apartments(
            keyword="강남구 삼성동 아파트",
            page=1,
            limit=20,
        )
        if response.success:
            print(f"   성공: {response.data}")
        else:
            print(f"   실패: {response.error}")
        print()

        # 7. 아파트 상세 정보
        print("7. 아파트 상세 정보")
        # 실제 ID는 API 응답에서 얻어야 함
        response = client.get_apartment_detail("apt_12345")
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
