#!/usr/bin/env python3
"""
호갱노노 아파트 단지 정보 API 테스트
- /api/v2/apts 엔드포인트 상세 분석
"""

import requests
import time


def test_apartments_api():
    print("=" * 80)
    print("호갱노노 아파트 단지 정보 API 테스트")
    print("=" * 80)

    # API 기본 설정
    base_url = "https://hogangnono.com"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        "Referer": "https://hogangnono.com/",
    }

    # 1. 기본 아파트 목록 API 테스트
    print("\n### 1. 기본 아파트 목록 조회")
    test_cases = [
        {"name": "강남구 전체", "url": "/api/v2/apts", "params": {"regionCode": "1168000000"}},
        {"name": "역삼동", "url": "/api/v2/apts", "params": {"regionCode": "1168010300"}},
        {"name": "서초구 전체", "url": "/api/v2/apts", "params": {"regionCode": "1165000000"}},
    ]

    for case in test_cases:
        print(f"\n🔍 {case['name']} 조회")
        try:
            response = requests.get(
                f"{base_url}{case['url']}", headers=headers, params=case["params"], timeout=10
            )

            print(f"  상태코드: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print("  응답 성공!")

                # 응답 구조 분석
                if "data" in data:
                    apt_data = data["data"]

                    if isinstance(apt_data, dict):
                        # 데이터 키 목록 출력
                        print(f"  데이터 키: {list(apt_data.keys())}")

                        # 아파트 목록이 있는지 확인
                        for key in ["apts", "apartments", "list", "items"]:
                            if key in apt_data:
                                items = apt_data[key]
                                if isinstance(items, list) and len(items) > 0:
                                    print(f"  ✅ 아파트 목록 발견 ({key}): {len(items)}개")

                                    # 첫 번째 아파트 정보 출력
                                    first_apt = items[0]
                                    print("  첫 번째 아파트 정보:")
                                    print(f"    - 키: {list(first_apt.keys())}")

                                    # 중요 필드 확인
                                    important_fields = [
                                        "name",
                                        "complexName",
                                        "aptName",
                                        "id",
                                        "complexId",
                                        "code",
                                    ]
                                    for field in important_fields:
                                        if field in first_apt:
                                            print(f"    - {field}: {first_apt[field][:50]}...")
                                    break

                        # 페이지네이션 정보 확인
                        for key in ["page", "paging", "pagination", "total", "count"]:
                            if key in apt_data:
                                print(f"  페이지네이션 ({key}): {apt_data[key]}")

                    elif isinstance(apt_data, list) and len(apt_data) > 0:
                        print(f"  ✅ 직접 리스트 형태: {len(apt_data)}개")
                        print(f"  첫 항목 키: {list(apt_data[0].keys())[:10]}...")

            elif response.status_code == 401:
                print(f"  ❌ 인증 필요: {response.text[:200]}...")
            else:
                print(f"  ❌ 오류: {response.text[:200]}...")

        except Exception as e:
            print(f"  ❌ 요청 실패: {str(e)}")

    # 2. 추가 파라미터 테스트
    print("\n\n### 2. 추가 파라미터 테스트")

    additional_params = [
        {"page": 1, "limit": 20},
        {"page": 2, "limit": 20},
        {"sort": "recent"},
        {"tradeType": "sale"},
        {"propertyType": "apartment"},
        {"minPrice": 100000, "maxPrice": 1000000},
        {"minArea": 33, "maxArea": 84},
    ]

    base_params = {"regionCode": "1168000000"}

    for params in additional_params:
        print(f"\n🔍 파라미터: {params}")
        try:
            response = requests.get(
                f"{base_url}/api/v2/apts",
                headers=headers,
                params={**base_params, **params},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                print("  ✅ 성공")

                # 총 개수 확인
                if "data" in data and isinstance(data["data"], dict):
                    for key in ["total", "count", "totalItems"]:
                        if key in data["data"]:
                            print(f"  - {key}: {data['data'][key]}")
            else:
                print(f"  ❌ 실패: {response.status_code}")

        except Exception as e:
            print(f"  ❌ 오류: {str(e)}")

    # 3. 단지 상세 정보 API 테스트
    print("\n\n### 3. 단지 상세 정보 API 테스트")

    detail_apis = [
        "/api/v2/apts/{complexId}",
        "/api/v2/apartments/{complexId}",
        "/api/v2/complexes/{complexId}",
        "/api/v1/complex/{complexId}",
    ]

    # 임시 단지 ID (실제로는 위 목록 조회에서 얻어야 함)
    test_complex_ids = ["1", "100", "1000", "12345"]

    for api_path in detail_apis:
        print(f"\n🔍 API: {api_path}")
        for complex_id in test_complex_ids[:2]:  # 처음 2개만 테스트
            url = f"{base_url}{api_path.format(complexId=complex_id)}"
            try:
                response = requests.get(url, headers=headers, timeout=5)

                if response.status_code == 200:
                    print(f"  ✅ ID {complex_id}: 성공")
                    data = response.json()
                    if "data" in data:
                        print(f"    데이터 키: {list(data['data'].keys())[:10]}...")
                else:
                    print(f"  ❌ ID {complex_id}: {response.status_code}")

            except Exception:
                print(f"  ❌ ID {complex_id}: 오류")

        time.sleep(0.5)  # 간격 두고 요청

    # 4. 요청 형식 요약
    print("\n\n### 4. 분석 결과 요약")
    print("발견된 API 패턴:")
    print("1. 기본 목록: GET /api/v2/apts?regionCode={코드}")
    print("2. 페이지네이션: page, limit 파라미터")
    print("3. 필터링: tradeType, propertyType, minPrice, maxPrice 등")
    print("4. 정렬: sort 파라미터")

    print("\n응답 구조:")
    print("- {data: {apts: [...], total: N, page: N}, status: 'success'}")

    print("\n지역 코드:")
    print("- 구 전체: 1168000000 (강남구)")
    print("- 동 단위: 1168010300 (역삼동)")

    print("\n### 다음 단계 제안")
    print("1. 실제 아파트 목록을 통해 단지 ID 확인")
    print("2. 단지별 상세 정보 API 완전 분석")
    print("3. 매물 목록과 단지 정보의 연관관계 파악")
    print("4. 좌표 정보 포함 여부 확인")


if __name__ == "__main__":
    test_apartments_api()
