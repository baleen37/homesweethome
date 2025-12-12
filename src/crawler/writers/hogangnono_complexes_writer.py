"""CSV writer for Hogangnono complexes data.

This module provides HogangnonoComplexesCSVWriter as a compatibility wrapper
for the new unified writer architecture.
"""

from pathlib import Path

from crawler.writers.hogangnono_factory import create_hogangnono_complex_writer


class HogangnonoComplexesCSVWriter:
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

    def __init__(self, output_path: Path) -> None:
        """Initialize HogangnonoComplexesCSVWriter.

        Args:
            output_path: Path to the CSV file
        """
        # Use the factory function to create the actual writer
        self._writer = create_hogangnono_complex_writer(output_path)

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
