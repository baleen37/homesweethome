"""Complex CSV writer for apartment complex data.

This module provides ComplexCSVWriter class that handles writing
complex/apartment data to CSV format using appropriate transformation
strategies.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from crawler.writers.unified_csv_writer import UnifiedCSVWriter, WriteConfig
from crawler.writers.complex_strategy import ComplexDataTransformationStrategy
from crawler.writers.csv_header_standard import CSVType


class ComplexCSVWriter(UnifiedCSVWriter):
    """CSV writer for complex/apartment data.

    This writer specializes in handling complex information including:
    - Basic apartment information
    - Building details
    - Statistics
    - POI validation results
    """

    def __init__(
        self,
        output_path: Path,
        config: Optional[WriteConfig] = None,
        use_korean_fields: bool = True,
    ):
        """Initialize ComplexCSVWriter.

        Args:
            output_path: Path to the output CSV file
            config: Write configuration
            use_korean_fields: Whether to use Korean field names
        """
        # Create appropriate strategy
        if use_korean_fields:
            strategy = ComplexDataTransformationStrategy()
        else:
            # Use English field names strategy
            strategy = GenericComplexStrategy()

        super().__init__(
            output_path=output_path,
            strategy=strategy,
            csv_type=CSVType.COMPLEXES,
            config=config,
        )

    def write_with_statistics(
        self,
        complex_data: Dict[str, Any],
        transactions: List[Dict[str, Any]],
    ) -> None:
        """Write complex data with calculated statistics.

        Args:
            complex_data: Basic complex information
            transactions: List of transactions for this complex
        """
        # Calculate statistics from transactions
        complex_with_stats = self._calculate_statistics(complex_data, transactions)

        # Write using strategy
        fieldnames = self.get_fieldnames()
        if self._strategy:
            transformed = self._strategy.transform(complex_with_stats, fieldnames)
        else:
            transformed = self._normalize_row_legacy(complex_with_stats, fieldnames)

        # Write to file
        self.append([transformed])

    def _calculate_statistics(
        self, complex_data: Dict[str, Any], transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate statistics from transaction data.

        Args:
            complex_data: Basic complex information
            transactions: List of transaction records

        Returns:
            Complex data with added statistics
        """
        stats = complex_data.copy()

        if not transactions:
            # Set default values if no transactions
            stats.update(
                {
                    "total_transaction_count": 0,
                    "deal_count": 0,
                    "lease_count": 0,
                    "rent_count": 0,
                    "latest_deal_price": 0,
                    "latest_deal_date": "",
                    "avg_deal_price_1year": 0,
                    "deal_count_1year": 0,
                    "lease_count_1year": 0,
                    "rent_count_1year": 0,
                }
            )
            return stats

        # Calculate basic counts
        deal_prices = []
        lease_prices = []
        rent_prices = []
        current_year = datetime.now().year

        for transaction in transactions:
            trade_type = transaction.get("trade_type", "").lower()
            price = transaction.get("deal_price", 0) or transaction.get("deposit", 0)
            date_str = transaction.get("trade_date", "")

            try:
                # Extract year from date
                if date_str and len(date_str) >= 4:
                    transaction_year = int(date_str[:4])
                else:
                    transaction_year = current_year
            except (ValueError, TypeError):
                transaction_year = current_year

            # Count by type
            if trade_type == "매매" or trade_type == "sale":
                deal_prices.append(price)
                if transaction_year == current_year:
                    stats["deal_count_1year"] = stats.get("deal_count_1year", 0) + 1
            elif trade_type == "전세" or trade_type == "jeonse":
                lease_prices.append(price)
                if transaction_year == current_year:
                    stats["lease_count_1year"] = stats.get("lease_count_1year", 0) + 1
            elif trade_type == "월세" or trade_type == "monthly":
                rent_prices.append(price)
                if transaction_year == current_year:
                    stats["rent_count_1year"] = stats.get("rent_count_1year", 0) + 1

        # Set counts
        stats["deal_count"] = len(deal_prices)
        stats["lease_count"] = len(lease_prices)
        stats["rent_count"] = len(rent_prices)
        stats["total_transaction_count"] = len(transactions)

        # Calculate latest deal price and date
        if transactions:
            latest_transaction = max(transactions, key=lambda x: x.get("trade_date", ""))
            stats["latest_deal_price"] = latest_transaction.get("deal_price", 0)
            stats["latest_deal_date"] = latest_transaction.get("trade_date", "")

        # Calculate average deal price for current year
        if deal_prices:
            stats["avg_deal_price_1year"] = sum(deal_prices) // len(deal_prices)

        return stats


class GenericComplexStrategy:
    """Generic strategy for complex data with English field names."""

    def transform(self, row: Dict[str, Any], fieldnames: List[str]) -> Dict[str, Any]:
        """Transform complex data using fieldnames from row."""
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
        """Get field names from complexes header standard."""
        from crawler.writers.csv_header_standard import HeaderStandardRegistry

        return HeaderStandardRegistry.get_fieldnames(CSVType.COMPLEXES)
