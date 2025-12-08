"""호갱노노 API 클라이언트 파라미터화된 테스트

다양한 파라미터 조합을 테스트하기 위한 파라미터화된 테스트
"""

import pytest
from unittest.mock import Mock, patch

from crawler.api.hogangnono_client import HogangnonoAPIClient, SearchParams, APIResponse
from crawler.config import CrawlerConfig


@pytest.fixture
def config():
    """테스트용 설정"""
    return CrawlerConfig(
        user_agent="Mozilla/5.0 (Param Test)",
        timeout=10.0,
    )


class TestSearchParamsParametrized:
    """SearchParams 파라미터화된 테스트"""

    @pytest.mark.parametrize(
        "bbox,expected_coords",
        [
            # (lat_min, lng_min, lat_max, lng_max), (start_lat, start_lng, end_lat, end_lng)
            ((37.5, 126.9, 37.6, 127.0), (37.5, 126.9, 37.6, 127.0)),  # 서울 강남구
            ((37.4, 127.0, 37.5, 127.1), (37.4, 127.0, 37.5, 127.1)),  # 서울 서초구
            ((37.6, 127.1, 37.7, 127.2), (37.6, 127.1, 37.7, 127.2)),  # 서울 송파구
            ((35.8, 128.5, 36.0, 129.0), (35.8, 128.5, 36.0, 129.0)),  # 대구
        ],
    )
    def test_bbox_coordinates_conversion(self, bbox, expected_coords):
        """bbox 좌표 변환 파라미터화 테스트"""
        params = SearchParams(bbox=bbox)

        assert params.startX == str(bbox[1])  # lng_min
        assert params.startY == str(bbox[0])  # lat_min
        assert params.endX == str(bbox[3])  # lng_max
        assert params.endY == str(bbox[2])  # lat_max

    @pytest.mark.parametrize(
        "zoom_level,expected_zoom",
        [
            (10, 10),
            (11, 11),
            (12, 12),
            (13, 13),
            (14, 14),
            (15, 15),
            (16, 16),
            (17, 17),
            (18, 18),
            (None, 17),  # 기본값 17
        ],
    )
    def test_zoom_levels(self, zoom_level, expected_zoom):
        """줌 레벨 파라미터화 테스트"""
        params = SearchParams(zoom=zoom_level)
        result = params.to_dict()
        assert result["level"] == expected_zoom

    @pytest.mark.parametrize(
        "trade_type,expected_value",
        [
            ("매매", 0),
            ("전세", 1),
            ("월세", 2),
            ("sale", 0),
            ("lease", 1),
            ("monthly", 2),
        ],
    )
    def test_trade_types(self, trade_type, expected_value):
        """거래 유형 파라미터화 테스트"""
        params = SearchParams(tradeType=expected_value)
        result = params.to_dict()
        assert result["tradeType"] == expected_value

    @pytest.mark.parametrize(
        "area_value,area_key",
        [
            (50.0, "areaFrom"),
            (100.0, "areaTo"),
            (None, None),
        ],
    )
    def test_area_parameters(self, area_value, area_key):
        """면적 파라미터 테스트"""
        params = SearchParams(areaFrom=50.0, areaTo=100.0)
        result = params.to_dict()

        assert result["areaFrom"] == 50.0
        assert result["areaTo"] == 100.0

        # None 값이 제외되는지 테스트
        if area_value is None:
            params_none = SearchParams(areaFrom=None, areaTo=None)
            result_none = params_none.to_dict()
            assert "areaFrom" not in result_none
            assert "areaTo" not in result_none

    @pytest.mark.parametrize(
        "price_value,price_key",
        [
            (50000, "priceFrom"),
            (200000, "priceTo"),
            (None, None),
        ],
    )
    def test_price_parameters(self, price_value, price_key):
        """가격 파라미터 테스트"""
        params = SearchParams(priceFrom=50000, priceTo=200000)
        result = params.to_dict()

        assert result["priceFrom"] == 50000
        assert result["priceTo"] == 200000

        # None 값이 제외되는지 테스트
        if price_value is None:
            params_none = SearchParams(priceFrom=None, priceTo=None)
            result_none = params_none.to_dict()
            assert "priceFrom" not in result_none
            assert "priceTo" not in result_none

    @pytest.mark.parametrize(
        "apt_type,expected_value",
        [
            (-1, -1),  # 전체
            (1, 1),  # 아파트
            (2, 2),  # 주택
            (3, 3),  # 오피스텔
            (None, -1),  # 기본값
        ],
    )
    def test_apartment_types(self, apt_type, expected_value):
        """아파트 유형 파라미터화 테스트"""
        params = SearchParams(aptType=apt_type)
        result = params.to_dict()
        assert result["aptType"] == expected_value

    @pytest.mark.parametrize(
        "map_type,expected_value",
        [
            ("google", "google"),
            ("naver", "naver"),
            ("kakao", "kakao"),
            (None, "google"),  # 기본값
        ],
    )
    def test_map_types(self, map_type, expected_value):
        """지도 유형 파라미터화 테스트"""
        params = SearchParams(map=map_type)
        result = params.to_dict()
        assert result["map"] == expected_value

    @pytest.mark.parametrize(
        "limit_value,expected_in_result",
        [
            (10, True),
            (20, True),
            (50, True),
            (100, True),
            (None, False),  # None 값은 포함되지 않음
        ],
    )
    def test_limit_parameter(self, limit_value, expected_in_result):
        """제한 수량 파라미터 테스트"""
        params = SearchParams(limit=limit_value)
        result = params.to_dict()

        if expected_in_result:
            assert "limit" in result
            assert result["limit"] == limit_value
        else:
            assert "limit" not in result

    @pytest.mark.parametrize(
        "screen_width,screen_height",
        [
            (1920, 1080),
            (1366, 768),
            (1200, 924),  # 호갱노노 기본값
            (800, 600),
        ],
    )
    def test_screen_parameters(self, screen_width, screen_height):
        """화면 크기 파라미터 테스트"""
        params = SearchParams()
        result = params.to_dict()

        # 항상 포함되는 screen 파라미터
        assert "screenWidth" in result
        assert "screenHeight" in result
        assert result["screenWidth"] == 1200  # 호갱노노 고정값
        assert result["screenHeight"] == 924  # 호갱노노 고정값

    @pytest.mark.parametrize(
        "bbox,individual_coords,use_bbox",
        [
            # bbox만 제공
            ((37.5, 126.9, 37.6, 127.0), None, True),
            # 개별 좌표만 제공
            (None, {"startX": 126.8, "startY": 37.4, "endX": 127.1, "endY": 37.7}, False),
            # 둘 다 제공할 경우 bbox 우선
            (
                (37.5, 126.9, 37.6, 127.0),
                {"startX": 126.8, "startY": 37.4, "endX": 127.1, "endY": 37.7},
                True,
            ),
        ],
    )
    def test_coordinate_priority(self, bbox, individual_coords, use_bbox):
        """좌표 우선순위 테스트"""
        if bbox and individual_coords:
            # 둘 다 제공하는 경우
            params = SearchParams(
                bbox=bbox,
                startX=individual_coords["startX"],
                startY=individual_coords["startY"],
                endX=individual_coords["endX"],
                endY=individual_coords["endY"],
            )
        elif bbox:
            params = SearchParams(bbox=bbox)
        else:
            params = SearchParams(
                startX=individual_coords["startX"],
                startY=individual_coords["startY"],
                endX=individual_coords["endX"],
                endY=individual_coords["endY"],
            )

        result = params.to_dict()

        if use_bbox:
            # bbox 값이 사용되어야 함
            assert result["lat_min"] == bbox[0]
            assert result["lng_min"] == bbox[1]
            assert result["lat_max"] == bbox[2]
            assert result["lng_max"] == bbox[3]
        else:
            # 개별 좌표 값이 사용되어야 함
            assert result["lat_min"] == individual_coords["startY"]
            assert result["lng_min"] == individual_coords["startX"]
            assert result["lat_max"] == individual_coords["endY"]
            assert result["lng_max"] == individual_coords["endX"]


