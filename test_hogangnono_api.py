#!/usr/bin/env python3
"""호갱노노 API 테스트 스크립트"""

import requests


def test_hogangnono_apis():
    """호갱노노 API 테스트"""
    base_url = "https://hogangnono.com"
    session = requests.Session()

    # 헤더 설정
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Ch-Ua": '"Not.A/Brand";v="8", "Chromium";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Referer": "https://hogangnono.com/",
        "Origin": "https://hogangnono.com",
        "X-Requested-With": "XMLHttpRequest",
    }

    # 1. 먼저 메인 페이지에 접속하여 세션 쿠키 받기
    print("1. 메인 페이지 접속 (세션 초기화)...")
    main_response = session.get(
        base_url,
        headers={
            "User-Agent": headers["User-Agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": headers["Accept-Language"],
            "Accept-Encoding": headers["Accept-Encoding"],
            "Cache-Control": "max-age=0",
            "Sec-Ch-Ua": headers["Sec-Ch-Ua"],
            "Sec-Ch-Ua-Mobile": headers["Sec-Ch-Ua-Mobile"],
            "Sec-Ch-Ua-Platform": headers["Sec-Ch-Ua-Platform"],
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        },
    )

    print(f"메인 페이지 상태: {main_response.status_code}")
    print(f"쿠키: {session.cookies.get_dict()}")

    # 2. suggestions API 테스트
    print("\n2. 지역 검색 suggestions API 테스트...")

    # 다양한 파라미터 조합 테스트
    test_queries = [
        {"query": "서울특별시"},
        {"keyword": "서울"},
        {"q": "서울특별시 강남구"},
        {"search": "강남구"},
        {"local1": "서울특별시"},
        {"region": "서울특별시"},
    ]

    for params in test_queries:
        try:
            response = session.get(
                f"{base_url}/api/v2/searches/suggestions", params=params, headers=headers
            )
            print(f"파라미터 {params}: 상태 {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  응답 크기: {len(str(data))}")
                if data and isinstance(data, dict):
                    if "data" in data:
                        print(f"  데이터 항목 수: {len(data.get('data', []))}")
        except Exception as e:
            print(f"  에러: {e}")

    # 3. regions API 테스트 (있을 경우)
    print("\n3. 지역 정보 API 테스트...")

    region_endpoints = [
        "/api/v2/regions",
        "/api/v2/regions/search",
        "/api/v2/local1",
        "/api/v2/local2",
        "/api/regions",
        "/api/local1",
        "/api/local2",
    ]

    for endpoint in region_endpoints:
        try:
            response = session.get(f"{base_url}{endpoint}", headers=headers)
            if response.status_code == 200:
                print(f"✓ {endpoint}: 정상 응답")
                data = response.json()
                if isinstance(data, dict) and "data" in data:
                    print(f"  데이터 항목 수: {len(data.get('data', []))}")
            else:
                print(f"✗ {endpoint}: 상태 {response.status_code}")
        except Exception as e:
            print(f"✗ {endpoint}: 에러 {e}")

    # 4. POI bounding 테스트 (서울시 각 구별)
    print("\n4. 서울시 구별 POI 조회 테스트...")

    # 서울시 주요 구 좌표 (대략적인 중심 좌표)
    seoul_districts = [
        {"name": "강남구", "lat": 37.5172, "lng": 127.0473},
        {"name": "강동구", "lat": 37.5302, "lng": 127.1239},
        {"name": "강북구", "lat": 37.6396, "lng": 127.0257},
        {"name": "강서구", "lat": 37.5509, "lng": 126.8495},
        {"name": "관악구", "lat": 37.4673, "lng": 126.9453},
        {"name": "광진구", "lat": 37.5485, "lng": 127.0837},
        {"name": "구로구", "lat": 37.4955, "lng": 126.8874},
        {"name": "금천구", "lat": 37.4560, "lng": 126.8950},
        {"name": "노원구", "lat": 37.6542, "lng": 127.0568},
        {"name": "도봉구", "lat": 37.6691, "lng": 127.0323},
        {"name": "동대문구", "lat": 37.5744, "lng": 127.0396},
        {"name": "동작구", "lat": 37.5124, "lng": 126.9393},
        {"name": "마포구", "lat": 37.5663, "lng": 126.9013},
        {"name": "서대문구", "lat": 37.5794, "lng": 126.9369},
        {"name": "서초구", "lat": 37.4837, "lng": 127.0324},
        {"name": "성동구", "lat": 37.5634, "lng": 127.0366},
        {"name": "성북구", "lat": 37.5894, "lng": 127.0168},
        {"name": "송파구", "lat": 37.5145, "lng": 127.1056},
        {"name": "양천구", "lat": 37.5169, "lng": 126.8665},
        {"name": "영등포구", "lat": 37.5265, "lng": 126.8963},
        {"name": "용산구", "lat": 37.5314, "lng": 126.9658},
        {"name": "은평구", "lat": 37.6176, "lng": 126.9227},
        {"name": "종로구", "lat": 37.5744, "lng": 126.9799},
        {"name": "중구", "lat": 37.5638, "lng": 126.9976},
        {"name": "중랑구", "lat": 37.6064, "lng": 127.0928},
    ]

    # bounding box 크기 (약 5km x 5km)
    delta = 0.025

    for district in seoul_districts[:5]:  # 처음 5개 구만 테스트
        print(f"\n  {district['name']} POI 조회...")
        params = {
            "level": "14",
            "startX": district["lng"] - delta,
            "endX": district["lng"] + delta,
            "startY": district["lat"] - delta,
            "endY": district["lat"] + delta,
            "map": "google",
            "screenWidth": 1200,
            "screenHeight": 924,
            "apt": "",
            "isIgnorePin": False,
        }

        try:
            response = session.get(
                f"{base_url}/api/v2/pois-bounding", params=params, headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                pois = data.get("data", [])
                print(f"    ✓ POI 수: {len(pois)}")

                # 카테고리별 분류
                categories = {}
                for poi in pois:
                    cat = poi.get("category", "unknown")
                    categories[cat] = categories.get(cat, 0) + 1

                print(f"    카테고리: {categories}")

                # 샘플 POI 출력
                if pois:
                    print(
                        f"    샘플: {pois[0].get('name', 'N/A')} (카테고리: {pois[0].get('category', 'N/A')})"
                    )
            else:
                print(f"    ✗ 상태: {response.status_code}")
        except Exception as e:
            print(f"    ✗ 에러: {e}")

    # 5. 검색 API 다양한 조합 테스트
    print("\n5. 검색 API 다양한 엔드포인트 테스트...")

    search_endpoints = [
        "/api/v2/search",
        "/api/v2/searches",
        "/api/search",
        "/api/search/regions",
        "/api/search/local",
        "/api/v2/search/local1",
        "/api/v2/search/local2",
    ]

    for endpoint in search_endpoints:
        try:
            response = session.get(
                f"{base_url}{endpoint}", params={"query": "서울특별시"}, headers=headers
            )
            if response.status_code == 200:
                print(f"✓ {endpoint}: 정상 응답")
                data = response.json()
                print(f"  응답 크기: {len(str(data))}")
        except Exception as e:
            print(f"✗ {endpoint}: 에러 {e}")


if __name__ == "__main__":
    test_hogangnono_apis()
