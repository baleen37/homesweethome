"""Integration tests for hierarchical crawling functionality.

These tests make real API calls to verify the complete hierarchical crawling workflow.
"""

# Import test setup to configure path and mocks

import json
import pytest

from crawler.coordinator import CrawlCoordinator
from crawler.config import CrawlerConfig
from crawler.crawlers.hogangnono import HogangnonoCrawler


@pytest.mark.integration
@pytest.mark.slow
def test_hierarchical_crawling_single_district(tmp_path):
    """Test hierarchical crawling for a single district with real API calls."""
    # Setup
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    config = CrawlerConfig(
        base_url="https://hogangnono.com",
        output_dir=str(output_dir),
        request_interval=2.0,  # Reduced for testing
        max_retries=2,
        timeout=30,
    )

    # Use 강남구 (11680) for testing - it's a well-known district
    district_code = "11680"
    district_name = "강남구"

    # Create coordinator
    coordinator = CrawlCoordinator(
        config=config,
        districts=[{"code": district_code, "name": district_name}],
        output_dir=output_dir,
        resume=False,
    )

    # Run hierarchical crawling for just one district
    coordinator.crawl_all()

    # Verify output files
    complexes_file = output_dir / "complexes.csv"
    transactions_file = output_dir / "transactions.csv"
    checkpoint_file = output_dir / "checkpoint.json"

    assert complexes_file.exists(), "complexes.csv should be created"
    assert transactions_file.exists(), "transactions.csv should be created"
    assert checkpoint_file.exists(), "checkpoint.json should be created"

    # Verify data in files
    with open(complexes_file, "r", encoding="utf-8") as f:
        complexes_content = f.read()
        # Skip header and check if we have data
        lines = complexes_content.strip().split("\n")
        assert len(lines) > 1, "complexes.csv should contain data rows"
        # Verify header structure
        header = lines[0]
        expected_columns = ["complex_id", "name", "address", "build_year", "households", "dongs"]
        for col in expected_columns:
            assert col in header, f"Header should contain {col} column"

    with open(transactions_file, "r", encoding="utf-8") as f:
        transactions_content = f.read()
        lines = transactions_content.strip().split("\n")
        assert len(lines) > 1, "transactions.csv should contain data rows"
        # Verify header structure
        header = lines[0]
        expected_columns = [
            "transaction_id",
            "complex_id",
            "complex_name",
            "exclusive_area",
            "floor",
            "price",
            "contract_date",
            "listing_type",
            "req_type",
        ]
        for col in expected_columns:
            assert col in header, f"Header should contain {col} column"

    # Verify checkpoint contains progress
    with open(checkpoint_file, "r", encoding="utf-8") as f:
        checkpoint = json.load(f)
        assert "completed_dongs" in checkpoint, "Checkpoint should track completed dongs"
        assert "failed_dongs" in checkpoint, "Checkpoint should track failed dongs"
        assert "progress" in checkpoint, "Checkpoint should track progress"

        # Check if 강남구 is marked as completed
        if checkpoint["completed_dongs"]:
            # At least some dongs should be completed
            assert len(checkpoint["completed_dongs"]) > 0, "Some dongs should be completed"


@pytest.mark.integration
@pytest.mark.slow
def test_crawl_coordinator_with_real_crawler(tmp_path):
    """Test CrawlCoordinator with real HogangnonoCrawler for API interaction."""
    # Setup
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    config = CrawlerConfig(
        base_url="https://hogangnono.com",
        output_dir=str(output_dir),
        request_interval=1.5,  # Reduced for testing
        max_retries=2,
        timeout=30,
    )

    # Use a smaller district for faster testing
    district_code = "11680"  # 강남구

    # Create crawler directly
    crawler = HogangnonoCrawler(config)

    # Test the first step: fetching dongs for a district
    dongs = crawler.fetch_dongs(district_code)
    assert len(dongs) > 0, "Should fetch at least one dong for 강남구"

    # Verify dong structure
    first_dong = dongs[0]
    assert "dongCode" in first_dong, "Dong should have dongCode"
    assert "dongName" in first_dong, "Dong should have dongName"

    # Test fetching complexes for the first dong
    first_dong_code = first_dong["dongCode"]
    complexes = crawler.fetch_complexes(first_dong_code)

    # We might not get complexes for all dongs, but the API call should succeed
    # without raising an exception
    assert isinstance(complexes, list), "Should return a list of complexes"

    # If we have complexes, verify their structure
    if complexes:
        first_complex = complexes[0]
        assert "id" in first_complex, "Complex should have an id"
        assert "name" in first_complex, "Complex should have a name"


