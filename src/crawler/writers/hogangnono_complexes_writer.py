"""CSV writer for Hogangnono complexes data.

This module provides HogangnonoComplexesCSVWriter class that inherits from BaseCSVWriter
to handle complexes.csv file for Hogangnono data.
"""

from typing import Any, Dict
from datetime import datetime

from crawler.writers.base_csv_writer import BaseCSVWriter


class HogangnonoComplexesCSVWriter(BaseCSVWriter):
    """호갱노노 단지 데이터를 CSV로 저장하는 전용 클래스"""

    # 네이버 CSV 형식 필드명
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

    def _normalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """단지 데이터를 네이버 형식으로 정규화"""
        # Base 정규화 적용
        normalized = self._normalize_common_fields(row)

        # 추가 정규화가 필요한 경우 여기에 구현
        if not normalized.get("completion_year_month"):
            if row.get("buildYear") and str(row["buildYear"]).isdigit():
                build_year = str(row["buildYear"])
                normalized["completion_year_month"] = f"{build_year}0101"

        # 필드 매핑
        field_mapping = {
            "complex_id": "aptSeq",
            "complex_name": "aptName",
            "total_household_count": "householdCnt",
            "deal_count": "dealCnt",
        }

        for naver_field, hogangnono_field in field_mapping.items():
            if hogangnono_field in row:
                normalized[naver_field] = (
                    str(row[hogangnono_field]) if row[hogangnono_field] is not None else ""
                )

        # 기본값 설정
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

        # FIELDNAMES 순서로 필터링
        return {field: normalized.get(field, "") for field in self.FIELDNAMES}
