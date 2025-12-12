"""Transaction CSV writer for real estate transaction data.

This module provides TransactionCSVWriter class that handles writing
transaction data to CSV format using appropriate transformation
strategies.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from crawler.writers.unified_csv_writer import UnifiedCSVWriter, WriteConfig
from crawler.writers.transaction_strategy import TransactionDataTransformationStrategy
from crawler.writers.csv_header_standard import CSVType


class TransactionCSVWriter(UnifiedCSVWriter):
    """CSV writer for transaction data.

    This writer specializes in handling transaction information including:
    - Deal prices and dates
    - Property details (floor, area)
    - Transaction types
    - Boolean flags
    """

    def __init__(
        self,
        output_path: Path,
        config: Optional[WriteConfig] = None,
        use_korean_fields: bool = True,
    ):
        """Initialize TransactionCSVWriter.

        Args:
            output_path: Path to the output CSV file
            config: Write configuration
            use_korean_fields: Whether to use Korean field names
        """
        # Create appropriate strategy
        if use_korean_fields:
            strategy = TransactionDataTransformationStrategy()
        else:
            # Use English field names strategy
            strategy = GenericTransactionStrategy()

        super().__init__(
            output_path=output_path,
            strategy=strategy,
            csv_type=CSVType.TRANSACTIONS,
            config=config,
        )

    def write_from_complex_data(
        self,
        complex_data: Dict[str, Any],
        transactions: List[Dict[str, Any]],
    ) -> None:
        """Write transactions extracted from complex data.

        Args:
            complex_data: Parent complex information
            transactions: List of transaction records
        """
        # Add complex info to each transaction if missing
        enriched_transactions = []
        for transaction in transactions:
            enriched = transaction.copy()

            # Add missing complex information
            if not enriched.get("complex_id"):
                enriched["complex_id"] = complex_data.get("id", "")
            if not enriched.get("complex_name"):
                enriched["complex_name"] = complex_data.get("name", "")

            enriched_transactions.append(enriched)

        # Write all transactions
        self.write(enriched_transactions)

    def write_trade_summary(
        self,
        complex_id: str,
        complex_name: str,
        trade_summary: Dict[str, Any],
    ) -> None:
        """Write a trade summary as a transaction record.

        Args:
            complex_id: ID of the complex
            complex_name: Name of the complex
            trade_summary: Trade summary information
        """
        # Create a transaction record from summary
        transaction = {
            "complex_id": complex_id,
            "complex_name": complex_name,
            "pyeong_type_number": trade_summary.get("pyeong_type", 0),
            "pyeong_name": trade_summary.get("pyeong_name", ""),
            "trade_type": trade_summary.get("trade_type", ""),
            "trade_type_name": trade_summary.get("trade_type_name", ""),
            "trade_date": trade_summary.get("latest_date", ""),
            "trade_year": self._extract_year(trade_summary.get("latest_date", "")),
            "floor": trade_summary.get("avg_floor", 0),
            "deal_price": trade_summary.get("avg_price", 0),
            "deposit": trade_summary.get("avg_deposit", 0),
            "monthly_rent": trade_summary.get("avg_monthly_rent", 0),
            "trade_category": "요약정보",
            "is_delete": False,
            "is_renew": False,
        }

        self.append([transaction])

    def _extract_year(self, date_str: str) -> int:
        """Extract year from date string."""
        if not date_str:
            return datetime.now().year

        try:
            # Try to extract 4-digit year from start of string
            year_part = date_str[:4]
            if year_part.isdigit():
                return int(year_part)
        except (ValueError, IndexError):
            pass

        return datetime.now().year

    def filter_by_date_range(
        self,
        start_date: str,
        end_date: str,
        data: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Filter transactions by date range.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            data: List of transaction data

        Returns:
            Filtered list of transactions
        """
        from datetime import datetime

        filtered = []
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        for transaction in data:
            trade_date = transaction.get("trade_date", "")
            if not trade_date:
                continue

            try:
                # Parse date (try various formats)
                date_str = trade_date.split()[0]  # Take only date part
                date_str = date_str.replace(".", "-")  # Normalize separator
                trade_dt = datetime.strptime(date_str, "%Y-%m-%d")

                if start_dt <= trade_dt <= end_dt:
                    filtered.append(transaction)
            except ValueError:
                # Skip invalid dates
                continue

        return filtered

    def get_price_statistics(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate price statistics from transaction data.

        Args:
            data: List of transaction data

        Returns:
            Dictionary with price statistics
        """
        if not data:
            return {
                "count": 0,
                "min_price": 0,
                "max_price": 0,
                "avg_price": 0,
                "total_value": 0,
            }

        prices = []
        for transaction in data:
            price = transaction.get("deal_price", 0) or transaction.get("deposit", 0)
            if price:
                try:
                    prices.append(float(price))
                except (ValueError, TypeError):
                    continue

        if not prices:
            return {
                "count": 0,
                "min_price": 0,
                "max_price": 0,
                "avg_price": 0,
                "total_value": 0,
            }

        return {
            "count": len(prices),
            "min_price": min(prices),
            "max_price": max(prices),
            "avg_price": sum(prices) / len(prices),
            "total_value": sum(prices),
        }


class GenericTransactionStrategy:
    """Generic strategy for transaction data with English field names."""

    def transform(self, row: Dict[str, Any], fieldnames: List[str]) -> Dict[str, Any]:
        """Transform transaction data using fieldnames from row."""
        # Simple pass-through transformation
        result = {}

        for field in fieldnames:
            value = row.get(field, "")

            if value is None:
                result[field] = ""
            elif isinstance(value, bool):
                result[field] = str(value).lower()
            elif isinstance(value, (int, float)):
                result[field] = str(value)
            else:
                result[field] = str(value)

        return result

    def get_fieldnames(self) -> List[str]:
        """Get field names from transactions header standard."""
        from crawler.writers.csv_header_standard import HeaderStandardRegistry

        return HeaderStandardRegistry.get_fieldnames(CSVType.TRANSACTIONS)
