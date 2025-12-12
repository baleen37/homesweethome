"""CSV data validation utilities

Provides comprehensive validation for CSV data including header validation,
data type checking, and consistency verification.
"""

import csv
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Validation result status"""

    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


class DataType(Enum):
    """Expected data types for CSV fields"""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    EMAIL = "email"
    PHONE = "phone"
    POSTAL_CODE = "postal_code"


@dataclass(frozen=True)
class FieldDefinition:
    """Definition of a CSV field with validation rules"""

    name: str
    data_type: DataType
    required: bool = True
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    allowed_values: Optional[Set[str]] = None
    pattern: Optional[str] = None  # Regex pattern
    description: Optional[str] = None


@dataclass
class ValidationError:
    """Represents a validation error"""

    row_number: int
    field_name: str
    field_value: Any
    error_message: str
    severity: ValidationStatus = ValidationStatus.FAILED


@dataclass
class ValidationResult:
    """Result of CSV validation"""

    file_path: str
    status: ValidationStatus
    total_rows: int = 0
    valid_rows: int = 0
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    missing_headers: Set[str] = field(default_factory=set)
    extra_headers: Set[str] = field(default_factory=set)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    @property
    def error_count(self) -> int:
        """Get total error count"""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Get total warning count"""
        return len(self.warnings)

    @property
    def validation_rate(self) -> float:
        """Calculate validation success rate"""
        if self.total_rows == 0:
            return 1.0
        return self.valid_rows / self.total_rows

    def is_valid(self) -> bool:
        """Check if validation passed without errors"""
        return len(self.errors) == 0

    def add_error(self, error: ValidationError):
        """Add a validation error"""
        self.errors.append(error)

    def add_warning(self, warning: ValidationError):
        """Add a validation warning"""
        warning.severity = ValidationStatus.WARNING
        self.warnings.append(warning)

    def finish(self):
        """Mark validation as complete"""
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        logger.info(
            "csv_validation_completed",
            file_path=self.file_path,
            duration_seconds=duration,
            total_rows=self.total_rows,
            valid_rows=self.valid_rows,
            error_count=self.error_count,
            warning_count=self.warning_count,
            validation_rate=self.validation_rate,
        )


class CSVFieldValidator:
    """Validator for individual CSV fields"""

    def __init__(self, field_def: FieldDefinition):
        """Initialize validator for a field"""
        self.field_def = field_def

    def validate(self, value: Any, row_number: int) -> List[ValidationError]:
        """Validate a field value"""
        errors = []

        # Check if required field is missing
        if self.field_def.required and (value is None or value == ""):
            errors.append(
                ValidationError(
                    row_number=row_number,
                    field_name=self.field_def.name,
                    field_value=value,
                    error_message=f"Required field '{self.field_def.name}' is missing or empty",
                )
            )
            return errors

        # Skip validation if field is optional and empty
        if not self.field_def.required and (value is None or value == ""):
            return errors

        # Convert value to string for validation
        str_value = str(value).strip()

        # Length validation
        if self.field_def.min_length is not None and len(str_value) < self.field_def.min_length:
            errors.append(
                ValidationError(
                    row_number=row_number,
                    field_name=self.field_def.name,
                    field_value=value,
                    error_message=f"Field '{self.field_def.name}' is too short (min: {self.field_def.min_length})",
                )
            )

        if self.field_def.max_length is not None and len(str_value) > self.field_def.max_length:
            errors.append(
                ValidationError(
                    row_number=row_number,
                    field_name=self.field_def.name,
                    field_value=value,
                    error_message=f"Field '{self.field_def.name}' is too long (max: {self.field_def.max_length})",
                )
            )

        # Data type validation
        type_error = self._validate_type(str_value)
        if type_error:
            errors.append(
                ValidationError(
                    row_number=row_number,
                    field_name=self.field_def.name,
                    field_value=value,
                    error_message=type_error,
                )
            )

        # Range validation
        range_error = self._validate_range(str_value)
        if range_error:
            errors.append(
                ValidationError(
                    row_number=row_number,
                    field_name=self.field_def.name,
                    field_value=value,
                    error_message=range_error,
                )
            )

        # Allowed values validation
        if self.field_def.allowed_values and str_value not in self.field_def.allowed_values:
            errors.append(
                ValidationError(
                    row_number=row_number,
                    field_name=self.field_def.name,
                    field_value=value,
                    error_message=f"Value '{str_value}' not in allowed values: {self.field_def.allowed_values}",
                )
            )

        # Pattern validation
        if self.field_def.pattern:
            import re

            if not re.match(self.field_def.pattern, str_value):
                errors.append(
                    ValidationError(
                        row_number=row_number,
                        field_name=self.field_def.name,
                        field_value=value,
                        error_message=f"Value '{str_value}' does not match required pattern",
                    )
                )

        return errors

    def _validate_type(self, value: str) -> Optional[str]:
        """Validate data type"""
        if self.field_def.data_type == DataType.INTEGER:
            try:
                int(value)
            except ValueError:
                return f"Value '{value}' is not a valid integer"

        elif self.field_def.data_type == DataType.FLOAT:
            try:
                float(value)
            except ValueError:
                return f"Value '{value}' is not a valid number"

        elif self.field_def.data_type == DataType.BOOLEAN:
            if value.lower() not in ["true", "false", "1", "0", "yes", "no"]:
                return f"Value '{value}' is not a valid boolean"

        elif self.field_def.data_type == DataType.DATE:
            # Try common date formats
            date_formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y-%m-%d %H:%M:%S"]
            valid_date = False
            for fmt in date_formats:
                try:
                    datetime.strptime(value, fmt)
                    valid_date = True
                    break
                except ValueError:
                    continue
            if not valid_date:
                return f"Value '{value}' is not a valid date format"

        elif self.field_def.data_type == DataType.EMAIL:
            email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if not re.match(email_pattern, value):
                return f"Value '{value}' is not a valid email address"

        elif self.field_def.data_type == DataType.PHONE:
            phone_pattern = r"^\d{2,4}-?\d{3,4}-?\d{4}$"
            if not re.match(phone_pattern, value.replace(" ", "")):
                return f"Value '{value}' is not a valid phone number"

        elif self.field_def.data_type == DataType.POSTAL_CODE:
            postal_pattern = r"^\d{5}$|^\d{3}-\d{3}$"
            if not re.match(postal_pattern, value):
                return f"Value '{value}' is not a valid postal code"

        return None

    def _validate_range(self, value: str) -> Optional[str]:
        """Validate numeric range"""
        if self.field_def.data_type in [DataType.INTEGER, DataType.FLOAT]:
            try:
                num_value = (
                    float(value) if self.field_def.data_type == DataType.FLOAT else int(value)
                )

                if self.field_def.min_value is not None and num_value < self.field_def.min_value:
                    return f"Value {num_value} is below minimum {self.field_def.min_value}"

                if self.field_def.max_value is not None and num_value > self.field_def.max_value:
                    return f"Value {num_value} is above maximum {self.field_def.max_value}"
            except ValueError:
                pass  # Type error already handled

        return None


