"""HogangnonoAPIClient 클래스 단위 테스트"""

import pytest
from unittest.mock import Mock, patch
from requests import Response, Session

from crawler.config import CrawlerConfig
from crawler.api.hogangnono_client import HogangnonoAPIClient, SearchParams, APIResponse
from tests.fixtures.hogangnono_responses import (
    MOCK_POIS_BOUNDING_RESPONSE,
    MOCK_RANKS_ROLLING_RESPONSE,
    MOCK_COMPLEX_LIST_RESPONSE,
)


class TestHogangnonoAPIClient:
    """HogangnonoAPIClient 클래스 테스트"""

    @pytest.fixture
    def config(self):
        """테스트용 CrawlerConfig fixture"""
        return CrawlerConfig(user_agent="test-agent", timeout=10)

    @pytest.fixture
    def client(self, config):
        """테스트용 HogangnonoAPIClient fixture"""
        return HogangnonoAPIClient(config)

    def test_initialization(self, client, config):
        """클라이언트 초기화 테스트"""
        assert client.config == config
        assert client.base_url == "https://hogangnono.com"
        assert isinstance(client.session, Session)
        assert client._session_initialized is False

    def test_build_url(self, client):
        """URL 빌드 테스트"""
        url = client._build_url("/api/test")
        assert url == "https://hogangnono.com/api/test"

        url = client._build_url("api/test")
        assert url == "https://hogangnono.com/api/test"

    def test_initialize_session_success(self, client):
        """세션 초기화 성공 테스트"""
        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock(spec=Response)
            mock_response.status_code = 200
            mock_response.cookies = []
            mock_get.return_value = mock_response

            result = client._initialize_session()

            assert result is True
            assert client._session_initialized is True
            mock_get.assert_called_once_with(
                client.base_url, headers=pytest.any(dict), timeout=client.config.timeout
            )

    def test_initialize_session_failure(self, client):
        """세션 초기화 실패 테스트"""
        with patch.object(client.session, "get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            result = client._initialize_session()

            assert result is False
            assert client._session_initialized is False

    def test_initialize_session_already_initialized(self, client):
        """이미 초기화된 세션 테스트"""
        client._session_initialized = True

        with patch.object(client.session, "get") as mock_get:
            result = client._initialize_session()

            assert result is True
            mock_get.assert_not_called()

    def test_get_api_headers(self, client):
        """API 헤더 생성 테스트"""
        headers = client._get_api_headers()

        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Accept-Language" in headers
        assert "X-Requested-With" in headers
        assert headers["X-Requested-With"] == "XMLHttpRequest"

    def test_add_auth_headers(self, client):
        """인증 헤더 추가 테스트"""
        custom_headers = {"Custom-Header": "custom-value"}
        final_headers = client._add_auth_headers(custom_headers)

        assert "Custom-Header" in final_headers
        assert final_headers["Custom-Header"] == "custom-value"
        assert "User-Agent" in final_headers
        assert "Accept" in final_headers

    def test_add_auth_headers_none(self, client):
        """인증 헤더 추가 (None 입력) 테스트"""
        final_headers = client._add_auth_headers(None)

        assert "User-Agent" in final_headers
        assert "Accept" in final_headers

    @patch.object(HogangnonoAPIClient, "_initialize_session")
    @patch.object(Session, "request")
    def test_make_request_success(self, mock_request, mock_init, client):
        """HTTP 요청 성공 테스트"""
        # 초기화되지 않은 상태에서 _initialize_session 호출
        client._session_initialized = False
        mock_init.return_value = True

        # Mock 응답 설정
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": {}}
        mock_response.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_response

        # API 호출
        result = client._make_request(method="GET", endpoint="/api/test", params={"test": "value"})

        # 결과 검증
        assert isinstance(result, APIResponse)
        assert result.success is True
        assert result.status_code == 200

        # 요청 검증
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]["method"] == "GET"
        assert call_args[1]["url"] == "https://hogangnono.com/api/test"
        assert call_args[1]["params"] == {"test": "value"}

    @patch.object(HogangnonoAPIClient, "_initialize_session")
    def test_make_request_session_init_failure(self, mock_init, client):
        """세션 초기화 실패 시 요청 테스트"""
        client._session_initialized = False
        mock_init.return_value = False

        result = client._make_request(method="GET", endpoint="/api/test")

        assert result.success is False
        assert "Failed to initialize session" in result.error
        assert result.status_code is None

    @patch.object(HogangnonoAPIClient, "_initialize_session")
    @patch.object(Session, "request")
    def test_make_request_with_data(self, mock_request, mock_init, client):
        """JSON 데이터와 함께 HTTP 요청 테스트"""
        client._session_initialized = True
        mock_init.return_value = True

        mock_response = Mock(spec=Response)
        mock_response.status_code = 201
        mock_response.json.return_value = {"success": True}
        mock_response.headers = {"content-type": "application/json"}
        mock_request.return_value = mock_response

        result = client._make_request(
            method="POST", endpoint="/api/test", data={"name": "test"}, params={"id": "123"}
        )

        assert result.success is True

        # JSON 데이터로 전달되는지 확인
        call_args = mock_request.call_args
        assert call_args[1]["json"] == {"name": "test"}
        assert call_args[1]["params"] == {"id": "123"}

    def test_get_complex_list(self, client):
        """단지 목록 조회 테스트"""
        with patch.object(client, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.success = True
            mock_response.data = MOCK_COMPLEX_LIST_RESPONSE
            mock_request.return_value = mock_response

            result = client.get_complex_list("1168010500", "test_bounds")

            assert result.success is True
            mock_request.assert_called_once_with(
                method="GET",
                endpoint="/cluster/ajax/complexList",
                params={"cortarNo": "1168010500", "bounds": "test_bounds"},
            )

    def test_get_complex_list_without_bounds(self, client):
        """bounds 없이 단지 목록 조회 테스트"""
        with patch.object(client, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.success = True
            mock_response.data = MOCK_COMPLEX_LIST_RESPONSE
            mock_request.return_value = mock_response

            result = client.get_complex_list("1168010500")

            assert result.success is True
            mock_request.assert_called_once_with(
                method="GET",
                endpoint="/cluster/ajax/complexList",
                params={"cortarNo": "1168010500"},
            )

    def test_get_complex_detail(self, client):
        """단지 상세 정보 조회 테스트"""
        with patch.object(client, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.success = True
            mock_response.data = {"complexNo": "123"}
            mock_request.return_value = mock_response

            result = client.get_complex_detail("C12345")

            assert result.success is True
            mock_request.assert_called_once_with(
                method="GET", endpoint="/cluster/ajax/complexDetail", params={"complexNo": "C12345"}
            )

    def test_get_apartments_bounding(self, client):
        """아파트 목록 조회 (bounding box) 테스트"""
        search_params = SearchParams(bbox=(126.7, 37.4, 127.0, 37.5), tradeType=0, aptType=1)

        with patch.object(client, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.success = True
            mock_response.data = MOCK_POIS_BOUNDING_RESPONSE
            mock_request.return_value = mock_response

            result = client.get_apartments_bounding(search_params)

            assert result.success is True
            mock_request.assert_called_once_with(
                method="GET", endpoint="/api/v2/pois-bounding", params=search_params.to_dict()
            )

    def test_fetch_ranks_rolling_success(self, client):
        """인기 순위 롤링 데이터 조회 성공 테스트"""
        with patch.object(client, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.success = True
            mock_response.data = MOCK_RANKS_ROLLING_RESPONSE
            mock_request.return_value = mock_response

            result = client.fetch_ranks_rolling()

            assert result == MOCK_RANKS_ROLLING_RESPONSE
            mock_request.assert_called_once_with(method="GET", endpoint="/api/v2/ranks/rolling")

    def test_fetch_ranks_rolling_failure(self, client):
        """인기 순위 롤링 데이터 조회 실패 테스트"""
        with patch.object(client, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.success = False
            mock_response.error = "API error"
            mock_request.return_value = mock_response

            with pytest.raises(Exception, match="Failed to fetch ranks/rolling"):
                client.fetch_ranks_rolling()

    def test_fetch_pois_bounding_success(self, client):
        """POI 데이터 조회 성공 테스트"""
        bounds = {"startX": 126.7, "endX": 127.0, "startY": 37.4, "endY": 37.5}

        with patch.object(client, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.success = True
            mock_response.data = MOCK_POIS_BOUNDING_RESPONSE
            mock_request.return_value = mock_response

            result = client.fetch_pois_bounding(bounds)

            assert result == MOCK_POIS_BOUNDING_RESPONSE
            mock_request.assert_called_once_with(
                method="GET",
                endpoint="/api/v2/pois-bounding",
                params={
                    "level": 17,
                    "startX": 126.7,
                    "endX": 127.0,
                    "startY": 37.4,
                    "endY": 37.5,
                    "isIgnorePin": False,
                },
            )

    def test_parse_complexes_from_ranks(self, client):
        """ranks/rolling 응답 파싱 테스트"""
        complexes = client.parse_complexes_from_ranks(MOCK_RANKS_ROLLING_RESPONSE)

        assert len(complexes) == 3
        assert complexes[0]["id"] == "rank_abc123"
        assert complexes[0]["aptName"] == "인기아파트"
        assert complexes[0]["region1"] == "서울특별시"
        assert complexes[0]["region2"] == "강남구"
        assert complexes[0]["region3"] == "대치동"
        assert complexes[0]["ranking"] == 1
        assert complexes[0]["prevRank"] == 2
        assert complexes[0]["visitor"] == 5000

    def test_parse_complexes_from_ranks_empty_data(self, client):
        """빈 ranks/rolling 응답 파싱 테스트"""
        empty_data = {"data": {}}
        complexes = client.parse_complexes_from_ranks(empty_data)

        assert len(complexes) == 0

    def test_parse_complexes_from_ranks_no_data(self, client):
        """data 필드가 없는 응답 파싱 테스트"""
        complexes = client.parse_complexes_from_ranks({})

        assert len(complexes) == 0

    def test_parse_pois_from_bounding(self, client):
        """pois-bounding 응답 파싱 테스트"""
        pois = client.parse_pois_from_bounding(MOCK_POIS_BOUNDING_RESPONSE)

        assert len(pois) == 2
        assert pois[0]["id"] == "complex_123456"
        assert pois[0]["name"] == "테스트아파트"
        assert pois[0]["lat"] == 37.5172
        assert pois[0]["lng"] == 127.0473
        assert pois[0]["type"] == "아파트"
        assert pois[0]["buildDate"] == "2005"
        assert pois[0]["households"] == 300

    def test_to_csv_rows_complexes(self, client):
        """단지 데이터 CSV 변환 테스트"""
        rows = client.to_csv_rows_complexes(MOCK_RANKS_ROLLING_RESPONSE)

        assert len(rows) == 3
        assert rows[0]["단지ID"] == "rank_abc123"
        assert rows[0]["단지명"] == "인기아파트"
        assert rows[0]["시도"] == "서울특별시"
        assert rows[0]["시군구"] == "강남구"
        assert rows[0]["동"] == "대치동"
        assert rows[0]["순위"] == 1
        assert rows[0]["방문자수"] == 5000

    def test_to_csv_rows_pois(self, client):
        """POI 데이터 CSV 변환 테스트"""
        rows = client.to_csv_rows_pois(MOCK_POIS_BOUNDING_RESPONSE)

        assert len(rows) == 2
        assert rows[0]["POI_ID"] == "complex_123456"
        assert rows[0]["명칭"] == "테스트아파트"
        assert rows[0]["위도"] == 37.5172
        assert rows[0]["경도"] == 127.0473
        assert rows[0]["유형"] == "아파트"
        assert rows[0]["건축년도"] == "2005"
        assert rows[0]["세대수"] == 300

    def test_close(self, client):
        """세션 종료 테스트"""
        with patch.object(client.session, "close") as mock_close:
            client.close()
            mock_close.assert_called_once()

    def test_context_manager(self, client):
        """Context manager 테스트"""
        with patch.object(client, "close") as mock_close:
            with patch.object(client, "_initialize_session") as mock_init:
                mock_init.return_value = True

                with client:
                    pass

                mock_init.assert_called_once()
                mock_close.assert_called_once()

    def test_get_headers(self, client):
        """헤더 생성 테스트 (테스트용)"""
        headers = client._get_headers()

        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "x-hogangnono-app-name" in headers
        assert "x-hogangnono-platform" in headers
