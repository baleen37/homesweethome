"""Tests for apartment ID validation and 404 error handling"""

# Import test setup to configure path and mocks

import pytest
from unittest.mock import Mock, patch
from requests import Response

from crawler.api.hogangnono_client import HogangnonoAPIClient, APIResponse
from crawler.models.api_responses import POIInfo
from crawler.config import CrawlerConfig


class TestApartmentIDValidation:
    """Tests for validating apartment IDs and handling 404 errors"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        config = CrawlerConfig()
        return HogangnonoAPIClient(config)

    def test_poi_info_apartment_id_validation(self):
        """Test POIInfo apartment ID validation logic"""
        # Valid apartment IDs (should pass validation)
        valid_apt_ids = [
            "1Iv2fb",  # 6+ characters
            "APT123456",
            "COMPLEX789",
            "1234567890",
        ]

        for apt_id in valid_apt_ids:
            poi = POIInfo(
                id=apt_id,
                name="Test Apartment",
                lat=37.5,
                lng=127.0,
                category=100,  # Apartment category
            )
            assert poi.is_valid_apartment_id(), f"ID {apt_id} should be valid"

        # Invalid apartment IDs (should fail validation)
        invalid_apt_ids = [
            "bi03",  # Subway station pattern
            "1zgA75",  # Subway station pattern
            "bhf2",  # Subway station pattern
            "1zgzf4",  # Subway station pattern
            "1Hbd0a",  # Hospital pattern
            "1A7fe4",  # Mart pattern
            "short",  # Too short
            "",  # Empty
        ]

        for apt_id in invalid_apt_ids:
            poi = POIInfo(
                id=apt_id,
                name="Test Facility",
                lat=37.5,
                lng=127.0,
                category=1,  # Non-apartment category
            )
            assert not poi.is_valid_apartment_id(), f"ID {apt_id} should be invalid"

    def test_validate_for_apartment_crawling(self):
        """Test complete validation for apartment crawling"""
        # Valid apartment POI
        valid_poi = POIInfo(
            id="1Iv2fb",
            name="테스트아파트",
            lat=37.5,
            lng=127.0,
            address="서울특별시 강남구 테헤란로 123",
            households=100,
            floors=20,
            category=100,
        )
        assert valid_poi.validate_for_apartment_crawling()

        # Invalid cases
        # 1. Missing coordinates
        poi_no_coords = POIInfo(
            id="1Iv2fb",
            name="테스트아파트",
            address="서울특별시 강남구 테헤란로 123",
            households=100,
            floors=20,
        )
        assert not poi_no_coords.validate_for_apartment_crawling()

        # 2. Invalid ID pattern
        poi_invalid_id = POIInfo(
            id="bi03",
            name="테스트역",
            lat=37.5,
            lng=127.0,
            address="서울특별시 강남구 테헤란로 지하",
            category=1,
        )
        assert not poi_invalid_id.validate_for_apartment_crawling()

        # 3. No apartment-specific data
        poi_no_data = POIInfo(id="1Iv2fb", name="테스트장소", lat=37.5, lng=127.0)
        assert not poi_no_data.validate_for_apartment_crawling()

    @patch("crawler.api.hogangnono_client.HogangnonoAPIClient._make_request")
    def test_get_apartment_transactions_404_handling(self, mock_request, client):
        """Test 404 error handling in get_apartment_transactions"""
        # Mock 404 response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 404
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "success": False,
            "message": "존재하지 않는 아파트입니다",
        }
        mock_request.return_value = APIResponse.from_response(mock_response)

        # Test with invalid apartment ID
        response = client.get_apartment_transactions("invalid_apt_id")

        assert response.success is False
        assert response.status_code == 404
        assert "존재하지 않는 아파트" in response.error or "HTTP error" in response.error

    @patch("crawler.api.hogangnono_client.HogangnonoAPIClient._make_request")
    def test_get_apartment_transactions_with_various_responses(self, mock_request, client):
        """Test get_apartment_transactions with various response scenarios"""
        test_cases = [
            # Success case
            {
                "status_code": 200,
                "response_data": {
                    "success": True,
                    "data": {
                        "shortTermReport": [
                            {
                                "date": "2025-01-31T15:00:00.000Z",
                                "minPrice": 300000,
                                "maxPrice": 400000,
                                "averagePrice": 350000,
                                "volume": 5,
                            }
                        ]
                    },
                },
                "expected_success": True,
                "description": "Successful transaction data fetch",
            },
            # 404 error
            {
                "status_code": 404,
                "response_data": {"success": False, "message": "존재하지 않는 아파트입니다"},
                "expected_success": False,
                "description": "Apartment not found",
            },
            # Server error
            {
                "status_code": 500,
                "response_data": {"success": False, "message": "서버 오류가 발생했습니다"},
                "expected_success": False,
                "description": "Server error",
            },
            # Network timeout
            {
                "status_code": None,
                "response_data": None,
                "expected_success": False,
                "description": "Network timeout",
            },
        ]

        for test_case in test_cases:
            with self.subTest(msg=test_case["description"]):
                # Setup mock
                mock_response = Mock(spec=Response)
                mock_response.status_code = test_case["status_code"]
                mock_response.headers = {"content-type": "application/json"}

                if test_case["response_data"]:
                    mock_response.json.return_value = test_case["response_data"]
                else:
                    # Simulate network error
                    mock_request.side_effect = Exception("Network timeout")

                mock_request.return_value = APIResponse.from_response(mock_response)

                # Execute
                response = client.get_apartment_transactions("test_apt_id")

                # Verify
                assert response.success == test_case["expected_success"]
                if not test_case["expected_success"]:
                    assert response.error is not None

    def test_poi_info_category_classification(self):
        """Test POI category classification"""
        # Test apartment classification
        apartment_poi = POIInfo(id="APT123456", name="테스트아파트", households=100, category=100)
        assert apartment_poi.is_apartment()
        assert not apartment_poi.is_transit()
        assert not apartment_poi.is_facility()

        # Test transit classification
        transit_poi = POIInfo(id="bi03", name="테스트역", description="지하철 2호선", category=1)
        assert not transit_poi.is_apartment()
        assert transit_poi.is_transit()
        assert not transit_poi.is_facility()

        # Test facility classification
        facility_poi = POIInfo(id="1Hbd0a", name="테스트병원", description="종합병원", category=9)
        assert not facility_poi.is_apartment()
        assert not facility_poi.is_transit()
        assert facility_poi.is_facility()

    def test_poi_info_automatic_categorization(self):
        """Test automatic POI categorization when category is not provided"""
        # Apartment by characteristics
        apt_poi = POIInfo(
            id="APT123456",
            name="테스트아파트",
            households=100,
            floors=20,
            address="서울시 강남구 아파트동 123",
        )
        assert apt_poi.is_apartment()

        # Transit by description
        transit_poi = POIInfo(id="STN123", name="테스트역사", description="지하철 2호선 테스트역")
        assert transit_poi.is_transit()

        # Facility by name
        facility_poi = POIInfo(id="FAC123", name="테스트종합병원")
        assert facility_poi.is_facility()

    @patch("crawler.api.hogangnono_client.HogangnonoAPIClient.fetch_apartments_by_pois")
    def test_parse_pois_with_invalid_apartments(self, mock_fetch, client):
        """Test parsing POIs with invalid apartment data"""
        # Mock POI response with mixed valid/invalid data
        mock_pois_response = {
            "data": [
                # Valid apartment
                {
                    "id": "APT123456",
                    "name": "유효한아파트",
                    "lat": 37.5,
                    "lng": 127.0,
                    "address": "서울특별시 강남구 테헤란로 123",
                    "households": 100,
                    "category": 100,
                },
                # Invalid - subway station
                {
                    "id": "bi03",
                    "name": "테스트역",
                    "lat": 37.5,
                    "lng": 127.0,
                    "description": "지하철역",
                    "category": 1,
                },
                # Invalid - hospital
                {
                    "id": "1Hbd0a",
                    "name": "테스트병원",
                    "lat": 37.5,
                    "lng": 127.0,
                    "description": "종합병원",
                    "category": 9,
                },
                # Invalid - missing coordinates
                {
                    "id": "APT789",
                    "name": "좌표없는아파트",
                    "address": "서울특별시 강남구",
                    "households": 50,
                    "category": 100,
                },
            ]
        }

        mock_fetch.return_value = [
            {
                "id": "APT123456",
                "name": "유효한아파트",
                "lat": 37.5,
                "lng": 127.0,
                "address": "서울특별시 강남구 테헤란로 123",
                "households": 100,
                "category": 100,
            }
        ]

        # Parse POIs
        pois = client.parse_pois_from_bounding(mock_pois_response)

        # Should only return the valid apartment
        assert len(pois) == 1
        assert pois[0].id == "APT123456"
        assert pois[0].name == "유효한아파트"
        assert pois[0].validate_for_apartment_crawling()
