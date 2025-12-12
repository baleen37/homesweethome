"""CSV writer for Hogangnono transactions data.

This module provides HogangnonoTransactionsCSVWriter class that handles transactions.csv
file for Hogangnono data using the refactored base class.
"""

from pathlib import Path

from crawler.writers.base_hogangnono_writer import BaseHogangnonoCSVWriter
from crawler.writers.hogangnono_strategy import HogangnonoTransactionStrategy
from crawler.writers.csv_header_standard import CSVType
from crawler.writers.data_transformation_strategy import DataTransformationStrategy


class HogangnonoTransactionsCSVWriter(BaseHogangnonoCSVWriter):
    """호갱노노 거래내역 데이터를 CSV로 저장하는 전용 클래스

    이 클래스는 Strategy 패턴을 사용하여 호갱노노 데이터를 네이버 형식으로 변환합니다.
    """

    # Fieldnames for backward compatibility
    FIELDNAMES = HogangnonoTransactionStrategy().get_fieldnames()

    def __init__(self, output_path: Path) -> None:
        """Initialize HogangnonoTransactionsCSVWriter with Hogangnono strategy.

        Args:
            output_path: Path to the CSV file
        """
        super().__init__(output_path, CSVType.TRANSACTIONS)

    def _create_strategy(self, csv_type: CSVType) -> DataTransformationStrategy:
        """Create the transactions strategy.

        Args:
            csv_type: Type of CSV (should be TRANSACTIONS)

        Returns:
            HogangnonoTransactionStrategy instance
        """
        if csv_type != CSVType.TRANSACTIONS:
            raise ValueError(
                f"HogangnonoTransactionsCSVWriter expects TRANSACTIONS type, got {csv_type}"
            )
        return HogangnonoTransactionStrategy()
