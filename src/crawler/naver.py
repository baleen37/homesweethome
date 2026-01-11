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
from urllib.parse import urlencode

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from crawler.dto.naver_listing import NaverAptDTO, NaverListingDTO, NaverSearchResultDTO


class NaverListingCrawler:
    """
    네이버 부동산 매물 크롤러

    Anti-Bot 우회 기술:
    1. Webdriver 속성 숨기기
    2. 리소스 차단 (이미지, 폰트, 미디어)
    3. 적절한 헤더 설정
    4. 랜덤 딜레이
    5. 사람처럼 보이는 마우스 이동
    """

    BASE_URL = "https://new.land.naver.com"
    MOBILE_BASE_URL = "https://m.land.naver.com"

    def __init__(
        self,
        keyword: str = "래미안",
        headless: bool = True,
        block_resources: bool = True,
    ):
        """
        Args:
            keyword: 검색 키워드 (아파트 이름)
            headless: 헤드리스 모드 여부
            block_resources: 무거운 리소스 차단 여부
        """
        self.keyword = keyword
        self.headless = headless
        self.block_resources = block_resources
        self.playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.playwright = await async_playwright().start()
        await self._setup_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
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
                "Referer": "https://land.naver.com/",
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

    async def search_apartments(self) -> NaverSearchResultDTO:
        """
        아파트 검색 - 맵 기반 접근 방식

        Returns:
            NaverSearchResultDTO: 검색 결과
        """
        result = NaverSearchResultDTO()

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
                                collected_data.append(("marker", item))
                except Exception:
                    pass

            # 매물 리스트 API 수집
            elif "/api/articles/complex/" in url:
                try:
                    data = await response.json()
                    collected_data.append(("articles", data))
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

        # 결과 파싱
        for data_type, data in collected_data:
            if data_type == "marker":
                if isinstance(data, dict):
                    complex_no = data.get("markerId") or data.get("complexNo", "")
                    if complex_no:
                        apt = NaverAptDTO(
                            complex_no=str(complex_no),
                            complex_name=data.get("complexName", ""),
                            article_count=data.get("articleCount", 0),
                            latitude=data.get("lat"),
                            longitude=data.get("lng"),
                            address=data.get("address"),
                        )
                        result.apartments.append(apt)

        result.total_count = len(result.apartments)
        return result

    async def get_listings(self, complex_no: str) -> list[NaverListingDTO]:
        """
        특정 단지의 매물 목록 조회

        Args:
            complex_no: 단지 번호

        Returns:
            list[NaverListingDTO]: 매물 목록
        """
        # 단지 상세 페이지
        detail_url = f"{self.BASE_URL}/complexes/{complex_no}"

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
        await self._random_delay()

        # 매물 탭 클릭 시도
        try:
            await self.page.locator('button:has-text("매매")').first.click()
            await self._random_delay()
        except Exception:
            pass

        # 대기
        await asyncio.sleep(2)

        # 리스너 제거
        self.page.remove_listener("response", handle_response)

        # 결과 파싱
        listings = []

        for data in response_data:
            articles = data.get("articleList", data.get("articles", []))
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
                    complex_no=complex_no,
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

    def crawl(self) -> NaverSearchResultDTO:
        """
        동기 크롤링 메서드

        Returns:
            NaverSearchResultDTO: 크롤링 결과
        """

        async def _crawl():
            async with self:
                # 검색
                result = await self.search_apartments()

                # 각 단지의 매물 조회
                for apt in result.apartments[:3]:  # 테스트를 위해 3개만
                    listings = await self.get_listings(apt.complex_no)
                    result.listings.extend(listings)

                return result

        return asyncio.run(_crawl())