class CSVValidator:
    """Comprehensive CSV validator"""

    def __init__(self, field_definitions: List[FieldDefinition]):
        """Initialize validator with field definitions"""
        self.field_definitions = {f.name: f for f in field_definitions}
        self.field_validators = {f.name: CSVFieldValidator(f) for f in field_definitions}
        self.required_headers = {f.name for f in field_definitions if f.required}

    def validate_file(self, file_path: Path, encoding: str = "utf-8") -> ValidationResult:
        """Validate an entire CSV file"""
        result = ValidationResult(file_path=str(file_path), status=ValidationStatus.PASSED)

        try:
            with open(file_path, "r", newline="", encoding=encoding) as csvfile:
                # Detect delimiter
                sample = csvfile.read(1024)
                csvfile.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter

                reader = csv.DictReader(csvfile, delimiter=delimiter)

                # Validate headers
                headers = set(reader.fieldnames or [])
                result.missing_headers = self.required_headers - headers
                result.extra_headers = headers - set(self.field_definitions.keys())

                if result.missing_headers:
                    result.status = ValidationStatus.FAILED
                    for header in result.missing_headers:
                        result.add_error(
                            ValidationError(
                                row_number=0,
                                field_name=header,
                                field_value=None,
                                error_message=f"Required header '{header}' is missing",
                            )
                        )

                # Validate rows
                for row_number, row in enumerate(reader, start=2):  # Start at 2 (after header)
                    result.total_rows += 1
                    row_valid = True

                    for field_name, field_def in self.field_definitions.items():
                        # Skip validation for missing extra headers
                        if field_name not in headers:
                            continue

                        value = row.get(field_name, "")

                        # Validate field
                        errors = self.field_validators[field_name].validate(value, row_number)
                        for error in errors:
                            if error.severity == ValidationStatus.FAILED:
                                result.add_error(error)
                                row_valid = False
                            else:
                                result.add_warning(error)

                    if row_valid:
                        result.valid_rows += 1

        except Exception as e:
            result.status = ValidationStatus.FAILED
            result.add_error(
                ValidationError(
                    row_number=0,
                    field_name="file",
                    field_value=None,
                    error_message=f"Failed to read CSV file: {str(e)}",
                )
            )

        result.finish()
        return result

    def validate_row(self, row: Dict[str, Any], row_number: int) -> ValidationResult:
        """Validate a single row of data"""
        result = ValidationResult(file_path="memory", status=ValidationStatus.PASSED, total_rows=1)

        row_valid = True

        # Check all required fields are present
        for field_name, field_validator in self.field_validators.items():
            if field_name in row:
                # Field exists, validate its value
                errors = field_validator.validate(row[field_name], row_number)
                for error in errors:
                    if error.severity == ValidationStatus.FAILED:
                        result.add_error(error)
                        row_valid = False
                    else:
                        result.add_warning(error)
            else:
                # Field is missing from row
                if field_validator.field_def.required:
                    # Required field is missing
                    result.add_error(
                        ValidationError(
                            row_number=row_number,
                            field_name=field_name,
                            field_value=None,
                            error_message=f"Required field '{field_name}' is missing",
                        )
                    )
                    row_valid = False
                # Optional fields that are missing are not an error

        if row_valid:
            result.valid_rows = 1
        else:
            result.status = ValidationStatus.FAILED

        return result

    def get_field_definition(self, field_name: str) -> Optional[FieldDefinition]:
        """Get field definition by name"""
        return self.field_definitions.get(field_name)


