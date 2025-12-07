import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from crawler.api.auth_manager import NaverAuthManager, AuthState
from crawler.config import CrawlerConfig


@pytest.fixture
def config():
    """테스트용 설정"""
    return CrawlerConfig(
        base_url="https://test.land.naver.com",
        timeout=30,
        max_retries=3,
        retry_delay=1.0,
    )


@pytest.fixture
def auth_manager(config):
    """테스트용 AuthManager"""
    return NaverAuthManager(config)


class TestNaverAuthManager:
    """NaverAuthManager 테스트 클래스"""

    def test_init(self, auth_manager):
        """초기화 테스트"""
        assert auth_manager.auth_state == AuthState.UNAUTHENTICATED
        assert auth_manager.cookies == {}
        assert auth_manager.last_authenticated is None
        assert auth_manager.session_expires_at is None

    def test_is_authenticated_false_by_default(self, auth_manager):
        """기본 상태에서는 인증되지 않음"""
        assert not auth_manager.is_authenticated()

    def test_is_authenticated_true_with_valid_session(self, auth_manager):
        """유효한 세션과 NNB 쿠키가 있으면 인증됨"""
        # 유효한 세션 설정
        auth_manager.auth_state = AuthState.AUTHENTICATED
        auth_manager.last_authenticated = datetime.now()
        auth_manager.session_expires_at = datetime.now() + timedelta(hours=1)
        # NNB 쿠키 추가
        auth_manager.cookies = {"NNB": "test_nnb_value"}

        assert auth_manager.is_authenticated()

    def test_is_authenticated_false_with_expired_session(self, auth_manager):
        """세션 만료 시 인증되지 않음"""
        # 만료된 세션 설정
        auth_manager.auth_state = AuthState.AUTHENTICATED
        auth_manager.last_authenticated = datetime.now() - timedelta(hours=2)
        auth_manager.session_expires_at = datetime.now() - timedelta(hours=1)

        assert not auth_manager.is_authenticated()

    def test_is_authenticated_false_without_nnb_cookie(self, auth_manager):
        """NNB 쿠키가 없으면 인증되지 않음"""
        # 유효한 세션 설정
        auth_manager.auth_state = AuthState.AUTHENTICATED
        auth_manager.last_authenticated = datetime.now()
        auth_manager.session_expires_at = datetime.now() + timedelta(hours=1)
        # NNB 없는 다른 쿠키만 설정
        auth_manager.cookies = {"session_id": "test_session", "auth_token": "test_token"}

        assert not auth_manager.is_authenticated()

    def test_is_authenticated_false_with_empty_nnb_cookie(self, auth_manager):
        """NNB 쿠키가 비어있으면 인증되지 않음"""
        # 유효한 세션 설정
        auth_manager.auth_state = AuthState.AUTHENTICATED
        auth_manager.last_authenticated = datetime.now()
        auth_manager.session_expires_at = datetime.now() + timedelta(hours=1)
        # 빈 NNB 쿠키
        auth_manager.cookies = {"NNB": ""}

        assert not auth_manager.is_authenticated()

    def test_update_cookies(self, auth_manager):
        """쿠키 업데이트 테스트"""
        new_cookies = {
            "NNB": "test_nnb",
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

    def test_update_cookies_without_nnb(self, auth_manager):
        """NNB 쿠키 없이 업데이트하면 인증되지 않음"""
        new_cookies = {
            "session_id": "test_session",
            "auth_token": "test_token",
            "expires": "2024-12-31",
        }

        auth_manager.update_cookies(new_cookies)

        assert auth_manager.cookies == new_cookies
        assert auth_manager.auth_state == AuthState.UNAUTHENTICATED
        assert auth_manager.last_authenticated is None

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
        """인증되지 않은 상태에서의 기본 헤더"""
        headers = auth_manager.get_default_headers()

        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Cookie" not in headers

    def test_get_default_headers_authenticated(self, auth_manager):
        """인증된 상태에서의 기본 헤더"""
        # 인증 설정
        auth_manager.auth_state = AuthState.AUTHENTICATED
        auth_manager.cookies = {"session_id": "test", "NNB": "test_nnb"}

        headers = auth_manager.get_default_headers()

        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Cookie" in headers
        assert "session_id=test" in headers["Cookie"]
        assert "NNB=test_nnb" in headers["Cookie"]

    def test_get_api_headers(self, auth_manager):
        """API 헤더 생성 테스트"""
        headers = auth_manager.get_api_headers()

        assert "User-Agent" in headers
        assert "Content-Type" in headers
        assert "X-Requested-With" in headers

    def test_set_session_expiry(self, auth_manager):
        """세션 만료 시간 설정"""
        expiry_time = datetime.now() + timedelta(hours=2)

        auth_manager.set_session_expiry(expiry_time)

        assert auth_manager.session_expires_at == expiry_time
        assert auth_manager.auth_state == AuthState.AUTHENTICATED

    def test_validate_cookies_valid(self, auth_manager):
        """유효한 쿠키 검증"""
        valid_cookies = {"NNB": "test_value", "session_id": "test"}

        assert auth_manager.validate_cookies(valid_cookies) is True

    def test_validate_cookies_missing_nnb(self, auth_manager):
        """NNB 쿠키가 없는 경우"""
        invalid_cookies = {"session_id": "test", "auth_token": "token"}

        assert auth_manager.validate_cookies(invalid_cookies) is False

    def test_validate_cookies_empty_nnb(self, auth_manager):
        """NNB 쿠키가 비어있는 경우"""
        invalid_cookies = {"NNB": "", "session_id": "test"}

        assert auth_manager.validate_cookies(invalid_cookies) is False

    def test_validate_cookies_empty(self, auth_manager):
        """빈 쿠키 검증"""
        assert auth_manager.validate_cookies({}) is False
        assert auth_manager.validate_cookies(None) is False

    @patch("crawler.api.auth_manager.datetime")
    def test_auto_refresh_if_needed_not_expired(self, mock_datetime, auth_manager):
        """만료되지 않은 세션은 새로고침하지 않음"""
        # 현재 시간 설정
        now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = now

        # 세션 만료 시간 설정 (나중에 만료)
        auth_manager.auth_state = AuthState.AUTHENTICATED
        auth_manager.session_expires_at = now + timedelta(minutes=30)
        auth_manager.cookies = {"NNB": "test"}  # NNB 쿠키 추가

        with patch.object(auth_manager, "refresh_session", return_value=True) as mock_refresh:
            result = auth_manager.auto_refresh_if_needed(current_time=now)

            assert result is False
            mock_refresh.assert_not_called()

    def test_auto_refresh_if_needed_not_authenticated(self, auth_manager):
        """인증되지 않은 상태에서는 새로고침하지 않음"""
        now = datetime.now()

        with patch.object(auth_manager, "refresh_session", return_value=True) as mock_refresh:
            result = auth_manager.auto_refresh_if_needed(current_time=now)

            assert result is False
            mock_refresh.assert_not_called()

    def test_get_auth_info_dict(self, auth_manager):
        """인증 정보 딕셔너리 반환"""
        auth_manager.auth_state = AuthState.AUTHENTICATED
        auth_manager.cookies = {"session_id": "test", "NNB": "test_nnb"}
        auth_manager.api_token = "api_token"
        auth_manager.last_authenticated = datetime.now()

        info = auth_manager.get_auth_info()

        assert "auth_state" in info
        assert "last_authenticated" in info
        assert "cookie_count" in info
        assert "has_api_token" in info
        assert info["auth_state"] == "AUTHENTICATED"
        assert info["cookie_count"] == 2
        assert "NNB" in info["cookie_names"]
        assert info["has_api_token"] is True
