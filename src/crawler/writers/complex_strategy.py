"""Complex data transformation strategy.

This module provides ComplexDataTransformationStrategy class for
normalizing complex/apartment data for CSV output.
"""

from typing import Any, Dict, List

from crawler.writers.data_transformation_strategy import (
    BaseDataTransformationStrategy,
    DataTransformationStrategy,
)


class ComplexDataTransformationStrategy(BaseDataTransformationStrategy):
    """Strategy for transforming complex/apartment data.

    Handles normalization of complex records including:
    - Basic information (ID, name, type)
    - Building details (completion, household counts)
    - Statistics fields (deal counts, prices)
    - Field mapping and ordering
    """

    # Import fieldnames from statistics module
    FIELDNAMES = [
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
        "pyeong_types",
        "fetched_at",
        "total_transaction_count",
        "latest_deal_price",
        "latest_deal_date",
        "avg_deal_price_1year",
        "deal_count_1year",
        "lease_count_1year",
        "rent_count_1year",
    ]

    def transform(self, row: Dict[str, Any], fieldnames: List[str]) -> Dict[str, Any]:
        """Transform complex data row.

        Args:
            row: Raw complex data
            fieldnames: Expected output field names

        Returns:
            Transformed complex data
        """
        # Apply common normalization
        normalized = self._normalize_common_fields(row)

        # Handle specific fields
        self._handle_completion_year(normalized, row)
        self._handle_numeric_fields(normalized, row)
        self._handle_statistics_fields(normalized, row)

        # Filter and order by fieldnames
        target_fields = fieldnames or self.FIELDNAMES
        result = {}
        for field in target_fields:
            value = normalized.get(field, "")
            # Convert everything to string for CSV, but format numbers nicely
            if isinstance(value, float) and value.is_integer():
                # Convert float with .0 to integer string
                result[field] = str(int(value))
            else:
                result[field] = str(value) if value is not None else ""

        return result

    def get_fieldnames(self) -> List[str]:
        """Get standard complex field names."""
        return self.FIELDNAMES.copy()

    def _handle_completion_year(self, normalized: Dict[str, Any], row: Dict[str, Any]) -> None:
        """Handle completion year/month field."""
        if not normalized.get("completion_year_month"):
            # Try to construct from buildYear or similar fields
            build_year = row.get("buildYear") or row.get("completion_year")
            if build_year and str(build_year).isdigit() and len(str(build_year)) == 4:
                normalized["completion_year_month"] = f"{build_year}0101"
            else:
                normalized["completion_year_month"] = ""

    def _handle_numeric_fields(self, normalized: Dict[str, Any], row: Dict[str, Any]) -> None:
        """Handle numeric fields."""
        numeric_fields = [
            "total_dong_count",
            "total_household_count",
            "min_area",
            "max_area",
            "deal_count",
            "lease_count",
            "rent_count",
        ]

        for field in numeric_fields:
            try:
                value = row.get(field, "")
                normalized[field] = float(value) if value and str(value) != "" else 0
            except (ValueError, TypeError):
                normalized[field] = 0

    def _handle_statistics_fields(self, normalized: Dict[str, Any], row: Dict[str, Any]) -> None:
        """Handle statistics fields."""
        statistics_fields = [
            "total_transaction_count",
            "latest_deal_price",
            "avg_deal_price_1year",
            "deal_count_1year",
            "lease_count_1year",
            "rent_count_1year",
        ]

        for field in statistics_fields:
            try:
                value = row.get(field, "")
                normalized[field] = int(value) if value and str(value) != "" else 0
            except (ValueError, TypeError):
                normalized[field] = 0

        # Handle date fields
        for field in ["latest_deal_date", "fetched_at"]:
            if row.get(field):
                normalized[field] = str(row[field])
            else:
                normalized[field] = ""


class GenericComplexStrategy(DataTransformationStrategy):
    """Generic complex strategy using Protocol interface.

    Alternative implementation that doesn't inherit from base class.
    """

    def __init__(self):
        self._fieldnames = ComplexDataTransformationStrategy.FIELDNAMES

    def transform(self, row: Dict[str, Any], fieldnames: List[str]) -> Dict[str, Any]:
        """Transform using delegation to base strategy."""
        strategy = ComplexDataTransformationStrategy()
        return strategy.transform(row, fieldnames or self._fieldnames)

    def get_fieldnames(self) -> List[str]:
        """Get field names."""
        return self._fieldnames.copy()
