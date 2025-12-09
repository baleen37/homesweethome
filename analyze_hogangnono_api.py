"""
호갱노노 아파트 단지 정보 조회 API 분석 스크립트
/api/apt/bounding 엔드포인트 상세 분석
"""

import asyncio
import json
from playwright.async_api import async_playwright
from urllib.parse import urlparse, parse_qs


class HogangnonoAPIAnalyzer:
    def __init__(self):
        self.base_url = "https://hogangnono.com"
        self.results = {
            "api_endpoint": None,
            "parameters": {},
            "sample_requests": {},
            "sample_responses": {},
            "field_analysis": {},
            "filter_options": {},
            "pagination_info": {},
        }

    async def analyze_api(self):
        """호갱노노 API 상세 분석"""
        async with async_playwright() as p:
            # 브라우저 실행 (headless=False로 실제 동작 확인)
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            )

            page = await context.new_page()

            # 네트워크 요청 감시
            api_calls = []

            def handle_request(request):
                if "/api/apt/bounding" in request.url:
                    api_calls.append(
                        {
                            "url": request.url,
                            "method": request.method,
                            "headers": dict(request.headers),
                            "post_data": request.post_data,
                        }
                    )

            def handle_response(response):
                if "/api/apt/bounding" in response.url:
                    try:
                        body = response.text()
                        if body:
                            data = json.loads(body)
                            self.results["sample_responses"][response.url] = data
                    except Exception:
                        pass

            page.on("request", handle_request)
            page.on("response", handle_response)

            print("1. 강남구 아파트 단지 정보 조회")
            print("=" * 50)

            # 1. 강남구 지도 접근
            await page.goto(f"{self.base_url}/apt/강남구")
            await page.wait_for_timeout(3000)

            # 지도가 로드되기를 기다림
            await page.wait_for_selector("#map", timeout=10000)
            await page.wait_for_timeout(5000)

            print("2. 서초구 아파트 단지 정보 조회")
            print("=" * 50)

            # 2. 서초구 지도 접근
            await page.goto(f"{self.base_url}/apt/서초구")
            await page.wait_for_timeout(3000)

            # 지도가 로드되기를 기다림
            await page.wait_for_selector("#map", timeout=10000)
            await page.wait_for_timeout(5000)

            print("3. 필터링 옵션 테스트")
            print("=" * 50)

            # 3. 필터링 옵션 테스트 (가격 필터)
            await page.goto(f"{self.base_url}/apt/강남구?minPrice=10&maxPrice=20")
            await page.wait_for_timeout(3000)

            # 4. 면적 필터 테스트
            await page.goto(f"{self.base_url}/apt/강남구?minSize=33&maxSize=85")
            await page.wait_for_timeout(3000)

            # 5. 지도 확대/축소 테스트 (bounds 변경)
            # 자바스크립트로 지도 조작
            await page.evaluate("""
                // 지도 객체 찾기
                const mapContainer = document.getElementById('map');
                if (mapContainer && window.naver && window.naver.maps) {
                    // 더 작은 영역으로 확대
                    const newBounds = new window.naver.maps.LatLngBounds(
                        new window.naver.maps.LatLng(37.495, 127.045),  // 남서쪽
                        new window.naver.maps.LatLng(37.520, 127.065)   // 북동쪽
                    );
                    if (window.map) {
                        window.map.fitBounds(newBounds);
                    }
                }
            """)
            await page.wait_for_timeout(5000)

            # API 호출 결과 분석
            print("\n6. API 호출 결과 분석")
            print("=" * 50)

            if api_calls:
                for i, call in enumerate(api_calls[:3]):  # 처음 3개만 분석
                    print(f"\nAPI Call #{i+1}:")
                    print(f"URL: {call['url']}")
                    print(f"Method: {call['method']}")

                    # URL 파라미터 파싱
                    parsed_url = urlparse(call["url"])
                    params = parse_qs(parsed_url.query)
                    print(f"Parameters: {json.dumps(params, indent=2, ensure_ascii=False)}")

                    # POST 데이터가 있는 경우
                    if call["post_data"]:
                        print(f"POST Data: {call['post_data']}")

                    self.results["sample_requests"][i] = call

                    # 응답 데이터 분석
                    response_key = call["url"]
                    if response_key in self.results["sample_responses"]:
                        response_data = self.results["sample_responses"][response_key]
                        print(
                            f"\nResponse fields count: {len(response_data) if isinstance(response_data, dict) else 'N/A'}"
                        )

                        # 응답 필드 분석
                        if isinstance(response_data, list) and len(response_data) > 0:
                            self.analyze_response_fields(response_data[0], "강남구")
                        elif isinstance(response_data, dict):
                            if "data" in response_data and isinstance(response_data["data"], list):
                                if len(response_data["data"]) > 0:
                                    self.analyze_response_fields(response_data["data"][0], "강남구")

            # 브라우저 종료
            await browser.close()

            # 최종 결과 저장
            await self.save_detailed_analysis()

    def analyze_response_fields(self, data: dict, location: str):
        """응답 데이터 필드 상세 분석"""
        print(f"\n[{location}] 응답 데이터 필드 분석:")
        print("-" * 40)

        for key, value in data.items():
            field_type = type(value).__name__
            print(f"{key}: {field_type} = {value}")

            # ID 체계 분석
            if "id" in key.lower() or "code" in key.lower() or "hash" in key.lower():
                print(f"  -> ID 필드: {key} (타입: {field_type})")

            # 좌표 정보
            if (
                "lat" in key.lower()
                or "lng" in key.lower()
                or "x" in key.lower()
                or "y" in key.lower()
            ):
                print(f"  -> 좌표 필드: {key} = {value}")

            # 가격 정보
            if "price" in key.lower() or "가격" in key or "매매" in key:
                print(f"  -> 가격 필드: {key} = {value}")

            # 면적 정보
            if "size" in key.lower() or "면적" in key or "m²" in str(value):
                print(f"  -> 면적 필드: {key} = {value}")

            # 날짜 정보
            if "date" in key.lower() or "년" in str(value) or "월" in str(value):
                print(f"  -> 날짜 필드: {key} = {value}")

        self.results["field_analysis"][location] = data

    async def save_detailed_analysis(self):
        """상세 분석 결과 저장"""
        # JSON 파일로 저장
        with open(
            "/Users/baleen/dev/homesweethome/hogangnono_api_detailed_analysis.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)

        # 분석 보고서 생성
        report = []
        report.append("# 호갱노노 아파트 단지 정보 조회 API 상세 분석 보고서\n")

        report.append("## 1. API 엔드포인트\n")
        report.append("```\n")
        report.append("https://hogangnono.com/api/apt/bounding\n")
        report.append("```\n")

        report.append("\n## 2. 파라미터 분석\n")
        if self.results["sample_requests"]:
            for i, call in self.results["sample_requests"].items():
                report.append(f"\n### 호출 #{i+1}\n")
                parsed_url = urlparse(call["url"])
                params = parse_qs(parsed_url.query)

                if params:
                    for key, values in params.items():
                        report.append(f"- **{key}**: {', '.join(values)}\n")

        report.append("\n## 3. 응답 데이터 필드\n")
        if self.results["field_analysis"]:
            for location, fields in self.results["field_analysis"].items():
                report.append(f"\n### {location}\n")
                for key, value in fields.items():
                    field_type = type(value).__name__
                    report.append(f"- **{key}** ({field_type}): {value}\n")

        report.append("\n## 4. 특이사항\n")
        report.append("- API 호출은 지도의 bounds(영역)가 변경될 때마다 발생\n")
        report.append("- 필터링 옵션(minPrice, maxSize 등)은 URL 파라미터로 전달\n")
        report.append("- 응답 데이터는 배열 형태로 여러 단지 정보 포함\n")
        report.append("- 각 단지는 고유한 ID/aptHash를 가짐\n")

        # 파일 저장
        with open(
            "/Users/baleen/dev/homesweethome/hogangnono_api_detailed_report.md",
            "w",
            encoding="utf-8",
        ) as f:
            f.writelines(report)

        print("\n분석 완료!")
        print("- 상세 데이터: hogangnono_api_detailed_analysis.json")
        print("- 분석 보고서: hogangnono_api_detailed_report.md")


async def main():
    analyzer = HogangnonoAPIAnalyzer()
    await analyzer.analyze_api()


if __name__ == "__main__":
    asyncio.run(main())
