"""Integration tests for WorkingHogangnonoCrawler with real API calls.

These tests make actual HTTP requests to Hogangnono APIs.
They should be run selectively to avoid rate limiting.
"""

import pytest
import json

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


@pytest.mark.integration
class TestWorkingHogangnonoRealAPI:
    """Integration tests with real API calls."""

    def test_fetch_popular_apartments_real(self, crawler):
        """Test fetching real popular apartments data."""
        # Make actual API call
        data = crawler.fetch_popular_apartments()

        # Verify response structure
        assert "status" in data
        assert "data" in data
        assert data["status"] == "success"
        assert "rolling" in data["data"]

        # Verify data content
        apartments = data["data"]["rolling"]
        assert len(apartments) > 0

        # Check first apartment structure
        first = apartments[0]
        required_fields = ["sidoName", "sigunguName", "dongName", "rank", "visitor", "name"]
        for field in required_fields:
            assert field in first, f"Missing field: {field}"

        # Print sample data for manual verification
        print("\n=== Popular Apartments Sample ===")
        print(json.dumps(apartments[:3], indent=2, ensure_ascii=False))

    def test_fetch_pois_in_area_real(self, crawler):
        """Test fetching real POI data for a specific area."""
        # Use Gangnam station area
        bbox = {
            "startX": 127.0,  # West
            "endX": 127.1,  # East
            "startY": 37.5,  # South
            "endY": 37.6,  # North
        }

        # Make actual API call
        data = crawler.fetch_pois_in_area(bbox)

        # Verify response structure
        assert "status" in data
        assert "data" in data
        assert data["status"] == "success"

        # Verify data content
        pois = data["data"]
        # Note: POIs might be empty for some areas
        print(f"\n=== Found {len(pois)} POIs in area ===")

        if pois:
            # Check first POI structure
            first = pois[0]
            required_fields = ["id", "category", "name", "description", "lat", "lng"]
            for field in required_fields:
                assert field in first, f"Missing field: {field}"

            # Print sample data
            print("\n=== POIs Sample ===")
            print(json.dumps(pois[:5], indent=2, ensure_ascii=False))

    def test_parse_to_csv_format_real_apartments(self, crawler):
        """Test CSV parsing with real apartment data."""
        # Fetch real data
        data = crawler.fetch_popular_apartments()

        # Parse to CSV format
        csv_rows = crawler.parse_to_csv_format(data, "apartments")

        # Verify
        assert len(csv_rows) > 0

        # Check CSV headers
        first_row = csv_rows[0]
        expected_headers = [
            "순위",
            "이전순위",
            "아파트명",
            "시도",
            "시군구",
            "동",
            "지역명",
            "방문자수",
            "랭킹타입",
            "상태",
            "hash",
        ]
        for header in expected_headers:
            assert header in first_row, f"Missing CSV header: {header}"

        # Print sample CSV data
        print("\n=== CSV Format Sample (Apartments) ===")
        for i, row in enumerate(csv_rows[:5]):
            print(f"Row {i + 1}: {json.dumps(row, ensure_ascii=False)}")

    def test_crawl_gangnam_area_integration(self, crawler):
        """Test complete crawling process for Gangnam area."""
        # This is a more comprehensive integration test
        results = crawler.crawl_gangnam_area()

        # Verify structure
        assert "apartments" in results
        assert "pois" in results

        # Print results summary
        print("\n=== Gangnam Area Crawling Results ===")
        print(f"Popular apartments: {len(results['apartments'])}")
        print(f"POIs in Gangnam: {len(results['pois'])}")

        # Print sample apartment data
        if results["apartments"]:
            print("\n=== Sample Popular Apartments ===")
            for i, apt in enumerate(results["apartments"][:3]):
                print(
                    f"{i + 1}. {apt['아파트명']} ({apt['시도']} {apt['시군구']} {apt['동']}) - 순위: {apt['순위']}"
                )

        # Print sample POI data
        if results["pois"]:
            print("\n=== Sample POIs ===")
            for i, poi in enumerate(results["pois"][:3]):
                print(f"{i + 1}. {poi['이름']} ({poi['설명']}) - 거리: {poi['거리(m)']}m")


if __name__ == "__main__":
    # Allow running this test directly
    pytest.main([__file__, "-v", "-s"])
