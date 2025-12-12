"""호갱노노 API 전용 클라이언트 (리팩토링 버전)

BaseAPIClient를 상속받아 중복 코드를 제거한 버전
"""

from dataclasses import dataclass
from typing import Any, Optional, List, Dict
from pathlib import Path

from structlog import get_logger

from crawler.config import CrawlerConfig
from .base_api_client import BaseAPIClient, APIResponse
from ..models.api_responses import (
    POIInfo,
    RankingInfo,
    poi_info_from_bounding_response,
    ranking_info_from_rolling_response,
)

# Required headers per API guide
_REQUIRED_HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://hogangnono.com/",
    "Origin": "https://hogangnono.com",
}


@dataclass
class SearchParams:
    """호갱노노 API 검색 파라미터"""

    # 유효한 level 값 범위
    MIN_LEVEL = 1
    MAX_LEVEL = 18

    # 유효한 tradeType 값
    VALID_TRADE_TYPES = {0, 1, 2}

    # 유효한 aptType 값
    VALID_APT_TYPES = {-1, 0, 1, 2}

    def __init__(
        self,
        startX: Optional[float] = None,
        endX: Optional[float] = None,
        startY: Optional[float] = None,
        endY: Optional[float] = None,
        level: Optional[int] = 17,
        tradeType: Optional[int] = 0,
        areaFrom: Optional[float] = None,
        areaTo: Optional[float] = None,
        priceFrom: Optional[int] = None,
        priceTo: Optional[int] = None,
        aptType: Optional[int] = -1,
        priceType: Optional[int] = 0,
        rentType: Optional[int] = 0,
        map: str = "google",
        bbox: Optional[tuple[float, float, float, float]] = None,
    ):
        # bbox가 제공되면 startX/Y, endX/Y로 변환
        if bbox:
            lng_min, lat_min, lng_max, lat_max = bbox
            self.startX = lng_min
            self.endX = lng_max
            self.startY = lat_min
            self.endY = lat_max
        else:
            self.startX = startX
            self.endX = endX
            self.startY = startY
            self.endY = endY

        # 유효성 검사
        if level is not None and not (self.MIN_LEVEL <= level <= self.MAX_LEVEL):
            raise ValueError(
                f"level must be between {self.MIN_LEVEL} and {self.MAX_LEVEL}, got {level}"
            )
        if tradeType is not None and tradeType not in self.VALID_TRADE_TYPES:
            raise ValueError(f"tradeType must be one of {self.VALID_TRADE_TYPES}, got {tradeType}")
        if aptType is not None and aptType not in self.VALID_APT_TYPES:
            raise ValueError(f"aptType must be one of {self.VALID_APT_TYPES}, got {aptType}")

        self.level = level
        self.tradeType = tradeType
        self.areaFrom = areaFrom
        self.areaTo = areaTo
        self.priceFrom = priceFrom
        self.priceTo = priceTo
        self.aptType = aptType
        self.priceType = priceType
        self.rentType = rentType
        self.map = map

    def to_dict(self) -> dict[str, Any]:
        """API 요청에 사용할 딕셔너리로 변환"""
        params: dict[str, Any] = {}

        # 필수 파라미터
        if self.startX is not None:
            params["startX"] = self.startX
        if self.endX is not None:
            params["endX"] = self.endX
        if self.startY is not None:
            params["startY"] = self.startY
        if self.endY is not None:
            params["endY"] = self.endY

        # 선택적 파라미터
        if self.level is not None:
            params["level"] = str(self.level)
        if self.tradeType is not None:
            params["tradeType"] = self.tradeType
        if self.areaFrom is not None:
            params["areaFrom"] = self.areaFrom
        if self.areaTo is not None:
            params["areaTo"] = self.areaTo
        if self.priceFrom is not None:
            params["priceFrom"] = self.priceFrom
        if self.priceTo is not None:
            params["priceTo"] = self.priceTo
        if self.aptType is not None:
            params["aptType"] = self.aptType
        if hasattr(self, "priceType") and self.priceType is not None:
            params["priceType"] = self.priceType
        if hasattr(self, "rentType") and self.rentType is not None:
            params["rentType"] = self.rentType

        # 항상 포함
        params["map"] = self.map
        params["screenWidth"] = 1200
        params["screenHeight"] = 924
        params["apt"] = ""

        return params


