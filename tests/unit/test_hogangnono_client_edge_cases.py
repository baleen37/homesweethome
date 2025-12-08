"""호갱노노 API 클라이언트 엣지 케이스 테스트"""

import pytest
import requests
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


class TestSearchParamsEdgeCases:
    """SearchParams 엣지 케이스 테스트"""

    def test_level_boundary_values(self):
        """level 경계값 테스트"""
        # 최소값
        params_min = SearchParams(level=SearchParams.MIN_LEVEL)
        assert params_min.level == SearchParams.MIN_LEVEL

        # 최대값
        params_max = SearchParams(level=SearchParams.MAX_LEVEL)
        assert params_max.level == SearchParams.MAX_LEVEL

        # 경계값 바깓 (예외 발생)
        with pytest.raises(ValueError):
            SearchParams(level=SearchParams.MIN_LEVEL - 1)

        with pytest.raises(ValueError):
            SearchParams(level=SearchParams.MAX_LEVEL + 1)

    def test_coordinate_edge_cases(self):
        """좌표 엣지 케이스 테스트"""
        # 극소값
        params = SearchParams(
            bbox=(-180.0, -90.0, 180.0, 90.0)  # 전 지구 범위
        )
        result = params.to_dict()
        assert result["startX"] == -180.0
        assert result["startY"] == -90.0
        assert result["endX"] == 180.0
        assert result["endY"] == 90.0

        # 한국 좌표 범위 (대략)
        params_korea = SearchParams(bbox=(124.0, 33.0, 132.0, 43.0))
        result_korea = params_korea.to_dict()
        assert 124.0 <= result_korea["startX"] <= 132.0
        assert 33.0 <= result_korea["startY"] <= 43.0

        # 좌표가 같은 경우 (점)
        params_point = SearchParams(bbox=(127.0, 37.5, 127.0, 37.5))
        result_point = params_point.to_dict()
        assert result_point["startX"] == result_point["endX"]
        assert result_point["startY"] == result_point["endY"]

    def test_price_edge_cases(self):
        """가격 엣지 케이스 테스트"""
        # 0원
        params_zero = SearchParams(priceFrom=0, priceTo=0)
        result = params_zero.to_dict()
        assert result["priceFrom"] == 0
        assert result["priceTo"] == 0

        # 매우 높은 가격
        params_high = SearchParams(
            priceFrom=1000000,  # 1000억
            priceTo=10000000,  # 1조
        )
        result_high = params_high.to_dict()
        assert result_high["priceFrom"] == 1000000
        assert result_high["priceTo"] == 10000000

        # 최소 가격이 최대 가격보다 큰 경우 (경고하지만 허용)
        params_invalid_range = SearchParams(priceFrom=100000, priceTo=50000)
        result_invalid = params_invalid_range.to_dict()
        assert result_invalid["priceFrom"] == 100000
        assert result_invalid["priceTo"] == 50000

    def test_area_edge_cases(self):
        """면적 엣지 케이스 테스트"""
        # 0㎡
        params_zero_area = SearchParams(areaFrom=0, areaTo=0)
        result = params_zero_area.to_dict()
        assert result["areaFrom"] == 0
        assert result["areaTo"] == 0

        # 소수점 면적
        params_decimal = SearchParams(areaFrom=16.55, areaTo=33.77)
        result = params_decimal.to_dict()
        assert result["areaFrom"] == 16.55
        assert result["areaTo"] == 33.77

    def test_missing_parameters(self):
        """파라미터 누락 케이스"""
        # 모든 파라미터가 None
        params_empty = SearchParams(
            startX=None,
            endX=None,
            startY=None,
            endY=None,
            level=None,
            tradeType=None,
            aptType=None,
        )
        result = params_empty.to_dict()

        # 필수 파라미터가 없으면 빈 딕셔너리에 추가되지 않음
        assert "startX" not in result
        assert "startY" not in result
        assert "endX" not in result
        assert "endY" not in result

        # 선택적 파라미터도 없으면 추가되지 않음
        assert "level" not in result
        assert "tradeType" not in result
        assert "aptType" not in result

        # 항상 포함되는 파라미터
        assert "map" in result
        assert "screenWidth" in result
        assert "screenHeight" in result
        assert "apt" in result

    def test_parameter_combinations(self):
        """다양한 파라미터 조합 테스트"""
        # bbox만 있는 경우
        params_bbox = SearchParams(bbox=(127.0, 37.0, 128.0, 38.0))
        result = params_bbox.to_dict()
        assert "startX" in result and "startY" in result
        assert "endX" in result and "endY" in result

        # 개별 좌표만 있는 경우
        params_coords = SearchParams(startX=127.0, startY=37.0, endX=128.0, endY=38.0)
        result = params_coords.to_dict()
        assert "startX" in result and "startY" in result
        assert "endX" in result and "endY" in result

        # bbox와 개별 좌표가 모두 있는 경우 (bbox 우선)
        params_both = SearchParams(
            startX=100.0,  # 무시됨
            startY=100.0,  # 무시됨
            endX=200.0,  # 무시됨
            endY=200.0,  # 무시됨
            bbox=(127.0, 37.0, 128.0, 38.0),
        )
        result = params_both.to_dict()
        assert result["startX"] == 127.0
        assert result["startY"] == 37.0