class TestAPIResponseParametrized:
    """APIResponse 파라미터화된 테스트"""

    @pytest.mark.parametrize(
        "status_code,expected_success",
        [
            (200, True),
            (201, True),
            (204, True),
            (301, True),
            (302, True),
            (400, False),
            (401, False),
            (403, False),
            (404, False),
            (429, False),
            (500, False),
            (502, False),
            (503, False),
        ],
    )
    def test_status_code_handling(self, status_code, expected_success):
        """HTTP 상태 코드 처리 파라미터화 테스트"""
        mock_response = Mock()
        mock_response.status_code = status_code

        if status_code >= 400:
            mock_response.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
        else:
            mock_response.json.return_value = {"success": True, "data": {}}
            mock_response.headers = {"content-type": "application/json"}

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success == expected_success
        assert api_response.status_code == status_code

    @pytest.mark.parametrize(
        "content_type,should_parse_json",
        [
            ("application/json", True),
            ("application/json; charset=utf-8", True),
            ("text/json", True),
            ("application/xml", False),
            ("text/html", False),
            ("text/html; charset=utf-8", False),
            ("text/plain", False),
            (None, False),
        ],
    )
    def test_content_type_handling(self, content_type, should_parse_json):
        """Content-Type 처리 파라미터화 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": content_type} if content_type else {}
        mock_response.json.return_value = {"success": True, "data": {}}

        api_response = APIResponse.from_response(mock_response)

        if should_parse_json:
            assert api_response.data == {"success": True, "data": {}}
        else:
            # JSON이 아닌 경우 raw_content 반환
            assert "raw_content" in api_response.data

    @pytest.mark.parametrize(
        "error_code,error_message,contains_keywords",
        [
            (400, "Bad Request", ["400", "Bad Request"]),
            (401, "Unauthorized", ["401", "Unauthorized"]),
            (403, "Forbidden", ["403", "Forbidden"]),
            (404, "Not Found", ["404", "Not Found"]),
            (429, "Too Many Requests", ["429", "Too Many"]),
            (500, "Internal Server Error", ["500", "Internal"]),
            (502, "Bad Gateway", ["502", "Gateway"]),
            (503, "Service Unavailable", ["503", "Service"]),
        ],
    )
    def test_error_responses(self, error_code, error_message, contains_keywords):
        """에러 응답 파라미터화 테스트"""
        mock_response = Mock()
        mock_response.status_code = error_code
        mock_response.raise_for_status.side_effect = Exception(error_message)

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is False
        assert api_response.status_code == error_code
        assert api_response.error is not None

        # 예상 키워드 모두 포함되어야 함
        for keyword in contains_keywords:
            assert keyword in api_response.error

    @pytest.mark.parametrize(
        "json_data,expected_success,expected_data",
        [
            # 성공 응답
            ({"success": True, "data": {"items": []}}, True, {"items": []}),
            ({"success": False, "data": None}, False, None),
            ({"data": {"result": "ok"}}, True, {"result": "ok"}),  # success 필드 없음
            ({"items": [1, 2, 3]}, True, {"items": [1, 2, 3]}),  # success 필드 없음
            # 에러 응답
            ({"status": "error", "message": "Failed"}, False, None),
            ({"error": "Invalid parameter"}, False, None),
        ],
    )
    def test_json_response_structure(self, json_data, expected_success, expected_data):
        """JSON 응답 구조 파라미터화 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = json_data

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success == expected_success
        assert api_response.data == expected_data


