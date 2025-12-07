import csv
from pathlib import Path
from typing import Any


class TransactionCSVWriter:
    """거래내역 CSV 파일을 처리하는 전용 클래스

    설계 문서의 CSV 스키마를 따르는 transactions.csv 파일을 생성합니다.
    점진적 저장(incremental write)을 지원합니다.
    """

    # 정의된 CSV 스키마
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

    def __init__(self, output_path: Path | str) -> None:
        """TransactionCSVWriter 초기화

        Args:
            output_path: CSV 파일 출력 경로 (예: Path("output/transactions.csv") 또는 "output/transactions.csv")
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

    def write(self, data: list[dict[str, Any]], mode: str = "w") -> None:
        """데이터를 CSV로 저장합니다.

        Args:
            data: 저장할 거래내역 데이터 리스트
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
            normalized_data = [self._normalize_transaction(item) for item in data]
            writer.writerows(normalized_data)

        self._file_exists = True

    def write_row(self, row: dict[str, Any]) -> None:
        """단일 행을 CSV 파일에 추가합니다.

        Args:
            row: 추가할 거래내역 데이터
        """
        self.append([row])

    def append(self, data: list[dict[str, Any]]) -> None:
        """기존 파일에 데이터를 추가합니다. 점진적 저장에 사용됩니다.

        Args:
            data: 추가할 거래내역 데이터 리스트
        """
        if not self._file_exists:
            # 파일이 없으면 새로 생성 (헤더 포함)
            self.write(data, mode="w")
        else:
            # 기존 파일에 추가
            self.write(data, mode="a")

    def _normalize_transaction(self, transaction: dict[str, Any]) -> dict[str, Any]:
        """거래내역 데이터를 CSV 스키마에 맞게 정규화합니다.

        필드 순서를 보장하고, 누락된 필드를 기본값으로 채웁니다.

        Args:
            transaction: 정규화할 거래내역 데이터

        Returns:
            정규화된 거래내역 데이터
        """
        normalized: dict[str, Any] = {}

        # 정의된 모든 필드에 대해 값을 설정
        for field in self.FIELDNAMES:
            value = transaction.get(field, "")

            # boolean 타입 필드 처리
            if field in ["is_delete", "is_renew"]:
                if isinstance(value, bool):
                    normalized[field] = value
                elif isinstance(value, str):
                    normalized[field] = value.lower() == "true"
                elif isinstance(value, int) and value in (0, 1):
                    normalized[field] = bool(value)
                else:
                    normalized[field] = False
            # 숫자 필드 처리
            elif field in ["floor", "deal_price", "deposit", "monthly_rent", "pyeong_type_number"]:
                try:
                    normalized[field] = int(value) if value != "" else 0
                except (ValueError, TypeError):
                    normalized[field] = 0
            else:
                # 문자열 필드
                normalized[field] = str(value) if value is not None else ""

        return normalized

    def ensure_file_exists(self) -> None:
        """CSV 파일이 존재하는지 확인하고, 없으면 빈 파일을 생성합니다."""
        if not self._file_exists:
            self.write_header()

    def close(self) -> None:
        """CSV writer를 종료합니다. 현재는 아무 작업도 하지 않습니다."""
        pass
