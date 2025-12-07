"""네이버 부동산 API 클라이언트"""

import json
import urllib.parse
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional
from enum import Enum

import requests
import structlog

from crawler.config import CrawlerConfig
from crawler.api.auth_manager import NaverAuthManager
from crawler.api.retry_manager import RetryManager, RetryConfig, RetryableError, NonRetryableError

logger = structlog.get_logger(__name__)


class APIEndpoint(Enum):
    """API 엔드포인트 열거형"""

    COMPLEX_LIST = "/cluster/ajax/complexList"
    COMPLEX_DETAIL = "/cluster/ajax/complexDetail"
    ARTICLE_LIST = "/cluster/ajax/articleList"
    TRANSACTION_HISTORY = "/cluster/ajax/statsMonth"


class NaverAPIClient:
    """네이버 부동산 API 호출을 담당하는 클라이언트 클래스"""

    def __init__(
        self, config: Optional[CrawlerConfig] = None, retry_config: Optional[RetryConfig] = None
    ):
        """초기화

        Args:
            config: 크롤러 설정
            retry_config: 재시도 설정
        """
        self.config = config or CrawlerConfig.from_env()
        self.base_url = "https://new.land.naver.com"
        self.timeout = self.config.timeout
        self._session: Optional[requests.Session] = None

        # 인증 관리자 초기화
        self.auth_manager = NaverAuthManager(self.config)

        # 재시도 관리자 초기화
        if retry_config is None:
            retry_config = RetryConfig(
                max_attempts=self.config.retry_attempts + 1,  # 최초 시도 포함
                base_delay=self.config.retry_delay,
                max_delay=10.0,
                circuit_breaker_threshold=5,
                circuit_breaker_timeout=60.0,
            )
        self.retry_manager = RetryManager(retry_config)

        # Fallback 엔드포인트 설정
        self._setup_fallback_endpoints()

        # 로거 바인딩
        self.logger = logger.bind(component="NaverAPIClient")

    def _get_api_headers(self) -> Dict[str, str]:
        """API 요청에 필요한 헤더 생성

        Returns:
            API 헤더 딕셔너리
        """
        # AuthManager를 통해 기본 헤더 가져오기
        headers = self.auth_manager.get_api_headers()

        # 네이버 API 특화 헤더 추가
        headers.update(
            {
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Referer": "https://m.land.naver.com/",
            }
        )

        return headers

    def _build_url(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        """엔드포인트와 파라미터로 전체 URL 빌드

        Args:
            endpoint: API 엔드포인트 (예: "/cluster/ajax/complexList")
            params: 요청 파라미터

        Returns:
            전체 URL
        """
        url = f"{self.base_url}{endpoint}"

        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"

        return url

    def _get_session(self) -> requests.Session:
        """HTTP 세션 가져오기 (캐시됨)

        Returns:
            requests Session 객체
        """
        if self._session is None:
            self._session = requests.Session()
            # 세션 설정
            self._session.headers.update(self._get_api_headers())

        return self._session

    def close(self):
        """세션 닫기 및 리소스 정리"""
        if self._session:
            self._session.close()
            self._session = None

    @contextmanager
    def managed_session(self):
        """컨텍스트 매니저로 세션 관리"""
        try:
            yield self._get_session()
        finally:
            self.close()

    def _setup_fallback_endpoints(self):
        """Fallback 엔드포인트 설정"""
        # 현재는 네이버 API에 대한 fallback이 없지만,
        # 향후 다른 데이터 소스로의 fallback을 위한 구조
        # 예: 공공데이터 API로 fallback
        pass

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """HTTP 요청 실행 (재시도 관리자용)

        Args:
            method: HTTP 메서드 (GET, POST 등)
            endpoint: API 엔드포인트
            **kwargs: requests에 전달할 추가 인자

        Returns:
            requests Response 객체

        Raises:
            RetryableError: 재시도 가능한 에러
            NonRetryableError: 재시도 불가능한 에러
        """
        session = self._get_session()

        # 자동 새로고침 체크
        self.auth_manager.auto_refresh_if_needed()

        # 세션 헤더 업데이트 (쿠키 등)
        session.headers.update(self._get_api_headers())

        # 요청 실행
        response = session.request(method, endpoint, timeout=self.timeout, **kwargs)

        # 응답 쿠키 업데이트
        if response.cookies:
            self.auth_manager.update_cookies(dict(response.cookies))

        # 상태 코드에 따른 에러 처리
        if response.status_code in self.retry_manager.config.retryable_status_codes:
            error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise RetryableError(error_msg, status_code=response.status_code)
        elif not response.ok:
            error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            raise NonRetryableError(error_msg, status_code=response.status_code)

        return response

    def fetch(self, endpoint: APIEndpoint, **kwargs) -> Dict[str, Any]:
        """GET 요청으로 데이터 조회

        Args:
            endpoint: API 엔드포인트
            **kwargs: 요청 파라미터

        Returns:
            응답 데이터 (JSON 파싱된 딕셔너리)

        Raises:
            Exception: API 호출 실패 시
        """

        def _fetch():
            url = self._build_url(endpoint.value, kwargs.get("params"))
            params = kwargs.get("params")

            # params를 kwargs에서 제외하고 나머지는 request에 전달
            request_kwargs = {k: v for k, v in kwargs.items() if k != "params"}

            response = self._make_request("GET", url, params=params, **request_kwargs)

            # JSON 파싱
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"response": response.text}

        return self.retry_manager.execute_with_retry(endpoint.value, _fetch)

    def post(
        self, endpoint: APIEndpoint, data: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        """POST 요청으로 데이터 전송

        Args:
            endpoint: API 엔드포인트
            data: 요청 데이터
            **kwargs: 추가 요청 파라미터

        Returns:
            응답 데이터 (JSON 파싱된 딕셔너리)

        Raises:
            Exception: API 호출 실패 시
        """

        def _post():
            url = self._build_url(endpoint.value)

            response = self._make_request("POST", url, json=data, **kwargs)

            # JSON 파싱
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"response": response.text}

        return self.retry_manager.execute_with_retry(endpoint.value, _post)

    def fetch_complex_list(self, cortar_no: str, bounds: str | None = None) -> Dict[str, Any]:
        """법정동별 단지 목록 조회

        Args:
            cortar_no: 법정동 코드
            bounds: 지도 경계 좌표 (옵션)

        Returns:
            단지 목록 정보
        """
        params = {
            "cortarNo": cortar_no,
            "hscpType": "APT",
            "page": 1,
            "count": 100,
        }

        if bounds:
            params["isp"] = bounds

        return self.fetch(APIEndpoint.COMPLEX_LIST, params=params)

    def fetch_complex_detail(self, complex_id: str) -> Dict[str, Any]:
        """단지 상세 정보 조회

        Args:
            complex_id: 단지 ID

        Returns:
            단지 상세 정보
        """
        params = {"complexNo": complex_id}
        return self.fetch(APIEndpoint.COMPLEX_DETAIL, params=params)

    def fetch_complex_listings(
        self, complex_id: str, trade_type: str, page: int = 1
    ) -> Dict[str, Any]:
        """단지별 매물 목록 조회

        Args:
            complex_id: 단지 ID
            trade_type: 거래 유형 (A1: 매매, B1: 전세, B2: 월세)
            page: 페이지 번호

        Returns:
            매물 목록 정보
        """
        params = {
            "complexNo": complex_id,
            "tradTpCd": trade_type,
            "page": page,
            "count": 20,
        }

        return self.fetch(APIEndpoint.ARTICLE_LIST, params=params)

    def fetch_transaction_history(
        self, cortar_no: str, trade_type: str, year: int
    ) -> Dict[str, Any]:
        """거래내역 조회

        Args:
            cortar_no: 법정동 코드
            trade_type: 거래 유형 (A1: 매매, B1: 전세, B2: 월세)
            year: 조회 년도

        Returns:
            거래내역 정보
        """
        params = {
            "cortarNo": cortar_no,
            "tradTpCd": trade_type,
            "yyyy": str(year),
        }

        return self.fetch(APIEndpoint.TRANSACTION_HISTORY, params=params)

    def __enter__(self):
        """컨텍스트 매니저 진입"""
        self._get_session()  # 세션 미리 생성
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        self.close()

    # 인증 관리 메서드들
    def is_authenticated(self) -> bool:
        """현재 인증 상태 확인"""
        return self.auth_manager.is_authenticated()

    def update_cookies(self, cookies: Dict[str, str]) -> None:
        """쿠키 업데이트"""
        self.auth_manager.update_cookies(cookies)

    def clear_cookies(self) -> None:
        """모든 쿠키 삭제"""
        self.auth_manager.clear_cookies()

    def refresh_session(self) -> bool:
        """세션 새로고침"""
        return self.auth_manager.refresh_session()

    def get_auth_info(self) -> Dict[str, Any]:
        """인증 정보 반환 (디버깅용)"""
        return self.auth_manager.get_auth_info()

    def set_api_token(self, token: str) -> None:
        """API 토큰 설정"""
        self.auth_manager.api_token = token

    def get_api_statistics(self) -> Dict[str, Any]:
        """API 호출 통계 정보 반환

        Returns:
            엔드포인트별 통계 정보
        """
        return self.retry_manager.get_statistics()

    def get_circuit_breaker_states(self) -> Dict[str, str]:
        """모든 엔드포인트의 서킷 브레이커 상태 반환

        Returns:
            엔드포인트별 서킷 브레이커 상태
        """
        states = {}
        for endpoint in APIEndpoint:
            state = self.retry_manager.get_circuit_state(endpoint.value)
            states[endpoint.value] = state.value
        return states

    def reset_circuit_breaker(self, endpoint: APIEndpoint):
        """특정 엔드포인트의 서킷 브레이커 초기화

        Args:
            endpoint: 초기화할 엔드포인트
        """
        self.retry_manager.reset_circuit_breaker(endpoint.value)
        self.logger.info("Circuit breaker reset", endpoint=endpoint.value)

    def reset_statistics(self):
        """모든 통계 정보 초기화"""
        self.retry_manager.reset_statistics()
        self.logger.info("API statistics reset")

    def register_fallback(
        self, primary_endpoint: APIEndpoint, fallback_name: str, fallback_func: Callable
    ):
        """Fallback 함수 등록

        Args:
            primary_endpoint: 기본 엔드포인트
            fallback_name: Fallback 식별 이름
            fallback_func: Fallback 함수
        """
        self.retry_manager.register_fallback_func(fallback_name, fallback_func)

        # fallback 설정에 추가
        if primary_endpoint.value not in self.retry_manager.config.fallback_endpoints:
            self.retry_manager.config.fallback_endpoints[primary_endpoint.value] = []
        if (
            fallback_name
            not in self.retry_manager.config.fallback_endpoints[primary_endpoint.value]
        ):
            self.retry_manager.config.fallback_endpoints[primary_endpoint.value].append(
                fallback_name
            )

        self.logger.info(
            "Fallback registered",
            primary_endpoint=primary_endpoint.value,
            fallback_name=fallback_name,
        )
