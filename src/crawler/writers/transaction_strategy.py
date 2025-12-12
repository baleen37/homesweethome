"""Transaction data transformation strategy.

This module provides TransactionDataTransformationStrategy class for
normalizing transaction data for CSV output.
"""

from typing import Any, Dict, List

from crawler.writers.data_transformation_strategy import (
    BaseDataTransformationStrategy,
    DataTransformationStrategy,
)
from crawler.models.csv_models import TransactionCSVRow


class TransactionDataTransformationStrategy(BaseDataTransformationStrategy):
    """Strategy for transforming transaction data.

    Handles normalization of transaction records including:
    - Boolean field handling (is_delete, is_renew)
    - Numeric field parsing (floor, prices)
    - Date parsing
    - Field mapping and ordering

    Uses Korean field names from TransactionCSVRow for consistent CSV output.
    """

    # Field mapping from internal English names to Korean CSV headers
    FIELD_MAPPING = {
        "complex_id": "단지ID",
        "complex_name": "단지명",
        "pyeong_type_number": "평형번호",
        "pyeong_name": "평형이름",
        "trade_type": "거래유형",
        "trade_type_name": "거래유형명",
        "trade_date": "거래일",
        "trade_year": "거래년도",
        "floor": "층",
        "deal_price": "매매가",
        "deposit": "전세가",
        "monthly_rent": "월세",
        "trade_category": "거래구분",
        # Boolean fields handled separately (not in FIELD_MAPPING)
        # "is_delete": "삭제여부",  # Handled separately
        # "is_renew": "갱신여부",    # Handled separately
        "gu_code": None,  # Not in dataclass
        "dong_code": None,  # Not in dataclass
        "gu_name": None,  # Not in dataclass
        "dong_name": None,  # Not in dataclass
    }

    def transform(self, row: Dict[str, Any], fieldnames: List[str]) -> Dict[str, Any]:
        """Transform transaction data row.

        Args:
            row: Raw transaction data
            fieldnames: Expected output field names (from dataclass)

        Returns:
            Transformed transaction data with Korean field names
        """
        # Get the expected Korean field names from dataclass
        target_fields = fieldnames or TransactionCSVRow.get_fieldnames()

        # Initialize result with all required fields set to empty
        result = {field: "" for field in target_fields}

        # Apply common normalization to get basic fields
        normalized = self._normalize_common_fields(row)

        # Handle boolean fields specifically for is_delete and is_renew
        is_delete = False
        is_renew = False

        for field in ["is_delete", "is_renew"]:
            value = row.get(field, "")
            if isinstance(value, bool):
                if field == "is_delete":
                    is_delete = value
                else:
                    is_renew = value
            elif isinstance(value, str):
                bool_val = value.lower() == "true"
                if field == "is_delete":
                    is_delete = bool_val
                else:
                    is_renew = bool_val
            elif isinstance(value, int) and value in (0, 1):
                if field == "is_delete":
                    is_delete = bool(value)
                else:
                    is_renew = bool(value)

        # Set default values for boolean fields
        result["삭제여부"] = "N" if not is_delete else "Y"
        result["갱신여부"] = "N" if not is_renew else "Y"

        # Map fields using FIELD_MAPPING
        for eng_name, kor_name in self.FIELD_MAPPING.items():
            if kor_name and kor_name in target_fields:
                # Get the value from the original row or normalized data
                value = row.get(eng_name) or normalized.get(eng_name)

                # Special handling for different field types
                if kor_name in ["평형번호", "거래년도", "매매가", "전세가", "월세"]:
                    # Numeric fields
                    try:
                        value = int(float(value)) if value and str(value) else 0
                        result[kor_name] = str(value)
                    except (ValueError, TypeError):
                        result[kor_name] = "0"
                else:
                    # String fields
                    result[kor_name] = str(value) if value is not None else ""

        # Handle direct mappings for common fields
        direct_mappings = {
            "id": "단지ID",
            "name": "단지명",
            "complex_id": "단지ID",
            "complex_name": "단지명",
            "exclusive_area": "평형번호",  # Convert area to pyeong number
            "trade_type": "거래유형",
            "trade_type_name": "거래유형명",
            "trade_date": "거래일",
            "price": "매매가",
            "deal_price": "매매가",  # Alternative field name
            "deposit": "전세가",
            "monthly_rent": "월세",
            "floor": "층",
        }

        for eng_name, kor_name in direct_mappings.items():
            if kor_name in target_fields:
                value = row.get(eng_name)
                if value is not None:
                    if kor_name in ["평형번호", "거래년도", "매매가", "전세가", "월세"]:
                        try:
                            # Handle pyeong conversion
                            if kor_name == "평형번호" and eng_name == "exclusive_area":
                                from .validators import SQM_TO_PYEONG_RATIO

                                pyeong = float(value) / SQM_TO_PYEONG_RATIO
                                result[kor_name] = str(round(pyeong))
                            elif kor_name in ["매매가", "전세가", "월세"]:
                                # Use money amount parsing for price fields
                                result[kor_name] = str(self._parse_money_amount(str(value)))
                            else:
                                result[kor_name] = str(int(float(value)))
                        except (ValueError, TypeError):
                            result[kor_name] = "0"
                    else:
                        result[kor_name] = str(value)

        # Handle trade type conversion
        trade_type = row.get("trade_type", "")
        if trade_type:
            if trade_type == "sale":
                result["거래유형"] = "A1"
                result["거래유형명"] = "매매"
            elif trade_type == "jeonse":
                result["거래유형"] = "B1"
                result["거래유형명"] = "전세"
            elif trade_type == "monthly":
                result["거래유형"] = "B2"
                result["거래유형명"] = "월세"

        # Extract trade year from trade date
        if result.get("거래일") and len(result["거래일"]) >= 4:
            year_str = result["거래일"][:4]
            if year_str.isdigit():
                result["거래년도"] = year_str

        # Set 거래구분 same as trade_type
        if trade_type:
            result["거래구분"] = trade_type

        # Generate 평형이름 from 평형번호
        if result.get("평형번호") and result["평형번호"] != "0":
            result["평형이름"] = f"{result['평형번호']}평형"

        return result

    def get_fieldnames(self) -> List[str]:
        """Get standard transaction field names from dataclass."""
        return TransactionCSVRow.get_fieldnames()


class GenericTransactionStrategy(DataTransformationStrategy):
    """Generic transaction strategy using Protocol interface.

    Alternative implementation that doesn't inherit from base class.
    """

    def __init__(self):
        self._fieldnames = TransactionCSVRow.get_fieldnames()

    def transform(self, row: Dict[str, Any], fieldnames: List[str]) -> Dict[str, Any]:
        """Transform using delegation to base strategy."""
        strategy = TransactionDataTransformationStrategy()
        return strategy.transform(row, fieldnames or self._fieldnames)

    def get_fieldnames(self) -> List[str]:
        """Get field names from dataclass."""
        return TransactionCSVRow.get_fieldnames()
