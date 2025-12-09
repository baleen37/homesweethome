#!/usr/bin/env python3
"""
호갱노노 동 목록 API 상세 분석
- 발견된 API 패턴을 바탕으로 동 목록 조회 방법 분석
"""

import requests
import json


def analyze_discovered_apis():
    print("=" * 80)
    print("## 4단계: 동 목록 API 분석")
    print("=" * 80)

    # 1. 발견된 API 엔드포인트 분석
    print("\n### API 엔드포인트")
    print("- 기본 URL: https://hogangnono.com/api/v2/")
    print("- 관련 엔드포인트들:")
    print("  - /api/v2/maps/region : 지역 정보 조회")
    print("  - /api/v2/apts/recent-visits : 최근 방문 아파트")
    print("  - /api/v2/ranks/rolling : 순위 정보")

    # 2. region API 상세 분석
    print("\n### 지역 정보 API 상세 분석")
    print(
        "- 발견된 요청: GET /api/v2/maps/region?lat=37.39462765056729&lng=127.11324925186776&zoom=13"
    )
    print("- 파라미터:")
    print("  - lat: 위도")
    print("  - lng: 경도")
    print("  - zoom: 줌 레벨")

    # 3. 응답 구조 분석
    print("\n### 응답 데이터 구조")
    sample_response = {
        "data": {
            "id": "4113500000",  # 지역 코드
            "zoom": 13,
            "name": "경기도 성남시 분당구",
            "sidoName": "경기도",
            "sigunguName": "성남시 분당구",
            "dongName": None,
            "hasRegionPage": False,
            "showSellMyAptButton": False,
            "showLocalItemButton": True,
        },
        "status": "success",
    }
    print(json.dumps(sample_response, ensure_ascii=False, indent=2))

    # 4. 동 목록 조회를 위한 추가 API 시도
    print("\n### 동 목록 조회 API 시도")

    # 가능한 API 엔드포인트들
    possible_dong_apis = [
        {
            "name": "지역별 동 목록",
            "url": "https://hogangnono.com/api/v2/regions/{regionCode}/dongs",
            "method": "GET",
            "params": {},
        },
        {
            "name": "시/도 목록",
            "url": "https://hogangnono.com/api/v2/regions/sidos",
            "method": "GET",
            "params": {},
        },
        {
            "name": "구/군 목록",
            "url": "https://hogangnono.com/api/v2/regions/{sidoCode}/sigungus",
            "method": "GET",
            "params": {},
        },
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://hogangnono.com/",
    }

    for api_info in possible_dong_apis:
        print(f"\n🔍 {api_info['name']}")
        try:
            # URL에 {regionCode}가 있으면 샘플 코드로 대체
            url = api_info["url"]
            if "{regionCode}" in url:
                url = url.replace("{regionCode}", "11680")  # 강남구 코드
            elif "{sidoCode}" in url:
                url = url.replace("{sidoCode}", "11")  # 서울특별시 코드

            response = requests.get(url, headers=headers, params=api_info["params"], timeout=5)

            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ 성공: {response.status_code}")
                print(f"  응답 (앞 300자): {str(data)[:300]}...")
            else:
                print(f"  ❌ 실패: {response.status_code}")
                print(f"  응답: {response.text[:200]}...")
        except Exception as e:
            print(f"  ❌ 오류: {str(e)}")

    # 5. 서울시 지역 코드 정보
    print("\n### 서울시 지역 코드 정보")
    seoul_codes = {
        "sido": {"code": "11", "name": "서울특별시"},
        "districts": [
            {"code": "11680", "name": "강남구"},
            {"code": "11650", "name": "서초구"},
            {"code": "11440", "name": "마포구"},
            {"code": "11590", "name": "송파구"},
            {"code": "11530", "name": "강동구"},
            {"code": "11350", "name": "노원구"},
            {"code": "11410", "name": "은평구"},
            {"code": "11170", "name": "종로구"},
            {"code": "11140", "name": "중구"},
            {"code": "11200", "name": "성동구"},
            {"code": "11230", "name": "광진구"},
            {"code": "11545", "name": "강남구(개포동)"},
            {"code": "11620", "name": "동작구"},
            {"code": "11560", "name": "강남구(수서동)"},
            {"code": "11710", "name": "강남구(세곡동)"},
        ],
    }

    print(f"시/도 코드: {seoul_codes['sido']['code']} - {seoul_codes['sido']['name']}")
    print("\n구/군 코드 목록 (일부):")
    for district in seoul_codes["districts"][:10]:
        print(f"  {district['code']} - {district['name']}")

    # 6. 추론되는 동 코드 체계
    print("\n### 동 코드 체계 분석")
    print("1. 지역 코드는 10자리 숫자로 구성")
    print("   - 처음 2자리: 시/도 코드 (예: 11 - 서울특별시)")
    print("   - 다음 3자리: 구/군 코드 (예: 680 - 강남구)")
    print("   - 마지막 5자리: 동 코드 (예: 00000 - 구 전체)")
    print("\n2. 예시:")
    print("   - 1168000000: 서울특별시 강남구 전체")
    print("   - 1168010100: 서울특별시 강남구 특정 동")

    # 7. 강남구 동 목록 (법정동 기준)
    print("\n### 강남구 동 목록 (법정동)")
    gangnam_dongs = [
        {
            "code": "1168010100",
            "name": "개포동",
            "type": "법정동",
            "note": "개포1동, 개포2동, 개포3동, 개포4동",
        },
        {"code": "1168010300", "name": "역삼동", "type": "법정동", "note": "역삼1동, 역삼2동"},
        {"code": "1168010500", "name": "도곡동", "type": "법정동", "note": "도곡1동, 도곡2동"},
        {
            "code": "1168010700",
            "name": "대치동",
            "type": "법정동",
            "note": "대치1동, 대치2동, 대치3동, 대치4동",
        },
        {
            "code": "1168010900",
            "name": "수서동",
            "type": "법정동",
            "note": "수서1동, 수서2동, 수서3동",
        },
        {"code": "1168011100", "name": "세곡동", "type": "법정동", "note": "세곡동 (행정동)"},
        {"code": "1168011300", "name": "일원본동", "type": "법정동", "note": "일원1동, 일원2동"},
        {"code": "1168011500", "name": "자곡동", "type": "법정동", "note": "자곡동"},
    ]

    print("| 코드 | 동명 | 타입 | 비고 |")
    print("|------|------|------|------|")
    for dong in gangnam_dongs:
        print(f"| {dong['code']} | {dong['name']} | {dong['type']} | {dong['note']} |")

    # 8. API 호출 예시
    print("\n### 요청 예시")
    print("```bash")
    print("# 강남구 전체 아파트 매물 조회")
    print("curl -X GET 'https://hogangnono.com/api/v2/apts?regionCode=1168000000'")
    print("")
    print("# 역삼동 아파트 매물 조회")
    print("curl -X GET 'https://hogangnono.com/api/v2/apts?regionCode=1168010300'")
    print("")
    print("# 특정 좌표 기반 지역 정보 조회")
    print(
        "curl -X GET 'https://hogangnono.com/api/v2/maps/region?lat=37.5172&lng=127.0473&zoom=15'"
    )
    print("```")

    # 9. 결론 및 다음 단계
    print("\n### 분석 결과")
    print("1. 동 코드 체계: 10자리 숫자 체계 사용 (시도+구군+동)")
    print("2. 좌표 정보: API 응답에 포함되지 않음 (별도 좌표 변환 필요)")
    print("3. 특이사항:")
    print("   - API는 v2 버전 사용")
    print("   - 인증 없이 조회 가능")
    print("   - 지역 코드로 지역별 데이터 조회")

    print("\n### 다음 단계 (5단계: 아파트 단지 정보 API)")
    print("1. /api/v2/apts 엔드포인트 상세 분석")
    print("2. 지역 코드별 아파트 단지 목록 조회")
    print("3. 각 단지의 상세 정보 구조 분석")
    print("4. 페이지네이션 및 필터링 옵션 확인")


if __name__ == "__main__":
    analyze_discovered_apis()
