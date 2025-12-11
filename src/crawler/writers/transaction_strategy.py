"""Transaction data transformation strategy.

This module provides TransactionDataTransformationStrategy class for
normalizing transaction data for CSV output.
"""

from typing import Any, Dict, List

from crawler.writers.data_transformation_strategy import (
    BaseDataTransformationStrategy,
    DataTransformationStrategy,
)


class TransactionDataTransformationStrategy(BaseDataTransformationStrategy):
    """Strategy for transforming transaction data.

    Handles normalization of transaction records including:
    - Boolean field handling (is_delete, is_renew)
    - Numeric field parsing (floor, prices)
    - Date parsing
    - Field mapping and ordering
    """

    # Standard transaction field names
    FIELDNAMES = [
        "complex_id",
        "complex_name",
        "pyeong_type_number",
        "pyeong_name",
        "trade_type",
        "trade_type_name",
        "trade_date",
        "trade_year",
        "floor",
        "deal_price",
        "deposit",
        "monthly_rent",
        "trade_category",
        "is_delete",
        "is_renew",
        "gu_code",
        "dong_code",
        "gu_name",
        "dong_name",
    ]

    def transform(self, row: Dict[str, Any], fieldnames: List[str]) -> Dict[str, Any]:
        """Transform transaction data row.

        Args:
            row: Raw transaction data
            fieldnames: Expected output field names

        Returns:
            Transformed transaction data
        """
        # Apply common normalization
        normalized = self._normalize_common_fields(row)

        # Handle boolean fields specifically
        for field in ["is_delete", "is_renew"]:
            value = row.get(field, "")
            if isinstance(value, bool):
                normalized[field] = value
            elif isinstance(value, str):
                normalized[field] = value.lower() == "true"
            elif isinstance(value, int) and value in (0, 1):
                normalized[field] = bool(value)
            else:
                normalized[field] = False

        # Handle numeric fields
        for field in ["floor", "deal_price", "deposit", "monthly_rent", "pyeong_type_number"]:
            try:
                value = row.get(field, "")
                # Handle comma-separated numbers
                if isinstance(value, str):
                    value = value.replace(",", "")
                normalized[field] = int(value) if value != "" else 0
            except (ValueError, TypeError):
                normalized[field] = 0

        # Parse trade year if trade_date exists
        if normalized.get("trade_date"):
            _, trade_year = self._parse_date(str(normalized["trade_date"]))
            normalized["trade_year"] = trade_year

        # Filter and order by fieldnames
        result = {}
        for field in fieldnames or self.FIELDNAMES:
            if field in ["is_delete", "is_renew"]:
                # Keep boolean fields as boolean
                result[field] = normalized.get(field, False)
            else:
                # Convert other fields to string
                value = normalized.get(field, "")
                result[field] = str(value) if value is not None else ""

        return result

    def get_fieldnames(self) -> List[str]:
        """Get standard transaction field names."""
        return self.FIELDNAMES.copy()


class GenericTransactionStrategy(DataTransformationStrategy):
    """Generic transaction strategy using Protocol interface.

    Alternative implementation that doesn't inherit from base class.
    """

    def __init__(self):
        self._fieldnames = TransactionDataTransformationStrategy.FIELDNAMES

    def transform(self, row: Dict[str, Any], fieldnames: List[str]) -> Dict[str, Any]:
        """Transform using delegation to base strategy."""
        strategy = TransactionDataTransformationStrategy()
        return strategy.transform(row, fieldnames or self._fieldnames)

    def get_fieldnames(self) -> List[str]:
        """Get field names."""
        return self._fieldnames.copy()
