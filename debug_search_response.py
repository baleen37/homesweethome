#!/usr/bin/env python3
"""검색 응답 디버깅"""

import requests
import json


def main():
    session = requests.Session()

    # 사이트 접속
    session.get("https://hogangnono.com")

    # 검색 API
    search_url = "https://hogangnono.com/api/v2/searches/new"
    search_params = {"query": "래미안", "x": "127.046953", "y": "37.517236"}

    response = session.get(search_url, params=search_params)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()

        # 전체 응답 저장
        with open("search_response_full.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("전체 응답 저장: search_response_full.json")

        # 응답 구조 확인
        print("\n=== 응답 구조 ===")
        if isinstance(data, dict):
            print(f"최상위 키: {list(data.keys())}")

            if "data" in data:
                print(f"\n['data'] 타입: {type(data['data'])}")
                if isinstance(data["data"], dict):
                    print(f"['data'] 키: {list(data['data'].keys())}")

                    # matched 확인
                    if "matched" in data["data"]:
                        matched = data["data"]["matched"]
                        print(
                            f"\n['matched'] 키: {list(matched.keys()) if isinstance(matched, dict) else type(matched)}"
                        )

                        if isinstance(matched, dict):
                            for key, value in matched.items():
                                print(f"\n{key}:")
                                if isinstance(value, dict):
                                    print(f"  - 키: {list(value.keys())}")
                                    if "list" in value:
                                        items = value["list"]
                                        print(f"  - list 개수: {len(items)}")
                                        if items:
                                            print(
                                                f"  - 첫 번째 아이템 키: {list(items[0].keys()) if isinstance(items[0], dict) else type(items[0])}"
                                            )
                                            if isinstance(items[0], dict):
                                                print(
                                                    f"  - 첫 번째 아이템 이름: {items[0].get('name', 'N/A')}"
                                                )
                                                print(
                                                    f"  - 첫 번째 아이템 ID: {items[0].get('id', 'N/A')}"
                                                )
                                else:
                                    print(f"  - 타입: {type(value)}")

        # 래미안 아파트만 필터링
        print("\n\n=== 래미안 아파트 목록 ===")
        if isinstance(data, dict) and "data" in data:
            data_content = data["data"]
            if isinstance(data_content, dict) and "matched" in data_content:
                matched = data_content["matched"]
                if isinstance(matched, dict) and "apt" in matched:
                    apt_data = matched["apt"]
                    if isinstance(apt_data, dict) and "list" in apt_data:
                        apartments = apt_data["list"]
                        print(f"총 아파트 수: {len(apartments)}")

                        for i, apt in enumerate(apartments[:5]):  # 처음 5개만
                            print(f"\n{i+1}. {apt.get('name', 'N/A')}")
                            print(f"   ID: {apt.get('id', 'N/A')}")
                            print(f"   주소: {apt.get('address', 'N/A')}")
                            print(f"   세대수: {apt.get('household', 'N/A')}")

                            # 래미원 아파트 찾기
                            if "래미안" in apt.get("name", ""):
                                print("   ✓ 래미안 아파트!")
                                # 상세 정보 조회
                                apt_id = apt.get("id")
                                if apt_id:
                                    detail_url = f"https://hogangnono.com/api/v2/apts/{apt_id}"
                                    detail_resp = session.get(detail_url)
                                    if detail_resp.status_code == 200:
                                        detail = detail_resp.json()
                                        with open(
                                            f"raemian_detail_{apt_id}.json", "w", encoding="utf-8"
                                        ) as f:
                                            json.dump(detail, f, indent=2, ensure_ascii=False)
                                        print(f"   상세 정보 저장: raemian_detail_{apt_id}.json")


if __name__ == "__main__":
    main()
