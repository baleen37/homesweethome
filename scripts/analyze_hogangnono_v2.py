#!/usr/bin/env python3
"""호갱노노 사이트 분석 스크립트 (개선 버전)

이 스크립트는 Playwright를 사용하여 호갱노노 사이트를 탐색하고,
UI 구조, 검색 기능, 매물 목록 표시 방식 등을 분석합니다.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, Request
from structlog import get_logger

logger = get_logger()


class HogangnonoAnalyzer:
    """호갱노노 사이트 분석기"""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.screenshot_dir = Path("output/hogangnono_screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.api_requests: List[Dict[str, Any]] = []
        self.current_url = ""

    async def setup(self) -> None:
        """Playwright 브라우저 설정"""
        self.playwright = await async_playwright().start()

        # 브라우저 실행 (시각적으로 확인을 위해 headless=False)
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=500,  # 0.5초 지연으로 실행 과정 확인
        )

        # 컨텍스트 설정
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        # 페이지 생성
        self.page = await self.context.new_page()

        # 네트워크 요청 수집
        self.api_requests = []
        self.page.on("request", self._handle_request)

        logger.info("브라우저 설정 완료")

    async def _handle_request(self, request: Request) -> None:
        """네트워크 요청 핸들러"""
        url = request.url
        if "api" in url or "ajax" in url:
            self.api_requests.append(
                {
                    "url": url,
                    "method": request.method,
                    "headers": dict(request.headers),
                    "timestamp": time.time(),
                }
            )
            logger.info("API 요청 감지", url=url, method=request.method)

    async def cleanup(self) -> None:
        """리소스 정리"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, "playwright"):
            await self.playwright.stop()
        logger.info("브라우저 리소스 정리 완료")

    async def take_screenshot(self, name: str) -> str:
        """스크린샷 저장"""
        if self.page:
            screenshot_path = self.screenshot_dir / f"{name}_{int(time.time())}.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info("스크린샷 저장", path=str(screenshot_path))
            return str(screenshot_path)
        return ""

    async def wait_and_click(self, selector: str, timeout: int = 10000) -> bool:
        """요소 대기 후 클릭"""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            await self.page.click(selector)
            return True
        except Exception as e:
            logger.warning("클릭 실패", selector=selector, error=str(e))
            return False

    async def wait_and_type(self, selector: str, text: str, timeout: int = 10000) -> bool:
        """요소 대기 후 텍스트 입력"""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            await self.page.fill(selector, text)
            return True
        except Exception as e:
            logger.warning("텍스트 입력 실패", selector=selector, error=str(e))
            return False

    async def analyze_homepage(self) -> Dict[str, Any]:
        """메인페이지 분석"""
        logger.info("=== 메인페이지 분석 시작 ===")
        analysis = {}

        try:
            # 사이트 접속
            await self.page.goto("https://hogangnono.com", timeout=60000)
            await asyncio.sleep(5)  # 페이지 로딩 대기
            self.current_url = self.page.url

            # 스크린샷
            await self.take_screenshot("homepage")

            # 페이지 기본 정보
            analysis["title"] = await self.page.title()
            analysis["url"] = self.page.url

            # UI 요소 분석
            ui_elements = {}

            # 검색 관련 요소
            search_selectors = [
                'input[placeholder*="검색"]',
                'input[placeholder*="지역"]',
                "#searchInput",
                ".search-input",
                'input[type="search"]',
                ".search-bar input",
            ]
            for selector in search_selectors:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    ui_elements["search_inputs"] = selector
                    break

            # 지역/버튼 요소
            region_selectors = ["[data-region]", ".region-btn", ".area-btn", ".location-btn"]
            for selector in region_selectors:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    ui_elements["region_buttons"] = selector
                    analysis["region_count"] = len(elements)
                    break

            # 거래유형 탭
            trade_selectors = [".trade-type", "[data-trade]", ".tab-trade", ".filter-trade"]
            for selector in trade_selectors:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    ui_elements["trade_tabs"] = selector
                    analysis["trade_count"] = len(elements)
                    break

            # 필터 옵션
            filter_selectors = [".filter", ".option", "select", ".range"]
            for selector in filter_selectors:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    ui_elements["filters"] = selector
                    analysis["filter_count"] = len(elements)
                    break

            analysis["ui_elements"] = ui_elements
            logger.info("UI 분석 완료", elements=ui_elements)

        except Exception as e:
            logger.error("홈페이지 분석 중 오류", error=str(e))

        return analysis

    async def search_location(self, location: str = "강남구") -> bool:
        """지역 검색"""
        logger.info(f"=== 지역 검색: {location} ===")

        try:
            # 방법 1: 검색창에 입력
            search_input_selectors = [
                'input[placeholder*="검색"]',
                'input[placeholder*="지역"]',
                ".search-input",
                "#searchInput",
            ]

            search_success = False
            for selector in search_input_selectors:
                if await self.wait_and_type(selector, location, timeout=5000):
                    # Enter 키 입력
                    await self.page.press(selector, "Enter")
                    search_success = True
                    break

            if not search_success:
                # 방법 2: 지역 버튼 클릭
                location_btn_selectors = [
                    f'button:has-text("{location}")',
                    f'[data-region*="{location}"]',
                    f'a:has-text("{location}")',
                    f'.region-btn:has-text("{location}")',
                ]

                for selector in location_btn_selectors:
                    if await self.wait_and_click(selector, timeout=5000):
                        search_success = True
                        break

            if search_success:
                await asyncio.sleep(3)
                await self.take_screenshot(f"search_result_{location}")
                self.current_url = self.page.url
                return True

        except Exception as e:
            logger.error("검색 중 오류", error=str(e))

        return False

    async def analyze_property_list(self) -> Dict[str, Any]:
        """매물 목록 분석"""
        logger.info("=== 매물 목록 분석 ===")
        analysis = {}

        try:
            # 매물 목록 컨테이너 찾기
            list_container_selectors = [
                ".property-list",
                ".item-list",
                ".apt-list",
                ".list-container",
                "[data-list]",
                "ul.items",
                ".cards",
            ]

            list_container = None
            for selector in list_container_selectors:
                element = await self.page.query_selector(selector)
                if element:
                    list_container = element
                    analysis["list_container_selector"] = selector
                    break

            if list_container:
                # 매물 아이템 찾기
                item_selectors = [
                    ".item",
                    ".property-item",
                    ".apt-item",
                    "li",
                    "[data-item]",
                    ".card",
                ]

                items = []
                for selector in item_selectors:
                    elements = await list_container.query_selector_all(selector)
                    if elements:
                        items = elements
                        analysis["item_selector"] = selector
                        break

                if items:
                    analysis["item_count"] = len(items)
                    logger.info("매물 발견", count=len(items))

                    # 첫 번째 매물 상세 분석
                    first_item = items[0]

                    # 가격 정보
                    price_info = []
                    price_selectors = [".price", ".cost", ".amount", ".won"]
                    for selector in price_selectors:
                        price_elements = await first_item.query_selector_all(selector)
                        for el in price_elements:
                            text = await el.text_content()
                            if text:
                                price_info.append(text.strip())

                    if price_info:
                        analysis["price_info"] = price_info

                    # 매물 클릭 시도
                    clickable = await first_item.is_enabled()
                    if clickable:
                        await first_item.click()
                        await asyncio.sleep(3)
                        await self.take_screenshot("property_detail")
                        analysis["detail_loaded"] = True
                        self.current_url = self.page.url

        except Exception as e:
            logger.error("매물 목록 분석 중 오류", error=str(e))

        return analysis

    async def analyze_trade_types(self) -> Dict[str, Any]:
        """거래유형(매매/전세/월세) 분석"""
        logger.info("=== 거래유형 분석 ===")
        analysis = {}

        try:
            # 탭 또는 버튼 찾기
            trade_selectors = [
                ".tab-trade",
                ".trade-type",
                "[data-trade]",
                ".filter-tabs button",
                ".trade-filter button",
            ]

            for selector in trade_selectors:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    trade_types = []
                    for el in elements:
                        text = await el.text_content()
                        if text:
                            trade_types.append(text.strip())

                    if trade_types:
                        analysis["trade_types"] = trade_types
                        analysis["selector"] = selector
                        logger.info("거래유형 발견", types=trade_types)
                        break

        except Exception as e:
            logger.error("거래유형 분석 중 오류", error=str(e))

        return analysis

    async def analyze_api_endpoints(self) -> List[Dict[str, Any]]:
        """API 엔드포인트 분석"""
        logger.info("=== API 엔드포인트 분석 ===")

        # 수집된 API 요청 정리
        api_analysis = []
        for req in self.api_requests:
            api_info = {
                "url": req["url"],
                "method": req["method"],
                "endpoint": req["url"].split("api/")[-1] if "api/" in req["url"] else req["url"],
                "headers": {
                    k: v
                    for k, v in req["headers"].items()
                    if k.lower() in ["content-type", "authorization", "x-requested-with"]
                },
            }
            api_analysis.append(api_info)

        # 중복 제거
        unique_apis = []
        seen_endpoints = set()
        for api in api_analysis:
            if api["endpoint"] not in seen_endpoints:
                unique_apis.append(api)
                seen_endpoints.add(api["endpoint"])

        logger.info("발견된 API 엔드포인트", count=len(unique_apis))
        for api in unique_apis[:5]:  # 처음 5개만 로깅
            logger.info("API", endpoint=api["endpoint"], method=api["method"])

        return unique_apis

    async def run_full_analysis(self) -> Dict[str, Any]:
        """전체 분석 실행"""
        results = {"timestamp": time.time(), "analysis": {}, "screenshots": [], "api_endpoints": []}

        try:
            await self.setup()

            # 1. 홈페이지 분석
            homepage_analysis = await self.analyze_homepage()
            results["analysis"]["homepage"] = homepage_analysis

            # 2. 지역 검색
            search_success = await self.search_location("강남구")
            results["analysis"]["search_success"] = search_success

            # 3. 매물 목록 분석
            if search_success:
                property_analysis = await self.analyze_property_list()
                results["analysis"]["property_list"] = property_analysis

                # 4. 거래유형 분석
                trade_analysis = await self.analyze_trade_types()
                results["analysis"]["trade_types"] = trade_analysis

            # 5. API 엔드포인트 분석
            api_endpoints = await self.analyze_api_endpoints()
            results["api_endpoints"] = api_endpoints

            # 스크린샷 목록
            screenshots = list(self.screenshot_dir.glob("*.png"))
            results["screenshots"] = [str(s) for s in screenshots]

            logger.info("분석 완료")

        except Exception as e:
            logger.error("전체 분석 중 오류", error=str(e))
            results["error"] = str(e)

        finally:
            await self.cleanup()

        return results


