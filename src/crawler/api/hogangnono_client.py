"""호갱노노 API 전용 클라이언트

호갱노노 API 엔드포인트에 접근하기 위한 전용 클라이언트를 제공합니다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal, Optional

import requests
from requests import Response, Session
from structlog import get_logger

from crawler.config import CrawlerConfig
# retry_with_backoff는 현재 구현되어 있지 않음


@dataclass
class SearchParams:
    """호갱노노 API 검색 파라미터

    Attributes:
        bbox: Bounding box 좌표 (lat_min,lng_min,lat_max,lng_max)
        zoom: 지도 확대 레벨
        filters: 필터링 조건
        limit: 결과 제한 개수
    """

    bbox: Optional[tuple[float, float, float, float]] = None
    zoom: Optional[int] = None
    filters: Optional[dict[str, Any]] = None
    limit: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        """API 요청에 사용할 딕셔너리로 변환"""
        params: dict[str, Any] = {}

        if self.bbox:
            params["lat_min"], params["lng_min"], params["lat_max"], params["lng_max"] = self.bbox

        if self.zoom is not None:
            params["zoom"] = self.zoom

        if self.filters:
            params.update(self.filters)

        if self.limit:
            params["limit"] = self.limit

        return params


@dataclass
class APIResponse:
    """API 응답 래퍼

    Attributes:
        success: API 호출 성공 여부
        data: 응답 데이터
        error: 에러 메시지
        status_code: HTTP 상태 코드
    """

    success: bool
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    status_code: Optional[int] = None

    @classmethod
    def from_response(cls, response: Response) -> APIResponse:
        """requests.Response 객체에서 APIResponse 생성"""
        try:
            response.raise_for_status()
            data = response.json()

            # 호갱노노 API 응답 구조 확인
            if isinstance(data, dict) and "success" in data:
                return cls(
                    success=data.get("success", True),
                    data=data.get("data"),
                    error=data.get("error"),
                    status_code=response.status_code,
                )
            else:
                # 직접 데이터 반환 경우
                return cls(success=True, data=data, status_code=response.status_code)
        except requests.HTTPError as e:
            return cls(
                success=False, error=f"HTTP error: {str(e)}", status_code=response.status_code
            )
        except json.JSONDecodeError as e:
            return cls(
                success=False,
                error=f"JSON decode error: {str(e)}",
                status_code=response.status_code,
            )
        except Exception as e:
            return cls(
                success=False, error=f"Unexpected error: {str(e)}", status_code=response.status_code
            )


class HogangnonoAPIClient:
    """호갱노노 API 클라이언트

    호갱노노 API와의 통신을 처리합니다.
    """

    def __init__(self, config: CrawlerConfig):
        """클라이언트 초기화

        Args:
            config: 크롤러 설정 객체
        """
        self.config = config
        self.base_url = "https://hogangnono.com"
        self.session = Session()

        # 기본 헤더 설정
        self.session.headers.update(
            {
                "User-Agent": config.user_agent,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Sec-Ch-Ua": '"Not.A/Brand";v="8", "Chromium";v="114"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"macOS"',
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Referer": self.base_url,
            }
        )

        self.logger = get_logger()

        # Rate limiting
        self.min_delay = 1.0  # 최소 1초 간격

    def _build_url(self, endpoint: str) -> str:
        """전체 URL 빌드"""
        return f"{self.base_url}{endpoint}"

    def _add_auth_headers(self, headers: Optional[dict[str, str]] = None) -> dict[str, str]:
        """인증 헤더 추가 (필요 시)"""
        if headers is None:
            headers = {}

        # 호갱노노는 특별한 인증이 필요없을 수 있음
        # 필요 시 JWT 토큰이나 API 키 추가
        return headers

    # @retry_with_backoff(max_attempts=3)  # 데코레이터 임시 제거
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> APIResponse:
        """HTTP 요청 실행"""
        url = self._build_url(endpoint)
        request_headers = self._add_auth_headers(headers)

        self.logger.info(
            "API request",
            method=method,
            url=url,
            params=params,
        )

        response = self.session.request(
            method=method,
            url=url,
            params=params,
            json=data,
            headers=request_headers,
            timeout=self.config.timeout,
        )

        api_response = APIResponse.from_response(response)

        if api_response.success:
            self.logger.info(
                "API request successful",
                status=response.status_code,
            )
        else:
            self.logger.error(
                "API request failed",
                status=response.status_code,
                error=api_response.error,
            )

        return api_response

    def get_ranking(
        self,
        rank_type: Literal["daily", "weekly", "monthly"] = "daily",
        region: Optional[str] = None,
        limit: int = 20,
    ) -> APIResponse:
        """랭킹 데이터 조회

        Args:
            rank_type: 랭킹 타입 (daily/weekly/monthly)
            region: 지역 코드 (선택)
            limit: 결과 제한 개수

        Returns:
            APIResponse 객체
        """
        params = {
            "type": rank_type,
            "limit": limit,
        }

        if region:
            params["region"] = region

        return self._make_request(
            method="GET",
            endpoint="/api/v2/ranks/rolling",
            params=params,
        )

    def get_recent_visits(
        self,
        apt_type: Optional[Literal["apart", "officetel", "house"]] = None,
        region: Optional[str] = None,
        limit: int = 50,
    ) -> APIResponse:
        """최근 조회한 매물 목록

        Args:
            apt_type: 매물 타입 (apart/officetel/house)
            region: 지역 코드 (선택)
            limit: 결과 제한 개수

        Returns:
            APIResponse 객체
        """
        params = {"limit": limit}

        if apt_type:
            params["type"] = apt_type
        if region:
            params["region"] = region

        return self._make_request(
            method="GET",
            endpoint="/api/v2/apts/recent-visits",
            params=params,
        )

    def get_region_info(
        self,
        lat: float,
        lng: float,
        zoom: int = 14,
    ) -> APIResponse:
        """지역 정보 조회

        Args:
            lat: 위도
            lng: 경도
            zoom: 지도 확대 레벨

        Returns:
            APIResponse 객체
        """
        params = {
            "lat": lat,
            "lng": lng,
            "zoom": zoom,
        }

        return self._make_request(
            method="GET",
            endpoint="/api/v2/maps/region",
            params=params,
        )

    def get_pois_bounding(
        self,
        search_params: SearchParams,
    ) -> APIResponse:
        """POI 정보 조회 (Bounding box 기반)

        Args:
            search_params: 검색 파라미터

        Returns:
            APIResponse 객체
        """
        params = search_params.to_dict()

        return self._make_request(
            method="GET",
            endpoint="/api/v2/pois-bounding",
            params=params,
        )

    def get_apartments_bounding(
        self,
        search_params: SearchParams,
        apt_type: Optional[Literal["apart", "officetel", "house"]] = None,
        trade_type: Optional[Literal["sale", "jeonse", "monthly"]] = None,
    ) -> APIResponse:
        """아파트/매물 목록 조회 (Bounding box 기반)

        Args:
            search_params: 검색 파라미터
            apt_type: 매물 타입
            trade_type: 거래 타입

        Returns:
            APIResponse 객체
        """
        params = search_params.to_dict()

        if apt_type:
            params["apt_type"] = apt_type
        if trade_type:
            params["trade_type"] = trade_type

        # 가상 엔드포인트 (실제 엔드포인트는 다를 수 있음)
        return self._make_request(
            method="GET",
            endpoint="/api/apt/bounding",
            params=params,
        )

    def search_apartments(
        self,
        keyword: str,
        region: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> APIResponse:
        """아파트 검색

        Args:
            keyword: 검색 키워드
            region: 지역 코드 (선택)
            page: 페이지 번호
            limit: 페이지당 결과 수

        Returns:
            APIResponse 객체
        """
        params = {
            "q": keyword,
            "page": page,
            "limit": limit,
        }

        if region:
            params["region"] = region

        # 가상 엔드포인트
        return self._make_request(
            method="GET",
            endpoint="/api/search/apartments",
            params=params,
        )

    def get_apartment_detail(self, apt_id: str) -> APIResponse:
        """아파트 상세 정보 조회

        Args:
            apt_id: 아파트 ID

        Returns:
            APIResponse 객체
        """
        return self._make_request(
            method="GET",
            endpoint=f"/api/apt/{apt_id}",
        )

    def close(self) -> None:
        """세션 종료"""
        self.session.close()
        self.logger.info("API client session closed")

    def __enter__(self) -> HogangnonoAPIClient:
        """Context manager 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager 종료"""
        self.close()
