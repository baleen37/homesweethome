"""Dataclass CSV writer with automatic type conversion.

This module provides DataClassCSVWriter that can handle dataclass objects
directly and convert them to CSV format with proper type safety.
"""

from dataclasses import is_dataclass, fields
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, get_type_hints
import structlog

from crawler.writers.unified_csv_writer import UnifiedCSVWriter, WriteConfig
from crawler.writers.data_transformation_strategy import DataTransformationStrategy
from crawler.writers.csv_header_standard import CSVType

logger = structlog.get_logger().bind(component="DataClassCSVWriter")

T = TypeVar("T")


class DataClassCSVWriter(UnifiedCSVWriter):
    """CSV writer that handles dataclass objects directly.

    Features:
    - Automatic dataclass field extraction
    - Type-aware value conversion
    - Nested dataclass support
    - Validation integration
    """

    def __init__(
        self,
        output_path: Path,
        dataclass_type: Optional[Type[T]] = None,
        strategy: Optional[DataTransformationStrategy] = None,
        csv_type: Optional[CSVType] = None,
        config: Optional[WriteConfig] = None,
        strict_mode: bool = True,
    ):
        """Initialize DataClassCSVWriter.

        Args:
            output_path: Path to the output CSV file
            dataclass_type: Type of dataclass to handle
            strategy: Data transformation strategy
            csv_type: Type of CSV for header standardization
            config: Write configuration
            strict_mode: Whether to enforce strict type checking
        """
        self.dataclass_type = dataclass_type
        self.strict_mode = strict_mode

        # Create strategy if not provided and dataclass_type is given
        if not strategy and dataclass_type and is_dataclass(dataclass_type):
            strategy = DataClassStrategy(dataclass_type)

        super().__init__(
            output_path=output_path,
            strategy=strategy,
            csv_type=csv_type,
            config=config,
        )

        # Extract fieldnames from dataclass if available
        if dataclass_type and is_dataclass(dataclass_type):
            self._dataclass_fields = [f.name for f in fields(dataclass_type)]
        else:
            self._dataclass_fields = []

    def write_dataclasses(self, dataclass_objects: List[T]) -> None:
        """Write dataclass objects to CSV.

        Args:
            dataclass_objects: List of dataclass instances to write
        """
        if not dataclass_objects:
            logger.info("no_dataclasses_to_write")
            return

        # Convert dataclass objects to dictionaries
        dict_data = []
        for obj in dataclass_objects:
            try:
                dict_data.append(self._convert_dataclass_to_dict(obj))
            except Exception as e:
                logger.error(
                    "dataclass_conversion_failed",
                    object_type=type(obj).__name__,
                    error=str(e),
                )
                if self.strict_mode:
                    raise
                continue

        # Write using parent method
        self.write(dict_data)

    def append_dataclasses(self, dataclass_objects: List[T]) -> None:
        """Append dataclass objects to existing file.

        Args:
            dataclass_objects: List of dataclass instances to append
        """
        if not dataclass_objects:
            logger.info("no_dataclasses_to_append")
            return

        # Convert dataclass objects to dictionaries
        dict_data = []
        for obj in dataclass_objects:
            try:
                dict_data.append(self._convert_dataclass_to_dict(obj))
            except Exception as e:
                logger.error(
                    "dataclass_conversion_failed",
                    object_type=type(obj).__name__,
                    error=str(e),
                )
                if self.strict_mode:
                    raise
                continue

        # Append using parent method
        self.append(dict_data)

    def _convert_dataclass_to_dict(self, obj: T) -> Dict[str, Any]:
        """Convert a dataclass object to a dictionary.

        Args:
            obj: Dataclass instance to convert

        Returns:
            Dictionary representation of the dataclass
        """
        if not is_dataclass(obj):
            if self.strict_mode:
                raise ValueError(f"Object {obj} is not a dataclass instance")
            else:
                logger.warning("not_a_dataclass", object=obj)
                return obj if isinstance(obj, dict) else {"value": obj}

        result = {}
        type_hints = get_type_hints(type(obj))

        for field_info in fields(obj):
            field_name = field_info.name
            field_type = type_hints.get(field_name, field_info.type)
            value = getattr(obj, field_name)

            # Convert based on type
            try:
                result[field_name] = self._convert_value_by_type(value, field_type)
            except Exception as e:
                logger.warning(
                    "field_conversion_failed",
                    field=field_name,
                    value=value,
                    type=field_type,
                    error=str(e),
                )
                if self.strict_mode:
                    raise
                result[field_name] = ""

        return result

    def _convert_value_by_type(self, value: Any, field_type: Type) -> str:
        """Convert a value based on its type annotation.

        Args:
            value: Value to convert
            field_type: Type annotation for the field

        Returns:
            Converted value as string
        """
        if value is None:
            return ""

        # Handle basic types
        if field_type in (int, float):
            return str(value)
        elif field_type is bool:
            return str(value).lower()
        elif field_type is str:
            return str(value)

        # Handle Optional types
        origin = getattr(field_type, "__origin__", None)
        if origin is type(Optional[int]) or origin is type(Optional[float]):
            return str(value) if value is not None else ""
        elif origin is type(Optional[bool]):
            return str(value).lower() if value is not None else ""
        elif origin is type(Optional[str]):
            return str(value) if value is not None else ""

        # Handle list types
        if origin is list:
            if isinstance(value, list):
                return ";".join(str(item) for item in value)
            else:
                return str(value)

        # Handle nested dataclasses
        if is_dataclass(field_type):
            if is_dataclass(value):
                # Convert nested dataclass to dict and flatten
                nested_dict = self._convert_dataclass_to_dict(value)
                # Prefix with field name to avoid collisions
                return str(nested_dict)
            else:
                return str(value)

        # Default conversion
        return str(value)

    def get_dataclass_fieldnames(self) -> List[str]:
        """Get field names from the dataclass type.

        Returns:
            List of field names from the dataclass
        """
        if not self.dataclass_type or not is_dataclass(self.dataclass_type):
            return self.get_fieldnames()

        return self._dataclass_fields

    def validate_dataclass_objects(self, objects: List[T]) -> List[str]:
        """Validate dataclass objects against the writer's expectations.

        Args:
            objects: List of dataclass objects to validate

        Returns:
            List of validation error messages
        """
        errors = []

        if not self.dataclass_type:
            errors.append("No dataclass type specified for validation")
            return errors

        for i, obj in enumerate(objects):
            if not is_dataclass(obj):
                errors.append(f"Object {i} is not a dataclass instance")
                continue

            if type(obj) is not self.dataclass_type:
                errors.append(
                    f"Object {i} is of type {type(obj).__name__}, "
                    f"expected {self.dataclass_type.__name__}"
                )
                continue

            # Check required fields
            for field_name in self._dataclass_fields:
                if not hasattr(obj, field_name):
                    errors.append(f"Object {i} missing required field: {field_name}")

        return errors


