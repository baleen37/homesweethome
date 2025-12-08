"""호갱노노 API 클라이언트 테스트"""

import pytest
from unittest.mock import Mock, patch

from crawler.api.hogangnono_client import (
    APIResponse,
    HogangnonoAPIClient,
    SearchParams,
)
from crawler.config import CrawlerConfig


@pytest.fixture
def config():
    """테스트용 설정"""
    return CrawlerConfig.from_env()


@pytest.fixture
def client(config):
    """테스트용 클라이언트"""
    with HogangnonoAPIClient(config) as client:
        yield client


@pytest.fixture
def search_params():
    """테스트용 검색 파라미터"""
    return SearchParams(
        bbox=(37.5, 126.9, 37.6, 127.0),
        level=15,
        tradeType=0,
        priceType=0,
    )


class TestSearchParams:
    """SearchParams 데이터클래스 테스트"""

    def test_to_dict_empty(self):
        """빈 SearchParams to_dict 테스트"""
        params = SearchParams()
        result = params.to_dict()
        # 실제 반환값 확인
        print(f"Actual result: {result}")
        # 빈 SearchParams는 최소한의 기본값만 포함
        assert "map" in result
        assert result["map"] == "google"
        assert "level" in result
        assert result["level"] == "17"

    def test_to_dict_with_bbox(self):
        """bbox가 있는 SearchParams to_dict 테스트"""
        params = SearchParams(bbox=(37.5, 126.9, 37.6, 127.0))
        result = params.to_dict()
        # bbox는 startX/startY/endX/endY로 변환되어야 함
        assert result["startX"] == 37.5
        assert result["startY"] == 126.9
        assert result["endX"] == 37.6
        assert result["endY"] == 127.0
        # 기본값들도 포함되어야 함
        assert "map" in result
        assert result["map"] == "google"

    def test_to_dict_with_all_params(self, search_params):
        """모든 파라미터가 있는 SearchParams to_dict 테스트"""
        result = search_params.to_dict()
        # bbox 파라미터가 좌표로 변환되었는지 확인
        assert result["startX"] == 37.5
        assert result["startY"] == 126.9
        assert result["endX"] == 37.6
        assert result["endY"] == 127.0
        # 기타 파라미터 확인
        assert result["level"] == "15"
        assert result["tradeType"] == 0
        # 기본값들도 포함되는지 확인
        assert "map" in result
        assert result["map"] == "google"