@pytest.mark.integration
def test_writers_with_real_data(tmp_path):
    """Test CSV writers with real data structure from API."""
    # Setup
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Create writer
    from crawler.writers import HogangnonoCSVWriter

    csv_writer = HogangnonoCSVWriter(str(output_dir))

    # Mock real data structure (based on API responses)
    test_complexes = [
        {
            "complex_id": "C001",
            "complex_name": "테스트단지",
            "real_estate_type": "아파트",
            "completion_year_month": "202001",
            "total_dong_count": 3,
            "total_household_count": 500,
            "min_area": 84.5,
            "max_area": 84.5,
            "deal_count": 1,
            "lease_count": 0,
            "rent_count": 0,
            "pyeong_types": "34평",
            "fetched_at": "2024-01-15 12:00:00",
            "total_transaction_count": 1,
            "latest_deal_price": 150000,
            "latest_deal_date": "2024-01-15",
            "avg_deal_price_1year": 150000,
            "deal_count_1year": 1,
            "lease_count_1year": 0,
            "rent_count_1year": 0,
        }
    ]

    test_transactions = [
        {
            "complex_id": "C001",
            "complex_name": "테스트단지",
            "pyeong_type_number": "1",
            "pyeong_name": "34평",
            "trade_type": "A1",
            "trade_type_name": "아파트 매매",
            "trade_date": "2024-01-15",
            "trade_year": "2024",
            "floor": "5",
            "deal_price": 150000,
            "deposit": 0,
            "monthly_rent": 0,
            "trade_category": "매매",
            "is_delete": "N",
            "is_renew": "N",
            "gu_code": "11680",
            "dong_code": "11680500",
            "gu_name": "강남구",
            "dong_name": "역삼동",
        }
    ]

    # Test writing
    csv_writer.write_complexes(test_complexes)
    csv_writer.write_transactions(test_transactions)

    # Verify files
    complexes_file = output_dir / "complexes.csv"
    transactions_file = output_dir / "transactions.csv"

    assert complexes_file.exists(), "Complexes CSV should be created"
    assert transactions_file.exists(), "Transactions CSV should be created"

    # Verify content
    with open(complexes_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert "테스트단지" in content, "Complex name should be in file"
        assert "C001" in content, "Complex ID should be in file"

    with open(transactions_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert "C001" in content, "Complex ID should be in file"
        assert "150000" in content, "Price should be in file"


@pytest.mark.integration
def test_checkpoint_system(tmp_path):
    """Test checkpoint system with real directory progress."""
    # Setup
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    config = CrawlerConfig(
        base_url="https://hogangnono.com",
        output_dir=str(output_dir),
        request_interval=1.0,
        max_retries=1,
        timeout=15,
    )

    # Create coordinator
    coordinator = CrawlCoordinator(
        config=config,
        districts=[{"code": "11680", "name": "강남구"}],
        output_dir=output_dir,
        resume=False,
    )

    # Save initial state
    coordinator.checkpoint_manager.save_checkpoint(
        completed_dongs=[],
        failed_dongs=[],
        progress={"current_district": "강남구", "completed_districts": []},
    )

    # Verify checkpoint exists
    checkpoint_file = output_dir / "checkpoint.json"
    assert checkpoint_file.exists(), "Checkpoint file should be created"

    # Load and verify content
    checkpoint = coordinator.checkpoint_manager.load_checkpoint()
    assert "completed_dongs" in checkpoint
    assert "failed_dongs" in checkpoint
    assert "progress" in checkpoint
    assert checkpoint["progress"]["current_district"] == "강남구"
