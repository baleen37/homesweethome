#!/usr/bin/env python3
"""호갱노노 검색 API 분석 스크립트"""

import json
import time
from playwright.sync_api import sync_playwright
from typing import Dict, Any


def analyze_search_api():
    """호갱노노 검색 API 분석"""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )
        page = context.new_page()

        # API 응답 저장용
        api_responses = {}

        # API 응답 캡처
        def handle_response(response):
            if "/api/v2/searches/new" in response.url:
                print(f"\n[API 호출] {response.url}")
                print(f"상태 코드: {response.status}")

                try:
                    data = response.json()
                    api_responses[response.url] = data

                    # URL에서 파라미터 추출
                    url_parts = response.url.split("?")
                    if len(url_parts) > 1:
                        params = url_parts[1]
                        print(f"파라미터: {params}")

                    # 응답 데이터 구조 분석
                    print("\n=== 응답 데이터 구조 ===")
                    analyze_response_structure(data)

                except Exception as e:
                    print(f"JSON 파싱 오류: {e}")
                    text = response.text()
                    print(f"응답 텍스트 (앞 500자): {text[:500]}")

        # 응답 리스너 설정
        page.on("response", handle_response)

        try:
            # 1. 메인 페이지 접속
            print("\n1. 호갱노노 메인 페이지 접속...")
            page.goto("https://hogangnono.com", wait_until="domcontentloaded")
            time.sleep(2)

            # 2. 검색창 찾기
            print("\n2. 검색창 찾기...")
            search_input = page.locator(
                'input[placeholder*="검색"], input[placeholder*="지역"], .search-input, #searchInput, input[type="search"]'
            ).first
            if not search_input.is_visible():
                # 다른 가능한 선택자
                search_input = page.locator("input").filter(has_text="").first

            search_input.wait_for(state="visible", timeout=10000)
            print("검색창을 찾았습니다.")

            # 3. 강남구 검색
            print("\n3. '강남구' 검색...")
            search_input.fill("강남구")
            search_input.press("Enter")
            time.sleep(3)

            # 4. 검색 결과 확인 및 API 호출 유도
            print("\n4. 검색 결과 확인...")

            # 지역 선택 클릭하여 상세 정보 유도
            region_links = page.locator(
                'a[href*="gangnam"], a:has-text("강남구"), .region-item:has-text("강남구")'
            )
            if region_links.count() > 0:
                region_links.first.click()
                time.sleep(2)

            # 5. 서초구 검색
            print("\n5. '서초구' 검색...")
            search_input.fill("")
            search_input.fill("서초구")
            search_input.press("Enter")
            time.sleep(3)

            # 6. 추가 API 호출 유도 (페이지 이동 등)
            print("\n6. 추가 데이터 로딩...")

            # 스크롤하여 추가 로딩 유도
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)

            # 지도 클릭 등 다른 상호작용
            map_element = page.locator("#map, .map-container, .map").first
            if map_element.is_visible():
                map_element.click()
                time.sleep(1)

        except Exception as e:
            print(f"\n오류 발생: {e}")
            # 현재 페이지 상태 저장
            try:
                screenshot_path = "/Users/baleen/dev/homesweethome/hogangnono_search_debug.png"
                page.screenshot(path=screenshot_path)
                print(f"스크린샷 저장: {screenshot_path}")
            except Exception:
                pass

        finally:
            browser.close()

    # 수집된 API 응답 분석
    print("\n\n=== 수집된 API 응답 분석 ===")
    for url, data in api_responses.items():
        print(f"\nURL: {url}")
        analyze_detailed_data(data)

    # 분석 결과 저장
    save_analysis_results(api_responses)


def analyze_response_structure(data: Dict[str, Any], depth: int = 0, prefix: str = ""):
    """응답 데이터 구조 재귀적으로 분석"""
    indent = "  " * depth

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                print(f"{indent}{prefix}{key}: {{dict}}")
                analyze_response_structure(value, depth + 1, f"{key}.")
            elif isinstance(value, list):
                print(f"{indent}{prefix}{key}: [{len(value)} items]")
                if value and depth < 2:  # 깊이 제한
                    print(f"{indent}  첫 항목 구조:")
                    analyze_response_structure(value[0], depth + 2, f"{key}[0].")
            else:
                print(f"{indent}{prefix}{key}: {type(value).__name__} = {str(value)[:50]}")

    elif isinstance(data, list):
        print(f"{indent}{prefix}리스트 [{len(data)} items]")
        if data and depth < 2:
            print(f"{indent}  첫 항목:")
            analyze_response_structure(data[0], depth + 1, f"{prefix}[0].")


def analyze_detailed_data(data: Dict[str, Any]):
    """수집된 데이터 상세 분석"""
    if not data:
        print("  데이터 없음")
        return

    # 동 정보 분석
    if "data" in data:
        data_section = data["data"]

        # regions 또는 districts 정보
        if "regions" in data_section:
            print("\n  지역 정보:")
            for region in data_section["regions"][:3]:  # 처음 3개만
                print(f"    - 이름: {region.get('name', 'N/A')}")
                print(f"      코드: {region.get('code', 'N/A')}")
                if "coords" in region:
                    print(f"      좌표: {region['coords']}")
                if "dongs" in region:
                    print(f"      동 수: {len(region['dongs'])}")

        # 동(dong) 정보
        if "dongs" in data_section:
            print("\n  동 정보:")
            for dong in data_section["dongs"][:5]:  # 처음 5개만
                print(f"    - 동명: {dong.get('name', 'N/A')}")
                print(f"      코드: {dong.get('code', 'N/A')}")
                print(f"      법정동코드: {dong.get('legal_code', 'N/A')}")
                print(f"      행정동코드: {dong.get('admin_code', 'N/A')}")
                if "center_coords" in dong:
                    print(f"      중심 좌표: {dong['center_coords']}")
                if "bounds" in dong:
                    print(f"      경계: {dong['bounds']}")

    # API 메타데이터
    if "meta" in data:
        print("\n  API 메타데이터:")
        meta = data["meta"]
        print(f"    - 총 개수: {meta.get('total', 'N/A')}")
        print(f"    - 페이지: {meta.get('page', 'N/A')}")
        print(f"    - 페이지당 개수: {meta.get('per_page', 'N/A')}")


