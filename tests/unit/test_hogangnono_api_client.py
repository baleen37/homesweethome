"""
Tests for Hogangnono API client using real API responses.
"""

import pytest
from unittest.mock import Mock, patch
from requests import Response

from crawler.api.hogangnono_client import HogangnonoAPIClient
from crawler.config import CrawlerConfig


class TestHogangnonoAPIClient:
    """Test cases for Hogangnono API client with real API endpoints."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return CrawlerConfig(timeout=30, max_retries=3, retry_delay=1, rate_limit_delay=5)

    @pytest.fixture
    def client(self, config):
        """Create client instance."""
        return HogangnonoAPIClient(config)

    @pytest.fixture
    def ranks_rolling_response(self):
        """Mock response for /api/v2/ranks/rolling endpoint."""
        # Based on actual API call from hogangnono_api_calls.json
        response_data = {
            "data": [
                {
                    "id": 1,
                    "aptName": "테스트단지",
                    "region1": "41",
                    "region2": "135",
                    "region3": "110",
                    "address": "서울특별시 강남구 테스트동",
                    "buildDate": "2005",
                    "households": "300",
                    "dongCount": "5",
                    "floorAreaRatio": "200",
                    "buildingCoverageRatio": "60",
                    "parking": "350",
                    "totalTransactionCount": "50",
                    "recentPrice": "15억",
                    "priceChange": "▲2.3%",
                    "ranking": 1,
                },
                {
                    "id": 2,
                    "aptName": "테스트단지2",
                    "region1": "41",
                    "region2": "135",
                    "region3": "110",
                    "address": "서울특별시 강남구 테스트동2",
                    "buildDate": "2010",
                    "households": "500",
                    "dongCount": "8",
                    "floorAreaRatio": "250",
                    "buildingCoverageRatio": "50",
                    "parking": "600",
                    "totalTransactionCount": "80",
                    "recentPrice": "20억",
                    "priceChange": "▼1.2%",
                    "ranking": 2,
                },
            ]
        }
        return response_data

    @pytest.fixture
    def pois_bounding_response(self):
        """Mock response for /api/v2/pois-bounding endpoint."""
        # Based on actual API call from hogangnono_api_calls.json
        response_data = {
            "data": [
                {
                    "id": 1001,
                    "name": "테스트아파트",
                    "lat": 37.39462765056729,
                    "lng": 127.11324925186776,
                    "type": "APT",
                    "region1": "41",
                    "region2": "135",
                    "region3": "110",
                    "address": "서울특별시 강남구 테스트동 123-45",
                    "buildDate": "2005",
                    "households": 300,
                    "floors": 20,
                    "elevatorCount": 6,
                    "parkingCount": 350,
                    "heatingType": "개별난방",
                    "totalFloorArea": 45000,
                    "totalSiteArea": 15000,
                },
                {
                    "id": 1002,
                    "name": "테스트아파트2",
                    "lat": 37.3900247,
                    "lng": 127.1029496,
                    "type": "APT",
                    "region1": "41",
                    "region2": "135",
                    "region3": "110",
                    "address": "서울특별시 강남구 테스트동2 678-90",
                    "buildDate": "2010",
                    "households": 500,
                    "floors": 25,
                    "elevatorCount": 10,
                    "parkingCount": 600,
                    "heatingType": "지역난방",
                    "totalFloorArea": 75000,
                    "totalSiteArea": 25000,
                },
            ]
        }
        return response_data

    def test_fetch_ranks_rolling_success(self, client, ranks_rolling_response):
        """Test successful fetching of ranks/rolling API."""
        # This test should fail initially (Red phase)
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = ranks_rolling_response

        with patch("requests.get", return_value=mock_response) as mock_get:
            result = client.fetch_ranks_rolling()

            # Verify API was called with correct parameters
            mock_get.assert_called_once_with(
                "https://hogangnono.com/api/v2/ranks/rolling",
                headers=client._get_headers(),
                timeout=30,
            )

            # Verify response parsing
            assert result is not None
            assert "data" in result
            assert len(result["data"]) == 2
            assert result["data"][0]["aptName"] == "테스트단지"

    def test_fetch_pois_bounding_success(self, client, pois_bounding_response):
        """Test successful fetching of pois-bounding API."""
        # This test should fail initially (Red phase)
        bounds = {
            "startX": 127.1029496,
            "endX": 127.1235489,
            "startY": 37.3900247,
            "endY": 37.3992303,
        }

        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = pois_bounding_response

        with patch("requests.get", return_value=mock_response) as mock_get:
            result = client.fetch_pois_bounding(bounds)

            # Verify API was called with correct parameters
            expected_url = "https://hogangnono.com/api/v2/pois-bounding"
            expected_params = {
                "level": 17,
                "startX": bounds["startX"],
                "endX": bounds["endX"],
                "startY": bounds["startY"],
                "endY": bounds["endY"],
                "isIgnorePin": False,
            }

            mock_get.assert_called_once_with(
                expected_url, params=expected_params, headers=client._get_headers(), timeout=30
            )

            # Verify response parsing
            assert result is not None
            assert "data" in result
            assert len(result["data"]) == 2
            assert result["data"][0]["name"] == "테스트아파트"

    def test_parse_complexes_from_ranks(self, client, ranks_rolling_response):
        """Test parsing complex data from ranks/rolling response."""
        # This test should fail initially (Red phase)
        complexes = client.parse_complexes_from_ranks(ranks_rolling_response)

        assert len(complexes) == 2

        # Check first complex
        complex1 = complexes[0]
        assert complex1["id"] == 1
        assert complex1["aptName"] == "테스트단지"
        assert complex1["address"] == "서울특별시 강남구 테스트동"
        assert complex1["buildDate"] == "2005"
        assert complex1["households"] == "300"
        assert complex1["ranking"] == 1

    def test_parse_pois_from_bounding(self, client, pois_bounding_response):
        """Test parsing POI data from pois-bounding response."""
        # This test should fail initially (Red phase)
        pois = client.parse_pois_from_bounding(pois_bounding_response)

        assert len(pois) == 2

        # Check first POI
        poi1 = pois[0]
        assert poi1["id"] == 1001
        assert poi1["name"] == "테스트아파트"
        assert poi1["lat"] == 37.39462765056729
        assert poi1["lng"] == 127.11324925186776
        assert poi1["type"] == "APT"
        assert poi1["address"] == "서울특별시 강남구 테스트동 123-45"

    def test_api_error_handling(self, client):
        """Test error handling for API calls."""
        # This test should fail initially (Red phase)
        mock_response = Mock(spec=Response)
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("requests.get", return_value=mock_response):
            with pytest.raises(Exception, match="API request failed"):
                client.fetch_ranks_rolling()

    def test_network_error_handling(self, client):
        """Test network error handling."""
        # This test should fail initially (Red phase)
        with patch("requests.get", side_effect=ConnectionError("Network error")):
            with pytest.raises(Exception, match="Network error"):
                client.fetch_ranks_rolling()

    def test_headers_generation(self, client):
        """Test that headers are correctly generated."""
        headers = client._get_headers()

        # Check required headers based on actual API calls
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "x-hogangnono-app-name" in headers
        assert "x-hogangnono-api-version" in headers
        assert "x-hogangnono-platform" in headers
        assert "x-hogangnono-release-version" in headers
        assert "x-hogangnono-at" in headers
        assert "x-hogangnono-ct" in headers
        assert "x-hogangnono-event-log" in headers
        assert "x-hogangnono-event-duration" in headers

    def test_to_csv_rows_complexes(self, client):
        """Test converting complexes data to CSV rows."""
        complexes_data = {
            "data": [
                {
                    "id": 1,
                    "aptName": "테스트단지",
                    "region1": "41",
                    "region2": "135",
                    "region3": "110",
                    "address": "서울특별시 강남구 테스트동",
                    "buildDate": "2005",
                    "households": "300",
                    "dongCount": "5",
                    "ranking": 1,
                }
            ]
        }

        rows = client.to_csv_rows_complexes(complexes_data)

        assert len(rows) == 1
        row = rows[0]
        assert row["단지ID"] == 1
        assert row["단지명"] == "테스트단지"
        assert row["주소"] == "서울특별시 강남구 테스트동"
        assert row["건축년도"] == "2005"
        assert row["세대수"] == "300"
        assert row["동수"] == "5"
        assert row["순위"] == 1

    def test_to_csv_rows_pois(self, client):
        """Test converting POI data to CSV rows."""
        pois_data = {
            "data": [
                {
                    "id": 1001,
                    "name": "테스트아파트",
                    "lat": 37.39462765056729,
                    "lng": 127.11324925186776,
                    "type": "APT",
                    "address": "서울특별시 강남구 테스트동 123-45",
                    "buildDate": "2005",
                    "households": 300,
                }
            ]
        }

        rows = client.to_csv_rows_pois(pois_data)

        assert len(rows) == 1
        row = rows[0]
        assert row["POI_ID"] == 1001
        assert row["명칭"] == "테스트아파트"
        assert row["위도"] == 37.39462765056729
        assert row["경도"] == 127.11324925186776
        assert row["유형"] == "APT"
        assert row["주소"] == "서울특별시 강남구 테스트동 123-45"
        assert row["건축년도"] == "2005"
        assert row["세대수"] == 300
