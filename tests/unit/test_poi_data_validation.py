"""Tests for POI data validation improvements

Tests the enhanced data classes and validators that ensure type safety
and proper identification of apartment vs non-apartment POIs.
"""

import pytest
from src.crawler.models.api_responses import POIInfo, POICategory, poi_info_from_bounding_response
from src.crawler.models.validators import (
    ValidationError,
    validate_poi_id,
    validate_apartment_poi,
    validate_coordinates_for_crawling,
    validate_poi_completeness,
)


class TestPOICategory:
    """Test POI category enum"""

    def test_category_from_value(self):
        """Test category creation from raw values"""
        assert POICategory.from_value(1) == POICategory.SUBWAY_STATION
        assert POICategory.from_value(9) == POICategory.HOSPITAL
        assert POICategory.from_value(10) == POICategory.MART
        assert POICategory.from_value(11) == POICategory.TRAIN_STATION
        assert POICategory.from_value(100) == POICategory.APARTMENT

        # Default for None
        assert POICategory.from_value(None) == POICategory.APARTMENT

        # Default for unknown values
        assert POICategory.from_value(999) == POICategory.APARTMENT

    def test_category_checks(self):
        """Test category helper methods"""
        assert POICategory.SUBWAY_STATION.is_transit() is True
        assert POICategory.SUBWAY_STATION.is_apartment() is False
        assert POICategory.SUBWAY_STATION.is_facility() is False

        assert POICategory.HOSPITAL.is_facility() is True
        assert POICategory.HOSPITAL.is_transit() is False
        assert POICategory.HOSPITAL.is_apartment() is False

        assert POICategory.APARTMENT.is_apartment() is True
        assert POICategory.APARTMENT.is_transit() is False
        assert POICategory.APARTMENT.is_facility() is False


class TestPOIInfo:
    """Test POIInfo data class with validation"""

    def test_subway_station_creation(self):
        """Test creating a subway station POI"""
        poi = POIInfo(
            id="bi03",
            name="일원",
            lat=37.4839886684666,
            lng=127.084129757128,
            category=1,
            description="3호선",
        )

        assert poi.id == "bi03"
        assert poi.name == "일원"
        assert poi.lat == 37.4839886684666
        assert poi.lng == 127.084129757128
        assert poi.category == 1
        assert poi.poi_category == POICategory.SUBWAY_STATION
        assert poi.is_transit() is True
        assert poi.is_apartment() is False
        assert poi.is_facility() is False

    def test_hospital_creation(self):
        """Test creating a hospital POI"""
        poi = POIInfo(
            id="1Hbd0a",
            name="삼성서울병원",
            lat=37.4882977,
            lng=127.0851508,
            category=9,
            description="종합병원",
        )

        assert poi.poi_category == POICategory.HOSPITAL
        assert poi.is_facility() is True
        assert poi.is_apartment() is False

    def test_apartment_inference(self):
        """Test apartment inference from available data"""
        # Test with households
        poi = POIInfo(
            id="apt123456",
            name="테스트아파트",
            lat=37.5,
            lng=127.0,
            households=150,
            floors=20,
            address="서울특별시 강남구 테헤란로 123",
        )

        assert poi.is_apartment() is True
        assert poi.is_transit() is False
        assert poi.is_facility() is False

    def test_invalid_apartment_id(self):
        """Test invalid apartment ID detection"""
        # Subway station ID
        subway = POIInfo(id="bi03", name="일원역", category=1)
        assert subway.is_valid_apartment_id() is False

        # Short ID
        short = POIInfo(id="abc", name="테스트")
        assert short.is_valid_apartment_id() is False

        # 1zg prefix
        zg = POIInfo(id="1zgB56", name="테스트")
        assert zg.is_valid_apartment_id() is False

        # Valid looking apartment ID
        valid = POIInfo(id="APT123456789", name="테스트아파트")
        assert valid.is_valid_apartment_id() is True

    def test_validate_for_apartment_crawling(self):
        """Test validation for apartment crawling"""
        # Valid apartment
        apartment = POIInfo(
            id="APT123456789",
            name="테스트아파트",
            lat=37.5,
            lng=127.0,
            households=100,
            address="서울특별시 강남구 테헤란로 123",
        )
        assert apartment.validate_for_apartment_crawling() is True

        # Invalid - no coordinates
        no_coords = POIInfo(id="APT123456789", name="테스트아파트", households=100)
        assert no_coords.validate_for_apartment_crawling() is False

        # Invalid - subway
        subway = POIInfo(
            id="bi03", name="일원역", lat=37.4839886684666, lng=127.084129757128, category=1
        )
        assert subway.validate_for_apartment_crawling() is False

    def test_immutability(self):
        """Test that POIInfo is immutable"""
        poi = POIInfo(id="test", name="Test POI")

        # Attempting to modify should raise an exception
        with pytest.raises(Exception):
            poi.name = "Modified"

        # But we can create new instances with modified data
        poi2 = POIInfo(id=poi.id, name="Modified")
        assert poi2.name == "Modified"
        assert poi.name == "Test POI"  # Original unchanged

    def test_coordinate_validation(self):
        """Test coordinate validation"""
        # Valid coordinates
        poi = POIInfo(id="test", name="Test", lat=37.5, lng=127.0)
        assert poi.lat == 37.5
        assert poi.lng == 127.0

        # Invalid coordinates should raise ValidationError
        with pytest.raises(ValidationError):
            POIInfo(id="test", name="Test", lat=91.0, lng=127.0)

        with pytest.raises(ValidationError):
            POIInfo(id="test", name="Test", lat=37.5, lng=181.0)


