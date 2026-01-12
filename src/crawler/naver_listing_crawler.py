"""네이버 부동산 매물 목록 크롤러

Cluster API를 사용하여 매물 목록을 크롤링합니다.
- 중심 좌표와 반경으로 지도 경계 계산
- Cluster API로 매물 목록 조회
- 페이지네이션 자동 처리
"""

import time

import requests

from crawler.dto.naver_article import NaverArticleItemDTO
from crawler.naver_cluster_api import NaverClusterAPIClient
from crawler.utils.geo import bounds_from_center


class RateLimit:
    """Rate Limiting 상수 (jissp 전략)"""

    BETWEEN_REQUESTS = 0.2  # 200ms - 각 API 호출 후
    BETWEEN_PAGES = 3.0  # 3초 - 페이지 로드 후


class NaverListingCrawler:
    """
    네이버 부동산 매물 목록 크롤러

    좌표 기반으로 매물 목록을 조회합니다.
    Cluster API를 사용하여 매물 정보를 제공합니다.
    """

    def __init__(
        self,
        lat: float,
        lon: float,
        radius_m: int = 1000,
        zoom: int = 13,
        cortar_no: str | None = None,
        rlet_tp_cd: str | None = None,
        trad_tp_cd: str | None = None,
        spc_min: int | None = None,
        spc_max: int | None = None,
        dprc_min: int | None = None,
        dprc_max: int | None = None,
    ):
        """
        Args:
            lat: 중심 위도
            lon: 중심 경도
            radius_m: 검색 반경 (미터, 기본값 1000)
            zoom: 줌 레벨 (기본값 13)
            cortar_no: 법정동코드
            rlet_tp_cd: 부동산유형코드 (A01:A02 - 아파트:오피스텔)
            trad_tp_cd: 거래유형코드 (A1:B1:B2 - 매매:전세:월세)
            spc_min: 최소 면적 (㎡)
            spc_max: 최대 면적 (㎡)
            dprc_min: 최소 매매가 (만원)
            dprc_max: 최대 매매가 (만원)
        """
        self.lat = lat
        self.lon = lon
        self.radius_m = radius_m
        self.zoom = zoom
        self.cortar_no = cortar_no
        self.rlet_tp_cd = rlet_tp_cd
        self.trad_tp_cd = trad_tp_cd
        self.spc_min = spc_min
        self.spc_max = spc_max
        self.dprc_min = dprc_min
        self.dprc_max = dprc_max

        # 지도 경계 계산
        self.s_lat, self.s_lng, self.e_lat, self.e_lng = bounds_from_center(
            lat, lon, radius_m, zoom
        )

        # API 클라이언트 초기화
        self.cluster_client = NaverClusterAPIClient(
            lat=lat,
            lon=lon,
            bottom=self.s_lat,
            left=self.s_lng,
            top=self.e_lat,
            right=self.e_lng,
            cortar_no=cortar_no,
            rlet_tp_cd=rlet_tp_cd,
            trad_tp_cd=trad_tp_cd,
            spc_min=spc_min,
            spc_max=spc_max,
            dprc_min=dprc_min,
            dprc_max=dprc_max,
            zoom=zoom,
        )

    def _rate_limit(self, type: str = "between_requests"):
        """
        Rate Limiting 적용

        Args:
            type: "between_requests" (200ms) 또는 "between_pages" (3초)
        """
        delay = RateLimit.BETWEEN_REQUESTS
        if type == "between_pages":
            delay = RateLimit.BETWEEN_PAGES
        time.sleep(delay)

    def crawl_listings(self, max_pages: int = 10) -> list[NaverArticleItemDTO]:
        """
        매물 목록 크롤링 (페이지네이션 포함)

        Args:
            max_pages: 최대 페이지 수 (기본값 10)

        Returns:
            list[NaverArticleItemDTO]: 매물 목록
        """
        all_articles = []
        page = 1

        while page <= max_pages:
            # URL 빌드
            url = self.cluster_client.build_url(page=page)

            try:
                # API 요청
                response_json = self.cluster_client.fetch(url)
                response_dto = self.cluster_client.parse_response(response_json)

                # 매물 추가
                articles = response_dto.articles
                all_articles.extend(articles)

                # 다음 페이지 확인 (more가 False이거나 pages가 0이면 종료)
                if not response_dto.more:
                    break

                page += 1

                # Rate limiting (페이지 로드 후)
                self._rate_limit(type="between_pages")

            except requests.RequestException as e:
                # 네트워크 에러 시 로그 출력 후 종료
                print(f"API 요청 실패 (page {page}): {e}")
                break
            except Exception as e:
                # 파싱 에러 시 로그 출력 후 종료
                print(f"데이터 파싱 실패 (page {page}): {e}")
                break

        return all_articles
