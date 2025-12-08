"""Tests for WorkingHogangnonoCrawler that use actual working APIs."""

from unittest.mock import Mock, patch
import pytest
import requests

from crawler.config import CrawlerConfig
from crawler.crawlers.working_hogangnono import WorkingHogangnonoCrawler


@pytest.fixture
def config():
    """Create test config."""
    return CrawlerConfig.from_env()


@pytest.fixture
def crawler(config):
    """Create crawler instance."""
    return WorkingHogangnonoCrawler(config)


class TestWorkingHogangnonoCrawler:
    """Test cases for WorkingHogangnonoCrawler."""

    def test_init(self, config):
        """Test crawler initialization."""
        crawler = WorkingHogangnonoCrawler(config)
        assert crawler.config == config
        assert crawler.base_url == "https://hogangnono.com"
        assert crawler.session is not None

    @patch("requests.Session.get")
    def test_fetch_popular_apartments_success(self, mock_get, crawler):
        """Test successful popular apartments fetching."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "rolling": [
                    {
                        "sidoName": "서울특별시",
                        "sigunguName": "강남구",
                        "dongName": "역삼동",
                        "rank": 1,
                        "prevRank": 1,
                        "visitor": 1744,
                        "rankType": "overall",
                        "hash": "gDG7d",
                        "regionName": "서울특별시 강남구 역삼동",
                        "name": "역삼센트럴자이",
                        "statusTag": "분양",
                    }
                ]
            },
        }
        mock_get.return_value = mock_response

        # Test
        result = crawler.fetch_popular_apartments()

        # Verify
        assert result is not None
        assert "data" in result
        assert "rolling" in result["data"]
        assert len(result["data"]["rolling"]) == 1
        assert result["data"]["rolling"][0]["name"] == "역삼센트럴자이"

        # Verify API call
        mock_get.assert_called_once_with("https://hogangnono.com/api/v2/ranks/rolling", timeout=30)

    @patch("requests.Session.get")
    def test_fetch_popular_apartments_with_location(self, mock_get, crawler):
        """Test popular apartments fetching with location parameters."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "data": {"rolling": []}}
        mock_get.return_value = mock_response

        # Test with location
        result = crawler.fetch_popular_apartments(lat=37.5665, lng=126.978)

        # Verify
        assert result["data"]["rolling"] == []

        # Note: The actual API doesn't seem to use lat/lng params,
        # but we test that our method accepts them

    @patch("requests.Session.get")
    def test_fetch_popular_apartments_api_error(self, mock_get, crawler):
        """Test handling of API error response."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
        mock_get.return_value = mock_response

        # Test
        with pytest.raises(requests.HTTPError):
            crawler.fetch_popular_apartments()

    @patch("requests.Session.get")
    def test_fetch_pois_in_area_success(self, mock_get, crawler):
        """Test successful POI fetching in area."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": [
                {
                    "id": "i54d",
                    "category": 1,
                    "name": "청담",
                    "description": "7호선",
                    "content": None,
                    "lat": 37.519455579961,
                    "lng": 127.053717937903,
                    "address": None,
                    "likes": 0,
                    "isExpired": 0,
                    "dong": None,
                    "dist": 334,
                }
            ],
        }
        mock_get.return_value = mock_response

        # Test with bounding box
        bbox = {"startX": 127.0, "endX": 127.1, "startY": 37.5, "endY": 37.6}
        result = crawler.fetch_pois_in_area(bbox)

        # Verify
        assert result is not None
        assert "data" in result
        assert len(result["data"]) == 1
        assert result["data"][0]["name"] == "청담"
        assert result["data"][0]["description"] == "7호선"

        # Verify API call
        expected_params = {
            "level": 17,
            "startX": 127.0,
            "endX": 127.1,
            "startY": 37.5,
            "endY": 37.6,
            "isIgnorePin": False,
        }
        mock_get.assert_called_once_with(
            "https://hogangnono.com/api/v2/pois-bounding", params=expected_params, timeout=30
        )

    @patch("requests.Session.get")
    def test_fetch_pois_in_area_custom_level(self, mock_get, crawler):
        """Test POI fetching with custom zoom level."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "data": []}
        mock_get.return_value = mock_response

        # Test with custom level
        bbox = {"startX": 127.0, "endX": 127.1, "startY": 37.5, "endY": 37.6}
        crawler.fetch_pois_in_area(bbox, level=15)

        # Verify level parameter
        call_args = mock_get.call_args
        assert call_args[1]["params"]["level"] == 15

    @patch("requests.Session.get")
    def test_fetch_pois_in_area_api_error(self, mock_get, crawler):
        """Test handling of POI API error."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        # Test
        bbox = {"startX": 127.0, "endX": 127.1, "startY": 37.5, "endY": 37.6}
        with pytest.raises(requests.HTTPError):
            crawler.fetch_pois_in_area(bbox)

    def test_parse_to_csv_format_apartments(self, crawler):
        """Test parsing apartment data to CSV format."""
        # Sample apartment data
        apartment_data = {
            "status": "success",
            "data": {
                "rolling": [
                    {
                        "sidoName": "서울특별시",
                        "sigunguName": "강남구",
                        "dongName": "역삼동",
                        "rank": 1,
                        "visitor": 1744,
                        "regionName": "서울특별시 강남구 역삼동",
                        "name": "역삼센트럴자이",
                        "statusTag": "분양",
                    },
                    {
                        "sidoName": "경기도",
                        "sigunguName": "성남시 분당구",
                        "dongName": "백현동",
                        "rank": 2,
                        "visitor": 86,
                        "regionName": "경기도 성남시 분당구 백현동",
                        "name": "판교푸르지오그랑블",
                        "statusTag": None,
                    },
                ]
            },
        }

        # Parse
        csv_rows = crawler.parse_to_csv_format(apartment_data, data_type="apartments")

        # Verify
        assert len(csv_rows) == 2

        # First apartment
        row1 = csv_rows[0]
        assert row1["순위"] == 1
        assert row1["아파트명"] == "역삼센트럴자이"
        assert row1["시도"] == "서울특별시"
        assert row1["시군구"] == "강남구"
        assert row1["동"] == "역삼동"
        assert row1["방문자수"] == 1744
        assert row1["상태"] == "분양"

        # Second apartment
        row2 = csv_rows[1]
        assert row2["순위"] == 2
        assert row2["아파트명"] == "판교푸르지오그랑블"
        assert row2["시도"] == "경기도"
        assert row2["시군구"] == "성남시 분당구"
        assert row2["동"] == "백현동"
        assert row2["상태"] == ""

    def test_parse_to_csv_format_pois(self, crawler):
        """Test parsing POI data to CSV format."""
        # Sample POI data
        poi_data = {
            "status": "success",
            "data": [
                {
                    "id": "i54d",
                    "category": 1,
                    "name": "청담",
                    "description": "7호선",
                    "lat": 37.519455579961,
                    "lng": 127.053717937903,
                    "address": None,
                    "dong": None,
                    "dist": 334,
                },
                {
                    "id": "1At470",
                    "category": 10,
                    "name": "판교점",
                    "description": "롯데마트",
                    "lat": 37.39554549999999,
                    "lng": 127.11361710000001,
                    "address": "경기도 성남시 분당구 삼평동 741번지",
                    "dong": "삼평동",
                    "dist": 106,
                },
            ],
        }

        # Parse
        csv_rows = crawler.parse_to_csv_format(poi_data, data_type="pois")

        # Verify
        assert len(csv_rows) == 2

        # First POI (subway station)
        row1 = csv_rows[0]
        assert row1["ID"] == "i54d"
        assert row1["이름"] == "청담"
        assert row1["설명"] == "7호선"
        assert row1["주소"] == ""
        assert row1["동"] == ""
        assert row1["거리(m)"] == 334

        # Second POI (mart)
        row2 = csv_rows[1]
        assert row2["ID"] == "1At470"
        assert row2["이름"] == "판교점"
        assert row2["설명"] == "롯데마트"
        assert row2["주소"] == "경기도 성남시 분당구 삼평동 741번지"
        assert row2["동"] == "삼평동"
        assert row2["거리(m)"] == 106

    def test_parse_to_csv_format_invalid_type(self, crawler):
        """Test parsing with invalid data type."""
        data = {"status": "success", "data": []}

        with pytest.raises(ValueError, match="Unknown data type"):
            crawler.parse_to_csv_format(data, data_type="invalid")

    def test_integration_example(self, crawler):
        """Integration example showing typical usage."""
        # This test demonstrates how the crawler would be used
        # but doesn't make actual API calls

        # Example: Fetch popular apartments
        # apartments = crawler.fetch_popular_apartments()

        # Example: Parse to CSV format
        sample_apartments = {
            "status": "success",
            "data": {
                "rolling": [
                    {
                        "sidoName": "서울특별시",
                        "sigunguName": "강남구",
                        "dongName": "역삼동",
                        "rank": 1,
                        "visitor": 1744,
                        "regionName": "서울특별시 강남구 역삼동",
                        "name": "역삼센트럴자이",
                        "statusTag": "분양",
                    }
                ]
            },
        }

        csv_data = crawler.parse_to_csv_format(sample_apartments, "apartments")

        # Verify CSV data structure
        assert len(csv_data) == 1
        assert csv_data[0]["아파트명"] == "역삼센트럴자이"
        assert all(
            key in csv_data[0]
            for key in ["순위", "아파트명", "시도", "시군구", "동", "방문자수", "상태"]
        )
