"""호갱노노 API 전용 클라이언트

호갱노노 API 엔드포인트에 접근하기 위한 전용 클라이언트를 제공합니다.
"""

import json
import time
import hashlib
import types
from dataclasses import dataclass
from typing import Any, Optional, List, Dict
from pathlib import Path

import requests
from requests import Response, Session
from structlog import get_logger

from crawler.config import CrawlerConfig
from ..utils.retry import retry_transient_errors, Retryable, BackoffStrategy, RetryError
from ..utils.enhanced_error_handler import EnhancedErrorHandler, CircuitBreaker
from ..models.api_responses import (
    POIInfo,
    RankingInfo,
    poi_info_from_bounding_response,
    ranking_info_from_rolling_response,
)

# Mock 객체 확인을 위한 임포트 (테스트 환경에서만 사용)
try:
    from unittest.mock import Mock
except ImportError:
    Mock = None

# Required headers per API guide
_REQUIRED_HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://hogangnono.com/",
    "Origin": "https://hogangnono.com",
}


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
        aptType: Optional[int] = -1,  # Restore default value for backward compatibility
        priceType: Optional[int] = 0,
        rentType: Optional[int] = 0,
        map: str = "google",
        bbox: Optional[tuple[float, float, float, float]] = None,
    ):
        # Initialize all attributes to avoid AttributeError
        self.startX = startX
        self.endX = endX
        self.startY = startY
        self.endY = endY
        self.level = level
        self.tradeType = tradeType
        self.areaFrom = areaFrom
        self.areaTo = areaTo
        self.priceFrom = priceFrom
        self.priceTo = priceTo
        self.map = map
        self.bbox = bbox
        self.aptType = aptType
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

        # 항상 포함
        params["map"] = self.map

        # aptType 포함
        if self.aptType is not None:
            params["aptType"] = self.aptType

        # priceType 포함
        if hasattr(self, "priceType") and self.priceType is not None:
            params["priceType"] = self.priceType

        # rentType 포함
        if hasattr(self, "rentType") and self.rentType is not None:
            params["rentType"] = self.rentType

        # 호갱노노 API 특정 파라미터
        params["screenWidth"] = 1200
        params["screenHeight"] = 924
        params["apt"] = ""  # 아파트 필터 (빈 문자열)

        return params


