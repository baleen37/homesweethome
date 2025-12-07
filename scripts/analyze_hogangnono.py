#!/usr/bin/env python3
"""호갱노노 사이트 분석 스크립트

이 스크립트는 Playwright를 사용하여 호갱노노 사이트를 탐색하고,
UI 구조, 검색 기능, 매물 목록 표시 방식 등을 분석합니다.
"""

import asyncio
import json
import time
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from structlog import get_logger

logger = get_logger()


class HogangnonoAnalyzer:
    """호갱노노 사이트 분석기"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.screenshot_dir = Path("output/hogangnono_screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    async def setup(self) -> None:
        """Playwright 브라우저 설정"""
        self.playwright = await async_playwright().start()

        # 브라우저 실행 (시각적으로 확인을 위해 headless=False)
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=1000,  # 1초 지연으로 실행 과정 확인
        )

        # 컨텍스트 설정 (모바일/데스크톱 전환 가능)
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        # 네트워크 요청 모니터링 설정
        self.page = await self.context.new_page()

        # 네트워크 요청/응답 로깅
        self.page.on("request", self._log_request)
        self.page.on("response", self._log_response)

        logger.info("브라우저 설정 완료")

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

    def _log_request(self, request) -> None:
        """네트워크 요청 로깅"""
        if "/api/" in request.url or "/ajax/" in request.url:
            logger.info("API 요청", url=request.url, method=request.method)

    def _log_response(self, response) -> None:
        """네트워크 응답 로깅"""
        if "/api/" in response.url or "/ajax/" in response.url:
            logger.info("API 응답", url=response.url, status=response.status)

    async def take_screenshot(self, name: str) -> str:
        """스크린샷 저장"""
        if self.page:
            screenshot_path = self.screenshot_dir / f"{name}_{int(time.time())}.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info("스크린샷 저장", path=str(screenshot_path))
            return str(screenshot_path)
        return ""

    async def analyze_homepage(self) -> None:
        """메인페이지 분석"""
        logger.info("=== 메인페이지 분석 시작 ===")

        # 사이트 접속 (더 관대한 타임아웃 설정)
        try:
            await self.page.goto(
                "https://hogangnono.com", wait_until="domcontentloaded", timeout=60000
            )
            await asyncio.sleep(5)  # 페이지 로딩 대기
        except Exception as e:
            logger.warning("networkidle 타임아웃, domcontentloaded로 재시도", error=str(e))
            await self.page.goto("https://hogangnono.com", wait_until="domcontentloaded")
            await asyncio.sleep(5)

        # 스크린샷
        await self.take_screenshot("homepage")

        # 페이지 제목 및 기본 정보
        title = await self.page.title()
        url = self.page.url
        logger.info("페이지 정보", title=title, url=url)

        # 메인 UI 요소 분석
        ui_elements = {
            "search_bar": 'input[placeholder*="검색"], input[placeholder*="지역"]',
            "region_buttons": 'button[data-region], [class*="region"], [class*="area"]',
            "trade_type_tabs": 'button[data-trade], [class*="tab"], [class*="trade"]',
            "filter_options": '[class*="filter"], select, input[type="checkbox"]',
            "property_list": '[class*="list"], [class*="items"], [class*="properties"]',
        }

        for element_name, selector in ui_elements.items():
            elements = await self.page.query_selector_all(selector)
            logger.info(f"{element_name} 요소", count=len(elements))

    async def analyze_search(self, region: str = "강남구") -> None:
        """지역 검색 기능 분석"""
        logger.info(f"=== 지역 검색 분석: {region} ===")

        try:
            # 검색창 찾기
            search_selectors = [
                'input[placeholder*="지역"]',
                'input[placeholder*="검색"]',
                "#searchInput",
                ".search-input",
                'input[type="search"]',
            ]

            search_input = None
            for selector in search_selectors:
                search_input = await self.page.query_selector(selector)
                if search_input:
                    logger.info("검색창 발견", selector=selector)
                    break

            if not search_input:
                # 검색창이 없다면 지역 버튼 클릭 시도
                logger.info("검색창 없음, 지역 버튼 탐색")
                region_selectors = [
                    f'button:has-text("{region}")',
                    f'[data-region*="{region}"]',
                    f'a:has-text("{region}")',
                ]

                for selector in region_selectors:
                    element = await self.page.query_selector(selector)
                    if element:
                        logger.info("지역 버튼 클릭", selector=selector)
                        await element.click()
                        await asyncio.sleep(2)
                        await self.take_screenshot(f"after_click_{region}")
                        break
            else:
                # 검색창에 지역 입력
                await search_input.fill(region)
                await asyncio.sleep(1)

                # 자동완성 또는 검색 버튼 클릭
                search_button = await self.page.query_selector('button[type="submit"], .search-btn')
                if search_button:
                    await search_button.click()
                else:
                    await self.page.press(search_input, "Enter")

                await asyncio.sleep(3)
                await self.take_screenshot(f"search_result_{region}")

        except Exception as e:
            logger.error("검색 중 오류 발생", error=str(e))
            await self.take_screenshot("search_error")

    async def analyze_property_list(self) -> None:
        """매물 목록 분석"""
        logger.info("=== 매물 목록 분석 ===")

        try:
            # 매물 목록 컨테이너 찾기
            list_selectors = [
                '[class*="property-list"]',
                '[class*="item-list"]',
                '[class*="article"]',
                ".list-container",
                "ul.items",
                "[data-list]",
            ]

            list_container = None
            for selector in list_selectors:
                list_container = await self.page.query_selector(selector)
                if list_container:
                    logger.info("매물 목록 발견", selector=selector)
                    break

            if list_container:
                # 매물 아이템 분석
                items = await list_container.query_selector_all('[class*="item"], li, [data-item]')
                logger.info("매물 개수", count=len(items))

                if items:
                    # 첫 번째 매물 분석
                    first_item = items[0]

                    # 가격 정보
                    price_elements = await first_item.query_selector_all(
                        '[class*="price"], [class*="cost"]'
                    )
                    for price_el in price_elements:
                        price_text = await price_el.text_content()
                        logger.info("가격 정보", price=price_text.strip() if price_text else "")

                    # 매물 정보
                    info_elements = await first_item.query_selector_all(
                        '[class*="info"], [class*="detail"]'
                    )
                    for info_el in info_elements:
                        info_text = await info_el.text_content()
                        logger.info("매물 정보", info=info_text.strip() if info_text else "")

                    # 첫 번째 매물 클릭
                    await first_item.click()
                    await asyncio.sleep(3)
                    await self.take_screenshot("property_detail")

        except Exception as e:
            logger.error("매물 목록 분석 중 오류", error=str(e))

    async def analyze_filters(self) -> None:
        """필터 옵션 분석"""
        logger.info("=== 필터 옵션 분석 ===")

        try:
            # 매매/전세/월세 탭
            trade_selectors = [
                '[class*="tab"] button',
                "[data-trade]",
                ".trade-type button",
                ".filter-tabs button",
            ]

            for selector in trade_selectors:
                tabs = await self.page.query_selector_all(selector)
                if tabs:
                    for tab in tabs:
                        tab_text = await tab.text_content()
                        logger.info("거래유형 탭", type=tab_text.strip() if tab_text else "")

            # 기타 필터
            filter_selectors = [
                "select",
                'input[type="checkbox"]',
                'input[type="radio"]',
                ".filter-option",
            ]

            for selector in filter_selectors:
                filters = await self.page.query_selector_all(selector)
                if filters:
                    logger.info(f"필터 요소 ({selector})", count=len(filters))

        except Exception as e:
            logger.error("필터 분석 중 오류", error=str(e))

    async def analyze_api_requests(self) -> list:
        """API 요청 분석"""
        logger.info("=== API 요청 분석 ===")

        api_requests = []

        # 이미 발생한 요청들로부터 API URL 수집
        # network_requests = (
        #     await self.context.request_counts()
        # )  # Note: 이 메서드는 실제로는 존재하지 않을 수 있음

        # 페이지에서 API URL 수집
        api_urls = await self.page.evaluate("""
        Array.from(document.querySelectorAll('script'))
            .map(script => script.textContent || '')
            .join(' ')
            .match(/https:\\/\\/hogangnono\\.com\\/api[^\"'\\s]*/g) || []
        """)

        if api_urls:
            api_requests.extend(api_urls)
            logger.info("페이지에서 발견된 API URL", urls=api_urls[:5])  # 처음 5개만 로깅

        # 현재까지의 네트워크 요청에서 API 추출
        # Playwright의 실제 구현에서는 request 이벤트를 통해 수집

        return api_requests

    async def run_analysis(self) -> dict:
        """전체 분석 실행"""
        results = {"screenshots": [], "ui_elements": {}, "api_endpoints": []}

        try:
            await self.setup()

            # 1. 메인페이지 분석
            await self.analyze_homepage()

            # 2. 지역 검색
            await self.analyze_search("강남구")

            # 3. 매물 목록 분석
            await self.analyze_property_list()

            # 4. 필터 분석
            await self.analyze_filters()

            # 5. 네트워크 분석 준비
            await self.analyze_api_requests()

            logger.info("분석 완료")

        except Exception as e:
            logger.error("분석 중 오류 발생", error=str(e))

        finally:
            await self.cleanup()

        return results


async def main():
    """메인 함수"""
    analyzer = HogangnonoAnalyzer(headless=False)  # 시각적으로 확인하기 위해 headless=False
    results = await analyzer.run_analysis()

    # 결과 저장
    output_path = Path("output/hogangnono_analysis.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info("분석 결과 저장", path=str(output_path))


if __name__ == "__main__":
    asyncio.run(main())