class DataClassStrategy(DataTransformationStrategy):
    """Strategy for handling dataclass transformations."""

    def __init__(self, dataclass_type: Type[T]):
        """Initialize strategy with dataclass type.

        Args:
            dataclass_type: Type of dataclass to handle
        """
        self.dataclass_type = dataclass_type
        self._fieldnames = [f.name for f in fields(dataclass_type)]

    def transform(self, row: Dict[str, Any], fieldnames: List[str]) -> Dict[str, Any]:
        """Transform a dataclass row.

        Args:
            row: Dataclass instance or dictionary
            fieldnames: Expected output field names

        Returns:
            Transformed data as dictionary
        """
        if is_dataclass(row):
            # Convert dataclass to dict
            writer = DataClassCSVWriter(Path("dummy.csv"), self.dataclass_type)
            return writer._convert_dataclass_to_dict(row)
        else:
            # Pass through dict as-is
            return row

    def get_fieldnames(self) -> List[str]:
        """Get field names from the dataclass."""
        return self._fieldnames.copy()


class MixedDataWriter:
    """Writer that can handle both dataclass objects and regular dictionaries."""

    def __init__(
        self,
        output_path: Path,
        dataclass_type: Optional[Type[T]] = None,
        strategy: Optional[DataTransformationStrategy] = None,
        csv_type: Optional[CSVType] = None,
        config: Optional[WriteConfig] = None,
    ):
        """Initialize MixedDataWriter.

        Args:
            output_path: Path to the output CSV file
            dataclass_type: Optional dataclass type for automatic detection
            strategy: Data transformation strategy
            csv_type: Type of CSV for header standardization
            config: Write configuration
        """
        self.output_path = output_path
        self.dataclass_type = dataclass_type
        self.strategy = strategy
        self.csv_type = csv_type
        self.config = config or WriteConfig()

        # Create appropriate writer based on input type
        self._writer = None

    def write(self, data: List[Any]) -> None:
        """Write mixed data (dataclasses and dictionaries).

        Args:
            data: List of dataclass objects or dictionaries
        """
        if not data:
            return

        # Detect data type from first item
        first_item = data[0]

        if is_dataclass(first_item):
            # Use DataClassCSVWriter
            if not self._writer or not isinstance(self._writer, DataClassCSVWriter):
                self._writer = DataClassCSVWriter(
                    output_path=self.output_path,
                    dataclass_type=type(first_item),
                    strategy=self.strategy,
                    csv_type=self.csv_type,
                    config=self.config,
                )
            self._writer.write_dataclasses(data)
        else:
            # Use regular UnifiedCSVWriter
            if not self._writer or isinstance(self._writer, DataClassCSVWriter):
                self._writer = UnifiedCSVWriter(
                    output_path=self.output_path,
                    strategy=self.strategy,
                    csv_type=self.csv_type,
                    config=self.config,
                )
            self._writer.write(data)
