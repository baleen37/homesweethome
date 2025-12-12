"""Tests for EnhancedPOIInfo data class using TDD approach"""


# Test First: 이 테스트들은 실패할 것입니다 (EnhancedPOIInfo가 아직 없음)
class TestEnhancedPOIIDValidation:
    """Test EnhancedPOIInfo apartment ID validation following TDD RED phase"""

    def test_valid_apartment_ids(self):
        """RED phase: Test that valid apartment IDs pass validation"""
        # These are known valid apartment IDs from real API responses
        valid_apt_ids = [
            "1OIb1",  # 강남구 아파트
            "A100000001",  # Systematic apartment ID
            "B200000002",  # Another systematic ID
            "C300000003",  # Another systematic ID
            "1KN8a",  # Real apartment hash
            "1NF62",  # Real apartment hash
            "gDG7d",  # 역삼센트럴자이
            "1Hq6f",  # Real apartment ID from API docs
            "1Hde0b",  # Real apartment ID
            "Dnzcb",  # Real apartment ID
        ]

        for apt_id in valid_apt_ids:
            # This will fail because EnhancedPOIInfo doesn't exist yet
            from src.crawler.models.enhanced_api_responses import EnhancedPOIInfo

            poi = EnhancedPOIInfo(id=apt_id, name="Test Apartment")
            assert poi.is_valid_apartment_id(), f"ID {apt_id} should be valid"

    def test_invalid_apartment_ids(self):
        """RED phase: Test that invalid apartment IDs fail validation"""
        # These are known non-apartment IDs from API responses
        invalid_apt_ids = [
            "bi03",  # Subway station
            "1zgA75",  # Subway station
            "1zgB56",  # Subway station
            "bhf2",  # Subway station
            "1zgzf4",  # Subway station
            "1Hbd0a",  # Hospital
            "1A7fe4",  # Mart
            "subway_123",  # Obviously not an apartment
            "",  # Empty string
            None,  # None value
            "123",  # Too short
            "역삼역",  # Subway station name
            "신촌병원",  # Hospital name
        ]

        for apt_id in invalid_apt_ids:
            from src.crawler.models.enhanced_api_responses import EnhancedPOIInfo

            poi = EnhancedPOIInfo(id=apt_id, name="Test POI")
            assert not poi.is_valid_apartment_id(), f"ID {apt_id} should be invalid"

    def test_apartment_id_patterns(self):
        """RED phase: Test specific apartment ID patterns"""
        # Test pattern matching for different ID formats

        # Hash-like IDs (mixed alphanumeric, 5-6 chars)
        hash_like_ids = ["1OIb1", "1KN8a", "gDG7d", "1Hq6f"]
        for apt_id in hash_like_ids:
            from src.crawler.models.enhanced_api_responses import EnhancedPOIInfo

            poi = EnhancedPOIInfo(id=apt_id, name="Test Apartment")
            assert poi.is_valid_apartment_id(), f"Hash-like ID {apt_id} should be valid"

        # Systematic IDs (Letter + numbers)
        systematic_ids = ["A100000001", "B200000002", "C300000003"]
        for apt_id in systematic_ids:
            from src.crawler.models.enhanced_api_responses import EnhancedPOIInfo

            poi = EnhancedPOIInfo(id=apt_id, name="Test Apartment")
            assert poi.is_valid_apartment_id(), f"Systematic ID {apt_id} should be valid"

        # Subway patterns to exclude
        subway_patterns = ["bi", "1zg", "bh"]
        for pattern in subway_patterns:
            test_id = pattern + "123"
            from src.crawler.models.enhanced_api_responses import EnhancedPOIInfo

            poi = EnhancedPOIInfo(id=test_id, name="Test POI")
            assert not poi.is_valid_apartment_id(), f"Subway pattern {pattern} should be excluded"

    def test_data_quality_assessment(self):
        """RED phase: Test data quality assessment for apartment POIs"""
        from src.crawler.models.enhanced_api_responses import EnhancedPOIInfo

        # Create a high-quality apartment POI
        poi = EnhancedPOIInfo(
            id="1OIb1",
            name="래미안 강남파크룩스",
            lat=37.5172,
            lng=127.0473,
            address="서울특별시 강남구 개포동",
            households=532,
            floors=35,
        )

        quality = poi.assess_data_quality()
        assert quality["score"] >= 0.8, (
            f"High-quality POI should have score >= 0.8, got {quality['score']}"
        )
        assert quality["level"] == "high", f"Quality level should be 'high', got {quality['level']}"

        # Create a low-quality POI
        low_quality_poi = EnhancedPOIInfo(
            id="bi03",  # Subway station ID
            name="역삼역",
            lat=None,
            lng=None,
            address=None,
            households=None,
            floors=None,
        )

        quality = low_quality_poi.assess_data_quality()
        assert quality["score"] <= 0.3, (
            f"Low-quality POI should have score <= 0.3, got {quality['score']}"
        )
        assert not low_quality_poi.is_valid_apartment_id(), (
            "Subway station should not be valid apartment"
        )

    def test_completeness_metrics(self):
        """RED phase: Test data completeness calculation"""
        from src.crawler.models.enhanced_api_responses import EnhancedPOIInfo

        # POI with all fields
        complete_poi = EnhancedPOIInfo(
            id="1OIb1",
            name="Complete Apartment",
            lat=37.5,
            lng=127.0,
            address="Complete Address",
            households=100,
            floors=20,
            build_date="201001",
            elevator_count=5,
            parking_count=200,
        )

        completeness = complete_poi.calculate_completeness()
        assert completeness >= 0.8, (
            f"Complete POI should have >= 80% completeness, got {completeness * 100}%"
        )

        # POI with minimal fields
        minimal_poi = EnhancedPOIInfo(id="12345", name="Minimal Apartment")

        completeness = minimal_poi.calculate_completeness()
        assert completeness <= 0.4, (
            f"Minimal POI should have <= 40% completeness, got {completeness * 100}%"
        )

    def test_validation_for_crawling(self):
        """RED phase: Test validation for apartment crawling suitability"""
        from src.crawler.models.enhanced_api_responses import EnhancedPOIInfo

        # Valid crawling candidate
        valid_poi = EnhancedPOIInfo(
            id="1OIb1",
            name="Valid Apartment",
            lat=37.5,
            lng=127.0,
            address="서울특별시 강남구",
            households=100,
        )

        assert valid_poi.validate_for_apartment_crawling(), (
            "Valid apartment should pass crawling validation"
        )

        # Invalid candidates
        invalid_pois = [
            EnhancedPOIInfo(id="bi03", name="역삼역"),  # Invalid ID
            EnhancedPOIInfo(id="12345", name="No Coords"),  # Missing coordinates
            EnhancedPOIInfo(
                id="123456", name="No Address", lat=37.5, lng=127.0
            ),  # Missing address/households
        ]

        for poi in invalid_pois:
            assert not poi.validate_for_apartment_crawling(), (
                f"POI {poi.name} should not pass crawling validation"
            )

    def test_edge_cases(self):
        """RED phase: Test edge cases and boundary conditions"""
        from src.crawler.models.enhanced_api_responses import EnhancedPOIInfo

        # Numeric IDs
        numeric_poi = EnhancedPOIInfo(id=123456, name="Numeric ID Apartment")
        assert numeric_poi.is_valid_apartment_id(), (
            "Numeric ID should be converted to string and validated"
        )

        # Mixed case IDs
        mixed_case_ids = ["a1B2c3", "AbCdEf", "1oIb1"]
        for apt_id in mixed_case_ids:
            poi = EnhancedPOIInfo(id=apt_id, name="Mixed Case Apartment")
            # Case shouldn't matter for validation
            result = poi.is_valid_apartment_id()
            assert isinstance(result, bool), f"Should return boolean for ID {apt_id}"

        # Special characters
        special_chars = ["A123-456", "B_123456", "C.123.456"]
        for apt_id in special_chars:
            poi = EnhancedPOIInfo(id=apt_id, name="Special Chars POI")
            # Should handle gracefully
            result = poi.is_valid_apartment_id()
            assert isinstance(result, bool), f"Should return boolean for special chars ID {apt_id}"

    def test_enhanced_features(self):
        """RED phase: Test enhanced features not in original POIInfo"""
        from src.crawler.models.enhanced_api_responses import EnhancedPOIInfo

        # Test data quality score calculation
        poi = EnhancedPOIInfo(
            id="1OIb1",
            name="Test Apartment",
            lat=37.5,
            lng=127.0,
            address="Test Address",
            households=100,
        )

        # Should have enhanced methods
        assert hasattr(poi, "assess_data_quality"), "Should have assess_data_quality method"
        assert hasattr(poi, "calculate_completeness"), "Should have calculate_completeness method"
        assert hasattr(poi, "get_validation_summary"), "Should have get_validation_summary method"

        # Test validation summary
        summary = poi.get_validation_summary()
        assert isinstance(summary, dict), "Validation summary should be a dict"
        assert "is_apartment" in summary, "Summary should include is_apartment"
        assert "is_valid_id" in summary, "Summary should include is_valid_id"
        assert "quality_score" in summary, "Summary should include quality_score"
