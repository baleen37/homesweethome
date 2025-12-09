#!/usr/bin/env python3
"""호갱노노 아파트 단지 정보 API 상세 분석"""

import json
import sys

sys.path.append("/Users/baleen/dev/homesweethome/src")

from crawler.config import CrawlerConfig
from crawler.api.hogangnono_client import HogangnonoAPIClient, SearchParams


def main():
    print("=" * 80)
    print("호갱노노 아파트 단지 정보 조회 API 상세 분석")
    print("=" * 80)

    config = CrawlerConfig.from_env()

    with HogangnonoAPIClient(config) as client:
        print("\n1. 기본 API 엔드포인트 정보")
        print("-" * 50)
        print("URL: https://hogangnono.com/api/apt/bounding")
        print("Method: GET")

        print("\n2. 강남구 아파트 단지 조회 (level=13, 구 단위)")
        print("-" * 50)

        # 강남구 bbox (대략적인 좌표)
        gangnam_bbox = (126.998, 37.483, 127.087, 37.545)

        search_params = SearchParams(
            bbox=gangnam_bbox,
            level=13,  # 구 단위 줌 레벨
            tradeType=0,  # 매매
            aptType=0,  # 아파트
        )

        # bbox 정보 출력
        print(
            f"bbox (lng_min, lat_min, lng_max, lat_max): {search_params.startX}, {search_params.startY}, {search_params.endX}, {search_params.endY}"
        )
        print(f"level: {search_params.level}")
        print(f"tradeType: {search_params.tradeType} (0: 매매)")
        print(f"aptType: {search_params.aptType} (0: 아파트)")

        response = client.get_apartments_bounding(search_params)

        if response.success:
            data = response.data
            print(f"\n✓ 응답 성공 (status: {response.status_code})")

            # 데이터 구조 분석
            if isinstance(data, list):
                apartments = data
                print("데이터 형식: 직접 배열")
                print(f"단지 수: {len(apartments)}")
            elif isinstance(data, dict):
                print("데이터 형식: 객체")
                if "data" in data:
                    apartments = data["data"]
                    print(f"- data 필드: {len(apartments)}개 단지")
                else:
                    apartments = []
                    print(f"- 응답 키: {list(data.keys())}")
            else:
                apartments = []
                print("알 수 없는 데이터 형식")

            # 첫 번째 단지 상세 분석
            if apartments:
                print("\n[첫 번째 단지 상세 정보]")
                print("-" * 50)
                sample = apartments[0]

                # 필드 분석
                id_fields = []
                coord_fields = []
                price_fields = []
                area_fields = []
                date_fields = []
                other_fields = []

                for key, value in sample.items():
                    if any(word in key.lower() for word in ["id", "hash", "code"]):
                        id_fields.append((key, type(value).__name__, value))
                    elif any(word in key.lower() for word in ["lat", "lng", "x", "y", "coord"]):
                        coord_fields.append((key, type(value).__name__, value))
                    elif any(word in key.lower() for word in ["price", "가격", "매매"]):
                        price_fields.append((key, type(value).__name__, value))
                    elif any(word in key.lower() for word in ["area", "면적", "size", "m²"]):
                        area_fields.append((key, type(value).__name__, value))
                    elif any(word in key.lower() for word in ["date", "년", "월", "day"]):
                        date_fields.append((key, type(value).__name__, value))
                    else:
                        other_fields.append((key, type(value).__name__, str(value)[:50]))

                # 필드별 출력
                if id_fields:
                    print("\n【ID 필드】")
                    for field, ftype, value in id_fields:
                        print(f"  {field} ({ftype}): {value}")

                if coord_fields:
                    print("\n【좌표 필드】")
                    for field, ftype, value in coord_fields:
                        print(f"  {field} ({ftype}): {value}")

                if price_fields:
                    print("\n【가격 필드】")
                    for field, ftype, value in price_fields:
                        print(f"  {field} ({ftype}): {value}")

                if area_fields:
                    print("\n【면적 필드】")
                    for field, ftype, value in area_fields:
                        print(f"  {field} ({ftype}): {value}")

                if date_fields:
                    print("\n【날짜 필드】")
                    for field, ftype, value in date_fields:
                        print(f"  {field} ({ftype}): {value}")

                if other_fields:
                    print("\n【기타 필드】")
                    for field, ftype, value in other_fields[:10]:  # 10개만
                        print(f"  {field} ({ftype}): {value}")
                    if len(other_fields) > 10:
                        print(f"  ... 외 {len(other_fields) - 10}개 필드")

        print("\n\n3. 서초구 아파트 단지 조회 (level=13, 구 단위)")
        print("-" * 50)

        # 서초구 bbox
        seocho_bbox = (126.974, 37.465, 127.030, 37.515)

        search_params = SearchParams(
            bbox=seocho_bbox,
            level=13,
            tradeType=0,
            aptType=0,
        )

        response = client.get_apartments_bounding(search_params)

        if response.success:
            data = response.data
            if isinstance(data, list):
                apartments = data
            elif isinstance(data, dict) and "data" in data:
                apartments = data["data"]
            else:
                apartments = []

            print(f"서초구 단지 수: {len(apartments)}")

        print("\n\n4. 줌 레벨별 데이터 차이 분석")
        print("-" * 50)

        # 강남구 역삼동 작은 영역
        yesan_bbox = (127.035, 37.500, 127.055, 37.520)

        for level in [13, 15, 17, 18]:
            search_params = SearchParams(
                bbox=yesan_bbox,
                level=level,
                tradeType=0,
                aptType=0,
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

                print(f"Level {level}: {count}개 단지")

        print("\n\n5. 필터링 옵션 테스트")
        print("-" * 50)

        # 가격 필터 (10억 ~ 30억)
        search_params = SearchParams(
            bbox=gangnam_bbox,
            level=13,
            tradeType=0,
            aptType=0,
            priceFrom=100000,  # 10억 (만원 단위)
            priceTo=300000,  # 30억
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
            print(f"가격 필터 (10억~30억): {count}개 단지")

        # 면적 필터 (33㎡ ~ 85㎡)
        search_params = SearchParams(
            bbox=gangnam_bbox,
            level=13,
            tradeType=0,
            aptType=0,
            areaFrom=33,
            areaTo=85,
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
            print(f"면적 필터 (33㎡~85㎡): {count}개 단지")

        print("\n\n6. 데이터 개수 제한 확인")
        print("-" * 50)

        # 서울 전체 bbox (큰 영역)
        seoul_bbox = (126.734, 37.413, 127.183, 37.715)

        search_params = SearchParams(
            bbox=seoul_bbox,
            level=13,
            tradeType=0,
            aptType=0,
        )

        response = client.get_apartments_bounding(search_params)
        if response.success:
            data = response.data
            if isinstance(data, list):
                count = len(data)
            elif isinstance(data, dict) and "data" in data:
                count = len(data["data"])
                # 추가 메타데이터 확인
                if "pagination" in data:
                    print(f"페이지네이션 정보: {data['pagination']}")
                if "total" in data:
                    print(f"전체 데이터 수: {data['total']}")
            else:
                count = 0

            print(f"서울 전체 단지 수: {count}")
            if count >= 600:
                print("⚠️ 데이터 제한에 도달했을 수 있음 (API는 보통 600개로 제한)")

        print("\n\n7. 응답 데이터 전체 구조 샘플 저장")
        print("-" * 50)

        # 샘플 데이터 저장
        if "apartments" in locals() and apartments:
            sample_data = {
                "query_info": {
                    "endpoint": "/api/apt/bounding",
                    "bbox": gangnam_bbox,
                    "level": 13,
                    "tradeType": 0,
                    "aptType": 0,
                },
                "response_structure": {
                    "total_count": len(apartments),
                    "sample_apartment": apartments[0] if apartments else None,
                },
            }

            with open(
                "/Users/baleen/dev/homesweethome/hogangnono_apt_api_sample.json",
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(sample_data, f, indent=2, ensure_ascii=False)

            print("샘플 데이터 저장: hogangnono_apt_api_sample.json")

        print("\n" + "=" * 80)
        print("분석 완료!")
        print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
