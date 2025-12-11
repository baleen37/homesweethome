"""CSV writer for complexes data including statistics.

This module provides ComplexesCSVWriter class for handling complexes.csv files
with basic information, detailed information, and calculated statistics fields.
"""

from typing import Any, List

from crawler.utils.statistics import COMPLEXES_CSV_FIELDNAMES
from crawler.writers.base_csv_writer import BaseCSVWriter


class ComplexesCSVWriter(BaseCSVWriter):
    """단지 정보 CSV 파일을 처리하는 전용 클래스

    설계 문서의 CSV 스키마를 따르는 complexes.csv 파일을 생성합니다.
    기본 정보, 상세 정보, 통계 정보를 모두 포함합니다.
    점진적 저장(incremental write)을 지원합니다.
    """

    # 정의된 CSV 스키마
    FIELDNAMES = COMPLEXES_CSV_FIELDNAMES

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

        # 정규화 후 추가
        normalized = self._normalize_row(complex_with_stats)
        self.append([normalized])

    def _normalize_row(self, complex_data: dict[str, Any]) -> dict[str, Any]:
        """단지 정보 데이터를 CSV 스키마에 맞게 정규화합니다.

        필드 순서를 보장하고, 누락된 필드를 기본값으로 채웁니다.

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
