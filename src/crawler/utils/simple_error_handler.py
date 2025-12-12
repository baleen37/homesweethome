"""Simple error handling utilities.

Provides basic error handling with simple try/except blocks and logging.
"""

import logging
from typing import Any, Callable, Optional, Set
import time

logger = logging.getLogger(__name__)


class SimpleErrorHandler:
    """Simple error handler with basic logging and retry logic.

    This is a simplified version that replaces the complex EnhancedErrorHandler.
    """

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """Initialize the simple error handler

        Args:
            max_retries: Maximum number of retries for transient errors
            retry_delay: Base delay between retries (seconds)
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        # Track invalid apartment IDs to avoid repeated requests
        self._invalid_apartment_ids: Set[str] = set()

    def is_apartment_invalid(self, apartment_id: str) -> bool:
        """Check if apartment ID is known to be invalid"""
        return apartment_id in self._invalid_apartment_ids

    def mark_apartment_invalid(self, apartment_id: str) -> None:
        """Mark apartment ID as invalid"""
        self._invalid_apartment_ids.add(apartment_id)
        logger.warning(f"Marked apartment {apartment_id} as invalid")

    def execute_with_retry(
        self, func: Callable, *args, apartment_id: Optional[str] = None, **kwargs
    ) -> Any:
        """Execute function with simple retry logic"""
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)

                # If this is an API response and it failed with 404, mark as invalid
                if hasattr(result, "status_code") and result.status_code == 404:
                    if apartment_id:
                        self.mark_apartment_invalid(apartment_id)
                    return result

                return result

            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    # Simple retry delay with exponential backoff
                    delay = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"Retrying after error (attempt {attempt + 1}/{self.max_retries + 1}): {str(e)}"
                    )
                    time.sleep(delay)
                    continue

        # All retries exhausted
        if apartment_id and "404" in str(last_error).lower():
            self.mark_apartment_invalid(apartment_id)

        raise last_error

    def should_skip_apartment(self, apartment_id: str) -> bool:
        """Check if apartment should be skipped based on error history"""
        return self.is_apartment_invalid(apartment_id)