class TestHogangnonoAPIClientParametrized:
    """HogangnonoAPIClient 파라미터화된 테스트"""

    @pytest.mark.parametrize(
        "method,expected_method",
        [
            ("GET", "GET"),
            ("POST", "POST"),
            ("PUT", "PUT"),
            ("DELETE", "DELETE"),
        ],
    )
    def test_http_methods(self, method, expected_method, config):
        """HTTP 메서드 파라미터화 테스트"""
        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.json.return_value = {"success": True, "data": {}}
            mock_session.request.return_value = mock_response

            mock_session.get.return_value = Mock(
                status_code=200, text="<html><body>Test</body></html>"
            )

            client = HogangnonoAPIClient(config)

            response = client._make_request(method, "/api/test")

            assert response.success is True

            # 요청 메서드 확인
            call_args = mock_session.request.call_args
            assert call_args[0][0] == expected_method

    @pytest.mark.parametrize(
        "endpoint,full_url",
        [
            ("/api/test", "https://hogangnono.com/api/test"),
            ("/v2/users", "https://hogangnono.com/v2/users"),
            ("/search?q=apt", "https://hogangnono.com/search?q=apt"),
            ("/", "https://hogangnono.com/"),
        ],
    )
    def test_url_building(self, endpoint, full_url, config):
        """URL 빌딩 파라미터화 테스트"""
        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.json.return_value = {"success": True, "data": {}}
            mock_session.request.return_value = mock_response

            mock_session.get.return_value = Mock(
                status_code=200, text="<html><body>Test</body></html>"
            )

            client = HogangnonoAPIClient(config)

            response = client._make_request("GET", endpoint)

            assert response.success is True

            # 요청 URL 확인
            call_args = mock_session.request.call_args
            assert call_args[1]["url"] == full_url

    @pytest.mark.parametrize(
        "timeout_value,expected_timeout",
        [
            (5.0, 5.0),
            (10.0, 10.0),
            (30.0, 30.0),
            (None, None),  # None은 기본값 사용
        ],
    )
    def test_timeout_parameter(self, timeout_value, expected_timeout, config):
        """타임아웃 파라미터 테스트"""
        if timeout_value is not None:
            config.timeout = timeout_value

        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.json.return_value = {"success": True, "data": {}}
            mock_session.request.return_value = mock_response

            mock_session.get.return_value = Mock(
                status_code=200, text="<html><body>Test</body></html>"
            )

            client = HogangnonoAPIClient(config)

            response = client._make_request("GET", "/api/test")

            assert response.success is True

            # 타임아웃 값 확인
            call_args = mock_session.request.call_args
            assert call_args[1]["timeout"] == expected_timeout

    @pytest.mark.parametrize(
        "headers_dict,should_contain",
        [
            ({"X-Custom": "value"}, ["X-Custom"]),
            ({"Authorization": "Bearer token"}, ["Authorization"]),
            ({"Content-Type": "application/json"}, ["Content-Type"]),
            ({}, []),  # 비어있는 딕셔너리
        ],
    )
    def test_custom_headers(self, headers_dict, should_contain, config):
        """커스텀 헤더 파라미터화 테스트"""
        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.json.return_value = {"success": True, "data": {}}
            mock_session.request.return_value = mock_response

            mock_session.get.return_value = Mock(
                status_code=200, text="<html><body>Test</body></html>"
            )

            client = HogangnonoAPIClient(config)

            response = client._make_request("GET", "/api/test", headers=headers_dict)

            assert response.success is True

            # 헤더 확인
            call_args = mock_session.request.call_args
            final_headers = call_args[1]["headers"]

            for header in should_contain:
                assert header in final_headers
                assert final_headers[header] == headers_dict[header]

            # 항상 포함되어야 하는 기본 헤더 확인
            assert "X-Requested-With" in final_headers


