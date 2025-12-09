#!/usr/bin/env python3
"""
호갱노노 사이트 분석 스크립트
- 페이지 구조 파악
- 네트워크 요청 모니터링
- JavaScript 동작 분석
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

from playwright.async_api import async_playwright, Page, BrowserContext
import structlog

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent / "src"))

from crawler.config import CrawlerConfig

# 로거 설정
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.ConsoleRenderer(),
    ]
)
logger = structlog.get_logger()


class HogangnonoAnalyzer:
    """호갱노노 사이트 분석기"""

    def __init__(self):
        self.config = CrawlerConfig.from_env()
        self.network_requests: List[Dict[str, Any]] = []
        self.analysis_results: Dict[str, Any] = {}

    async def analyze_site(self):
        """사이트 전체 분석 수행"""
        logger.info("호갱노노 사이트 분석 시작", url="https://hogangnono.com")

        async with async_playwright() as p:
            # 브라우저 설정
            browser = await p.chromium.launch(
                headless=False,  # 분석을 위해 브라우저 표시
                slow_mo=1000,  # 1초 지연으로 동작 관찰
                args=["--window-size=1920,1080"],
            )

            # 컨텍스트 생성 및 네트워크 요청 모니터링 설정
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            )

            # 분석 실행
            try:
                await self._analyze_main_page(context)
                await self._analyze_search_functionality(context)
                await self._analyze_pagination(context)
                await self._analyze_filters(context)

            except Exception as e:
                logger.error("분석 중 오류 발생", error=str(e))

            finally:
                await browser.close()

        # 분석 결과 저장
        self._save_results()

    async def _analyze_main_page(self, context: BrowserContext):
        """메인 페이지 분석"""
        logger.info("메인 페이지 분석 시작")

        page = await context.new_page()

        # 네트워크 요청 캡처 설정
        requests_log = []

        def handle_request(request):
            requests_log.append(
                {
                    "url": request.url,
                    "method": request.method,
                    "headers": dict(request.headers),
                    "resource_type": request.resource_type,
                    "timestamp": request.timing["requestTime"],
                }
            )
            logger.debug("요청 캡처", url=request.url, method=request.method)

        def handle_response(response):
            if response.request.resource_type in ["xhr", "fetch"]:
                logger.info(
                    "API 응답 캡처",
                    url=response.url,
                    status=response.status,
                    content_type=response.headers.get("content-type", ""),
                )

        page.on("request", handle_request)
        page.on("response", handle_response)

        # 페이지 이동
        await page.goto("https://hogangnono.com", wait_until="networkidle")

        # 페이지 구조 분석
        await self._analyze_page_structure(page)

        # 초기 로드된 데이터 확인
        await self._analyze_initial_data(page)

        self.analysis_results["main_page"] = {
            "title": await page.title(),
            "url": page.url,
            "network_requests": requests_log[:20],  # 처음 20개만 저장
            "structure": await self._get_page_structure(page),
        }

        await page.close()
        logger.info("메인 페이지 분석 완료")

    async def _analyze_search_functionality(self, context: BrowserContext):
        """검색 기능 분석"""
        logger.info("검색 기능 분석 시작")

        page = await context.new_page()
        search_requests = []

        def capture_search_request(request):
            if "api" in request.url.lower() or "search" in request.url.lower():
                search_requests.append(
                    {
                        "url": request.url,
                        "method": request.method,
                        "headers": dict(request.headers),
                        "post_data": request.post_data,
                    }
                )
                logger.info("검색 API 요청 캡처", url=request.url)

        page.on("request", capture_search_request)

        await page.goto("https://hogangnono.com")

        try:
            # 지역 검색 시도
            # 검색 입력창 찾기
            search_input = await page.wait_for_selector(
                'input[placeholder*="지역"], input[placeholder*="검색"], .search-input, #search',
                timeout=10000,
            )

            if search_input:
                logger.info("검색 입력창 발견")

                # 검색어 입력
                await search_input.fill("강남구")
                await page.wait_for_timeout(2000)

                # 자동완성 목록 확인
                autocomplete_items = await page.query_selector_all(
                    ".autocomplete-item, .search-result, .suggestion"
                )

                if autocomplete_items:
                    logger.info("자동완성 목록 발견", count=len(autocomplete_items))
                    # 첫번째 항목 클릭
                    await autocomplete_items[0].click()
                    await page.wait_for_timeout(3000)

        except Exception as e:
            logger.warning("검색 기능 분석 중 오류", error=str(e))

        self.analysis_results["search"] = {
            "requests": search_requests,
            "found_elements": {
                "search_input": bool(search_input if "search_input" in locals() else False),
                "autocomplete": len(autocomplete_items) if "autocomplete_items" in locals() else 0,
            },
        }

        await page.close()
        logger.info("검색 기능 분석 완료")

    async def _analyze_pagination(self, context: BrowserContext):
        """페이지네이션 분석"""
        logger.info("페이지네이션 분석 시작")

        page = await context.new_page()
        pagination_requests = []

        def capture_pagination_request(request):
            if "page" in request.url.lower() or "offset" in request.url.lower():
                pagination_requests.append(
                    {"url": request.url, "method": request.method, "headers": dict(request.headers)}
                )
                logger.info("페이지네이션 요청 캡처", url=request.url)

        page.on("request", capture_pagination_request)

        # 강남구 매물 페이지로 직접 이동 시도
        try:
            await page.goto("https://hogangnono.com/search?region=강남구")
            await page.wait_for_timeout(3000)

            # 페이지네이션 버튼 찾기
            pagination_buttons = await page.query_selector_all(
                ".pagination a, .page-link, [data-page], .page-item"
            )

            if pagination_buttons:
                logger.info("페이지네이션 버튼 발견", count=len(pagination_buttons))

                # 다음 페이지 버튼 클릭 시도
                for button in pagination_buttons:
                    text = await button.text_content()
                    if text and ("다음" in text or "2" in text or ">" in text):
                        logger.info("다음 페이지 버튼 클릭", text=text)
                        await button.click()
                        await page.wait_for_timeout(3000)
                        break

        except Exception as e:
            logger.warning("페이지네이션 분석 중 오류", error=str(e))

        self.analysis_results["pagination"] = {
            "requests": pagination_requests,
            "found_buttons": len(pagination_buttons) if "pagination_buttons" in locals() else 0,
        }

        await page.close()
        logger.info("페이지네이션 분석 완료")

    async def _analyze_filters(self, context: BrowserContext):
        """필터링 옵션 분석"""
        logger.info("필터링 옵션 분석 시작")

        page = await context.new_page()
        filter_requests = []

        def capture_filter_request(request):
            if "filter" in request.url.lower() or any(
                key in request.url.lower() for key in ["price", "type", "size", "floor"]
            ):
                filter_requests.append(
                    {"url": request.url, "method": request.method, "post_data": request.post_data}
                )
                logger.info("필터링 요청 캡처", url=request.url)

        page.on("request", capture_filter_request)

        await page.goto("https://hogangnono.com")
        await page.wait_for_timeout(3000)

        # 필터링 옵션 찾기
        filter_elements = {
            "price_range": await page.query_selector_all(
                'input[name*="price"], .price-filter, [data-filter="price"]'
            ),
            "property_type": await page.query_selector_all(
                'input[name*="type"], .type-filter, [data-filter="type"]'
            ),
            "size_range": await page.query_selector_all(
                'input[name*="size"], .size-filter, [data-filter="size"]'
            ),
            "floor_range": await page.query_selector_all(
                'input[name*="floor"], .floor-filter, [data-filter="floor"]'
            ),
        }

        # 각 필터 옵션 개수 기록
        filter_counts = {k: len(v) for k, v in filter_elements.items()}
        logger.info("발견된 필터 옵션", **filter_counts)

        # 필터링 시도 (매매/전세 타입 필터)
        if filter_elements["property_type"]:
            try:
                # 첫 번째 필터 옵션 클릭
                await filter_elements["property_type"][0].click()
                await page.wait_for_timeout(2000)
                logger.info("매물 유형 필터 클릭")
            except Exception as e:
                logger.warning("필터 클릭 실패", error=str(e))

        self.analysis_results["filters"] = {"requests": filter_requests, "elements": filter_counts}

        await page.close()
        logger.info("필터링 옵션 분석 완료")

    async def _analyze_page_structure(self, page: Page):
        """페이지 구조 분석"""
        structure = {}

        # 메인 네비게이션
        nav_items = await page.query_selector_all("nav a, .navbar a, .gnb a")
        structure["navigation"] = [await item.text_content() for item in nav_items[:10]]

        # 주요 섹션
        sections = await page.query_selector_all("section, .section, main")
        structure["sections"] = len(sections)

        # 리스트 아이템 (매물 목록)
        list_items = await page.query_selector_all(".item, .list-item, .property-item, .card")
        structure["list_items"] = len(list_items)

        # 폼 요소
        forms = await page.query_selector_all("form")
        structure["forms"] = len(forms)

        # JavaScript 실행 확인
        scripts = await page.query_selector_all("script[src]")
        structure["external_scripts"] = len(scripts)

        logger.info("페이지 구조 분석 완료", **structure)

    async def _analyze_initial_data(self, page: Page):
        """초기 로드된 데이터 분석"""
        # localStorage 확인
        local_storage = await page.evaluate("""
            () => {
                const storage = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    storage[key] = localStorage.getItem(key);
                }
                return storage;
            }
        """)

        # sessionStorage 확인
        session_storage = await page.evaluate("""
            () => {
                const storage = {};
                for (let i = 0; i < sessionStorage.length; i++) {
                    const key = sessionStorage.key(i);
                    storage[key] = sessionStorage.getItem(key);
                }
                return storage;
            }
        """)

        # 전역 변수 확인
        global_vars = await page.evaluate("""
            () => {
                const vars = {};
                if (window.__INITIAL_STATE__) vars.__INITIAL_STATE__ = window.__INITIAL_STATE__;
                if (window.__PRELOADED_STATE__) vars.__PRELOADED_STATE__ = window.__PRELOADED_STATE__;
                if (window.hogangnono) vars.hogangnono = window.hogangnono;
                return vars;
            }
        """)

        self.analysis_results["initial_data"] = {
            "local_storage": local_storage,
            "session_storage": session_storage,
            "global_variables": global_vars,
        }

    async def _get_page_structure(self, page: Page) -> Dict[str, Any]:
        """페이지 구조 정보 가져오기"""
        return await page.evaluate("""
            () => {
                return {
                    meta: {
                        title: document.title,
                        description: document.querySelector('meta[name="description"]')?.content,
                        keywords: document.querySelector('meta[name="keywords"]')?.content
                    },
                    api_endpoints: Array.from(document.querySelectorAll('script'))
                        .map(script => {
                            const text = script.textContent || '';
                            const matches = text.match(/https?:\\/\\/[\\w.-]+\\/api\\/[\\w.-]+/g);
                            return matches || [];
                        })
                        .flat()
                        .filter((v, i, a) => a.indexOf(v) === i),
                    forms: Array.from(document.querySelectorAll('form'))
                        .map(form => ({
                            action: form.action,
                            method: form.method,
                            inputs: Array.from(form.querySelectorAll('input, select, textarea'))
                                .map(input => ({
                                    name: input.name,
                                    type: input.type,
                                    required: input.required
                                }))
                        }))
                };
            }
        """)

    def _save_results(self):
        """분석 결과 저장"""
        output_path = Path("output")
        output_path.mkdir(exist_ok=True)

        result_file = output_path / "hogangnono_analysis.json"

        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(self.analysis_results, f, ensure_ascii=False, indent=2, default=str)

        logger.info("분석 결과 저장 완료", file=str(result_file))

        # 주요 발견사항 출력
        self._print_key_findings()

    def _print_key_findings(self):
        """주요 발견사항 출력"""
        print("\n" + "=" * 50)
        print("호갱노노 사이트 분석 결과 요약")
        print("=" * 50)

        # 메인 페이지 정보
        if "main_page" in self.analysis_results:
            main = self.analysis_results["main_page"]
            print("\n1. 메인 페이지 정보:")
            print(f"   - 제목: {main.get('title', 'N/A')}")
            print(f"   - URL: {main.get('url', 'N/A')}")
            print(f"   - 네트워크 요청 수: {len(main.get('network_requests', []))}")

            if main.get("structure", {}).get("api_endpoints"):
                print("   - 발견된 API 엔드포인트:")
                for endpoint in main["structure"]["api_endpoints"][:5]:
                    print(f"     * {endpoint}")

        # 검색 기능
        if "search" in self.analysis_results:
            search = self.analysis_results["search"]
            print("\n2. 검색 기능:")
            print(f"   - 검색 요청 수: {len(search.get('requests', []))}")
            print(
                f"   - 검색 입력창: {'있음' if search.get('found_elements', {}).get('search_input') else '없음'}"
            )
            print(
                f"   - 자동완성 항목 수: {search.get('found_elements', {}).get('autocomplete', 0)}"
            )

        # 페이지네이션
        if "pagination" in self.analysis_results:
            pagination = self.analysis_results["pagination"]
            print("\n3. 페이지네이션:")
            print(f"   - 페이지네이션 요청 수: {len(pagination.get('requests', []))}")
            print(f"   - 페이지네이션 버튼 수: {pagination.get('found_buttons', 0)}")

        # 필터링
        if "filters" in self.analysis_results:
            filters = self.analysis_results["filters"]
            print("\n4. 필터링 옵션:")
            print(f"   - 필터링 요청 수: {len(filters.get('requests', []))}")
            elements = filters.get("elements", {})
            for filter_type, count in elements.items():
                print(f"   - {filter_type}: {count}개")

        # 초기 데이터
        if "initial_data" in self.analysis_results:
            initial = self.analysis_results["initial_data"]
            print("\n5. 초기 데이터:")
            print(f"   - localStorage 항목 수: {len(initial.get('local_storage', {}))}")
            print(f"   - sessionStorage 항목 수: {len(initial.get('session_storage', {}))}")

            if initial.get("global_variables"):
                print("   - 전역 변수:")
                for key, value in initial["global_variables"].items():
                    print(f"     * {key}: {type(value).__name__}")

        print("\n" + "=" * 50)


async def main():
    """메인 함수"""
    analyzer = HogangnonoAnalyzer()
    await analyzer.analyze_site()


if __name__ == "__main__":
    asyncio.run(main())