class HogangnonoAPIClient(BaseAPIClient):
    """호갱노노 API 클라이언트 (리팩토링 버전)

    BaseAPIClient를 상속받아 중복을 제거하고 호갱노노 특화 기능만 구현
    """

    def __init__(self, config: CrawlerConfig, cache_dir: Optional[Path] = None):
        """클라이언트 초기화"""
        super().__init__(config=config, base_url="https://hogangnono.com", cache_dir=cache_dir)
        self.logger = get_logger().bind(component="HogangnonoAPIClient")

    def get_required_headers(self) -> Dict[str, str]:
        """호갱노노 API에 필요한 필수 헤더 반환"""
        return _REQUIRED_HEADERS

    def _initialize_session(self) -> bool:
        """호갱노노 세션 초기화 (재정의)"""
        if self._session_initialized:
            return True

        self.logger.info("Initializing session and getting cookies")

        # 메인 페이지 접속 헤더
        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "max-age=0",
            "Sec-Ch-Ua": '"Not.A/Brand";v="8", "Chromium";v="114"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }

        try:
            response = self.session.get(
                self.base_url,
                headers=headers,
                timeout=self.config.timeout,
            )

            self.logger.info(
                "Session initialized",
                status_code=response.status_code,
                cookies=list(self.session.cookies.keys()),
            )

            self._session_initialized = True
            return response.status_code == 200

        except Exception as e:
            self.logger.error(
                "Failed to initialize session",
                error=str(e),
            )
            return False

    # API 메서드들 - BaseAPIClient의 _make_request를 사용하여 중복 제거
    def get_complex_list(
        self,
        cortar_no: str,
        bounds: Optional[str] = None,
    ) -> APIResponse:
        """단지 목록 조회"""
        params = {"cortarNo": cortar_no}
        if bounds:
            params["bounds"] = bounds

        return self._make_request(
            method="GET",
            endpoint="/cluster/ajax/complexList",
            params=params,
        )

    def get_complex_detail(self, complex_id: str) -> APIResponse:
        """단지 상세 정보 조회"""
        params = {"complexNo": complex_id}
        return self._make_request(
            method="GET",
            endpoint="/cluster/ajax/complexDetail",
            params=params,
        )

    def get_apartments_bounding(self, search_params: SearchParams) -> APIResponse:
        """아파트/매물 목록 조회 (Bounding box 기반)"""
        return self._make_request(
            method="GET",
            endpoint="/api/v2/pois-bounding",
            params=search_params.to_dict(),
        )

    def get_ranking(self, rank_type: str = "daily", limit: int = 100) -> APIResponse:
        """인기 순위 조회"""
        params = {"type": rank_type, "limit": limit}
        return self._make_request(
            method="GET",
            endpoint="/api/v2/ranks/rolling",
            params=params,
        )

    def get_regions(self, region_code: Optional[str] = None) -> APIResponse:
        """시/도, 구/군 목록 조회"""
        params = {}
        if region_code:
            params["regionCode"] = region_code

        # regions API는 간단한 헤더 사용
        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "application/json",
        }

        return self._make_request(
            method="GET",
            endpoint="/api/v2/regions",
            params=params,
            headers=headers,
        )

    # 데이터 처리 유틸리티 메서드들
    def parse_complexes_from_ranks(self, ranks_data: dict[str, Any]) -> List[RankingInfo]:
        """ranks/rolling 응답에서 단지 정보 파싱"""
        complexes = []

        if (
            not ranks_data
            or "data" not in ranks_data
            or "rolling" not in ranks_data.get("data", {})
        ):
            return complexes

        for item in ranks_data["data"]["rolling"]:
            ranking_info = ranking_info_from_rolling_response(item)
            complexes.append(ranking_info)

        return complexes

    def parse_pois_from_bounding(self, pois_data: dict[str, Any]) -> List[POIInfo]:
        """pois-bounding 응답에서 POI 정보 파싱"""
        pois = []

        if not pois_data or "data" not in pois_data:
            return pois

        for item in pois_data["data"]:
            poi_info = poi_info_from_bounding_response(item)
            if poi_info.validate_for_apartment_crawling():
                pois.append(poi_info)

        return pois