class TestRealWorldScenarios:
    """실제 시나리오 기반 파라미터화 테스트"""

    @pytest.mark.parametrize(
        "district,bbox",
        [
            # 서울 지역
            ("강남구", (37.5132, 127.0286, 37.5232, 127.0386)),
            ("서초구", (37.4763, 127.0294, 37.4863, 127.0394)),
            ("송파구", (37.5149, 127.1036, 37.5249, 127.1136)),
            ("마포구", (37.5662, 126.8867, 37.5762, 126.8967)),
            # 기타 지역
            ("분당구", (37.3580, 127.1056, 37.3680, 127.1156)),
            ("부산 해운대구", (35.1602, 129.1608, 35.1702, 129.1708)),
        ],
    )
    def test_district_search_parameters(self, district, bbox, config):
        """구별 검색 파라미터 테스트"""
        search_params = SearchParams(
            bbox=bbox,
            zoom=15,
            limit=20,
        )

        params_dict = search_params.to_dict()

        # bbox가 올바르게 변환되었는지 확인
        assert params_dict["lat_min"] == bbox[0]
        assert params_dict["lng_min"] == bbox[1]
        assert params_dict["lat_max"] == bbox[2]
        assert params_dict["lng_max"] == bbox[3]

        # 필수 파라미터 확인
        assert params_dict["level"] == 15
        assert params_dict["limit"] == 20
        assert params_dict["screenWidth"] == 1200
        assert params_dict["screenHeight"] == 924

    @pytest.mark.parametrize(
        "trade_type,price_range,area_range,expected_keys",
        [
            # 매매 - 고가
            ("매매", (50000, 200000), (84, 120), ["priceFrom", "priceTo", "areaFrom", "areaTo"]),
            # 전세 - 중가
            ("전세", (100000, 300000), (60, 85), ["priceFrom", "priceTo", "areaFrom", "areaTo"]),
            # 월세 - 전체
            ("월세", None, None, ["tradeType"]),
            # 매매 - 가격 없음
            ("매매", None, (80, 100), ["areaFrom", "areaTo"]),
        ],
    )
    def test_search_filter_combinations(
        self, trade_type, price_range, area_range, expected_keys, config
    ):
        """검색 필터 조합 테스트"""
        params_dict = {}

        # 거래 유형 설정
        if trade_type == "매매":
            params_dict["tradeType"] = 0
        elif trade_type == "전세":
            params_dict["tradeType"] = 1
        elif trade_type == "월세":
            params_dict["tradeType"] = 2

        # 가격 범위 설정
        if price_range:
            params_dict["priceFrom"] = price_range[0]
            params_dict["priceTo"] = price_range[1]

        # 면적 범위 설정
        if area_range:
            params_dict["areaFrom"] = area_range[0]
            params_dict["areaTo"] = area_range[1]

        search_params = SearchParams(**params_dict)
        result = search_params.to_dict()

        # 예상 키가 모두 포함되는지 확인
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

        # 거래 유형이 올바르게 설정되었는지 확인
        if "tradeType" in params_dict:
            assert result["tradeType"] == params_dict["tradeType"]

    @pytest.mark.parametrize(
        "apt_config",
        [
            # 아파트 매매
            {"apt_type": "apart", "trade_type": "sale", "price_range": (50000, 200000)},
            # 주택 전세
            {"apt_type": "house", "trade_type": "lease", "price_range": (30000, 100000)},
            # 오피스텔 월세
            {"apt_type": "officetel", "trade_type": "monthly", "price_range": None},
            # 전체 (기본값)
            {"apt_type": None, "trade_type": None, "price_range": None},
        ],
    )
    def test_apartment_search_configurations(self, apt_config, config):
        """아파트 검색 설정 조합 테스트"""
        # SearchParams 생성
        search_params = SearchParams(
            aptType=apt_config["apt_type"],
            tradeType=0
            if apt_config["trade_type"] == "sale"
            else 1
            if apt_config["trade_type"] == "lease"
            else 2,
        )

        # 가격 범위 추가
        if apt_config["price_range"]:
            search_params.priceFrom = apt_config["price_range"][0]
            search_params.priceTo = apt_config["price_range"][1]

        result = search_params.to_dict()

        # apt_type 설정 확인
        if apt_config["apt_type"] is not None:
            assert result["aptType"] == apt_config["apt_type"]

        # trade_type 설정 확인
        if apt_config["trade_type"] is not None:
            expected_trade = (
                0
                if apt_config["trade_type"] == "sale"
                else 1
                if apt_config["trade_type"] == "lease"
                else 2
            )
            assert result["tradeType"] == expected_trade

        # 가격 범위 확인
        if apt_config["price_range"]:
            assert result["priceFrom"] == apt_config["price_range"][0]
            assert result["priceTo"] == apt_config["price_range"][1]

    @pytest.mark.parametrize(
        "api_endpoint,param_dict",
        [
            # 랭킹 API
            ("/api/v2/ranks/rolling", {"rank_type": "daily", "limit": 10}),
            # 최근 조회 API
            ("/api/v2/apts/recent-visits", {"apt_type": "apart", "limit": 20}),
            # 지역 정보 API
            ("/api/v2/maps/region", {"lat": 37.5, "lng": 126.9, "zoom": 14}),
            # POI 바운딩 API
            (
                "/api/v2/pois-bounding",
                {"level": 17, "startX": 126.9, "startY": 37.5, "endX": 127.0, "endY": 37.6},
            ),
            # 아파트 바운딩 API
            ("/api/apt/bounding", {"apt_type": "apart", "trade_type": "sale"}),
        ],
    )
    def test_api_endpoint_parameter_combinations(self, api_endpoint, param_dict, config):
        """API 엔드포인트별 파라미터 조합 테스트"""
        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.json.return_value = {"success": True, "data": {}}
            mock_session.request.return_value = mock_response

            mock_session.get.return_value = Mock(
                status_code=200, text="<html><body>Test</body></html>"
            )

            client = HogangnonoAPIClient(config)

            # API 호출
            response = client._make_request("GET", api_endpoint, params=param_dict)

            assert response.success is True

            # 요청 파라미터 확인
            call_args = mock_session.request.call_args
            request_params = call_args[1]["params"]

            # 모든 파라미터가 전달되었는지 확인
            for key, value in param_dict.items():
                assert key in request_params
                assert request_params[key] == value
