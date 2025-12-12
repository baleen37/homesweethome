"""Base API client to eliminate common functionality duplication."""

import time
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, Dict
from pathlib import Path
import json

import requests
from requests import Response, Session
from structlog import get_logger

from crawler.config import Config, USER_AGENT
from ..utils.retry import Retryable, BackoffStrategy, RetryError
from ..utils.enhanced_error_handler import EnhancedErrorHandler, CircuitBreaker


@dataclass
class APIResponse:
    """API 응답 래퍼"""

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
            return cls(
                success=False,
                error=f"Unexpected error: {str(e)}",
                status_code=None,
            )

        # headers 접근 (예외 처리 포함)
        try:
            headers = response.headers
            content_type = ""
            if hasattr(headers, "get") and callable(getattr(headers, "get", None)):
                content_type = headers.get("content-type", "")
                if content_type:
                    content_type = content_type.lower()
        except Exception:
            content_type = ""

        try:
            # Content-Type 확인
            if "application/json" in content_type:
                # JSON 응답 처리
                data = response.json()

                # 호갱노노 API 응답 구조 확인
                if isinstance(data, dict) and "success" in data:
                    api_success = data.get("success", True)
                    http_error = status_code is not None and status_code >= 400

                    error_msg = data.get("error")
                    if http_error:
                        if error_msg:
                            error_msg = f"HTTP error: {status_code} - {error_msg}"
                        else:
                            if "message" in data:
                                error_msg = f"HTTP error: {status_code} - {data['message']}"
                            else:
                                error_msg = f"HTTP error: {status_code}"

                    return cls(
                        success=api_success and not http_error,
                        data=data.get("data"),
                        error=error_msg,
                        status_code=status_code,
                    )
                else:
                    # 직접 데이터 반환 경우
                    http_error = status_code is not None and status_code >= 400

                    error_msg = None
                    if http_error and isinstance(data, dict) and "message" in data:
                        error_msg = f"HTTP error: {status_code} - {data['message']}"

                    return cls(
                        success=not http_error and data is not None,
                        data=data if not http_error and data is not None else None,
                        error=error_msg
                        if error_msg
                        else (
                            None
                            if not http_error and data is not None
                            else f"HTTP error: {status_code}"
                        ),
                        status_code=status_code,
                    )
            else:
                # HTML 또는 텍스트 응답 처리
                if status_code == 200:
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
            if status_code == 200:
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
                error_msg = f"JSON decode error: {str(e)}"
                if status_code is not None:
                    error_msg = f"HTTP error: {status_code} - {error_msg}"
                return cls(
                    success=False,
                    error=error_msg,
                    status_code=status_code,
                )
        except Exception as e:
            return cls(
                success=False,
                error=f"Unexpected error: {str(e)}",
                status_code=status_code,
            )