class TestAPIResponse:
    """APIResponse 클래스 테스트"""

    def test_from_response_success(self):
        """성공 응답 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "success": True,
            "data": {"items": []},
        }

        api_response = APIResponse.from_response(mock_response)
        assert api_response.success is True
        assert api_response.data == {"items": []}  # data 필드만 추출됨
        assert api_response.error is None
        assert api_response.status_code == 200

    def test_from_response_direct_data(self):
        """직접 데이터 응답 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"items": []}

        api_response = APIResponse.from_response(mock_response)
        assert api_response.success is True
        assert api_response.data == {"items": []}
        assert api_response.error is None
        assert api_response.status_code == 200

    def test_from_response_error(self):
        """에러 응답 테스트"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = Exception("Bad Request")

        api_response = APIResponse.from_response(mock_response)
        assert api_response.success is False
        assert api_response.error is not None
        assert api_response.status_code == 400


class TestHogangnonoAPIClient:
    """HogangnonoAPIClient 테스트"""

    @patch("crawler.api.hogangnono_client.Session")
    def test_init(self, mock_session_class, config):
        """초기화 테스트"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        assert client.base_url == "https://hogangnono.com"
        assert client.session == mock_session
        assert client.min_delay == 1.0
        # 세션 초기화 상태 확인
        assert client._session_initialized is False

    @patch("crawler.api.hogangnono_client.Session")
    def test_build_url(self, mock_session_class, config):
        """URL 빌드 테스트"""
        client = HogangnonoAPIClient(config)

        url = client._build_url("/api/test")
        assert url == "https://hogangnono.com/api/test"

    @patch("crawler.api.hogangnono_client.Session")
    def test_make_request_success(self, mock_session_class, config):
        """성공 요청 테스트"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": {"items": []}}
        mock_session.request.return_value = mock_response
        mock_session.get.return_value = Mock(status_code=200)
        mock_session.cookies = Mock()
        mock_session.cookies.__iter__ = Mock(return_value=iter([]))
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        api_response = client._make_request(
            method="GET",
            endpoint="/api/test",
            params={"q": "test"},
        )

        assert api_response.success is True
        mock_session.request.assert_called_once()

    @patch("crawler.api.hogangnono_client.Session")
    def test_get_ranking(self, mock_session_class, config):
        """랭킹 조회 테스트"""
        mock_session = Mock()
        # 세션 초기화를 위한 Mock 응답
        mock_session.get.return_value = Mock(
            status_code=200,
        )
        mock_session.cookies = []  # 빈 쿠키 리스트
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        # API 응답 Mock 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": []}
        mock_session.request.return_value = mock_response

        response = client.get_ranking(rank_type="daily", limit=10)

        assert response.success is True
        # API 호출 확인 - headers는 실제 값으로 확인
        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        assert call_args[1]["method"] == "GET"
        assert "api/v2/ranks/rolling" in call_args[1]["url"]
        assert call_args[1]["params"]["type"] == "daily"
        assert call_args[1]["params"]["limit"] == 10

    @patch("crawler.api.hogangnono_client.Session")
    def test_get_recent_visits(self, mock_session_class, config):
        """최근 조회 목록 테스트"""
        mock_session = Mock()
        # 세션 초기화를 위한 Mock 응답
        mock_session.get.return_value = Mock(
            status_code=200,
        )
        mock_session.cookies = []  # 빈 쿠키 리스트
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        # API 응답 Mock 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": []}
        mock_session.request.return_value = mock_response

        response = client.get_recent_visits(apt_type="apart", limit=50)

        assert response.success is True
        # API 호출 확인 - headers는 실제 값으로 확인
        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        assert call_args[1]["method"] == "GET"
        assert "api/v2/apts/recent-visits" in call_args[1]["url"]
        assert call_args[1]["params"]["aptType"] == "apart"
        assert call_args[1]["params"]["limit"] == 50

    @patch("crawler.api.hogangnono_client.Session")
    def test_get_region_info(self, mock_session_class, config):
        """지역 정보 조회 테스트"""
        mock_session = Mock()
        # 세션 초기화를 위한 Mock 응답
        mock_session.get.return_value = Mock(
            status_code=200,
        )
        mock_session.cookies = []  # 빈 쿠키 리스트
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        # API 응답 Mock 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": []}
        mock_session.request.return_value = mock_response

        response = client.get_region_info(lat=37.5, lng=126.9, zoom=15)

        assert response.success is True
        # API 호출 확인 - headers는 실제 값으로 확인
        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        assert call_args[1]["method"] == "GET"
        assert "api/v2/maps/region" in call_args[1]["url"]
        assert call_args[1]["params"]["lat"] == 37.5
        assert call_args[1]["params"]["lng"] == 126.9
        assert call_args[1]["params"]["zoom"] == 15

    @patch("crawler.api.hogangnono_client.Session")
    def test_get_pois_bounding(self, mock_session_class, config, search_params):
        """POI 정보 조회 테스트"""
        mock_session = Mock()
        # 세션 초기화를 위한 Mock 응답
        mock_session.get.return_value = Mock(
            status_code=200,
        )
        mock_session.cookies = []  # 빈 쿠키 리스트
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        # API 응답 Mock 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": []}
        mock_session.request.return_value = mock_response

        response = client.get_pois_bounding(search_params)

        assert response.success is True
        mock_session.request.assert_called_once_with(
            method="GET",
            url="https://hogangnono.com/api/v2/pois-bounding",
            params=search_params.to_dict(),
            json=None,
            headers={},
            timeout=config.timeout,
        )

    @patch("crawler.api.hogangnono_client.Session")
    def test_get_apartments_bounding(self, mock_session_class, config, search_params):
        """아파트 목록 조회 테스트"""
        mock_session = Mock()
        mock_session.request.return_value = Mock(
            status_code=200,
            json=lambda: {"success": True, "data": []},
        )
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        response = client.get_apartments_bounding(search_params)

        assert response.success is True

        expected_params = search_params.to_dict()
        expected_params["apt_type"] = "apart"
        expected_params["trade_type"] = "sale"

        mock_session.request.assert_called_once_with(
            method="GET",
            url="https://hogangnono.com/api/apt/bounding",
            params=expected_params,
            json=None,
            headers={},
            timeout=config.timeout,
        )

    @patch("crawler.api.hogangnono_client.Session")
    def test_search_apartments(self, mock_session_class, config):
        """아파트 검색 테스트"""
        mock_session = Mock()
        mock_session.request.return_value = Mock(
            status_code=200,
            json=lambda: {"success": True, "data": []},
        )
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        response = client.search_apartments(
            query="강남구 아파트",
            page=1,
            limit=20,
        )

        assert response.success is True
        mock_session.request.assert_called_once_with(
            method="GET",
            url="https://hogangnono.com/api/search/apartments",
            params={"q": "강남구 아파트", "page": 1, "limit": 20},
            json=None,
            headers={},
            timeout=config.timeout,
        )

    @patch("crawler.api.hogangnono_client.Session")
    def test_get_apartment_detail(self, mock_session_class, config):
        """아파트 상세 정보 조회 테스트"""
        mock_session = Mock()
        mock_session.request.return_value = Mock(
            status_code=200,
            json=lambda: {"success": True, "data": {}},
        )
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        response = client.get_apartment_detail("apt_123")

        assert response.success is True
        mock_session.request.assert_called_once_with(
            method="GET",
            url="https://hogangnono.com/api/apt/apt_123",
            params=None,
            json=None,
            headers={},
            timeout=config.timeout,
        )

    @patch("crawler.api.hogangnono_client.Session")
    def test_context_manager(self, mock_session_class, config):
        """컨텍스트 매니저 테스트"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        with HogangnonoAPIClient(config) as client:
            assert client.session == mock_session

        # 컨텍스트 종료 시 세션 클로즈 확인
        mock_session.close.assert_called_once()
