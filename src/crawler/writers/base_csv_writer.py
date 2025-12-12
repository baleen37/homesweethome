"""Base CSV writer with common functionality for all CSV writers.

This module provides BaseCSVWriter class that contains common patterns
for file I/O operations, CSV writer setup, and data normalization.
"""

import csv
from pathlib import Path
from typing import Any, List, Dict
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseCSVWriter(ABC):
    """Base class for CSV writers with common functionality.

    Provides common patterns for:
    - File I/O operations (opening, closing files)
    - CSV writer setup
    - Header and row writing patterns
    - Data normalization
    """

    # Subclasses should define their fieldnames
    FIELDNAMES: List[str] = []

    def __init__(self, output_path: Path) -> None:
        """Initialize BaseCSVWriter.

        Args:
            output_path: Path to the CSV file
        """
        self.output_path = output_path
        self._file_exists = output_path.exists()

    @abstractmethod
    def _normalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a single row of data.

        Args:
            row: Raw data row to normalize

        Returns:
            Normalized data row with all fields present
        """
        pass

    def write_header(self) -> None:
        """Write CSV header to file.

        Creates a new file with only the header row.
        """
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writeheader()

        self._file_exists = True

    def write(
        self,
        data: List[Dict[str, Any]],
        mode: str = "w",
        write_header: bool = None,
    ) -> None:
        """Write data to CSV file.

        Args:
            data: List of data rows to write
            mode: Write mode ('w' for overwrite, 'a' for append)
            write_header: Whether to write header (None means auto-detect)
        """
        if not data:
            return

        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Auto-detect header writing if not specified
        if write_header is None:
            write_header = mode == "w"

        # Normalize data
        normalized_data = []
        for row in data:
            try:
                normalized = self._normalize_row(row)
                normalized_data.append(normalized)
            except Exception as e:
                logger.error("normalization_failed", row_data=row, error=str(e))
                raise

        # Write to file
        with open(self.output_path, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)

            if write_header:
                writer.writeheader()

            if normalized_data:
                writer.writerows(normalized_data)

        self._file_exists = True

    def append(self, data: List[Dict[str, Any]]) -> None:
        """Append data to existing file or create new file.

        Args:
            data: List of data rows to append
        """
        if not self._file_exists:
            # File doesn't exist, create with header
            self.write(data, mode="w")
        else:
            # Append to existing file
            self.write(data, mode="a", write_header=False)

    def ensure_file_exists(self) -> None:
        """Ensure CSV file exists, create empty file with header if not."""
        if not self._file_exists:
            self.write_header()

    def _normalize_common_fields(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize common fields for CSV output.

        Args:
            row: Raw data row to normalize

        Returns:
            Normalized data row with common fields processed
        """
        normalized = {}
        for key, value in row.items():
            if value is None:
                normalized[key] = ""
            elif isinstance(value, bool):
                normalized[key] = "true" if value else "false"
            else:
                # Keep original type for numbers, convert others to string
                if isinstance(value, (int, float)):
                    normalized[key] = value
                else:
                    normalized[key] = str(value)

        # Filter to only include fields in FIELDNAMES
        return {field: normalized.get(field, "") for field in self.FIELDNAMES}

    def get_fieldnames(self) -> List[str]:
        """Get the fieldnames for this CSV writer.

        Returns:
            List of field names
        """
        return self.FIELDNAMES

    def get_file_info(self) -> Dict[str, Any]:
        """Get information about the CSV file.

        Returns:
            Dictionary with file information
        """
        if self._file_exists and self.output_path.exists():
            file_size = self.output_path.stat().st_size
            with open(self.output_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                record_count = max(0, len(lines) - 1)  # Subtract header
        else:
            file_size = 0
            record_count = 0

        return {
            "file_path": str(self.output_path),
            "file_exists": self._file_exists,
            "file_size": file_size,
            "record_count": record_count,
            "fieldnames": self.FIELDNAMES,
        }
