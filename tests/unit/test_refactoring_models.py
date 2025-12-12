"""Tests for model refactoring - verify existing behavior before refactoring."""

import pytest
import sys
from datetime import datetime
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from crawler.models.apartment_data import PoiData, ApartmentComplex
from crawler.models.apartment_models import POI, Apartment, RealEstateType, POICategory


class TestPoiDataVsPOI:
    """Test behavior of both PoiData and POI classes."""

    def test_poi_data_creation(self):
        """Test PoiData creation and validation."""
        poi = PoiData(
            poi_id="12345",
            name="테스트 아파트",
            lat=37.123,
            lng=127.456,
            category=1,
            description="아파트",
            address="서울시 강남구",
            dong="강남구",
        )

        assert poi.poi_id == "12345"
        assert poi.name == "테스트 아파트"
        assert poi.lat == 37.123
        assert poi.lng == 127.456
        assert poi.category == 1

    def test_poi_data_validation(self):
        """Test PoiData validation."""
        # Valid coordinates should pass
        poi = PoiData(poi_id="123", name="Test", lat=37.5, lng=127.0, category=1)
        assert poi.lat == 37.5
        assert poi.lng == 127.0

        # Invalid coordinates should raise error
        with pytest.raises(ValueError, match="lat must be between -90 and 90"):
            PoiData(
                poi_id="123",
                name="Test",
                lat=91.0,  # Invalid latitude
                lng=127.0,
                category=1,
            )

        with pytest.raises(ValueError, match="lng must be between -180 and 180"):
            PoiData(
                poi_id="123",
                name="Test",
                lat=37.5,
                lng=181.0,  # Invalid longitude
                category=1,
            )

    def test_poi_data_from_api_response(self):
        """Test PoiData.from_api_response factory method."""
        response = {
            "id": "APT_12345",
            "name": "테스트 아파트",
            "lat": "37.123",
            "lng": "127.456",
            "category": "1",
            "description": "아파트 단지",
            "dong": "강남구",
        }

        poi = PoiData.from_api_response(response)

        assert poi.poi_id == "APT_12345"
        assert poi.name == "테스트 아파트"
        assert poi.lat == 37.123
        assert poi.lng == 127.456
        assert poi.category == 1
        assert poi.description == "아파트 단지"
        assert poi.dong == "강남구"

    def test_poi_data_to_dict(self):
        """Test PoiData.to_dict method."""
        poi = PoiData(poi_id="123", name="Test", lat=37.5, lng=127.0, category=1, dong="Test Dong")

        poi_dict = poi.to_dict()

        assert isinstance(poi_dict, dict)
        assert poi_dict["poi_id"] == "123"
        assert poi_dict["name"] == "Test"
        assert poi_dict["lat"] == 37.5
        assert poi_dict["lng"] == 127.0
        assert poi_dict["category"] == 1
        assert poi_dict["dong"] == "Test Dong"

    def test_poi_creation(self):
        """Test POI creation from apartment_models."""
        poi = POI(
            id="APT_123",
            name="테스트 POI",
            category=POICategory.APARTMENT,
            coordinates=(37.123, 127.456),
            address="서울시 강남구",
        )

        assert poi.id == "APT_123"
        assert poi.name == "테스트 POI"
        assert poi.category == POICategory.APARTMENT
        assert poi.coordinates == (37.123, 127.456)

    def test_poi_is_apartment(self):
        """Test POI.is_apartment method."""
        apartment_poi = POI(
            id="APT_123", name="아파트", category=POICategory.APARTMENT, coordinates=(37.0, 127.0)
        )

        non_apartment_poi = POI(
            id="SUB_123", name="지하철역", category=POICategory.SUBWAY, coordinates=(37.0, 127.0)
        )

        assert apartment_poi.is_apartment()
        assert not non_apartment_poi.is_apartment()


