"""Unified CSV writer with consolidated functionality.

This module provides UnifiedCSVWriter that consolidates functionality from
BaseCSVWriter and AbstractCSVWriter to eliminate code duplication.
It uses the Strategy pattern for data transformation and provides
comprehensive CSV writing capabilities.
"""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional
import structlog

from crawler.writers.common import normalize_row_legacy
from crawler.writers.data_transformation_strategy import DataTransformationStrategy
from crawler.validators.csv_validator import CSVValidator, ValidationResult
from crawler.writers.csv_header_standard import CSVType, HeaderStandardRegistry

logger = structlog.get_logger().bind(component="UnifiedCSVWriter")


class WriteConfig:
    """Configuration for CSV writing operations."""

    def __init__(
        self,
        encoding: str = "utf-8",
        newline: str = "",
        delimiter: str = ",",
        quotechar: str = '"',
        quoting: int = csv.QUOTE_MINIMAL,
        skip_invalid_rows: bool = True,
        enable_validation: bool = True,
        buffer_size: int = 8192,
    ):
        self.encoding = encoding
        self.newline = newline
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.quoting = quoting
        self.skip_invalid_rows = skip_invalid_rows
        self.enable_validation = enable_validation
        self.buffer_size = buffer_size


class UnifiedCSVWriter:
    """Unified CSV writer with comprehensive functionality.

    This writer consolidates functionality from BaseCSVWriter and AbstractCSVWriter,
    providing:
    - Strategy-based data transformation
    - Configurable validation
    - Flexible file operations
    - Statistics tracking
    - Memory-efficient writing
    """

    def __init__(
        self,
        output_path: Path,
        strategy: Optional[DataTransformationStrategy] = None,
        validator: Optional[CSVValidator] = None,
        csv_type: Optional[CSVType] = None,
        config: Optional[WriteConfig] = None,
    ):
        """Initialize UnifiedCSVWriter.

        Args:
            output_path: Path to the CSV file
            strategy: Data transformation strategy
            validator: CSV validator for data validation
            csv_type: Type of CSV for header standardization
            config: Write configuration
        """
        self.output_path = output_path
        self.config = config or WriteConfig()
        self._strategy = strategy
        self._validator = validator
        self._csv_type = csv_type
        self._file_exists = output_path.exists()

        # Statistics tracking
        self.stats = {
            "rows_written": 0,
            "rows_skipped": 0,
            "validation_errors": 0,
            "validation_warnings": 0,
            "chunks_written": 0,
            "bytes_written": 0,
        }

        # Initialize validator if csv_type is provided
        if not self._validator and self._csv_type:
            field_definitions = HeaderStandardRegistry.get_field_definitions(self._csv_type)
            if field_definitions:
                self._validator = CSVValidator(field_definitions)

    @property
    def strategy(self) -> Optional[DataTransformationStrategy]:
        """Get the current transformation strategy."""
        return self._strategy

    @strategy.setter
    def strategy(self, strategy: DataTransformationStrategy) -> None:
        """Set a new transformation strategy."""
        self._strategy = strategy

    @property
    def validator(self) -> Optional[CSVValidator]:
        """Get the current validator."""
        return self._validator

    @validator.setter
    def validator(self, validator: CSVValidator) -> None:
        """Set a new validator."""
        self._validator = validator

    def get_fieldnames(self) -> List[str]:
        """Get field names based on strategy or CSV type."""
        if self._strategy:
            fieldnames = self._strategy.get_fieldnames()
        elif self._csv_type:
            fieldnames = HeaderStandardRegistry.get_fieldnames(self._csv_type)
        else:
            raise ValueError("Either strategy or csv_type must be provided")

        return fieldnames

    def write_header(self) -> None:
        """Write CSV header to file."""
        self._ensure_directory()

        fieldnames = self.get_fieldnames()

        with open(
            self.output_path,
            mode="w",
            encoding=self.config.encoding,
            newline=self.config.newline,
            buffering=self.config.buffer_size,
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
                delimiter=self.config.delimiter,
                quotechar=self.config.quotechar,
                quoting=self.config.quoting,
            )
            writer.writeheader()

        self._file_exists = True
        logger.info("header_written", file_path=str(self.output_path))

    def write(
        self,
        data: List[Dict[str, Any]],
        mode: str = "w",
        write_header: Optional[bool] = None,
        chunk_size: Optional[int] = None,
    ) -> None:
        """Write data to CSV file.

        Args:
            data: List of data rows to write
            mode: Write mode ('w' for overwrite, 'a' for append)
            write_header: Whether to write header (None for auto-detect)
            chunk_size: Size of chunks for memory-efficient writing
        """
        if not data:
            logger.info("write_skipped", reason="empty_data")
            return

        self._ensure_directory()

        # Auto-detect header writing
        if write_header is None:
            write_header = mode == "w" or not self._file_exists

        # Get fieldnames
        fieldnames = self.get_fieldnames()

        # Process data in chunks if specified
        if chunk_size and len(data) > chunk_size:
            self._write_chunks(data, fieldnames, mode, write_header, chunk_size)
        else:
            self._write_all(data, fieldnames, mode, write_header)

        self._file_exists = True
        logger.info(
            "write_completed",
            file_path=str(self.output_path),
            rows_written=self.stats["rows_written"],
            rows_skipped=self.stats["rows_skipped"],
        )

    def _write_chunks(
        self,
        data: List[Dict[str, Any]],
        fieldnames: List[str],
        mode: str,
        write_header: bool,
        chunk_size: int,
    ) -> None:
        """Write data in chunks for memory efficiency."""
        for i in range(0, len(data), chunk_size):
            chunk = data[i : i + chunk_size]
            chunk_mode = mode if i == 0 else "a"
            chunk_write_header = write_header if i == 0 else False
            self._write_all(chunk, fieldnames, chunk_mode, chunk_write_header)
            self.stats["chunks_written"] += 1

    def _write_all(
        self,
        data: List[Dict[str, Any]],
        fieldnames: List[str],
        mode: str,
        write_header: bool,
    ) -> None:
        """Write all data to file."""
        # Process and validate data
        processed_data = []
        for i, row in enumerate(data, start=1):
            # Validate row
            if not self._validate_row(row, i):
                if self.config.skip_invalid_rows:
                    self.stats["rows_skipped"] += 1
                    continue
                else:
                    raise ValueError(f"Row {i} failed validation")

            # Transform row
            try:
                if self._strategy:
                    transformed = self._strategy.transform(row, fieldnames)
                else:
                    transformed = self._normalize_row_legacy(row, fieldnames)
                processed_data.append(transformed)
            except Exception as e:
                logger.error(
                    "transformation_failed",
                    row_number=i,
                    error=str(e),
                    skipping=True,
                )
                if self.config.skip_invalid_rows:
                    self.stats["rows_skipped"] += 1
                    continue
                else:
                    raise

        # Write to file
        with open(
            self.output_path,
            mode=mode,
            encoding=self.config.encoding,
            newline=self.config.newline,
            buffering=self.config.buffer_size,
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
                delimiter=self.config.delimiter,
                quotechar=self.config.quotechar,
                quoting=self.config.quoting,
            )

            if write_header:
                writer.writeheader()

            if processed_data:
                writer.writerows(processed_data)
                self.stats["rows_written"] += len(processed_data)

                # Update bytes written
                f.flush()
                self.stats["bytes_written"] = f.tell()

    def append(self, data: List[Dict[str, Any]], chunk_size: Optional[int] = None) -> None:
        """Append data to existing file or create new file."""
        if not self._file_exists:
            self.write(data, mode="w", chunk_size=chunk_size)
        else:
            self.write(data, mode="a", write_header=False, chunk_size=chunk_size)

    def _validate_row(self, row: Dict[str, Any], row_number: int) -> bool:
        """Validate a single row of data."""
        if not self.config.enable_validation or not self._validator:
            return True

        result = self._validator.validate_row(row, row_number)
        self.stats["validation_errors"] += len(result.errors)
        self.stats["validation_warnings"] += len(result.warnings)

        # Log validation issues
        if result.errors:
            logger.error(
                "row_validation_failed",
                row_number=row_number,
                error_count=len(result.errors),
            )

        if result.warnings:
            logger.warning(
                "row_validation_warnings",
                row_number=row_number,
                warning_count=len(result.warnings),
            )

        return result.is_valid()

    def _normalize_row_legacy(self, row: Dict[str, Any], fieldnames: List[str]) -> Dict[str, Any]:
        """Legacy normalization method for backward compatibility."""
        return normalize_row_legacy(row, fieldnames)

    def _ensure_directory(self) -> None:
        """Ensure output directory exists."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def get_stats(self) -> Dict[str, Any]:
        """Get writing statistics."""
        stats = self.stats.copy()
        stats["file_exists"] = self._file_exists
        stats["file_path"] = str(self.output_path)

        if self._file_exists:
            stats["file_size"] = self.output_path.stat().st_size

        return stats

    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = {
            "rows_written": 0,
            "rows_skipped": 0,
            "validation_errors": 0,
            "validation_warnings": 0,
            "chunks_written": 0,
            "bytes_written": 0,
        }

    def validate_existing_file(self) -> Optional[ValidationResult]:
        """Validate the existing CSV file."""
        if not self._file_exists or not self._validator:
            return None

        return self._validator.validate_file(self.output_path)

    def repair_file(self, backup_suffix: str = ".backup") -> bool:
        """Repair the existing CSV file by removing invalid rows."""
        if not self._file_exists or not self._validator:
            logger.warning("repair_file_skipped", reason="no_file_or_validator")
            return False

        # Create backup
        backup_path = self.output_path.with_suffix(self.output_path.suffix + backup_suffix)

        try:
            import shutil

            shutil.copy2(self.output_path, backup_path)
            logger.info("backup_created", backup_path=str(backup_path))
        except Exception as e:
            logger.error("backup_failed", error=str(e))
            return False

        # Validate and collect valid rows
        validation_result = self.validate_existing_file()
        if not validation_result or validation_result.is_valid():
            logger.info("no_repair_needed", file_path=str(self.output_path))
            return True

        # Read file and filter valid rows
        try:
            with open(self.output_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames or []

                valid_rows = []
                invalid_row_numbers = set(e.row_number for e in validation_result.errors)

                for row_number, row in enumerate(reader, start=2):
                    if row_number not in invalid_row_numbers:
                        valid_rows.append(row)

                # Write back only valid rows
                if valid_rows:
                    with open(
                        self.output_path,
                        "w",
                        newline="",
                        encoding="utf-8",
                        buffering=self.config.buffer_size,
                    ) as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(valid_rows)

                    logger.info(
                        "file_repaired",
                        original_rows=validation_result.total_rows,
                        valid_rows=len(valid_rows),
                        removed_rows=validation_result.total_rows - len(valid_rows),
                    )
                    return True
                else:
                    logger.warning("no_valid_rows_found", file_path=str(self.output_path))
                    return False

        except Exception as e:
            logger.error("repair_failed", error=str(e))
            # Restore from backup
            try:
                shutil.copy2(backup_path, self.output_path)
                logger.info("backup_restored", backup_path=str(backup_path))
            except Exception as e:
                logger.error("backup_restore_failed", error=str(e))
            return False
