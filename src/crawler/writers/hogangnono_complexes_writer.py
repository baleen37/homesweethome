"""CSV writer for Hogangnono complexes data.

This module provides HogangnonoComplexesCSVWriter as a compatibility wrapper
for the new unified writer architecture.
"""

from pathlib import Path

from crawler.writers.hogangnono_base_wrapper import BaseHogangnonoWrapper
from crawler.writers.hogangnono_factory import create_hogangnono_complex_writer


class HogangnonoComplexesCSVWriter(BaseHogangnonoWrapper):
    """Compatibility wrapper for Hogangnono complex data writer.

    This class maintains backward compatibility while using the new
    unified writer architecture internally.
    """

    # Fieldnames for backward compatibility
    FIELDNAMES = [
        "complex_id",
        "complex_name",
        "real_estate_type",
        "address",
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
        "poi_type",
        "poi_category",
        "validation_result",
        "validation_reason",
        "data_source",
    ]

    def _create_writer(self, output_path: Path):
        """Create the underlying writer using the factory function.

        Args:
            output_path: Path to the CSV file

        Returns:
            The actual writer instance
        """
        return create_hogangnono_complex_writer(output_path)
