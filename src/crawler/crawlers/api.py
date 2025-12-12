"""API 기반 크롤러를 위한 추상 베이스 클래스.

이 모듈은 BaseCrawler를 확장하여 API 호출에 필요한 공통 기능을 제공하는
APICrawler 추상 클래스를 구현합니다. 세션 관리, 헤더 설정, 인증 처리,
JSON 응답 파싱, 페이지네이션, 에러 핸들링, Rate Limiting 등의 기능을 포함합니다.
"""

import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import requests

from crawler.crawlers.base import BaseCrawler
from crawler.config import CrawlerConfig
from crawler.utils.retry import AdaptiveRateLimiter
from crawler.utils.retry import retry_with_delay


class APIError(Exception):
    """API 호출 중 발생하는 에러를 위한 커스텀 예외."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        request_url: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data
        self.request_url = request_url


class APICrawler(BaseCrawler, ABC):
    """API 기반 크롤러를 위한 추상 베이스 클래스.

    BaseCrawler를 확장하여 API 호출에 필요한 공통 기능을 제공합니다.
    - 세션 관리
    - 동적 헤더 설정
    - 인증 처리
    - JSON 응답 파싱
    - 페이지네이션 처리
    - API 에러 코드별 처리
    - Rate Limiting
    - 재시도 로직
    """

    def __init__(
        self,
        config: CrawlerConfig,
        base_url: Optional[str] = None,
        default_headers: Optional[Dict[str, str]] = None,
        auth: Optional[Tuple[str, str]] = None,
        api_key: Optional[str] = None,
        rate_limit_delay: float = 1.0,
        timeout: float = 30.0,
    ) -> None:
        """APICrawler 초기화.

        Args:
            config: CrawlerConfig 설정
            base_url: API의 기본 URL
            default_headers: 기본 HTTP 헤더
            auth: (username, password) 형태의 기본 인증
            api_key: API 키
            rate_limit_delay: API 호출 간 기본 지연 시간 (초)
            timeout: 요청 타임아웃 시간 (초)
        """
        super().__init__(config)

        # API 관련 설정
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.default_headers = default_headers or {}
        self.auth = auth
        self.api_key = api_key
        self.timeout = timeout

        # 세션 관리
        self.session = requests.Session()
        self._setup_session()

        # Rate Limiting
        self.rate_limiter = AdaptiveRateLimiter()
        # 전달된 rate_limit_delay로 초기 지연시간 설정
        if rate_limit_delay != 1.0:  # 기본값이 아닌 경우에만 설정
            self.rate_limiter.current_delay = max(
                self.rate_limiter.min_delay, min(self.rate_limiter.max_delay, rate_limit_delay)
            )

    def _setup_session(self) -> None:
        """세션 초기 설정."""
        # 기본 헤더 설정
        self.session.headers.update(self.default_headers)

        # 인증 설정
        if self.auth:
            self.session.auth = self.auth

        # API 키 헤더 추가
        if self.api_key:
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {self.api_key}",
                    "X-API-Key": self.api_key,
                }
            )

    @abstractmethod
    def get_endpoint(self) -> str:
        """API 엔드포인트 경로 반환.

        Returns:
            엔드포인트 경로 (예: "/api/v1/search")
        """
        pass

    @abstractmethod
    def get_params(self) -> Dict[str, Any]:
        """API 요청 파라미터 반환.

        Returns:
            요청 파라미터 딕셔너리
        """
        pass

    @abstractmethod
    def parse_response(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """API 응답 데이터 파싱.

        Args:
            response_data: API 응답 JSON 데이터

        Returns:
            파싱된 데이터 리스트
        """
        pass

    def get_url(self) -> str:
        """전체 API URL 반환.

        Returns:
            base_url + endpoint 형태의 전체 URL
        """
        endpoint = self.get_endpoint()
        if endpoint.startswith("http"):
            return endpoint
        return f"{self.base_url}{endpoint}"

    def fetch(self, url: str) -> str:
        """API 호출을 통해 데이터 가져오기.

        Args:
            url: 요청할 URL

        Returns:
            응답 데이터 (JSON 문자열)
        """
        # Rate limiting 적용
        self.rate_limiter.wait()

        # 요청 준비
        method = self.get_request_method()
        params = self.get_params()
        headers = self.get_headers()
        data = self.get_request_body() if method.upper() == "POST" else None

        # 재시도 로직과 함께 API 호출
        try:

            def _make_request():
                return self._make_request(
                    url,
                    method=method,
                    params=params,
                    headers=headers,
                    data=data,
                )

            response = retry_with_delay(
                _make_request, max_attempts=3, delay=1.0, logger=self.logger
            )

            # 성공 시 Rate Limiter 업데이트
            self.rate_limiter.on_success()

            # 응답을 JSON 문자열로 변환
            if isinstance(response, dict):
                return json.dumps(response, ensure_ascii=False)
            return str(response)

        except Exception as e:
            # 에러 발생 시 Rate Limiter 업데이트
            self.rate_limiter.on_error()
            self.logger.error(
                "api_request_failed",
                url=url,
                method=method,
                error=str(e),
                params=params,
            )
            raise

    def parse(self, html: str) -> List[Dict[str, Any]]:
        """API 응답 파싱.

        Args:
            html: API 응답 데이터 (JSON 문자열)

        Returns:
            파싱된 데이터 리스트
        """
        try:
            response_data = json.loads(html)
            return self.parse_response(response_data)
        except json.JSONDecodeError as e:
            self.logger.error(
                "json_parse_error",
                error=str(e),
                response_preview=html[:200] if html else "",
            )
            raise APIError("Failed to parse JSON response", response_data={"raw": html})

    def get_request_method(self) -> str:
        """HTTP 요청 메서드 반환.

        Returns:
            'GET' 또는 'POST'
        """
        return "GET"

    def get_headers(self) -> Dict[str, str]:
        """요청 헤더 반환.

        Returns:
            HTTP 헤더 딕셔너리
        """
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "User-Agent": self.config.user_agent,
        }

        # 동적 헤더 추가
        dynamic_headers = self.get_dynamic_headers()
        headers.update(dynamic_headers)

        return headers

    def get_dynamic_headers(self) -> Dict[str, str]:
        """동적으로 생성되는 헤더 반환.

        하위 클래스에서 오버라이드하여 API 특화 헤더를 추가할 수 있습니다.

        Returns:
            동적 헤더 딕셔너리
        """
        return {}

    def get_request_body(self) -> Optional[Dict[str, Any]]:
        """POST 요청 시 바디 데이터 반환.

        Returns:
            요청 바디 딕셔너리 또는 None
        """
        return None

    def _make_request(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """실제 API 요청 수행.

        Args:
            url: 요청 URL
            method: HTTP 메서드
            params: 쿼리 파라미터
            headers: 요청 헤더
            data: POST 데이터

        Returns:
            API 응답 JSON 데이터

        Raises:
            APIError: API 호출 에러 발생 시
        """
        start_time = time.time()

        try:
            # 요청 전송
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                json=data,
                timeout=self.timeout,
            )

            # 응답 시간 측정
            response_time = time.time() - start_time

            # API 호출 로깅
            self.logger.info(
                "api_call",
                url=url,
                method=method,
                status_code=response.status_code,
                response_time=response_time,
                params=params,
            )

            # 상태 코드 검증
            self._validate_response(response)

            # JSON 응답 파싱
            try:
                return response.json()
            except json.JSONDecodeError as e:
                self.logger.error(
                    "invalid_json_response",
                    status_code=response.status_code,
                    response_text=response.text[:500],
                    error=str(e),
                )
                raise APIError(
                    "Invalid JSON response from API",
                    status_code=response.status_code,
                    response_data={"text": response.text},
                    request_url=url,
                )

        except requests.exceptions.Timeout as e:
            self.logger.error(
                "api_timeout",
                url=url,
                timeout=self.timeout,
                error=str(e),
            )
            raise APIError(
                f"API request timeout after {self.timeout} seconds",
                request_url=url,
            )

        except requests.exceptions.ConnectionError as e:
            self.logger.error(
                "api_connection_error",
                url=url,
                error=str(e),
            )
            raise APIError(
                "Failed to connect to API server",
                request_url=url,
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(
                "api_request_error",
                url=url,
                error=str(e),
            )
            raise APIError(
                f"API request failed: {str(e)}",
                request_url=url,
            )

    def _validate_response(self, response: requests.Response) -> None:
        """API 응답 검증.

        Args:
            response: requests Response 객체

        Raises:
            APIError: 응답이 에러 상태인 경우
        """
        # 상태 코드에 따른 에러 처리
        if response.status_code == 401:
            raise APIError(
                "Authentication failed",
                status_code=response.status_code,
                request_url=response.url,
            )
        elif response.status_code == 403:
            raise APIError(
                "Access forbidden",
                status_code=response.status_code,
                request_url=response.url,
            )
        elif response.status_code == 404:
            raise APIError(
                "Resource not found",
                status_code=response.status_code,
                request_url=response.url,
            )
        elif response.status_code == 429:
            raise APIError(
                "Rate limit exceeded",
                status_code=response.status_code,
                request_url=response.url,
            )
        elif response.status_code >= 500:
            raise APIError(
                "Server error",
                status_code=response.status_code,
                request_url=response.url,
            )
        elif response.status_code >= 400:
            # 클라이언트 에러
            try:
                error_data = response.json()
                error_message = error_data.get("message", "Client error")
            except json.JSONDecodeError:
                error_message = f"HTTP {response.status_code}"

            raise APIError(
                error_message,
                status_code=response.status_code,
                response_data=error_data if "error_data" in locals() else None,
                request_url=response.url,
            )

    def handle_pagination(
        self,
        initial_response: Dict[str, Any],
        fetch_next_page: callable,
    ) -> List[Dict[str, Any]]:
        """페이지네이션 처리.

        Args:
            initial_response: 첫 페이지 응답
            fetch_next_page: 다음 페이지를 가져오는 콜백 함수

        Returns:
            모든 페이지의 데이터를 합친 리스트
        """
        all_items = []
        page = 1

        # 첫 페이지 데이터 파싱
        items, has_more = self.parse_page(initial_response, page)
        all_items.extend(items)

        # 다음 페이지가 있으면 계속 가져오기
        while has_more:
            page += 1

            # Rate limiting
            self.rate_limiter.wait()

            try:
                next_response = fetch_next_page(page)
                items, has_more = self.parse_page(next_response, page)
                all_items.extend(items)

                self.logger.info(
                    "pagination_fetched",
                    page=page,
                    items_count=len(items),
                    total_count=len(all_items),
                )

            except Exception as e:
                self.logger.error(
                    "pagination_error",
                    page=page,
                    error=str(e),
                )
                # 페이지네이션 에러 시 중단 (이전까지 가져온 데이터 반환)
                break

        self.logger.info(
            "pagination_completed",
            total_pages=page,
            total_items=len(all_items),
        )

        return all_items

    def parse_page(
        self,
        response: Dict[str, Any],
        page: int,
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """단일 페이지 데이터 파싱.

        Args:
            response: API 응답 데이터
            page: 페이지 번호

        Returns:
            (데이터 리스트, 다음 페이지 존재 여부) 튜플
        """
        # 하위 클래스에서 오버라이드하여 구현
        items = self.parse_response(response)
        has_more = False

        # 일반적인 페이지네이션 필드 확인
        if "pagination" in response:
            pagination = response["pagination"]
            has_more = pagination.get("hasNext", False)
        elif "has_more" in response:
            has_more = response["has_more"]
        elif "hasNext" in response:
            has_more = response["hasNext"]
        elif "next" in response:
            has_more = response["next"] is not None
        elif len(items) == self.get_page_size():
            # 현재 페이지가 가득 찼으면 다음 페이지가 있을 가능성이 높음
            has_more = True

        return items, has_more

    def get_page_size(self) -> int:
        """페이지 크기 반환.

        Returns:
            페이지당 아이템 수
        """
        return 20

    def __enter__(self):
        """컨텍스트 매니저 진입."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료."""
        self.cleanup()

    def cleanup(self) -> None:
        """리소스 정리."""
        if self.session:
            self.session.close()
            self.session = None
