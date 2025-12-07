"""
NaverApiClient와 NaverAuthManager 통합 테스트
"""

import pytest
from unittest.mock import Mock, patch

from crawler.api.naver_client import NaverAPIClient, APIEndpoint
from crawler.api.auth_manager import AuthState
from crawler.config import CrawlerConfig


@pytest.fixture
def config():
    """테스트용 설정 객체"""
    return CrawlerConfig.from_env()


@pytest.fixture
def api_client(config):
    """테스트용 API 클라이언트"""
    return NaverAPIClient(config)


class TestNaverApiClientAuthIntegration:
    """NaverApiClient와 NaverAuthManager 통합 테스트"""

    def test_init_with_auth_manager(self, api_client):
        """초기화 시 AuthManager가 생성됨"""
        assert api_client.auth_manager is not None
        assert hasattr(api_client.auth_manager, "is_authenticated")

    def test_is_authenticated_delegates_to_auth_manager(self, api_client):
        """is_authenticated가 AuthManager에 위임됨"""
        # AuthManager의 상태 설정
        api_client.auth_manager.auth_state = AuthState.AUTHENTICATED
        # NNB 쿠키 추가
        api_client.auth_manager.cookies = {"NNB": "test_nnb"}

        assert api_client.is_authenticated() is True

    def test_update_cookies_delegates_to_auth_manager(self, api_client):
        """update_cookies가 AuthManager에 위임됨"""
        cookies = {"session_id": "test", "auth_token": "token"}

        with patch.object(api_client.auth_manager, "update_cookies") as mock_update:
            api_client.update_cookies(cookies)

            mock_update.assert_called_once_with(cookies)

    def test_clear_cookies_delegates_to_auth_manager(self, api_client):
        """clear_cookies가 AuthManager에 위임됨"""
        with patch.object(api_client.auth_manager, "clear_cookies") as mock_clear:
            api_client.clear_cookies()

            mock_clear.assert_called_once()

    def test_refresh_session_delegates_to_auth_manager(self, api_client):
        """refresh_session이 AuthManager에 위임됨"""
        with patch.object(api_client.auth_manager, "refresh_session") as mock_refresh:
            mock_refresh.return_value = True

            result = api_client.refresh_session()

            assert result is True
            mock_refresh.assert_called_once()

    def test_get_auth_info_delegates_to_auth_manager(self, api_client):
        """get_auth_info가 AuthManager에 위임됨"""
        expected_info = {"auth_state": "UNAUTHENTICATED"}

        with patch.object(api_client.auth_manager, "get_auth_info") as mock_get_info:
            mock_get_info.return_value = expected_info

            result = api_client.get_auth_info()

            assert result == expected_info
            mock_get_info.assert_called_once()

    def test_set_api_token_updates_auth_manager(self, api_client):
        """set_api_token이 AuthManager의 토큰을 업데이트함"""
        token = "test_api_token"

        api_client.set_api_token(token)

        assert api_client.auth_manager.api_token == token

    @patch("requests.Session.get")
    def test_fetch_with_auto_refresh(self, mock_get, api_client):
        """API 호출 시 자동 새로고침 확인"""
        # Mock 응답 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_response.cookies = {}
        mock_get.return_value = mock_response

        # AuthManager mock 설정
        with patch.object(api_client.auth_manager, "auto_refresh_if_needed") as mock_auto_refresh:
            with patch.object(api_client.auth_manager, "get_api_headers") as mock_headers:
                mock_headers.return_value = {"Content-Type": "application/json"}

                # API 호출
                api_client.fetch(APIEndpoint.COMPLEX_LIST)

                # 자동 새로고침 호출 확인
                mock_auto_refresh.assert_called_once()

    @patch("requests.Session.get")
    def test_fetch_updates_cookies_from_response(self, mock_get, api_client):
        """응답 쿠키가 AuthManager에 업데이트됨"""
        # Mock 응답 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_response.cookies = {"session_id": "new_session"}
        mock_get.return_value = mock_response

        # AuthManager mock 설정
        with patch.object(api_client.auth_manager, "auto_refresh_if_needed"):
            with patch.object(api_client.auth_manager, "get_api_headers"):
                with patch.object(api_client.auth_manager, "update_cookies") as mock_update:
                    # API 호출
                    api_client.fetch(APIEndpoint.ARTICLE_LIST)

                    # 쿠키 업데이트 확인
                    mock_update.assert_called_once()

    def test_headers_include_auth_manager_headers(self, api_client):
        """헤더에 AuthManager의 헤더가 포함됨"""
        # AuthManager 헤더 mock 설정
        auth_headers = {
            "User-Agent": "test-agent",
            "Authorization": "Bearer token123",
            "Content-Type": "application/json",
        }

        with patch.object(api_client.auth_manager, "get_api_headers") as mock_auth_headers:
            mock_auth_headers.return_value = auth_headers

            headers = api_client._get_api_headers()

            # AuthManager 헤더가 포함되는지 확인
            assert headers["User-Agent"] == "test-agent"
            assert headers["Authorization"] == "Bearer token123"
            assert headers["Content-Type"] == "application/json"

            # 네이버 특화 헤더도 포함되는지 확인
            assert headers["Cache-Control"] == "no-cache"
            assert headers["Pragma"] == "no-cache"
            assert headers["Referer"] == "https://new.land.naver.com/"

    @patch("requests.Session.get")
    def test_429_error_handling_with_auth(self, mock_get, api_client):
        """429 에러 처리 시 인증 상태 유지"""
        # 첫 번째 요청은 429, 두 번째는 성공
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.text = "Rate limit exceeded"

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"result": "success"}
        mock_response_success.cookies = {}

        mock_get.side_effect = [mock_response_429, mock_response_success]

        # AuthManager mock 설정
        with patch.object(api_client.auth_manager, "auto_refresh_if_needed"):
            with patch.object(api_client.auth_manager, "get_api_headers"):
                with patch.object(api_client.auth_manager, "update_cookies"):
                    # API 호출 (재시도 로직으로 인해 두 번 호출됨)
                    result = api_client.fetch(APIEndpoint.COMPLEX_DETAIL)

                    # 최종적으로 성공해야 함
                    assert result == {"result": "success"}

                    # 재시도 지연 시간 증가 확인
                    assert api_client.retry_delay > api_client.config.retry_delay