@dataclass
class APIResponse:
    """API 응답 래퍼 (기존 호환성 유지)

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
                        success=not http_error and data is not None,
                        data=data if not http_error and data is not None else None,
                        error=error_msg
                        if error_msg
                        else (
                            None
                            if not http_error and data is not None
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


@dataclass
class CacheEntry:
    """API 응답 캐시 항목"""

    data: Dict[str, Any]
    cached_at: float
    ttl: float = 3600.0  # 기본 1시간

    def is_expired(self) -> bool:
        """캐시 만료 여부 확인"""
        return time.time() > (self.cached_at + self.ttl)

    def to_response(self, status_code: int = 200) -> "APIResponse":
        """캐시된 데이터를 APIResponse로 변환"""
        return APIResponse(
            success=True,
            data=self.data,
            status_code=status_code,
        )


class APIResponseCache:
    """API 응답 캐시 관리자"""

    def __init__(self, cache_dir: Optional[Path] = None):
        """캐시 초기화

        Args:
            cache_dir: 캐시 디렉토리 (None이면 메모리 캐시만 사용)
        """
        self.cache_dir = cache_dir
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.logger = get_logger().bind(component="APIResponseCache")

        # 캐시 디렉토리 생성
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _generate_cache_key(
        self, method: str, url: str, params: Optional[Dict] = None, data: Optional[Dict] = None
    ) -> str:
        """요청에 대한 캐시 키 생성"""
        key_data = {
            "method": method,
            "url": url,
            "params": params or {},
            "data": data or {},
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(
        self, method: str, url: str, params: Optional[Dict] = None, data: Optional[Dict] = None
    ) -> Optional[APIResponse]:
        """캐시된 응답 가져오기"""
        cache_key = self._generate_cache_key(method, url, params, data)

        # 메모리 캐시 확인
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if not entry.is_expired():
                self.logger.debug("cache_hit_memory", cache_key=cache_key[:8])
                return entry.to_response()
            else:
                del self.memory_cache[cache_key]

        # 파일 캐시 확인
        if self.cache_dir:
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        cache_data = json.load(f)
                    entry = CacheEntry(**cache_data)
                    if not entry.is_expired():
                        # 메모리에도 로드
                        self.memory_cache[cache_key] = entry
                        self.logger.debug("cache_hit_file", cache_key=cache_key[:8])
                        return entry.to_response()
                    else:
                        cache_file.unlink()  # 만료된 파일 삭제
                except Exception as e:
                    self.logger.warning(
                        "cache_file_read_failed", cache_key=cache_key[:8], error=str(e)
                    )
                    try:
                        cache_file.unlink()  # 손상된 파일 삭제
                    except (OSError, PermissionError):
                        pass

        return None

    def set(
        self,
        method: str,
        url: str,
        response: APIResponse,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        ttl: Optional[float] = None,
    ) -> None:
        """응답 캐시에 저장"""
        if not response.success or not response.data:
            return  # 실패한 응답은 캐싱하지 않음

        cache_key = self._generate_cache_key(method, url, params, data)
        entry = CacheEntry(data=response.data, cached_at=time.time(), ttl=ttl or 3600.0)

        # 메모리에 저장
        self.memory_cache[cache_key] = entry

        # 파일에 저장
        if self.cache_dir:
            cache_file = self.cache_dir / f"{cache_key}.json"
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(entry.__dict__, f, ensure_ascii=False, indent=2)
                self.logger.debug("cache_saved", cache_key=cache_key[:8])
            except Exception as e:
                self.logger.warning(
                    "cache_file_write_failed", cache_key=cache_key[:8], error=str(e)
                )

    def clear(self) -> None:
        """캐시 비우기"""
        self.memory_cache.clear()
        if self.cache_dir and self.cache_dir.exists():
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                except (OSError, PermissionError):
                    pass
        self.logger.info("cache_cleared")

    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 정보"""
        memory_count = len(self.memory_cache)
        file_count = 0
        if self.cache_dir and self.cache_dir.exists():
            file_count = len(list(self.cache_dir.glob("*.json")))

        return {
            "memory_entries": memory_count,
            "file_entries": file_count,
            "cache_dir": str(self.cache_dir) if self.cache_dir else None,
        }


