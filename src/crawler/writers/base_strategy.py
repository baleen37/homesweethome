"""Base strategy classes for CSV writers.

This module provides common base classes for transformation strategies
to reduce code duplication, especially for get_fieldnames methods.
"""

from abc import ABC, abstractmethod
from typing import List

from crawler.writers.csv_header_standard import CSVType, HeaderStandardRegistry
from crawler.writers.data_transformation_strategy import DataTransformationStrategy


class BaseCSVTypeStrategy(DataTransformationStrategy, ABC):
    """Base strategy class that provides get_fieldnames functionality for CSV types.

    Subclasses only need to specify the CSVType and implement transform method.
    """

    @property
    @abstractmethod
    def csv_type(self) -> CSVType:
        """Return the CSV type for this strategy."""
        pass

    def get_fieldnames(self) -> List[str]:
        """Get field names from the appropriate header standard."""
        return HeaderStandardRegistry.get_fieldnames(self.csv_type)


class ComplexesStrategy(BaseCSVTypeStrategy):
    """Base strategy for complexes data."""

    @property
    def csv_type(self) -> CSVType:
        return CSVType.COMPLEXES


class TransactionsStrategy(BaseCSVTypeStrategy):
    """Base strategy for transactions data."""

    @property
    def csv_type(self) -> CSVType:
        return CSVType.TRANSACTIONS
