#!/usr/bin/env python3
"""호갱노노 아파트 단지 정보 API 상세 분석 스크립트"""

import json
import sys
from crawler.config import CrawlerConfig
from crawler.api.hogangnono_client import HogangnonoAPIClient, SearchParams


def test_api_endpoints():
    """호갱노노 API 엔드포인트 테스트"""
    config = CrawlerConfig.from_env()

    with HogangnonoAPIClient(config) as client:
        print("=" * 80)
        print("호갱노노 API 엔드포인트 테스트")
        print("=" * 80)

        # 1. ranks/rolling API 테스트
        print("\n1. ranks/rolling API (인기 순위)")
        print("-" * 40)
        ranks_response = client._make_request("GET", "/api/v2/ranks/rolling")
        if ranks_response.success:
            data = ranks_response.data
            print(f"✓ 응답 성공 (status: {ranks_response.status_code})")
            print(f"데이터 구조: {list(data.keys()) if data else 'None'}")
            if data and "data" in data:
                rolling_data = data.get("data", {}).get("rolling", [])
                print(f"롤링 데이터 개수: {len(rolling_data)}")
                if rolling_data:
                    print(f"첫 번째 아이템 키: {list(rolling_data[0].keys())}")
                    print(
                        f"샘플: {json.dumps(rolling_data[0], ensure_ascii=False, indent=2)[:500]}..."
                    )
        else:
            print(f"✗ 실패: {ranks_response.error}")

        # 2. pois-bounding API 테스트 (강남구)
        print("\n\n2. pois-bounding API (강남구 아파트 단지)")
        print("-" * 40)

        # 강남구 bbox (대략적인 좌표)
        gangnam_bbox = (126.998, 37.483, 127.087, 37.545)  # (lng_min, lat_min, lng_max, lat_max)

        search_params = SearchParams(
            bbox=gangnam_bbox,
            level=14,  # 낮은 줌 레벨
            tradeType=0,  # 매매
            aptType=1,  # 아파트
        )

        pois_response = client.get_apartments_bounding(search_params)
        if pois_response.success:
            data = pois_response.data
            print(f"✓ 응답 성공 (status: {pois_response.status_code})")
            print(f"데이터 구조: {list(data.keys()) if data else 'None'}")

            if data and isinstance(data, list):
                print(f"단지 데이터 개수: {len(data)}")
                if data:
                    print(f"첫 번째 단지 키: {list(data[0].keys())}")
                    print(f"샘플: {json.dumps(data[0], ensure_ascii=False, indent=2)[:800]}...")
            elif data and "data" in data:
                pois_data = data["data"]
                print(f"단지 데이터 개수: {len(pois_data)}")
                if pois_data:
                    print(f"첫 번째 단지 키: {list(pois_data[0].keys())}")
                    print(
                        f"샘플: {json.dumps(pois_data[0], ensure_ascii=False, indent=2)[:800]}..."
                    )
        else:
            print(f"✗ 실패: {pois_response.error}")

        # 3. 다른 zoom 레벨 테스트
        print("\n\n3. 다른 zoom 레벨별 데이터 차이")
        print("-" * 40)

        for zoom_level in [12, 14, 16, 18]:
            search_params = SearchParams(
                bbox=gangnam_bbox,
                level=zoom_level,
                tradeType=0,
                aptType=1,
            )

            response = client.get_apartments_bounding(search_params)
            if response.success:
                data = response.data
                count = 0
                if isinstance(data, list):
                    count = len(data)
                elif isinstance(data, dict) and "data" in data:
                    count = len(data["data"])

                print(f"Zoom {zoom_level}: {count}개 단지")
            else:
                print(f"Zoom {zoom_level}: 실패 - {response.error}")

        # 4. bbox 파라미터 형식 테스트
        print("\n\n4. bbox 파라미터 형식 테스트")
        print("-" * 40)

        # 서울시 좌표계 (WGS84)
        seoul_bounds = {
            "min_lat": 37.413294,
            "max_lat": 37.715133,
            "min_lng": 126.734086,
            "max_lng": 127.183394,
        }

        print(
            f"서울시 bbox: ({seoul_bounds['min_lng']}, {seoul_bounds['min_lat']}, "
            f"{seoul_bounds['max_lng']}, {seoul_bounds['max_lat']})"
        )

        # 특정 동 (역삼1동) bbox - 더 작은 영역
        yesan_bbox = (127.035, 37.500, 127.055, 37.520)

        search_params = SearchParams(
            bbox=yesan_bbox,
            level=17,  # 높은 줌 레벨
            tradeType=0,
            aptType=1,
        )

        response = client.get_apartments_bounding(search_params)
        if response.success:
            data = response.data
            if isinstance(data, list):
                count = len(data)
                sample = data[0] if data else None
            elif isinstance(data, dict) and "data" in data:
                count = len(data["data"])
                sample = data["data"][0] if data["data"] else None
            else:
                count = 0
                sample = None

            print(f"\n역삼1동 단지 수: {count}")
            if sample:
                print("\n단지 정보 필드:")
                for key, value in sample.items():
                    print(f"  {key}: {type(value).__name__} = {str(value)[:50]}...")
        else:
            print(f"실패: {response.error}")

        # 5. types 파라미터 확인 (아파트 단지용)
        print("\n\n5. aptType 파라미터 값 테스트")
        print("-" * 40)

        for apt_type in [-1, 0, 1, 2]:  # 전체, 아파트, 주상복합, 오피스텔
            search_params = SearchParams(
                bbox=yesan_bbox,
                level=17,
                tradeType=0,
                aptType=apt_type,
            )

            response = client.get_apartments_bounding(search_params)
            if response.success:
                data = response.data
                if isinstance(data, list):
                    count = len(data)
                elif isinstance(data, dict) and "data" in data:
                    count = len(data["data"])
                else:
                    count = 0

                apt_type_name = {-1: "전체", 0: "아파트", 1: "주상복합", 2: "오피스텔"}.get(
                    apt_type, f"알 수 없음({apt_type})"
                )

                print(f"aptType={apt_type} ({apt_type_name}): {count}개")
            else:
                print(f"aptType={apt_type}: 실패 - {response.error}")


