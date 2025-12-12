"""Enhanced error handling utilities for API responses

Provides utilities for handling API errors, particularly 404 errors for invalid apartments,
with retry logic, circuit breaker pattern, and data filtering capabilities.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable
from collections import deque, OrderedDict
import threading
from ..models.enhanced_api_responses import EnhancedPOIInfo, ApartmentCollection
from structlog import get_logger

logger = get_logger()


class LRUCache:
    """Thread-safe LRU cache with fixed maximum size"""

    def __init__(self, max_size: int = 1000):
        """Initialize LRU cache

        Args:
            max_size: Maximum number of items to store
        """
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()
        self.lock = threading.Lock()

    def get(self, key: str, default: int = 0) -> int:
        """Get value by key, returns default if not found"""
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                value = self.cache.pop(key)
                self.cache[key] = value
                return value
            return default

    def set(self, key: str, value: int):
        """Set value for key"""
        with self.lock:
            if key in self.cache:
                # Update existing
                self.cache.pop(key)
            elif len(self.cache) >= self.max_size:
                # Remove oldest (least recently used)
                self.cache.popitem(last=False)

            self.cache[key] = value

    def increment(self, key: str, increment: int = 1):
        """Increment value for key"""
        with self.lock:
            current = self.get(key, 0)
            self.set(key, current + increment)

    def items(self):
        """Get all items as list of (key, value) tuples"""
        with self.lock:
            return list(self.cache.items())

    def clear(self):
        """Clear all items"""
        with self.lock:
            self.cache.clear()

    def __len__(self):
        """Get number of items"""
        with self.lock:
            return len(self.cache)


class ErrorType(Enum):
    """Classification of API errors"""

    NOT_FOUND = "not_found"  # 404 - Apartment doesn't exist
    SERVER_ERROR = "server_error"  # 5xx - Server issues
    RATE_LIMIT = "rate_limit"  # 429 - Too many requests
    NETWORK_ERROR = "network_error"  # Network connectivity issues
    AUTH_ERROR = "auth_error"  # 401/403 - Authentication issues
    TIMEOUT = "timeout"  # Request timeout
    UNKNOWN = "unknown"  # Unclassified error


@dataclass(frozen=True)
class ErrorInfo:
    """Information about an API error"""

    error_type: ErrorType
    status_code: Optional[int]
    message: str
    timestamp: datetime
    apartment_id: Optional[str] = None
    retry_count: int = 0
    is_transient: bool = False  # Whether error might resolve on retry


@dataclass
class ErrorStatistics:
    """Statistics tracking API errors with memory-safe storage"""

    total_requests: int = 0
    total_errors: int = 0
    error_counts: Dict[ErrorType, int] = field(default_factory=lambda: dict.fromkeys(ErrorType, 0))
    error_by_apartment: LRUCache = field(default_factory=lambda: LRUCache(max_size=1000))
    recent_errors: deque = field(default_factory=lambda: deque(maxlen=100))
    last_reset: datetime = field(default_factory=datetime.now)
    _stats_lock: threading.Lock = field(default_factory=threading.Lock)

    def record_error(self, error_info: ErrorInfo):
        """Record an error occurrence - thread safe"""
        with self._stats_lock:
            self.total_errors += 1
            self.error_counts[error_info.error_type] += 1
            self.recent_errors.append(error_info)

            if error_info.apartment_id:
                self.error_by_apartment.increment(error_info.apartment_id)

    def record_request(self):
        """Record a request attempt - thread safe"""
        with self._stats_lock:
            self.total_requests += 1

    def get_error_rate(self) -> float:
        """Calculate error rate (0.0 to 1.0) - thread safe"""
        with self._stats_lock:
            if self.total_requests == 0:
                return 0.0
            return self.total_errors / self.total_requests

    def get_frequent_error_apartments(self, min_errors: int = 3) -> List[str]:
        """Get apartment IDs with frequent errors"""
        return [apt_id for apt_id, count in self.error_by_apartment.items() if count >= min_errors]

    def reset(self):
        """Reset statistics - thread safe"""
        with self._stats_lock:
            self.total_requests = 0
            self.total_errors = 0
            self.error_counts = dict.fromkeys(ErrorType, 0)
            self.error_by_apartment.clear()
            self.recent_errors.clear()
            self.last_reset = datetime.now()


class CircuitBreaker:
    """Thread-safe circuit breaker to prevent cascading failures"""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """Initialize circuit breaker

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before trying again
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()

    def __call__(self, func: Callable) -> Callable:
        """Decorator for circuit breaker functionality"""

        def wrapper(*args, **kwargs):
            with self._lock:
                if self.state == "OPEN":
                    if self._should_attempt_reset():
                        self.state = "HALF_OPEN"
                    else:
                        raise Exception("Circuit breaker is OPEN")

            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except Exception:
                self._on_failure()
                raise

        return wrapper

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        return self.last_failure_time and time.time() - self.last_failure_time >= self.timeout

    def _on_success(self):
        """Handle successful call - thread safe"""
        with self._lock:
            self.failure_count = 0
            self.state = "CLOSED"

    def _on_failure(self):
        """Handle failed call - thread safe"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"


class ApartmentIDFilter:
    """Filter for managing and tracking invalid apartment IDs"""

    def __init__(self):
        """Initialize the filter"""
        # Track invalid IDs with reasons
        self.invalid_ids: Dict[str, str] = {}
        # Track IDs with temporary errors (might be valid)
        self.temporarily_unavailable: Dict[str, datetime] = {}
        # Track successfully validated IDs
        self.validated_ids: Set[str] = set()
        # Statistics
        self.stats = {
            "total_checked": 0,
            "valid_found": 0,
            "invalid_found": 0,
            "temporarily_unavailable": 0,
        }

    def is_invalid(self, apartment_id: str) -> bool:
        """Check if apartment ID is known to be invalid"""
        return apartment_id in self.invalid_ids

    def is_temporarily_unavailable(self, apartment_id: str) -> bool:
        """Check if apartment ID is temporarily unavailable"""
        if apartment_id not in self.temporarily_unavailable:
            return False

        # Check if temporary status has expired (after 1 hour)
        unavailable_time = self.temporarily_unavailable[apartment_id]
        if datetime.now() - unavailable_time > timedelta(hours=1):
            del self.temporarily_unavailable[apartment_id]
            return False

        return True

    def mark_invalid(self, apartment_id: str, reason: str = "404 Not Found"):
        """Mark apartment ID as permanently invalid"""
        self.invalid_ids[apartment_id] = reason
        self.stats["invalid_found"] += 1
        logger.info("apartment_marked_invalid", apartment_id=apartment_id, reason=reason)

    def mark_temporarily_unavailable(self, apartment_id: str):
        """Mark apartment ID as temporarily unavailable"""
        self.temporarily_unavailable[apartment_id] = datetime.now()
        self.stats["temporarily_unavailable"] += 1
        logger.info("apartment_temporarily_unavailable", apartment_id=apartment_id)

    def mark_validated(self, apartment_id: str):
        """Mark apartment ID as successfully validated"""
        self.validated_ids.add(apartment_id)
        self.stats["valid_found"] += 1

        # Remove from invalid/temporary lists if present
        self.invalid_ids.pop(apartment_id, None)
        self.temporarily_unavailable.pop(apartment_id, None)

    def should_skip(self, apartment_id: str) -> bool:
        """Check if apartment ID should be skipped"""
        self.stats["total_checked"] += 1

        if self.is_invalid(apartment_id):
            logger.debug(
                "skipping_invalid_apartment",
                apartment_id=apartment_id,
                reason=self.invalid_ids[apartment_id],
            )
            return True

        if self.is_temporarily_unavailable(apartment_id):
            logger.debug("skipping_temporarily_unavailable", apartment_id=apartment_id)
            return True

        return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get filter statistics"""
        return {
            **self.stats,
            "invalid_ids_count": len(self.invalid_ids),
            "temporarily_unavailable_count": len(self.temporarily_unavailable),
            "validated_ids_count": len(self.validated_ids),
            "invalid_ids": dict(list(self.invalid_ids.items())[:10]),  # Show first 10
        }

    def export_invalid_ids(self) -> Dict[str, str]:
        """Export all invalid IDs for persistence"""
        return self.invalid_ids.copy()

    def import_invalid_ids(self, invalid_ids: Dict[str, str]):
        """Import invalid IDs from storage"""
        self.invalid_ids.update(invalid_ids)
        self.stats["invalid_found"] = len(self.invalid_ids)


