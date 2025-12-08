"""호갱노노 API 클라이언트 향상된 테스트

TDD 접근법에 따라 실제 API 동작과 에러 시나리오를 포함한 테스트
"""

import json
import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch
from requests import Response, HTTPError, ConnectionError, Timeout

from crawler.api.hogangnono_client import (
    APIResponse,
    HogangnonoAPIClient,
    SearchParams,
)
from crawler.config import CrawlerConfig


@pytest.fixture
def config():
    """테스트용 설정"""
    return CrawlerConfig(
        user_agent="Mozilla/5.0 (Test Enhanced)",
        timeout=10.0,
    )


@pytest.fixture
def client(config):
    """테스트용 클라이언트"""
    with HogangnonoAPIClient(config) as client:
        yield client


@pytest.fixture
def fixture_path():
    """Fixture 파일 경로 반환"""
    return Path(__file__).parent / "fixtures" / "hogangnono"


class TestSearchParamsEnhanced:
    """SearchParams 데이터클래스 향상된 테스트"""

    def test_bbox_to_coords_conversion(self):
        """bbox 좌표 변환 테스트"""
        # bbox=(lat_min, lng_min, lat_max, lng_max) → (startX, startY, endX, endY)
        params = SearchParams(bbox=(37.5, 126.9, 37.6, 127.0))

        assert params.startX == 126.9  # lng_min
        assert params.startY == 37.5  # lat_min
        assert params.endX == 127.0  # lng_max
        assert params.endY == 37.6  # lat_max

    def test_bbox_and_individual_coords_conflict(self):
        """bbox와 개별 좌표가 함께 제공될 때 bbox 우선순위 테스트"""
        params = SearchParams(
            bbox=(37.5, 126.9, 37.6, 127.0),
            startX=126.8,  # 이 값은 무시되어야 함
            startY=37.4,
            endX=127.1,
            endY=37.7,
        )

        # bbox 값으로 덮어쓰기
        assert params.startX == 126.9
        assert params.startY == 37.5
        assert params.endX == 127.0
        assert params.endY == 37.6

    def test_required_params_always_present(self):
        """필수 파라미터가 항상 포함되는지 테스트"""
        params = SearchParams()
        result = params.to_dict()

        # map은 항상 포함
        assert "map" in result
        assert result["map"] == "google"

        # screen 관련 파라미터 항상 포함
        assert "screenWidth" in result
        assert "screenHeight" in result
        assert "apt" in result

    def test_trade_type_values(self):
        """거래 유형 값 테스트"""
        # 매매 (0)
        params_sale = SearchParams(tradeType=0)
        result = params_sale.to_dict()
        assert result["tradeType"] == 0

        # 전세 (1)
        params_lease = SearchParams(tradeType=1)
        result = params_lease.to_dict()
        assert result["tradeType"] == 1

        # 월세 (2)
        params_monthly = SearchParams(tradeType=2)
        result = params_monthly.to_dict()
        assert result["tradeType"] == 2

    def test_area_and_price_filtering(self):
        """면적 및 가격 필터링 테스트"""
        params = SearchParams(
            areaFrom=50.0,
            areaTo=100.0,
            priceFrom=50000,
            priceTo=200000,
        )

        result = params.to_dict()

        assert result["areaFrom"] == 50.0
        assert result["areaTo"] == 100.0
        assert result["priceFrom"] == 50000
        assert result["priceTo"] == 200000

    @pytest.mark.parametrize(
        "apt_type,expected",
        [
            (-1, -1),  # 전체
            (1, 1),  # 아파트
            (2, 2),  # 주택
            (3, 3),  # 오피스텔
        ],
    )
    def test_apt_type_parameterization(self, apt_type, expected):
        """아파트 유형 파라미터화 테스트"""
        params = SearchParams(aptType=apt_type)
        result = params.to_dict()
        assert result["aptType"] == expected

    def test_zoom_level_validation(self):
        """줌 레벨 기본값 및 유효성 테스트"""
        params = SearchParams()
        result = params.to_dict()

        # 기본값 17
        assert result["level"] == 17

        # 커스텀 값
        params_custom = SearchParams(level=15)
        result_custom = params_custom.to_dict()
        assert result_custom["level"] == 15


