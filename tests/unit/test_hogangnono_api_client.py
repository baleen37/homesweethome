"""호갱노노 API 클라이언트 테스트

TDD 방식으로 API 메서드 구현을 테스트합니다.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from crawler.api.hogangnono_client import APIResponse, HogangnonoAPIClient
from crawler.config import CrawlerConfig


@pytest.fixture
def config():
    """테스트용 설정 객체"""
    return CrawlerConfig(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        timeout=10,
    )


@pytest.fixture
def client(config):
    """테스트용 API 클라이언트"""
    return HogangnonoAPIClient(config)


class TestGetRegions:
    """get_regions 메서드 테스트"""

    def test_get_regions_success(self, client):
        """정상적인 지역 목록 조회"""
        # Mock response setup
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

    def test_get_regions_http_error(self, client):
        """HTTP 에러 응답"""
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 500
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"message": "Internal Server Error"}

        with patch.object(
            client, "_make_request", return_value=APIResponse.from_response(mock_response)
        ):
            response = client.get_regions()

            assert response.success is False
            assert response.status_code == 500

    def test_get_regions_verify_endpoint(self, client):
        """올바른 엔드포인트 호출 확인"""
        with patch.object(client, "_make_request") as mock_request:
            mock_response = Mock(spec=requests.Response)
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.json.return_value = {"success": True, "data": {"regionList": []}}
            mock_request.return_value = APIResponse.from_response(mock_response)

            client.get_regions(region_code="11")

            # Verify the call was made with correct parameters and headers
            mock_request.assert_called_once()
            call_args = mock_request.call_args

            # Check method, endpoint, and params (using keyword arguments)
            assert call_args.kwargs["method"] == "GET"
            assert call_args.kwargs["endpoint"] == "/api/v2/regions"
            assert call_args.kwargs["params"] == {"regionCode": "11"}

            # Check basic headers
            headers = call_args.kwargs["headers"]
            assert headers["User-Agent"] == client.config.user_agent
            assert "application/json" in headers["Accept"]

    def test_get_regions_empty_response(self, client):
        """빈 응답 처리"""
        mock_response_data = {"success": True, "data": {"regionList": []}}

        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = mock_response_data

        with patch.object(
            client, "_make_request", return_value=APIResponse.from_response(mock_response)
        ):
            response = client.get_regions()

            assert response.success is True
            assert response.data["regionList"] == []


class TestGetApartmentDetail:
    """get_apartment_detail 메서드 테스트"""

    def test_get_apartment_detail_success(self, client):
        """정상적인 아파트 상세 정보 조회"""
        mock_response_data = {
            "success": True,
            "data": {
                "aptHash": "1Hq6f",
                "aptName": "래미안",
                "buildYear": 2005,
                "household": 1012,
                "parkingCount": 850,
                "floorAreaRatio": 250.5,
                "buildingCoverageRatio": 15.3,
            },
        }

        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = mock_response_data

        with patch.object(
            client, "_make_request", return_value=APIResponse.from_response(mock_response)
        ):
            response = client.get_apartment_detail("1Hq6f")

            assert response.success is True
            assert response.data["aptHash"] == "1Hq6f"
            assert response.data["aptName"] == "래미안"
            assert response.data["buildYear"] == 2005

    def test_get_apartment_detail_not_found(self, client):
        """존재하지 않는 아파트 ID"""
        mock_response_data = {"success": False, "error": "Apartment not found"}

        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 404
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = mock_response_data

        with patch.object(
            client, "_make_request", return_value=APIResponse.from_response(mock_response)
        ):
            response = client.get_apartment_detail("invalid_id")

            assert response.success is False
            assert response.status_code == 404
            assert "Apartment not found" in response.error

    def test_get_apartment_detail_verify_endpoint(self, client):
        """올바른 엔드포인트 호출 확인"""
        with patch.object(client, "_make_request") as mock_request:
            mock_response = Mock(spec=requests.Response)
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.json.return_value = {"success": True, "data": {}}
            mock_request.return_value = APIResponse.from_response(mock_response)

            client.get_apartment_detail("1Hq6f")

            # Verify the call was made with correct parameters
            mock_request.assert_called_once()
            call_args = mock_request.call_args

            # Check method, endpoint, and params (using keyword arguments)
            assert call_args.kwargs["method"] == "GET"
            assert call_args.kwargs["endpoint"] == "/api/v2/apts/1Hq6f"
            assert call_args.kwargs["params"] == {}

            # headers parameter might not be explicitly passed (it can be None and added internally)
            # So we just verify the call happened with correct method, endpoint, and params


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

    def test_get_transactions_with_area_filter(self, client):
        """면적 필터링"""
        mock_response_data = {
            "success": True,
            "data": {
                "shortTermReport": [
                    {
                        "date": "2025-01-31T15:00:00.000Z",
                        "minPrice": 400000,
                        "maxPrice": 420000,
                        "averagePrice": 410000,
                        "volume": 1,
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
            response = client.get_apartment_transactions("1Hq6f", area_no=1)

            assert response.success is True

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

            # Check method, endpoint, and params (using keyword arguments)
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

            # Check method, endpoint, and params (using keyword arguments)
            assert call_args.kwargs["method"] == "GET"
            assert call_args.kwargs["endpoint"] == "/api/v2/apts/1Hq6f/monthly-reports/more"
            assert call_args.kwargs["params"] == {"tradeType": 1, "areaNo": 1}

    def test_get_transactions_invalid_apt_id(self, client):
        """유효하지 않은 아파트 ID"""
        mock_response_data = {"success": False, "error": "Invalid apartment ID"}

        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 400
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = mock_response_data

        with patch.object(
            client, "_make_request", return_value=APIResponse.from_response(mock_response)
        ):
            response = client.get_apartment_transactions("")

            assert response.success is False
            assert response.status_code == 400

    def test_get_transactions_no_data(self, client):
        """실거래 내역이 없는 경우"""
        mock_response_data = {"success": True, "data": {"shortTermReport": []}}

        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = mock_response_data

        with patch.object(
            client, "_make_request", return_value=APIResponse.from_response(mock_response)
        ):
            response = client.get_apartment_transactions("1Hq6f")

            assert response.success is True
            assert response.data["shortTermReport"] == []


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

    def test_fetch_dong_codes_status_not_success(self, client):
        """API 응답의 status가 success가 아닌 경우"""
        mock_response_data = {"status": "error", "message": "Invalid query"}

        api_response = Mock(spec=APIResponse)
        api_response.success = True
        api_response.data = mock_response_data

        with patch.object(client, "_make_request", return_value=api_response):
            dongs = client.fetch_dong_codes("강남구")

            assert dongs == {}

    def test_fetch_dong_codes_no_region_data(self, client):
        """region 데이터가 없는 경우"""
        mock_response_data = {"status": "success", "data": {"matched": {}}}

        api_response = Mock(spec=APIResponse)
        api_response.success = True
        api_response.data = mock_response_data

        with patch.object(client, "_make_request", return_value=api_response):
            dongs = client.fetch_dong_codes("강남구")

            assert dongs == {}

    def test_fetch_dong_codes_no_local3_data(self, client):
        """local_type이 local3인 데이터가 없는 경우"""
        mock_response_data = {
            "status": "success",
            "data": {
                "matched": {
                    "region": {
                        "list": [
                            {
                                "local_type": "local2",
                                "local2_name": "강남구",
                                "local2_code": "11680",
                            },
                            {
                                "local_type": "local1",
                                "local1_name": "서울특별시",
                                "local1_code": "11",
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

    def test_fetch_dong_codes_request_exception(self, client):
        """요청 중 예외 발생"""
        with patch.object(client, "_make_request", side_effect=Exception("Network error")):
            dongs = client.fetch_dong_codes("강남구")

            assert dongs == {}


class TestRateLimiting:
    """Rate limiting 초기값 테스트"""

    def test_rate_limiting_initial_values(self, config):
        """Rate limiting은 API 가이드에 따라 2초에서 시작하고 최소 1초를 가져야 함"""
        client = HogangnonoAPIClient(config)

        # 초기값 확인
        assert (
            client.rate_limiter.current_delay == 2.0
        ), f"Expected 2.0, got {client.rate_limiter.current_delay}"
        assert (
            client.rate_limiter.min_delay == 1.0
        ), f"Expected 1.0, got {client.rate_limiter.min_delay}"

        # 최대값 확인
        assert (
            client.rate_limiter.max_delay == 10.0
        ), f"Expected 10.0, got {client.rate_limiter.max_delay}"