class TestApartmentComplexVsApartment:
    """Test behavior of both ApartmentComplex and Apartment classes."""

    def test_apartment_complex_creation(self):
        """Test ApartmentComplex creation and validation."""
        complex_data = ApartmentComplex(
            complex_id="APT_12345",
            complex_name="테스트 아파트",
            real_estate_type="아파트",
            address="서울시 강남구",
            dong_name="강남구",
            lat=37.123,
            lng=127.456,
            completion_year_month="202001",
            total_dong_count=5,
            total_household_count=500,
            min_area=33.0,
            max_area=84.0,
            deal_count=10,
            lease_count=5,
            rent_count=2,
        )

        assert complex_data.complex_id == "APT_12345"
        assert complex_data.complex_name == "테스트 아파트"
        assert complex_data.total_household_count == 500

    def test_apartment_complex_validation(self):
        """Test ApartmentComplex validation."""
        # Valid complex should pass
        complex_data = ApartmentComplex(
            complex_id="APT_123", complex_name="Test", total_household_count=100
        )
        assert complex_data.total_household_count == 100

        # Invalid counts should raise error
        with pytest.raises(ValueError, match="deal_count must be a non-negative integer"):
            ApartmentComplex(complex_id="APT_123", complex_name="Test", deal_count=-1)

        # Invalid area consistency should raise error
        with pytest.raises(ValueError, match="min_area .* cannot be greater than max_area"):
            ApartmentComplex(
                complex_id="APT_123", complex_name="Test", min_area=100.0, max_area=50.0
            )

    def test_apartment_complex_from_poi_data(self):
        """Test ApartmentComplex.from_poi_data method."""
        poi = PoiData(
            poi_id="APT_12345",
            name="테스트 아파트",
            lat=37.123,
            lng=127.456,
            category=1,
            description="주상복합",
            address="서울특별시 강남구 역삼동",
            dong="역삼동",
        )

        complex_data = ApartmentComplex.from_poi_data(poi)

        assert complex_data.complex_id == "APT_12345"
        assert complex_data.complex_name == "테스트 아파트"
        assert complex_data.real_estate_type == "주상복합"
        assert complex_data.address == "서울특별시 강남구 역삼동"
        assert complex_data.dong_name == "역삼동"
        assert complex_data.lat == 37.123
        assert complex_data.lng == 127.456

    def test_apartment_creation(self):
        """Test Apartment creation from apartment_models."""
        apartment = Apartment(
            complex_id="APT_123",
            complex_name="테스트 아파트",
            real_estate_type=RealEstateType.APARTMENT,
            completion_year_month="202001",
            total_household_count=500,
            coordinates=(37.123, 127.456),
            fetched_at=datetime(2024, 1, 1, 12, 0, 0),
        )

        assert apartment.complex_id == "APT_123"
        assert apartment.complex_name == "테스트 아파트"
        assert apartment.real_estate_type == RealEstateType.APARTMENT
        assert apartment.total_household_count == 500

    def test_apartment_validation(self):
        """Test Apartment.is_valid_apartment method."""
        valid_apartment = Apartment(
            complex_id="APT_123",
            complex_name="테스트",
            real_estate_type=RealEstateType.APARTMENT,
            total_household_count=100,
        )

        invalid_apartment = Apartment(
            complex_id="123",  # Missing APT_ prefix
            complex_name="테스트",
            real_estate_type=RealEstateType.APARTMENT,
            total_household_count=100,
        )

        zero_household = Apartment(
            complex_id="APT_123",
            complex_name="테스트",
            real_estate_type=RealEstateType.APARTMENT,
            total_household_count=0,
        )

        assert valid_apartment.is_valid_apartment()
        assert not invalid_apartment.is_valid_apartment()
        assert not zero_household.is_valid_apartment()

    def test_apartment_to_csv_row(self):
        """Test Apartment.to_csv_row method."""
        apartment = Apartment(
            complex_id="APT_123",
            complex_name="테스트 아파트",
            real_estate_type=RealEstateType.APARTMENT,
            completion_year_month="202001",
            total_household_count=500,
            coordinates=(37.123, 127.456),
            fetched_at=datetime(2024, 1, 1, 12, 0, 0),
        )

        csv_row = apartment.to_csv_row()

        assert isinstance(csv_row, dict)
        assert csv_row["complex_id"] == "APT_123"
        assert csv_row["complex_name"] == "테스트 아파트"
        assert csv_row["real_estate_type"] == "아파트"
        assert csv_row["total_household_count"] == 500
        assert csv_row["latitude"] == 37.123
        assert csv_row["longitude"] == 127.456


class TestModelDifferences:
    """Document differences between similar models for refactoring reference."""

    def test_poi_vs_poidata_field_differences(self):
        """Test field differences between POI and PoiData."""
        # POI uses 'id', PoiData uses 'poi_id'
        # POI uses 'coordinates' tuple, PoiData uses separate 'lat'/'lng'
        # PoiData has more validation logic
        pass

    def test_apartment_vs_apartmentcomplex_field_differences(self):
        """Test field differences between Apartment and ApartmentComplex."""
        # Similar fields but different names
        # Apartment uses enum for real_estate_type
        # ApartmentComplex uses string for real_estate_type
        # Different validation approaches
        pass
