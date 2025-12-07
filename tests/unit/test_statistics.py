"""Tests for statistics calculation utilities."""

from datetime import datetime
from typing import Any

from crawler.utils.statistics import (
    _filter_transactions_by_date,
    _find_latest_transaction,
    calculate_statistics_from_transactions,
    normalize_complex_data,
)


class TestStatisticsCalculation:
    """Tests for statistics calculation from transaction data."""

    def test_calculate_statistics_with_empty_transactions(self) -> None:
        """Test statistics calculation with no transactions."""
        complex_data = {
            "complex_id": "111515",
            "complex_name": "헬리오시티",
        }
        transactions: list[dict[str, Any]] = []

        result = calculate_statistics_from_transactions(complex_data, transactions)

        # Check that all statistics fields are present with defaults
        assert result["total_transaction_count"] == 0
        assert result["latest_deal_price"] == 0
        assert result["latest_deal_date"] == ""
        assert result["avg_deal_price_1year"] == 0
        assert result["deal_count_1year"] == 0
        assert result["lease_count_1year"] == 0
        assert result["rent_count_1year"] == 0

        # Check that original complex data is preserved
        assert result["complex_id"] == "111515"
        assert result["complex_name"] == "헬리오시티"

    def test_calculate_statistics_with_sample_transactions(self) -> None:
        """Test statistics calculation with sample transaction data."""
        complex_data = {
            "complex_id": "111515",
            "complex_name": "헬리오시티",
        }

        # Sample transactions from different dates and types
        transactions = [
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
            {
                "complex_id": "111515",
                "trade_type": "A1",  # 매매 (older)
                "trade_date": "2024-06-15",
                "deal_price": 1600000000,
                "is_delete": False,
            },
            {
                "complex_id": "111515",
                "trade_type": "A1",  # 매매 (deleted)
                "trade_date": "2025-11-20",
                "deal_price": 1750000000,
                "is_delete": True,  # Should be ignored
            },
        ]

        # Use a fixed current date for predictable results
        current_date = datetime(2025, 12, 6)
        result = calculate_statistics_from_transactions(complex_data, transactions, current_date)

        # Check total transaction count (excluding deleted)
        assert result["total_transaction_count"] == 4

        # Check latest transaction info
        assert result["latest_deal_date"] == "2025-11-14"
        assert result["latest_deal_price"] == 1700000000  # Latest non-deleted deal

        # Check last year statistics (from 2024-12-06 to 2025-12-06)
        assert result["deal_count_1year"] == 1  # Only one 매매 in last year
        assert result["lease_count_1year"] == 1
        assert result["rent_count_1year"] == 1

        # Check average deal price for last year
        assert result["avg_deal_price_1year"] == 1700000000

    def test_calculate_statistics_with_only_old_transactions(self) -> None:
        """Test statistics when all transactions are older than 1 year."""
        complex_data = {
            "complex_id": "111515",
            "complex_name": "헬리오시티",
        }

        # All transactions are older than 1 year
        transactions = [
            {
                "complex_id": "111515",
                "trade_type": "A1",
                "trade_date": "2023-11-14",
                "deal_price": 1500000000,
                "is_delete": False,
            },
            {
                "complex_id": "111515",
                "trade_type": "B1",
                "trade_date": "2023-10-20",
                "deal_price": 0,
                "deposit": 700000000,
                "is_delete": False,
            },
        ]

        current_date = datetime(2025, 12, 6)
        result = calculate_statistics_from_transactions(complex_data, transactions, current_date)

        # Still has total count
        assert result["total_transaction_count"] == 2

        # Latest transaction info
        assert result["latest_deal_date"] == "2023-11-14"
        assert result["latest_deal_price"] == 1500000000

        # But no transactions in last year
        assert result["avg_deal_price_1year"] == 0
        assert result["deal_count_1year"] == 0
        assert result["lease_count_1year"] == 0
        assert result["rent_count_1year"] == 0

    def test_find_latest_transaction(self) -> None:
        """Test finding the latest transaction by date."""
        transactions = [
            {"trade_date": "2025-10-20", "deal_price": 800000000},
            {"trade_date": "2025-11-14", "deal_price": 1700000000},
            {"trade_date": "2025-09-10", "deal_price": 100000000},
        ]

        latest = _find_latest_transaction(transactions)
        assert latest is not None
        assert latest["trade_date"] == "2025-11-14"
        assert latest["deal_price"] == 1700000000

    def test_find_latest_transaction_with_empty_list(self) -> None:
        """Test finding latest transaction with empty list."""
        latest = _find_latest_transaction([])
        assert latest is None

    def test_find_latest_transaction_with_invalid_dates(self) -> None:
        """Test finding latest transaction with some invalid dates."""
        transactions = [
            {"trade_date": "invalid-date", "deal_price": 800000000},
            {"trade_date": "2025-11-14", "deal_price": 1700000000},
            {"trade_date": "", "deal_price": 100000000},
        ]

        latest = _find_latest_transaction(transactions)
        assert latest is not None
        assert latest["trade_date"] == "2025-11-14"

    def test_filter_transactions_by_date(self) -> None:
        """Test filtering transactions within a date range."""
        transactions = [
            {"trade_date": "2025-09-10"},
            {"trade_date": "2025-10-20"},
            {"trade_date": "2025-11-14"},
            {"trade_date": "2024-11-30"},  # Outside range
            {"trade_date": "2025-12-07"},  # Outside range
            {"trade_date": "invalid-date"},  # Should be ignored
        ]

        start_date = datetime(2025, 9, 1)
        end_date = datetime(2025, 12, 6)

        filtered = _filter_transactions_by_date(transactions, start_date, end_date)

        # Should have 3 transactions within range
        assert len(filtered) == 3
        dates = [t["trade_date"] for t in filtered]
        assert "2025-09-10" in dates
        assert "2025-10-20" in dates
        assert "2025-11-14" in dates

    def test_normalize_complex_data(self) -> None:
        """Test normalizing complex data with statistics fields."""
        complex_data = {
            "complex_id": "111515",
            "complex_name": "헬리오시티",
            "total_transaction_count": "5",  # String that should be int
            "latest_deal_price": 1700000000,
            "avg_deal_price_1year": "",  # Empty string should be 0
            # Missing statistics fields should be added
        }

        statistics_fields = [
            "total_transaction_count",
            "latest_deal_price",
            "latest_deal_date",
            "avg_deal_price_1year",
            "deal_count_1year",
            "lease_count_1year",
            "rent_count_1year",
        ]

        normalized = normalize_complex_data(complex_data, statistics_fields)

        # Check that original fields are preserved
        assert normalized["complex_id"] == "111515"
        assert normalized["complex_name"] == "헬리오시티"

        # Check numeric conversions
        assert normalized["total_transaction_count"] == 5  # Converted from string
        assert normalized["latest_deal_price"] == 1700000000
        assert normalized["avg_deal_price_1year"] == 0  # Empty string converted to 0

        # Check that missing fields are added with defaults
        assert normalized["latest_deal_date"] == ""
        assert normalized["deal_count_1year"] == 0
        assert normalized["lease_count_1year"] == 0
        assert normalized["rent_count_1year"] == 0

    def test_average_calculation_with_multiple_deals(self) -> None:
        """Test average price calculation with multiple deals in last year."""
        complex_data = {"complex_id": "111515"}

        # Multiple 매매 transactions in last year
        transactions = [
            {
                "trade_type": "A1",
                "trade_date": "2025-01-15",
                "deal_price": 1500000000,
                "is_delete": False,
            },
            {
                "trade_type": "A1",
                "trade_date": "2025-06-15",
                "deal_price": 1600000000,
                "is_delete": False,
            },
            {
                "trade_type": "A1",
                "trade_date": "2025-11-15",
                "deal_price": 1700000000,
                "is_delete": False,
            },
            # Non-매매 transactions (should not affect average)
            {
                "trade_type": "B1",
                "trade_date": "2025-10-15",
                "deal_price": 0,
                "deposit": 800000000,
                "is_delete": False,
            },
        ]

        current_date = datetime(2025, 12, 6)
        result = calculate_statistics_from_transactions(complex_data, transactions, current_date)

        # Check average calculation: (1500 + 1600 + 1700) / 3 = 1600
        assert result["avg_deal_price_1year"] == 1600000000
        assert result["deal_count_1year"] == 3

    def test_lease_and_rent_latest_deal_price(self) -> None:
        """Test that latest_deal_price is 0 for latest lease/rent transactions."""
        complex_data = {"complex_id": "111515"}

        # Latest transaction is 전세
        transactions = [
            {
                "trade_type": "A1",
                "trade_date": "2025-10-15",
                "deal_price": 1600000000,
                "is_delete": False,
            },
            {
                "trade_type": "B1",  # 전세
                "trade_date": "2025-11-15",  # Latest date
                "deal_price": 0,
                "deposit": 800000000,
                "is_delete": False,
            },
        ]

        current_date = datetime(2025, 12, 6)
        result = calculate_statistics_from_transactions(complex_data, transactions, current_date)

        # Latest deal price should be 0 since latest transaction is not 매매
        assert result["latest_deal_price"] == 0
        assert result["latest_deal_date"] == "2025-11-15"
