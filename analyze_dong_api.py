#!/usr/bin/env python3
"""
호갱노노 동 목록 API 분석 스크립트
- 특정 구/군에 속한 동 목록 조회 방법 분석
- API 엔드포인트와 파라미터 분석
- 동 코드 체계와 응답 구조 분석
"""

from playwright.sync_api import sync_playwright
import time
from urllib.parse import urlparse, parse_qs


def analyze_dong_api():
    api_requests = []
    dong_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # 네트워크 요청 로그 설정
        api_requests = []

        def log_request(request):
            if (
                "api" in request.url.lower()
                or "dong" in request.url.lower()
                or "region" in request.url.lower()
            ):
                api_requests.append(
                    {
                        "url": request.url,
                        "method": request.method,
                        "headers": dict(request.headers),
                        "post_data": request.post_data,
                    }
                )
                print(f"\n[API 요청] {request.method} {request.url}")
                if request.post_data:
                    print(f"  POST Data: {request.post_data}")

        def log_response(response):
            if (
                "api" in response.url.lower()
                or "dong" in response.url.lower()
                or "region" in response.url.lower()
            ):
                print(f"\n[API 응답] {response.status} {response.url}")
                try:
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        data = response.json()
                        print(f"  응답 (앞 500자): {str(data)[:500]}...")
                except Exception:
                    print(f"  응답 텍스트 (앞 200자): {response.text()[:200]}...")

        page.on("request", log_request)
        page.on("response", log_response)

        try:
            # 1. 메인 페이지 접속
            print("\n=== 1. 메인 페이지 접속 ===")
            page.goto("https://hogangnono.com")
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            # 2. 지역 검색 버튼 클릭
            print("\n=== 2. 지역 검색 버튼 찾기 ===")

            # 여러 가능한 지역 선택자 시도
            region_selectors = [
                "button[aria-label*='지역']",
                "button[data-testid*='region']",
                ".region-button",
                ".location-button",
                "[class*='region']",
                "[class*='location']",
                "button:has-text('지역')",
                "button:has-text('서울')",
                "a:has-text('지역')",
            ]

            region_button = None
            for selector in region_selectors:
                try:
                    region_button = page.wait_for_selector(selector, timeout=3000)
                    if region_button:
                        print(f"  ✅ 지역 버튼 찾음: {selector}")
                        region_button.click()
                        break
                except Exception:
                    continue

            if not region_button:
                # URL로 직접 접근 시도
                print("  🔄 지역 버튼을 찾지 못해 URL로 직접 접근...")
                page.goto("https://hogangnono.com/main")
                page.wait_for_load_state("networkidle")
                time.sleep(2)

            # 3. 서울특별시 선택
            print("\n=== 3. 서울특별시 선택 ===")

            # 시/도 선택
            city_selectors = [
                "button:has-text('서울특별시')",
                "[data-ciy*='서울']",
                "a:has-text('서울')",
            ]

            for selector in city_selectors:
                try:
                    city_button = page.wait_for_selector(selector, timeout=3000)
                    if city_button:
                        city_button.click()
                        print("  ✅ 서울특별시 선택")
                        time.sleep(1)
                        break
                except Exception:
                    continue

            # 4. 강남구 선택 및 동 목록 API 분석
            print("\n=== 4. 강남구 선택 및 동 목록 분석 ===")

            # 구/군 선택 전 API 요청 초기화
            api_requests.clear()

            # 강남구 클릭
            district_selectors = [
                "button:has-text('강남구')",
                "a:has-text('강남구')",
                "[data-gu*='강남']",
            ]

            for selector in district_selectors:
                try:
                    district_button = page.wait_for_selector(selector, timeout=3000)
                    if district_button:
                        district_button.click()
                        print("  ✅ 강남구 선택")
                        time.sleep(2)
                        break
                except Exception:
                    continue

            # 동 목록 API 요청 분석
            print("\n=== 강남구 동 목록 API 요청 분석 ===")
            dong_requests = [req for req in api_requests if "dong" in req["url"].lower()]

            if dong_requests:
                print(f"  총 {len(dong_requests)}개의 동 관련 API 요청 발견")
                for req in dong_requests[:3]:  # 처음 3개만 표시
                    print(f"\n  요청: {req['method']} {req['url']}")
                    if req.get("post_data"):
                        print(f"  데이터: {req['post_data']}")

            # 5. 다른 구(서초구) 선택하여 비교
            print("\n=== 5. 서초구 동 목록 비교 ===")

            # 서초구 클릭
            api_requests.clear()

            seocho_selectors = [
                "button:has-text('서초구')",
                "a:has-text('서초구')",
                "[data-gu*='서초']",
            ]

            for selector in seocho_selectors:
                try:
                    seocho_button = page.wait_for_selector(selector, timeout=3000)
                    if seocho_button:
                        seocho_button.click()
                        print("  ✅ 서초구 선택")
                        time.sleep(2)
                        break
                except Exception:
                    continue

            # 6. DOM에서 직접 동 정보 추출
            print("\n=== 6. DOM에서 동 정보 직접 추출 ===")

            # 동 목록이 표시될 수 있는 요소들
            dong_list_selectors = [
                ".dong-list",
                ".region-list",
                "[class*='dong']",
                "li:has-text('동')",
                "div:has-text('동')",
            ]

            dong_data = []
            for selector in dong_list_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    if elements:
                        print(f"\n  ✅ {len(elements)}개의 동 요소 발견: {selector}")
                        for elem in elements[:10]:  # 처음 10개만
                            text = elem.text_content()
                            if text and "동" in text:
                                print(f"    - {text}")
                                # 데이터 속성 추출
                                data_code = elem.get_attribute("data-code")
                                data_id = elem.get_attribute("data-id")
                                data_value = elem.get_attribute("data-value")

                                dong_data.append(
                                    {
                                        "name": text,
                                        "code": data_code,
                                        "id": data_id,
                                        "value": data_value,
                                    }
                                )
                        break
                except Exception:
                    continue

            # 7. JavaScript 실행으로 동 데이터 가져오기
            print("\n=== 7. JavaScript로 동 데이터 가져오기 ===")

            js_code = """
            () => {
                // 페이지 내의 동 관련 데이터 찾기
                const dongData = [];

                // window 객체 확인
                if (window.__INITIAL_STATE__ || window.__NUXT__ || window.__VUE__) {
                    const state = window.__INITIAL_STATE__ || window.__NUXT__ || window.__VUE__;
                    dongData.push({source: "window", data: JSON.stringify(state).substring(0, 500)});
                }

                // localStorage 확인
                try {
                    for (let i = 0; i < localStorage.length; i++) {
                        const key = localStorage.key(i);
                        if (key && (key.includes('dong') || key.includes('region') || key.includes('area'))) {
                            dongData.push({source: "localStorage", key: key, value: localStorage.getItem(key)});
                        }
                    }
                } catch(e) {}

                // sessionStorage 확인
                try {
                    for (let i = 0; i < sessionStorage.length; i++) {
                        const key = sessionStorage.key(i);
                        if (key && (key.includes('dong') || key.includes('region') || key.includes('area'))) {
                            dongData.push({source: "sessionStorage", key: key, value: sessionStorage.getItem(key)});
                        }
                    }
                } catch(e) {}

                // 버튼 요소에서 동 정보 추출
                const buttons = document.querySelectorAll('button, a, li[onclick]');
                buttons.forEach(btn => {
                    const text = btn.textContent || '';
                    if (text.includes('동') && text.length < 10) {
                        const onclick = btn.getAttribute('onclick');
                        const dataset = btn.dataset;
                        dongData.push({
                            source: "element",
                            text: text,
                            onclick: onclick,
                            dataset: dataset
                        });
                    }
                });

                return dongData;
            }
            """

            try:
                js_result = page.evaluate(js_code)
                print("\n  JavaScript 실행 결과:")
                for item in js_result[:20]:  # 처음 20개만
                    if isinstance(item, dict):
                        if item.get("text"):
                            print(f"    - {item.get('text')}")
                        elif item.get("key"):
                            print(f"    {item.get('key')}: {str(item.get('value'))[:100]}...")
                    else:
                        print(f"    {str(item)[:100]}...")
            except Exception as e:
                print(f"  JavaScript 실행 오류: {e}")

            # 8. 수동으로 API 호출 시도
            print("\n=== 8. 수동 API 호출 시도 ===")

            # 가능한 동 목록 API 엔드포인트
            possible_apis = [
                "https://hogangnono.com/api/regions",
                "https://hogangnono.com/api/dongs",
                "https://api.hogangnono.com/regions",
                "https://hogangnono.com/v1/regions",
                "/api/common/region",
                "/api/region/dong",
            ]

            for api in possible_apis:
                try:
                    # GET 요청 시도
                    response = page.goto(api, wait_until="networkidle")
                    if response and response.status == 200:
                        data = response.json()
                        print(f"\n  ✅ API 발견: {api}")
                        print(f"  응답: {str(data)[:300]}...")
                        break
                except Exception:
                    # POST 요청 시도
                    try:
                        response = page.request.post(api, data={"regionCode": "11680"})
                        if response and response.status == 200:
                            data = response.json()
                            print(f"\n  ✅ API 발견 (POST): {api}")
                            print(f"  응답: {str(data)[:300]}...")
                            break
                    except Exception:
                        continue

        except Exception as e:
            print(f"\n❌ 분석 중 오류 발생: {e}")
            # 스크린샷 저장
            page.screenshot(path="dong_api_analysis.png")
            print("  📸 스크린샷 저장: dong_api_analysis.png")

        finally:
            time.sleep(3)
            browser.close()

    return api_requests, dong_data


