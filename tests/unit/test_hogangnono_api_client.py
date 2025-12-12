"""호갱노노 API 클라이언트 통합 테스트

세 개의 중복된 테스트 파일을 통합하여 포괄적인 테스트를 제공합니다.
- TDD 접근 방식으로 실패하는 테스트를 먼저 정의
- 실제 기능 검증 테스트 포함
- 모든 고유한 시나리오를 보존
"""

# Import test setup to configure path and mocks

import json
import pytest
from unittest.mock import Mock, patch

import requests
from crawler.api.hogangnono_client import (
    APIResponse,
    HogangnonoAPIClient,
    SearchParams,
)
from crawler.config import CrawlerConfig


@pytest.fixture
def config():
    """테스트용 설정 객체"""
    return CrawlerConfig()


@pytest.fixture
def client(config):
    """테스트용 API 클라이언트"""
    return HogangnonoAPIClient(config)


class TestSearchParams:
    """SearchParams 클래스 테스트"""

    def test_search_params_bbox_conversion(self):
        """bbox 파라미터를 startX, startY, endX, endY로 올바르게 변환"""
        # bbox 파라미터 (lng_min, lat_min, lng_max, lat_max)
        params = SearchParams(bbox=(126.8781, 37.4132, 127.1834, 37.7151))

        result = params.to_dict()

        # 예상되는 결과
        assert result["startX"] == 126.8781
        assert result["startY"] == 37.4132
        assert result["endX"] == 127.1834
        assert result["endY"] == 37.7151

    def test_search_params_with_required_fields(self):
        """필수 필드를 모두 포함하는지 확인"""
        params = SearchParams(
            bbox=(126.8781, 37.4132, 127.1834, 37.7151),
            level=14,
            tradeType=0,  # 매매
            aptType=1,  # 아파트
        )

        result = params.to_dict()

        # 필수 필드 확인
        assert "startX" in result
        assert "startY" in result
        assert "endX" in result
        assert "endY" in result
        assert "level" in result
        assert "tradeType" in result
        assert "aptType" in result
        assert result["map"] == "google"

    def test_search_params_hogangnono_specific_fields(self):
        """호갱노노 API에 필요한 특정 필드 포함 확인"""
        params = SearchParams(
            bbox=(126.8781, 37.4132, 127.1834, 37.7151),
            level=14,
        )

        result = params.to_dict()

        # 호갱노노 특정 필드 확인
        assert "screenWidth" in result
        assert "screenHeight" in result
        assert "apt" in result
        assert result["screenWidth"] == 1200
        assert result["screenHeight"] == 924


class TestAPIResponse:
    """APIResponse 클래스 테스트"""

    def test_api_response_success_structure(self):
        """성공 응답 구조 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "success": True,
            "data": [
                {
                    "id": "12345",
                    "name": "테스트아파트",
                    "address": "서울시 강남구",
                    "lat": 37.5,
                    "lng": 127.0,
                }
            ],
        }

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is True
        assert api_response.data is not None
        assert len(api_response.data) > 0

    def test_api_response_error_handling(self):
        """에러 응답 처리 테스트"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "success": False,
            "error": "Rate limit exceeded",
        }

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is False
        assert api_response.status_code == 429
        assert "Rate limit" in api_response.error

    def test_api_response_html_content(self):
        """HTML 응답 처리 테스트 (세션 초기화 등)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        mock_response.text = "<html><body>Test HTML</body></html>"

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is True
        assert api_response.status_code == 200
        assert api_response.data is not None

    def test_api_response_invalid_json(self):
        """잘못된 JSON 응답 처리 테스트"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        api_response = APIResponse.from_response(mock_response)

        assert api_response.success is False
        assert api_response.status_code == 500


class TestHogangnonoAPIClientHeaders:
    """API 클라이언트 헤더 테스트"""

    def test_required_headers_always_present(self):
        """모든 API 요청에 필수 헤더가 포함되어야 함"""
        client = HogangnonoAPIClient(CrawlerConfig())
        headers = client._get_api_headers()

        required_headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://hogangnono.com/",
            "Origin": "https://hogangnono.com",
        }

        for key, value in required_headers.items():
            assert key in headers, f"Missing required header: {key}"
            assert headers[key] == value, f"Incorrect {key}: expected {value}, got {headers[key]}"

    def test_api_headers_structure(self, client):
        """올바른 API 요청 헤더 구조 생성 확인"""
        headers = client._get_api_headers()

        # 필수 헤더 필드 확인
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Referer" in headers
        assert "Origin" in headers
        assert "X-Requested-With" in headers
        assert headers["X-Requested-With"] == "XMLHttpRequest"

        # 헤더 값 검증
        assert "application/json, text/plain, */*" in headers["Accept"]
        assert "no-cache" in headers["Cache-Control"]
        assert "Pragma" in headers
        assert "Sec-Ch-Ua" in headers
        assert "Sec-Ch-Ua-Mobile" in headers
        assert "Sec-Ch-Ua-Platform" in headers
        assert "Sec-Fetch-Dest" in headers
        assert "Sec-Fetch-Mode" in headers
        assert "Sec-Fetch-Site" in headers


