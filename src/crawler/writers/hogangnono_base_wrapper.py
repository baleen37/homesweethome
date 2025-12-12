"""Base wrapper class for Hogangnono compatibility writers.

This module provides the base functionality for all Hogangnono compatibility
wrappers, reducing code duplication.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any


class BaseHogangnonoWrapper(ABC):
    """Base class for Hogangnono compatibility wrappers.

    This class provides common functionality for all Hogangnono writers
    while allowing subclasses to specify their fieldnames and factory function.
    """

    # Subclasses should override this
    FIELDNAMES: List[str] = []

    def __init__(self, output_path: Path) -> None:
        """Initialize the wrapper.

        Args:
            output_path: Path to the CSV file
        """
        # Use the factory function to create the actual writer
        self._writer = self._create_writer(output_path)

    @abstractmethod
    def _create_writer(self, output_path: Path):
        """Create the underlying writer using a factory function.

        Args:
            output_path: Path to the CSV file

        Returns:
            The actual writer instance
        """
        pass

    def write(self, data: List[Dict[str, Any]], mode: str = "w", write_header: bool = True) -> None:
        """Write data to CSV.

        Args:
            data: List of dictionaries to write
            mode: Write mode ('w' or 'a')
            write_header: Whether to write header
        """
        self._writer.write(data, mode=mode, write_header=write_header)

    def append(self, data: List[Dict[str, Any]]) -> None:
        """Append data to CSV.

        Args:
            data: List of dictionaries to append
        """
        self._writer.append(data)

    def get_file_info(self) -> Dict[str, Any]:
        """Get file information.

        Returns:
            Dictionary with file statistics
        """
        return self._writer.get_stats()
