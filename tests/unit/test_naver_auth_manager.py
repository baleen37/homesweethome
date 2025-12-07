"""
네이버 인증 관리자 테스트
"""

import pytest
from unittest.mock import patch
from datetime import datetime, timedelta

from crawler.api.auth_manager import NaverAuthManager, AuthState
from crawler.config import CrawlerConfig


@pytest.fixture
def config():
    """테스트용 설정 객체"""
    return CrawlerConfig.from_env()


@pytest.fixture
def auth_manager(config):
    """테스트용 인증 관리자"""
    return NaverAuthManager(config)


class TestNaverAuthManager:
    """NaverAuthManager 테스트 클래스"""

    def test_init_default_values(self, auth_manager):
        """기본값으로 초기화 테스트"""
        assert auth_manager.auth_state == AuthState.UNAUTHENTICATED
        assert auth_manager.cookies == {}
        assert auth_manager.last_authenticated is None
        assert auth_manager.session_expires_at is None

    def test_is_authenticated_false_by_default(self, auth_manager):
        """기본 상태에서는 인증되지 않음"""
        assert not auth_manager.is_authenticated()

    def test_is_authenticated_true_with_valid_session(self, auth_manager):
        """유효한 세션이 있으면 인증됨"""
        # 유효한 세션 설정
        auth_manager.auth_state = AuthState.AUTHENTICATED
        auth_manager.last_authenticated = datetime.now()
        auth_manager.session_expires_at = datetime.now() + timedelta(hours=1)

        assert auth_manager.is_authenticated()

    def test_is_authenticated_false_with_expired_session(self, auth_manager):
        """세션 만료 시 인증되지 않음"""
        # 만료된 세션 설정
        auth_manager.auth_state = AuthState.AUTHENTICATED
        auth_manager.last_authenticated = datetime.now() - timedelta(hours=2)
        auth_manager.session_expires_at = datetime.now() - timedelta(hours=1)

        assert not auth_manager.is_authenticated()

    def test_update_cookies(self, auth_manager):
        """쿠키 업데이트 테스트"""
        new_cookies = {
            "session_id": "test_session",
            "auth_token": "test_token",
            "expires": "2024-12-31",
        }

        auth_manager.update_cookies(new_cookies)

        assert auth_manager.cookies == new_cookies
        assert auth_manager.auth_state == AuthState.AUTHENTICATED
        assert auth_manager.last_authenticated is not None

    def test_update_cookies_partial_update(self, auth_manager):
        """부분적인 쿠키 업데이트 테스트"""
        # 초기 쿠키 설정
        auth_manager.cookies = {"existing": "value"}

        # 새 쿠키 추가
        new_cookies = {
            "session_id": "test_session",
            "existing": "updated_value",  # 기존 값 덮어쓰기
        }

        auth_manager.update_cookies(new_cookies)

        expected = {"existing": "updated_value", "session_id": "test_session"}
        assert auth_manager.cookies == expected

    def test_clear_cookies(self, auth_manager):
        """쿠키 삭제 테스트"""
        # 쿠키 설정
        auth_manager.cookies = {"session_id": "test"}
        auth_manager.auth_state = AuthState.AUTHENTICATED

        auth_manager.clear_cookies()

        assert auth_manager.cookies == {}
        assert auth_manager.auth_state == AuthState.UNAUTHENTICATED
        assert auth_manager.last_authenticated is None

    def test_get_default_headers_unauthenticated(self, auth_manager):
        """인증되지 않은 상태에서 기본 헤더 가져오기"""
        headers = auth_manager.get_default_headers()

        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Accept-Language" in headers
        assert "Cookie" not in headers  # 인증되지 않으면 쿠키 없음

    def test_get_default_headers_authenticated(self, auth_manager):
        """인증된 상태에서 기본 헤더 가져오기"""
        # 쿠키 설정
        auth_manager.cookies = {"session_id": "test_session", "auth_token": "test_token"}
        auth_manager.auth_state = AuthState.AUTHENTICATED

        headers = auth_manager.get_default_headers()

        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Cookie" in headers
        assert "session_id=test_session" in headers["Cookie"]
        assert "auth_token=test_token" in headers["Cookie"]

    def test_get_api_headers_with_token(self, auth_manager):
        """API 토큰이 있는 경우 API 헤더 가져오기"""
        # API 토큰 설정
        auth_manager.api_token = "test_api_token"

        headers = auth_manager.get_api_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_api_token"
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"

    def test_get_api_headers_without_token(self, auth_manager):
        """API 토큰이 없는 경우 API 헤더 가져오기"""
        headers = auth_manager.get_api_headers()

        assert "Authorization" not in headers
        assert "Content-Type" in headers

    def test_set_session_expiry(self, auth_manager):
        """세션 만료 시간 설정"""
        expiry_time = datetime.now() + timedelta(hours=2)
        auth_manager.set_session_expiry(expiry_time)

        assert auth_manager.session_expires_at == expiry_time
        assert auth_manager.auth_state == AuthState.AUTHENTICATED

    def test_validate_cookies_empty(self, auth_manager):
        """빈 쿠키 검증"""
        assert not auth_manager.validate_cookies({})

    def test_validate_cookies_missing_required(self, auth_manager):
        """필수 쿠키가 없는 경우"""
        cookies = {"optional": "value"}
        assert not auth_manager.validate_cookies(cookies)

    def test_validate_cookies_valid(self, auth_manager):
        """유효한 쿠키"""
        cookies = {"session_id": "test_session", "auth_token": "test_token"}
        assert auth_manager.validate_cookies(cookies)

    def test_refresh_session_success(self, auth_manager):
        """세션 새로고침 성공"""
        with patch.object(auth_manager, "_perform_refresh") as mock_refresh:
            mock_refresh.return_value = {"session_id": "new_session", "auth_token": "new_token"}

            result = auth_manager.refresh_session()

            assert result is True
            assert auth_manager.auth_state == AuthState.AUTHENTICATED
            assert "new_session" in auth_manager.cookies.values()
            mock_refresh.assert_called_once()

    def test_refresh_session_failure(self, auth_manager):
        """세션 새로고침 실패"""
        with patch.object(auth_manager, "_perform_refresh") as mock_refresh:
            mock_refresh.return_value = None

            result = auth_manager.refresh_session()

            assert result is False
            assert auth_manager.auth_state == AuthState.UNAUTHENTICATED

    def test_auto_refresh_if_needed_expires_soon(self, auth_manager):
        """만료 임박 시 자동 새로고침"""
        # 현재 시간 설정
        now = datetime.now()

        # 5분 후 만료되는 세션 설정
        auth_manager.auth_state = AuthState.AUTHENTICATED
        auth_manager.session_expires_at = now + timedelta(minutes=5)

        with patch.object(auth_manager, "refresh_session") as mock_refresh:
            mock_refresh.return_value = True

            auth_manager.auto_refresh_if_needed(current_time=now)

            mock_refresh.assert_called_once()

    def test_auto_refresh_if_needed_not_needed(self, auth_manager):
        """새로고침 불필요"""
        # 현재 시간 설정
        now = datetime.now()

        # 1시간 후 만료되는 세션 설정
        auth_manager.auth_state = AuthState.AUTHENTICATED
        auth_manager.session_expires_at = now + timedelta(hours=1)

        with patch.object(auth_manager, "refresh_session") as mock_refresh:
            auth_manager.auto_refresh_if_needed(current_time=now)

            mock_refresh.assert_not_called()

    def test_get_auth_info_dict(self, auth_manager):
        """인증 정보 딕셔너리 반환"""
        auth_manager.auth_state = AuthState.AUTHENTICATED
        auth_manager.cookies = {"session_id": "test"}
        auth_manager.api_token = "api_token"
        auth_manager.last_authenticated = datetime.now()

        info = auth_manager.get_auth_info()

        assert "auth_state" in info
        assert "last_authenticated" in info
        assert "cookie_count" in info
        assert "has_api_token" in info
        assert info["auth_state"] == "AUTHENTICATED"
        assert info["cookie_count"] == 1
        assert info["has_api_token"] is True