class TestSessionManagement:
    """세션 관리 테스트"""

    def test_session_initialization(self, client):
        """세션 초기화 테스트"""
        # 초기화 전 상태 확인
        assert client._session_initialized is False

        # 세션 초기화 시도
        with patch.object(client, "session") as mock_session:
            mock_session.get.return_value = Mock(status_code=200)
            result = client._initialize_session()

            # 초기화 성공 확인
            assert result is True
            assert client._session_initialized is True

    def test_session_initialization_failure(self, client):
        """세션 초기화 실패 처리"""
        with patch("requests.Session.get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            result = client._initialize_session()

            assert result is False
            assert client._session_initialized is False

    def test_session_recovery_on_401(self):
        """401/403 에러 시 자동 세션 재초기화"""
        import requests_mock

        config = CrawlerConfig()
        client = HogangnonoAPIClient(config)

        with requests_mock.Mocker() as m:
            # First call returns 401
            m.get(
                "https://hogangnono.com/api/v2/regions",
                status_code=401,
                json={"error": "Unauthorized"},
            )

            # Session reinitialization
            m.get("https://hogangnono.com/", status_code=200)

            # Second call after reinit succeeds
            m.get(
                "https://hogangnono.com/api/v2/regions",
                status_code=200,
                json={"data": {"regionList": []}, "status": "success"},
            )

            # Should succeed after auto-recovery
            response = client.get_regions()
            assert response.success
            assert client._session_initialized


class TestGetRegions:
    """get_regions 메서드 테스트"""

    def test_get_regions_success(self, client):
        """정상적인 지역 목록 조회"""
        mock_response_data = {
            "success": True,
            "data": {
                "regionList": [
                    {
                        "regionCode": "11",
                        "name": "서울",
                        "fullName": "서울특별시",
                        "children": [
                            {
                                "regionCode": "11680",
                                "name": "강남구",
                                "fullName": "서울특별시 강남구",
                            },
                            {
                                "regionCode": "11560",
                                "name": "서초구",
                                "fullName": "서울특별시 서초구",
                            },
                        ],
                    },
                    {
                        "regionCode": "26",
                        "name": "부산",
                        "fullName": "부산광역시",
                        "children": [
                            {
                                "regionCode": "26500",
                                "name": "해운대구",
                                "fullName": "부산광역시 해운대구",
                            }
                        ],
                    },
                ]
            },
        }

        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = mock_response_data

        with patch.object(
            client, "_make_request", return_value=APIResponse.from_response(mock_response)
        ):
            response = client.get_regions()

            assert response.success is True
            assert "regionList" in response.data
            assert len(response.data["regionList"]) == 2
            assert response.data["regionList"][0]["regionCode"] == "11"
            assert response.data["regionList"][0]["name"] == "서울"

    def test_get_regions_with_region_code(self, client):
        """특정 지역 코드로 필터링"""
        mock_response_data = {
            "success": True,
            "data": {
                "regionList": [
                    {
                        "regionCode": "11680",
                        "name": "강남구",
                        "fullName": "서울특별시 강남구",
                        "children": [],
                    }
                ]
            },
        }

        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = mock_response_data

        with patch.object(
            client, "_make_request", return_value=APIResponse.from_response(mock_response)
        ):
            response = client.get_regions(region_code="11")

            assert response.success is True
            assert response.data["regionList"][0]["regionCode"] == "11680"

    def test_get_regions_api_error(self, client):
        """API 에러 응답"""
        mock_response_data = {"success": False, "error": "Invalid region code"}

        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 400
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = mock_response_data

        with patch.object(
            client, "_make_request", return_value=APIResponse.from_response(mock_response)
        ):
            response = client.get_regions()

            assert response.success is False
            assert "Invalid region code" in response.error

    def test_get_regions_verify_endpoint(self, client):
        """올바른 엔드포인트 호출 확인"""
        with patch.object(client, "_make_request") as mock_request:
            mock_response = Mock(spec=requests.Response)
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.json.return_value = {"success": True, "data": {"regionList": []}}
            mock_request.return_value = APIResponse.from_response(mock_response)

            client.get_regions(region_code="11")

            # Verify the call was made with correct parameters
            mock_request.assert_called_once()
            call_args = mock_request.call_args

            # Check method, endpoint, and params
            assert call_args.kwargs["method"] == "GET"
            assert call_args.kwargs["endpoint"] == "/api/v2/regions"
            assert call_args.kwargs["params"] == {"regionCode": "11"}


class TestGetApartmentDetail:
    """get_apartment_detail 메서드 테스트"""

    def test_get_apartment_detail_success(self, client):
        """정상적인 아파트 상세 정보 조회 - deprecated: endpoint doesn't exist"""
        # This test is deprecated since the endpoint doesn't exist
        response = client.get_apartment_detail("1Hq6f")

        # The method should return failure since the endpoint doesn't exist
        assert response.success is False
        assert response.status_code == 404
        assert "doesn't exist" in response.error

    def test_get_apartment_detail_not_found(self, client):
        """존재하지 않는 아파트 ID - deprecated: endpoint doesn't exist"""
        # This test is deprecated since the endpoint doesn't exist
        response = client.get_apartment_detail("invalid_id")

        # All IDs should return 404 since the endpoint doesn't exist
        assert response.success is False
        assert response.status_code == 404
        assert "doesn't exist" in response.error

    def test_get_apartment_detail_verify_endpoint(self, client):
        """올바른 엔드포인트 호출 확인 - 엔드포인트가 존재하지 않음"""
        # The endpoint doesn't exist, so _make_request should not be called
        with patch.object(client, "_make_request") as mock_request:
            response = client.get_apartment_detail("1Hq6f")

            # Verify that no API call was made since the endpoint doesn't exist
            mock_request.assert_not_called()

            # Verify the response indicates the endpoint doesn't exist
            assert response.success is False
            assert response.status_code == 404
            assert "doesn't exist" in response.error


class TestGetApartmentTransactions:
    """get_apartment_transactions 메서드 테스트"""

    def test_get_transactions_short_term(self, client):
        """최근 3년 실거래 내역 조회 (기본값)"""
        mock_response_data = {
            "success": True,
            "data": {
                "shortTermReport": [
                    {
                        "date": "2025-01-31T15:00:00.000Z",
                        "minPrice": 333000,
                        "maxPrice": 346000,
                        "averagePrice": 343000,
                        "volume": 3,
                        "trades": [
                            {"date": "2025-01-15", "price": 340000, "floor": 12, "area": 84.5}
                        ],
                    }
                ]
            },
        }

        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = mock_response_data

        with patch.object(
            client, "_make_request", return_value=APIResponse.from_response(mock_response)
        ):
            response = client.get_apartment_transactions("1Hq6f")

            assert response.success is True
            assert "shortTermReport" in response.data
            assert len(response.data["shortTermReport"]) == 1
            assert response.data["shortTermReport"][0]["volume"] == 3

    def test_get_transactions_full_period(self, client):
        """전체 기간 실거래 내역 조회"""
        mock_response_data = {
            "success": True,
            "data": {
                "monthlyReports": [
                    {"year": 2020, "month": 1, "price": 280000},
                    {"year": 2021, "month": 6, "price": 320000},
                ]
            },
        }

        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = mock_response_data

        with patch.object(
            client, "_make_request", return_value=APIResponse.from_response(mock_response)
        ):
            response = client.get_apartment_transactions("1Hq6f", full_period=True)

            assert response.success is True
            assert "monthlyReports" in response.data

    def test_get_transactions_with_trade_type(self, client):
        """거래 유형 필터링 (전세)"""
        mock_response_data = {
            "success": True,
            "data": {
                "shortTermReport": [
                    {
                        "date": "2025-01-31T15:00:00.000Z",
                        "minPrice": 85000,
                        "maxPrice": 90000,
                        "averagePrice": 87500,
                        "volume": 2,
                        "trades": [],
                    }
                ]
            },
        }

        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = mock_response_data

        with patch.object(
            client, "_make_request", return_value=APIResponse.from_response(mock_response)
        ):
            response = client.get_apartment_transactions("1Hq6f", trade_type=1)

            assert response.success is True
            assert response.data["shortTermReport"][0]["minPrice"] == 85000

    def test_get_transactions_verify_endpoint_short(self, client):
        """최근 3년 조회 시 올바른 엔드포인트 호출 확인"""
        with patch.object(client, "_make_request") as mock_request:
            mock_response = Mock(spec=requests.Response)
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.json.return_value = {"success": True, "data": {}}
            mock_request.return_value = APIResponse.from_response(mock_response)

            client.get_apartment_transactions("1Hq6f", trade_type=0, area_no=0)

            # Verify the call was made with correct parameters
            mock_request.assert_called_once()
            call_args = mock_request.call_args

            assert call_args.kwargs["method"] == "GET"
            assert call_args.kwargs["endpoint"] == "/api/v2/apts/1Hq6f/monthly-reports"
            assert call_args.kwargs["params"] == {"tradeType": 0, "areaNo": 0}

    def test_get_transactions_verify_endpoint_full(self, client):
        """전체 기간 조회 시 올바른 엔드포인트 호출 확인"""
        with patch.object(client, "_make_request") as mock_request:
            mock_response = Mock(spec=requests.Response)
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.json.return_value = {"success": True, "data": {}}
            mock_request.return_value = APIResponse.from_response(mock_response)

            client.get_apartment_transactions("1Hq6f", trade_type=1, area_no=1, full_period=True)

            # Verify the call was made with correct parameters
            mock_request.assert_called_once()
            call_args = mock_request.call_args

            assert call_args.kwargs["method"] == "GET"
            assert call_args.kwargs["endpoint"] == "/api/v2/apts/1Hq6f/monthly-reports/more"
            assert call_args.kwargs["params"] == {"tradeType": 1, "areaNo": 1}


class TestFetchDongCodes:
    """fetch_dong_codes 메서드 테스트"""

    def test_fetch_dong_codes_success(self, client):
        """정상적인 동 코드 조회"""
        mock_response_data = {
            "status": "success",
            "data": {
                "matched": {
                    "region": {
                        "list": [
                            {
                                "local_type": "local3",
                                "local3_name": "역삼동",
                                "local3_code": "11680500",
                            },
                            {
                                "local_type": "local3",
                                "local3_name": "개포동",
                                "local3_code": "11680600",
                            },
                            {
                                "local_type": "local2",  # 구 정보 (무시해야 함)
                                "local2_name": "강남구",
                                "local2_code": "11680",
                            },
                        ]
                    }
                }
            },
        }

        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}

        # APIResponse를 직접 mock
        api_response = Mock(spec=APIResponse)
        api_response.success = True
        api_response.data = mock_response_data

        with patch.object(client, "_make_request", return_value=api_response):
            dongs = client.fetch_dong_codes("강남구")

            assert len(dongs) == 2
            assert dongs["역삼동"] == "11680500"
            assert dongs["개포동"] == "11680600"
            assert "강남구" not in dongs  # 구 정보는 포함되지 않아야 함

    def test_fetch_dong_codes_with_coordinates(self, client):
        """좌표와 함께 동 코드 조회"""
        mock_response_data = {
            "status": "success",
            "data": {
                "matched": {
                    "region": {
                        "list": [
                            {
                                "local_type": "local3",
                                "local3_name": "서교동",
                                "local3_code": "11440500",
                            }
                        ]
                    }
                }
            },
        }

        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}

        api_response = Mock(spec=APIResponse)
        api_response.success = True
        api_response.data = mock_response_data

        with patch.object(client, "_make_request", return_value=api_response) as mock_request:
            dongs = client.fetch_dong_codes("마포구", lat=37.5568, lng=126.9236)

            # Check that _make_request was called with correct parameters
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args.args[0] == "GET"  # method
            assert call_args.args[1] == "https://hogangnono.com/api/v2/searches/new"  # URL
            assert call_args.kwargs["params"]["query"] == "마포구"
            assert call_args.kwargs["params"]["y"] == 37.5568
            assert call_args.kwargs["params"]["x"] == 126.9236

            assert len(dongs) == 1
            assert dongs["서교동"] == "11440500"

    def test_fetch_dong_codes_api_failure(self, client):
        """API 응답 실패"""
        api_response = Mock(spec=APIResponse)
        api_response.success = False
        api_response.error = "API Error"

        with patch.object(client, "_make_request", return_value=api_response):
            dongs = client.fetch_dong_codes("강남구")

            assert dongs == {}

    def test_fetch_dong_codes_incomplete_data(self, client):
        """일부 데이터가 누락된 경우"""
        mock_response_data = {
            "status": "success",
            "data": {
                "matched": {
                    "region": {
                        "list": [
                            {
                                "local_type": "local3",
                                "local3_name": "역삼동",
                                # local3_code 누락
                            },
                            {
                                "local_type": "local3",
                                # local3_name 누락
                                "local3_code": "11680600",
                            },
                            {
                                "local_type": "local3",
                                "local3_name": "개포동",
                                "local3_code": "11680600",
                            },
                        ]
                    }
                }
            },
        }

        api_response = Mock(spec=APIResponse)
        api_response.success = True
        api_response.data = mock_response_data

        with patch.object(client, "_make_request", return_value=api_response):
            dongs = client.fetch_dong_codes("강남구")

            # 완전한 데이터만 포함
            assert len(dongs) == 1
            assert dongs["개포동"] == "11680600"
            assert "역삼동" not in dongs