# Predefined field definitions for common CSV formats
COMPLEX_FIELD_DEFINITIONS = [
    FieldDefinition(
        name="complex_id",
        data_type=DataType.STRING,
        required=True,
        min_length=1,
        max_length=50,
        description="Unique identifier for the apartment complex",
    ),
    FieldDefinition(
        name="complex_name",
        data_type=DataType.STRING,
        required=True,
        min_length=1,
        max_length=200,
        description="Name of the apartment complex",
    ),
    FieldDefinition(
        name="address",
        data_type=DataType.STRING,
        required=True,
        min_length=5,
        max_length=500,
        description="Full address of the complex",
    ),
    FieldDefinition(
        name="latitude",
        data_type=DataType.FLOAT,
        required=False,
        min_value=-90,
        max_value=90,
        description="Latitude coordinate",
    ),
    FieldDefinition(
        name="longitude",
        data_type=DataType.FLOAT,
        required=False,
        min_value=-180,
        max_value=180,
        description="Longitude coordinate",
    ),
    FieldDefinition(
        name="build_year",
        data_type=DataType.INTEGER,
        required=False,
        min_value=1900,
        max_value=2030,
        description="Year the complex was built",
    ),
    FieldDefinition(
        name="households",
        data_type=DataType.INTEGER,
        required=False,
        min_value=1,
        max_value=10000,
        description="Number of households in the complex",
    ),
    FieldDefinition(
        name="floors",
        data_type=DataType.INTEGER,
        required=False,
        min_value=1,
        max_value=100,
        description="Number of floors",
    ),
    FieldDefinition(
        name="gu_code",
        data_type=DataType.STRING,
        required=False,
        pattern=r"^\d{5}$",
        description="Administrative district code (5 digits)",
    ),
    FieldDefinition(
        name="dong_code",
        data_type=DataType.STRING,
        required=False,
        pattern=r"^\d{8}$",
        description="Administrative dong code (8 digits)",
    ),
]

TRANSACTION_FIELD_DEFINITIONS = [
    FieldDefinition(
        name="complex_id",
        data_type=DataType.STRING,
        required=True,
        min_length=1,
        max_length=50,
        description="Unique identifier for the apartment complex",
    ),
    FieldDefinition(
        name="complex_name",
        data_type=DataType.STRING,
        required=True,
        min_length=1,
        max_length=200,
        description="Name of the apartment complex",
    ),
    FieldDefinition(
        name="pyeong_type_number",
        data_type=DataType.INTEGER,
        required=True,
        min_value=1,
        max_value=100,
        description="Pyeong type number (e.g., 33 for 33평형)",
    ),
    FieldDefinition(
        name="pyeong_name",
        data_type=DataType.STRING,
        required=False,
        max_length=50,
        description="Pyeong type name (e.g., '33평형')",
    ),
    FieldDefinition(
        name="trade_type",
        data_type=DataType.STRING,
        required=True,
        allowed_values={"A1", "B1", "B2", "매매", "전세", "월세"},
        description="Trade type code",
    ),
    FieldDefinition(
        name="trade_type_name",
        data_type=DataType.STRING,
        required=True,
        allowed_values={"매매", "전세", "월세", "일반거래"},
        description="Trade type name",
    ),
    FieldDefinition(
        name="trade_date", data_type=DataType.DATE, required=True, description="Date of the trade"
    ),
    FieldDefinition(
        name="trade_year",
        data_type=DataType.INTEGER,
        required=True,
        min_value=2000,
        max_value=2030,
        description="Year of the trade",
    ),
    FieldDefinition(
        name="floor",
        data_type=DataType.INTEGER,
        required=False,
        min_value=-2,
        max_value=100,
        description="Floor number (negative for basement)",
    ),
    FieldDefinition(
        name="deal_price",
        data_type=DataType.INTEGER,
        required=False,
        min_value=0,
        max_value=10000000,
        description="Deal price in Korean Won",
    ),
    FieldDefinition(
        name="deposit",
        data_type=DataType.INTEGER,
        required=False,
        min_value=0,
        max_value=10000000,
        description="Deposit amount in Korean Won",
    ),
    FieldDefinition(
        name="monthly_rent",
        data_type=DataType.INTEGER,
        required=False,
        min_value=0,
        max_value=1000000,
        description="Monthly rent in Korean Won",
    ),
]


def create_complexes_validator() -> CSVValidator:
    """Create a validator for complexes.csv"""
    return CSVValidator(COMPLEX_FIELD_DEFINITIONS)


def create_transactions_validator() -> CSVValidator:
    """Create a validator for transactions.csv"""
    return CSVValidator(TRANSACTION_FIELD_DEFINITIONS)
