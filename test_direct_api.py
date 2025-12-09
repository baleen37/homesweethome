#!/usr/bin/env python3
"""직접 API 테스트"""

import requests
import json


def test_api():
    # 세션 생성
    session = requests.Session()

    # 1. 사이트 접속하여 쿠키 획득
    print("1. 사이트 접속 및 쿠키 획득...")
    home_response = session.get("https://hogangnono.com")
    print(f"Home page status: {home_response.status_code}")

    # 2. 아파트 지도 페이지 접속
    print("\n2. 아파트 지도 페이지 접속...")
    map_response = session.get("https://hogangnono.com/apt/강남구")
    print(f"Map page status: {map_response.status_code}")

    # 3. API 직접 호출 테스트
    print("\n3. API 엔드포인트 테스트...")

    # API 엔드포인트 목록
    endpoints = [
        "https://hogangnono.com/api/apt/bounding",
        "https://hogangnono.com/api/v2/pois-bounding",
        "https://hogangnono.com/api/v2/apts/bounding",
    ]

    params = {
        "map": "google",
        "level": "17",
        "screenWidth": "1200",
        "screenHeight": "924",
        "startX": "127.035",
        "endX": "127.055",
        "startY": "37.500",
        "endY": "37.520",
        "tradeType": "0",
        "aptType": "0",
        "priceType": "0",
        "rentType": "0",
    }

    for endpoint in endpoints:
        print(f"\n엔드포인트: {endpoint}")
        try:
            response = session.get(endpoint, params=params)
            print(f"상태 코드: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"응답 키: {list(data.keys()) if isinstance(data, dict) else 'array'}")

                if isinstance(data, dict) and "data" in data:
                    if isinstance(data["data"], list):
                        print(f"데이터 개수: {len(data['data'])}")
                        if data["data"]:
                            # 첫 번째 아이템의 카테고리 확인
                            first_item = data["data"][0]
                            print(
                                f"첫 번째 아이템: {first_item.get('name', 'N/A')} (category: {first_item.get('category', 'N/A')})"
                            )
                            if (
                                "아파트" in first_item.get("name", "")
                                or first_item.get("category") == 0
                            ):
                                print("✓ 아파트 데이터 발견!")
                                # 샘플 저장
                                with open(
                                    "sample_apartment_response.json", "w", encoding="utf-8"
                                ) as f:
                                    json.dump(data, f, indent=2, ensure_ascii=False)
                                break
                    else:
                        print(f"데이터 타입: {type(data['data'])}")
                elif isinstance(data, list) and data:
                    first_item = data[0]
                    print(
                        f"첫 번째 아이템: {first_item.get('name', 'N/A')} (category: {first_item.get('category', 'N/A')})"
                    )
                    if "아파트" in first_item.get("name", "") or first_item.get("category") == 0:
                        print("✓ 아파트 데이터 발견!")
                        with open("sample_apartment_response.json", "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        break
            else:
                print(f"실패: {response.text[:200]}")

        except Exception as e:
            print(f"오류: {e}")

    # 4. 다른 파라미터 조합 테스트
    print("\n\n4. 다른 파라미터 조합 테스트...")

    # 강남구 실제 아파트가 많은 곳
    params_academic = {
        "map": "google",
        "level": "17",
        "screenWidth": "1200",
        "screenHeight": "924",
        "startX": "127.045",  # 압구정역 근처
        "endX": "127.065",
        "startY": "37.520",
        "endY": "37.540",
        "tradeType": "0",
        "aptType": "-1",  # 전체
        "types": "0",  # 아파트만?
    }

    response = session.get("https://hogangnono.com/api/v2/pois-bounding", params=params_academic)
    if response.status_code == 200:
        data = response.json()
        print(
            f"응답 데이터 개수: {len(data['data']) if isinstance(data, dict) and 'data' in data else 0}"
        )

        if isinstance(data, dict) and "data" in data and data["data"]:
            # 카테고리별 분류
            categories = {}
            for item in data["data"][:20]:  # 처음 20개만
                cat = item.get("category", "unknown")
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(item.get("name", "N/A"))

            print("\n카테고리별 분류:")
            for cat, names in categories.items():
                print(f"  Category {cat}: {names[:5]}")  # 각 카테고리 5개만


if __name__ == "__main__":
    test_api()