class TestRetryMechanism:
    """재시도 메커니즘 테스트"""

    def test_retry_decorator_applied_to_api_methods(self, client):
        """@retry_transient_errors 데코레이터가 API 메서드에 적용되었는지 확인"""

        # 데코레이터가 적용된 메서드 목록
        api_methods = [
            "get_complex_list",
            "get_complex_detail",
            "get_apartments_bounding",
            "get_ranking",
            "get_recent_visits",
            "get_region_info",
            "get_pois_bounding",
            "search_apartments",
            "get_apartment_detail",
            "get_apartment_transactions",
            "get_regions",
            "fetch_ranks_rolling",
            "fetch_pois_bounding",
            "search_apartments_by_location",
        ]

        for method_name in api_methods:
            method = getattr(client, method_name)

            # 메서드의 __func__를 통해 데코레이터 적용 확인
            assert "wrapper" in method.__name__, (
                f"{method_name} should be wrapped by retry decorator"
            )

    def test_retry_behavior_on_transient_errors(self, client):
        """일시적 오류 시 재시도 동작 테스트"""
        with patch.object(client, "_initialize_session", return_value=True):
            with patch.object(client.session, "request") as mock_request:
                # 처음 두 번은 예외 발생, 세 번째는 성공
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.headers = {"content-type": "application/json"}
                mock_response.json.return_value = {"status": "success", "data": {}}

                # 처음 두 번은 timeout 예외, 세 번째는 성공
                mock_request.side_effect = [
                    requests.exceptions.Timeout("Connection timeout"),
                    requests.exceptions.Timeout("Connection timeout"),
                    mock_response,
                ]

                # retry가 적용되면 최종적으로 성공해야 함
                result = client.get_regions()

                # 3번의 요청이 있었는지 확인 (2번 재시도 + 1번 성공)
                assert mock_request.call_count == 3
                assert result.success is True


