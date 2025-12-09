#!/usr/bin/env python3
"""아파트 검색 API 테스트"""

import requests
import json


def main():
    session = requests.Session()

    # 사이트 접속
    session.get("https://hogangnono.com")

    # 1. 검색 API로 아파트 찾기
    print("1. 검색 API로 '래미안 아파트' 검색...")
    search_url = "https://hogangnono.com/api/v2/searches/new"
    search_params = {"query": "래미안", "x": "127.046953", "y": "37.517236"}

    response = session.get(search_url, params=search_params)
    if response.status_code == 200:
        data = response.json()
        print(f"검색 응답 키: {list(data.keys()) if isinstance(data, dict) else 'array'}")

        if isinstance(data, dict) and "matched" in data:
            matched = data["matched"]
            if "apt" in matched and "list" in matched["apt"]:
                apartments = matched["apt"]["list"]
                print(f"\n찾은 아파트 수: {len(apartments)}")

                if apartments:
                    # 첫 번째 아파트 상세 정보
                    apt = apartments[0]
                    print(f"\n첫 번째 아파트: {apt.get('name')}")
                    print(f"ID: {apt.get('id')}")
                    print(f"주소: {apt.get('address')}")
                    print(f"좌표: ({apt.get('lat')}, {apt.get('lng')})")

                    # 아파트 상세 정보 API 호출
                    apt_id = apt.get("id")
                    if apt_id:
                        print(f"\n2. 아파트 상세 정보 조회 (ID: {apt_id})...")

                        # 다양한 상세 정보 API 엔드포인트 시도
                        detail_endpoints = [
                            f"https://hogangnono.com/api/v2/apts/{apt_id}",
                            f"https://hogangnono.com/api/v2/apt/{apt_id}",
                            f"https://hogangnono.com/api/v2/apartments/{apt_id}",
                            f"https://hogangnono.com/api/apt/{apt_id}",
                        ]

                        for endpoint in detail_endpoints:
                            print(f"\n시도: {endpoint}")
                            detail_response = session.get(endpoint)
                            if detail_response.status_code == 200:
                                detail_data = detail_response.json()
                                print(
                                    f"✓ 성공! 응답 키: {list(detail_data.keys()) if isinstance(detail_data, dict) else 'array'}"
                                )

                                # 상세 정보 저장
                                with open(f"apt_detail_{apt_id}.json", "w", encoding="utf-8") as f:
                                    json.dump(detail_data, f, indent=2, ensure_ascii=False)
                                print(f"상세 정보 저장: apt_detail_{apt_id}.json")
                                break
                            else:
                                print(f"✗ 실패: {detail_response.status_code}")

    # 3. 실거래 내역 API
    print("\n\n3. 실거래 내역 API...")
    if "apt_id" in locals():
        transaction_endpoints = [
            f"https://hogangnono.com/api/v2/apts/{apt_id}/monthly-reports",
            f"https://hogangnono.com/api/v2/apts/{apt_id}/trades",
            f"https://hogangnono.com/api/v2/apts/{apt_id}/transactions",
        ]

        transaction_params = {
            "tradeType": "0",  # 매매
            "areaNo": "0",  # 전체 면적
        }

        for endpoint in transaction_endpoints:
            print(f"\n시도: {endpoint}")
            trans_response = session.get(endpoint, params=transaction_params)
            if trans_response.status_code == 200:
                trans_data = trans_response.json()
                print(
                    f"✓ 성공! 응답 키: {list(trans_data.keys()) if isinstance(trans_data, dict) else 'array'}"
                )

                # 샘플 실거래 내역 저장
                with open(f"apt_transactions_{apt_id}.json", "w", encoding="utf-8") as f:
                    json.dump(trans_data, f, indent=2, ensure_ascii=False)
                print(f"실거래 내역 저장: apt_transactions_{apt_id}.json")
                break
            else:
                print(f"✗ 실패: {trans_response.status_code}")

    # 4. bbox로 주변 아파트 찾기 (실제 아파트 좌표 근처)
    print("\n\n4. 주변 아파트 bbox 조회...")
    if "apt" in locals():
        lat = apt.get("lat", 37.517236)
        lng = apt.get("lng", 127.046953)

        # 작은 bbox 생성 (아파트 근처 500m)
        bbox_params = {
            "map": "google",
            "level": "18",  # 가장 높은 줌
            "startX": lng - 0.005,
            "endX": lng + 0.005,
            "startY": lat - 0.005,
            "endY": lat + 0.005,
            "tradeType": "0",
        }

        # bounding API 시도
        bounding_endpoints = [
            "https://hogangnono.com/api/v2/pois-bounding",
            "https://hogangnono.com/api/apt/bounding",
        ]

        for endpoint in bounding_endpoints:
            print(f"\n시도: {endpoint}")
            bbox_response = session.get(endpoint, params=bbox_params)
            if bbox_response.status_code == 200:
                bbox_data = bbox_response.json()
                print("✓ 성공!")

                if isinstance(bbox_data, dict) and "data" in bbox_data:
                    items = bbox_data["data"]
                    print(f"총 {len(items)}개 데이터")

                    # 카테고리별 분류
                    categories = {}
                    for item in items:
                        cat = item.get("category", "unknown")
                        name = item.get("name", "N/A")
                        if cat not in categories:
                            categories[cat] = []
                        categories[cat].append(name)

                    print("\n카테고리별 목록:")
                    for cat, names in categories.items():
                        print(f"  Category {cat}: {len(names)}개 - {names[:5]}")

                    # 아파트(category=0) 필터링
                    apartments = [item for item in items if item.get("category") == 0]
                    if apartments:
                        print(f"\n✓ 아파트 발견! {len(apartments)}개")
                        with open("nearby_apartments.json", "w", encoding="utf-8") as f:
                            json.dump(apartments, f, indent=2, ensure_ascii=False)
                        print("주변 아파트 저장: nearby_apartments.json")

                        # 첫 번째 아파트 상세 분석
                        print("\n첫 번째 아파트 상세:")
                        for key, value in apartments[0].items():
                            print(f"  {key}: {value}")
                break
            else:
                print(f"✗ 실패: {bbox_response.status_code}")


if __name__ == "__main__":
    main()
