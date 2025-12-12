"""Factory functions for creating Hogangnono-compatible writers.

This module provides factory functions to create appropriate CSV writers
for Hogangnono data while maintaining backward compatibility.
"""

from pathlib import Path
from typing import Dict, Any, List

from crawler.writers.complex_csv_writer import ComplexCSVWriter
from crawler.writers.transaction_csv_writer import TransactionCSVWriter
from crawler.writers.hogangnono_strategy import (
    HogangnonoComplexStrategy,
    HogangnonoTransactionStrategy,
)
from crawler.writers.csv_header_standard import CSVType


def create_hogangnono_complex_writer(output_path: Path) -> ComplexCSVWriter:
    """Create a CSV writer for Hogangnono complex data.

    Args:
        output_path: Path to the output CSV file

    Returns:
        Configured ComplexCSVWriter instance
    """
    strategy = HogangnonoComplexStrategy()
    writer = ComplexCSVWriter(
        output_path=output_path,
        use_korean_fields=False,  # Use English field names for compatibility
    )
    writer.strategy = strategy
    writer._csv_type = CSVType.COMPLEXES

    return writer


def create_hogangnono_transaction_writer(output_path: Path) -> TransactionCSVWriter:
    """Create a CSV writer for Hogangnono transaction data.

    Args:
        output_path: Path to the output CSV file

    Returns:
        Configured TransactionCSVWriter instance
    """
    strategy = HogangnonoTransactionStrategy()
    writer = TransactionCSVWriter(
        output_path=output_path,
        use_korean_fields=False,  # Use English field names for compatibility
    )
    writer.strategy = strategy
    writer._csv_type = CSVType.TRANSACTIONS

    return writer


class HogangnonoCSVWriter:
    """Legacy compatibility wrapper for Hogangnono CSV operations.

    This class maintains compatibility with the original HogangnonoCSVWriter
    while using the new unified writer architecture.
    """

    def __init__(self, output_dir: str = "output"):
        """Initialize HogangnonoCSVWriter.

        Args:
            output_dir: Directory for output files
        """
        from pathlib import Path

        self.output_dir = Path(output_dir)
        self.complexes_path = self.output_dir / "complexes.csv"
        self.transactions_path = self.output_dir / "transactions.csv"

        # Create writers using factory functions
        self.complexes_writer = create_hogangnono_complex_writer(self.complexes_path)
        self.transactions_writer = create_hogangnono_transaction_writer(self.transactions_path)

    def save_complexes(self, complexes_data: List[Dict[str, Any]]) -> None:
        """Save complex data to complexes.csv.

        Args:
            complexes_data: List of complex data dictionaries
        """
        self.complexes_writer.write(complexes_data)

    def save_transactions(self, transactions_data: List[Dict[str, Any]]) -> None:
        """Save transaction data to transactions.csv.

        Args:
            transactions_data: List of transaction data dictionaries
        """
        self.transactions_writer.write(transactions_data)

    def transform_to_naver_format(
        self, hogangnono_data: Dict[str, Any], data_type: str = "complex"
    ) -> Dict[str, Any]:
        """Transform Hogangnono data to Naver format.

        Args:
            hogangnono_data: Raw Hogangnono data
            data_type: Type of data ('complex' or 'transaction')

        Returns:
            Transformed data in Naver format
        """
        if data_type == "complex":
            strategy = HogangnonoComplexStrategy()
            fieldnames = strategy.get_fieldnames()
            return strategy.transform(hogangnono_data, fieldnames)
        elif data_type == "transaction":
            strategy = HogangnonoTransactionStrategy()
            fieldnames = strategy.get_fieldnames()
            return strategy.transform(hogangnono_data, fieldnames)
        else:
            raise ValueError(f"Unsupported data_type: {data_type}")

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about written files.

        Returns:
            Dictionary with file statistics
        """
        complexes_stats = self.complexes_writer.get_stats()
        transactions_stats = self.transactions_writer.get_stats()

        return {
            "complexes_file_size": complexes_stats.get("file_size", 0),
            "transactions_file_size": transactions_stats.get("file_size", 0),
            "complexes_record_count": complexes_stats.get("rows_written", 0),
            "transactions_record_count": transactions_stats.get("rows_written", 0),
        }

    async def write(self, data: List[Dict[str, Any]]) -> None:
        """Write method for ApartmentSearchCrawler compatibility.

        Args:
            data: Data to write (assumed to be complex data)
        """
        if isinstance(data, dict):
            data = [data]

        # Assume complex data and save accordingly
        self.save_complexes(data)
