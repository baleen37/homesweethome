"""호갱노노 API pois-bounding 엔드포인트 TDD 테스트"""

import pytest
from unittest.mock import Mock, patch

from crawler.api.hogangnono_client import (
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


class TestSearchParamsValidation:
    """SearchParams 유효성 검사 테스트"""

    def test_valid_level_range(self):
        """유효한 level 범위 테스트"""
        for level in range(SearchParams.MIN_LEVEL, SearchParams.MAX_LEVEL + 1):
            params = SearchParams(level=level)
            assert params.level == level

    def test_invalid_level_range(self):
        """유효하지 않은 level 범위 테스트"""
        invalid_levels = [-1, 0, 19, 100]
        for level in invalid_levels:
            with pytest.raises(
                ValueError,
                match=f"level must be between {SearchParams.MIN_LEVEL} and {SearchParams.MAX_LEVEL}",
            ):
                SearchParams(level=level)

    def test_valid_trade_types(self):
        """유효한 tradeType 테스트"""
        for trade_type in SearchParams.VALID_TRADE_TYPES:
            params = SearchParams(tradeType=trade_type)
            assert params.tradeType == trade_type

    def test_invalid_trade_type(self):
        """유효하지 않은 tradeType 테스트"""
        with pytest.raises(ValueError, match="tradeType must be one of"):
            SearchParams(tradeType=99)

    def test_valid_apt_types(self):
        """유효한 aptType 테스트"""
        for apt_type in SearchParams.VALID_APT_TYPES:
            params = SearchParams(aptType=apt_type)
            assert params.aptType == apt_type

    def test_invalid_apt_type(self):
        """유효하지 않은 aptType 테스트"""
        with pytest.raises(ValueError, match="aptType must be one of"):
            SearchParams(aptType=99)

    def test_coordinate_validation(self):
        """좌표 유효성 검사 테스트"""
        # bbox와 개별 좌표를 함께 사용하면 bbox가 우선됨
        params = SearchParams(
            startX=100.0,
            startY=100.0,
            endX=200.0,
            endY=200.0,
            bbox=(127.0, 37.0, 128.0, 38.0),
        )

        result = params.to_dict()
        assert result["startX"] == 127.0
        assert result["startY"] == 37.0
        assert result["endX"] == 128.0
        assert result["endY"] == 38.0

    def test_new_parameters_in_to_dict(self):
        """새 파라미터(priceType, rentType)가 to_dict에 포함되는지 확인"""
        params = SearchParams(
            level=17,
            tradeType=0,
            aptType=-1,
            priceType=1,
            rentType=2,
        )

        result = params.to_dict()

        # 기존 파라미터 확인
        assert result["level"] == "17"
        assert result["tradeType"] == 0
        assert result["aptType"] == -1

        # 새 파라미터 확인
        assert result["priceType"] == 1
        assert result["rentType"] == 2


class TestPoisBoundingAPI:
    """pois-bounding API TDD 테스트"""

    @patch("crawler.api.hogangnono_client.Session")
    def test_level_parameter_conversion(self, mock_session_class, config):
        """level 파라미터가 정수에서 문자열로 올바르게 변환되는지 테스트"""
        # Mock 설정
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": []}
        mock_session.request.return_value = mock_response
        mock_session.get.return_value = Mock(status_code=200)
        mock_session.cookies = Mock()
        mock_session.cookies.__iter__ = Mock(return_value=iter([]))
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        # 정수 level로 SearchParams 생성
        search_params = SearchParams(
            level=17,  # 정수로 입력
            bbox=(127.045, 37.515, 127.055, 37.525),
        )

        # API 호출
        response = client.get_apartments_bounding(search_params)

        # 검증: 요청 파라미터 확인
        assert response.success is True
        mock_session.request.assert_called_once()

        # 호출된 파라미터 추출
        call_args = mock_session.request.call_args
        actual_params = call_args[1]["params"]

        # level이 문자열로 변환되었는지 확인
        assert isinstance(
            actual_params["level"], str
        ), f"level should be string, got {type(actual_params['level'])}"
        assert actual_params["level"] == "17", f"level should be '17', got {actual_params['level']}"

    @patch("crawler.api.hogangnono_client.Session")
    def test_bbox_coordinate_order(self, mock_session_class, config):
        """bbox 좌표 순서가 올바른지 확인 (lng_min, lat_min, lng_max, lat_max)"""
        # Mock 설정
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": []}
        mock_session.request.return_value = mock_response
        mock_session.get.return_value = Mock(status_code=200)
        mock_session.cookies = Mock()
        mock_session.cookies.__iter__ = Mock(return_value=iter([]))
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        # bbox로 SearchParams 생성
        search_params = SearchParams(
            bbox=(127.045, 37.515, 127.055, 37.525),  # (lng_min, lat_min, lng_max, lat_max)
        )

        # API 호출
        response = client.get_apartments_bounding(search_params)

        # 검증
        assert response.success is True
        call_args = mock_session.request.call_args
        actual_params = call_args[1]["params"]

        # 좌표 순서 확인
        assert (
            actual_params["startX"] == 127.045
        ), f"startX should be 127.045, got {actual_params['startX']}"
        assert (
            actual_params["startY"] == 37.515
        ), f"startY should be 37.515, got {actual_params['startY']}"
        assert (
            actual_params["endX"] == 127.055
        ), f"endX should be 127.055, got {actual_params['endX']}"
        assert (
            actual_params["endY"] == 37.525
        ), f"endY should be 37.525, got {actual_params['endY']}"

    @patch("crawler.api.hogangnono_client.Session")
    def test_missing_required_parameters(self, mock_session_class, config):
        """필수 파라미터가 누락되었을 때 에러 처리 확인"""
        # Mock 설정
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 400  # Bad Request
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"error": "Missing required parameters"}
        mock_session.request.return_value = mock_response
        mock_session.get.return_value = Mock(status_code=200)
        mock_session.cookies = Mock()
        mock_session.cookies.__iter__ = Mock(return_value=iter([]))
        mock_session_class.return_value = mock_session

        client = HogangnonoAPIClient(config)

        # 빈 SearchParams 생성
        search_params = SearchParams()

        # API 호출
        response = client.get_apartments_bounding(search_params)

        # 검증: 실패 응답 확인
        assert response.success is False
        assert response.status_code == 400
        assert (
            "Missing required parameters" in response.error
            or "error" in str(response.error).lower()
        )

    @patch("crawler.api.hogangnono_client.Session")
    def test_invalid_level_values(self, mock_session_class, config):
        """잘못된 level 값에 대한 처리 확인"""
        # Mock 설정
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"error": "Invalid level parameter"}
        mock_session.request.return_value = mock_response
        mock_session.get.return_value = Mock(status_code=200)
        mock_session.cookies = Mock()
        mock_session.cookies.__iter__ = Mock(return_value=iter([]))
        mock_session_class.return_value = mock_session

        HogangnonoAPIClient(config)

        # 유효하지 않은 level 값 테스트
        invalid_levels = [-1, 0, 19, 100]

        for invalid_level in invalid_levels:
            # SearchParams 생성 시 ValueError가 발생해야 함
            with pytest.raises(ValueError, match="level must be between"):
                SearchParams(
                    level=invalid_level,
                    bbox=(127.045, 37.515, 127.055, 37.525),
                )

    def test_search_params_to_dict_format(self):
        """SearchParams.to_dict()가 올바른 형식으로 변환하는지 테스트"""
        # bbox 없이 개별 좌표로 생성
        params = SearchParams(
            startX=127.045,
            startY=37.515,
            endX=127.055,
            endY=37.525,
            level=17,
            tradeType=0,
            aptType=-1,
        )

        result = params.to_dict()

        # 필수 파라미터 확인
        assert "startX" in result
        assert "startY" in result
        assert "endX" in result
        assert "endY" in result

        # level이 문자열로 변환되었는지 확인 (현재는 실패해야 함)
        # 이 assertion은 Red 단계에서 실패할 것임
        assert isinstance(
            result["level"], str
        ), f"level should be string, got {type(result['level'])}"

        # 다른 파라미터들은 원래 타입 유지
        assert isinstance(
            result["tradeType"], int
        ), f"tradeType should be int, got {type(result['tradeType'])}"
        assert isinstance(
            result["aptType"], int
        ), f"aptType should be int, got {type(result['aptType'])}"

    def test_bbox_conversion_priority(self):
        """bbox가 개별 좌표보다 우선순위가 높은지 확인"""
        # bbox와 개별 좌표를 모두 제공
        params = SearchParams(
            startX=100.0,  # 무시되어야 함
            startY=100.0,  # 무시되어야 함
            endX=200.0,  # 무시되어야 함
            endY=200.0,  # 무시되어야 함
            bbox=(127.045, 37.515, 127.055, 37.525),  # 우선 적용되어야 함
        )

        result = params.to_dict()

        # bbox 값이 적용되었는지 확인
        assert result["startX"] == 127.045
        assert result["startY"] == 37.515
        assert result["endX"] == 127.055
        assert result["endY"] == 37.525
