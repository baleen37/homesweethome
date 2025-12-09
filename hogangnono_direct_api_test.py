#!/usr/bin/env python3
"""호갱노노 API 직접 호출 테스트"""

import requests
import json
import time


def test_search_api(query: str, x: float = None, y: float = None):
    """검색 API 직접 호출"""
    base_url = "https://hogangnono.com/api/v2/searches/new"

    # 기본 파라미터
    params = {
        "query": query,
    }

    # 좌표가 있는 경우 추가
    if x is not None:
        params["x"] = x
    if y is not None:
        params["y"] = y

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9",
        "Referer": "https://hogangnono.com/",
    }

    print(f"\n호출 URL: {base_url}?{ '&'.join(f'{k}={v}' for k, v in params.items()) }")

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        # 기본 정보 출력
        print(f"\n=== {query} 검색 결과 ===")
        print(f"상태: {data.get('status', 'N/A')}")

        # region 정보 추출
        if "data" in data and "matched" in data["data"]:
            matched = data["data"]["matched"]

            if "region" in matched:
                print("\n지역 정보:")
                for region in matched["region"]["list"]:
                    print(f"\n  지역명: {region.get('name', 'N/A')}")
                    print(f"  코드: {region.get('code', 'N/A')}")
                    print(f"  타입: {region.get('type', 'N/A')}")
                    print(f"  좌표: {region.get('x', 'N/A')}, {region.get('y', 'N/A')}")
                    print(f"  주소: {region.get('addr', 'N/A')}")

                    # 하위 동 정보
                    if "dongs" in region:
                        print(f"\n  포함된 동 ({len(region['dongs'])}개):")
                        for dong in region["dongs"][:5]:  # 처음 5개만
                            print(
                                f"    - {dong.get('name', 'N/A')} (코드: {dong.get('code', 'N/A')})"
                            )

                        if len(region["dongs"]) > 5:
                            print(f"    ... 외 {len(region['dongs'])-5}개")

        # 응답 전체 저장
        timestamp = int(time.time())
        filename = f"/Users/baleen/dev/homesweethome/hogangnono_api_{query.replace('구', '')}_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 상세 데이터 저장: {filename}")

        return data

    except Exception as e:
        print(f"오류 발생: {e}")
        return None


def test_regions_api():
    """지역 목록 API 테스트"""
    print("\n\n=== 지역 목록 API 테스트 ===")

    # 서울특별시 코드로 시도
    url = "https://hogangnono.com/api/v1/regions?code=11"  # 서울특별시 코드: 11

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://hogangnono.com/",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()

            # 서울시 구 목록 저장
            filename = "/Users/baleen/dev/homesweethome/seoul_regions.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"\n서울시 구 정보가 저장되었습니다: {filename}")

            # 구 정보 중 강남구, 서초구 출력
            if "data" in data and "regions" in data["data"]:
                for region in data["data"]["regions"]:
                    if region.get("name") in ["강남구", "서초구"]:
                        print(f"\n{region.get('name')}:")
                        print(f"  - 코드: {region.get('code')}")
                        print(f"  - 타입: {region.get('type')}")
                        print(f"  - 좌표: {region.get('x')}, {region.get('y')}")

                        # 동 정보
                        if "dongs" in region:
                            print(f"  - 동 수: {len(region['dongs'])}")

        else:
            print(f"API 호출 실패: {response.status_code}")

    except Exception as e:
        print(f"오류: {e}")


def analyze_gangnam_seocho():
    """강남구와 서초구 상세 분석"""
    print("\n\n=== 강남구와 서초구 상세 분석 ===")

    # 강남구 중심 좌표
    gangnam_coords = (127.046953, 37.517236)
    seocho_coords = (127.005732, 37.483735)

    # 강남구 검색
    gangnam_data = test_search_api("강남구", *gangnam_coords)

    time.sleep(1)  # Rate limiting 고려

    # 서초구 검색
    seocho_data = test_search_api("서초구", *seocho_coords)

    # 비교 분석
    print("\n\n=== 비교 분석 ===")
    if gangnam_data and seocho_data:
        print("\n강남구 vs 서초구:")

        # 동 수 비교
        gangnam_dongs = len(extract_dongs_count(gangnam_data))
        seocho_dongs = len(extract_dongs_count(seocho_data))

        print(f"  - 동 수: 강남구 {gangnam_dongs}개, 서초구 {seocho_dongs}개")

        # 동 목록 출력
        print("\n  강남구 동 목록:")
        for dong in extract_all_dongs(gangnam_data):
            print(f"    - {dong}")

        print("\n  서초구 동 목록:")
        for dong in extract_all_dongs(seocho_data):
            print(f"    - {dong}")


def extract_dongs_count(data: dict) -> list:
    """데이터에서 동 정보 추출"""
    dongs = []
    if "data" in data and "matched" in data["data"]:
        if "region" in data["data"]["matched"]:
            for region in data["data"]["matched"]["region"]["list"]:
                if "dongs" in region:
                    dongs.extend(region["dongs"])
    return dongs


def extract_all_dongs(data: dict) -> list:
    """모든 동명 추출"""
    dong_names = []
    dongs = extract_dongs_count(data)
    for dong in dongs:
        name = dong.get("name", "")
        if name and name not in dong_names:
            dong_names.append(name)
    return sorted(dong_names)


if __name__ == "__main__":
    print("호갱노노 API 직접 호출 테스트")
    print("=" * 50)

    # 1. 강남구 상세 정보
    test_search_api("강남구", 127.046953, 37.517236)

    time.sleep(1)

    # 2. 서초구 상세 정보
    test_search_api("서초구", 127.005732, 37.483735)

    time.sleep(1)

    # 3. 지역 목록 API
    test_regions_api()

    time.sleep(1)

    # 4. 비교 분석
    analyze_gangnam_seocho()

    print("\n\n✅ 모든 테스트 완료")
    print("생성된 파일:")
    print("  - hogangnono_search_api_raw.json (원본 API 응답)")
    print("  - hogangnono_search_analysis_report.md (분석 보고서)")
    print("  - seoul_regions.json (서울시 구 정보)")
