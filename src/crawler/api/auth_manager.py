"""
네이버 API 인증 관리자

API 인증, 쿠키 관리, 헤더 생성 등 인증 관련 기능을 중앙에서 관리합니다.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional, Any

import structlog

from crawler.config import CrawlerConfig


logger = structlog.get_logger()


class AuthState(Enum):
    """인증 상태 열거형"""

    UNAUTHENTICATED = "UNAUTHENTICATED"
    AUTHENTICATED = "AUTHENTICATED"
    EXPIRED = "EXPIRED"
    ERROR = "ERROR"


class NaverAuthManager:
    """
    네이버 API 인증 관리자

    쿠키, 세션, API 토큰 등 인증 관련 정보를 관리하고,
    필요한 HTTP 헤더를 동적으로 생성합니다.
    """

    # 필수 쿠키 목록
    REQUIRED_COOKIES = ["NNB"]

    # 자동 새로고침 임계 시간 (분)
    AUTO_REFRESH_THRESHOLD_MINUTES = 10

    # 세션 기본 만료 시간 (시간)
    DEFAULT_SESSION_EXPIRY_HOURS = 2

    def __init__(self, config: CrawlerConfig):
        """초기화"""
        self.config = config
        self.logger = structlog.get_logger("auth_manager")

        # 인증 상태
        self.auth_state: AuthState = AuthState.UNAUTHENTICATED

        # 쿠키 저장소
        self.cookies: Dict[str, str] = {}

        # API 토큰 (API 호출 시 필요)
        self.api_token: Optional[str] = None

        # 세션 정보
        self.last_authenticated: Optional[datetime] = None
        self.session_expires_at: Optional[datetime] = None

        # 인증 실패 횟수
        self.auth_failure_count: int = 0
        self.max_auth_failures: int = 3

    def is_authenticated(self) -> bool:
        """
        현재 인증 상태 확인

        Returns:
            bool: 인증되어 있으면 True
        """
        # 상태 체크
        if self.auth_state != AuthState.AUTHENTICATED:
            return False

        # 세션 만료 체크
        if self.session_expires_at and datetime.now() >= self.session_expires_at:
            self.logger.warning("Session expired", expires_at=self.session_expires_at)
            self.auth_state = AuthState.EXPIRED
            return False

        # 쿠키가 비어있으면 False
        if not self.cookies:
            return False

        # 쿠키 유효성 체크
        if not self.validate_cookies(self.cookies):
            self.logger.warning("Invalid cookies", cookies=list(self.cookies.keys()))
            self.auth_state = AuthState.ERROR
            return False

        return True

    def update_cookies(self, new_cookies: Dict[str, str]) -> None:
        """
        쿠키 업데이트

        Args:
            new_cookies: 새로운 쿠키 딕셔너리
        """
        if not new_cookies:
            self.logger.warning("Empty cookies provided")
            return

        # NNB 쿠키 보호 로직
        preserved_nnb = self.cookies.get("NNB")

        # 기존 쿠키에 새 쿠키 병합
        self.cookies.update(new_cookies)

        # NNB 쿠키가 새로운 쿠키에 없고 기존에 있었다면 복원
        if "NNB" not in new_cookies and preserved_nnb:
            self.cookies["NNB"] = preserved_nnb
            self.logger.debug("NNB cookie preserved from being overwritten")

        # 인증 상태 업데이트
        if self.validate_cookies(self.cookies):
            self.auth_state = AuthState.AUTHENTICATED
            self.last_authenticated = datetime.now()

            # 세션 만료 시간 설정 (없으면 기본값)
            if not self.session_expires_at:
                self.set_session_expiry(
                    datetime.now() + timedelta(hours=self.DEFAULT_SESSION_EXPIRY_HOURS)
                )

            self.logger.info(
                "Cookies updated", cookie_count=len(self.cookies), cookies=list(new_cookies.keys())
            )
        else:
            self.logger.warning("Invalid cookies after update", cookies=list(new_cookies.keys()))

    def clear_cookies(self) -> None:
        """모든 쿠키 삭제"""
        self.cookies.clear()
        self.auth_state = AuthState.UNAUTHENTICATED
        self.last_authenticated = None
        self.session_expires_at = None
        self.api_token = None

        self.logger.info("All authentication data cleared")

    def get_default_headers(self) -> Dict[str, str]:
        """
        기본 HTTP 헤더 생성

        Returns:
            Dict[str, str]: HTTP 헤더 딕셔너리
        """
        headers = {
            "User-Agent": self._get_user_agent(),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

        # 인증된 경우 쿠키 추가
        if self.is_authenticated() and self.cookies:
            cookie_string = "; ".join([f"{k}={v}" for k, v in self.cookies.items()])
            headers["Cookie"] = cookie_string

        return headers

    def get_api_headers(self) -> Dict[str, str]:
        """
        API 호출용 헤더 생성

        Returns:
            Dict[str, str]: API 헤더 딕셔너리
        """
        headers = self.get_default_headers()

        # API 관련 헤더 추가
        headers.update(
            {
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            }
        )

        # API 토큰이 있으면 Authorization 헤더 추가
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        return headers

    def set_session_expiry(self, expiry_time: datetime) -> None:
        """
        세션 만료 시간 설정

        Args:
            expiry_time: 만료 시간
        """
        self.session_expires_at = expiry_time
        # 세션 만료 시간이 설정되면 인증 상태로 변경
        self.auth_state = AuthState.AUTHENTICATED
        self.logger.info(
            "Session expiry set",
            expires_at=expiry_time.isoformat(),
            ttl_seconds=(expiry_time - datetime.now()).total_seconds(),
        )

    def validate_cookies(self, cookies: Dict[str, str]) -> bool:
        """
        쿠키 유효성 검사

        Args:
            cookies: 검사할 쿠키 딕셔너리

        Returns:
            bool: 유효하면 True
        """
        if not cookies:
            return False

        # 필수 쿠키 확인
        for required in self.REQUIRED_COOKIES:
            if required not in cookies or not cookies[required]:
                self.logger.debug("Missing required cookie", cookie=required)
                return False

        return True

    def refresh_session(self) -> bool:
        """
        세션 새로고침

        Returns:
            bool: 성공하면 True
        """
        self.logger.info("Attempting to refresh session")

        try:
            # 새로고침 로직 수행
            new_auth_data = self._perform_refresh()

            if new_auth_data:
                # 쿠키 업데이트 - 두 가지 형식 지원
                if "cookies" in new_auth_data:
                    self.update_cookies(new_auth_data["cookies"])
                elif isinstance(new_auth_data, dict) and any(
                    k in new_auth_data for k in self.REQUIRED_COOKIES
                ):
                    # 직접 쿠키 딕셔너리 형식 (테스트 호환성)
                    self.update_cookies(new_auth_data)

                # API 토큰 업데이트
                if "api_token" in new_auth_data:
                    self.api_token = new_auth_data["api_token"]

                # 실패 횟수 리셋
                self.auth_failure_count = 0

                self.logger.info("Session refreshed successfully")
                return True
            else:
                self.auth_failure_count += 1
                self.logger.warning("Session refresh failed", failure_count=self.auth_failure_count)

                # 실패 횟수가 너무 많으면 상태 변경
                if self.auth_failure_count >= self.max_auth_failures:
                    self.auth_state = AuthState.ERROR

                return False

        except Exception as e:
            self.logger.error(
                "Error during session refresh", error=str(e), error_type=type(e).__name__
            )
            self.auth_state = AuthState.ERROR
            return False

    def _perform_refresh(self) -> Optional[Dict[str, Any]]:
        """
        실제 세션 새로고침 수행 (내부 메서드)

        Returns:
            Optional[Dict[str, Any]]: 새로운 인증 데이터
        """
        # TODO: 실제 새로고침 로직 구현
        # 현재는 더미 데이터 반환
        return {
            "cookies": {
                "session_id": f"refreshed_{datetime.now().timestamp()}",
                "auth_token": f"token_{datetime.now().timestamp()}",
            }
        }

    def auto_refresh_if_needed(self, current_time: Optional[datetime] = None) -> bool:
        """
        필요 시 자동 세션 새로고침

        Args:
            current_time: 현재 시간 (테스트용)

        Returns:
            bool: 새로고침 수행 여부
        """
        if not self.is_authenticated():
            return False

        # 만료 임박 체크
        if self.session_expires_at:
            now = current_time or datetime.now()
            time_until_expiry = self.session_expires_at - now
            threshold = timedelta(minutes=self.AUTO_REFRESH_THRESHOLD_MINUTES)

            if time_until_expiry <= threshold:
                self.logger.info(
                    "Session expiring soon, auto-refreshing",
                    time_until_expiry_seconds=time_until_expiry.total_seconds(),
                )
                return self.refresh_session()

        return False

    def _get_user_agent(self) -> str:
        """
        User-Agent 문자열 생성

        Returns:
            str: User-Agent 문자열
        """
        # 모바일 User-Agent 사용 (네이버 모바일 API 호환성)
        return (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/16.0 Mobile/15E148 Safari/604.1 "
            "NAVER(inapp; search; 880; 11.4.3)"
        )

    def get_auth_info(self) -> Dict[str, Any]:
        """
        현재 인증 정보 반환 (디버깅용)

        Returns:
            Dict[str, Any]: 인증 정보
        """
        return {
            "auth_state": self.auth_state.value,
            "last_authenticated": (
                self.last_authenticated.isoformat() if self.last_authenticated else None
            ),
            "session_expires_at": (
                self.session_expires_at.isoformat() if self.session_expires_at else None
            ),
            "cookie_count": len(self.cookies),
            "cookie_names": list(self.cookies.keys()),
            "has_api_token": self.api_token is not None,
            "auth_failure_count": self.auth_failure_count,
        }

    def export_auth_data(self) -> Dict[str, Any]:
        """
        인증 데이터 내보내기 (백업용)

        Returns:
            Dict[str, Any]: 직렬화 가능한 인증 데이터
        """
        return {
            "cookies": self.cookies,
            "api_token": self.api_token,
            "last_authenticated": (
                self.last_authenticated.isoformat() if self.last_authenticated else None
            ),
            "session_expires_at": (
                self.session_expires_at.isoformat() if self.session_expires_at else None
            ),
            "auth_state": self.auth_state.value,
        }

    def import_auth_data(self, auth_data: Dict[str, Any]) -> bool:
        """
        인증 데이터 가져오기 (복원용)

        Args:
            auth_data: 인증 데이터

        Returns:
            bool: 성공하면 True
        """
        try:
            if "cookies" in auth_data:
                self.cookies = auth_data["cookies"]

            if "api_token" in auth_data:
                self.api_token = auth_data["api_token"]

            if "last_authenticated" in auth_data and auth_data["last_authenticated"]:
                self.last_authenticated = datetime.fromisoformat(auth_data["last_authenticated"])

            if "session_expires_at" in auth_data and auth_data["session_expires_at"]:
                self.session_expires_at = datetime.fromisoformat(auth_data["session_expires_at"])

            if "auth_state" in auth_data:
                self.auth_state = AuthState(auth_data["auth_state"])

            self.logger.info("Auth data imported successfully")
            return True

        except Exception as e:
            self.logger.error(
                "Failed to import auth data", error=str(e), error_type=type(e).__name__
            )
            return False
