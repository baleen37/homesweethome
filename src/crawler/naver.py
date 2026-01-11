"""네이버 부동산 크롤러 - Anti-Bot 우회 기술 적용

anti_bot_scraper (HarimxChoi/anti_bot_scraper)에서 학습한 기법 적용:
- Webdriver 속성 숨기기
- 리소스 차단 (이미지, 폰트, 미디어)
- 적절한 헤더 설정 (Referer, Accept-Language)
- 랜덤 딜레이
- 사람처럼 보이는 마우스 이동

API 엔드포인트:
- /complexes/single-markers: 단지 마커 정보
- /api/articles/complex/{complex_no}: 단지별 매물 리스트
"""

import asyncio
import random
import re
from typing import Any
from urllib.parse import urlencode

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from crawler.dto.naver_listing import NaverAptDTO, NaverListingDTO


class _NaverBaseCrawler:
    """네이버 부동산 크롤러 베이스 클래스 - Anti-Bot 공통 기능"""

    BASE_URL = "https://new.land.naver.com"

    def __init__(
        self,
        headless: bool = True,
        block_resources: bool = True,
        page: Page | None = None,
    ):
        """
        Args:
            headless: 헤드리스 모드 여부
            block_resources: 무거운 리소스 차단 여부
            page: 외부에서 생성한 Playwright Page 객체 (테스트용 공유 브라우저)
        """
        self.headless = headless
        self.block_resources = block_resources
        self.playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page = page  # 외부에서 제공된 page가 있으면 사용

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        # 외부에서 제공된 page가 없으면 새로 생성
        if self.page is None:
            self.playwright = await async_playwright().start()
            await self._setup_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        # 외부에서 제공된 page가 없으면 자원 정리
        if self.page is None:
            await self._close()

    async def _setup_browser(self):
        """브라우저 설정 - Anti-Bot 우회 기술 적용"""
        # 브라우저 시작
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
        )

        # 컨텍스트 생성
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="ko-KR",
            extra_http_headers={
                "Referer": "https://new.land.naver.com/",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        )

        # 리소스 차단 설정
        if self.block_resources:
            await self._setup_resource_blocking()

        # 페이지 생성
        self.page = await self.context.new_page()

        # Webdriver 속성 숨기기 (Anti-Bot 핵심)
        await self.page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )

    async def _setup_resource_blocking(self):
        """
        무거운 리소스 차단 설정

        효과:
        - 페이지 로딩 속도 2-3배 향상
        - 네트워크 대역폭 절약
        - 봇 탐지에는 영향 없음 (오히려 자연스러움 - 광고 차단 사용자처럼)
        """

        async def _route(route):
            resource_type = route.request.resource_type
            if resource_type in ("image", "media", "font"):
                await route.abort()
            else:
                await route.continue_()

        await self.context.route("**/*", _route)

    async def _random_delay(self, min_sec: float = 0.5, max_sec: float = 1.5):
        """랜덤 딜레이 - 사람처럼 보이기 위해"""
        await asyncio.sleep(random.uniform(min_sec, max_sec))

    async def _human_like_mouse_move(self, x: int, y: int, steps: int = 20):
        """
        사람처럼 마우스 이동

        Args:
            x: 목표 X 좌표
            y: 목표 Y 좌표
            steps: 이동 단계 수 (20단계로 부드럽게 이동)
        """
        await self.page.mouse.move(x, y, steps=steps)

    async def _close(self):
        """브라우저 종료"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    def _parse_price(self, price_str: str) -> int | None:
        """
        한국어 가격 표기를 숫자로 변환

        Args:
            price_str: 가격 문자열 (예: "3억 8,000만원", "85000")

        Returns:
            int: 가격 (원 단위)
        """
        if not price_str:
            return None

        # 쉼표, 공백, 원 제거
        price_str = price_str.replace(",", "").replace(" ", "").replace("원", "")

        # 억 단위 처리
        eok_match = re.search(r"(\d+(?:\.\d+)?)억", price_str)
        total = 0
        if eok_match:
            total += int(float(eok_match.group(1)) * 100_000_000)

        # 만 단위 처리
        man_match = re.search(r"(\d+)만", price_str)
        if man_match:
            total += int(man_match.group(1)) * 10_000

        # 억도 만도 없는 경우 (예: "85000" = 8억 5천)
        if total == 0 and price_str.isdigit():
            # 만원 단위로 가정
            total = int(price_str) * 10_000

        return total if total > 0 else None


class NaverSearchCrawler(_NaverBaseCrawler):
    """
    네이버 부동산 아파트 검색 크롤러

    아파트 이름으로 검색하여 단지 정보를 수집합니다.
    """

    def __init__(
        self,
        keyword: str,
        headless: bool = True,
        block_resources: bool = True,
        page: Page | None = None,
    ):
        """
        Args:
            keyword: 검색 키워드 (아파트 이름)
            headless: 헤드리스 모드 여부
            block_resources: 무거운 리소스 차단 여부
            page: 외부에서 생성한 Playwright Page 객체 (테스트용 공유 브라우저)
        """
        super().__init__(headless, block_resources, page)
        self.keyword = keyword

    async def _search_async(self) -> list[dict[str, Any]]:
        """
        비동기 검색 수행

        Returns:
            list[dict]: 검색된 단지 정보 리스트
        """
        # 맵 페이지 URL 생성 (서울시청 근처)
        params = {
            "ms": "37.5665,126.9780,15",  # 서울시청 좌표
            "a": "APT",  # 아파트
            "b": "A1",  # 매매
        }
        map_url = f"{self.BASE_URL}/complexes?{urlencode(params)}"

        # 수집한 데이터 저장
        collected_data = []

        async def handle_response(response):
            url = response.url

            # 단지 마커 API 수집
            if "complexes/single-markers" in url:
                try:
                    data = await response.json()
                    if isinstance(data, list):
                        for item in data:
                            # 검색어와 일치하는 단지만 필터링
                            name = item.get("complexName", "")
                            if self.keyword in name:
                                collected_data.append(item)
                except Exception:
                    pass

        # 리스너 등록 (페이지 접속 전에 등록해야 함)
        self.page.on("response", handle_response)

        # 페이지 접속
        await self.page.goto(map_url, wait_until="domcontentloaded")
        await self._random_delay(1, 2)

        # 맵 캔버스 대기
        try:
            await self.page.wait_for_selector("canvas", timeout=10000)
        except Exception:
            pass

        # 사람처럼 마우스 이동
        await self._human_like_mouse_move(960, 540)
        await self._random_delay(0.5, 1)

        # 약간의 스크롤로 API 트리거
        await self.page.mouse.wheel(0, -60)
        await asyncio.sleep(2)

        # 리스너 제거
        self.page.remove_listener("response", handle_response)

        return collected_data

    async def crawl_async(self) -> list[NaverAptDTO]:
        """
        아파트 검색 수행 (비동기 버전)

        테스트에서 공유 브라우저를 사용할 때 사용합니다.

        Returns:
            list[NaverAptDTO]: 검색된 아파트 리스트
        """
        # 빈 검색어 처리 (빈 문자열 또는 공백만)
        if not self.keyword or not self.keyword.strip():
            return []

        async with self:
            data = await self._search_async()

            # DTO 변환
            results = []
            for item in data:
                complex_no = item.get("markerId") or item.get("complexNo", "")
                if complex_no:
                    apt = NaverAptDTO(
                        complex_no=str(complex_no),
                        complex_name=item.get("complexName", ""),
                        article_count=item.get("articleCount", 0),
                        latitude=item.get("lat"),
                        longitude=item.get("lng"),
                        address=item.get("address"),
                    )
                    results.append(apt)

            return results

    def crawl(self) -> list[NaverAptDTO]:
        """
        아파트 검색 수행

        Returns:
            list[NaverAptDTO]: 검색된 아파트 리스트
        """
        return asyncio.run(self.crawl_async())


class NaverComplexInfoCrawler(_NaverBaseCrawler):
    """
    네이버 부동산 단지 상세 정보 크롤러

    특정 단지의 상세 정보를 수집합니다.
    """

    def __init__(
        self,
        complex_no: str,
        headless: bool = True,
        block_resources: bool = True,
        page: Page | None = None,
    ):
        """
        Args:
            complex_no: 단지 번호
            headless: 헤드리스 모드 여부
            block_resources: 무거운 리소스 차단 여부
            page: 외부에서 생성한 Playwright Page 객체 (테스트용 공유 브라우저)
        """
        super().__init__(headless, block_resources, page)
        self.complex_no = complex_no

    async def _get_complex_info_async(self) -> dict[str, Any] | None:
        """
        비동기 단지 정보 수집

        Returns:
            dict | None: 단지 정보
        """
        # 단지 상세 페이지
        detail_url = f"{self.BASE_URL}/complexes/{self.complex_no}"

        response_data = None

        async def handle_response(response):
            nonlocal response_data
            if f"/complexes/{self.complex_no}" in response.url and response.request.method == "GET":
                try:
                    # API 응답 확인
                    if "complexes" in response.url:
                        data = await response.json()
                        response_data = data
                except Exception:
                    pass

        # 리스너 등록 (페이지 접속 전에 등록)
        self.page.on("response", handle_response)

        # 페이지 접속
        await self.page.goto(detail_url, wait_until="domcontentloaded")
        await self._random_delay()

        # 대기
        await asyncio.sleep(2)

        # 리스너 제거
        self.page.remove_listener("response", handle_response)

        return response_data

    async def crawl_async(self) -> dict[str, Any] | None:
        """
        단지 상세 정보 수집 (비동기 버전)

        테스트에서 공유 브라우저를 사용할 때 사용합니다.

        Returns:
            dict | None: 단지 정보
        """
        async with self:
            return await self._get_complex_info_async()

    def crawl(self) -> dict[str, Any] | None:
        """
        단지 상세 정보 수집

        Returns:
            dict | None: 단지 정보
        """
        return asyncio.run(self.crawl_async())


class NaverListingsCrawler(_NaverBaseCrawler):
    """
    네이버 부동산 매물 목록 크롤러

    특정 단지의 매물 목록을 수집합니다.
    """

    def __init__(
        self,
        complex_no: str,
        headless: bool = True,
        block_resources: bool = True,
        page: Page | None = None,
    ):
        """
        Args:
            complex_no: 단지 번호
            headless: 헤드리스 모드 여부
            block_resources: 무거운 리소스 차단 여부
            page: 외부에서 생성한 Playwright Page 객체 (테스트용 공유 브라우저)
        """
        super().__init__(headless, block_resources, page)
        self.complex_no = complex_no

    async def _get_listings_async(self) -> list[dict[str, Any]]:
        """
        비동기 매물 목록 수집

        Returns:
            list[dict]: 매물 정보 리스트
        """
        # 단지 상세 페이지
        detail_url = f"{self.BASE_URL}/complexes/{self.complex_no}"

        response_data = []

        async def handle_response(response):
            if "/api/articles/complex/" in response.url:
                try:
                    data = await response.json()
                    response_data.append(data)
                except Exception:
                    pass

        # 리스너 등록 (페이지 접속 전에 등록)
        self.page.on("response", handle_response)

        # 페이지 접속
        await self.page.goto(detail_url, wait_until="domcontentloaded")
        await asyncio.sleep(1)

        # 매물 탭 클릭 - 명시적인 타임아웃과 함께
        try:
            await self.page.locator('button:has-text("매매")').first.click(timeout=5000)
            await asyncio.sleep(1)
        except Exception:
            pass

        # API 응답을 충분히 기다림
        await asyncio.sleep(3)

        # 리스너 제거
        self.page.remove_listener("response", handle_response)

        return response_data

    async def crawl_async(self) -> list[NaverListingDTO]:
        """
        매물 목록 수집 (비동기 버전)

        테스트에서 공유 브라우저를 사용할 때 사용합니다.

        Returns:
            list[NaverListingDTO]: 매물 리스트
        """
        async with self:
            data = await self._get_listings_async()

            # 결과 파싱
            listings = []

            for response in data:
                articles = response.get("articleList", response.get("articles", []))
                if not isinstance(articles, list):
                    continue

                for article in articles:
                    # 매매만 필터링
                    trade_type = article.get("tradeType", "")
                    trade_name = article.get("tradeTypeName", "")

                    if trade_type != "A1" and trade_name != "매매":
                        continue

                    listing = NaverListingDTO(
                        article_no=str(article.get("articleNo", "")),
                        complex_name=article.get("articleName", ""),
                        complex_no=self.complex_no,
                        trade_type=trade_name,
                        deal_price=self._parse_price(article.get("dealOrWarrantPrc", "")),
                        floor_info=article.get("floorInfo", ""),
                        area1=article.get("area1"),
                        area2=article.get("area2"),
                        direction=article.get("direction", ""),
                        description=article.get("articleFeatureDesc", ""),
                        confirm_date=article.get("articleConfirmYmd"),
                    )
                    listings.append(listing)

            return listings

    def crawl(self) -> list[NaverListingDTO]:
        """
        매물 목록 수집

        Returns:
            list[NaverListingDTO]: 매물 리스트
        """
        return asyncio.run(self.crawl_async())
