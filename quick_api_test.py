#!/usr/bin/env python
"""빠른 API 테스트

호갱노노 API의 실제 응답을 빠르게 확인합니다.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# 프로젝트 루트에 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.crawler.api.hogangnono_client import HogangnonoAPIClient
from src.crawler.config import CrawlerConfig


def test_api_endpoints():
    """다양한 API 엔드포인트 테스트"""
    print("=" * 80)
    print("호갱노노 API 테스트")
    print("=" * 80)

    config = CrawlerConfig()
    client = HogangnonoAPIClient(config)

    # 테스트 지역: 서울 강남구
    test_bbox = (126.924, 37.514, 127.087, 37.632)

    results = {}

    # 1. 기본 POI 엔드포인트
    print("\n1. /api/v2/pois-bounding (기본 POI)")
    try:
        from src.crawler.api.hogangnono_client import SearchParams

        params = SearchParams(bbox=test_bbox, aptType=1, level=14)

        response = client.get_apartments_bounding(params)
        if response.success and response.data:
            items = (
                response.data if isinstance(response.data, list) else response.data.get("data", [])
            )
            print(f"  ✓ 성공: {len(items)}개 항목")

            # 처음 3개 샘플
            for i, item in enumerate(items[:3]):
                print(f"\n    샘플 {i + 1}:")
                print(f"      ID: {item.get('id', 'N/A')}")
                print(f"      이름: {item.get('name', 'N/A')}")
                print(f"      카테고리: {item.get('category', 'N/A')}")
                print(f"      설명: {str(item.get('description', ''))[:50]}...")
        else:
            print(f"  ✗ 실패: {response.error}")
    except Exception as e:
        print(f"  ✗ 예외: {str(e)}")

    # 2. 검색 API
    print("\n2. /api/search/apartments (아파트 검색)")
    try:
        params = {"keyword": "아파트", "lat": 37.5172, "lng": 127.0473, "radius": 1000}

        response = client._make_request("GET", "/api/search/apartments", params=params)
        if response.success and response.data:
            print(f"  ✓ 성공: {type(response.data).__name__}")
            if isinstance(response.data, dict):
                print(f"  키 목록: {list(response.data.keys())[:5]}")
            elif isinstance(response.data, list):
                print(f"  항목 수: {len(response.data)}")
        else:
            print(f"  ✗ 실패: {response.error}")
    except Exception as e:
        print(f"  ✗ 예외: {str(e)}")

    # 3. 지역별 아파트
    print("\n3. /api/apt/by-district (지역별 아파트)")
    try:
        data = {
            "districtCode": "11680",  # 강남구
            "bounds": [126.924, 37.514, 127.087, 37.632],
        }

        response = client._make_request("POST", "/api/apt/by-district", data=data)
        if response.success and response.data:
            print(f"  ✓ 성공: {type(response.data).__name__name__}")
        else:
            print(f"  ✗ 실패: {response.error}")
    except Exception as e:
        print(f"  ✗ 예외: {str(e)}")

    # 4. 랭킹 순위
    print("\n4. /api/v2/ranks/rolling (랭킹)")
    try:
        params = {"lat": 37.5172, "lng": 127.0473, "limit": 10}

        response = client._make_request("GET", "/api/v2/ranks/rolling", params=params)
        if response.success and response.data:
            print(f"  ✓ 성공: {type(response.data).__name__name__}")
        else:
            print(f"  ✗ 실패: {response.error}")
    except Exception as e:
        print(f"  ✗ 예외: {str(e)}")

    # 5. 다른 파라미터 테스트
    print("\n5. 다른 파라미터 조합 테스트")
    test_params = [
        {"aptType": 0, "level": 14},  # 전체
        {"aptType": 2, "level": 14},  # 오피스텔
        {"aptType": 1, "level": 15},  # 더 상세
        {"aptType": 1, "level": 13},  # 더 넓은 범위
    ]

    for i, params in enumerate(test_params):
        print(f"\n  테스트 5-{i + 1}: {params}")
        try:
            test_search_params = SearchParams(bbox=test_bbox, **params)

            response = client.get_apartments_bounding(test_search_params)
            if response.success and response.data:
                items = (
                    response.data
                    if isinstance(response.data, list)
                    else response.data.get("data", [])
                )
                print(f"    ✓ 성공: {len(items)}개 항목")
            else:
                print(f"    ✗ 실패: {response.error}")
        except Exception as e:
            print(f"    ✗ 예외: {str(e)}")

        time.sleep(1)  # API 요청 간격

    # 6. 통계 출력
    print("\n\nAPI 통계")
    stats = client.get_api_stats()
    print(f"총 요청 수: {stats['total_requests']}")
    print(f"성공률: {stats['success_rate']:.2%}")
    print(f"평균 응답 시간: {stats['average_response_time']:.2f}초")
    print(f"캐시 히트율: {stats.get('cache_hit_rate', 0):.2%}")

    # 7. 샘플 데이터 저장
    output_dir = Path("output/api_test_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = output_dir / f"api_test_results_{timestamp}.json"

    test_results = {
        "test_time": datetime.now().isoformat(),
        "test_area": "서울 강남구",
        "bbox": test_bbox,
        "results": results,
    }

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)

    print(f"\n\n결과 저장: {results_file}")
    print("\n테스트 완료!")


def main():
    """메인 함수"""
    test_api_endpoints()


if __name__ == "__main__":
    main()