class HogangnonoAPIClient:
    """호갱노노 API 클라이언트

    호갱노노 API와의 통신을 처리합니다.
    """

    def __init__(self, config: CrawlerConfig, cache_dir: Optional[Path] = None):
        """클라이언트 초기화

        Args:
            config: 크롤러 설정 객체
            cache_dir: API 응답 캐시 디렉토리
        """
        self.config = config
        self.base_url = "https://hogangnono.com"
        self.session = Session()

        # 초기화 상태 추적
        self._session_initialized = False

        self.logger = get_logger()

        # Rate limiting - 단일 AdaptiveRateLimiter
        from ..rate_limiter import AdaptiveRateLimiter

        self.rate_limiter = AdaptiveRateLimiter(
            initial_delay=2.0,  # API 가이드에 따라 5.0에서 2.0으로 변경
            min_delay=1.0,  # API 가이드에 따라 1.5에서 1.0으로 변경
            max_delay=10.0,
        )

        # API 응답 캐시
        self.cache = APIResponseCache(cache_dir)

        # API 응답 통계
        self.response_stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "success_count": 0,
            "error_count": 0,
            "error_types": {},
            "average_response_time": 0.0,
            "response_times": [],
        }

        # 네트워크 설정
        self.timeout = config.timeout if hasattr(config, "timeout") else 30
        self.max_retries = config.max_retries if hasattr(config, "max_retries") else 3

        # API 에러 타입 정의
        self.ERROR_TYPES = {
            "NETWORK_ERROR": "네트워크 오류",
            "TIMEOUT": "요청 시간 초과",
            "HTTP_ERROR": "HTTP 에러",
            "API_ERROR": "API 비즈니스 로직 에러",
            "INVALID_RESPONSE": "유효하지 않은 응답",
            "PARSE_ERROR": "응답 파싱 에러",
            "RATE_LIMIT": "요청 제한 초과",
            "AUTH_ERROR": "인증 에러",
        }

        # 개선된 에러 핸들러 초기화
        self.error_handler = EnhancedErrorHandler(max_retries=self.max_retries, retry_delay=1.0)

        # 서킷 브레이커 초기화
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=10,  # 10번 실패 후 열림
            timeout=60,  # 60초 후 재시도
        )

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
        headers = {
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
            **_REQUIRED_HEADERS,  # Ensure all required headers are included
        }
        return headers

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
        use_cache: bool = True,
        cache_ttl: Optional[float] = None,
    ) -> APIResponse:
        """HTTP 요청 실행 (캐싱, 재시도, 서킷 브레이커 포함)

        Args:
            method: HTTP 메서드
            endpoint: API 엔드포인트
            params: 쿼리 파라미터
            data: 요청 데이터
            headers: 추가 헤더
            use_cache: 캐시 사용 여부
            cache_ttl: 캐시 유효시간 (초)

        Returns:
            API 응답 객체
        """
        # 통계 기록
        self.response_stats["total_requests"] += 1
        start_time = time.time()

        # 캐시 확인 (GET 요청만)
        if use_cache and method.upper() == "GET":
            cached_response = self.cache.get(method, endpoint, params, data)
            if cached_response:
                self.response_stats["cache_hits"] += 1
                self.logger.debug("api_response_cache_hit", endpoint=endpoint)
                return cached_response
            self.response_stats["cache_misses"] += 1

        # Rate limiting 적용
        self.rate_limiter.wait()

        # 세션이 초기화되지 않았다면 초기화
        if not self._session_initialized:
            if not self._initialize_session():
                return self._create_error_response(
                    "Failed to initialize session", "INIT_ERROR", None
                )

        # 서킷 브레이커 확인
        if self.circuit_breaker.state == "OPEN":
            if self.circuit_breaker._should_attempt_reset():
                self.circuit_breaker.state = "HALF_OPEN"
                self.logger.info(
                    "circuit_breaker_half_open",
                    endpoint=endpoint,
                    timeout=self.circuit_breaker.timeout,
                )
            else:
                self.logger.warning(
                    "circuit_breaker_open",
                    endpoint=endpoint,
                    last_failure_time=self.circuit_breaker.last_failure_time,
                )
                return self._create_error_response(
                    "Circuit breaker is OPEN - too many failures", "CIRCUIT_BREAKER_OPEN", 503
                )

        # 개선된 재시도 로직 적용
        retryable = Retryable(
            max_attempts=self.max_retries + 1,
            base_delay=1.0,
            max_delay=30.0,
            strategy=BackoffStrategy.EXPONENTIAL,
            jitter=True,
            exponential_base=2.0,
            retry_on=(
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                requests.exceptions.HTTPError,
                Exception,
            ),
            retry_on_predicate=self._is_retryable_error,
            stop_on=(requests.exceptions.HTTPError,),
        )

        try:
            # 재시도 가능한 함수 정의
            def make_http_request():
                url = self._build_url(endpoint)
                request_headers = self._add_auth_headers(headers)

                # 요청 전 로깅
                self.logger.debug(
                    "api_request",
                    method=method,
                    endpoint=endpoint,
                    url=url,
                )

                # HTTP 요청 실행
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    headers=request_headers,
                    timeout=self.timeout,
                )

                # 응답 처리
                api_response = APIResponse.from_response(response)

                # 404 에러는 예외 처리로 변환하여 재시도 로직에서 처리되지 않도록 함
                if api_response.status_code == 404:
                    raise requests.exceptions.HTTPError("404 Not Found", response=response)

                # 응답 데이터 검증
                if api_response.success and api_response.data:
                    api_response = self._validate_response_data(api_response)

                return api_response

            # 재시도 가능한 HTTP 요청 실행
            api_response = retryable.execute(make_http_request)

            # 성공 시 캐시 저장
            if api_response.success and api_response.data and method.upper() == "GET":
                self.cache.set(method, endpoint, api_response, params, data, cache_ttl)

            # 통계 업데이트
            response_time = time.time() - start_time
            self._update_response_stats(api_response, response_time)

            # 서킷 브레이커 성공 처리
            self.circuit_breaker._on_success()

            # 에러 핸들러에 성공 기록
            apartment_id = self._extract_apartment_id(endpoint, params)
            if apartment_id:
                self.error_handler.id_filter.mark_validated(apartment_id)

            return api_response

        except requests.exceptions.HTTPError as e:
            response = getattr(e, "response", None)
            status_code = response.status_code if response else None

            # 404는 즉시 반환 (재시도 안 함)
            if status_code == 404:
                api_response = APIResponse(success=False, error="404 Not Found", status_code=404)
                self._update_response_stats(api_response, time.time() - start_time)

                # 에러 핸들러에 404 기록
                apartment_id = self._extract_apartment_id(endpoint, params)
                if apartment_id:
                    self.error_handler.handle_error(
                        success=api_response.success,
                        status_code=api_response.status_code,
                        error_message=api_response.error,
                        apartment_id=apartment_id,
                    )

                return api_response

            # 429 에러 처리
            elif status_code == 429:
                self.logger.warning(
                    "rate_limit_hit",
                    endpoint=endpoint,
                    retry_after=response.headers.get("Retry-After") if response else None,
                )
                self._handle_rate_limit(
                    APIResponse(
                        success=False,
                        error="Rate limit exceeded",
                        status_code=429,
                        data=response.json() if response and hasattr(response, "json") else None,
                    )
                )
                # 재시도는 retryable이 처리
                raise

            # 기타 HTTP 에러
            else:
                self.circuit_breaker._on_failure()
                raise

        except Exception as e:
            # 서킷 브레이커 실패 처리
            self.circuit_breaker._on_failure()

            # 에러 응답 생성
            error_msg = str(e)
            error_type = "UNKNOWN_ERROR"

            if isinstance(e, requests.exceptions.Timeout):
                error_type = "TIMEOUT"
            elif isinstance(e, requests.exceptions.ConnectionError):
                error_type = "NETWORK_ERROR"
            elif isinstance(e, RetryError):
                error_type = "MAX_RETRIES_EXCEEDED"
                error_msg = f"Max retries exceeded: {str(e)}"

            error_response = self._create_error_response(error_msg, error_type, None)

            # 통계 업데이트
            response_time = time.time() - start_time
            self._update_response_stats(error_response, response_time)

            # 에러 핸들러에 기록
            apartment_id = self._extract_apartment_id(endpoint, params)
            if apartment_id:
                self.error_handler.handle_error(
                    success=error_response.success,
                    status_code=error_response.status_code,
                    error_message=error_response.error,
                    apartment_id=apartment_id,
                )

            return error_response

    def _validate_response_data(self, api_response: APIResponse) -> APIResponse:
        """API 응답 데이터 검증

        데이터 구조 분석 및 유효성 검사
        """
        if not api_response.data:
            return api_response

        data = api_response.data

        try:
            # 데이터 정제 적용
            from ..validators import sanitize_api_data, validate_api_response

            # 데이터 정제
            sanitized_data = sanitize_api_data(data, "unknown")
            if sanitized_data != data:
                self.logger.warning("data_sanitized", changes="malformed data fixed")
                data = sanitized_data
                api_response.data = sanitized_data

            # 응답 데이터 구조 분석
            structure_info = {
                "data_type": type(data).__name__,
                "has_list": isinstance(data, list),
                "has_dict": isinstance(data, dict),
                "list_length": len(data) if isinstance(data, list) else None,
                "dict_keys": list(data.keys())[:10] if isinstance(data, dict) else None,
                "sample_items": None,
            }

            # 샘플 데이터 추출
            if isinstance(data, list) and data:
                structure_info["sample_items"] = data[:3]
            elif isinstance(data, dict):
                if "data" in data and isinstance(data["data"], list):
                    structure_info["sample_items"] = data["data"][:3]
                elif "items" in data and isinstance(data["items"], list):
                    structure_info["sample_items"] = data["items"][:3]

            # 로깅
            self.logger.info(
                "api_response_structure",
                endpoint=api_response.status_code,
                structure=structure_info,
            )

            # 스키마 기반 검증
            response_type = self._detect_response_type(data)
            validation_report = validate_api_response(data, response_type)

            # 에러 처리 - 심각한 에러가 있는 경우 처리를 중단
            if validation_report.has_errors():
                errors = validation_report.get_errors()
                critical_errors = [e for e in errors if e.severity.value == "critical"]

                if critical_errors:
                    # Critical 에러가 있으면 응답을 실패로 처리
                    error_messages = [e.message for e in critical_errors]
                    self.logger.error(
                        "api_response_critical_validation_errors",
                        error_count=len(critical_errors),
                        errors=error_messages,
                    )
                    return APIResponse(
                        success=False,
                        error=f"Critical validation errors: {'; '.join(error_messages)}",
                        status_code=api_response.status_code,
                        data=None,
                    )

                # 일반 에러가 있으면 경고 로그와 함께 계속 진행
                non_critical_errors = [e for e in errors if e.severity.value != "critical"]
                if non_critical_errors:
                    self.logger.warning(
                        "api_response_validation_errors",
                        error_count=len(non_critical_errors),
                        errors=[e.message for e in non_critical_errors[:5]],  # 처음 5개 에러만
                    )

            # 경고 로깅
            warnings = validation_report.get_warnings()
            if warnings:
                self.logger.info(
                    "api_response_validation_warnings",
                    warning_count=len(warnings),
                    warnings=[w.message for w in warnings[:3]],  # 처음 3개 경고만
                )

            # POI 데이터 분석
            if isinstance(data, list):
                poi_analysis = self._analyze_poi_data(data)
                if poi_analysis:
                    self.logger.info("poi_data_analysis", **poi_analysis)
            elif isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
                poi_analysis = self._analyze_poi_data(data["data"])
                if poi_analysis:
                    self.logger.info("poi_data_analysis", **poi_analysis)

        except Exception as e:
            # 검증 중 에러가 발생하면 응답을 실패로 처리
            self.logger.error(
                "response_validation_failed", error=str(e), error_type=type(e).__name__
            )
            return APIResponse(
                success=False,
                error=f"Response validation failed: {str(e)}",
                status_code=api_response.status_code,
                data=None,
            )

        return api_response

    def _detect_response_type(self, data: Any) -> str:
        """응답 타입 감지"""
        if not data:
            return "unknown"

        # 리스트 형태이면 POI
        if isinstance(data, list):
            # 첫 항목으로 POI인지 확인
            if data and isinstance(data[0], dict):
                first_item = data[0]
                if all(k in first_item for k in ["id", "lat", "lng"]):
                    return "poi"
            return "list"

        # 딕셔너리 형태
        if isinstance(data, dict):
            # 키로 응답 타입 추정
            if "data" in data:
                if isinstance(data["data"], list):
                    return "poi"
                elif isinstance(data["data"], dict):
                    # 단지 정보 특징
                    inner = data["data"]
                    if any(k in inner for k in ["complexNo", "complexName", "buildYear"]):
                        return "complex"
                    # 거래 정보 특징
                    elif any(k in inner for k in ["shortTermReport", "monthlyReport", "tradeType"]):
                        return "transaction"

            # 최상위 키로 판단
            if any(k in data for k in ["complexNo", "complexName", "name", "buildYear"]):
                return "complex"
            elif any(k in data for k in ["shortTermReport", "reports", "transactions"]):
                return "transaction"

        return "unknown"

    def _analyze_poi_data(self, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """POI 데이터 분석"""
        if not data_list:
            return {}

        analysis = {
            "total_items": len(data_list),
            "poi_types": {},
            "has_apartments": False,
            "has_transit": False,
            "has_facilities": False,
            "id_patterns": {},
        }

        # 첫 100개 항목만 분석 (성능 고려)
        sample_size = min(100, len(data_list))
        for item in data_list[:sample_size]:
            # ID 패턴 분석
            item_id = str(item.get("id", ""))
            if item_id:
                if item_id.isdigit():
                    analysis["id_patterns"]["numeric"] = (
                        analysis["id_patterns"].get("numeric", 0) + 1
                    )
                elif item_id.startswith("APT_"):
                    analysis["id_patterns"]["apt_prefixed"] = (
                        analysis["id_patterns"].get("apt_prefixed", 0) + 1
                    )
                else:
                    analysis["id_patterns"]["other"] = analysis["id_patterns"].get("other", 0) + 1

            # POI 타입 분석
            name = item.get("name", "").lower()
            category = item.get("category", "")

            if "역" in name or "station" in name or category == 2:
                analysis["has_transit"] = True
                analysis["poi_types"]["transit"] = analysis["poi_types"].get("transit", 0) + 1
            elif any(keyword in name for keyword in ["아파트", "apt"]) or category == 1:
                analysis["has_apartments"] = True
                analysis["poi_types"]["apartment"] = analysis["poi_types"].get("apartment", 0) + 1
            elif any(keyword in name for keyword in ["병원", "hospital", "마트", "mart"]):
                analysis["has_facilities"] = True
                analysis["poi_types"]["facility"] = analysis["poi_types"].get("facility", 0) + 1

        return analysis

    def _create_error_response(
        self, error_msg: str, error_type: str, status_code: Optional[int]
    ) -> APIResponse:
        """에러 응답 생성"""
        # 에러 타입 통계 업데이트
        self.response_stats["error_count"] += 1
        if error_type not in self.response_stats["error_types"]:
            self.response_stats["error_types"][error_type] = 0
        self.response_stats["error_types"][error_type] += 1

        self.logger.error(
            "api_request_failed",
            error_type=error_type,
            error_message=error_msg,
            status_code=status_code,
        )

        return APIResponse(
            success=False,
            error=error_msg,
            status_code=status_code,
        )

    def _update_response_stats(self, api_response: APIResponse, response_time: float):
        """응답 통계 업데이트"""
        if api_response.success:
            self.response_stats["success_count"] += 1

        # 응답 시간 기록
        self.response_stats["response_times"].append(response_time)
        # 최근 100개 응답 시간만 유지
        if len(self.response_stats["response_times"]) > 100:
            self.response_stats["response_times"] = self.response_stats["response_times"][-100:]

        # 평균 응답 시간 계산
        if self.response_stats["response_times"]:
            self.response_stats["average_response_time"] = sum(
                self.response_stats["response_times"]
            ) / len(self.response_stats["response_times"])

    def _handle_rate_limit(self, api_response: APIResponse):
        """Rate limit 에러 처리"""
        retry_after = api_response.status_code
        if api_response.data and isinstance(api_response.data, dict):
            retry_after = api_response.data.get("retryAfter", retry_after)

        # Rate limiter에 지연 시간 증가
        current_delay = self.rate_limiter.current_delay
        new_delay = min(current_delay * 2, 30.0)  # 최대 30초
        self.rate_limiter.update_delay(new_delay)

        self.logger.warning(
            "api_rate_limit_hit",
            retry_after=retry_after,
            new_delay=new_delay,
        )

        # 대기
        time.sleep(new_delay)

    def get_api_stats(self) -> Dict[str, Any]:
        """API 통계 정보 반환"""
        stats = self.response_stats.copy()

        # 캐시 통계 추가
        stats.update(self.cache.get_stats())

        # 성공률 계산
        if stats["total_requests"] > 0:
            stats["success_rate"] = stats["success_count"] / stats["total_requests"]
            stats["cache_hit_rate"] = stats["cache_hits"] / stats["total_requests"]
        else:
            stats["success_rate"] = 0.0
            stats["cache_hit_rate"] = 0.0

        # Rate limiter 정보
        stats["rate_limiter"] = {
            "current_delay": self.rate_limiter.current_delay,
            "min_delay": self.rate_limiter.min_delay,
            "max_delay": self.rate_limiter.max_delay,
        }

        return stats

    def clear_cache(self):
        """API 응답 캐시 비우기"""
        self.cache.clear()
        self.logger.info("api_cache_cleared")

    def reset_stats(self):
        """API 통계 초기화"""
        self.response_stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "success_count": 0,
            "error_count": 0,
            "error_types": {},
            "average_response_time": 0.0,
            "response_times": [],
        }
        self.logger.info("api_stats_reset")

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

        # 호갱노노 API 엔드포인트 (POI 기반)
        # apt/bounding and search/apartments endpoints don't work
        # We need to use pois-bounding with better filtering
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

    def get_apartment_detail(self, apt_id: str) -> APIResponse:
        """아파트 상세 정보 조회

        DEPRECATED: 상세 정보 엔드포인트는 존재하지 않음.
        대신 get_apartment_transactions를 사용하세요.

        Args:
            apt_id: 아파트 ID (aptHash)

        Returns:
            APIResponse 객체 (get_apartment_transactions 호출 결과)
        """
        # This endpoint has been replaced - redirect to monthly-reports
        return self.get_apartment_transactions(apt_id=apt_id, trade_type=0, area_no=0)

    @retry_transient_errors(max_attempts=3, base_delay=1.0, max_delay=10.0)
    def get_apartment_transactions(
        self, apt_id: str, trade_type: int = 1, area_no: int = 201, full_period: bool = False
    ) -> APIResponse:
        """실거래 내역 조회

        Args:
            apt_id: 단지 ID (aptHash)
            trade_type: 1=매매, 0=전세, 2=월세 (기본값: 매매)
            area_no: 면적 필터 (201=33㎡, 기본값: 201)
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

    def get_complexes_by_district(self, district_code: str) -> APIResponse:
        """구/군별 단지 목록 조회

        Args:
            district_code: 구/군 코드

        Returns:
            APIResponse 객체
        """
        params = {
            "districtCode": district_code,
        }

        return self._make_request(
            method="GET",
            endpoint="/api/apt/by-district",
            params=params,
        )

    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if an error is retryable

        Args:
            error: Exception to check

        Returns:
            True if error is retryable
        """
        error_msg = str(error).lower()

        # Check for retryable error patterns
        retryable_patterns = [
            "timeout",
            "connection",
            "network",
            "temporary",
            "502",  # Bad gateway
            "503",  # Service unavailable
            "504",  # Gateway timeout
        ]

        return any(pattern in error_msg for pattern in retryable_patterns)

    def _extract_apartment_id(self, endpoint: str, params: Optional[dict] = None) -> Optional[str]:
        """Extract apartment ID from endpoint and parameters

        Args:
            endpoint: API endpoint
            params: Request parameters

        Returns:
            Apartment ID if found
        """
        # Check endpoint pattern for apartment ID
        if "/apts/" in endpoint:
            parts = endpoint.split("/apts/")
            if len(parts) > 1:
                apt_id = parts[1].split("/")[0]
                return apt_id

        # Check parameters for apartment ID
        if params:
            for key in ["complexNo", "apt_id", "apartmentId"]:
                if key in params:
                    return str(params[key])

        return None

    def get_error_summary(self) -> dict[str, Any]:
        """Get comprehensive error summary

        Returns:
            Error summary including statistics and recommendations
        """
        return self.error_handler.get_error_summary()

    def get_circuit_breaker_status(self) -> dict[str, Any]:
        """Get current circuit breaker status

        Returns:
            Circuit breaker state and statistics
        """
        return {
            "state": self.circuit_breaker.state,
            "failure_count": self.circuit_breaker.failure_count,
            "failure_threshold": self.circuit_breaker.failure_threshold,
            "timeout": self.circuit_breaker.timeout,
            "last_failure_time": self.circuit_breaker.last_failure_time,
            "is_open": self.circuit_breaker.state == "OPEN",
            "is_half_open": self.circuit_breaker.state == "HALF_OPEN",
            "is_closed": self.circuit_breaker.state == "CLOSED",
        }

    def reset_circuit_breaker(self):
        """Manually reset circuit breaker to CLOSED state"""
        self.circuit_breaker.failure_count = 0
        self.circuit_breaker.state = "CLOSED"
        self.circuit_breaker.last_failure_time = None
        self.logger.info("circuit_breaker_manually_reset")

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

    def parse_complexes_from_ranks(self, ranks_data: dict[str, Any]) -> List[RankingInfo]:
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
            ranking_info = ranking_info_from_rolling_response(item)
            complexes.append(ranking_info)

        return complexes

    def parse_pois_from_bounding(self, pois_data: dict[str, Any]) -> List[POIInfo]:
        """pois-bounding 응답에서 POI 정보 파싱

        Args:
            pois_data: pois-bounding API 응답 데이터

        Returns:
            POI 정보 리스트
        """
        pois = []

        if not pois_data or "data" not in pois_data:
            return pois

        # Count different types for logging
        type_counts = {"total": 0, "apartments": 0, "transit": 0, "facilities": 0, "others": 0}

        for item in pois_data["data"]:
            poi_info = poi_info_from_bounding_response(item)
            type_counts["total"] += 1

            # Count types for analysis
            if poi_info.is_transit():
                type_counts["transit"] += 1
            elif poi_info.is_facility():
                type_counts["facilities"] += 1
            elif poi_info.is_apartment():
                type_counts["apartments"] += 1
            else:
                type_counts["others"] += 1

            # Only include valid apartments
            if poi_info.validate_for_apartment_crawling():
                pois.append(poi_info)

        # Log filtering results
        self.logger.info(
            "poi_filtering_results",
            total_items=type_counts["total"],
            apartments_found=type_counts["apartments"],
            transit_count=type_counts["transit"],
            facilities_count=type_counts["facilities"],
            valid_apartments=len(pois),
            filtering_ratio=len(pois) / type_counts["total"] if type_counts["total"] > 0 else 0,
        )

        return pois

    def to_csv_rows_complexes(self, complexes_data: dict[str, Any]) -> List[dict[str, Any]]:
        """단지 데이터를 CSV 행으로 변환

        Args:
            complexes_data: 단지 데이터

        Returns:
            CSV 행 리스트
        """
        from ..models.csv_models import RankingCSVRow

        rows = []
        complexes = self.parse_complexes_from_ranks(complexes_data)

        for complex_item in complexes:
            csv_row = RankingCSVRow.from_ranking_info(complex_item)
            rows.append(csv_row.to_dict())

        return rows

    def to_csv_rows_pois(self, pois_data: dict[str, Any]) -> List[dict[str, Any]]:
        """POI 데이터를 CSV 행으로 변환

        Args:
            pois_data: POI 데이터

        Returns:
            CSV 행 리스트
        """
        from ..models.csv_models import POICSVRow

        rows = []
        pois = self.parse_pois_from_bounding(pois_data)

        for poi in pois:
            csv_row = POICSVRow.from_poi_info(poi)
            rows.append(csv_row.to_dict())

        return rows

    def fetch_apartments_by_pois(self, pois_response: dict[str, Any]) -> list[dict[str, Any]]:
        """API 응답에서 아파트 데이터 추출

        Args:
            pois_response: API 응답 데이터 (get_apartments_bounding 결과)

        Returns:
            아파트 매물 정보 리스트
        """
        apartments = []

        # Parse POIs and filter for apartments only
        pois = self.parse_pois_from_bounding(pois_response)

        # Convert POIInfos to apartment dict format
        for poi in pois:
            # Only process valid apartments
            if not poi.validate_for_apartment_crawling():
                continue

            apartment_info = {
                "id": poi.id,
                "name": poi.name,
                "lat": poi.lat,
                "lng": poi.lng,
                "address": poi.address,
                "build_year": poi.build_date,  # POI uses build_date
                "households": poi.households,
                "floors": poi.floors,
                "raw_data": poi.__dict__,  # Store the POI object data
            }
            apartments.append(apartment_info)

        self.logger.info(
            "apartments_extracted_from_pois",
            total_pois=len(pois_response.get("data", [])),
            valid_apartments=len(apartments),
        )

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
            [
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
        """
        params = {}
        if region_code:
            params["regionCode"] = region_code

        # regions API는 인증 헤더가 필요 없으므로 간단한 헤더 사용
        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "application/json",
        }

        response = self._make_request(
            method="GET", endpoint="/api/v2/regions", params=params, headers=headers
        )

        # 응답 데이터가 리스트 형태인지 확인
        if response.success and response.data:
            if isinstance(response.data, list):
                # 리스트 형태로 반환되면 그대로 사용
                pass
            elif isinstance(response.data, dict) and "data" in response.data:
                # data 객체에서 regionList 추출
                if "regionList" in response.data["data"]:
                    response.data = response.data["data"]["regionList"]
                else:
                    # data 객체가 있지만 regionList가 없는 경우 원본 데이터 유지
                    pass
            else:
                # 예상치 못한 구조인 경우 원본 데이터 유지
                pass

        return response

    def fetch_dong_codes(
        self, district_name: str, lat: float = None, lng: float = None
    ) -> dict[str, str]:
        """API를 통해 동 코드 정보 가져오기

        Args:
            district_name: 구/군 이름
            lat: 위도 (선택사항)
            lng: 경도 (선택사항)

        Returns:
            동 이름과 코드의 매핑 딕셔너리
        """
        search_url = "https://hogangnono.com/api/v2/searches/new"
        params = {"query": district_name}
        if lat is not None:
            params["y"] = lat
        if lng is not None:
            params["x"] = lng

        try:
            response = self._make_request("GET", search_url, params=params, timeout=10)

            if not response.success or not response.data:
                self.logger.error(
                    "fetch_dong_codes_failed", district=district_name, error=response.error
                )
                return {}

            data = response.data

            if data.get("status") != "success":
                return {}

            dongs = {}
            # The matched data is nested inside data.data
            matched = data.get("data", {}).get("matched", {})

            if "region" in matched:
                for item in matched["region"].get("list", []):
                    if item.get("local_type") == "local3":  # 동 정보
                        dong_name = item.get("local3_name", "")
                        dong_code = item.get("local3_code", "")
                        if dong_name and dong_code:
                            dongs[dong_name] = dong_code

            return dongs

        except Exception as e:
            self.logger.error("fetch_dong_codes_error", district=district_name, error=str(e))
            return {}
