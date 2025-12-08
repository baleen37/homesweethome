"""호갱노노 API 클라이언트 세션 관리 테스트

실제 세션 관리 로직과 쿠키 처리를 검증하는 테스트
"""

import pytest
import time
from unittest.mock import Mock, patch
from requests import RequestException

from crawler.api.hogangnono_client import HogangnonoAPIClient
from crawler.config import CrawlerConfig


@pytest.fixture
def config():
    """테스트용 설정"""
    return CrawlerConfig(
        user_agent="Mozilla/5.0 (Session Test)",
        timeout=10.0,
    )


class TestSessionManagement:
    """세션 관리 테스트"""

    def test_session_initialization_flow(self, config):
        """세션 초기화 흐름 테스트"""
        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # 메인 페이지 응답 모킹
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "<html><body>Welcome</body></html>"
            mock_session.get.return_value = mock_response

            # 쿠키 모킹
            mock_cookie = Mock()
            mock_cookie.name = "hogang_session"
            mock_cookie.value = "test123"
            mock_cookie.domain = "hogangnono.com"
            mock_session.cookies = [mock_cookie]

            client = HogangnonoAPIClient(config)

            # 첫 번째 요청 - 세션 초기화 발생
            api_response = client._make_request("GET", "/api/test")

            assert api_response.success is True
            assert client._session_initialized is True

            # 메인 페이지 GET 요청 확인
            mock_session.get.assert_called_once()
            call_args = mock_session.get.call_args
            assert call_args[0][0] == "https://hogangnono.com"
            assert "User-Agent" in call_args[1]["headers"]

    @patch("requests.Session")
    def test_session_already_initialized(self, mock_session_class, config):
        """이미 초기화된 세션 동작 테스트"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": {}}
        mock_session.request.return_value = mock_response

        client = HogangnonoAPIClient(config)

        # 첫 번째 요청 - 세션 초기화
        client._make_request("GET", "/api/test")

        # 두 번째 요청 - 세션 초기화 재시도 방지 확인
        call_count_before = mock_session.get.call_count
        client._make_request("GET", "/api/test")
        call_count_after = mock_session.get.call_count

        # 두 번째 요청에서 get()이 호출되지 않아야 함
        assert call_count_after == call_count_before

    def test_session_close_on_context_exit(self, config):
        """Context manager 종료 시 세션 닫기 테스트"""
        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            with HogangnonoAPIClient(config) as client:
                # 요청 한 번 실행
                client._make_request("GET", "/api/test")

            # 컨텍스트 종료 시 close() 호출 확인
            mock_session.close.assert_called_once()

    def test_session_close_error_handling(self, config):
        """세션 닫기 오류 처리 테스트"""
        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # close()에서 오류 발생시켜도 무시되는지 테스트
            mock_session.close.side_effect = Exception("Close error")

            with HogangnonoAPIClient(config):
                pass  # 컨텍스트 관리자가 close() 오류를 무시해야 함

            # 예외가 발생하지 않으면 성공
            assert True

    def test_session_initialization_failure(self, config):
        """세션 초기화 실패 처리 테스트"""
        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # 메인 페이지 접속 실패 모킹
            mock_session.get.side_effect = RequestException("Connection failed")

            client = HogangnonoAPIClient(config)

            # API 요청 - 세션 초기화 실패 처리 확인
            response = client._make_request("GET", "/api/test")

            assert response.success is False
            assert "Failed to initialize session" in response.error
            assert client._session_initialized is False

    def test_session_cookie_persistence(self, config):
        """쿠키 지속성 테스트"""
        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # 첫 번째 응답
            mock_response1 = Mock()
            mock_response1.status_code = 200
            mock_response1.headers = {"content-type": "application/json"}
            mock_response1.json.return_value = {
                "success": True,
                "data": {},
                "set-cookie": "session_id=abc123; Path=/",
            }

            # 두 번째 응답
            mock_response2 = Mock()
            mock_response2.status_code = 200
            mock_response2.headers = {"content-type": "application/json"}
            mock_response2.json.return_value = {"success": True, "data": {}}

            mock_session.request.side_effect = [mock_response1, mock_response2]

            client = HogangnonoAPIClient(config)

            # 첫 번째 요청
            response1 = client._make_request("GET", "/api/test")

            # 쿠키 설정 확인
            cookie_jar = mock_session.cookies
            assert len(cookie_jar) > 0

            # 두 번째 요청
            response2 = client._make_request("GET", "/api/test")

            assert response1.success is True
            assert response2.success is True

            # 두 요청 모두 동일한 세션 사용
            assert mock_session.request.call_count == 2

    def test_session_cookie_logging(self, config, caplog):
        """쿠키 로깅 테스트"""
        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # 쿠키 모킹
            mock_cookie1 = Mock()
            mock_cookie1.name = "auth_token"
            mock_cookie1.value = "secret123"
            mock_cookie2 = Mock()
            mock_cookie2.name = "user_id"
            mock_cookie2.value = "user456"

            mock_session.cookies = [mock_cookie1, mock_cookie2]
            mock_session.get.return_value = Mock(
                status_code=200, text="<html><body>Test</body></html>"
            )

            client = HogangnonoAPIClient(config)

            # 요청 실행 (로그 캡처)
            client._make_request("GET", "/api/test")

            # 쿠키 정보 로그 확인
            assert "auth_token" in caplog.text or "cookies=" in caplog.text

    def test_session_reinitialization_after_failure(self, config):
        """세션 초기화 실패 후 재시도 테스트"""
        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            client = HogangnonoAPIClient(config)

            # 첫 번째 시도 - 실패
            mock_session.get.side_effect = RequestException("Connection failed")
            response1 = client._make_request("GET", "/api/test")

            assert response1.success is False

            # 세션 상태는 여전히 초기화되지 않음
            assert client._session_initialized is False

            # 두 번째 시도 - 성공
            mock_session.get.reset_mock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "<html><body>Success</body></html>"
            mock_session.get.return_value = mock_response

            response2 = client._make_request("GET", "/api/test")

            assert response2.success is True
            assert client._session_initialized is True

    def test_session_with_malformed_cookies(self, config):
        """잘못된 형식의 쿠키 처리 테스트"""
        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # 잘못된 형식의 쿠키 모킹
            mock_session.cookies = "invalid_cookie_format"
            mock_session.get.return_value = Mock(
                status_code=200, text="<html><body>Test</body></html>"
            )

            client = HogangnonoAPIClient(config)

            # 오류 발생 없이 처리되는지 확인
            response = client._make_request("GET", "/api/test")

            assert response.success is True
            assert client._session_initialized is True

    def test_session_headers_compatibility(self, config):
        """세션 헤더 호환성 테스트"""
        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # 메인 페이지 응답
            mock_session.get.return_value = Mock(
                status_code=200, text="<html><body>Test</body></html>"
            )

            client = HogangnonoAPIClient(config)

            # 헤더 검증을 위한 API 요청
            api_response = client._make_request(
                "GET", "/api/v2/test", headers={"X-Custom": "value"}
            )

            assert api_response.success is True

            # 최종 요청 헤더 검증
            call_args = mock_session.request.call_args
            final_headers = call_args[1]["headers"]

            # API 헤더와 커스텀 헤더가 모두 포함되어야 함
            assert "X-Requested-With" in final_headers
            assert "X-Custom" in final_headers
            assert final_headers["X-Custom"] == "value"


class TestAuthenticationFlow:
    """인증 흐름 테스트"""

    @patch("requests.Session")
    def test_authentication_headers_added(self, mock_session_class, config):
        """인증 헤더 추가 테스트"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # 메인 페이지 응답
        mock_session.get.return_value = Mock(
            status_code=200, text="<html><body>Login page</body></html>"
        )

        # API 응답
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": {}}
        mock_session.request.return_value = mock_response

        client = HogangnonoAPIClient(config)

        # API 요청 - 인증 헤더 자동 추가 확인
        response = client._make_request("GET", "/api/me")

        assert response.success is True

        # 요청 헤더 검증
        call_args = mock_session.request.call_args
        headers = call_args[1]["headers"]

        # 필수 인증 헤더 확인
        assert "X-Requested-With" in headers
        assert headers["X-Requested-With"] == "XMLHttpRequest"
        assert "Referer" in headers
        assert headers["Referer"] == "https://hogangnono.com"
        assert "Origin" in headers
        assert headers["Origin"] == "https://hogangnono.com"

    @patch("requests.Session")
    def test_session_based_authentication(self, mock_session_class, config):
        """세션 기반 인증 테스트"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # 로그인 페이지 접속
        mock_session.get.return_value = Mock(
            status_code=200, text="<html><body>Login successful</body></html>"
        )

        # 인증이 필요한 API 응답
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "success": True,
            "data": {"user_id": "test_user", "is_authenticated": True},
        }
        mock_session.request.return_value = mock_response

        client = HogangnonoAPIClient(config)

        # 인증 API 요청
        response = client._make_request("GET", "/api/user/profile")

        assert response.success is True
        assert response.data["user_id"] == "test_user"

    @patch("requests.Session")
    def test_authentication_error_handling(self, mock_session_class, config):
        """인증 오류 처리 테스트"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # 메인 페이지는 성공
        mock_session.get.return_value = Mock(
            status_code=200, text="<html><body>Login page</body></html>"
        )

        # 인증 실패 응답
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"status": "error", "message": "로그인 하지 않았습니다."}
        mock_response.raise_for_status.side_effect = RequestException("Unauthorized")
        mock_session.request.return_value = mock_response

        client = HogangnonoAPIClient(config)

        # 인증 실패 응답 처리
        response = client._make_request("GET", "/api/me")

        assert response.success is False
        assert response.status_code == 401
        assert "로그인" in response.error or "인증" in response.error