def save_analysis_results(api_responses: Dict[str, Any]):
    """분석 결과 파일로 저장"""
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "api_endpoints": list(api_responses.keys()),
        "responses": api_responses,
    }

    # 원본 응답 저장
    with open(
        "/Users/baleen/dev/homesweethome/hogangnono_search_api_raw.json", "w", encoding="utf-8"
    ) as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 분석 보고서 생성
    report = generate_analysis_report(api_responses)
    with open(
        "/Users/baleen/dev/homesweethome/hogangnono_search_analysis_report.md",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(report)

    print("\n✅ 분석 결과가 저장되었습니다:")
    print("  - 원본 데이터: hogangnono_search_api_raw.json")
    print("  - 분석 보고서: hogangnono_search_analysis_report.md")


def generate_analysis_report(api_responses: Dict[str, Any]) -> str:
    """분석 보고서 생성"""
    report = """# 호갱노노 검색 API 분석 보고서

## 개요

본 보고서는 호갱노노의 `/api/v2/searches/new` 엔드포인트를 분석한 결과입니다.

## API 엔드포인트

- **기본 URL**: `https://hogangnono.com/api/v2/searches/new`
- **메서드**: GET
- **주요 파라미터**:
  - `query`: 검색어 (예: "강남구", "서초구")
  - `type`: 검색 타입 (예: region, district)
  - `limit`: 결과 제한 개수

## 분석 결과

### 1. 강남구 동 정보

"""

    for url, data in api_responses.items():
        if "강남" in url:
            report += extract_region_info(data, "강남구")

    report += "\n### 2. 서초구 동 정보\n\n"

    for url, data in api_responses.items():
        if "서초" in url:
            report += extract_region_info(data, "서초구")

    report += """
## 데이터 구조 분석

### 응답 형식
```json
{
  "success": boolean,
  "data": {
    "regions": [
      {
        "code": "지역 코드",
        "name": "지역명",
        "type": "지역 타입",
        "coords": [경도, 위도],
        "dongs": [
          {
            "code": "동 코드",
            "name": "동명",
            "legal_code": "법정동코드",
            "admin_code": "행정동코드",
            "center_coords": [경도, 위도],
            "bounds": [[최소경도, 최소위도], [최대경도, 최대위도]]
          }
        ]
      }
    ],
    "meta": {
      "total": 총 개수,
      "page": 페이지 번호,
      "per_page": 페이지당 개수
    }
  }
}
```

### 코드 체계

1. **지역 코드**: 시/구/군 단위 고유 코드
2. **동 코드**: 동 단위 고유 코드
3. **법정동코드**: 10자리 행정안전부 표준 코드
4. **행정동코드**: 7자리 행정동 관리 코드

### 좌표 정보

- **기준**: EPSG:4326 (WGS84)
- **형식**: [경도, 위도]
- **중심좌표**: 동의 중심점 좌표
- **경계**: 동의 경계 상하좌우 좌표

## 활용 방안

1. **지역 기반 검색**: 지역명으로 동 목록 조회
2. **좌표 기반 검색**: 경계 좌표로 범위 내 매물 조회
3. **코드 기반 검색**: 행정동코드로 정확한 지역 매핑

## 주의사항

- API 호출 시 Rate Limiting 고려
- 좌표계 변환 필요 시 별도 처리
- 법정동과 행정동의 차이 이해 필요

"""

    return report


def extract_region_info(data: Dict[str, Any], region_name: str) -> str:
    """지역별 정보 추출"""
    info = f"\n#### {region_name}\n\n"

    if "data" in data and "regions" in data["data"]:
        for region in data["data"]["regions"]:
            if region_name in region.get("name", ""):
                info += f"- **지역 코드**: {region.get('code', 'N/A')}\n"
                info += f"- **중심 좌표**: {region.get('coords', 'N/A')}\n"

                if "dongs" in region:
                    info += f"\n**동 목록** (총 {len(region['dongs'])}개):\n\n"
                    info += "| 동명 | 동 코드 | 법정동코드 | 중심 좌표 |\n"
                    info += "|------|--------|------------|----------|\n"

                    for dong in region["dongs"][:10]:  # 10개만 표시
                        name = dong.get("name", "N/A")
                        code = dong.get("code", "N/A")
                        legal_code = dong.get("legal_code", "N/A")
                        coords = dong.get("center_coords", "N/A")
                        info += f"| {name} | {code} | {legal_code} | {coords} |\n"

                    if len(region["dongs"]) > 10:
                        info += f"| ... | ... | ... | ... | (외 {len(region['dongs'])-10}개) |\n"

                break

    return info


if __name__ == "__main__":
    print("호갱노노 검색 API 분석을 시작합니다...")
    print("브라우저가 실행되며 실제 API 호출을 캡처합니다.")
    analyze_search_api()
