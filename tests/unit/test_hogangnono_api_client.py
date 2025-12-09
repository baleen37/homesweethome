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
        user_agent="Mozilla/5.0 (Test)",
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

            mock_request.assert_called_once_with(
                method="GET", endpoint="/api/v2/regions", params={"regionCode": "11"}
            )

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

            mock_request.assert_called_once_with(
                method="GET", endpoint="/api/v2/apts/1Hq6f", params={}
            )


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

            mock_request.assert_called_once_with(
                method="GET",
                endpoint="/api/v2/apts/1Hq6f/monthly-reports",
                params={"tradeType": 0, "areaNo": 0},
            )

    def test_get_transactions_verify_endpoint_full(self, client):
        """전체 기간 조회 시 올바른 엔드포인트 호출 확인"""
        with patch.object(client, "_make_request") as mock_request:
            mock_response = Mock(spec=requests.Response)
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.json.return_value = {"success": True, "data": {}}
            mock_request.return_value = APIResponse.from_response(mock_response)

            client.get_apartment_transactions("1Hq6f", trade_type=1, area_no=1, full_period=True)

            mock_request.assert_called_once_with(
                method="GET",
                endpoint="/api/v2/apts/1Hq6f/monthly-reports/more",
                params={"tradeType": 1, "areaNo": 1},
            )

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
