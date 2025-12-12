"""Base API client to eliminate common functionality duplication."""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, Dict

import requests
from requests import Response, Session
from structlog import get_logger

from crawler.config import Config, USER_AGENT
from ..utils.retry import retry_with_delay
from ..utils.simple_error_handler import SimpleErrorHandler


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
        except Exception as e:
            return cls(
                success=False,
                error=f"Unexpected error: {str(e)}",
                status_code=status_code,
            )


class BaseAPIClient(ABC):
    """Base API client to eliminate common functionality duplication."""

    def __init__(self, config: Config, base_url: str):
        """초기화

        Args:
            config: 크롤러 설정 객체
            base_url: API 기본 URL
        """
        self.config = config
        self.base_url = base_url
        self.session = Session()
        self._session_initialized = False
        self.logger = get_logger()

        # 네트워크 설정
        self.timeout = config.TIMEOUT
        self.max_retries = config.RETRY_ATTEMPTS

        # 단순화된 에러 핸들러 초기화
        self.error_handler = SimpleErrorHandler(max_retries=self.max_retries, retry_delay=1.0)

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
    ) -> APIResponse:
        """HTTP 요청 실행 (재시도 포함)

        Args:
            method: HTTP 메서드 (GET, POST, etc.)
            endpoint: API 엔드포인트
            params: 쿼리 파라미터
            data: 요청 바디 데이터
            headers: 추가 헤더

        Returns:
            APIResponse 객체
        """
        # 기본 딜레이 적용
        time.sleep(1.0)

        # 세션 초기화 확인
        if not self._session_initialized:
            if not self._initialize_session():
                return APIResponse(
                    success=False,
                    error="Failed to initialize session",
                    status_code=None,
                )

        # 단순화된 재시도 로직 적용
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

            api_response = retry_with_delay(
                make_http_request, max_attempts=self.max_retries + 1, delay=1.0, logger=self.logger
            )

            return api_response

        except requests.exceptions.HTTPError as e:
            response = getattr(e, "response", None)
            status_code = response.status_code if response else None

            if status_code == 404:
                return APIResponse(success=False, error="404 Not Found", status_code=404)

            raise

        except Exception as e:
            error_msg = str(e)

            if isinstance(e, requests.exceptions.Timeout):
                pass
            elif isinstance(e, requests.exceptions.ConnectionError):
                pass

            return APIResponse(
                success=False,
                error=error_msg,
                status_code=None,
            )

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
