#!/usr/bin/env python3
"""아파트 bounding API 최종 테스트"""

import requests
import json


def main():
    session = requests.Session()

    # 사이트 접속
    session.get("https://hogangnono.com")

    # 1. 먼저 아파트 ID 얻기
    print("1. 강남구 아파트 ID 얻기...")
    search_url = "https://hogangnono.com/api/v2/searches/new"
    search_params = {"query": "강남구 아파트", "x": "127.046953", "y": "37.517236"}

    response = session.get(search_url, params=search_params)
    apartments = []

    if response.status_code == 200:
        data = response.json()
        if "data" in data and "matched" in data["data"]:
            apt_list = data["data"]["matched"].get("apt", {}).get("list", [])
            # 강남구 아파트만 필터링
            apartments = [apt for apt in apt_list if "강남구" in apt.get("address", "")]
            print(f"강남구 아파트 수: {len(apartments)}")

            if apartments:
                # 첫 번째 강남구 아파트 선택
                apt = apartments[0]
                print(f"선택된 아파트: {apt['name']}")
                print(f"ID: {apt['id']}")
                print(f"좌표: ({apt['lat']}, {apt['lng']})")

                # 2. bounding API 테스트
                print("\n2. 아파트 주변 bounding API...")
                lat = apt["lat"]
                lng = apt["lng"]

                # 여러 level로 테스트
                for level in [14, 15, 16, 17, 18]:
                    print(f"\nLevel {level} 테스트...")
                    bbox_params = {
                        "map": "google",
                        "level": str(level),
                        "startX": lng - 0.01,
                        "endX": lng + 0.01,
                        "startY": lat - 0.01,
                        "endY": lat + 0.01,
                        "tradeType": "0",
                    }

                    # 필수 파라미터 추가
                    bbox_params.update(
                        {
                            "screenWidth": "1200",
                            "screenHeight": "924",
                            "priceType": "0",
                            "rentType": "0",
                        }
                    )

                    # bounding API 호출
                    bbox_response = session.get(
                        "https://hogangnono.com/api/v2/pois-bounding", params=bbox_params
                    )

                    if bbox_response.status_code == 200:
                        bbox_data = bbox_response.json()
                        if "data" in bbox_data and isinstance(bbox_data["data"], list):
                            items = bbox_data["data"]

                            # 카테고리별 분류
                            categories = {}
                            for item in items:
                                cat = item.get("category", "unknown")
                                if cat not in categories:
                                    categories[cat] = []
                                categories[cat].append(item.get("name", "N/A"))

                            # 아파트 찾기 (category=0)
                            apartments_found = [item for item in items if item.get("category") == 0]

                            print(f"  총 데이터: {len(items)}개")
                            print(f"  카테고리: {categories}")
                            print(f"  아파트: {len(apartments_found)}개")

                            if apartments_found:
                                print("  ✓ 아파트 발견!")
                                sample_apt = apartments_found[0]
                                print(
                                    f"  샘플: {sample_apt.get('name')} (ID: {sample_apt.get('id')})"
                                )

                                # 샘플 저장
                                sample_data = {
                                    "level": level,
                                    "params": bbox_params,
                                    "categories": categories,
                                    "apartments": apartments_found[:5],
                                    "sample_apartment": sample_apt,
                                }

                                with open(
                                    f"bounding_result_level_{level}.json", "w", encoding="utf-8"
                                ) as f:
                                    json.dump(sample_data, f, indent=2, ensure_ascii=False)
                                print(f"  결과 저장: bounding_result_level_{level}.json")
                                break  # 아파트를 찾으면 루프 종료
                            else:
                                print("  아파트 없음")
                    else:
                        print(f"  실패: {bbox_response.status_code}")

    # 3. 다른 파라미터 조합
    print("\n\n3. 다른 파라미터 조합 테스트...")
    if apartments:
        apt = apartments[0]
        lat = apt["lat"]
        lng = apt["lng"]

        # apt 파라미터 추가
        special_params = {
            "map": "google",
            "level": "17",
            "startX": lng - 0.01,
            "endX": lng + 0.01,
            "startY": lat - 0.01,
            "endY": lat + 0.01,
            "tradeType": "0",
            "apt": apt["id"],  # 특정 아파트 ID
        }

        response = session.get("https://hogangnono.com/api/v2/pois-bounding", params=special_params)
        if response.status_code == 200:
            data = response.json()
            print(f"apt 파라미터 사용 결과: {len(data.get('data', []))}개 데이터")

    # 4. 최종 분석 보고서
    print("\n\n" + "=" * 80)
    print("최종 분석 결과")
    print("=" * 80)
    print("\nAPI 엔드포인트: https://hogangnono.com/api/v2/pois-bounding")
    print("\n주요 파라미터:")
    print("- map: 'google' (필수)")
    print("- level: 줌 레벨 (14-18)")
    print("- startX/endX: 경도 범위")
    print("- startY/endY: 위도 범위")
    print("- tradeType: 거래 유형 (0: 매매)")
    print("- apt: 특정 아파트 ID (선택)")
    print("\n응답 데이터:")
    print("- data: POI 배열")
    print("- 각 POI는 category로 구분 (0: 아파트, 1: 지하철, 10: 마트 등)")
    print("- 아파트는 category=0으로 필터링 가능")
    print("\n아파트 ID 체계:")
    print("- 5자리 영숫자 조합 (예: 5SA38, 20B1c)")
    print("- 검색 API를 통해 먼저 ID를 얻어야 함")


if __name__ == "__main__":
    main()
