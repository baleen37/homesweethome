"""CSV writer for complexes data including statistics.

This module provides ComplexesCSVWriter class for handling complexes.csv files
with basic information, detailed information, and calculated statistics fields.
"""

from pathlib import Path
from typing import Any, List

from crawler.utils.statistics import COMPLEXES_CSV_FIELDNAMES
from crawler.writers.base_csv_writer import BaseCSVWriter
from crawler.writers.complex_strategy import ComplexDataTransformationStrategy


class ComplexesCSVWriter(BaseCSVWriter):
    """단지 정보 CSV 파일을 처리하는 전용 클래스

    설계 문서의 CSV 스키마를 따르는 complexes.csv 파일을 생성합니다.
    기본 정보, 상세 정보, 통계 정보를 모두 포함합니다.
    점진적 저장(incremental write)을 지원합니다.

    이 클래스는 Strategy 패턴을 사용하여 데이터 변환을 처리합니다.
    """

    # 정의된 CSV 스키마 (향후 호환성을 위해 유지)
    FIELDNAMES = COMPLEXES_CSV_FIELDNAMES

    def __init__(self, output_path: Path) -> None:
        """Initialize ComplexesCSVWriter with complex strategy.

        Args:
            output_path: Path to the CSV file
        """
        # Create and set the complex transformation strategy
        strategy = ComplexDataTransformationStrategy()
        super().__init__(output_path, strategy=strategy)

    def append_with_statistics(
        self,
        complex_data: dict[str, Any],
        transactions: List[dict[str, Any]],
    ) -> None:
        """단지 정보와 거래내역을 바탕으로 통계를 계산하여 추가합니다.

        Args:
            complex_data: 기본 단지 정보
            transactions: 해당 단지의 거래내역 리스트
        """
        from crawler.utils.statistics import calculate_statistics_from_transactions

        # 통계 계산
        complex_with_stats = calculate_statistics_from_transactions(complex_data, transactions)

        # Strategy를 통해 정규화 후 추가
        normalized = self._normalize_row(complex_with_stats)
        self.append([normalized])

    def _normalize_row_legacy(self, complex_data: dict[str, Any]) -> dict[str, Any]:
        """Legacy normalization method - not used when strategy is set.

        This method is kept for backward compatibility but should not be called
        when a strategy is provided.

        Args:
            complex_data: 정규화할 단지 정보 데이터

        Returns:
            정규화된 단지 정보 데이터
        """
        # Import here to avoid circular import
        from crawler.utils.statistics import STATISTICS_FIELDS, normalize_complex_data

        # Base 정규화 적용
        normalized = self._normalize_common_fields(complex_data)

        # 통계 필드 정규화
        normalized = normalize_complex_data(normalized, STATISTICS_FIELDS)

        # FIELDNAMES 순서로 필터링
        return {field: normalized.get(field, "") for field in self.FIELDNAMES}
