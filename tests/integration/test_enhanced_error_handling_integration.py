"""Integration tests for enhanced error handling and data validation"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock
from datetime import datetime

from crawler.api.hogangnono_client import HogangnonoAPIClient, APIResponse
from crawler.config import CrawlerConfig
from crawler.models.enhanced_api_responses import EnhancedPOIInfo, ApartmentCollection, DataQuality
from crawler.utils.enhanced_error_handler import EnhancedErrorHandler, ErrorType, ErrorInfo
from crawler.validators.csv_validator import create_complexes_validator
from crawler.writers.hogangnono_csv_writer import HogangnonoCSVWriter


class TestEnhancedErrorHandlingIntegration:
    """Integration tests for the enhanced error handling system"""

    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return CrawlerConfig()

    @pytest.fixture
    def client(self, config):
        """Create test API client"""
        return HogangnonoAPIClient(config)

    @pytest.fixture
    def error_handler(self):
        """Create enhanced error handler"""
        return EnhancedErrorHandler(max_retries=2, retry_delay=0.1)

    @pytest.fixture
    def sample_pois_data(self):
        """Sample POI data with mixed valid/invalid apartments"""
        return {
            "data": [
                # Valid apartment
                {
                    "id": "APT123456789",
                    "name": "테스트아파트1",
                    "lat": 37.5665,
                    "lng": 126.9780,
                    "address": "서울특별시 중구 세종대로 123",
                    "households": 300,
                    "floors": 25,
                    "category": 100,
                },
                # Another valid apartment
                {
                    "id": "COMPLEX987654",
                    "name": "테스트아파트2",
                    "lat": 37.5670,
                    "lng": 126.9785,
                    "address": "서울특별시 중구 세종대로 456",
                    "households": 150,
                    "floors": 15,
                    "category": 100,
                },
                # Invalid - subway station
                {
                    "id": "bi03",
                    "name": "테스트역",
                    "lat": 37.5660,
                    "lng": 126.9775,
                    "description": "지하철 2호선",
                    "category": 1,
                },
                # Invalid - hospital
                {
                    "id": "1Hbd0a",
                    "name": "테스트병원",
                    "lat": 37.5680,
                    "lng": 126.9790,
                    "description": "종합병원",
                    "category": 9,
                },
                # Invalid - missing coordinates
                {
                    "id": "APT111222",
                    "name": "좌표없는아파트",
                    "address": "서울특별시 중구",
                    "households": 100,
                    "category": 100,
                },
            ]
        }

    def test_end_to_end_error_handling(self, client, error_handler, sample_pois_data):
        """Test end-to-end error handling flow"""

        # Mock API responses
        def mock_get_apartment_transactions(apt_id, **kwargs):
            # Return 404 for certain IDs
            if apt_id in ["APT111222", "nonexistent_id"]:
                response = Mock(spec=APIResponse)
                response.success = False
                response.status_code = 404
                response.error = "존재하지 않는 아파트입니다"
                return response

            # Return success for valid IDs
            if apt_id in ["APT123456789", "COMPLEX987654"]:
                response = Mock(spec=APIResponse)
                response.success = True
                response.data = {
                    "shortTermReport": [
                        {
                            "date": "2025-01-31T15:00:00.000Z",
                            "minPrice": 300000,
                            "maxPrice": 400000,
                            "averagePrice": 350000,
                            "volume": 3,
                        }
                    ]
                }
                return response

            # Return server error for testing retry
            response = Mock(spec=APIResponse)
            response.success = False
            response.status_code = 500
            response.error = "Internal server error"
            return response

        client.get_apartment_transactions = mock_get_apartment_transactions

        # Parse POIs from sample data
        pois = client.parse_pois_from_bounding(sample_pois_data)

        # Should have 2 valid apartments
        assert len(pois) == 2
        assert all(apt.validate_for_apartment_crawling() for apt in pois)

        # Filter apartments through error handler
        filtered_collection = error_handler.filter_apartment_collection(pois)

        # Should still have 2 apartments (none filtered yet)
        assert filtered_collection.valid_count == 2

        # Process each apartment with error handling
        successful_apts = []
        failed_apts = []

        for poi in pois:
            if error_handler.should_skip_apartment(poi.id):
                failed_apts.append(poi.id)
                continue

            try:
                response = error_handler.execute_with_retry(
                    client.get_apartment_transactions, apartment_id=poi.id, apt_id=poi.id
                )

                if response.success:
                    successful_apts.append(poi.id)
                else:
                    failed_apts.append(poi.id)
                    error_handler.handle_error(response, poi.id)
            except Exception as e:
                failed_apts.append(poi.id)
                error_info = ErrorInfo(
                    error_type=ErrorType.UNKNOWN,
                    status_code=None,
                    message=str(e),
                    timestamp=datetime.now(),
                    apartment_id=poi.id,
                )
                error_handler.stats.record_error(error_info)

        # Check results
        assert len(successful_apts) == 2
        assert "APT123456789" in successful_apts
        assert "COMPLEX987654" in successful_apts

        # Get error summary
        summary = error_handler.get_error_summary()
        assert summary["error_statistics"]["total_requests"] >= 2
        assert summary["id_filter_stats"]["validated_ids_count"] == 2

    def test_csv_validation_with_error_handling(self, sample_pois_data):
        """Test CSV validation with error handling integration"""
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create enhanced POI objects
            enhanced_pois = []
            for poi_data in sample_pois_data["data"]:
                poi = EnhancedPOIInfo(
                    id=poi_data["id"],
                    name=poi_data["name"],
                    lat=poi_data.get("lat"),
                    lng=poi_data.get("lng"),
                    address=poi_data.get("address"),
                    households=poi_data.get("households"),
                    description=poi_data.get("description"),
                    category=poi_data.get("category"),
                )
                enhanced_pois.append(poi)

            # Create collection and filter valid apartments
            collection = ApartmentCollection(apartments=enhanced_pois)
            valid_collection = collection.filter_valid()

            # Convert to CSV data
            csv_data = []
            for apt in valid_collection.apartments:
                csv_data.append(
                    {
                        "complex_id": apt.id,
                        "complex_name": apt.name,
                        "address": apt.address or "",
                        "latitude": str(apt.lat) if apt.lat else "",
                        "longitude": str(apt.lng) if apt.lng else "",
                        "build_year": "",
                        "households": str(apt.households) if apt.households else "",
                        "floors": str(apt.floors) if apt.floors else "",
                        "gu_code": "",
                        "dong_code": "",
                    }
                )

            # Write CSV
            csv_file = temp_path / "test_complexes.csv"
            csv_writer = HogangnonoCSVWriter(str(temp_path))
            csv_writer.save_complexes(csv_data)

            # Validate CSV
            validator = create_complexes_validator()
            result = validator.validate_file(csv_file)

            # Should have valid data
            assert result.status in ["passed", "warning"]
            assert result.total_rows == 2
            assert result.valid_rows == 2

    def test_error_accumulation_and_recommendations(self, client, error_handler):
        """Test error accumulation and recommendation generation"""
        # Simulate various errors
        error_scenarios = [
            (404, "존재하지 않는 아파트입니다", "APT123"),
            (404, "존재하지 않는 아파트입니다", "APT456"),
            (404, "존재하지 않는 아파트입니다", "APT789"),
            (429, "요청 한도 초과", None),
            (500, "서버 오류", None),
            (500, "서버 오류", None),
            (401, "인증 실패", None),
        ]

        for status_code, message, apt_id in error_scenarios:
            response = Mock(spec=APIResponse)
            response.success = False
            response.status_code = status_code
            response.error = message

            error_handler.handle_error(response, apt_id)

        # Get summary
        summary = error_handler.get_error_summary()

        # Check error statistics
        stats = summary["error_statistics"]
        assert stats["total_errors"] == 7
        assert stats["total_requests"] == 7
        assert stats["error_rate"] == 1.0

        # Check recommendations
        recommendations = summary["recommendations"]
        assert any("404 errors" in rec for rec in recommendations)
        assert any("Rate limiting" in rec for rec in recommendations)

    def test_enhanced_poi_validation(self, sample_pois_data):
        """Test enhanced POI validation logic"""
        enhanced_pois = []

        # Create enhanced POIs from sample data
        for poi_data in sample_pois_data["data"]:
            poi = EnhancedPOIInfo(
                id=poi_data["id"],
                name=poi_data["name"],
                lat=poi_data.get("lat"),
                lng=poi_data.get("lng"),
                address=poi_data.get("address"),
                households=poi_data.get("households"),
                description=poi_data.get("description"),
                category=poi_data.get("category"),
                source="test",
            )
            enhanced_pois.append(poi)

        # Create collection
        collection = ApartmentCollection(apartments=enhanced_pois)

        # Test collection filtering
        valid_collection = collection.filter_valid()
        collection.filter_by_quality(DataQuality.HIGH)

        # Should have filtered out invalid apartments
        assert len(valid_collection.apartments) == 2
        assert valid_collection.valid_count == 2

        # Get summary
        summary = collection.get_summary()
        assert summary["total_apartments"] == 5
        assert summary["apartments"] == 2
        assert summary["transit"] == 1
        assert summary["facilities"] == 1
        assert summary["others"] == 1

    def test_circuit_breaker_functionality(self, error_handler):
        """Test circuit breaker prevents cascading failures"""
        # Mock function that always fails
        failing_func = Mock(side_effect=Exception("Service unavailable"))

        # Apply circuit breaker decorator
        wrapped_func = error_handler.circuit_breaker(failing_func)

        # Trigger failures to open circuit
        for _ in range(6):  # More than failure_threshold
            with pytest.raises(Exception):
                wrapped_func()

        # Circuit should be open now
        assert error_handler.circuit_breaker.state == "OPEN"

        # Subsequent calls should fail immediately
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            wrapped_func()

    def test_apartment_id_filter_persistence(self, error_handler):
        """Test apartment ID filter persistence and import/export"""
        # Add some invalid IDs
        error_handler.id_filter.mark_invalid("APT123", "Test error 1")
        error_handler.id_filter.mark_invalid("APT456", "Test error 2")
        error_handler.id_filter.mark_temporarily_unavailable("APT789")

        # Export invalid IDs
        exported = error_handler.id_filter.export_invalid_ids()
        assert len(exported) == 2
        assert "APT123" in exported
        assert "APT456" in exported

        # Create new filter and import
        new_handler = EnhancedErrorHandler()
        new_handler.id_filter.import_invalid_ids(exported)

        # Should recognize imported invalid IDs
        assert new_handler.should_skip_apartment("APT123")
        assert new_handler.should_skip_apartment("APT456")
        assert not new_handler.should_skip_apartment("APT999")

    def test_data_quality_assessment(self):
        """Test data quality assessment for POIs"""
        # High quality POI
        high_quality_poi = EnhancedPOIInfo(
            id="APT123456789",
            name="고품질아파트",
            lat=37.5665,
            lng=126.9780,
            address="서울특별시 중구 세종대로 123",
            households=300,
            floors=25,
            category=100,
        )
        assert high_quality_poi.data_quality == DataQuality.HIGH

        # Low quality POI (missing data)
        low_quality_poi = EnhancedPOIInfo(
            id="APT111", name="저품질아파트", lat=37.5665, lng=126.9780, category=100
        )
        assert low_quality_poi.data_quality == DataQuality.LOW

        # Invalid POI (fails validation)
        invalid_poi = EnhancedPOIInfo(
            id="bi03",
            name="테스트역",
            lat=37.5665,
            lng=126.9780,
            description="지하철역",
            category=1,
        )
        assert invalid_poi.data_quality == DataQuality.INVALID