class TestAPIResponseEdgeCases:
    """APIResponse 엣지 케이스 테스트"""

    def test_empty_response(self):
        """빈 응답 처리"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {}

        api_response = APIResponse.from_response(mock_response)
        assert api_response.success is True
        assert api_response.data == {}
        assert api_response.error is None

    def test_null_response(self):
        """null 응답 처리"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = None

        api_response = APIResponse.from_response(mock_response)
        assert api_response.success is True
        assert api_response.data is None

    def test_nested_data_response(self):
        """중첩 데이터 응답 처리"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "items": [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}],
                "pagination": {"page": 1, "total": 100},
            },
        }

        api_response = APIResponse.from_response(mock_response)
        assert api_response.success is True
        assert api_response.data["items"][0]["id"] == 1
        assert api_response.data["pagination"]["total"] == 100

    def test_unicode_response(self):
        """유니코드 응답 처리"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "message": "안녕하세요",
            "data": ["아파트", "오피스텔", "주상복합"],
        }

        api_response = APIResponse.from_response(mock_response)
        assert api_response.success is True
        assert "아파트" in api_response.data["data"]
        assert api_response.data["message"] == "안녕하세요"

    def test_large_response(self):
        """대용량 응답 처리"""
        # 대용량 데이터 생성
        large_data = []
        for i in range(1000):
            large_data.append(
                {
                    "id": i,
                    "name": f"아파트{i}",
                    "address": f"서울시 강남구 테헤란로 {i}길",
                    "description": "가" * 100,  # 긴 설명
                }
            )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": large_data}

        api_response = APIResponse.from_response(mock_response)
        assert api_response.success is True
        assert len(api_response.data["data"]) == 1000

    def test_special_status_codes(self):
        """특수 상태 코드 처리"""
        # 204 No Content
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.headers = {"content-type": "application/json"}

        api_response = APIResponse.from_response(mock_response)
        assert api_response.success is True
        assert api_response.status_code == 204

        # 301 Moved Permanently
        mock_response.status_code = 301
        mock_response.headers = {"location": "https://new-url.com"}

        api_response = APIResponse.from_response(mock_response)
        assert api_response.success is False
        assert "301" in api_response.error

    def test_malformed_json_response(self):
        """잘못된 JSON 응답 처리"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.side_effect = ValueError("No JSON object could be decoded")
        mock_response.text = '{"invalid": json'  # 잘못된 JSON

        api_response = APIResponse.from_response(mock_response)
        # 200 상태 코드이므로 성공으로 간주 (HTML로 처리)
        assert api_response.success is True
        assert api_response.data is not None
        assert "raw_content" in api_response.data


class TestHogangnonoAPIClientEdgeCases:
    """HogangnonoAPIClient 엣지 케이스 테스트"""

    @patch("crawler.api.hogangnono_client.Session")
    def test_session_initialization_failure(self, mock_session_class, config):
        """세션 초기화 실패 처리"""
        mock_session = Mock()
        mock_session.get.side_effect = Exception("Network error")
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        # API 호출 시 세션 초기화 실패
        response = client.get_apartments_bounding(SearchParams())
        assert response.success is False
        assert "Failed to initialize session" in response.error

    @patch("crawler.api.hogangnono_client.Session")
    def test_request_timeout(self, mock_session_class, config):
        """요청 타임아웃 처리"""
        mock_session = Mock()
        mock_session.get.return_value = Mock(status_code=200)
        mock_session.cookies = []
        mock_session.request.side_effect = requests.exceptions.Timeout("Request timeout")
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        response = client.get_apartments_bounding(SearchParams())
        assert response.success is False
        assert "Request error" in response.error or "timeout" in response.error.lower()

    @patch("crawler.api.hogangnono_client.Session")
    def test_connection_error(self, mock_session_class, config):
        """연결 에러 처리"""
        mock_session = Mock()
        mock_session.get.return_value = Mock(status_code=200)
        mock_session.cookies = []
        mock_session.request.side_effect = requests.exceptions.ConnectionError("Connection failed")
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        response = client.get_apartments_bounding(SearchParams())
        assert response.success is False
        assert "Request error" in response.error

    @patch("crawler.api.hogangnono_client.Session")
    def test_multiple_concurrent_requests(self, mock_session_class, config):
        """동시 다중 요청 처리"""
        mock_session = Mock()
        mock_session.get.return_value = Mock(status_code=200)
        mock_session.cookies = []

        # 성공 응답 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": []}
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        # 여러 요청을 순차적으로 실행
        responses = []
        for i in range(5):
            params = SearchParams(level=i + 1)
            response = client.get_apartments_bounding(params)
            responses.append(response)

        # 모든 요청이 성공
        assert all(r.success for r in responses)
        assert len(responses) == 5

    @patch("crawler.api.hogangnono_client.Session")
    def test_context_manager_cleanup(self, mock_session_class, config):
        """컨텍스트 매니저 자원 정리"""
        mock_session = Mock()
        mock_session.get.return_value = Mock(status_code=200)
        mock_session_class.return_value = mock_session

        # 컨텍스트 매니저 사용
        with HogangnonoAPIClient(config) as client:
            assert client is not None
            client.get_apartments_bounding(SearchParams())

        # 컨텍스트 종료 후 세션 클로즈 확인
        mock_session.close.assert_called_once()
