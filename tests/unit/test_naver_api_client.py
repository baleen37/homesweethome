"""네이버 API 클라이언트 테스트"""

import json
from unittest.mock import Mock, patch

import pytest

from crawler.api.naver_client import NaverApiClient
from crawler.config import CrawlerConfig


@pytest.fixture
def config():
    """테스트용 CrawlerConfig fixture"""
    return CrawlerConfig(
        timeout=30,
        retry_attempts=3,
        retry_delay=1.0,
        delay_seconds=5.0,
    )


@pytest.fixture
def api_client(config):
    """NaverApiClient fixture"""
    return NaverApiClient(config)


class TestNaverApiClient:
    """NaverApiClient 테스트 클래스"""

    def test_init(self, api_client, config):
        """초기화 테스트"""
        assert api_client.config == config
        assert api_client.base_url == "https://m.land.naver.com"  # 기본값
        assert api_client.timeout == config.timeout
        assert api_client.max_retries == config.retry_attempts  # config 필드명과 다름
        assert api_client.retry_delay == config.retry_delay
        assert api_client._session is None

    def test_get_api_headers(self, api_client):
        """API 헤더 생성 테스트"""
        headers = api_client._get_api_headers()

        assert "Accept" in headers
        assert "Accept-Language" in headers
        assert "User-Agent" in headers
        assert "X-Requested-With" in headers
        assert headers["X-Requested-With"] == "XMLHttpRequest"

    def test_build_url(self, api_client):
        """URL 빌드 테스트"""
        endpoint = "/test/endpoint"
        params = {"param1": "value1", "param2": "value2"}

        url = api_client._build_url(endpoint, params)

        assert "https://m.land.naver.com/test/endpoint" in url
        assert "param1=value1" in url
        assert "param2=value2" in url

    def test_build_url_without_params(self, api_client):
        """파라미터 없는 URL 빌드 테스트"""
        endpoint = "/test/endpoint"

        url = api_client._build_url(endpoint)

        assert url == "https://m.land.naver.com/test/endpoint"

    @patch("crawler.api.naver_client.requests.Session")
    def test_get_session(self, mock_session_class, api_client):
        """세션 가져오기 테스트"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # 첫 호출
        session1 = api_client._get_session()
        assert session1 == mock_session
        mock_session_class.assert_called_once()

        # 두 번째 호출 (캐시된 세션 반환)
        session2 = api_client._get_session()
        assert session2 == session1
        assert mock_session_class.call_count == 1

    @patch("crawler.api.naver_client.requests.Session")
    def test_close_session(self, mock_session_class, api_client):
        """세션 닫기 테스트"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # 세션 생성
        api_client._get_session()
        assert api_client._session is not None

        # 세션 닫기
        api_client.close()
        mock_session.close.assert_called_once()
        assert api_client._session is None

    @patch("crawler.api.naver_client.NaverApiClient._get_session")
    def test_fetch_endpoint_with_retry_success(self, mock_get_session, api_client):
        """API 엔드포인트 요청 성공 테스트"""
        # Mock 설정
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"result": "success"}'
        mock_session.get.return_value = mock_response
        mock_get_session.return_value = mock_session

        # API 호출
        result = api_client._fetch_endpoint_with_retry("/test/endpoint", {"param": "value"})

        # 검증
        assert result == '{"result": "success"}'
        mock_session.get.assert_called_once()

        # URL과 파라미터 검증
        call_args = mock_session.get.call_args
        assert "/test/endpoint" in call_args[0][0]
        assert "param=value" in call_args[0][0]
        assert "timeout" in call_args[1]

    @patch("crawler.api.naver_client.NaverApiClient._get_session")
    def test_fetch_endpoint_with_retry_429_error(self, mock_get_session, api_client):
        """429 에러 발생 시 재시도 테스트"""
        # Mock 설정
        mock_session = Mock()
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.text = '{"result": "success"}'

        # 첫 호출은 429, 두 번째 호출은 200
        mock_session.get.side_effect = [mock_response_429, mock_response_200]
        mock_get_session.return_value = mock_session

        # API 호출
        with patch("time.sleep"):  # sleep 모킹
            result = api_client._fetch_endpoint_with_retry("/test/endpoint")

        # 검증
        assert result == '{"result": "success"}'
        assert mock_session.get.call_count == 2

    @patch("crawler.api.naver_client.NaverApiClient._get_session")
    def test_fetch_endpoint_with_retry_max_retries_exceeded(self, mock_get_session, api_client):
        """최대 재시도 횟수 초과 테스트"""
        # Mock 설정
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Server Error")
        mock_session.get.return_value = mock_response
        mock_get_session.return_value = mock_session

        # API 호출 (예외 발생 예상)
        with pytest.raises(Exception) as exc_info:
            with patch("time.sleep"):  # sleep 모킹
                api_client._fetch_endpoint_with_retry("/test/endpoint")

        # 검증
        assert "Server Error" in str(exc_info.value)
        assert mock_session.get.call_count == api_client.max_retries + 1  # 초기 호출 + 재시도

    def test_fetch_complex_list(self, api_client):
        """단지 목록 조회 테스트"""
        with patch.object(api_client, "_fetch_endpoint_with_retry") as mock_fetch:
            mock_fetch.return_value = json.dumps({"result": "success"})

            result = api_client.fetch_complex_list("12345", "1,2,3,4")

            # 검증
            assert result == {"result": "success"}
            mock_fetch.assert_called_once()

            # 파라미터 검증
            call_args = mock_fetch.call_args[0]
            assert call_args[0] == "/cluster/ajax/complexList"
            params = call_args[1]
            assert params["cortarNo"] == "12345"
            assert params["isp"] == "1,2,3,4"

    def test_fetch_complex_detail(self, api_client):
        """단지 상세 정보 조회 테스트"""
        with patch.object(api_client, "_fetch_endpoint_with_retry") as mock_fetch:
            mock_fetch.return_value = json.dumps({"result": "success"})

            result = api_client.fetch_complex_detail("12345")

            # 검증
            assert result == {"result": "success"}
            mock_fetch.assert_called_once()

            # 파라미터 검증
            call_args = mock_fetch.call_args[0]
            assert call_args[0] == "/cluster/ajax/complexDetail"
            assert call_args[1]["complexNo"] == "12345"

    def test_fetch_complex_listings(self, api_client):
        """단지 매물 목록 조회 테스트"""
        with patch.object(api_client, "_fetch_endpoint_with_retry") as mock_fetch:
            mock_fetch.return_value = json.dumps({"result": "success"})

            result = api_client.fetch_complex_listings("12345", "A1", 2)

            # 검증
            assert result == {"result": "success"}
            mock_fetch.assert_called_once()

            # 파라미터 검증
            call_args = mock_fetch.call_args[0]
            assert call_args[0] == "/cluster/ajax/articleList"
            params = call_args[1]
            assert params["complexNo"] == "12345"
            assert params["tradTpCd"] == "A1"
            assert params["page"] == 2

    def test_fetch_transaction_history(self, api_client):
        """거래내역 조회 테스트"""
        with patch.object(api_client, "_fetch_endpoint_with_retry") as mock_fetch:
            mock_fetch.return_value = json.dumps({"result": "success"})

            result = api_client.fetch_transaction_history("12345", "A1", 2024)

            # 검증
            assert result == {"result": "success"}
            mock_fetch.assert_called_once()

            # 파라미터 검증
            call_args = mock_fetch.call_args[0]
            assert call_args[0] == "/cluster/ajax/statsMonth"
            params = call_args[1]
            assert params["cortarNo"] == "12345"
            assert params["tradTpCd"] == "A1"
            assert params["yyyy"] == "2024"

    def test_context_manager(self, config):
        """컨텍스트 매니저 테스트"""
        with patch("crawler.api.naver_client.requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # 컨텍스트 매니저 사용
            with NaverApiClient(config) as client:
                assert client._session is not None

            # 컨텍스트 종료 시 세션 닫힘 확인
            mock_session.close.assert_called_once()
            assert client._session is None
