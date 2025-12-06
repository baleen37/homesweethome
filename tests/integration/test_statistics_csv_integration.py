"""Integration test for statistics calculation and CSV writing."""

import tempfile
from datetime import datetime
from pathlib import Path

from crawler.writers.complexes_csv_writer import ComplexesCSVWriter
from crawler.utils.statistics import calculate_statistics_from_transactions


def test_statistics_and_csv_integration() -> None:
    """Test that statistics calculation integrates correctly with CSV writing."""
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_path = Path(tmp_dir) / "complexes.csv"
        writer = ComplexesCSVWriter(csv_path)

        # Sample complex data
        complex_data = {
            "complex_id": "111515",
            "complex_name": "헬리오시티",
            "real_estate_type": "아파트",
            "completion_year_month": "2021-12",
            "total_dong_count": 8,
            "total_household_count": 1247,
            "min_area": 59.91,
            "max_area": 114.88,
            "deal_count": 10,
            "lease_count": 5,
            "rent_count": 3,
        }

        # Sample transaction data spanning multiple years
        transactions = [
            # Recent transactions (within last year)
            {
                "complex_id": "111515",
                "trade_type": "A1",  # 매매
                "trade_date": "2025-11-14",
                "deal_price": 1700000000,
                "is_delete": False,
            },
            {
                "complex_id": "111515",
                "trade_type": "B1",  # 전세
                "trade_date": "2025-10-20",
                "deal_price": 0,
                "deposit": 800000000,
                "is_delete": False,
            },
            {
                "complex_id": "111515",
                "trade_type": "B2",  # 월세
                "trade_date": "2025-09-10",
                "deal_price": 0,
                "deposit": 100000000,
                "monthly_rent": 2000000,
                "is_delete": False,
            },
            # Older transactions (more than 1 year)
            {
                "complex_id": "111515",
                "trade_type": "A1",
                "trade_date": "2023-11-14",
                "deal_price": 1500000000,
                "is_delete": False,
            },
            {
                "complex_id": "111515",
                "trade_type": "A1",
                "trade_date": "2024-06-15",
                "deal_price": 1600000000,
                "is_delete": False,
            },
            # Deleted transaction (should be ignored)
            {
                "complex_id": "111515",
                "trade_type": "A1",
                "trade_date": "2025-11-20",
                "deal_price": 1750000000,
                "is_delete": True,
            },
        ]

        # Calculate statistics
        current_date = datetime(2025, 12, 6)
        complex_with_stats = calculate_statistics_from_transactions(
            complex_data, transactions, current_date
        )

        # Write to CSV
        writer.write([complex_with_stats])

        # Verify CSV was created
        assert csv_path.exists()

        # Read and verify CSV content
        import csv

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # Should have exactly one row
            assert len(rows) == 1

            row = rows[0]

            # Verify basic fields are preserved
            assert row["complex_id"] == "111515"
            assert row["complex_name"] == "헬리오시티"
            assert row["real_estate_type"] == "아파트"

            # Verify statistics fields are calculated correctly
            # Total transactions (excluding deleted)
            assert int(row["total_transaction_count"]) == 5

            # Latest transaction (should be the 2025-11-14 매매)
            assert row["latest_deal_date"] == "2025-11-14"
            assert int(row["latest_deal_price"]) == 1700000000

            # Last year statistics (from 2024-12-06 to 2025-12-06)
            assert int(row["deal_count_1year"]) == 1  # One 매매 transaction
            assert int(row["lease_count_1year"]) == 1  # One 전세 transaction
            assert int(row["rent_count_1year"]) == 1  # One 월세 transaction

            # Average deal price for last year (only 매매 transactions)
            assert int(row["avg_deal_price_1year"]) == 1700000000

        # Test append_with_statistics method
        another_complex = {
            "complex_id": "222222",
            "complex_name": "테스트 단지",
        }
        another_transactions = [
            {
                "complex_id": "222222",
                "trade_type": "A1",
                "trade_date": "2025-11-01",
                "deal_price": 1200000000,
                "is_delete": False,
            }
        ]

        writer.append_with_statistics(another_complex, another_transactions)

        # Read CSV again to verify append
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # Should have two rows now
            assert len(rows) == 2

            # Check the second row
            row2 = rows[1]
            assert row2["complex_id"] == "222222"
            assert row2["complex_name"] == "테스트 단지"
            assert int(row2["total_transaction_count"]) == 1
            assert row2["latest_deal_date"] == "2025-11-01"
            assert int(row2["latest_deal_price"]) == 1200000000

    print("✅ Statistics and CSV integration test passed!")