def analyze_response_structure():
    """API 응답 구조 상세 분석"""
    config = CrawlerConfig.from_env()

    with HogangnonoAPIClient(config) as client:
        print("\n\n" + "=" * 80)
        print("API 응답 구조 상세 분석")
        print("=" * 80)

        # 강남구 삼성동 bbox
        samseong_bbox = (127.045, 37.505, 127.075, 37.525)

        search_params = SearchParams(
            bbox=samseong_bbox,
            level=17,
            tradeType=0,  # 매매
            aptType=0,  # 아파트
        )

        response = client.get_apartments_bounding(search_params)

        if response.success and response.data:
            data = response.data

            # 데이터 형식 확인
            if isinstance(data, list):
                pois = data
            elif isinstance(data, dict) and "data" in data:
                pois = data["data"]
            else:
                pois = []

            if pois:
                print(f"\n총 {len(pois)}개 단지 발견")
                print("\n첫 번째 단지 상세 정보:")
                print("-" * 40)

                sample = pois[0]
                for key, value in sample.items():
                    value_str = str(value)
                    if len(value_str) > 100:
                        value_str = value_str[:100] + "..."
                    print(f"{key:20} {type(value).__name__:10} = {value_str}")

                # 필드 분석
                print("\n\n주요 필드 분석:")
                print("-" * 40)

                field_analysis = {
                    "id": ("단지 고유 ID", "number"),
                    "name": ("단지명", "string"),
                    "lat": ("위도", "float"),
                    "lng": ("경도", "float"),
                    "address": ("주소", "string"),
                    "buildDate": ("건축년도", "string"),
                    "households": ("세대수", "number"),
                    "floors": ("층수", "number"),
                }

                print(f"{'필드명':15} {'설명':20} {'타입':10} {'예시'}")
                print("-" * 65)

                for field, (desc, ftype) in field_analysis.items():
                    if field in sample:
                        example = str(sample[field])[:30]
                        print(f"{field:15} {desc:20} {ftype:10} {example}")

                # 좌표 정확도 확인
                print("\n\n좌표 정확도 확인:")
                print("-" * 40)
                for i, poi in enumerate(pois[:5]):
                    lat = poi.get("lat")
                    lng = poi.get("lng")
                    name = poi.get("name", "Unknown")
                    print(f"{i+1}. {name}: ({lat}, {lng})")
        else:
            print(f"API 호출 실패: {response.error}")


def test_pagination_and_limits():
    """페이지네이션 및 데이터 제한 확인"""
    print("\n\n" + "=" * 80)
    print("페이지네이션 및 데이터 제한 확인")
    print("=" * 80)

    config = CrawlerConfig.from_env()

    with HogangnonoAPIClient(config) as client:
        # 서울 전체 bbox
        seoul_bbox = (126.734086, 37.413294, 127.183394, 37.715133)

        # 다른 bbox 크기로 테스트
        test_cases = [
            ("동 단위 (역삼1동)", (127.035, 37.500, 127.055, 37.520)),
            ("구 단위 (강남구)", (126.998, 37.483, 127.087, 37.545)),
            ("시 단위 (서울시)", seoul_bbox),
        ]

        for name, bbox in test_cases:
            print(f"\n{name} bbox 테스트:")
            print("-" * 40)
            print(f"bbox: {bbox}")

            search_params = SearchParams(
                bbox=bbox,
                level=14,
                tradeType=0,
                aptType=0,
            )

            response = client.get_apartments_bounding(search_params)

            if response.success and response.data:
                data = response.data

                if isinstance(data, list):
                    count = len(data)
                elif isinstance(data, dict) and "data" in data:
                    count = len(data["data"])
                    # 페이지네이션 정보 확인
                    if "pagination" in data:
                        print(f"페이지네이션 정보: {data['pagination']}")
                    if "total" in data:
                        print(f"전체 데이터 수: {data['total']}")
                else:
                    count = 0

                print(f"반환된 데이터 수: {count}")

                # 제한 확인 (600개 제한)
                if count >= 600:
                    print("⚠️  데이터 제한에 도달했을 수 있음 (600개)")
            else:
                print(f"실패: {response.error}")


def main():
    """메인 실행 함수"""
    print("호갱노노 아파트 단지 정보 API 상세 분석")
    print("=" * 80)

    try:
        # API 엔드포인트 테스트
        test_api_endpoints()

        # 응답 구조 분석
        analyze_response_structure()

        # 페이지네이션 및 제한 확인
        test_pagination_and_limits()

        print("\n\n" + "=" * 80)
        print("분석 완료!")
        print("=" * 80)

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