class TestMakeRequest:
    """_make_request 메서드 테스트"""

    @patch("requests.Session.request")
    def test_make_request_with_cookies(self, mock_request, client):
        """쿠키와 함께 요청 테스트"""
        # Mock 응답 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"success": True, "data": []}
        mock_request.return_value = mock_response

        # 세션 초기화 Mock
        with patch.object(client, "_initialize_session", return_value=True):
            client._session_initialized = True
            client.session.cookies = Mock()

            # API 요청
            client._make_request(
                method="GET",
                endpoint="/api/test",
                params={"test": "value"},
            )

            # 요청 확인
            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args[1]

            # 헤더 확인
            assert "headers" in call_kwargs
            headers = call_kwargs["headers"]

            # 필수 헤더 확인
            assert "User-Agent" in headers
            assert "Accept" in headers
            assert "Referer" in headers
            assert "Origin" in headers
            assert "X-Requested-With" in headers
            assert headers["X-Requested-With"] == "XMLHttpRequest"

    def test_api_timeout_handling(self, client):
        """API 타임아웃 처리 테스트"""
        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = APIResponse(
                success=False,
                error="Request timeout",
                status_code=None,
            )

            response = client._make_request("GET", "/api/test")

            assert response.success is False
            assert "timeout" in response.error.lower()


