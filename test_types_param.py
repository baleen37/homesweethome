#!/usr/bin/env python3
"""types 파라미터 테스트"""

import requests
import json


def test_types():
    session = requests.Session()

    # 사이트 접속
    session.get("https://hogangnono.com")

    # 기본 파라미터
    base_params = {
        "map": "google",
        "level": "17",
        "screenWidth": "1200",
        "screenHeight": "924",
        "startX": "127.045",  # 압구정
        "endX": "127.065",
        "startY": "37.520",
        "endY": "37.540",
        "tradeType": "0",
        "priceType": "0",
        "rentType": "0",
    }

    # types 파라미터 테스트
    print("1. types 파라미터 없이")
    params = base_params.copy()
    response = session.get("https://hogangnono.com/api/v2/pois-bounding", params=params)
    if response.status_code == 200:
        data = response.json()
        if "data" in data:
            categories = {}
            for item in data["data"]:
                cat = item.get("category", "unknown")
                if cat not in categories:
                    categories[cat] = 0
                categories[cat] += 1
            print(f"카테고리별 개수: {categories}")

    print("\n2. types=0 (아파트)")
    params = base_params.copy()
    params["types"] = "0"
    response = session.get("https://hogangnono.com/api/v2/pois-bounding", params=params)
    if response.status_code == 200:
        data = response.json()
        if "data" in data:
            print(f"데이터 개수: {len(data['data'])}")
            if data["data"]:
                sample = data["data"][0]
                print(f"샘플: {sample}")

    print("\n3. types=1 (주상복합)")
    params = base_params.copy()
    params["types"] = "1"
    response = session.get("https://hogangnono.com/api/v2/pois-bounding", params=params)
    if response.status_code == 200:
        data = response.json()
        if "data" in data:
            print(f"데이터 개수: {len(data['data'])}")

    print("\n4. types=2 (오피스텔)")
    params = base_params.copy()
    params["types"] = "2"
    response = session.get("https://hogangnono.com/api/v2/pois-bounding", params=params)
    if response.status_code == 200:
        data = response.json()
        if "data" in data:
            print(f"데이터 개수: {len(data['data'])}")

    print("\n5. types=-1 (전체)")
    params = base_params.copy()
    params["types"] = "-1"
    response = session.get("https://hogangnono.com/api/v2/pois-bounding", params=params)
    if response.status_code == 200:
        data = response.json()
        if "data" in data:
            print(f"데이터 개수: {len(data['data'])}")

    # 아파트만 필터링
    print("\n6. category=0으로 필터링")
    params = base_params.copy()
    # types 파라미터 없이 호출
    response = session.get("https://hogangnono.com/api/v2/pois-bounding", params=params)
    if response.status_code == 200:
        data = response.json()
        if "data" in data:
            # category=0인 것만 필터링
            apartments = [item for item in data["data"] if item.get("category") == 0]
            print(f"아파트 개수: {len(apartments)}")
            if apartments:
                print(f"첫 번째 아파트: {apartments[0]}")

                # 아파트 샘플 저장
                sample_data = {
                    "query_params": params,
                    "total_data": data,
                    "apartments_only": apartments[:5],  # 처음 5개 아파트
                }

                with open("apartments_sample.json", "w", encoding="utf-8") as f:
                    json.dump(sample_data, f, indent=2, ensure_ascii=False)
                print("\n아파트 샘플 저장: apartments_sample.json")


if __name__ == "__main__":
    test_types()
