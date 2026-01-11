"""네이버 부동산 좌표 기반 검색 크롤러

좌표(위도/경도)와 반경을 사용하여 아파트 단지를 검색합니다.
Mercator projection을 사용하여 지리 좌표를 픽셀로 변환하고,
중심 좌표와 반경으로 경계를 계산합니다.

API 엔드포인트:
- /complexes/single-markers/2.0: 단지 마커 정보 (좌표 기반)
"""

import asyncio
import math
from typing import Any
from urllib.parse import urlencode

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from crawler.dto.naver_listing import NaverAptDTO

# =============================================================================
# 지리 좌표 변환 함수들 (Mercator Projection)
# =============================================================================


def ll_to_pixel(lat: float, lon: float, zoom: float) -> tuple[float, float]:
    """
    위도/경도를 픽셀 좌표로 변환 (Mercator projection).

    Args:
        lat: 위도 (-85 ~ 85)
        lon: 경도 (-180 ~ 180)
        zoom: 줌 레벨 (1 ~ 20)

    Returns:
        (x, y) 픽셀 좌표

    Raises:
        ValueError: 위도가 유효 범위를 벗어날 때
    """
    if abs(lat) > 85:
        raise ValueError(f"위도는 ±85도까지만 유효함: {lat}")

    scale = 256 * (2**zoom)
    x = (lon + 180.0) / 360.0 * scale

    siny = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + siny) / (1 - siny)) / (4 * math.pi)) * scale

    return x, y


def pixel_to_ll(x: float, y: float, zoom: float) -> tuple[float, float]:
    """
    픽셀 좌표를 위도/경도로 변환 (Mercator projection 역변환).

    Args:
        x: 픽셀 X 좌표
        y: 픽셀 Y 좌표
        zoom: 줌 레벨 (1 ~ 20)

    Returns:
        (lat, lon) 위도/경도
    """
    scale = 256 * (2**zoom)

    lon = (x / scale) * 360.0 - 180.0

    n = math.pi - 2.0 * math.pi * y / scale
    lat = (180.0 / math.pi) * math.atan(0.5 * (math.exp(n) - math.exp(-n)))

    return lat, lon


def bounds_from_center(
    lat: float, lon: float, radius_m: float, zoom: float
) -> tuple[float, float, float, float]:
    """
    중심 좌표와 반경으로 지도 경계 계산.

    Args:
        lat: 중심 위도
        lon: 중심 경도
        radius_m: 반경 (미터)
        zoom: 줌 레벨

    Returns:
        (s_lat, s_lng, e_lat, e_lng) 경계 좌표
    """
    # 중심 좌표를 픽셀로 변환
    center_x, center_y = ll_to_pixel(lat, lon, zoom)

    # 위도 방향 반경 (픽셀)
    # 위도 1도의 미터 거리는 적도에서 약 111,320m
    lat_deg_per_meter = 1.0 / 111320.0
    lat_offset_deg = radius_m * lat_deg_per_meter

    # 경도 방향 반경 (픽셀)
    # 경도 1도의 미터 거리는 위도에 따라 다름
    lon_deg_per_meter = 1.0 / (111320.0 * math.cos(math.radians(lat)))
    lon_offset_deg = radius_m * lon_deg_per_meter

    # 경계 좌표 계산
    s_lat = lat - lat_offset_deg
    e_lat = lat + lat_offset_deg
    s_lng = lon - lon_offset_deg
    e_lng = lon + lon_offset_deg

    return s_lat, s_lng, e_lat, e_lng


# =============================================================================
# 네이버 부동산 크롤러 베이스 클래스
# =============================================================================


class _NaverBaseCrawler:
    """네이버 부동산 크롤러 베이스 클래스 - Anti-Bot 공통 기능"""

    BASE_URL = "https://new.land.naver.com"

    def __init__(self, headless: bool = True, block_resources: bool = True):
        """
        Args:
            headless: 헤드리스 모드 여부
            block_resources: 무거운 리소스 차단 여부
        """
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
        await asyncio.sleep(min_sec)  # 간단한 고정 딜레이로 변경

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


# =============================================================================
# 좌표 기반 검색 크롤러
# =============================================================================


class NaverCoordinateSearchCrawler(_NaverBaseCrawler):
    """
    네이버 부동산 좌표 기반 검색 크롤러

    중심 좌표(위도/경도)와 반경을 사용하여
    해당 영역 내의 아파트 단지를 검색합니다.
    """

    def __init__(
        self,
        center_lat: float,
        center_lon: float,
        radius_m: float,
        zoom: int = 15,
        headless: bool = True,
        block_resources: bool = True,
    ):
        """
        Args:
            center_lat: 중심 위도
            center_lon: 중심 경도
            radius_m: 검색 반경 (미터)
            zoom: 줌 레벨 (기본값 15)
            headless: 헤드리스 모드 여부
            block_resources: 무거운 리소스 차단 여부
        """
        super().__init__(headless, block_resources)
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.radius_m = radius_m
        self.zoom = zoom

    async def _search_async(self) -> list[dict[str, Any]]:
        """
        비동기 좌표 기반 검색 수행

        Returns:
            list[dict]: 검색된 단지 정보 리스트
        """
        # 경계 계산
        s_lat, s_lng, e_lat, e_lng = bounds_from_center(
            self.center_lat, self.center_lon, self.radius_m, self.zoom
        )

        # 맵 페이지 URL 생성
        # 네이버 부동산은 ms 파라미터로 중심 좌표와 줌 레벨을 받음
        params = {
            "ms": f"{self.center_lat},{self.center_lon},{self.zoom}",
            "a": "APT",  # 아파트
            "b": "A1",  # 매매
        }
        map_url = f"{self.BASE_URL}/complexes?{urlencode(params)}"

        # 수집한 데이터 저장
        collected_data = []

        async def handle_response(response):
            url = response.url

            # 단지 마커 API 수집 (2.0 버전)
            if "complexes/single-markers/2.0" in url:
                try:
                    data = await response.json()
                    if isinstance(data, list):
                        for item in data:
                            # 모든 단지 수집 (필터링 없음)
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

    def crawl(self) -> list[NaverAptDTO]:
        """
        좌표 기반 아파트 검색 수행

        Returns:
            list[NaverAptDTO]: 검색된 아파트 리스트
        """

        async def _crawl():
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

        return asyncio.run(_crawl())