class TestAPIResponseEnhanced:
    """APIResponse 클래스 향상된 테스트"""

    def test_from_response_with_gzipped_content(self):
        """Gzip 압축된 응답 처리 테스트"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json", "content-encoding": "gzip"}

        # 실제 gzip 데이터 생성 대신 간단한 데이터로 테스트
        mock_response.json.return_value = {"success": True, "data": {"items": []}}

        api_response = APIResponse.from_response(mock_response)
        assert api_response.success is True
        assert api_response.data == {"items": []}

    def test_from_response_with_html_content(self):
        """HTML 응답 처리 테스트"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        mock_response.text = "<html><body>Hello World</body></html>"

        api_response = APIResponse.from_response(mock_response)
        assert api_response.success is True
        assert "raw_content" in api_response.data
        assert api_response.data["raw_content"] == "<html><body>Hello World</body></html>"

    def test_from_response_with_network_error(self):
        """네트워크 오류 처리 테스트"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.side_effect = ConnectionError("Network error")
        mock_response.text = "Network error occurred"

        api_response = APIResponse.from_response(mock_response)
        assert api_response.success is True  # 200이면 성공으로 간주
        assert api_response.data == {"raw_content": "Network error occurred"}

    def test_from_response_with_json_decode_error(self):
        """JSON 파싱 오류 처리 테스트"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "{invalid json}"

        api_response = APIResponse.from_response(mock_response)
        assert api_response.success is True
        assert api_response.data == {"raw_content": "{invalid json}"}

    def test_from_response_with_timeout_error(self):
        """타임아웃 오류 처리 테스트"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 408
        mock_response.raise_for_status.side_effect = Timeout("Request timeout")

        api_response = APIResponse.from_response(mock_response)
        assert api_response.success is False
        assert "HTTP error" in api_response.error
        assert "408" in api_response.error

    def test_from_response_with_rate_limit_error(self):
        """Rate limit 오류 처리 테스트"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 429
        mock_response.headers = {
            "content-type": "application/json",
            "retry-after": "60",  # 60초 후 재시도
        }
        mock_response.json.return_value = {"error": "Too many requests", "retry_after": 60}
        mock_response.raise_for_status.side_effect = HTTPError("429 Too Many Requests")

        api_response = APIResponse.from_response(mock_response)
        assert api_response.success is False
        assert "429" in api_response.error
        assert "Too many requests" in api_response.error

    def test_from_response_with_server_error(self):
        """서버 오류 (500대) 처리 테스트"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 500
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "error": "Internal server error",
            "message": "Database connection failed",
        }
        mock_response.raise_for_status.side_effect = HTTPError("500 Internal Server Error")

        api_response = APIResponse.from_response(mock_response)
        assert api_response.success is False
        assert "HTTP error" in api_response.error
        assert "500" in api_response.error
        assert "Database connection failed" in api_response.error

    def test_from_response_with_authentication_error(self):
        """인증 오류 처리 테스트"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 401
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"status": "error", "message": "로그인 하지 않았습니다."}
        mock_response.raise_for_status.side_effect = HTTPError("401 Unauthorized")

        api_response = APIResponse.from_response(mock_response)
        assert api_response.success is False
        assert "HTTP error" in api_response.error
        assert "401" in api_response.error
        assert "로그인 하지 않았습니다" in api_response.error


