"""CSV writer for Hogangnono complexes data.

This module provides HogangnonoComplexesCSVWriter class that inherits from BaseCSVWriter
to handle complexes.csv file for Hogangnono data.
"""

from pathlib import Path
from typing import Any, Dict

from crawler.writers.base_csv_writer import BaseCSVWriter
from crawler.writers.hogangnono_strategy import HogangnonoComplexStrategy


class HogangnonoComplexesCSVWriter(BaseCSVWriter):
    """호갱노노 단지 데이터를 CSV로 저장하는 전용 클래스

    이 클래스는 Strategy 패턴을 사용하여 호갱노노 데이터를 네이버 형식으로 변환합니다.
    """

    # 네이버 CSV 형식 필드명 (향후 호환성을 위해 유지)
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

    def __init__(self, output_path: Path) -> None:
        """Initialize HogangnonoComplexesCSVWriter with Hogangnono strategy.

        Args:
            output_path: Path to the CSV file
        """
        # Create and set the Hogangnono complex transformation strategy
        strategy = HogangnonoComplexStrategy()
        super().__init__(output_path, strategy=strategy)

    def _normalize_row_legacy(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy normalization method - not used when strategy is set.

        This method is kept for backward compatibility but should not be called
        when a strategy is provided.
        """
        # This should not be reached when strategy is set
        # Base class will use the strategy instead
        return row