class TestRateLimitingWithSession:
    """세션 기반 Rate Limiting 테스트"""

    @patch("requests.Session")
    def test_rate_limiting_with_session(self, mock_session_class, config):
        """세션을 통한 Rate Limiting 동작 테스트"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # 성공 응답
        success_response = Mock()
        success_response.status_code = 200
        success_response.headers = {"content-type": "application/json"}
        success_response.json.return_value = {"success": True, "data": {}}

        # Rate limit 응답
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {"content-type": "application/json", "retry-after": "30"}
        rate_limit_response.raise_for_status.side_effect = RequestException("Too Many Requests")

        mock_session.get.return_value = Mock(status_code=200, text="<html><body>Test</body></html>")
        mock_session.request.side_effect = [success_response, rate_limit_response]

        client = HogangnonoAPIClient(config)

        # 첫 번째 요청 - 성공
        response1 = client._make_request("GET", "/api/test")
        assert response1.success is True

        # 두 번째 요청 - Rate limit
        response2 = client._make_request("GET", "/api/test")
        assert response2.success is False
        assert "429" in response2.error

    @patch("requests.Session")
    def test_consecutive_requests_with_same_session(self, mock_session_class, config):
        """동일 세션에서의 연속 요청 테스트"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # 동일한 성공 응답
        response_mock = Mock()
        response_mock.status_code = 200
        response_mock.headers = {"content-type": "application/json"}
        response_mock.json.return_value = {"success": True, "data": {}}
        mock_session.request.return_value = response_mock

        mock_session.get.return_value = Mock(status_code=200, text="<html><body>Test</body></html>")

        client = HogangnonoAPIClient(config)

        start_time = time.time()

        # 여러 연속 요청
        responses = []
        for i in range(5):
            response = client._make_request("GET", f"/api/test{i}")
            responses.append(response)

        total_time = time.time() - start_time

        # 모든 요청이 성공해야 함
        assert all(r.success for r in responses)

        # 최소 지연 시간 보장 (요청당 최소 1초)
        assert total_time >= len(responses) * client.min_delay

        # 모든 요청이 동일 세션 사용
        assert mock_session.request.call_count == 5
