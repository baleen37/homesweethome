"""CSV writer for Hogangnono transactions data.

This module provides HogangnonoTransactionsCSVWriter as a compatibility wrapper
for the new unified writer architecture.
"""

from pathlib import Path

from crawler.writers.hogangnono_factory import create_hogangnono_transaction_writer


class HogangnonoTransactionsCSVWriter:
    """Compatibility wrapper for Hogangnono transaction data writer.

    This class maintains backward compatibility while using the new
    unified writer architecture internally.
    """

    # Fieldnames for backward compatibility
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

    def __init__(self, output_path: Path) -> None:
        """Initialize HogangnonoTransactionsCSVWriter.

        Args:
            output_path: Path to the CSV file
        """
        # Use the factory function to create the actual writer
        self._writer = create_hogangnono_transaction_writer(output_path)

    def write(self, data: list[dict], mode: str = "w", write_header: bool = True) -> None:
        """Write data to CSV.

        Args:
            data: List of dictionaries to write
            mode: Write mode ('w' or 'a')
            write_header: Whether to write header
        """
        self._writer.write(data, mode=mode, write_header=write_header)

    def append(self, data: list[dict]) -> None:
        """Append data to CSV.

        Args:
            data: List of dictionaries to append
        """
        self._writer.append(data)

    def get_file_info(self) -> dict:
        """Get file information.

        Returns:
            Dictionary with file statistics
        """
        return self._writer.get_stats()
