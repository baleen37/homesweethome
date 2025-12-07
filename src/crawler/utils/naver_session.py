"""네이버 부동산 크롤러 세션 관리 유틸리티"""

import time
from enum import Enum
from typing import Any, Dict, List

import structlog


class SessionState(Enum):
    """세션 상태 Enum"""

    UNINITIALIZED = 0
    VALID = 1
    INVALID = 2
    EXPIRED = 3


class NaverSessionManager:
    """네이버 세션 관리자

    싱글톤 패턴을 사용하여 전역적으로 세션 상태를 관리합니다.
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.state = SessionState.UNINITIALIZED
            self.last_check_time = 0.0
            self.retry_count = 0
            self.max_retries = 3
            self.session_check_interval = 300  # 5분
            self.logger = structlog.get_logger("naver_session_manager")
            self._initialized = True

    def ensure_session(self, page: Any) -> None:
        """세션 확보 및 유효성 확인

        Args:
            page: Playwright 페이지 객체
        """
        current_time = time.time()

        # 기존 세션 확인
        try:
            existing_cookies = page.context.cookies()
            if existing_cookies and self.validate_session(existing_cookies):
                self.state = SessionState.VALID
                self.last_check_time = current_time
                self.logger.info("existing_session_valid", cookie_count=len(existing_cookies))
                return
        except Exception as e:
            self.logger.warning("failed_to_check_existing_session", error=str(e))

        # 새 세션 확보
        if not self._acquire_new_session(page):
            self.logger.error("failed_to_acquire_session")
            raise Exception("Failed to acquire Naver session")

    def validate_session(self, cookies: List[Dict[str, Any]]) -> bool:
        """세션 유효성 검증

        Args:
            cookies: 쿠키 리스트

        Returns:
            세션이 유효하면 True, 아니면 False
        """
        if not cookies:
            return False

        # 필수 쿠키 확인
        required_cookies = self.get_required_cookies(cookies)

        # NaverSession 쿠키가 있는지 확인
        has_naver_session = any(c.get("name") == "NaverSession" for c in required_cookies)

        # 만료되지 않은 쿠키가 있는지 확인
        valid_cookies = [c for c in required_cookies if not self.check_cookie_expiration(c)]

        return has_naver_session and len(valid_cookies) > 0

    def get_required_cookies(self, all_cookies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """필요한 쿠키만 필터링하여 반환

        Args:
            all_cookies: 전체 쿠키 리스트

        Returns:
            필터링된 쿠키 리스트
        """
        # 네이버 관련 쿠키만 필터링
        naver_domains = [".naver.com", "naver.com", "m.land.naver.com", "fin.land.naver.com"]

        required_cookies = []
        for cookie in all_cookies:
            domain = cookie.get("domain", "")
            if any(nav_domain in domain for nav_domain in naver_domains):
                required_cookies.append(cookie)

        return required_cookies

    def extract_storage_data(self, page: Any) -> Dict[str, Any]:
        """localStorage 및 sessionStorage 데이터 추출

        Args:
            page: Playwright page 객체

        Returns:
            스토리지 데이터
        """
        try:
            # JavaScript를 사용하여 스토리지 데이터 추출
            storage_data = page.evaluate("""
            () => {
                const data = {};

                // localStorage 데이터 추출
                try {
                    const localStorageData = {};
                    for (let i = 0; i < localStorage.length; i++) {
                        const key = localStorage.key(i);
                        if (key) {
                            localStorageData[key] = localStorage.getItem(key);
                        }
                    }
                    data.localStorage = localStorageData;
                } catch (e) {
                    data.localStorage = {};
                }

                // sessionStorage 데이터 추출
                try {
                    const sessionStorageData = {};
                    for (let i = 0; i < sessionStorage.length; i++) {
                        const key = sessionStorage.key(i);
                        if (key) {
                            sessionStorageData[key] = sessionStorage.getItem(key);
                        }
                    }
                    data.sessionStorage = sessionStorageData;
                } catch (e) {
                    data.sessionStorage = {};
                }

                return data;
            }
            """)

            return storage_data

        except Exception as e:
            self.logger.error("failed_to_extract_storage_data", error=str(e))
            return {"localStorage": {}, "sessionStorage": {}}

    def check_cookie_expiration(self, cookie: Dict[str, Any]) -> bool:
        """쿠키 만료 확인

        Args:
            cookie: 쿠키 객체

        Returns:
            만료되었으면 True, 아니면 False
        """
        # 만료 시간이 없으면 세션 쿠키로 간주 (만료 안 됨)
        if "expires" not in cookie:
            return False

        # 만료 시간 확인
        current_time = time.time()
        return cookie["expires"] < current_time

    def refresh_session(self, page: Any) -> None:
        """세션 새로고침

        Args:
            page: Playwright 페이지 객체
        """
        self.logger.info("refreshing_session")

        # 기존 쿠키 클리어
        try:
            page.context.clear_cookies()
            self.logger.info("existing_cookies_cleared")
        except Exception as e:
            self.logger.warning("failed_to_clear_cookies", error=str(e))

        # 상태 초기화
        self.state = SessionState.UNINITIALIZED
        self.retry_count = 0

        # 새 세션 확보
        self.ensure_session(page)

    def is_session_valid(self) -> bool:
        """세션 유효성 확인 (시간 기반)

        Returns:
            세션이 유효하면 True, 아니면 False
        """
        current_time = time.time()

        # 상태가 유효하고, 마지막 확인 시간이 기준 내인 경우
        if (
            self.state == SessionState.VALID
            and current_time - self.last_check_time < self.session_check_interval
        ):
            return True

        return False

    def _acquire_new_session(self, page: Any) -> bool:
        """새로운 세션 확보

        Args:
            page: Playwright 페이지 객체

        Returns:
            세션 확보 성공 여부
        """
        self.logger.info("acquiring_new_session", retry_count=self.retry_count)

        try:
            # 네이버 부동산 모바일 메인 페이지 접속
            self.logger.info("accessing_naver_mobile_main")
            response = page.goto(
                "https://m.land.naver.com/", wait_until="domcontentloaded", timeout=30000
            )

            if not response or response.status >= 400:
                self.logger.error(
                    "failed_to_access_naver_mobile",
                    status=response.status if response else "no_response",
                )
                return self._handle_acquisition_failure(page)

            # 페이지 로딩 대기
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                # networkidle 시간 초과는 무시하고 진행
                pass

            # 쿠키 확인
            cookies = page.context.cookies()
            if not cookies:
                self.logger.warning("no_cookies_found")
                return self._handle_acquisition_failure(page)

            # 필수 쿠키 필터링
            required_cookies = self.get_required_cookies(cookies)
            self.logger.info(
                "cookies_acquired", total_count=len(cookies), required_count=len(required_cookies)
            )

            # 세션 유효성 검증
            if self.validate_session(required_cookies):
                self.state = SessionState.VALID
                self.last_check_time = time.time()
                self.retry_count = 0

                # localStorage/sessionStorage 데이터 추출
                storage_data = self.extract_storage_data(page)
                if storage_data:
                    self.logger.info(
                        "storage_data_extracted",
                        localStorage_count=len(storage_data.get("localStorage", {})),
                        sessionStorage_count=len(storage_data.get("sessionStorage", {})),
                    )

                return True
            else:
                self.logger.warning("session_validation_failed")
                return self._handle_acquisition_failure(page)

        except Exception as e:
            self.logger.error("session_acquisition_error", error=str(e))
            return self._handle_acquisition_failure(page)

    def _handle_acquisition_failure(self, page: Any) -> bool:
        """세션 확보 실패 처리

        Args:
            page: Playwright 페이지 객체

        Returns:
            재시도 여부
        """
        self.retry_count += 1

        if self.retry_count < self.max_retries:
            # 재시도 전 잠시 대기
            wait_time = min(self.retry_count * 2, 5)
            self.logger.info(
                "retrying_session_acquisition", retry_count=self.retry_count, wait_time=wait_time
            )
            time.sleep(wait_time)
            return self._acquire_new_session(page)
        else:
            self.logger.error("max_retries_exceeded", max_retries=self.max_retries)
            self.state = SessionState.INVALID
            return False


# 전역 인스턴스 (싱글톤)
_session_manager = None


def get_session_manager() -> NaverSessionManager:
    """세션 관리자 인스턴스 가져오기

    Returns:
        NaverSessionManager 싱글톤 인스턴스
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = NaverSessionManager()
    return _session_manager