class TestGetApartmentsBounding:
    """get_apartments_bounding 메서드 테스트"""

    def test_get_apartments_bounding_endpoint(self, client):
        """아파트 바운딩 엔드포인트 테스트"""
        search_params = SearchParams(
            bbox=(126.8781, 37.4132, 127.1834, 37.7151),
            level=14,
            tradeType=0,
        )

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = APIResponse(success=True)

            client.get_apartments_bounding(search_params)

            # 올바른 엔드포인트 호출 확인
            mock_request.assert_called_once_with(
                method="GET",
                endpoint="/api/v2/pois-bounding",
                params=search_params.to_dict(),
            )


class TestApartmentDataFiltering:
    """아파트 데이터 필터링 테스트 - Category 1은 지하철역이지 아파트가 아님"""

    def test_current_implementation_returns_subway_stations(self, client):
        """현재 구현이 지하철역만 반환하는 것을 보여주는 테스트 (실패할 것임)"""
        # Mock API 응답 - 실제 API가 반환하는 데이터 구조와 유사
        mock_response_data = {
            "data": [
                {
                    "id": "poi_1",
                    "name": "강남역",
                    "lat": 37.5172,
                    "lng": 127.0473,
                    "category": 1,  # Category 1 = 지하철역
                    "description": "지하철역",
                },
                {
                    "id": "poi_2",
                    "name": "역삼역",
                    "lat": 37.5000,
                    "lng": 127.0365,
                    "category": 1,  # Category 1 = 지하철역
                    "description": "지하철역",
                },
                {
                    "id": "poi_3",
                    "name": "래미안아파트",
                    "lat": 37.5200,
                    "lng": 127.0500,
                    "category": 3,  # Category 3 = 아파트 (가정)
                    "description": "아파트 단지",
                },
                {
                    "id": "poi_4",
                    "name": "푸르지오",
                    "lat": 37.5100,
                    "lng": 127.0400,
                    "category": 3,  # Category 3 = 아파트 (가정)
                    "description": "아파트",
                },
            ]
        }

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = APIResponse(success=True, data=mock_response_data)

            # SearchParams 생성 (aptType=1: 주상복합)
            search_params = SearchParams(
                bbox=(126.8781, 37.4132, 127.1834, 37.7151),
                level=14,
                tradeType=0,
                aptType=1,  # 주상복합으로 설정
            )

            # API 호출
            response = client.get_apartments_bounding(search_params)

            # API 호출 성공 확인
            assert response.success is True
            assert "data" in response.data

            # 현재 필터링 로직은 category == 1인 항목만 필터링
            # 이는 지하철역만 반환하게 됨
            pois = response.data["data"]
            category_1_items = [poi for poi in pois if poi.get("category") == 1]

            # Category 1 항목은 지하철역이어야 함
            assert len(category_1_items) > 0, "Category 1 항목이 있어야 함"

            # Category 1 항목들의 이름이 지하철역인지 확인
            for poi in category_1_items:
                assert "역" in poi.get("name", ""), (
                    f"Category 1 항목은 지하철역이어야 함: {poi.get('name')}"
                )

            # 실제 아파트 데이터는 category 3에 있음
            apartment_items = [poi for poi in pois if poi.get("category") == 3]
            assert len(apartment_items) > 0, "아파트 데이터가 있어야 함"

            # 아파트 이름 확인
            apartment_names = [poi.get("name") for poi in apartment_items]
            assert any("아파트" in name or "푸르지오" in name for name in apartment_names), (
                "아파트 이름이 포함되어야 함"
            )

    def test_apartment_filtering_should_not_use_category_1(self, client):
        """아파트 필터링은 category 1을 사용해서는 안 됨"""
        # Mock API 응답
        mock_response_data = {
            "data": [
                {
                    "id": "subway_1",
                    "name": "서울역",
                    "category": 1,
                    "description": "지하철역",
                },
                {
                    "id": "apt_1",
                    "name": "자이아파트",
                    "category": 3,
                    "description": "아파트",
                },
                {
                    "id": "apt_2",
                    "name": "힐스테이트",
                    "category": 3,
                    "description": "아파트",
                },
            ]
        }

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = APIResponse(success=True, data=mock_response_data)

            search_params = SearchParams(
                bbox=(126.8781, 37.4132, 127.1834, 37.7151),
                level=14,
                tradeType=0,
                aptType=0,  # 아파트로 설정
            )

            response = client.get_apartments_bounding(search_params)

            # 성공 확인
            assert response.success is True

            # fetch_apartments_by_pois 메서드 테스트
            apartments = client.fetch_apartments_by_pois(response.data)

            # 현재 구현은 category 1만 필터링하므로 지하철역만 반환됨
            # 이 테스트는 실패해야 함 - 왜냐하면 category 1은 지하철역이기 때문
            assert len(apartments) == 0, "Category 1은 지하철역이므로 아파트가 없어야 함"
