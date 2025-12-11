"""Hogangnono-specific data transformation strategies.

This module provides strategy implementations for transforming Hogangnono
API data to Naver-compatible CSV format.
"""

from datetime import datetime
from typing import Any, Dict, List

from crawler.writers.data_transformation_strategy import (
    BaseDataTransformationStrategy,
    DataTransformationStrategy,
)


class HogangnonoComplexStrategy(BaseDataTransformationStrategy):
    """Strategy for transforming Hogangnono complex data to Naver format.

    Handles field mapping from Hogangnono API response to Naver CSV format.
    """

    # Naver-compatible field names for complexes
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
    ]

    def transform(self, row: Dict[str, Any], fieldnames: List[str]) -> Dict[str, Any]:
        """Transform Hogangnono complex data to Naver format.

        Args:
            row: Hogangnono complex data
            fieldnames: Expected output field names

        Returns:
            Transformed data in Naver format
        """
        # Apply common normalization
        normalized = self._normalize_common_fields(row)

        # Field mapping from Hogangnono to Naver format
        field_mapping = {
            "complex_id": "aptSeq",
            "complex_name": "aptName",
            "total_household_count": "householdCnt",
            "deal_count": "dealCnt",
        }

        # Apply field mapping
        for naver_field, hogangnono_field in field_mapping.items():
            if hogangnono_field in row:
                value = row[hogangnono_field]
                normalized[naver_field] = str(value) if value is not None else ""

        # Handle completion year
        self._handle_completion_year(normalized, row)

        # Set default values for required fields
        defaults = {
            "real_estate_type": "아파트",
            "total_dong_count": "1",
            "min_area": "33.0",
            "max_area": "85.0",
            "lease_count": "0",
            "rent_count": "0",
            "pyeong_types": "33평, 59평",
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        for field, value in defaults.items():
            if not normalized.get(field):
                normalized[field] = value

        # Filter and order by fieldnames
        target_fields = fieldnames or self.FIELDNAMES
        result = {}
        for field in target_fields:
            result[field] = normalized.get(field, "")

        return result

    def get_fieldnames(self) -> List[str]:
        """Get Naver-compatible field names."""
        return self.FIELDNAMES.copy()

    def _handle_completion_year(self, normalized: Dict[str, Any], row: Dict[str, Any]) -> None:
        """Handle completion year/month field."""
        if not normalized.get("completion_year_month"):
            build_year = row.get("buildYear")
            if build_year and str(build_year).isdigit() and len(str(build_year)) == 4:
                normalized["completion_year_month"] = f"{build_year}0101"
            else:
                normalized["completion_year_month"] = ""


class HogangnonoTransactionStrategy(BaseDataTransformationStrategy):
    """Strategy for transforming Hogangnono transaction data to Naver format.

    Handles field mapping from Hogangnono API response to Naver CSV format.
    """

    # Naver-compatible field names for transactions
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
    ]

    def transform(self, row: Dict[str, Any], fieldnames: List[str]) -> Dict[str, Any]:
        """Transform Hogangnono transaction data to Naver format.

        Args:
            row: Hogangnono transaction data
            fieldnames: Expected output field names

        Returns:
            Transformed data in Naver format
        """
        # Trade type mapping
        trade_type_mapping = {
            "매매": ("매매", "일반거래"),
            "전세": ("전세", "일반거래"),
            "월세": ("월세", "일반거래"),
        }

        # Parse trade type
        deal_type = row.get("dealType", "")
        trade_info = trade_type_mapping.get(deal_type, ("", "일반거리"))

        # Parse date
        deal_date = row.get("dealDate", "")
        trade_year = datetime.now().year
        if deal_date:
            formatted_date, trade_year = self._parse_date(deal_date)
            deal_date = formatted_date

        # Parse pyeong type
        pyeong = row.get("pyeong", "")
        pyeong_type_number = 0
        if pyeong and pyeong.isdigit():
            pyeong_type_number = int(pyeong)

        # Build normalized data
        normalized = {
            "complex_id": str(row.get("aptSeq", "")),
            "complex_name": str(row.get("aptName", "")),
            "pyeong_type_number": str(pyeong_type_number),
            "pyeong_name": str(row.get("pyeongName", "")),
            "trade_type": trade_info[0],
            "trade_type_name": trade_info[1],
            "trade_date": deal_date,
            "trade_year": str(trade_year),
            "floor": str(self._parse_floor(row.get("floor", ""))),
            "deal_price": str(self._parse_money_amount(row.get("dealAmount", ""))),
            "deposit": str(self._parse_money_amount(row.get("deposit", ""))),
            "monthly_rent": str(self._parse_money_amount(row.get("monthlyRent", ""))),
            "trade_category": "일반거래",
            "is_delete": "false",
            "is_renew": "false",
        }

        # Filter and order by fieldnames
        target_fields = fieldnames or self.FIELDNAMES
        result = {}
        for field in target_fields:
            result[field] = normalized.get(field, "")

        return result

    def get_fieldnames(self) -> List[str]:
        """Get Naver-compatible field names."""
        return self.FIELDNAMES.copy()

    def _parse_date(self, date_str: str) -> tuple[str, int]:
        """Parse Hogangnono date format.

        Override to handle specific Hogangnono date formats.
        """
        if not date_str:
            return "", datetime.now().year

        try:
            # Normalize separators
            date_str = date_str.replace(".", "-")
            date_part = date_str.split()[0]

            # Parse date
            date_obj = datetime.strptime(date_part, "%Y-%m-%d")
            return date_part, date_obj.year
        except (ValueError, IndexError):
            return "", datetime.now().year


class HogangnonoComplexStrategyProtocol(DataTransformationStrategy):
    """Protocol-based implementation for Hogangnono complex data.

    Alternative implementation using Protocol interface.
    """

    def __init__(self):
        self._fieldnames = HogangnonoComplexStrategy.FIELDNAMES

    def transform(self, row: Dict[str, Any], fieldnames: List[str]) -> Dict[str, Any]:
        """Transform using delegation to strategy."""
        strategy = HogangnonoComplexStrategy()
        return strategy.transform(row, fieldnames or self._fieldnames)

    def get_fieldnames(self) -> List[str]:
        """Get field names."""
        return self._fieldnames.copy()


class HogangnonoTransactionStrategyProtocol(DataTransformationStrategy):
    """Protocol-based implementation for Hogangnono transaction data.

    Alternative implementation using Protocol interface.
    """

    def __init__(self):
        self._fieldnames = HogangnonoTransactionStrategy.FIELDNAMES

    def transform(self, row: Dict[str, Any], fieldnames: List[str]) -> Dict[str, Any]:
        """Transform using delegation to strategy."""
        strategy = HogangnonoTransactionStrategy()
        return strategy.transform(row, fieldnames or self._fieldnames)

    def get_fieldnames(self) -> List[str]:
        """Get field names."""
        return self._fieldnames.copy()
