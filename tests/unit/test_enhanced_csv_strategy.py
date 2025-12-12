"""Tests for enhanced CSV strategy using dataclasses."""

from unittest.mock import Mock, patch

from src.crawler.models.apartment_data import ApartmentComplex, PoiData
from src.crawler.writers.enhanced_hogangnono_strategy import EnhancedHogangnonoComplexStrategy


class TestEnhancedHogangnonoComplexStrategy:
    """Test cases for the enhanced CSV strategy."""

    def test_write_apartment_complex_to_csv(self):
        """Test writing ApartmentComplex data to CSV."""
        # Create test data
        complexes = [
            ApartmentComplex(
                complex_id="APT_001",
                complex_name="테스트아파트1",
                dong_name="테스트동",
                completion_year_month="2023",
                total_household_count=300,
            ),
            ApartmentComplex(
                complex_id="APT_002",
                complex_name="테스트아파트2",
                dong_name="예시동",
                completion_year_month="2022",
            ),
        ]

        # Create strategy and mock CSV writer
        strategy = EnhancedHogangnonoComplexStrategy()

        # Mock the CSV file operations
        with patch("builtins.open", create=True) as mock_open:
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            # Test writing
            strategy.write_apartments_to_csv(complexes, "test.csv")

            # Verify file was opened
            mock_open.assert_called_once_with("test.csv", mode="w", encoding="utf-8", newline="")

            # Verify CSV was written
            mock_file.write.assert_called()

    def test_complex_to_dict_mapping(self):
        """Test that ApartmentComplex is properly mapped to CSV dict."""
        complex = ApartmentComplex(
            complex_id="APT_TEST",
            complex_name="매핑테스트",
            dong_name="테스트동",
            address="서울특별시 강남구 테스트동",
            completion_year_month="2023",
            total_household_count=500,
            min_area=33.0,
            max_area=85.0,
            deal_count=10,
        )

        # Use the strategy to convert to dict
        strategy = EnhancedHogangnonoComplexStrategy()
        result = strategy._complex_to_dict(complex)

        # Verify mapping
        assert result["complex_id"] == "APT_TEST"
        assert result["complex_name"] == "매핑테스트"
        assert result["dong_name"] == "테스트동"  # This should now be included!
        assert result["total_household_count"] == 500
        assert result["deal_count"] == 10

    def test_merge_poi_data_to_complex(self):
        """Test merging POI data into ApartmentComplex."""
        # Create POI data with dong field
        poi = PoiData(
            poi_id="APT_POI",
            name="POI테스트",
            lat=37.5,
            lng=127.0,
            category=1,
            address="서울특별시 강남구 청담동",
            dong="청담동",  # This is the key field!
        )

        # Convert to ApartmentComplex
        complex = ApartmentComplex.from_poi_data(poi)

        # Verify dong was properly extracted
        assert complex.complex_id == "APT_POI"
        assert complex.complex_name == "POI테스트"
        assert complex.dong_name == "청담동"  # Should be extracted from POI!

    def test_csv_headers_included_dong(self):
        """Test that CSV headers include the dong_name field."""
        strategy = EnhancedHogangnonoComplexStrategy()
        headers = strategy.get_csv_headers()

        assert "complex_id" in headers
        assert "complex_name" in headers
        assert "dong_name" in headers  # Critical: this field must be included!
        assert "completion_year_month" in headers
        assert "total_household_count" in headers