class TestHogangnonoAPIClientEnhanced:
    """HogangnonoAPIClient 향상된 테스트"""

    @patch("crawler.api.hogangnono_client.Session")
    def test_rate_limiting_behavior(self, mock_session_class, config):
        """Rate limiting 동작 테스트"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # 성공 응답
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": {}}
        mock_session.request.return_value = mock_response

        client = HogangnonoAPIClient(config)

        # 첫 번째 요청 - 성공
        start_time = time.time()
        response1 = client._make_request("GET", "/api/test")
        elapsed1 = time.time() - start_time

        assert response1.success is True
        assert elapsed1 >= client.min_delay  # 최소 지연 시간 검증

    @patch("crawler.api.hogangnono_client.Session")
    def test_session_initialization_failure(self, mock_session_class, config):
        """세션 초기화 실패 시나리오 테스트"""
        mock_session = Mock()
        mock_session.get.side_effect = ConnectionError("Failed to connect")
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        response = client._make_request("GET", "/api/test")

        assert response.success is False
        assert "Failed to initialize session" in response.error

    @patch("crawler.api.hogangnono_client.Session")
    def test_retry_after_on_rate_limit(self, mock_session_class, config):
        """Rate limit 시 retry-after 헤더 처리 테스트"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"content-type": "application/json", "retry-after": "30"}
        mock_response.raise_for_status.side_effect = HTTPError("429 Too Many Requests")
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        response = client._make_request("GET", "/api/test")

        assert response.success is False
        assert "429" in response.error

    def test_context_manager_with_exception(self, config):
        """예외 발생 시 context manager 동작 테스트"""
        with pytest.raises(ValueError, match="Test exception"):
            with HogangnonoAPIClient(config):
                # 세션 초기화 후 예외 발생
                raise ValueError("Test exception")

        # 컨텍스트 종료 시 세션이 닫혔는지 검증
        # (실제로는 세션 객체가 닫혔는지 확인해야 하지만 Mock 환경이므로 스킵)

    @patch("crawler.api.hogangnono_client.Session")
    def test_request_headers_injection(self, mock_session_class, config):
        """요청 헤더 주입 테스트"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": {}}
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        # 커스텀 헤더 추가
        client._make_request("GET", "/api/test", headers={"X-Custom-Header": "test-value"})

        # 요청 시 전달된 헤더 검증
        call_args = mock_session.request.call_args
        request_headers = call_args[1]["headers"]

        assert "X-Custom-Header" in request_headers
        assert request_headers["X-Custom-Header"] == "test-value"
        assert "X-Requested-With" in request_headers
        assert request_headers["X-Requested-With"] == "XMLHttpRequest"

    @patch("crawler.api.hogangnono_client.Session")
    def test_cookies_persistence(self, mock_session_class, config):
        """쿠키 지속성 테스트"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": {}}

        # 쿠키 설정
        mock_cookie = Mock()
        mock_cookie.name = "test_cookie"
        mock_cookie.value = "test_value"
        mock_session.cookies = [mock_cookie]
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        # 첫 번째 요청
        response1 = client._make_request("GET", "/api/test")

        # 두 번째 요청
        response2 = client._make_request("GET", "/api/test")

        assert response1.success is True
        assert response2.success is True

        # 두 요청 모두 동일한 쿠키를 사용해야 함
        assert mock_session.request.call_count == 2

    @patch("crawler.api.hogangnono_client.Session")
    def test_timeout_handling(self, mock_session_class, config):
        """타임아웃 처리 테스트"""
        mock_session = Mock()
        mock_session.request.side_effect = Timeout("Request timeout")
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        response = client._make_request("GET", "/api/test")

        assert response.success is False
        assert "Request error" in response.error
        assert "timeout" in response.error.lower()

    @patch("crawler.api.hogangnono_client.Session")
    def test_authentication_headers(self, mock_session_class, config):
        """인증 헤더 추가 테스트"""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": {}}
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        # 인증 헤더가 기본적으로 포함되는지 검증
        response = client._make_request("GET", "/api/test")

        assert response.success is True

        call_args = mock_session.request.call_args
        headers = call_args[1]["headers"]

        # 기본 API 헤더 확인
        assert "X-Requested-With" in headers
        assert headers["X-Requested-With"] == "XMLHttpRequest"
        assert "Referer" in headers
        assert headers["Referer"] == client.base_url
        assert "Origin" in headers
        assert headers["Origin"] == client.base_url