class EnhancedErrorHandler:
    """Enhanced error handler with filtering and retry logic"""

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """Initialize the error handler

        Args:
            max_retries: Maximum number of retries for transient errors
            retry_delay: Base delay between retries (seconds)
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.stats = ErrorStatistics()
        self.id_filter = ApartmentIDFilter()
        self.circuit_breaker = CircuitBreaker()

    def classify_error(
        self,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        apartment_id: Optional[str] = None,
    ) -> ErrorInfo:
        """Classify the type of error from status code and message"""
        if status_code == 404:
            error_type = ErrorType.NOT_FOUND
            message = "Apartment not found (404)"
            is_transient = False
        elif status_code == 429:
            error_type = ErrorType.RATE_LIMIT
            message = "Rate limit exceeded (429)"
            is_transient = True
        elif status_code and 500 <= status_code < 600:
            error_type = ErrorType.SERVER_ERROR
            message = f"Server error ({status_code})"
            is_transient = True
        elif status_code in [401, 403]:
            error_type = ErrorType.AUTH_ERROR
            message = f"Authentication error ({status_code})"
            is_transient = False
        elif error_message and "timeout" in error_message.lower():
            error_type = ErrorType.TIMEOUT
            message = "Request timeout"
            is_transient = True
        elif error_message and "network" in error_message.lower():
            error_type = ErrorType.NETWORK_ERROR
            message = "Network error"
            is_transient = True
        else:
            error_type = ErrorType.UNKNOWN
            message = error_message or "Unknown error"
            is_transient = False

        return ErrorInfo(
            error_type=error_type,
            status_code=status_code,
            message=message,
            timestamp=datetime.now(),
            apartment_id=apartment_id,
            is_transient=is_transient,
        )

    def handle_error(
        self,
        success: bool,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        apartment_id: Optional[str] = None,
    ) -> Optional[ErrorInfo]:
        """Handle API error with appropriate actions

        Args:
            success: Whether the API call was successful
            status_code: HTTP status code
            error_message: Error message
            apartment_id: Apartment ID if applicable

        Returns:
            ErrorInfo if error occurred, None if success
        """
        self.stats.record_request()

        if not success:
            error_info = self.classify_error(status_code, error_message, apartment_id)
            self.stats.record_error(error_info)

            # Update ID filter based on error type
            if apartment_id:
                if error_info.error_type == ErrorType.NOT_FOUND:
                    self.id_filter.mark_invalid(apartment_id, error_info.message)
                elif error_info.is_transient:
                    self.id_filter.mark_temporarily_unavailable(apartment_id)
                elif error_info.error_type != ErrorType.NOT_FOUND:
                    # For non-404 errors, mark as temporarily unavailable
                    self.id_filter.mark_temporarily_unavailable(apartment_id)

            logger.warning(
                "api_error_handled",
                apartment_id=apartment_id,
                error_type=error_info.error_type.value,
                message=error_info.message,
                is_transient=error_info.is_transient,
            )

            return error_info
        else:
            # Success - mark as validated if apartment ID provided
            if apartment_id:
                self.id_filter.mark_validated(apartment_id)

            return None

    def execute_with_retry(
        self, func: Callable, *args, apartment_id: Optional[str] = None, **kwargs
    ) -> Any:
        """Execute function with retry logic for transient errors"""
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)

                # Check if result has success attribute (like APIResponse)
                if hasattr(result, "success"):
                    success = result.success
                    status_code = getattr(result, "status_code", None)
                    error_message = getattr(result, "error", None)

                    error_info = self.handle_error(
                        success, status_code, error_message, apartment_id
                    )
                    if error_info and error_info.is_transient and attempt < self.max_retries:
                        # Wait with exponential backoff
                        delay = self.retry_delay * (2**attempt)
                        logger.info(
                            "retrying_api_call",
                            attempt=attempt + 1,
                            max_attempts=self.max_retries + 1,
                            delay=delay,
                            apartment_id=apartment_id,
                        )
                        time.sleep(delay)
                        continue

                return result

            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2**attempt)
                    logger.warning(
                        "retrying_after_exception",
                        attempt=attempt + 1,
                        max_attempts=self.max_retries + 1,
                        delay=delay,
                        error=str(e),
                        apartment_id=apartment_id,
                    )
                    time.sleep(delay)
                    continue

        # All retries exhausted
        if last_error:
            # Record as unknown error
            error_info = ErrorInfo(
                error_type=ErrorType.UNKNOWN,
                status_code=None,
                message=str(last_error),
                timestamp=datetime.now(),
                apartment_id=apartment_id,
                retry_count=self.max_retries + 1,
            )
            self.stats.record_error(error_info)

        raise last_error

    def should_skip_apartment(self, apartment_id: str) -> bool:
        """Check if apartment should be skipped based on error history"""
        return self.id_filter.should_skip(apartment_id)

    def filter_apartment_collection(self, apartments: List[EnhancedPOIInfo]) -> ApartmentCollection:
        """Filter apartment collection to remove invalid entries"""
        filtered = []
        for apt in apartments:
            if not self.should_skip_apartment(apt.id):
                filtered.append(apt)

        return ApartmentCollection(apartments=filtered)

    def get_error_summary(self) -> Dict[str, Any]:
        """Get comprehensive error summary"""
        error_rate = self.stats.get_error_rate()

        # Get most common error types
        common_errors = sorted(
            [(error_type.value, count) for error_type, count in self.stats.error_counts.items()],
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        # Get apartments with most errors
        problematic_apartments = sorted(
            self.stats.error_by_apartment.items(), key=lambda x: x[1], reverse=True
        )[:10]

        return {
            "error_statistics": {
                "total_requests": self.stats.total_requests,
                "total_errors": self.stats.total_errors,
                "error_rate": error_rate,
                "common_errors": common_errors,
                "problematic_apartments": problematic_apartments,
            },
            "id_filter_stats": self.id_filter.get_statistics(),
            "recommendations": self._generate_recommendations(error_rate),
        }

    def _generate_recommendations(self, error_rate: float) -> List[str]:
        """Generate recommendations based on error patterns"""
        recommendations = []

        if error_rate > 0.5:
            recommendations.append("High error rate detected - consider reducing request frequency")

        not_found_errors = self.stats.error_counts.get(ErrorType.NOT_FOUND, 0)
        if not_found_errors > 100:
            recommendations.append(
                f"Many 404 errors ({not_found_errors}) - review data source quality"
            )

        rate_limit_errors = self.stats.error_counts.get(ErrorType.RATE_LIMIT, 0)
        if rate_limit_errors > 10:
            recommendations.append("Rate limiting issues - increase delay between requests")

        invalid_ids = len(self.id_filter.invalid_ids)
        if invalid_ids > 500:
            recommendations.append(
                f"Many invalid IDs ({invalid_ids}) - implement better pre-filtering"
            )

        if not recommendations:
            recommendations.append("Error rates within acceptable range")

        return recommendations

    def reset_statistics(self):
        """Reset all statistics"""
        self.stats.reset()
        logger.info("error_handler_statistics_reset")
