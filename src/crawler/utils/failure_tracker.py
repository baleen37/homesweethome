"""Failure tracking system for recording and analyzing failed operations.

This module provides a comprehensive system to track failed items,
categorize errors, and generate reports for later review.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()


class FailureType(Enum):
    """Types of failures that can occur."""
    NETWORK_ERROR = "network_error"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    PARSE_ERROR = "parse_error"
    DATA_VALIDATION = "data_validation"
    AUTH_ERROR = "auth_error"
    SERVER_ERROR = "server_error"
    UNKNOWN_ERROR = "unknown_error"


class FailureSeverity(Enum):
    """Severity levels for failures."""
    LOW = "low"          # Non-critical, can be retried
    MEDIUM = "medium"    # Affects data quality but can continue
    HIGH = "high"        # Prevents progress on current item
    CRITICAL = "critical"  # Stops entire operation


@dataclass
class FailureRecord:
    """Record of a failed operation."""
    timestamp: float
    failure_type: FailureType
    severity: FailureSeverity
    item_id: str
    item_type: str  # e.g., "complex", "dong", "transaction"
    operation: str  # e.g., "fetch_detail", "parse_data"
    error_message: str
    error_type: str
    context: Dict[str, Any]
    attempt_count: int = 1
    retry_after: Optional[float] = None
    resolved: bool = False
    resolution_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["failure_type"] = self.failure_type.value
        data["severity"] = self.severity.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FailureRecord":
        """Create from dictionary."""
        data["failure_type"] = FailureType(data["failure_type"])
        data["severity"] = FailureSeverity(data["severity"])
        return cls(**data)


class FailureTracker:
    """
    Tracks and manages failed operations.

    Features:
    - Categorize failures by type and severity
    - Track retry attempts and resolutions
    - Generate failure reports
    - Persist failure records
    - Automatic cleanup of old records
    """

    def __init__(
        self,
        max_records: int = 10000,
        cleanup_age_hours: float = 24.0,
        persistence_file: Optional[Path] = None,
    ) -> None:
        """
        Initialize failure tracker.

        Args:
            max_records: Maximum number of records to keep in memory
            cleanup_age_hours: Age in hours after which records are cleaned up
            persistence_file: File to persist records to
        """
        self.max_records = max_records
        self.cleanup_age_seconds = cleanup_age_hours * 3600
        self.persistence_file = persistence_file

        self.records: List[FailureRecord] = []
        self.by_item: Dict[str, List[FailureRecord]] = defaultdict(list)
        self.by_type: Counter[FailureType] = Counter()
        self.by_severity: Counter[FailureSeverity] = Counter()

        self.logger = structlog.get_logger().bind(
            failure_tracker=id(self),
            max_records=max_records,
            cleanup_age_hours=cleanup_age_hours,
        )

        # Load persisted records if file exists
        if persistence_file and persistence_file.exists():
            self.load_from_disk()

    def record_failure(
        self,
        item_id: str,
        item_type: str,
        operation: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        attempt_count: int = 1,
        retry_after: Optional[float] = None,
    ) -> FailureRecord:
        """
        Record a failure.

        Args:
            item_id: Unique identifier of the item that failed
            item_type: Type of the item (e.g., "complex", "dong")
            operation: Operation being performed (e.g., "fetch_detail")
            error: The exception that occurred
            context: Additional context information
            attempt_count: Number of attempts made
            retry_after: Suggested retry delay in seconds

        Returns:
            The created failure record
        """
        failure_type = self._classify_error(error)
        severity = self._determine_severity(error, failure_type)

        record = FailureRecord(
            timestamp=time.time(),
            failure_type=failure_type,
            severity=severity,
            item_id=item_id,
            item_type=item_type,
            operation=operation,
            error_message=str(error),
            error_type=type(error).__name__,
            context=context or {},
            attempt_count=attempt_count,
            retry_after=retry_after,
        )

        self._add_record(record)
        self.logger.warning(
            "failure_recorded",
            item_id=item_id,
            item_type=item_type,
            operation=operation,
            failure_type=failure_type.value,
            severity=severity.value,
            attempt_count=attempt_count,
        )

        # Persist if configured
        if self.persistence_file:
            self.save_to_disk()

        return record

    def record_resolution(self, item_id: str) -> None:
        """
        Mark failures for an item as resolved.

        Args:
            item_id: ID of the item that was successfully processed
        """
        now = time.time()
        resolved_count = 0

        for record in self.by_item.get(item_id, []):
            if not record.resolved:
                record.resolved = True
                record.resolution_time = now
                resolved_count += 1

        if resolved_count > 0:
            self.logger.info(
                "failures_resolved",
                item_id=item_id,
                count=resolved_count,
            )
            if self.persistence_file:
                self.save_to_disk()

    def get_failures_for_item(self, item_id: str) -> List[FailureRecord]:
        """Get all failures for a specific item."""
        return self.by_item.get(item_id, [])

    def get_unresolved_failures(
        self,
        failure_type: Optional[FailureType] = None,
        severity: Optional[FailureSeverity] = None,
    ) -> List[FailureRecord]:
        """Get unresolved failures, optionally filtered."""
        records = [r for r in self.records if not r.resolved]

        if failure_type:
            records = [r for r in records if r.failure_type == failure_type]

        if severity:
            records = [r for r in records if r.severity == severity]

        return records

    def get_retry_candidates(self, max_age_seconds: float = 300.0) -> List[FailureRecord]:
        """
        Get items that can be retried.

        Args:
            max_age_seconds: Maximum age of failures to consider for retry

        Returns:
            List of failure records that are good candidates for retry
        """
        now = time.time()
        candidates = []

        for record in self.get_unresolved_failures():
            # Skip if too recent
            if now - record.timestamp < max_age_seconds:
                continue

            # Skip if retry time not reached
            if record.retry_after and now - record.timestamp < record.retry_after:
                continue

            # Prioritize network and rate limit errors
            if record.failure_type in [FailureType.NETWORK_ERROR, FailureType.RATE_LIMIT]:
                candidates.append(record)

        # Sort by severity (low first) and timestamp (old first)
        candidates.sort(key=lambda r: (r.severity.value, r.timestamp))
        return candidates

    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive failure report."""
        total_failures = len(self.records)
        unresolved_failures = len(self.get_unresolved_failures())

        # Group by hour
        failures_by_hour = defaultdict(int)
        for record in self.records:
            hour = int(record.timestamp // 3600)
            failures_by_hour[hour] += 1

        # Most common errors
        error_messages = Counter(r.error_message for r in self.records)
        common_errors = error_messages.most_common(10)

        # Items with most failures
        items_by_failure_count = defaultdict(int)
        for record in self.records:
            items_by_failure_count[record.item_id] += 1
        problematic_items = sorted(
            items_by_failure_count.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        return {
            "summary": {
                "total_failures": total_failures,
                "unresolved_failures": unresolved_failures,
                "resolved_failures": total_failures - unresolved_failures,
                "unique_items": len(self.by_item),
            },
            "by_type": {k.value: v for k, v in self.by_type.items()},
            "by_severity": {k.value: v for k, v in self.by_severity.items()},
            "failures_by_hour": dict(sorted(failures_by_hour.items())),
            "common_errors": [{"error": e, "count": c} for e, c in common_errors],
            "problematic_items": [{"item_id": i, "failure_count": c} for i, c in problematic_items],
        }

    def cleanup_old_records(self) -> int:
        """Remove old records to prevent memory bloat."""
        cutoff_time = time.time() - self.cleanup_age_seconds
        old_count = len(self.records)

        # Filter old records
        self.records = [r for r in self.records if r.timestamp > cutoff_time]

        # Rebuild indexes
        self.by_item.clear()
        self.by_type.clear()
        self.by_severity.clear()

        for record in self.records:
            self.by_item[record.item_id].append(record)
            self.by_type[record.failure_type] += 1
            self.by_severity[record.severity] += 1

        removed = old_count - len(self.records)
        if removed > 0:
            self.logger.info(
                "cleaned_up_old_records",
                removed=removed,
                remaining=len(self.records),
            )
            if self.persistence_file:
                self.save_to_disk()

        return removed

    def _add_record(self, record: FailureRecord) -> None:
        """Add a record to internal structures."""
        # Enforce max records
        if len(self.records) >= self.max_records:
            # Remove oldest record
            oldest = self.records[0]
            self.records.pop(0)
            self.by_item[oldest.item_id].remove(oldest)
            if not self.by_item[oldest.item_id]:
                del self.by_item[oldest.item_id]

        self.records.append(record)
        self.by_item[record.item_id].append(record)
        self.by_type[record.failure_type] += 1
        self.by_severity[record.severity] += 1

    def _classify_error(self, error: Exception) -> FailureType:
        """Classify error into a failure type."""
        error_msg = str(error).lower()
        error_type = type(error).__name__.lower()

        if "timeout" in error_msg or "timed out" in error_msg:
            return FailureType.TIMEOUT
        elif "429" in error_msg or "too many requests" in error_msg:
            return FailureType.RATE_LIMIT
        elif "connection" in error_msg or "network" in error_msg:
            return FailureType.NETWORK_ERROR
        elif "parse" in error_msg or "json" in error_msg or "invalid" in error_msg:
            return FailureType.PARSE_ERROR
        elif "unauthorized" in error_msg or "403" in error_msg or "401" in error_msg:
            return FailureType.AUTH_ERROR
        elif "500" in error_msg or "502" in error_msg or "503" in error_msg:
            return FailureType.SERVER_ERROR
        else:
            return FailureType.UNKNOWN_ERROR

    def _determine_severity(
        self,
        error: Exception,
        failure_type: FailureType
    ) -> FailureSeverity:
        """Determine severity of failure."""
        if failure_type in [FailureType.TIMEOUT, FailureType.NETWORK_ERROR]:
            return FailureSeverity.MEDIUM  # Likely temporary
        elif failure_type == FailureType.RATE_LIMIT:
            return FailureSeverity.LOW  # Expected, can wait
        elif failure_type == FailureType.AUTH_ERROR:
            return FailureSeverity.CRITICAL  # Cannot continue without auth
        elif failure_type == FailureType.PARSE_ERROR:
            return FailureSeverity.HIGH  # Data quality issue
        elif failure_type == FailureType.SERVER_ERROR:
            return FailureSeverity.MEDIUM  # Usually temporary
        else:
            return FailureSeverity.MEDIUM  # Default

    def save_to_disk(self) -> None:
        """Persist records to disk."""
        if not self.persistence_file:
            return

        try:
            data = {
                "records": [r.to_dict() for r in self.records],
                "metadata": {
                    "saved_at": time.time(),
                    "version": "1.0",
                },
            }

            self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.persistence_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.logger.error(
                "failed_to_save_failures",
                error=str(e),
                path=str(self.persistence_file),
            )

    def load_from_disk(self) -> None:
        """Load records from disk."""
        if not self.persistence_file or not self.persistence_file.exists():
            return

        try:
            with open(self.persistence_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for record_data in data.get("records", []):
                record = FailureRecord.from_dict(record_data)
                self._add_record(record)

            self.logger.info(
                "loaded_failures_from_disk",
                count=len(self.records),
            )

        except Exception as e:
            self.logger.error(
                "failed_to_load_failures",
                error=str(e),
                path=str(self.persistence_file),
            )