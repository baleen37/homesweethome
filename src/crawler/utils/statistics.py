"""Statistics calculation utilities for real estate transaction data.

This module provides functions to calculate various statistics from transaction data
including deal counts, average prices, and recent transaction information.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


def calculate_statistics_from_transactions(
    complex_data: Dict[str, Any],
    transactions: List[Dict[str, Any]],
    current_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Calculate statistics from transaction data and merge with complex data.

    Args:
        complex_data: Basic complex information (complex_id, complex_name, etc.)
        transactions: List of transaction records for this complex
        current_date: Reference date for calculations (defaults to today)

    Returns:
        Complex data merged with calculated statistics fields
    """
    if current_date is None:
        current_date = datetime.now()

    # Filter out deleted transactions
    active_transactions = [
        t for t in transactions
        if not t.get("is_delete", False)
    ]

    # Calculate statistics
    one_year_ago = current_date - timedelta(days=365)

    # Initialize all statistics with default values
    stats: dict[str, Any] = {
        "total_transaction_count": len(active_transactions),
        "latest_deal_price": 0,
        "latest_deal_date": "",
        "avg_deal_price_1year": 0,
        "deal_count_1year": 0,
        "lease_count_1year": 0,
        "rent_count_1year": 0,
    }

    if not active_transactions:
        # No transactions, return complex data with default statistics
        return {**complex_data, **stats}

    # Find latest transaction (by date)
    latest_transaction = _find_latest_transaction(active_transactions)
    if latest_transaction:
        stats["latest_deal_date"] = latest_transaction.get("trade_date", "")

        # Latest deal price depends on trade type
        if latest_transaction.get("trade_type") == "A1":  # 매매
            deal_price = latest_transaction.get("deal_price", 0)
            try:
                stats["latest_deal_price"] = int(deal_price) if deal_price else 0
            except (ValueError, TypeError):
                stats["latest_deal_price"] = 0
        # For lease/rent, we don't fill latest_deal_price (keep as 0)

    # Calculate statistics for the last year
    recent_transactions = _filter_transactions_by_date(active_transactions, one_year_ago, current_date)

    if recent_transactions:
        # Count by trade type
        for transaction in recent_transactions:
            trade_type = transaction.get("trade_type", "")
            if trade_type == "A1":  # 매매
                stats["deal_count_1year"] += 1
            elif trade_type == "B1":  # 전세
                stats["lease_count_1year"] += 1
            elif trade_type == "B2":  # 월세
                stats["rent_count_1year"] += 1

        # Calculate average deal price for the last year (only for 매매)
        deal_prices = []
        for t in recent_transactions:
            if t.get("trade_type") == "A1":
                deal_price = t.get("deal_price", 0)
                # Convert to int if it's a string
                try:
                    deal_price_int = int(deal_price) if deal_price else 0
                except (ValueError, TypeError):
                    deal_price_int = 0
                if deal_price_int > 0:
                    deal_prices.append(deal_price_int)

        if deal_prices:
            stats["avg_deal_price_1year"] = sum(deal_prices) // len(deal_prices)

    # Merge complex data with statistics
    return {**complex_data, **stats}


def _find_latest_transaction(transactions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find the most recent transaction by trade_date.

    Args:
        transactions: List of transaction records

    Returns:
        The latest transaction record or None if no transactions
    """
    if not transactions:
        return None

    # Sort by trade_date (format: YYYY-MM-DD)
    def date_key(transaction: Dict[str, Any]) -> datetime:
        trade_date_str = transaction.get("trade_date", "")
        try:
            return datetime.strptime(trade_date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            # Invalid date, treat as oldest
            return datetime.min

    return max(transactions, key=date_key)


def _filter_transactions_by_date(
    transactions: List[Dict[str, Any]],
    start_date: datetime,
    end_date: datetime,
) -> List[Dict[str, Any]]:
    """Filter transactions within the specified date range.

    Args:
        transactions: List of transaction records
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        List of transactions within the date range
    """
    filtered = []

    for transaction in transactions:
        trade_date_str = transaction.get("trade_date", "")
        try:
            trade_date = datetime.strptime(trade_date_str, "%Y-%m-%d")
            if start_date <= trade_date <= end_date:
                filtered.append(transaction)
        except (ValueError, TypeError):
            # Invalid date format, skip
            continue

    return filtered


def normalize_complex_data(
    complex_data: Dict[str, Any],
    statistics_fields: List[str],
) -> Dict[str, Any]:
    """Normalize complex data to ensure all fields are present with proper types.

    Args:
        complex_data: Raw complex data
        statistics_fields: List of statistics field names

    Returns:
        Normalized complex data with all fields present
    """
    normalized = complex_data.copy()

    # Ensure all statistics fields are present with proper defaults
    for field in statistics_fields:
        if field not in normalized:
            if field in ["latest_deal_date"]:
                normalized[field] = ""
            else:
                # For all numeric fields
                normalized[field] = 0

    # Convert numeric fields to integers
    numeric_fields = [
        "total_transaction_count",
        "latest_deal_price",
        "avg_deal_price_1year",
        "deal_count_1year",
        "lease_count_1year",
        "rent_count_1year",
    ]

    for field in numeric_fields:
        if field in normalized:
            try:
                value = normalized[field]
                if isinstance(value, str) and value.strip() == "":
                    normalized[field] = 0
                else:
                    normalized[field] = int(value)
            except (ValueError, TypeError):
                normalized[field] = 0

    return normalized


# List of all statistics fields for complexes.csv
STATISTICS_FIELDS = [
    "total_transaction_count",
    "latest_deal_price",
    "latest_deal_date",
    "avg_deal_price_1year",
    "deal_count_1year",
    "lease_count_1year",
    "rent_count_1year",
]

# All fields for complexes.csv (basic + detail + statistics)
COMPLEXES_CSV_FIELDNAMES = [
    # Basic fields (현재 구현)
    "complex_id",
    "complex_name",
    "real_estate_type",
    "completion_year_month",
    "total_dong_count",
    "total_household_count",
    "min_area",
    "max_area",
    "deal_count",
    "lease_count",
    "rent_count",
    # Additional fields (상세 정보)
    "pyeong_types",
    "fetched_at",
    # Statistics fields (거래내역 통계)
    *STATISTICS_FIELDS,
]