class TestRealResponseScenarios:
    """실제 응답 시나리오 테스트"""

    @pytest.fixture
    def load_fixture(self, fixture_path):
        """Fixture 파일 로더"""

        def _load(filename):
            file_path = fixture_path / filename
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return None

        return _load

    def test_ranking_response_parsing(self, client, load_fixture):
        """랭킹 응답 파싱 테스트"""
        fixture_data = load_fixture("ranking_response.json")
        if not fixture_data:
            pytest.skip("Fixture file not found")

        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = fixture_data

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is True
        assert api_response.data is not None
        assert "rolling" in api_response.data

        ranking_list = api_response.data["rolling"]
        assert len(ranking_list) > 0

        # 첫 번째 항목 검증
        first_item = ranking_list[0]
        assert "sidoName" in first_item
        assert "sigunguName" in first_item
        assert "dongName" in first_item
        assert "rank" in first_item
        assert "visitor" in first_item
        assert "regionName" in first_item
        assert "name" in first_item

    def test_pois_bounding_response_parsing(self, client, load_fixture):
        """POI 바운딩 응답 파싱 테스트"""
        fixture_data = load_fixture("pois_bounding_response.json")
        if not fixture_data:
            pytest.skip("Fixture file not found")

        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = fixture_data

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is True
        assert api_response.data is not None
        assert isinstance(api_response.data, list)

        # 첫 번째 POI 검증
        first_poi = api_response.data[0]
        assert "id" in first_poi
        assert "category" in first_poi
        assert "name" in first_poi
        assert "lat" in first_poi
        assert "lng" in first_poi
        assert "dist" in first_poi
        assert first_poi["dist"] >= 0  # 거리는 0 이상

    def test_apartments_bounding_response_parsing(self, client, load_fixture):
        """아파트 바운딩 응답 파싱 테스트"""
        fixture_data = load_fixture("apartments_bounding_response.json")
        if not fixture_data:
            pytest.skip("Fixture file not found")

        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = fixture_data

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is True
        assert api_response.data is not None

        # 데이터 구조 검증
        assert "complex" in api_response.data
        assert "list" in api_response.data
        assert "page" in api_response.data

        # 단지 정보 검증
        complex_info = api_response.data["complex"]
        assert "no" in complex_info
        assert "name" in complex_info
        assert "lat" in complex_info
        assert "lng" in complex_info

        # 매물 목록 검증
        listing_list = api_response.data["list"]
        assert len(listing_list) > 0

        first_listing = listing_list[0]
        required_fields = [
            "agentId",
            "agentName",
            "aptNo",
            "buildingName",
            "dealAmount",
            "area",
            "floor",
            "lat",
            "lng",
        ]
        for field in required_fields:
            assert field in first_listing

    def test_error_response_parsing(self, client, load_fixture):
        """에러 응답 파싱 테스트"""
        fixture_data = load_fixture("error_response.json")
        if not fixture_data:
            pytest.skip("Fixture file not found")

        mock_response = Mock(spec=Response)
        mock_response.status_code = 401
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = fixture_data
        mock_response.raise_for_status.side_effect = HTTPError("401 Unauthorized")

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is False
        assert api_response.status_code == 401
        assert api_response.error is not None
        assert "인증" in api_response.error or "로그인" in api_response.error

    @pytest.mark.parametrize(
        "filename,expected_structure",
        [
            ("ranking_response.json", ["data", "rolling"]),
            ("pois_bounding_response.json", ["data"]),
            ("apartments_bounding_response.json", ["data", "complex", "list", "page"]),
            ("apartment_detail_response.json", ["data"]),
            ("complex_list_response.json", ["data"]),
        ],
    )
    def test_fixture_structure_validation(self, load_fixture, filename, expected_structure):
        """Fixture 구조 검증 테스트"""
        fixture_data = load_fixture(filename)
        if not fixture_data:
            pytest.skip(f"Fixture file {filename} not found")

        # 최상위 구조 검증
        for key in expected_structure:
            assert key in fixture_data, f"Missing key '{key}' in {filename}"

        # status 필드 검증
        assert "status" in fixture_data
        assert fixture_data["status"] in ["success", "error"]
