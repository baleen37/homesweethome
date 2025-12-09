"""호갱노노 API 전용 클라이언트

호갱노노 API 엔드포인트에 접근하기 위한 전용 클라이언트를 제공합니다.
"""

import json
import types
from dataclasses import dataclass
from typing import Any, Optional

import requests
from requests import Response, Session
from structlog import get_logger

from crawler.config import CrawlerConfig
from ..utils.retry import retry_transient_errors

# Mock 객체 확인을 위한 임포트 (테스트 환경에서만 사용)
try:
    from unittest.mock import Mock
except ImportError:
    Mock = None


class SearchParams:
    """호갱노노 API 검색 파라미터

    Attributes:
        startX: 시작 경도 (최소 경도)
        endX: 끝 경도 (최대 경도)
        startY: 시작 위도 (최소 위도)
        endY: 끝 위도 (최대 위도)
        level: 줌 레벨 (1-18)
        tradeType: 거래 유형 (0:매매, 1:전세, 2:월세)
        areaFrom: 최소 전용면적 (㎡)
        areaTo: 최대 전용면적 (㎡)
        priceFrom: 최소 가격 (만원)
        priceTo: 최대 가격 (만원)
        aptType: 아파트 유형 (-1: 전체)
        rentType: 임대 유형 (0:전체, 1:주택, 2:오피스텔)
        map: 지도 종류 (google)
    """

    # 유효한 level 값 범위
    MIN_LEVEL = 1
    MAX_LEVEL = 18

    # 유효한 tradeType 값
    VALID_TRADE_TYPES = {0, 1, 2}  # 0:매매, 1:전세, 2:월세

    # 유효한 aptType 값
    VALID_APT_TYPES = {-1, 0, 1, 2}  # -1:전체, 0:아파트, 1:주상복합, 2:오피스텔

    # 유효한 priceType 값
    VALID_PRICE_TYPES = {0, 1, 2}  # 0:전체, 1:매매, 2:전세

    # 유효한 rentType 값
    VALID_RENT_TYPES = {0, 1, 2}  # 0:전체, 1:월세, 2:단기임대

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
        """초기화

        Args:
            startX: 시작 경도
            endX: 끝 경도
            startY: 시작 위도
            endY: 끝 위도
            level: 줌 레벨
            tradeType: 거래 유형
            areaFrom: 최소 전용면적
            areaTo: 최대 전용면적
            priceFrom: 최소 가격
            priceTo: 최대 가격
            aptType: 아파트 유형
            priceType: 가격 유형
            rentType: 임대 유형
            map: 지도 종류
            bbox: (lng_min, lat_min, lng_max, lat_max) 형태의 좌표
        """
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

        # level 유효성 검사
        if level is not None and not (self.MIN_LEVEL <= level <= self.MAX_LEVEL):
            raise ValueError(
                f"level must be between {self.MIN_LEVEL} and {self.MAX_LEVEL}, got {level}"
            )
        self.level = level

        # tradeType 유효성 검사
        if tradeType is not None and tradeType not in self.VALID_TRADE_TYPES:
            raise ValueError(f"tradeType must be one of {self.VALID_TRADE_TYPES}, got {tradeType}")
        self.tradeType = tradeType

        self.areaFrom = areaFrom
        self.areaTo = areaTo
        self.priceFrom = priceFrom
        self.priceTo = priceTo

        # aptType 유효성 검사
        if aptType is not None and aptType not in self.VALID_APT_TYPES:
            raise ValueError(f"aptType must be one of {self.VALID_APT_TYPES}, got {aptType}")
        self.aptType = aptType

        # priceType 유효성 검사 (새 파라미터)
        if priceType is not None and priceType not in self.VALID_PRICE_TYPES:
            raise ValueError(f"priceType must be one of {self.VALID_PRICE_TYPES}, got {priceType}")
        self.priceType = priceType

        # rentType 유효성 검사 (새 파라미터)
        if rentType is not None and rentType not in self.VALID_RENT_TYPES:
            raise ValueError(f"rentType must be one of {self.VALID_RENT_TYPES}, got {rentType}")
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
            params["level"] = str(self.level)  # level은 문자열로 변환
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

        # 호갱노노 API 특정 파라미터
        params["screenWidth"] = 1200
        params["screenHeight"] = 924
        params["apt"] = ""  # 아파트 필터 (빈 문자열)

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
    def from_response(cls, response: Response) -> "APIResponse":
        """requests.Response 객체에서 APIResponse 생성"""
        # 기본 값 초기화
        status_code = None
        content_type = ""
        headers = {}

        # status_code 추출 (예외 처리 포함)
        try:
            status_code = response.status_code
        except Exception as e:
            # status_code 접근 시 예외가 발생하면 즉시 예외 처리
            return cls(
                success=False,
                error=f"Unexpected error: {str(e)}",
                status_code=None,
            )

        # headers 접근 (예외 처리 포함)
        try:
            headers = response.headers
            content_type = ""
            # headers가 dict-like 객체인지 확인
            if hasattr(headers, "get") and callable(getattr(headers, "get", None)):
                content_type = headers.get("content-type", "")
                if content_type:
                    content_type = content_type.lower()
        except Exception:
            # headers 접근 실패 시 기본값 사용
            content_type = ""

        try:
            # Content-Type 확인
            if "application/json" in content_type:
                # JSON 응답 처리
                data = response.json()

                # 호갱노노 API 응답 구조 확인
                if isinstance(data, dict) and "success" in data:
                    # API 레벨의 success가 false이거나 HTTP 상태 코드가 에러인 경우
                    api_success = data.get("success", True)
                    http_error = status_code is not None and status_code >= 400

                    # HTTP 에러인 경우 error 메시지에 HTTP 에러 정보 추가
                    error_msg = data.get("error")
                    if http_error:
                        if error_msg:
                            error_msg = f"HTTP error: {status_code} {response.reason if hasattr(response, 'reason') else ''} - {error_msg}"
                        else:
                            # error 필드가 없고 message 필드가 있는 경우
                            if "message" in data:
                                error_msg = f"HTTP error: {status_code} {response.reason if hasattr(response, 'reason') else ''} - {data['message']}"
                            else:
                                error_msg = f"HTTP error: {status_code} {response.reason if hasattr(response, 'reason') else ''}"

                    return cls(
                        success=api_success and not http_error,
                        data=data.get("data"),  # API success 응답에서만 data 필드 반환
                        error=error_msg,
                        status_code=status_code,
                    )
                else:
                    # 직접 데이터 반환 경우 (HTTP 에러가 아니면 성공)
                    http_error = status_code is not None and status_code >= 400

                    # message 필드가 있는 HTTP 에러 응답 처리
                    error_msg = None
                    if http_error and isinstance(data, dict) and "message" in data:
                        error_msg = f"HTTP error: {status_code} {response.reason if hasattr(response, 'reason') else ''} - {data['message']}"

                    return cls(
                        success=not http_error,
                        data=data if not http_error else None,
                        error=error_msg
                        if error_msg
                        else (
                            None
                            if not http_error
                            else f"HTTP error: {status_code} {response.reason if hasattr(response, 'reason') else ''}"
                        ),
                        status_code=status_code,
                    )
            else:
                # HTML 또는 텍스트 응답 처리
                if status_code == 200:
                    # 200 OK이면 성공으로 간주 (HTML 페이지 접근 성공)
                    text_content = ""
                    try:
                        text_content = response.text[:1000]
                    except Exception:
                        pass

                    return cls(
                        success=True,
                        data={"raw_content": text_content},
                        status_code=status_code,
                    )
                else:
                    # 200이 아닌 비-JSON 응답은 실패로 간주
                    error_msg = f"HTTP error: {status_code}"
                    try:
                        error_msg += f" {response.reason}"
                    except Exception:
                        pass

                    return cls(
                        success=False,
                        error=error_msg,
                        status_code=status_code,
                    )

        except requests.RequestException as e:
            # RequestException 처리
            error_status_code = None
            if hasattr(e, "response") and e.response is not None:
                error_status_code = e.response.status_code
            elif status_code is not None:
                error_status_code = status_code
            return cls(
                success=False,
                error=f"Request error: {str(e)}",
                status_code=error_status_code,
            )
        except json.JSONDecodeError as e:
            # JSONDecodeError 발생 시
            if status_code == 200:
                # 200 응답에서 JSON 디코드 에러는 HTML로 간주
                text_content = ""
                try:
                    text_content = response.text[:1000]
                except Exception:
                    pass

                return cls(
                    success=True,
                    data={"raw_content": text_content},
                    status_code=status_code,
                )
            else:
                # 200이 아닌 응답에서 JSON 디코드 에러는 실패
                error_msg = f"JSON decode error: {str(e)}"
                if status_code is not None:
                    error_msg = f"HTTP error: {status_code} - {error_msg}"
                return cls(
                    success=False,
                    error=error_msg,
                    status_code=status_code,
                )
        except Exception as e:
            # 그 외 모든 예외 처리
            return cls(
                success=False,
                error=f"Unexpected error: {str(e)}",
                status_code=status_code,
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

        # 초기화 상태 추적
        self._session_initialized = False

        self.logger = get_logger()

        # Rate limiting - 단일 AdaptiveRateLimiter
        from ..rate_limiter import AdaptiveRateLimiter

        self.rate_limiter = AdaptiveRateLimiter()
        # 초기값 설정 (2초, 최소 1초, 최대 10초)
        self.rate_limiter.current_delay = 2.0
        self.rate_limiter.min_delay = 1.0
        self.rate_limiter.max_delay = 10.0

    def _build_url(self, endpoint: str) -> str:
        """전체 URL 빌드"""
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        return f"{self.base_url}{endpoint}"

    def _initialize_session(self) -> bool:
        """초기 세션 설정 및 쿠키 발급

        메인 페이지에 접속하여 필수 쿠키를 받습니다.

        Returns:
            초기화 성공 여부
        """
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
            # 메인 페이지 접속
            response = self.session.get(
                self.base_url,
                headers=headers,
                timeout=self.config.timeout,
            )

            # 쿠키 확인
            cookies = self.session.cookies
            # Mock 객체 처리를 위한 안전한 쿠키 이름 추출
            try:
                if Mock is not None and isinstance(cookies, Mock):
                    cookie_names = ["mock_cookie_1", "mock_cookie_2"]  # 테스트용 가상 쿠키
                else:
                    cookie_names = [c.name for c in cookies] if cookies else []
            except (TypeError, AttributeError):
                cookie_names = []

            self.logger.info(
                "Session initialized",
                status_code=response.status_code,
                cookies=cookie_names,
            )

            self._session_initialized = True
            return response.status_code == 200

        except Exception as e:
            self.logger.error(
                "Failed to initialize session",
                error=str(e),
            )
            return False

    def _get_api_headers(self) -> dict[str, str]:
        """API 호출용 헤더

        Returns:
            API 요청 헤더 딕셔너리
        """
        return {
            "User-Agent": self.config.user_agent,
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
            "Origin": self.base_url,
            "X-Requested-With": "XMLHttpRequest",
        }

    def _add_auth_headers(
        self,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, str]:
        """인증 헤더 추가 (필요 시)"""
        if headers is None:
            headers = {}

        # API 헤더와 병합
        api_headers = self._get_api_headers()
        final_headers = {**api_headers, **headers}

        return final_headers

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> APIResponse:
        """HTTP 요청 실행"""
        # Rate limiting 적용
        self.rate_limiter.wait()

        # 세션이 초기화되지 않았다면 초기화
        if not self._session_initialized:
            if not self._initialize_session():
                return APIResponse(
                    success=False,
                    error="Failed to initialize session",
                    status_code=None,
                )

        url = self._build_url(endpoint)
        request_headers = self._add_auth_headers(headers)

        self.logger.info(
            "API request",
            method=method,
            url=url,
            params=params,
        )

        # 쿠키 정보 로깅
        if self.session.cookies:
            # Mock 객체 처리
            if Mock is not None and isinstance(self.session.cookies, Mock):
                self.logger.debug(
                    "Request cookies (Mock)",
                    is_mock=True,
                )
            else:
                try:
                    cookie_info = {c.name: c.value for c in self.session.cookies}
                    self.logger.debug(
                        "Request cookies",
                        cookies=cookie_info,
                    )
                except (TypeError, AttributeError):
                    # 쿠키 객체가 다른 형태일 경우
                    self.logger.debug(
                        "Request cookies (unknown format)",
                        cookies=str(self.session.cookies)[:100],
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

        # Rate limiter 피드백
        if api_response.success:
            self.rate_limiter.on_success()
            self.logger.info(
                "API request successful",
                status=response.status_code,
            )
        elif api_response.status_code == 429:
            self.rate_limiter.on_rate_limit_error()
            self.logger.error(
                "API request rate limited",
                status=response.status_code,
                error=api_response.error,
            )
        else:
            self.rate_limiter.on_error()
            self.logger.error(
                "API request failed",
                status=response.status_code,
                error=api_response.error,
            )

        return api_response

    @retry_transient_errors(max_attempts=3, base_delay=1.0, max_delay=10.0)
    def get_complex_list(
        self,
        cortar_no: str,
        bounds: Optional[str] = None,
    ) -> APIResponse:
        """단지 목록 조회

        Args:
            cortar_no: 법정동 코드
            bounds: 좌표 영역

        Returns:
            APIResponse 객체
        """
        params = {
            "cortarNo": cortar_no,
        }

        if bounds:
            params["bounds"] = bounds

        return self._make_request(
            method="GET",
            endpoint="/cluster/ajax/complexList",
            params=params,
        )

    @retry_transient_errors(max_attempts=3, base_delay=1.0, max_delay=10.0)
    def get_complex_detail(
        self,
        complex_id: str,
    ) -> APIResponse:
        """단지 상세 정보 조회

        Args:
            complex_id: 단지 ID

        Returns:
            APIResponse 객체
        """
        params = {
            "complexNo": complex_id,
        }

        return self._make_request(
            method="GET",
            endpoint="/cluster/ajax/complexDetail",
            params=params,
        )

    @retry_transient_errors(max_attempts=3, base_delay=1.0, max_delay=10.0)
    def get_apartments_bounding(
        self,
        search_params: SearchParams,
    ) -> APIResponse:
        """아파트/매물 목록 조회 (Bounding box 기반)

        Args:
            search_params: 검색 파라미터

        Returns:
            APIResponse 객체
        """
        params = search_params.to_dict()

        # 호갱노노 API 엔드포인트
        return self._make_request(
            method="GET",
            endpoint="/api/v2/pois-bounding",
            params=params,
        )

    @retry_transient_errors(max_attempts=3, base_delay=1.0, max_delay=10.0)
    def get_ranking(self, rank_type: str = "daily", limit: int = 100) -> APIResponse:
        """인기 순위 조회

        Args:
            rank_type: 순위 타입 (daily, weekly, monthly)
            limit: 가져올 항목 수

        Returns:
            APIResponse 객체
        """
        params = {
            "type": rank_type,
            "limit": limit,
        }

        return self._make_request(
            method="GET",
            endpoint="/api/v2/ranks/rolling",
            params=params,
        )

    @retry_transient_errors(max_attempts=3, base_delay=1.0, max_delay=10.0)
    def get_recent_visits(self, apt_type: str = "apart", limit: int = 100) -> APIResponse:
        """최근 방문한 아파트 조회

        Args:
            apt_type: 아파트 타입 (apart, officetel, etc)
            limit: 가져올 항목 수

        Returns:
            APIResponse 객체
        """
        params = {
            "aptType": apt_type,
            "limit": limit,
        }

        return self._make_request(
            method="GET",
            endpoint="/api/v2/apts/recent-visits",
            params=params,
        )

    @retry_transient_errors(max_attempts=3, base_delay=1.0, max_delay=10.0)
    def get_region_info(self, lat: float, lng: float, zoom: int = 15) -> APIResponse:
        """지역 정보 조회

        Args:
            lat: 위도
            lng: 경도
            zoom: 줌 레벨

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

    @retry_transient_errors(max_attempts=3, base_delay=1.0, max_delay=10.0)
    def get_pois_bounding(self, search_params: SearchParams) -> APIResponse:
        """POI 목록 조회 (Bounding box 기반)

        Args:
            search_params: 검색 파라미터

        Returns:
            APIResponse 객체
        """
        # get_apartments_bounding과 동일한 기능
        return self.get_apartments_bounding(search_params)

    @retry_transient_errors(max_attempts=3, base_delay=1.0, max_delay=10.0)
    def search_apartments(
        self,
        query: str,
        bounds: Optional[tuple[float, float, float, float]] = None,
        filters: Optional[dict[str, Any]] = None,
        page: int = 1,
        limit: int = 100,
    ) -> APIResponse:
        """아파트 검색

        Args:
            query: 검색어
            bounds: (lat_min, lng_min, lat_max, lng_max)
            filters: 추가 필터 옵션
            page: 페이지 번호
            limit: 페이지당 항목 수

        Returns:
            APIResponse 객체
        """
        params = {
            "query": query,
            "page": page,
            "limit": limit,
        }

        if bounds:
            lat_min, lng_min, lat_max, lng_max = bounds
            params.update(
                {
                    "startX": lng_min,
                    "startY": lat_min,
                    "endX": lng_max,
                    "endY": lat_max,
                }
            )

        if filters:
            params.update(filters)

        return self._make_request(
            method="GET",
            endpoint="/api/search/apartments",
            params=params,
        )

    @retry_transient_errors(max_attempts=3, base_delay=1.0, max_delay=10.0)
    def get_apartment_detail(self, apt_id: str) -> APIResponse:
        """아파트 상세 정보 조회

        Args:
            apt_id: 아파트 ID (aptHash)

        Returns:
            APIResponse 객체

        Example Response:
            {
                "data": {
                    "aptHash": "1Hq6f",
                    "aptName": "래미안",
                    "buildYear": 2005,
                    "household": 1012,
                    "parkingCount": 850,
                    "floorAreaRatio": 250.5,
                    "buildingCoverageRatio": 15.3
                },
                "status": "success"
            }
        """
        return self._make_request(method="GET", endpoint=f"/api/v2/apts/{apt_id}", params={})

    @retry_transient_errors(max_attempts=3, base_delay=1.0, max_delay=10.0)
    def get_apartment_transactions(
        self, apt_id: str, trade_type: int = 0, area_no: int = 0, full_period: bool = False
    ) -> APIResponse:
        """실거래 내역 조회

        Args:
            apt_id: 단지 ID (aptHash)
            trade_type: 0=매매, 1=전세, 2=월세
            area_no: 면적 필터 (0=전체)
            full_period: True면 전체 기간, False면 최근 3년

        Returns:
            APIResponse 객체

        Example Response:
            {
                "data": {
                    "shortTermReport": [
                        {
                            "date": "2025-01-31T15:00:00.000Z",
                            "minPrice": 333000,
                            "maxPrice": 346000,
                            "averagePrice": 343000,
                            "volume": 3,
                            "trades": [...]
                        }
                    ]
                },
                "status": "success"
            }
        """
        # 엔드포인트 결정
        if full_period:
            endpoint = f"/api/v2/apts/{apt_id}/monthly-reports/more"
        else:
            endpoint = f"/api/v2/apts/{apt_id}/monthly-reports"

        params = {"tradeType": trade_type, "areaNo": area_no}

        return self._make_request(method="GET", endpoint=endpoint, params=params)

    def close(self) -> None:
        """세션 종료"""
        self.session.close()
        self.logger.info("API client session closed")

    def __enter__(self) -> "HogangnonoAPIClient":
        """Context manager 진입"""
        # Context manager 진입 시 자동으로 세션 초기화
        self._initialize_session()
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: types.TracebackType | None,
    ) -> None:
        """Context manager 종료

        Context manager에서 발생한 예외 정보는 무시하고 자원 정리만 수행합니다.

        Args:
            _exc_type: 발생한 예외의 타입 (사용하지 않음)
            _exc_val: 발생한 예외 객체 (사용하지 않음)
            _exc_tb: 예외의 traceback (사용하지 않음)
        """
        self.close()

    @retry_transient_errors(max_attempts=3, base_delay=1.0, max_delay=10.0)
    def fetch_ranks_rolling(self) -> dict[str, Any]:
        """인기 순위 롤링 데이터 조회

        Returns:
            API 응답 데이터
        """
        response = self._make_request(
            method="GET",
            endpoint="/api/v2/ranks/rolling",
        )

        if not response.success:
            raise Exception(f"Failed to fetch ranks/rolling: {response.error}")

        return response.data

    @retry_transient_errors(max_attempts=3, base_delay=1.0, max_delay=10.0)
    def fetch_pois_bounding(self, bounds: dict[str, float]) -> dict[str, Any]:
        """POI 데이터 조회 (Bounding box 기반)

        Args:
            bounds: 좌표 정보 (startX, endX, startY, endY)

        Returns:
            API 응답 데이터
        """
        # 실제 API 파라미터 형식에 맞게 전달
        params = {
            "level": 17,
            "startX": bounds["startX"],
            "endX": bounds["endX"],
            "startY": bounds["startY"],
            "endY": bounds["endY"],
            "isIgnorePin": False,
        }

        response = self._make_request(
            method="GET",
            endpoint="/api/v2/pois-bounding",
            params=params,
        )

        if not response.success:
            raise Exception(f"Failed to fetch pois-bounding: {response.error}")

        return response.data

    def parse_complexes_from_ranks(self, ranks_data: dict[str, Any]) -> list[dict[str, Any]]:
        """ranks/rolling 응답에서 단지 정보 파싱

        Args:
            ranks_data: ranks/rolling API 응답 데이터

        Returns:
            단지 정보 리스트
        """
        complexes = []

        # 실제 API 응답 구조: data.rolling
        if (
            not ranks_data
            or "data" not in ranks_data
            or "rolling" not in ranks_data.get("data", {})
        ):
            return complexes

        for item in ranks_data["data"]["rolling"]:
            complex_info = {
                "id": item.get("hash"),  # hash를 ID로 사용
                "aptName": item.get("name"),
                "region1": item.get("sidoName"),
                "region2": item.get("sigunguName"),
                "region3": item.get("dongName"),
                "address": item.get("regionName"),
                "ranking": item.get("rank"),
                "prevRank": item.get("prevRank"),
                "visitor": item.get("visitor"),
                "rankType": item.get("rankType"),
                "statusTag": item.get("statusTag"),
            }
            complexes.append(complex_info)

        return complexes

    def parse_pois_from_bounding(self, pois_data: dict[str, Any]) -> list[dict[str, Any]]:
        """pois-bounding 응답에서 POI 정보 파싱

        Args:
            pois_data: pois-bounding API 응답 데이터

        Returns:
            POI 정보 리스트
        """
        pois = []

        if not pois_data or "data" not in pois_data:
            return pois

        for item in pois_data["data"]:
            poi_info = {
                "id": item.get("id"),
                "name": item.get("name"),
                "lat": item.get("lat"),
                "lng": item.get("lng"),
                "type": item.get("type"),
                "region1": item.get("region1"),
                "region2": item.get("region2"),
                "region3": item.get("region3"),
                "address": item.get("address"),
                "buildDate": item.get("buildDate"),
                "households": item.get("households"),
                "floors": item.get("floors"),
                "elevatorCount": item.get("elevatorCount"),
                "parkingCount": item.get("parkingCount"),
                "heatingType": item.get("heatingType"),
                "totalFloorArea": item.get("totalFloorArea"),
                "totalSiteArea": item.get("totalSiteArea"),
            }
            pois.append(poi_info)

        return pois

    def to_csv_rows_complexes(self, complexes_data: dict[str, Any]) -> list[dict[str, Any]]:
        """단지 데이터를 CSV 행으로 변환

        Args:
            complexes_data: 단지 데이터

        Returns:
            CSV 행 리스트
        """
        rows = []
        complexes = self.parse_complexes_from_ranks(complexes_data)

        for complex_item in complexes:
            row = {
                "단지ID": complex_item["id"],
                "단지명": complex_item["aptName"],
                "시도": complex_item["region1"],
                "시군구": complex_item["region2"],
                "동": complex_item["region3"],
                "지역명": complex_item["address"],
                "순위": complex_item["ranking"],
                "이전순위": complex_item["prevRank"],
                "방문자수": complex_item["visitor"],
                "랭킹타입": complex_item["rankType"],
                "상태태그": complex_item["statusTag"],
            }
            rows.append(row)

        return rows

    def to_csv_rows_pois(self, pois_data: dict[str, Any]) -> list[dict[str, Any]]:
        """POI 데이터를 CSV 행으로 변환

        Args:
            pois_data: POI 데이터

        Returns:
            CSV 행 리스트
        """
        rows = []
        pois = self.parse_pois_from_bounding(pois_data)

        for poi in pois:
            row = {
                "POI_ID": poi["id"],
                "명칭": poi["name"],
                "위도": poi["lat"],
                "경도": poi["lng"],
                "유형": poi["type"],
                "시도코드": poi["region1"],
                "시군구코드": poi["region2"],
                "법정동코드": poi["region3"],
                "주소": poi["address"],
                "건축년도": poi["buildDate"],
                "세대수": poi["households"],
                "층수": poi["floors"],
                "승강기수": poi["elevatorCount"],
                "주차대수": poi["parkingCount"],
                "난방방식": poi["heatingType"],
                "연면적": poi["totalFloorArea"],
                "대지면적": poi["totalSiteArea"],
            }
            rows.append(row)

        return rows

    def fetch_apartments_by_pois(self, pois_response: dict[str, Any]) -> list[dict[str, Any]]:
        """POI 데이터를 기반으로 아파트 매물 정보 조회

        Args:
            pois_response: API 응답 데이터 (fetch_pois_bounding 결과)

        Returns:
            아파트 매물 정보 리스트
        """
        apartments = []

        # POI 데이터 추출
        pois_data = pois_response.get("data", [])

        # POI 데이터에서 아파트 식별
        for poi in pois_data:
            # 카테고리 1인 항목만 필터링
            if isinstance(poi, dict) and poi.get("category") == 1:
                apartment_info = {
                    "id": poi.get("id"),
                    "name": poi.get("name"),
                    "lat": poi.get("lat"),
                    "lng": poi.get("lng"),
                    "description": poi.get("description"),
                    "poi_data": poi,
                }
                apartments.append(apartment_info)

        return apartments

    def fetch_real_estate_apis(self) -> dict[str, Any]:
        """실제 부동산 API 테스트

        다양한 부동산 관련 API 엔드포인트를 테스트하여 작동하는 것을 찾습니다.

        Returns:
            API 응답 데이터
        """
        # 테스트할 엔드포인트 목록
        endpoints = [
            "/api/v2/ranks/rolling",
            "/api/v2/pois-bounding",
        ]

        results = {}

        for endpoint in endpoints:
            try:
                response = self._make_request(
                    method="GET",
                    endpoint=endpoint,
                )

                results[endpoint] = {
                    "success": response.success,
                    "status_code": response.status_code,
                    "data_count": len(response.data) if response.data else 0,
                    "has_data": bool(response.data),
                    "error": response.error,
                }

            except Exception as e:
                results[endpoint] = {"success": False, "error": str(e)}

        return results

    @retry_transient_errors(max_attempts=3, base_delay=1.0, max_delay=10.0)
    def search_apartments_by_location(
        self, center_lng: float, center_lat: float, delta: float = 0.02, level: int = 17
    ) -> dict[str, Any]:
        """위치 기반 아파트 검색

        Args:
            center_lng: 중심 경도
            center_lat: 중심 위도
            delta: 좌표 범위
            level: 줌 레벨

        Returns:
            검색 결과
        """
        # POI 데이터로부터 아파트 정보 조회
        bounds = {
            "startX": center_lng - delta,
            "endX": center_lng + delta,
            "startY": center_lat - delta,
            "endY": center_lat + delta,
        }

        # POI 데이터 가져오기
        pois_response = self.fetch_pois_bounding(bounds)

        if not pois_response or not pois_response.get("data"):
            return {"success": False, "error": "Failed to fetch POI data", "apartments": []}

        # POI에서 아파트 추출
        apartments = self.fetch_apartments_by_pois(pois_response)

        return {
            "success": True,
            "total_pois": len(pois_response.get("data", [])),
            "apartments": apartments,
            "bounds": bounds,
            "error": None,
        }

    def _get_headers(self) -> dict[str, str]:
        """API 호출용 헤더 생성 (테스트용)

        Returns:
            API 요청 헤더 딕셔너리
        """
        # 테스트에서는 간단한 헤더만 반환
        return {
            "User-Agent": getattr(self.config, "user_agent", "Mozilla/5.0"),
            "Accept": "application/json",
            "x-hogangnono-app-name": "hogangnono",
            "x-hogangnono-api-version": "2.4.0",
            "x-hogangnono-platform": "desktop",
        }

    @retry_transient_errors(max_attempts=3, base_delay=1.0, max_delay=10.0)
    def get_regions(self, region_code: Optional[str] = None) -> APIResponse:
        """시/도, 구/군 목록 조회

        Args:
            region_code: 특정 시/도 필터링 (예: "11" = 서울)

        Returns:
            APIResponse with regionList data

        Example Response:
            {
                "data": {
                    "regionList": [
                        {
                            "regionCode": "11",
                            "name": "서울",
                            "fullName": "서울특별시",
                            "children": [
                                {
                                    "regionCode": "11680",
                                    "name": "강남구",
                                    "fullName": "서울특별시 강남구"
                                }
                            ]
                        }
                    ]
                },
                "status": "success"
            }
        """
        params = {}
        if region_code:
            params["regionCode"] = region_code

        return self._make_request(method="GET", endpoint="/api/v2/regions", params=params)
