"""Base writer for Hogangnono data to eliminate code duplication."""

from pathlib import Path
from typing import Any, Dict, List
from abc import ABC, abstractmethod

from crawler.writers.base_csv_writer import BaseCSVWriter
from crawler.writers.data_transformation_strategy import DataTransformationStrategy
from crawler.writers.csv_header_standard import CSVType
from crawler.validators.csv_validator import (
    create_complexes_validator,
    create_transactions_validator,
)


class StandardizedHogangnonoStrategy(DataTransformationStrategy):
    """Wrapper strategy that ensures fieldnames follow standard order."""

    def __init__(self, wrapped_strategy: DataTransformationStrategy, csv_type: CSVType):
        self._wrapped_strategy = wrapped_strategy
        self._csv_type = csv_type

    def transform(self, row: Dict[str, Any], fieldnames: List[str]) -> Dict[str, Any]:
        """Delegate transform to wrapped strategy."""
        return self._wrapped_strategy.transform(row, fieldnames)

    def get_fieldnames(self) -> List[str]:
        """Get fieldnames from wrapped strategy."""
        return self._wrapped_strategy.get_fieldnames()


class BaseHogangnonoCSVWriter(BaseCSVWriter, ABC):
    """Base class for Hogangnono CSV writers to eliminate duplication."""

    def __init__(self, output_path: Path, csv_type: CSVType):
        """Initialize base Hogangnono writer.

        Args:
            output_path: Path to the CSV file
            csv_type: Type of CSV (COMPLEXES or TRANSACTIONS)
        """
        # Create appropriate strategy based on CSV type
        strategy = self._create_strategy(csv_type)

        # Wrap with standardized strategy
        standardized_strategy = StandardizedHogangnonoStrategy(strategy, csv_type)

        # Create appropriate validator
        validator = self._create_validator(csv_type)

        super().__init__(
            output_path,
            strategy=standardized_strategy,
            validator=validator,
            csv_type=csv_type,
            enable_validation=True,
        )

    @abstractmethod
    def _create_strategy(self, csv_type: CSVType) -> DataTransformationStrategy:
        """Create the appropriate strategy for the CSV type.

        Args:
            csv_type: Type of CSV to create strategy for

        Returns:
            Data transformation strategy instance
        """
        pass

    def _create_validator(self, csv_type: CSVType):
        """Create the appropriate validator for the CSV type."""
        if csv_type == CSVType.COMPLEXES:
            return create_complexes_validator()
        elif csv_type == CSVType.TRANSACTIONS:
            return create_transactions_validator()
        else:
            raise ValueError(f"Unsupported CSV type: {csv_type}")

    def _normalize_row_legacy(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy normalization method - not used when strategy is set.

        This method is kept for backward compatibility but should not be called
        when a strategy is provided.
        """
        # This should not be reached when strategy is set
        # Base class will use the strategy instead
        return row
