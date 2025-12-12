"""CSV Header Standardization module

This module provides standardized header definitions and utilities
for ensuring consistent CSV format across the application.
"""

from enum import Enum
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

from crawler.validators.csv_validator import FieldDefinition, DataType


class CSVType(Enum):
    """Types of CSV files supported"""

    COMPLEXES = "complexes"
    TRANSACTIONS = "transactions"


@dataclass
class HeaderStandard:
    """Standard header definition for a CSV type"""

    csv_type: CSVType
    field_definitions: List[FieldDefinition]
    description: str
    version: str = "1.0"


# Standardized header definitions for complexes.csv
COMPLEXES_HEADER_STANDARD = HeaderStandard(
    csv_type=CSVType.COMPLEXES,
    field_definitions=[
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
            name="real_estate_type",
            data_type=DataType.STRING,
            required=True,
            allowed_values={"아파트", "오피스텔", "연립다세대", "단독다가구"},
            description="Type of real estate",
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
            name="completion_year_month",
            data_type=DataType.STRING,
            required=False,
            pattern=r"^\d{6}$",
            description="Completion date in YYYYMM format",
        ),
        FieldDefinition(
            name="total_dong_count",
            data_type=DataType.INTEGER,
            required=False,
            min_value=1,
            max_value=1000,
            description="Number of buildings (dongs)",
        ),
        FieldDefinition(
            name="total_household_count",
            data_type=DataType.INTEGER,
            required=False,
            min_value=1,
            max_value=10000,
            description="Total number of households",
        ),
        FieldDefinition(
            name="min_area",
            data_type=DataType.FLOAT,
            required=False,
            min_value=0,
            max_value=1000,
            description="Minimum exclusive area in square meters",
        ),
        FieldDefinition(
            name="max_area",
            data_type=DataType.FLOAT,
            required=False,
            min_value=0,
            max_value=1000,
            description="Maximum exclusive area in square meters",
        ),
        FieldDefinition(
            name="pyeong_types",
            data_type=DataType.STRING,
            required=False,
            max_length=500,
            description="Available pyeong types (e.g., '33평, 59평')",
        ),
        FieldDefinition(
            name="deal_count",
            data_type=DataType.INTEGER,
            required=False,
            min_value=0,
            max_value=10000,
            description="Number of deals in the last 3 months",
        ),
        FieldDefinition(
            name="lease_count",
            data_type=DataType.INTEGER,
            required=False,
            min_value=0,
            max_value=10000,
            description="Number of lease deals in the last 3 months",
        ),
        FieldDefinition(
            name="rent_count",
            data_type=DataType.INTEGER,
            required=False,
            min_value=0,
            max_value=10000,
            description="Number of rent deals in the last 3 months",
        ),
        FieldDefinition(
            name="fetched_at",
            data_type=DataType.STRING,
            required=True,
            pattern=r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$",
            description="Timestamp when data was fetched",
        ),
    ],
    description="Standard header for apartment complexes data",
    version="1.0",
)


# Standardized header definitions for transactions.csv
TRANSACTIONS_HEADER_STANDARD = HeaderStandard(
    csv_type=CSVType.TRANSACTIONS,
    field_definitions=[
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
            allowed_values={"매매", "전세", "월세"},
            description="Trade type (매매/전세/월세)",
        ),
        FieldDefinition(
            name="trade_type_name",
            data_type=DataType.STRING,
            required=True,
            allowed_values={"일반거래", "동일단지", "분양권"},
            description="Trade category",
        ),
        FieldDefinition(
            name="trade_date",
            data_type=DataType.STRING,
            required=True,
            pattern=r"^\d{4}-\d{2}-\d{2}$",
            description="Date of the trade in YYYY-MM-DD format",
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
            description="Deal price in Korean Won (원)",
        ),
        FieldDefinition(
            name="deposit",
            data_type=DataType.INTEGER,
            required=False,
            min_value=0,
            max_value=10000000,
            description="Deposit amount in Korean Won (원)",
        ),
        FieldDefinition(
            name="monthly_rent",
            data_type=DataType.INTEGER,
            required=False,
            min_value=0,
            max_value=1000000,
            description="Monthly rent in Korean Won (원)",
        ),
        FieldDefinition(
            name="trade_category",
            data_type=DataType.STRING,
            required=True,
            allowed_values={"일반거래", "동일단지", "분양권"},
            description="Trade category",
        ),
        FieldDefinition(
            name="is_delete",
            data_type=DataType.BOOLEAN,
            required=True,
            description="Whether this record is marked for deletion",
        ),
        FieldDefinition(
            name="is_renew",
            data_type=DataType.BOOLEAN,
            required=True,
            description="Whether this is a renewed contract",
        ),
    ],
    description="Standard header for real estate transaction data",
    version="1.0",
)


class HeaderStandardRegistry:
    """Registry for CSV header standards"""

    _standards: Dict[CSVType, HeaderStandard] = {
        CSVType.COMPLEXES: COMPLEXES_HEADER_STANDARD,
        CSVType.TRANSACTIONS: TRANSACTIONS_HEADER_STANDARD,
    }

    @classmethod
    def get_standard(cls, csv_type: CSVType) -> Optional[HeaderStandard]:
        """Get header standard for a CSV type"""
        return cls._standards.get(csv_type)

    @classmethod
    def get_fieldnames(cls, csv_type: CSVType) -> List[str]:
        """Get fieldnames for a CSV type"""
        standard = cls.get_standard(csv_type)
        if standard:
            return [field.name for field in standard.field_definitions]
        return []

    @classmethod
    def get_field_definitions(cls, csv_type: CSVType) -> List[FieldDefinition]:
        """Get field definitions for a CSV type"""
        standard = cls.get_standard(csv_type)
        if standard:
            return standard.field_definitions
        return []

    @classmethod
    def get_required_fields(cls, csv_type: CSVType) -> Set[str]:
        """Get required field names for a CSV type"""
        standard = cls.get_standard(csv_type)
        if standard:
            return {field.name for field in standard.field_definitions if field.required}
        return set()

    @classmethod
    def register_standard(cls, standard: HeaderStandard) -> None:
        """Register a new header standard"""
        cls._standards[standard.csv_type] = standard

    @classmethod
    def list_standards(cls) -> Dict[CSVType, str]:
        """List all registered standards with descriptions"""
        return {csv_type: std.description for csv_type, std in cls._standards.items()}


def ensure_header_consistency(data: Dict[str, any], csv_type: CSVType) -> Dict[str, any]:
    """Ensure data conforms to header standard

    Args:
        data: Input data dictionary
        csv_type: Type of CSV being written

    Returns:
        Data adjusted to match header standard
    """
    standard = HeaderStandardRegistry.get_standard(csv_type)
    if not standard:
        return data

    fieldnames = HeaderStandardRegistry.get_fieldnames(csv_type)
    required_fields = HeaderStandardRegistry.get_required_fields(csv_type)

    # Create a new dictionary with only standard fields
    result = {}

    # Copy existing fields that match standard
    for field in fieldnames:
        if field in data:
            result[field] = data[field]
        elif field in required_fields:
            # Add empty string for required fields that are missing
            result[field] = ""
        else:
            # Add empty string for optional fields that are missing
            result[field] = ""

    # Warn about extra fields
    extra_fields = set(data.keys()) - set(fieldnames)
    if extra_fields:
        import structlog

        logger = structlog.get_logger().bind(component="HeaderStandard")
        logger.warning(
            "extra_fields_in_data",
            csv_type=csv_type.value,
            extra_fields=list(extra_fields),
            message="Extra fields will be ignored",
        )

    return result