# 결과 분석 및 출력
def print_analysis_results(api_requests, dong_data):
    print("\n\n" + "=" * 80)
    print("## 4단계: 동 목록 API 분석 결과")
    print("=" * 80)

    print("\n### API 엔드포인트")
    if api_requests:
        unique_apis = set(req["url"] for req in api_requests)
        for api in unique_apis:
            print(f"- 발견된 API: {api}")
    else:
        print("- API 엔드포인트를 자동으로 찾지 못했습니다")

    print("\n### 요청 패턴 분석")
    for req in api_requests[:5]:
        print(f"\n요청: {req['method']} {req['url']}")
        if req.get("post_data"):
            print(f"  POST 데이터: {req['post_data']}")
        print(f"  헤더: {dict(list(req['headers'].items())[:5])}")  # 처음 5개 헤더만

    print("\n### 동 데이터 추출 결과")
    if dong_data:
        print(f"- 총 {len(dong_data)}개의 동 데이터 발견")
        for i, dong in enumerate(dong_data[:10]):
            print(f"\n  {i+1}. {dong}")
    else:
        print("- 동 데이터를 직접 추출하지 못했습니다")

    print("\n### 추론되는 API 패턴")
    print("1. URL 패턴: /api/regions 또는 /api/dongs")
    print("2. 파라미터: regionCode (예: 11680 - 강남구)")
    print("3. 응답 형식: JSON 배열 형태의 동 목록")

    print("\n### 다음 단계 제안")
    print("1. 소스 코드 분석을 통한 API 엔드포인트 확인")
    print("2. 네트워크 탭에서 필터링하여 동 관련 API 찾기")
    print("3. 특정 구 선택 시 발생하는 XHR/Fetch 요청 모니터링")

    # 저장된 데이터 분석
    if api_requests:
        print("\n### 발견된 네트워크 요청 요약")
        for i, req in enumerate(api_requests):
            print(f"\n{i+1}. {req['method']} {req['url']}")
            parsed = urlparse(req["url"])
            print(f"   - 도메인: {parsed.netloc}")
            print(f"   - 경로: {parsed.path}")
            if parsed.query:
                params = parse_qs(parsed.query)
                print(f"   - 쿼리 파라미터: {params}")


if __name__ == "__main__":
    print("🚀 호갱노노 동 목록 API 분석 시작...")
    api_requests, dong_data = analyze_dong_api()
    print_analysis_results(api_requests, dong_data)