class TestPoiInfoFromApiResponse:
    """Test factory function for creating POIInfo from API responses"""

    def test_subway_from_api(self):
        """Test creating POI from actual API response data"""
        data = {
            "id": "bi03",
            "category": 1,
            "name": "일원",
            "description": "3호선",
            "lat": 37.4839886684666,
            "lng": 127.084129757128,
            "address": None,
        }

        poi = poi_info_from_bounding_response(data)

        assert isinstance(poi, POIInfo)
        assert poi.id == "bi03"
        assert poi.name == "일원"
        assert poi.category == 1
        assert poi.is_transit() is True
        assert poi.is_apartment() is False

    def test_missing_name(self):
        """Test handling of missing name field"""
        data = {"id": "test123", "lat": 37.5, "lng": 127.0}

        poi = poi_info_from_bounding_response(data)
        assert poi.name == ""  # Default empty string


class TestValidators:
    """Test validator functions"""

    def test_validate_poi_id(self):
        """Test POI ID validation"""
        # Valid IDs
        assert validate_poi_id("APT123456") == "APT123456"
        assert validate_poi_id(123) == "123"

        # Invalid IDs
        with pytest.raises(ValidationError):
            validate_poi_id("")

        with pytest.raises(ValidationError):
            validate_poi_id("a")

        assert validate_poi_id(None) is None

    def test_validate_apartment_poi(self):
        """Test apartment POI validation"""
        # Valid apartment
        assert (
            validate_apartment_poi(
                poi_id="APT123456789",
                address="서울특별시 강남구 테헤란로 123 아파트",
                households=200,
                floors=25,
            )
            is True
        )

        # Non-apartment patterns
        assert validate_apartment_poi(poi_id="bi03") is False
        assert validate_apartment_poi(poi_id="1zgB56") is False
        assert validate_apartment_poi(poi_id="Dnzcb") is False

        # Insufficient indicators
        assert validate_apartment_poi(poi_id="APT123", households=5, floors=2) is False

    def test_validate_coordinates_for_crawling(self):
        """Test coordinate validation for crawling"""
        # Valid Korea coordinates
        assert validate_coordinates_for_crawling(37.5, 127.0) is True

        # Invalid - None
        assert validate_coordinates_for_crawling(None, 127.0) is False
        assert validate_coordinates_for_crawling(37.5, None) is False

        # Invalid - Outside Korea
        assert validate_coordinates_for_crawling(0.0, 0.0) is False
        assert validate_coordinates_for_crawling(50.0, 140.0) is False

    def test_validate_poi_completeness(self):
        """Test POI data completeness validation"""
        # Complete POI
        complete_data = {
            "id": "APT123456789",
            "name": "테스트아파트",
            "lat": 37.5,
            "lng": 127.0,
            "address": "서울특별시 강남구 테헤란로 123",
            "households": 200,
            "floors": 25,
        }

        results = validate_poi_completeness(complete_data)
        assert results["has_id"] is True
        assert results["has_coordinates"] is True
        assert results["has_name"] is True
        assert results["has_address"] is True
        assert results["has_households"] is True
        assert results["has_floors"] is True
        assert results["is_apartment"] is True
        assert results["suitable_for_crawling"] is True

        # Transit POI
        transit_data = {
            "id": "bi03",
            "name": "일원역",
            "lat": 37.4839886684666,
            "lng": 127.084129757128,
            "category": 1,
            "description": "3호선",
        }

        results = validate_poi_completeness(transit_data)
        assert results["is_transit"] is True
        assert results["is_apartment"] is False
        assert results["suitable_for_crawling"] is False
