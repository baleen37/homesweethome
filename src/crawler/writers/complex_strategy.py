"""Complex data transformation strategy.

This module provides ComplexDataTransformationStrategy class for
normalizing complex/apartment data for CSV output.
"""

from typing import Any, Dict, List

from crawler.writers.data_transformation_strategy import (
    BaseDataTransformationStrategy,
)
from crawler.models.csv_models import ComplexCSVRow


class ComplexDataTransformationStrategy(BaseDataTransformationStrategy):
    """Strategy for transforming complex/apartment data.

    Handles normalization of complex records including:
    - Basic information (ID, name, type)
    - Building details (completion, household counts)
    - Statistics fields (deal counts, prices)
    - Field mapping and ordering

    Uses Korean field names from ComplexCSVRow for consistent CSV output.
    """

    # Field mapping from internal English names to Korean CSV headers
    FIELD_MAPPING = {
        # Basic info mapping
        "complex_id": "단지ID",
        "complex_name": "단지명",
        "real_estate_type": "주소",  # Using address as real estate type info
        "completion_year_month": "건축년도",
        "total_dong_count": "층수",  # Using floor count for dong count
        "total_household_count": "세대수",
        "min_area": "연면적",  # Using total floor area for min area
        "max_area": "대지면적",  # Using site area for max area
        # Additional info
        "deal_count": "승강기수",
        "lease_count": "주차대수",
        "rent_count": "난방방식",
        "pyeong_types": "구코드",
        "fetched_at": "동코드",
        "total_transaction_count": "구이름",
        "latest_deal_price": "동이름",
        # Numeric fields that can be mapped to coordinates
        "latest_deal_date": "위도",
        "avg_deal_price_1year": "경도",
        # Remaining fields (can be stored in additional columns or ignored)
        "deal_count_1year": None,
        "lease_count_1year": None,
        "rent_count_1year": None,
    }

    def transform(self, row: Dict[str, Any], fieldnames: List[str]) -> Dict[str, Any]:
        """Transform complex data row.

        Args:
            row: Raw complex data
            fieldnames: Expected output field names (from dataclass)

        Returns:
            Transformed complex data with Korean field names
        """
        # Get the expected Korean field names from dataclass
        target_fields = fieldnames or ComplexCSVRow.get_fieldnames()

        # Initialize result with all required fields set to empty
        result = {field: "" for field in target_fields}

        # Apply common normalization to get basic fields
        normalized = self._normalize_common_fields(row)

        # Map fields using FIELD_MAPPING
        for eng_name, kor_name in self.FIELD_MAPPING.items():
            if kor_name and kor_name in target_fields:
                # Get the value from the original row or normalized data
                value = row.get(eng_name) or normalized.get(eng_name)

                # Special handling for different field types
                if kor_name in ["건축년도", "세대수", "층수", "승강기수", "주차대수"]:
                    # Numeric fields
                    try:
                        value = int(float(value)) if value and str(value) else 0
                        result[kor_name] = str(value)
                    except (ValueError, TypeError):
                        result[kor_name] = "0"
                elif kor_name in ["연면적", "대지면적", "위도", "경도"]:
                    # Float fields
                    try:
                        value = float(value) if value and str(value) else 0.0
                        result[kor_name] = str(value)
                    except (ValueError, TypeError):
                        result[kor_name] = "0.0"
                else:
                    # String fields
                    result[kor_name] = str(value) if value is not None else ""

        # Handle direct mappings for common fields
        direct_mappings = {
            "id": "단지ID",
            "name": "단지명",
            "address": "주소",
            "latitude": "위도",
            "longitude": "경도",
            "build_year": "건축년도",
            "buildYear": "건축년도",  # Alternative field name
            "households": "세대수",
            "floors": "층수",
            "elevator_count": "승강기수",
            "parking_count": "주차대수",
            "heating_type": "난방방식",
            "total_floor_area": "연면적",
            "total_site_area": "대지면적",
            "gu_code": "구코드",
            "dong_code": "동코드",
            "gu_name": "구이름",
            "dong_name": "동이름",
        }

        for eng_name, kor_name in direct_mappings.items():
            if kor_name in target_fields:
                value = row.get(eng_name)
                if value is not None:
                    if kor_name in ["건축년도", "세대수", "층수", "승강기수", "주차대수"]:
                        try:
                            result[kor_name] = str(int(float(value)))
                        except (ValueError, TypeError):
                            result[kor_name] = "0"
                    elif kor_name in ["연면적", "대지면적", "위도", "경도"]:
                        try:
                            result[kor_name] = str(float(value))
                        except (ValueError, TypeError):
                            result[kor_name] = "0.0"
                    else:
                        result[kor_name] = str(value)

        return result

    def get_fieldnames(self) -> List[str]:
        """Get standard complex field names from dataclass."""
        return ComplexCSVRow.get_fieldnames()

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