async def main():
    """메인 함수"""
    logger.info("호갱노노 사이트 분석 시작")

    analyzer = HogangnonoAnalyzer(headless=False)  # 시각적 확인을 위해 headless=False
    results = await analyzer.run_full_analysis()

    # 결과 저장
    output_path = Path("output/hogangnono_analysis.json")
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info("분석 결과 저장", path=str(output_path))

    # 요약 출력
    if "analysis" in results:
        print("\n=== 분석 요약 ===")

        # 홈페이지 정보
        if "homepage" in results["analysis"]:
            homepage = results["analysis"]["homepage"]
            print("\n1. 홈페이지 정보:")
            print(f"   - 제목: {homepage.get('title', 'N/A')}")
            print(f"   - URL: {homepage.get('url', 'N/A')}")
            if "ui_elements" in homepage:
                print(f"   - UI 요소: {homepage['ui_elements']}")

        # 검색 결과
        print(f"\n2. 검색 성공: {results['analysis'].get('search_success', False)}")

        # 매물 정보
        if "property_list" in results["analysis"]:
            props = results["analysis"]["property_list"]
            print("\n3. 매물 목록:")
            print(f"   - 매물 수: {props.get('item_count', 0)}")
            if "price_info" in props:
                print(f"   - 가격 정보 예시: {props['price_info'][:2]}")

        # 거래유형
        if "trade_types" in results["analysis"]:
            trades = results["analysis"]["trade_types"]
            print(f"\n4. 거래유형: {trades.get('trade_types', [])}")

        # API 엔드포인트
        print(f"\n5. 발견된 API 엔드포인트: {len(results.get('api_endpoints', []))}개")
        for api in results.get("api_endpoints", [])[:3]:
            print(f"   - {api['method']} {api['endpoint']}")

        # 스크린샷
        screenshots = results.get("screenshots", [])
        print(f"\n6. 저장된 스크린샷: {len(screenshots)}개")
        for ss in screenshots:
            print(f"   - {ss}")


if __name__ == "__main__":
    asyncio.run(main())
