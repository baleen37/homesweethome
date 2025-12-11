"""Base CSV writer with common functionality for all CSV writers.

This module provides BaseCSVWriter class that contains common patterns
for file I/O operations, CSV writer setup, and data normalization.
"""

import csv
from pathlib import Path
from typing import Any, List, Dict
from abc import ABC, abstractmethod


class BaseCSVWriter(ABC):
    """Base class for CSV writers with common functionality.

    Provides common patterns for:
    - File I/O operations (opening, closing files)
    - CSV writer setup
    - Header and row writing patterns
    - Data normalization
    - Error handling
    """

    # Subclasses must define their fieldnames
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

        Subclasses must implement this to handle their specific
        data normalization requirements.

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

    def write(self, data: List[Dict[str, Any]], mode: str = "w", write_header: bool = None) -> None:
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

        with open(self.output_path, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)

            if write_header:
                writer.writeheader()

            # Normalize and write data
            normalized_data = [self._normalize_row(row) for row in data]
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
        """Apply common normalization rules to a row.

        This handles generic normalization that applies to most CSV writers:
        - Convert None to empty string
        - Convert boolean values to lowercase strings
        - Convert numeric values to appropriate types

        Args:
            row: Data row to normalize

        Returns:
            Row with common fields normalized
        """
        normalized = {}

        for field in self.FIELDNAMES:
            value = row.get(field, "")

            if value is None:
                # Convert None to empty string
                normalized[field] = ""
            elif isinstance(value, bool):
                # Convert boolean to lowercase string
                normalized[field] = str(value).lower()
            elif isinstance(value, (int, float)):
                # Keep numeric values as-is
                normalized[field] = value
            else:
                # Convert everything else to string
                normalized[field] = str(value)

        return normalized

    def get_file_info(self) -> Dict[str, Any]:
        """Get information about the CSV file.

        Returns:
            Dictionary with file information (size, record count, etc.)
        """
        info = {
            "file_path": str(self.output_path),
            "file_exists": self._file_exists,
            "file_size": 0,
            "record_count": 0,
            "fieldnames": self.FIELDNAMES.copy(),
        }

        if self._file_exists:
            try:
                info["file_size"] = self.output_path.stat().st_size

                # Count records (excluding header)
                with open(self.output_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if lines:
                        info["record_count"] = len(lines) - 1
            except Exception:
                # If we can't read the file, just return basic info
                pass

        return info