class BaseAPIClient(ABC):
    """Base API client to eliminate common functionality duplication."""

    def __init__(self, config: Config, base_url: str, cache_dir: Optional[Path] = None):
        """초기화

        Args:
            config: 크롤러 설정 객체
            base_url: API 기본 URL
            cache_dir: API 응답 캐시 디렉토리
        """
        self.config = config
        self.base_url = base_url
        self.session = Session()
        self._session_initialized = False
        self.logger = get_logger()

        # Rate limiting
        from ..rate_limiter import AdaptiveRateLimiter

        self.rate_limiter = AdaptiveRateLimiter(
            initial_delay=2.0,
            min_delay=1.0,
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
        self.timeout = config.TIMEOUT
        self.max_retries = config.RETRY_ATTEMPTS

        # 개선된 에러 핸들러 초기화
        self.error_handler = EnhancedErrorHandler(max_retries=self.max_retries, retry_delay=1.0)

        # 서킷 브레이커 초기화
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=10,
            timeout=60,
        )

    @abstractmethod
    def get_required_headers(self) -> Dict[str, str]:
        """필수 헤더를 반환해야 하는 추상 메서드"""
        pass

    def _build_url(self, endpoint: str) -> str:
        """전체 URL 빌드

        Args:
            endpoint: API 엔드포인트 경로

        Returns:
            완전한 URL 문자열
        """
        # endpoint가 슬래시로 시작하지 않으면 슬래시 추가
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        return f"{self.base_url}{endpoint}"

    def _get_common_headers(self) -> Dict[str, str]:
        """공통 헤더 생성

        모든 API 요청에 포함될 기본 HTTP 헤더를 생성합니다.
        실제 브라우저처럼 보이기 위한 User-Agent와 보안 관련 헤더 포함.

        Returns:
            HTTP 헤더 딕셔너리
        """
        return {
            "User-Agent": USER_AGENT,  # 브라우저 User-Agent 흉내
            "Accept": "application/json, text/plain, */*",  # 응답 타입 지정
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",  # 언어 우선순위
            "Accept-Encoding": "gzip, deflate, br",  # 압축 지원
            "Cache-Control": "no-cache",  # 캐시 방지
            "Pragma": "no-cache",  # 구버전 브라우저 캐시 방지
            # Chrome 보안 헤더들 (실제 브라우저처럼 보이기 위함)
            "Sec-Ch-Ua": '"Not.A/Brand";v="8", "Chromium";v="114"',
            "Sec-Ch-Ua-Mobile": "?0",  # 모바일 여부 (0: 데스크탑)
            "Sec-Ch-Ua-Platform": '"macOS"',  # 플랫폼 정보
            "Sec-Fetch-Dest": "empty",  # 요청 대상
            "Sec-Fetch-Mode": "cors",  # 요청 모드
            "Sec-Fetch-Site": "same-origin",  # 요청 사이트
            **self.get_required_headers(),  # 자식 클래스에서 구현한 필수 헤더 추가
        }

    def _initialize_session(self) -> bool:
        """세션 초기화 기본 구현"""
        if self._session_initialized:
            return True

        self.logger.info("Initializing session")

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "max-age=0",
        }

        try:
            response = self.session.get(
                self.base_url,
                headers=headers,
                timeout=self.config.TIMEOUT,
            )

            self._session_initialized = True
            return response.status_code == 200

        except Exception as e:
            self.logger.error(
                "Failed to initialize session",
                error=str(e),
            )
            return False

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
            method: HTTP 메서드 (GET, POST, etc.)
            endpoint: API 엔드포인트
            params: 쿼리 파라미터
            data: 요청 바디 데이터
            headers: 추가 헤더
            use_cache: 캐시 사용 여부
            cache_ttl: 캐시 만료 시간

        Returns:
            APIResponse 객체
        """
        # 통계 기록 시작
        self.response_stats["total_requests"] += 1
        start_time = time.time()

        # 캐시 확인 - GET 요청만 캐싱 적용
        if use_cache and method.upper() == "GET":
            cached_response = self.cache.get(method, endpoint, params, data)
            if cached_response:
                # 캐시 히트 시 바로 반환
                self.response_stats["cache_hits"] += 1
                self.logger.debug("api_response_cache_hit", endpoint=endpoint)
                return cached_response
            self.response_stats["cache_misses"] += 1

        # Rate limiting 적용 - API 호출 간격 조절
        self.rate_limiter.wait()

        # 세션 초기화 확인
        if not self._session_initialized:
            if not self._initialize_session():
                return self._create_error_response(
                    "Failed to initialize session", "INIT_ERROR", None
                )

        # 서킷 브레이커 확인 - 연쇄 실패 방지
        if self.circuit_breaker.state == "OPEN":
            # 서킷 브레이커 리셋 시도
            if self.circuit_breaker._should_attempt_reset():
                self.circuit_breaker.state = "HALF_OPEN"
            else:
                # 서킷 브레이커가 열려있으면 요청 거부
                return self._create_error_response(
                    "Circuit breaker is OPEN - too many failures", "CIRCUIT_BREAKER_OPEN", 503
                )

        # 재시도 로직 적용
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

            def make_http_request():
                url = self._build_url(endpoint)
                request_headers = self._get_common_headers()
                if headers:
                    request_headers.update(headers)

                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    headers=request_headers,
                    timeout=self.timeout,
                )

                api_response = APIResponse.from_response(response)

                # 404 에러는 예외 처리로 변환
                if api_response.status_code == 404:
                    raise requests.exceptions.HTTPError("404 Not Found", response=response)

                return api_response

            api_response = retryable.execute(make_http_request)

            # 성공 시 캐시 저장
            if api_response.success and api_response.data and method.upper() == "GET":
                self.cache.set(method, endpoint, api_response, params, data, cache_ttl)

            # 통계 업데이트
            response_time = time.time() - start_time
            self._update_response_stats(api_response, response_time)

            # 서킷 브레이커 성공 처리
            self.circuit_breaker._on_success()

            return api_response

        except requests.exceptions.HTTPError as e:
            response = getattr(e, "response", None)
            status_code = response.status_code if response else None

            if status_code == 404:
                api_response = APIResponse(success=False, error="404 Not Found", status_code=404)
                self._update_response_stats(api_response, time.time() - start_time)
                return api_response

            self.circuit_breaker._on_failure()
            raise

        except Exception as e:
            self.circuit_breaker._on_failure()

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
            self._update_response_stats(error_response, time.time() - start_time)
            return error_response

    def _is_retryable_error(self, error: Exception) -> bool:
        """에러가 재시도 가능한지 확인"""
        error_msg = str(error).lower()
        retryable_patterns = [
            "timeout",
            "connection",
            "network",
            "temporary",
            "502",
            "503",
            "504",
        ]
        return any(pattern in error_msg for pattern in retryable_patterns)

    def _create_error_response(
        self, error_msg: str, error_type: str, status_code: Optional[int]
    ) -> APIResponse:
        """에러 응답 생성"""
        self.response_stats["error_count"] += 1
        if error_type not in self.response_stats["error_types"]:
            self.response_stats["error_types"][error_type] = 0
        self.response_stats["error_types"][error_type] += 1

        return APIResponse(
            success=False,
            error=error_msg,
            status_code=status_code,
        )

    def _update_response_stats(self, api_response: APIResponse, response_time: float):
        """응답 통계 업데이트"""
        if api_response.success:
            self.response_stats["success_count"] += 1

        self.response_stats["response_times"].append(response_time)
        if len(self.response_stats["response_times"]) > 100:
            self.response_stats["response_times"] = self.response_stats["response_times"][-100:]

        if self.response_stats["response_times"]:
            self.response_stats["average_response_time"] = sum(
                self.response_stats["response_times"]
            ) / len(self.response_stats["response_times"])

    def get_api_stats(self) -> Dict[str, Any]:
        """API 통계 정보 반환"""
        stats = self.response_stats.copy()
        stats.update(self.cache.get_stats())

        if stats["total_requests"] > 0:
            stats["success_rate"] = stats["success_count"] / stats["total_requests"]
            stats["cache_hit_rate"] = stats["cache_hits"] / stats["total_requests"]
        else:
            stats["success_rate"] = 0.0
            stats["cache_hit_rate"] = 0.0

        return stats

    def close(self) -> None:
        """세션 종료"""
        self.session.close()

    def __enter__(self):
        """Context manager 진입"""
        self._initialize_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료"""
        self.close()


@dataclass
class CacheEntry:
    """API 응답 캐시 항목"""

    data: Dict[str, Any]
    cached_at: float
    ttl: float = 3600.0

    def is_expired(self) -> bool:
        """캐시 만료 여부 확인"""
        return time.time() > (self.cached_at + self.ttl)


class APIResponseCache:
    """API 응답 캐시 관리자"""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.logger = get_logger().bind(component="APIResponseCache")

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

        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if not entry.is_expired():
                return APIResponse(
                    success=True,
                    data=entry.data,
                    status_code=200,
                )
            else:
                del self.memory_cache[cache_key]

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
            return

        cache_key = self._generate_cache_key(method, url, params, data)
        entry = CacheEntry(data=response.data, cached_at=time.time(), ttl=ttl or 3600.0)
        self.memory_cache[cache_key] = entry

    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 정보"""
        return {
            "memory_entries": len(self.memory_cache),
            "file_entries": 0,
            "cache_dir": str(self.cache_dir) if self.cache_dir else None,
        }

    def clear(self) -> None:
        """캐시 비우기"""
        self.memory_cache.clear()
