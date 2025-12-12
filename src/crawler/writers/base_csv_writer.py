"""Base CSV writer with common functionality for all CSV writers.

This module provides BaseCSVWriter class that contains common patterns
for file I/O operations, CSV writer setup, and data normalization.
"""

import csv
from pathlib import Path
from typing import Any, List, Dict, Optional
from abc import ABC, abstractmethod
import structlog
import re

from crawler.writers.data_transformation_strategy import (
    DataTransformationStrategy,
)
from crawler.validators.csv_validator import (
    CSVValidator,
    ValidationResult,
    ValidationError,
    ValidationStatus,
)
from crawler.writers.csv_header_standard import (
    CSVType,
    HeaderStandardRegistry,
    ensure_header_consistency,
)

logger = structlog.get_logger().bind(component="BaseCSVWriter")


class BaseCSVWriter(ABC):
    """Base class for CSV writers with common functionality.

    Provides common patterns for:
    - File I/O operations (opening, closing files)
    - CSV writer setup
    - Header and row writing patterns
    - Data normalization through strategy pattern
    - Error handling

    The class now uses the Strategy pattern for data transformation,
    allowing different normalization logic to be injected.
    """

    # Subclasses can define default fieldnames (deprecated in favor of strategy)
    FIELDNAMES: List[str] = []

    def __init__(
        self,
        output_path: Path,
        strategy: Optional[DataTransformationStrategy] = None,
        validator: Optional[CSVValidator] = None,
        enable_validation: bool = True,
        csv_type: Optional[CSVType] = None,
    ) -> None:
        """Initialize BaseCSVWriter.

        Args:
            output_path: Path to the CSV file
            strategy: Data transformation strategy to use. If None, subclasses
                     should override _normalize_row for backward compatibility.
            validator: CSV validator to use for data validation
            enable_validation: Whether to enable validation during writes
            csv_type: Type of CSV for header standardization
        """
        self.output_path = output_path
        self._file_exists = output_path.exists()
        self._strategy = strategy
        self._validator = validator
        self._enable_validation = enable_validation
        self._csv_type = csv_type
        self._validation_errors: List[ValidationError] = []
        self._validation_warnings: List[ValidationError] = []

        # If no validator provided but csv_type is specified, create one
        if not self._validator and self._csv_type:
            from crawler.validators.csv_validator import CSVValidator

            field_definitions = HeaderStandardRegistry.get_field_definitions(self._csv_type)
            if field_definitions:
                self._validator = CSVValidator(field_definitions)

        # If no strategy provided but csv_type is specified, get fieldnames from standard
        if not self._strategy and self._csv_type and not self.FIELDNAMES:
            self.FIELDNAMES = HeaderStandardRegistry.get_fieldnames(self._csv_type)

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

    @property
    def validation_errors(self) -> List[ValidationError]:
        """Get accumulated validation errors."""
        return self._validation_errors.copy()

    @property
    def validation_warnings(self) -> List[ValidationError]:
        """Get accumulated validation warnings."""
        return self._validation_warnings.copy()

    def clear_validation_logs(self) -> None:
        """Clear accumulated validation errors and warnings."""
        self._validation_errors.clear()
        self._validation_warnings.clear()

    def _normalize_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a single row of data.

        This method now uses the strategy pattern if a strategy is set.
        For backward compatibility, subclasses can still override this method.

        Args:
            row: Raw data row to normalize

        Returns:
            Normalized data row with all fields present
        """
        # 진단 로깅: 정규화 전
        logger.info(
            "diagnostic_normalize_row_start",
            component="BaseCSVWriter",
            strategy_name=self._strategy.__class__.__name__ if self._strategy else None,
            input_keys=list(row.keys()),
            input_sample=row,
        )

        if self._strategy:
            # Use strategy for transformation
            fieldnames = self._strategy.get_fieldnames()
            result = self._strategy.transform(row, fieldnames)

            # 진단 로깅: 정규화 후
            logger.info(
                "diagnostic_normalize_row_complete",
                component="BaseCSVWriter",
                strategy_name=self._strategy.__class__.__name__,
                fieldnames=fieldnames,
                output_keys=list(result.keys()) if isinstance(result, dict) else None,
                output_sample=result,
            )

            return result

        # Fall back to abstract method for backward compatibility
        result = self._normalize_row_legacy(row)

        # 진단 로깅: legacy 정규화 후
        logger.info(
            "diagnostic_normalize_row_legacy_complete",
            component="BaseCSVWriter",
            output_keys=list(result.keys()) if isinstance(result, dict) else None,
            output_sample=result,
        )

        return result

    @abstractmethod
    def _normalize_row_legacy(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy normalization method for backward compatibility.

        Subclasses should implement this if no strategy is provided.
        This method will be called when _normalize_row falls back
        due to no strategy being set.

        Args:
            row: Raw data row to normalize

        Returns:
            Normalized data row with all fields present
        """
        pass

    def get_fieldnames(self) -> List[str]:
        """Get field names based on strategy or class attribute."""
        if self._strategy:
            fieldnames = self._strategy.get_fieldnames()
        else:
            fieldnames = self.FIELDNAMES.copy()

        # If csv_type is specified, ensure we follow standard field order
        if self._csv_type:
            return self._get_standardized_fieldnames(fieldnames)

        return fieldnames

    def _get_standardized_fieldnames(self, fieldnames: List[str]) -> List[str]:
        """Get fieldnames in standard order for the CSV type.

        Args:
            fieldnames: List of fieldnames to standardize

        Returns:
            Fieldnames in standard order with extra fields appended
        """
        standard_fieldnames = HeaderStandardRegistry.get_fieldnames(self._csv_type)

        # Create ordered list following standard order
        ordered_fieldnames = [field for field in standard_fieldnames if field in fieldnames]

        # Append any extra fields not in standard
        ordered_fieldnames.extend(
            [field for field in fieldnames if field not in ordered_fieldnames]
        )

        return ordered_fieldnames

    def _validate_row(self, row: Dict[str, Any], row_number: int) -> bool:
        """Validate a single row of data.

        Args:
            row: Data row to validate
            row_number: Row number for error reporting

        Returns:
            True if row is valid (or validation is disabled), False otherwise
        """
        if not self._enable_validation or not self._validator:
            return True

        result = self._validator.validate_row(row, row_number)

        # Collect errors and warnings
        self._validation_errors.extend(result.errors)
        self._validation_warnings.extend(result.warnings)

        # Log validation issues
        if result.errors:
            logger.error(
                "row_validation_failed",
                row_number=row_number,
                error_count=len(result.errors),
                errors=[e.error_message for e in result.errors],
            )

        if result.warnings:
            logger.warning(
                "row_validation_warnings",
                row_number=row_number,
                warning_count=len(result.warnings),
                warnings=[w.error_message for w in result.warnings],
            )

        return result.status != ValidationStatus.FAILED

    def write_header(self) -> None:
        """Write CSV header to file.

        Creates a new file with only the header row.
        """
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get fieldnames using get_fieldnames method
        fieldnames = self.get_fieldnames()

        # Validate fieldnames if csv_type is specified
        if self._csv_type:
            self._validate_fieldnames(fieldnames)

        with open(self.output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

        self._file_exists = True

    def write(
        self,
        data: List[Dict[str, Any]],
        mode: str = "w",
        write_header: bool = None,
        skip_invalid: bool = True,
    ) -> None:
        """Write data to CSV file with optional validation.

        Args:
            data: List of data rows to write
            mode: Write mode ('w' for overwrite, 'a' for append)
            write_header: Whether to write header (None means auto-detect)
            skip_invalid: Whether to skip invalid rows (True) or raise exception (False)
        """
        # 진단 로깅: 쓰기 시작
        logger.info(
            "write_operation_start",
            component="BaseCSVWriter",
            output_path=str(self.output_path),
            mode=mode,
            input_count=len(data),
            write_header=write_header,
            file_exists_before=self._file_exists,
            validation_enabled=self._enable_validation,
            skip_invalid=skip_invalid,
        )

        if not data:
            logger.info("write_operation_skip", reason="empty_data")
            return

        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get fieldnames using get_fieldnames method
        fieldnames = self.get_fieldnames()

        # Auto-detect header writing if not specified
        if write_header is None:
            write_header = mode == "w"

        # Apply header standardization if csv_type is specified
        if self._csv_type:
            standardized_data = []
            for i, row in enumerate(data, start=1):
                try:
                    standardized_row = ensure_header_consistency(row, self._csv_type)
                    standardized_data.append(standardized_row)
                except Exception as e:
                    logger.error(
                        "header_standardization_failed", row_number=i, error=str(e), skipping=True
                    )
                    if not skip_invalid:
                        raise
                    # Skip this row if standardization fails
                    continue
            data = standardized_data

        # Validate and filter data if validation is enabled
        valid_data = []
        invalid_rows = []

        if self._enable_validation and self._validator:
            for i, row in enumerate(data, start=1):
                if self._validate_row(row, i):
                    valid_data.append(row)
                else:
                    invalid_rows.append((i, row))
                    if not skip_invalid:
                        error_msg = f"Validation failed for row {i}: {[e.error_message for e in self._validation_errors if e.row_number == i]}"
                        logger.error("write_operation_failed", error=error_msg)
                        raise ValueError(error_msg)
        else:
            valid_data = data

        # Log validation results
        if invalid_rows:
            logger.warning(
                "rows_skipped_due_to_validation",
                skipped_count=len(invalid_rows),
                valid_count=len(valid_data),
                invalid_row_numbers=[row[0] for row in invalid_rows[:10]],  # Log first 10
            )

        # Normalize valid data
        normalized_data = []
        for row in valid_data:
            try:
                normalized = self._normalize_row(row)
                normalized_data.append(normalized)
            except Exception as e:
                logger.error("normalization_failed", row_data=row, error=str(e), skipping=True)
                if not skip_invalid:
                    raise
                # Skip this row if normalization fails
                continue

        # 진단 로깅: 정규화된 데이터
        logger.info(
            "data_normalized",
            component="BaseCSVWriter",
            input_count=len(data),
            valid_count=len(valid_data),
            normalized_count=len(normalized_data),
            skipped_count=len(data) - len(normalized_data),
            fieldnames=fieldnames,
        )

        # Write to file
        try:
            with open(self.output_path, mode, newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)

                if write_header:
                    writer.writeheader()

                if normalized_data:
                    writer.writerows(normalized_data)

            self._file_exists = True

            # 진단 로깅: 쓰기 완료
            logger.info(
                "write_operation_complete",
                component="BaseCSVWriter",
                output_path=str(self.output_path),
                file_size=self.output_path.stat().st_size if self.output_path.exists() else 0,
                rows_written=len(normalized_data),
            )

        except Exception as e:
            logger.error(
                "write_operation_failed",
                output_path=str(self.output_path),
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def append(self, data: List[Dict[str, Any]], skip_invalid: bool = True) -> None:
        """Append data to existing file or create new file.

        Args:
            data: List of data rows to append
            skip_invalid: Whether to skip invalid rows (True) or raise exception (False)
        """
        if not self._file_exists:
            # File doesn't exist, create with header
            self.write(data, mode="w", skip_invalid=skip_invalid)
        else:
            # Append to existing file
            self.write(data, mode="a", write_header=False, skip_invalid=skip_invalid)

    def validate_existing_file(self) -> ValidationResult:
        """Validate the existing CSV file.

        Returns:
            ValidationResult with validation details
        """
        if not self._file_exists or not self._validator:
            result = ValidationResult(
                file_path=str(self.output_path), status=ValidationStatus.SKIPPED
            )
            if not self._file_exists:
                result.add_error(
                    ValidationError(
                        row_number=0,
                        field_name="file",
                        field_value=None,
                        error_message="File does not exist",
                    )
                )
            else:
                result.add_error(
                    ValidationError(
                        row_number=0,
                        field_name="validator",
                        field_value=None,
                        error_message="No validator configured",
                    )
                )
            return result

        return self._validator.validate_file(self.output_path)

    def repair_file(self, backup_suffix: str = ".backup") -> bool:
        """Attempt to repair the existing CSV file by removing invalid rows.

        Args:
            backup_suffix: Suffix to add to backup file

        Returns:
            True if repair was successful, False otherwise
        """
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
        if validation_result.status == ValidationStatus.PASSED:
            logger.info("no_repair_needed", file_path=str(self.output_path))
            return True

        # Read file and filter valid rows
        try:
            with open(self.output_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames or []

                valid_rows = []
                invalid_row_numbers = set(e.row_number for e in validation_result.errors)

                for row_number, row in enumerate(reader, start=2):  # Start at 2 (after header)
                    if row_number not in invalid_row_numbers:
                        valid_rows.append(row)

                # Write back only valid rows
                if valid_rows:
                    with open(self.output_path, "w", newline="", encoding="utf-8") as f:
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

    def ensure_file_exists(self) -> None:
        """Ensure CSV file exists, create empty file with header if not."""
        if not self._file_exists:
            self.write_header()

    def _validate_fieldnames(self, fieldnames: List[str]) -> None:
        """Validate that fieldnames meet the standard requirements.

        Args:
            fieldnames: List of field names to validate

        Raises:
            ValueError: If required fields are missing
        """
        if not self._csv_type:
            return

        required_fields = HeaderStandardRegistry.get_required_fields(self._csv_type)

        # Check for missing required fields
        missing_fields = set(required_fields) - set(fieldnames)
        if missing_fields:
            error_msg = (
                f"Missing required fields for {self._csv_type.value}: {sorted(missing_fields)}"
            )
            logger.error("fieldnames_validation_failed", missing_fields=list(missing_fields))
            raise ValueError(error_msg)

        # Log any extra fields (not an error, just informational)
        standard_fields = set(HeaderStandardRegistry.get_fieldnames(self._csv_type))
        extra_fields = set(fieldnames) - standard_fields
        if extra_fields:
            logger.info(
                "extra_fields_present",
                csv_type=self._csv_type.value,
                extra_fields=list(extra_fields),
            )

    def _normalize_common_fields(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Apply common normalization rules to a row.

        Enhanced normalization with better type handling and CSV escaping:
        - Convert None to empty string
        - Convert boolean values to lowercase 'true'/'false' strings
        - Preserve integer values as-is (for tests that expect type preservation)
        - Format numeric values appropriately
        - Escape CSV special characters
        - Handle date/time formatting
        - Clean string values (trim, normalize whitespace)

        Args:
            row: Data row to normalize

        Returns:
            Row with common fields normalized
        """
        normalized = {}

        for field in self.FIELDNAMES:
            value = row.get(field, "")

            # Handle None values
            if value is None or value == "":
                normalized[field] = ""
                continue

            # Handle boolean values
            if isinstance(value, bool):
                # Use lowercase 'true'/'false' for CSV compatibility
                normalized[field] = "true" if value else "false"
                continue

            # Handle numeric values
            if isinstance(value, (int, float)):
                # Special formatting for certain field types
                field_lower = field.lower()
                if any(
                    keyword in field_lower for keyword in ["가", "price", "amount", "fee", "비용"]
                ):
                    # Price fields - format as integer with no decimals
                    normalized[field] = (
                        f"{int(value):,}" if isinstance(value, (int, float)) else str(value)
                    )
                elif "율" in field or "ratio" in field_lower or "rate" in field_lower:
                    # Percentage fields - format with 2 decimal places
                    normalized[field] = (
                        f"{float(value):.2f}" if isinstance(value, (int, float)) else str(value)
                    )
                elif any(keyword in field_lower for keyword in ["면적", "area"]):
                    # Area fields - format with 1 decimal place
                    normalized[field] = (
                        f"{float(value):.1f}" if isinstance(value, (int, float)) else str(value)
                    )
                else:
                    # For tests, preserve integer type when possible
                    # But CSV DictWriter will convert to string anyway
                    normalized[field] = value
                continue

            # Handle dates and timestamps
            if isinstance(value, str):
                # Detect date patterns and normalize
                value = self._normalize_date_string(value)
                # Clean and escape string value
                value = self._clean_and_escape_string(value)
                normalized[field] = value
                continue

            # Handle other types (convert to string)
            normalized[field] = self._clean_and_escape_string(str(value))

        return normalized

    def _normalize_date_string(self, date_str: str) -> str:
        """Normalize date string to consistent format.

        Detects various date formats and converts to YYYY-MM-DD or YYYY-MM-DD HH:MM:SS.

        Args:
            date_str: Input date string

        Returns:
            Normalized date string
        """
        import datetime

        if not date_str or date_str == "":
            return ""

        # Common date formats to try
        date_formats = [
            "%Y-%m-%d %H:%M:%S",  # Already in correct format
            "%Y-%m-%d",  # Date only
            "%Y/%m/%d",  # Slash separator
            "%Y.%m.%d",  # Dot separator
            "%Y%m%d",  # No separator
            "%Y-%m-%d %H:%M",  # No seconds
        ]

        for fmt in date_formats:
            try:
                dt = datetime.datetime.strptime(date_str.strip(), fmt)
                # If original format included time, return with time
                if "%H" in fmt:
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        # If no format matched, return original string
        return date_str

    def _clean_and_escape_string(self, value: str) -> str:
        """Clean and escape string value for CSV output.

        Args:
            value: String value to clean and escape

        Returns:
            Cleaned and escaped string
        """
        if not value:
            return ""

        # Normalize whitespace
        value = re.sub(r"\s+", " ", value.strip())

        # Handle special characters that might cause CSV issues
        # If value contains comma, newline, or quote, wrap in quotes
        if any(char in value for char in [",", "\n", "\r", '"']):
            # Escape existing quotes by doubling them
            value = value.replace('"', '""')
            # Wrap in quotes
            value = f'"{value}"'

        return value

    def get_file_info(self) -> Dict[str, Any]:
        """Get information about the CSV file.

        Returns:
            Dictionary with file information (size, record count, etc.)
        """
        # Get fieldnames using get_fieldnames method
        fieldnames = self.get_fieldnames()

        info = {
            "file_path": str(self.output_path),
            "file_exists": self._file_exists,
            "file_size": 0,
            "record_count": 0,
            "fieldnames": fieldnames.copy(),
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
