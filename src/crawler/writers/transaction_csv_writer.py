from pathlib import Path
from typing import Any

from crawler.writers.base_csv_writer import BaseCSVWriter
from crawler.writers.transaction_strategy import TransactionDataTransformationStrategy


class TransactionCSVWriter(BaseCSVWriter):
    """거래내역 CSV 파일을 처리하는 전용 클래스

    설계 문서의 CSV 스키마를 따르는 transactions.csv 파일을 생성합니다.
    점진적 저장(incremental write)을 지원합니다.

    이 클래스는 Strategy 패턴을 사용하여 데이터 변환을 처리합니다.
    """

    # 정의된 CSV 스키마 (향후 호환성을 위해 유지)
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
        "gu_code",  # 추가: 구 코드
        "dong_code",  # 추가: 동 코드
        "gu_name",  # 추가: 구 이름
        "dong_name",  # 추가: 동 이름
    ]

    def __init__(self, output_path: Path) -> None:
        """Initialize TransactionCSVWriter with transaction strategy.

        Args:
            output_path: Path to the CSV file
        """
        # Create and set the transaction transformation strategy
        strategy = TransactionDataTransformationStrategy()
        super().__init__(output_path, strategy=strategy)

    def _normalize_row_legacy(self, row: dict[str, Any]) -> dict[str, Any]:
        """Legacy normalization method - not used when strategy is set.

        This method is kept for backward compatibility but should not be called
        when a strategy is provided.

        Args:
            row: 정규화할 거래내역 데이터

        Returns:
            정규화된 거래내역 데이터
        """
        # This should not be reached when strategy is set
        # Base class will use the strategy instead
        return row
