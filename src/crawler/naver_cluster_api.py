"""네이버 부동산 Cluster API 클라이언트

Cluster API는 모바일 네이버 부동산의 매물 목록 API입니다.
- Endpoint: https://m.land.naver.com/cluster/ajax/articleList
- Method: GET
- 주요 기능: 지도 경계 내 매물 조회, 필터링, 페이지네이션
"""

import random
import time
from urllib.parse import urlencode

import requests
from playwright.sync_api import sync_playwright
from pydantic import BaseModel, Field

from crawler.dto.naver_article import NaverArticleItemDTO


class NaverClusterResponseDTO(BaseModel):
    """Cluster API 응답 DTO"""

    code: str = Field(description="응답 코드")
    has_paid_presale: bool = Field(description="유료 분양 존재 여부")
    more: bool = Field(description="다음 페이지 존재 여부")
    zoom: int = Field(description="줌 레벨")
    page: int = Field(description="현재 페이지 번호")
    articles: list[NaverArticleItemDTO] = Field(default_factory=list, description="매물 목록")


class NaverClusterAPIClient:
    """
    네이버 부동산 Cluster API 클라이언트

    모바일 네이버 부동산의 매물 목록 API를 호출합니다.
    """

    BASE_URL = "https://m.land.naver.com"
    ENDPOINT = "/cluster/ajax/articleList"
    ABUSE_DETECTION_PATH = "/error/abuse"

    # Rate limiting: 5~10초 사이 랜덤 딜레이
    MIN_DELAY_SECONDS = 5.0
    MAX_DELAY_SECONDS = 10.0

    # 기본 User-Agent
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/16.0 Mobile/15E148 Safari/604.1"
    )

    def __init__(
        self,
        lat: float,
        lon: float,
        bottom: float,
        left: float,
        top: float,
        right: float,
        cortar_no: str | None = None,
        rlet_tp_cd: str | None = None,
        trad_tp_cd: str | None = None,
        spc_min: int | None = None,
        spc_max: int | None = None,
        dprc_min: int | None = None,
        dprc_max: int | None = None,
        zoom: int = 13,
    ):
        """
        Args:
            lat: 중심 위도
            lon: 중심 경도
            bottom: 지도 경계 남쪽 좌표
            left: 지도 경계 서쪽 좌표
            top: 지도 경계 북쪽 좌표
            right: 지도 경계 동쪽 좌표
            cortar_no: 법정동코드
            rlet_tp_cd: 부동산유형코드 (A01:A02 - 아파트:오피스텔)
            trad_tp_cd: 거래유형코드 (A1:B1:B2 - 매매:전세:월세)
            spc_min: 최소 면적 (㎡)
            spc_max: 최대 면적 (㎡)
            dprc_min: 최소 매매가 (만원)
            dprc_max: 최대 매매가 (만원)
            zoom: 줌 레벨 (기본값 13)
        """
        self.lat = lat
        self.lon = lon
        self.bottom = bottom
        self.left = left
        self.top = top
        self.right = right
        self.cortar_no = cortar_no
        self.rlet_tp_cd = rlet_tp_cd
        self.trad_tp_cd = trad_tp_cd
        self.spc_min = spc_min
        self.spc_max = spc_max
        self.dprc_min = dprc_min
        self.dprc_max = dprc_max
        self.zoom = zoom

    def build_url(self, page: int = 1, **kwargs) -> str:
        """
        API 요청 URL 빌드

        Args:
            page: 페이지 번호 (기본값 1)
            **kwargs: 추가 파라미터 (클라이언트 설정 오버라이드)

        Returns:
            str: 완전한 API URL
        """
        # 기본 파라미터 - float은 format을 사용하여 소수점 자릿수 유지
        params = {
            "z": str(kwargs.get("zoom", self.zoom)),
            "lat": f"{kwargs.get('lat', self.lat):.4f}",
            "lon": f"{kwargs.get('lon', self.lon):.4f}",
            "btm": f"{kwargs.get('bottom', self.bottom):.4f}",
            "lft": f"{kwargs.get('left', self.left):.4f}",
            "top": f"{kwargs.get('top', self.top):.4f}",
            "rgt": f"{kwargs.get('right', self.right):.4f}",
            "page": str(page),
        }

        # 필터 파라미터 추가 (선택적)
        cortar_no = kwargs.get("cortar_no", self.cortar_no)
        if cortar_no:
            params["cortarNo"] = cortar_no

        rlet_tp_cd = kwargs.get("rlet_tp_cd", self.rlet_tp_cd)
        if rlet_tp_cd:
            params["rletTpCd"] = rlet_tp_cd

        trad_tp_cd = kwargs.get("trad_tp_cd", self.trad_tp_cd)
        if trad_tp_cd:
            params["tradTpCd"] = trad_tp_cd

        spc_min = kwargs.get("spc_min", self.spc_min)
        if spc_min is not None:
            params["spcMin"] = str(spc_min)

        spc_max = kwargs.get("spc_max", self.spc_max)
        if spc_max is not None:
            params["spcMax"] = str(spc_max)

        dprc_min = kwargs.get("dprc_min", self.dprc_min)
        if dprc_min is not None:
            params["dprcMin"] = str(dprc_min)

        dprc_max = kwargs.get("dprc_max", self.dprc_max)
        if dprc_max is not None:
            params["dprcMax"] = str(dprc_max)

        return f"{self.BASE_URL}{self.ENDPOINT}?{urlencode(params)}"

    def fetch(self, url: str) -> dict:
        """
        HTTP GET 요청

        Rate limiting을 적용하고, Abuse 페이지 감지 시 Playwright로 우회합니다.

        Args:
            url: 요청 URL

        Returns:
            dict: 응답 JSON 데이터

        Raises:
            ValueError: JSON 파싱에 실패하고 HTML 응답인 경우
        """
        # Rate limiting: 랜덤 딜레이 적용
        delay = random.uniform(self.MIN_DELAY_SECONDS, self.MAX_DELAY_SECONDS)
        time.sleep(delay)

        headers = {
            "User-Agent": self.DEFAULT_USER_AGENT,
            "Referer": "https://m.land.naver.com/",
            "Accept": "application/json, text/plain, */*",
        }

        try:
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            response.raise_for_status()

            # Abuse 페이지 감지 (URL 리다이렉트 확인)
            if self.ABUSE_DETECTION_PATH in response.url:
                return self._fetch_with_playwright(url)

            # JSON 파싱 시도
            try:
                return response.json()
            except requests.JSONDecodeError as e:
                # JSON 파싱 실패 시 HTML 응답 확인
                content_type = response.headers.get("Content-Type", "")
                text_preview = response.text[:500] if response.text else ""

                # HTML 응답인 경우 abuse 감지
                if "text/html" in content_type or "<html" in text_preview.lower():
                    # Abuse 페이지 HTML인지 확인
                    if "abuse" in text_preview.lower() or self.ABUSE_DETECTION_PATH in text_preview:
                        return self._fetch_with_playwright(url)

                # 그 외의 경우 명확한 에러 메시지와 함께 재시도
                raise ValueError(
                    f"JSON 파싱 실패 (Content-Type: {content_type}). 응답 미리보기: {text_preview}"
                ) from e

        except requests.RequestException:
            # 요청 실패 시 Playwright 우회 시도
            return self._fetch_with_playwright(url)

    def _fetch_with_playwright(self, url: str) -> dict:
        """
        Playwright로 Abuse 페이지 우회 후 API 요청

        Args:
            url: 요청 URL

        Returns:
            dict: 응답 JSON 데이터

        Raises:
            ValueError: Playwright 우회 후에도 JSON 파싱에 실패한 경우
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=self.DEFAULT_USER_AGENT,
                viewport={"width": 375, "height": 667},  # iPhone SE 사이즈
            )
            page = context.new_page()

            try:
                # 메인 페이지 방문으로 쿠키 획득
                page.goto("https://m.land.naver.com/", wait_until="networkidle")

                # 쿠키 추출
                cookies = context.cookies()

                # 쿠키로 requests 세션 생성 후 재시도
                session = requests.Session()
                session.headers.update(
                    {
                        "User-Agent": self.DEFAULT_USER_AGENT,
                        "Referer": "https://m.land.naver.com/",
                        "Accept": "application/json, text/plain, */*",
                    }
                )

                for cookie in cookies:
                    session.cookies.set(cookie["name"], cookie["value"])

                response = session.get(url, timeout=10, allow_redirects=True)
                response.raise_for_status()

                # JSON 파싱 시도
                try:
                    return response.json()
                except requests.JSONDecodeError as e:
                    # Playwright 우회 후에도 JSON 파싱 실패 시
                    content_type = response.headers.get("Content-Type", "")
                    text_preview = response.text[:500] if response.text else ""

                    # 여전히 HTML/abuse 응답인 경우
                    if "text/html" in content_type or "<html" in text_preview.lower():
                        if (
                            "abuse" in text_preview.lower()
                            or self.ABUSE_DETECTION_PATH in text_preview
                        ):
                            raise ValueError(
                                f"Playwright 우회 후에도 abuse 감지. "
                                f"Content-Type: {content_type}, "
                                f"응답 미리보기: {text_preview}"
                            ) from e

                    # 그 외의 JSON 파싱 실패
                    raise ValueError(
                        f"Playwright 우회 후 JSON 파싱 실패. "
                        f"Content-Type: {content_type}, "
                        f"응답 미리보기: {text_preview}"
                    ) from e

            finally:
                browser.close()

    def parse_article_item(self, item_dict: dict) -> NaverArticleItemDTO:
        """
        매물 아이템 파싱

        Args:
            item_dict: API 응답의 개별 매물 딕셔너리

        Returns:
            NaverArticleItemDTO: 파싱된 매물 정보
        """
        return NaverArticleItemDTO(
            atcl_no=item_dict.get("atclNo", ""),
            cortar_no=item_dict.get("cortarNo", ""),
            atcl_nm=item_dict.get("atclNm", ""),
            atcl_stat_cd=item_dict.get("atclStatCd", ""),
            rlet_tp_cd=item_dict.get("rletTpCd", ""),
            rlet_tp_nm=item_dict.get("rletTpNm", ""),
            trad_tp_cd=item_dict.get("tradTpCd", ""),
            trad_tp_nm=item_dict.get("tradTpNm", ""),
            prc=item_dict.get("prc"),
            rent_prc=item_dict.get("rentPrc"),
            flr_info=item_dict.get("flrInfo", ""),
            spc1=item_dict.get("spc1", ""),
            spc2=item_dict.get("spc2", ""),
            direction=item_dict.get("direction"),
            atcl_cfm_ymd=item_dict.get("atclCfmYmd"),
            lat=item_dict.get("lat"),
            lng=item_dict.get("lng"),
            atcl_fetr_desc=item_dict.get("atclFetrDesc", ""),
            tag_list=item_dict.get("tagList", []),
            bild_nm=item_dict.get("bildNm", ""),
        )

    def parse_response(self, response_json: dict) -> NaverClusterResponseDTO:
        """
        Cluster API 응답 파싱

        Args:
            response_json: API 응답 JSON 딕셔너리

        Returns:
            NaverClusterResponseDTO: 파싱된 응답 정보
        """
        # body 리스트의 각 아이템을 NaverArticleItemDTO로 변환
        articles = []
        for item in response_json.get("body", []):
            try:
                article = self.parse_article_item(item)
                articles.append(article)
            except Exception:
                # 파싱 실패 시 건너뜀
                continue

        return NaverClusterResponseDTO(
            code=response_json.get("code", ""),
            has_paid_presale=response_json.get("hasPaidPreSale", False),
            more=response_json.get("more", False),
            zoom=response_json.get("z", 0),
            page=response_json.get("page", 1),
            articles=articles,
        )


# =============================================================================
# 모듈 레벨 헬퍼 함수 (테스트에서 직접 호출용)
# =============================================================================


def build_cluster_url(
    zoom: int,
    lat: float,
    lon: float,
    bottom: float,
    left: float,
    top: float,
    right: float,
    cortar_no: str | None = None,
    rlet_tp_cd: str | None = None,
    trad_tp_cd: str | None = None,
    spc_min: int | None = None,
    spc_max: int | None = None,
    dprc_min: int | None = None,
    dprc_max: int | None = None,
    page: int = 1,
) -> str:
    """
    Cluster API URL 빌드 헬퍼 함수

    Args:
        zoom: 줌 레벨
        lat: 중심 위도
        lon: 중심 경도
        bottom: 지도 경계 남쪽 좌표
        left: 지도 경계 서쪽 좌표
        top: 지도 경계 북쪽 좌표
        right: 지도 경계 동쪽 좌표
        cortar_no: 법정동코드
        rlet_tp_cd: 부동산유형코드 (A01:A02 - 아파트:오피스텔)
        trad_tp_cd: 거래유형코드 (A1:B1:B2 - 매매:전세:월세)
        spc_min: 최소 면적 (㎡)
        spc_max: 최대 면적 (㎡)
        dprc_min: 최소 매매가 (만원)
        dprc_max: 최대 매매가 (만원)
        page: 페이지 번호

    Returns:
        str: 완전한 API URL
    """
    client = NaverClusterAPIClient(
        lat=lat,
        lon=lon,
        bottom=bottom,
        left=left,
        top=top,
        right=right,
        cortar_no=cortar_no,
        rlet_tp_cd=rlet_tp_cd,
        trad_tp_cd=trad_tp_cd,
        spc_min=spc_min,
        spc_max=spc_max,
        dprc_min=dprc_min,
        dprc_max=dprc_max,
        zoom=zoom,
    )
    return client.build_url(page=page)


def parse_article_item(item_dict: dict) -> NaverArticleItemDTO:
    """
    매물 아이템 파싱 헬퍼 함수

    Args:
        item_dict: API 응답의 개별 매물 딕셔너리

    Returns:
        NaverArticleItemDTO: 파싱된 매물 정보
    """
    client = NaverClusterAPIClient(
        lat=0,
        lon=0,
        bottom=0,
        left=0,
        top=0,
        right=0,
    )
    return client.parse_article_item(item_dict)


def parse_cluster_response(response_json: dict) -> NaverClusterResponseDTO:
    """
    Cluster API 응답 파싱 헬퍼 함수

    Args:
        response_json: API 응답 JSON 딕셔너리

    Returns:
        NaverClusterResponseDTO: 파싱된 응답 정보
    """
    client = NaverClusterAPIClient(
        lat=0,
        lon=0,
        bottom=0,
        left=0,
        top=0,
        right=0,
    )
    return client.parse_response(response_json)
