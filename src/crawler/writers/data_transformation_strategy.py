"""Data transformation strategies for CSV writers.

This module provides the strategy interface and concrete implementations
for different data transformation requirements across various CSV writers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Protocol


class DataTransformationStrategy(Protocol):
    """Protocol for data transformation strategies.

    This defines the interface that all data transformation strategies
    must implement. It uses Protocol for better type hinting and
    duck typing support.
    """

    def transform(self, row: Dict[str, Any], fieldnames: List[str]) -> Dict[str, Any]:
        """Transform a data row according to the specific strategy.

        Args:
            row: Raw data row to transform
            fieldnames: List of expected field names in the output

        Returns:
            Transformed data row with all fields present
        """
        ...

    def get_fieldnames(self) -> List[str]:
        """Get the list of field names this strategy expects.

        Returns:
            List of field names for this strategy
        """
        ...


class BaseDataTransformationStrategy(ABC):
    """Abstract base class for data transformation strategies.

    Provides common functionality that all strategies can inherit from.
    This is an alternative to the Protocol approach for cases where
    inheritance is preferred.
    """

    @abstractmethod
    def transform(self, row: Dict[str, Any], fieldnames: List[str]) -> Dict[str, Any]:
        """Transform a data row according to the specific strategy."""
        pass

    @abstractmethod
    def get_fieldnames(self) -> List[str]:
        """Get the list of field names this strategy expects."""
        pass

    def _normalize_common_fields(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Apply common normalization rules to a row.

        Handles generic normalization that applies to most CSV writers:
        - Convert None to empty string
        - Convert boolean values to appropriate strings
        - Convert numeric values to appropriate types

        Args:
            row: Data row to normalize

        Returns:
            Row with common fields normalized
        """
        normalized = {}

        for key, value in row.items():
            if value is None:
                normalized[key] = ""
            elif isinstance(value, bool):
                # Keep boolean as-is for now, strategies can override
                normalized[key] = value
            elif isinstance(value, (int, float)):
                normalized[key] = value
            else:
                normalized[key] = str(value)

        return normalized

    def _parse_floor(self, floor_str: str) -> int:
        """Parse floor string to integer.

        Args:
            floor_str: Floor string (e.g., "5", "5/15", "B1")

        Returns:
            Floor number (0 for basement/invalid)
        """
        if not floor_str:
            return 0

        try:
            import re

            # Return 0 for basement
            if re.search(r"[bB지하]", floor_str):
                return 0

            # Extract first number
            numbers = re.findall(r"\d+", floor_str)
            if numbers:
                return int(numbers[0])
        except (ValueError, IndexError):
            pass

        return 0

    def _parse_money_amount(self, amount_str: str) -> int:
        """Parse money amount string to integer (in 만원 units).

        Args:
            amount_str: Money amount string (e.g., "45,000", "45억")

        Returns:
            Parsed amount as integer
        """
        if not amount_str:
            return 0

        try:
            # Remove commas
            amount_str = amount_str.replace(",", "")

            # Extract numbers
            import re

            numbers = re.findall(r"\d+", amount_str)
            if numbers:
                return int(numbers[0])
        except (ValueError, IndexError):
            pass

        return 0

    def _parse_date(self, date_str: str) -> tuple[str, int]:
        """Parse date string and return (formatted_date, year).

        Args:
            date_str: Date string in various formats

        Returns:
            Tuple of (formatted_date as YYYY-MM-DD, year as int)
        """
        from datetime import datetime

        if not date_str:
            return "", datetime.now().year

        try:
            # Normalize separators
            date_str = date_str.replace(".", "-")
            date_part = date_str.split()[0]  # Take only date part

            # Parse date
            date_obj = datetime.strptime(date_part, "%Y-%m-%d")
            return date_part, date_obj.year
        except (ValueError, IndexError):
            return "", datetime.now().year
