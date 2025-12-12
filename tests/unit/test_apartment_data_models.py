"""Tests for apartment data models with dataclasses."""

import unittest

# Import the dataclasses
from src.crawler.models.apartment_models import ApartmentComplex, PoiData


class TestApartmentComplex(unittest.TestCase):
    """Test cases for ApartmentComplex dataclass."""

    def test_apartment_complex_creation(self):
        """Test creating an ApartmentComplex with all fields."""
        complex_data = ApartmentComplex(
            complex_id="APT_12345",
            complex_name="테스트 아파트",
            real_estate_type="아파트",
            address="서울특별시 강남구 테헤란로",
            dong_name="테헤란동",
            lat=37.5172,
            lng=127.0473,
            completion_year_month="202301",
            total_dong_count=5,
            total_household_count=500,
            min_area=84.0,
            max_area=135.0,
            pyeong_types="84, 135",
            deal_count=10,
            lease_count=5,
            rent_count=3,
        )

        self.assertEqual(complex_data.complex_id, "APT_12345")
        self.assertEqual(complex_data.complex_name, "테스트 아파트")
        self.assertEqual(complex_data.real_estate_type, "아파트")
        self.assertEqual(complex_data.address, "서울특별시 강남구 테헤란로")
        self.assertEqual(complex_data.dong_name, "테헤란동")
        self.assertEqual(complex_data.lat, 37.5172)
        self.assertEqual(complex_data.lng, 127.0473)
        self.assertEqual(complex_data.completion_year_month, "202301")
        self.assertEqual(complex_data.total_dong_count, 5)
        self.assertEqual(complex_data.total_household_count, 500)
        self.assertEqual(complex_data.min_area, 84.0)
        self.assertEqual(complex_data.max_area, 135.0)
        self.assertEqual(complex_data.deal_count, 10)
        self.assertEqual(complex_data.lease_count, 5)
        self.assertEqual(complex_data.rent_count, 3)

    def test_apartment_complex_optional_fields(self):
        """Test creating an ApartmentComplex with optional fields as None."""
        complex_data = ApartmentComplex(complex_id="APT_12345", complex_name="테스트 아파트")

        self.assertEqual(complex_data.complex_id, "APT_12345")
        self.assertEqual(complex_data.complex_name, "테스트 아파트")
        self.assertEqual(complex_data.real_estate_type, "아파트")  # Default value
        self.assertIsNone(complex_data.address)
        self.assertIsNone(complex_data.dong_name)
        self.assertIsNone(complex_data.lat)
        self.assertIsNone(complex_data.lng)
        self.assertEqual(complex_data.deal_count, 0)  # Default value
        self.assertEqual(complex_data.lease_count, 0)  # Default value
        self.assertEqual(complex_data.rent_count, 0)  # Default value

    def test_apartment_complex_to_dict(self):
        """Test converting ApartmentComplex to dictionary."""
        complex_data = ApartmentComplex(
            complex_id="APT_12345", complex_name="테스트 아파트", lat=37.5172, lng=127.0473
        )

        result = complex_data.to_dict()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["complex_id"], "APT_12345")
        self.assertEqual(result["complex_name"], "테스트 아파트")
        self.assertEqual(result["lat"], 37.5172)
        self.assertEqual(result["lng"], 127.0473)

    def test_apartment_complex_validation(self):
        """Test validation of apartment complex data."""
        # Test valid data
        complex_data = ApartmentComplex(complex_id="APT_12345", complex_name="테스트 아파트")
        # Should not raise any exception
        self.assertIsNotNone(complex_data)

        # Test invalid complex_id (empty string)
        with self.assertRaises(ValueError) as cm:
            ApartmentComplex(complex_id="", complex_name="테스트 아파트")
        self.assertIn("complex_id is required", str(cm.exception))

        # Test invalid complex_name (None)
        with self.assertRaises(ValueError) as cm:
            ApartmentComplex(complex_id="APT_12345", complex_name=None)
        self.assertIn("complex_name is required", str(cm.exception))

        # Test invalid coordinates
        with self.assertRaises(ValueError) as cm:
            ApartmentComplex(complex_id="APT_12345", complex_name="테스트 아파트", lat=91.0)
        self.assertIn("lat must be between -90 and 90", str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            ApartmentComplex(complex_id="APT_12345", complex_name="테스트 아파트", lng=-181.0)
        self.assertIn("lng must be between -180 and 180", str(cm.exception))

        # Test negative counts
        with self.assertRaises(ValueError) as cm:
            ApartmentComplex(complex_id="APT_12345", complex_name="테스트 아파트", deal_count=-1)
        self.assertIn("deal_count must be a non-negative", str(cm.exception))

        # Test invalid area values
        with self.assertRaises(ValueError) as cm:
            ApartmentComplex(complex_id="APT_12345", complex_name="테스트 아파트", min_area=0)
        self.assertIn("min_area must be a positive", str(cm.exception))

        # Test min_area > max_area
        with self.assertRaises(ValueError) as cm:
            ApartmentComplex(
                complex_id="APT_12345", complex_name="테스트 아파트", min_area=100.0, max_area=80.0
            )
        self.assertIn("min_area", str(cm.exception))
        self.assertIn("max_area", str(cm.exception))


class TestPoiData(unittest.TestCase):
    """Test cases for PoiData dataclass."""

    def test_poi_data_creation(self):
        """Test creating a PoiData with all fields."""
        poi_data = PoiData(
            poi_id="poi_123",
            name="테스트 POI",
            lat=37.5172,
            lng=127.0473,
            category=1,
            description="아파트",
            address="서울특별시 강남구",
            dong="강남동",
        )

        self.assertEqual(poi_data.poi_id, "poi_123")
        self.assertEqual(poi_data.name, "테스트 POI")
        self.assertEqual(poi_data.lat, 37.5172)
        self.assertEqual(poi_data.lng, 127.0473)
        self.assertEqual(poi_data.category, 1)
        self.assertEqual(poi_data.description, "아파트")
        self.assertEqual(poi_data.address, "서울특별시 강남구")
        self.assertEqual(poi_data.dong, "강남동")

    def test_poi_data_extraction_from_api(self):
        """Test extracting PoiData from API response."""
        api_response = {
            "id": "poi_123",
            "name": "테스트 POI",
            "lat": 37.5172,
            "lng": 127.0473,
            "category": 1,
            "description": "아파트",
            "address": "서울특별시 강남구",
            "dong": "강남동",
        }

        poi_data = PoiData.from_api_response(api_response)

        self.assertEqual(poi_data.poi_id, "poi_123")
        self.assertEqual(poi_data.name, "테스트 POI")
        self.assertEqual(poi_data.lat, 37.5172)
        self.assertEqual(poi_data.lng, 127.0473)
        self.assertEqual(poi_data.category, 1)
        self.assertEqual(poi_data.description, "아파트")
        self.assertEqual(poi_data.address, "서울특별시 강남구")
        self.assertEqual(poi_data.dong, "강남동")

    def test_poi_data_to_dict(self):
        """Test converting PoiData to dictionary."""
        poi_data = PoiData(
            poi_id="poi_123", name="테스트 POI", lat=37.5172, lng=127.0473, category=1
        )

        result = poi_data.to_dict()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["poi_id"], "poi_123")
        self.assertEqual(result["name"], "테스트 POI")
        self.assertEqual(result["lat"], 37.5172)
        self.assertEqual(result["lng"], 127.0473)
        self.assertEqual(result["category"], 1)

    def test_poi_data_validation(self):
        """Test validation of POI data."""
        # Test valid data
        poi_data = PoiData(
            poi_id="poi_123", name="테스트 POI", lat=37.5172, lng=127.0473, category=1
        )
        self.assertIsNotNone(poi_data)

        # Test invalid poi_id (empty string)
        with self.assertRaises(ValueError) as cm:
            PoiData(poi_id="", name="테스트 POI", lat=37.5, lng=127.0, category=1)
        self.assertIn("poi_id is required", str(cm.exception))

        # Test invalid name (None)
        with self.assertRaises(ValueError) as cm:
            PoiData(poi_id="poi_123", name=None, lat=37.5, lng=127.0, category=1)
        self.assertIn("name is required", str(cm.exception))

        # Test invalid coordinates
        with self.assertRaises(ValueError) as cm:
            PoiData(poi_id="poi_123", name="테스트 POI", lat=91.0, lng=127.0, category=1)
        self.assertIn("lat must be between -90 and 90", str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            PoiData(poi_id="poi_123", name="테스트 POI", lat=37.5, lng=-181.0, category=1)
        self.assertIn("lng must be between -180 and 180", str(cm.exception))

        # Test negative category
        with self.assertRaises(ValueError) as cm:
            PoiData(poi_id="poi_123", name="테스트 POI", lat=37.5, lng=127.0, category=-1)
        self.assertIn("category must be non-negative", str(cm.exception))


class TestDataMapping(unittest.TestCase):
    """Test cases for data mapping between API responses and dataclasses."""

    def test_map_poi_response_to_poi_data(self):
        """Test mapping POI API response to PoiData."""
        # Sample API response from POI bounding API
        poi_response = {
            "id": "APT_cMf5",
            "category": 1,
            "name": "독립문",
            "description": "아파트",
            "lat": 37.596,
            "lng": 126.976,
            "address": "서울특별시 종로구 돈암동",
            "dong": "돈암동",  # This field is currently being ignored
        }

        # Test that we can map this to our dataclass
        poi_data = PoiData.from_api_response(poi_response)
        self.assertEqual(poi_data.poi_id, "APT_cMf5")
        self.assertEqual(poi_data.name, "독립문")
        self.assertEqual(poi_data.description, "아파트")
        self.assertEqual(poi_data.dong, "돈암동")

    def test_map_complex_response_to_apartment_complex(self):
        """Test mapping complex API response to ApartmentComplex."""
        complex_response = {
            "no": "11046",
            "name": "강남자이",
            "cortarNo": "1168051500",
            "cortarName": "강남구 청담동",
            "buildYear": "2023",
            "lat": 37.524462,
            "lng": 127.050101,
        }

        # Test mapping
        complex_data = ApartmentComplex.from_complex_api_response(complex_response)
        self.assertEqual(complex_data.complex_id, "APT_11046")
        self.assertEqual(complex_data.complex_name, "강남자이")
        self.assertEqual(complex_data.dong_name, "청담동")
        self.assertEqual(complex_data.completion_year_month, "2023")
        self.assertEqual(complex_data.lat, 37.524462)
        self.assertEqual(complex_data.lng, 127.050101)


if __name__ == "__main__":
    unittest.main()
