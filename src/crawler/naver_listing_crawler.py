"""네이버 부동산 매물 목록 크롤러

Cluster API + Front API를 조합하여 매물 목록과 상세 정보를 크롤링합니다.
- 중심 좌표와 반경으로 지도 경계 계산
- Cluster API로 매물 목록 조회
- Front API로 매물 상세 정보 조회
- 페이지네이션 자동 처리
"""

import time
from typing import Any

import requests

from crawler.dto.naver_article import NaverArticleItemDTO
from crawler.naver_cluster_api import NaverClusterAPIClient
from crawler.naver_coordinate import bounds_from_center
from crawler.naver_front_api import NaverFrontAPIClient


class RateLimit:
    """Rate Limiting 상수 (jissp 전략)"""

    BETWEEN_REQUESTS = 0.2  # 200ms - 각 API 호출 후
    BETWEEN_PAGES = 3.0  # 3초 - 페이지 로드 후


class NaverListingCrawler:
    """
    네이버 부동산 매물 목록 크롤러

    좌표 기반으로 매물 목록을 조회하고 상세 정보를 수집합니다.
    Cluster API와 Front API를 조합하여 완전한 매물 정보를 제공합니다.
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
        self.front_client = NaverFrontAPIClient()

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

    def crawl_listing_detail(
        self, article_id: str, real_estate_type: str, trade_type: str
    ) -> dict[str, Any] | None:
        """
        매물 상세 정보 크롤링

        Args:
            article_id: 매물 ID
            real_estate_type: 부동산 유형 (APT, OPST 등)
            trade_type: 거래 유형 (A1=매매, B1=전세, B2=월세)

        Returns:
            dict | None: 매물 상세 정보
        """
        try:
            # URL 빌드
            url = self.front_client.get_article_basic_info_url(
                article_id=article_id,
                real_estate_type=real_estate_type,
                trade_type=trade_type,
            )

            # API 요청
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            response_json = response.json()

            # 응답 파싱
            result = {
                "price_info": self.front_client.parse_basic_info_price(response_json),
                "detail_info": self.front_client.parse_basic_info_detail(response_json),
                "size_info": self.front_client.parse_basic_info_size(response_json),
            }

            return result

        except requests.RequestException as e:
            print(f"매물 상세 정보 요청 실패 (article_id: {article_id}): {e}")
            return None
        except Exception as e:
            print(f"매물 상세 정보 파싱 실패 (article_id: {article_id}): {e}")
            return None

    def crawl_all(self, max_pages: int = 10) -> list[dict[str, Any]]:
        """
        매물 목록과 상세 정보를 모두 크롤링

        Args:
            max_pages: 최대 페이지 수 (기본값 10)

        Returns:
            list[dict]: 매물 목록 + 상세 정보
        """
        # 매물 목록 조회
        articles = self.crawl_listings(max_pages=max_pages)

        results = []
        for article in articles:
            # 매물 기본 정보
            article_dict = article.model_dump()

            # 매물 상세 정보 조회
            detail = self.crawl_listing_detail(
                article_id=article.atcl_no,
                real_estate_type=article.rlet_tp_cd,
                trade_type=article.trad_tp_cd,
            )

            # 병합
            article_dict.update(detail or {})
            results.append(article_dict)

            # Rate limiting (각 API 호출 후)
            self._rate_limit(type="between_requests")

        return results
