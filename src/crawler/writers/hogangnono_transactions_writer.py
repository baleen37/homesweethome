"""CSV writer for Hogangnono transactions data.

This module provides HogangnonoTransactionsCSVWriter as a compatibility wrapper
for the new unified writer architecture.
"""

from pathlib import Path

from crawler.writers.hogangnono_base_wrapper import BaseHogangnonoWrapper
from crawler.writers.hogangnono_factory import create_hogangnono_transaction_writer


class HogangnonoTransactionsCSVWriter(BaseHogangnonoWrapper):
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

    def _create_writer(self, output_path: Path):
        """Create the underlying writer using the factory function.

        Args:
            output_path: Path to the CSV file

        Returns:
            The actual writer instance
        """
        return create_hogangnono_transaction_writer(output_path)
