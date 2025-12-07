"""CSV writer for complexes data including statistics.

This module provides ComplexesCSVWriter class for handling complexes.csv files
with basic information, detailed information, and calculated statistics fields.
"""

import csv
from pathlib import Path
from typing import Any, List

from crawler.utils.statistics import COMPLEXES_CSV_FIELDNAMES


class ComplexesCSVWriter:
    """단지 정보 CSV 파일을 처리하는 전용 클래스

    설계 문서의 CSV 스키마를 따르는 complexes.csv 파일을 생성합니다.
    기본 정보, 상세 정보, 통계 정보를 모두 포함합니다.
    점진적 저장(incremental write)을 지원합니다.
    """

    # 정의된 CSV 스키마
    FIELDNAMES = COMPLEXES_CSV_FIELDNAMES

    def __init__(self, output_path: Path | str) -> None:
        """ComplexesCSVWriter 초기화

        Args:
            output_path: CSV 파일 출력 경로 (예: Path("output/complexes.csv") 또는 "output/complexes.csv")
        """
        self.output_path = Path(output_path) if isinstance(output_path, str) else output_path
        self._file_exists = self.output_path.exists()

    def write_header(self) -> None:
        """CSV 파일에 헤더만 작성합니다. 새 파일 생성 시 사용됩니다."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writeheader()

        self._file_exists = True

    def write(self, data: List[dict[str, Any]], mode: str = "w") -> None:
        """데이터를 CSV로 저장합니다.

        Args:
            data: 저장할 단지 정보 데이터 리스트
            mode: 쓰기 모드 ('w'는 새로 쓰기, 'a'는 이어 쓰기)
        """
        if not data:
            return

        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # 새 파일인 경우 헤더 작성
        write_header = mode == "w"

        with open(self.output_path, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)

            if write_header:
                writer.writeheader()

            # 데이터의 각 필드를 검증하고 정규화
            normalized_data = [self._normalize_complex_data(item) for item in data]
            writer.writerows(normalized_data)

        self._file_exists = True

    def write_row(self, row: dict[str, Any]) -> None:
        """단일 행을 CSV 파일에 추가합니다.

        Args:
            row: 추가할 단지 정보 데이터
        """
        self.append([row])

    def append(self, data: List[dict[str, Any]]) -> None:
        """기존 파일에 데이터를 추가합니다. 점진적 저장에 사용됩니다.

        Args:
            data: 추가할 단지 정보 데이터 리스트
        """
        if not self._file_exists:
            # 파일이 없으면 새로 생성 (헤더 포함)
            self.write(data, mode="w")
        else:
            # 기존 파일에 추가
            self.write(data, mode="a")

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
        normalized = self._normalize_complex_data(complex_with_stats)
        self.append([normalized])

    def _normalize_complex_data(self, complex_data: dict[str, Any]) -> dict[str, Any]:
        """단지 정보 데이터를 CSV 스키마에 맞게 정규화합니다.

        필드 순서를 보장하고, 누락된 필드를 기본값으로 채웁니다.

        Args:
            complex_data: 정규화할 단지 정보 데이터

        Returns:
            정규화된 단지 정보 데이터
        """
        # Import here to avoid circular import
        from crawler.utils.statistics import STATISTICS_FIELDS, normalize_complex_data

        # Start with a copy of the original data
        normalized = complex_data.copy()

        # Define default values for all non-statistics fields
        default_values = {
            "complex_id": "",
            "complex_name": "",
            "real_estate_type": "",
            "completion_year_month": "",
            "total_dong_count": 0,
            "total_household_count": 0,
            "min_area": 0.0,
            "max_area": 0.0,
            "deal_count": 0,
            "lease_count": 0,
            "rent_count": 0,
            "pyeong_types": "",
            "fetched_at": "",
        }

        # Fill in missing non-statistics fields with defaults
        for field, default_value in default_values.items():
            if field not in normalized:
                normalized[field] = default_value

        # Normalize statistics fields
        normalized = normalize_complex_data(normalized, STATISTICS_FIELDS)

        # Only keep fields that are in the CSV schema
        filtered = {field: normalized.get(field) for field in self.FIELDNAMES}

        return filtered

    def ensure_file_exists(self) -> None:
        """CSV 파일이 존재하는지 확인하고, 없으면 빈 파일을 생성합니다."""
        if not self._file_exists:
            self.write_header()

    def close(self) -> None:
        """CSV writer를 종료합니다. 현재는 아무 작업도 하지 않습니다."""
        pass
