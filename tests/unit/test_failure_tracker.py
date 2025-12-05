"""Tests for the failure tracker system."""

import json
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path

from crawler.utils.failure_tracker import (
    FailureRecord,
    FailureTracker,
    FailureType,
    FailureSeverity,
)


class TestFailureRecord(unittest.TestCase):
    """Test cases for FailureRecord."""

    def test_creation(self) -> None:
        """Test failure record creation."""
        record = FailureRecord(
            timestamp=time.time(),
            failure_type=FailureType.NETWORK_ERROR,
            severity=FailureSeverity.MEDIUM,
            item_id="test-123",
            item_type="complex",
            operation="fetch_detail",
            error_message="Connection timeout",
            error_type="TimeoutError",
            context={"url": "http://example.com"},
        )

        self.assertEqual(record.failure_type, FailureType.NETWORK_ERROR)
        self.assertEqual(record.severity, FailureSeverity.MEDIUM)
        self.assertEqual(record.item_id, "test-123")
        self.assertFalse(record.resolved)

    def test_serialization(self) -> None:
        """Test record serialization to/from dict."""
        record = FailureRecord(
            timestamp=time.time(),
            failure_type=FailureType.RATE_LIMIT,
            severity=FailureSeverity.LOW,
            item_id="test-456",
            item_type="dong",
            operation="crawl",
            error_message="HTTP 429",
            error_type="RateLimitError",
            context={},
        )

        # Serialize
        data = record.to_dict()
        self.assertIsInstance(data, dict)
        self.assertEqual(data["failure_type"], "rate_limit")
        self.assertEqual(data["severity"], "low")

        # Deserialize
        restored = FailureRecord.from_dict(data)
        self.assertEqual(restored.failure_type, FailureType.RATE_LIMIT)
        self.assertEqual(restored.severity, FailureSeverity.LOW)
        self.assertEqual(restored.item_id, "test-456")


class TestFailureTracker(unittest.TestCase):
    """Test cases for FailureTracker."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.tracker = FailureTracker()

    def test_record_failure(self) -> None:
        """Test recording a failure."""
        error = ConnectionError("Connection refused")

        record = self.tracker.record_failure(
            item_id="complex-1",
            item_type="complex",
            operation="fetch_detail",
            error=error,
            context={"url": "http://example.com"},
        )

        self.assertIsInstance(record, FailureRecord)
        self.assertEqual(record.item_id, "complex-1")
        self.assertEqual(record.failure_type, FailureType.NETWORK_ERROR)
        self.assertEqual(record.severity, FailureSeverity.MEDIUM)

        # Check internal storage
        self.assertEqual(len(self.tracker.records), 1)
        self.assertIn("complex-1", self.tracker.by_item)
        self.assertEqual(self.tracker.by_type[FailureType.NETWORK_ERROR], 1)
        self.assertEqual(self.tracker.by_severity[FailureSeverity.MEDIUM], 1)

    def test_record_resolution(self) -> None:
        """Test marking failures as resolved."""
        error = ValueError("Invalid data")

        # Record multiple failures
        self.tracker.record_failure(
            item_id="item-1",
            item_type="test",
            operation="process",
            error=error,
        )
        self.tracker.record_failure(
            item_id="item-1",
            item_type="test",
            operation="process",
            error=error,
        )

        # Check unresolved
        unresolved = self.tracker.get_unresolved_failures()
        self.assertEqual(len(unresolved), 2)

        # Mark as resolved
        self.tracker.record_resolution("item-1")

        # Check resolved
        unresolved = self.tracker.get_unresolved_failures()
        self.assertEqual(len(unresolved), 0)

    def test_get_failures_for_item(self) -> None:
        """Test retrieving failures for specific item."""
        error1 = TimeoutError("Timeout")
        error2 = ValueError("Invalid")

        self.tracker.record_failure(
            item_id="item-1",
            item_type="test",
            operation="op1",
            error=error1,
        )
        self.tracker.record_failure(
            item_id="item-2",
            item_type="test",
            operation="op2",
            error=error2,
        )
        self.tracker.record_failure(
            item_id="item-1",
            item_type="test",
            operation="op3",
            error=error1,
        )

        # Get failures for item-1
        failures = self.tracker.get_failures_for_item("item-1")
        self.assertEqual(len(failures), 2)
        self.assertEqual(failures[0].item_id, "item-1")
        self.assertEqual(failures[1].item_id, "item-1")

    def test_get_retry_candidates(self) -> None:
        """Test getting retry candidates."""
        # Record some old failures
        old_time = time.time() - 3600  # 1 hour ago
        with patch('time.time', return_value=old_time):
            self.tracker.record_failure(
                item_id="item-1",
                item_type="test",
                operation="fetch",
                error=ConnectionError("Network error"),
            )

        # Record recent failure
        self.tracker.record_failure(
            item_id="item-2",
            item_type="test",
            operation="fetch",
            error=ConnectionError("Network error"),
        )

        # Get retry candidates (max_age=1800 seconds = 30 minutes)
        candidates = self.tracker.get_retry_candidates(max_age_seconds=1800)

        # Should only include the old one
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].item_id, "item-1")

    def test_generate_report(self) -> None:
        """Test generating failure report."""
        # Record some failures
        errors = [
            ConnectionError("Network error"),
            TimeoutError("Timeout"),
            ValueError("Invalid data"),
            ConnectionError("Another network error"),
        ]

        for i, error in enumerate(errors):
            self.tracker.record_failure(
                item_id=f"item-{i}",
                item_type="test",
                operation="process",
                error=error,
            )

        report = self.tracker.generate_report()

        # Check summary
        self.assertEqual(report["summary"]["total_failures"], 4)
        self.assertEqual(report["summary"]["unresolved_failures"], 4)
        self.assertEqual(report["summary"]["unique_items"], 4)

        # Check by type
        self.assertEqual(report["by_type"]["network_error"], 2)
        self.assertEqual(report["by_type"]["timeout"], 1)
        self.assertEqual(report["by_type"]["parse_error"], 1)  # ValueError is classified as parse_error

        # Check by severity
        self.assertEqual(report["by_severity"]["medium"], 3)
        self.assertEqual(report["by_severity"]["high"], 1)  # parse_error is high severity

    def test_cleanup_old_records(self) -> None:
        """Test cleaning up old records."""
        # Record a failure
        self.tracker.record_failure(
            item_id="item-1",
            item_type="test",
            operation="process",
            error=RuntimeError("Error"),
        )

        self.assertEqual(len(self.tracker.records), 1)

        # Set cleanup age to 0 seconds to force cleanup
        self.tracker.cleanup_age_seconds = 0

        # Run cleanup
        removed = self.tracker.cleanup_old_records()

        self.assertEqual(removed, 1)
        self.assertEqual(len(self.tracker.records), 0)

    def test_persistence(self) -> None:
        """Test saving and loading failures to disk."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "failures.json"
            tracker = FailureTracker(persistence_file=file_path)

            # Record a failure
            tracker.record_failure(
                item_id="persist-1",
                item_type="test",
                operation="process",
                error=ValueError("Test error"),
                context={"key": "value"},
            )

            # Save should happen automatically
            self.assertTrue(file_path.exists())

            # Create new tracker and load
            tracker2 = FailureTracker(persistence_file=file_path)
            self.assertEqual(len(tracker2.records), 1)
            self.assertEqual(tracker2.records[0].item_id, "persist-1")
            self.assertEqual(tracker2.records[0].context["key"], "value")

    def test_max_records_enforcement(self) -> None:
        """Test maximum records enforcement."""
        tracker = FailureTracker(max_records=2)

        # Add 3 records
        for i in range(3):
            tracker.record_failure(
                item_id=f"item-{i}",
                item_type="test",
                operation="process",
                error=RuntimeError(f"Error {i}"),
            )

        # Should only keep 2 records
        self.assertEqual(len(tracker.records), 2)
        self.assertEqual(tracker.records[0].item_id, "item-1")  # item-0 removed
        self.assertEqual(tracker.records[1].item_id, "item-2")

    def test_error_classification(self) -> None:
        """Test error type classification."""
        test_cases = [
            (TimeoutError("Operation timed out"), FailureType.TIMEOUT),
            (ConnectionError("Connection failed"), FailureType.NETWORK_ERROR),
            (Exception("HTTP 429 Too Many Requests"), FailureType.RATE_LIMIT),
            (ValueError("Invalid JSON"), FailureType.PARSE_ERROR),
            (PermissionError("403 Forbidden"), FailureType.AUTH_ERROR),
            (RuntimeError("500 Internal Server Error"), FailureType.SERVER_ERROR),
            (Exception("Unknown error"), FailureType.UNKNOWN_ERROR),
        ]

        for error, expected_type in test_cases:
            actual_type = self.tracker._classify_error(error)
            self.assertEqual(
                actual_type, expected_type,
                f"Failed to classify {error}: expected {expected_type}, got {actual_type}"
            )

    def test_severity_determination(self) -> None:
        """Test severity level determination."""
        test_cases = [
            (FailureType.TIMEOUT, FailureSeverity.MEDIUM),
            (FailureType.RATE_LIMIT, FailureSeverity.LOW),
            (FailureType.AUTH_ERROR, FailureSeverity.CRITICAL),
            (FailureType.PARSE_ERROR, FailureSeverity.HIGH),
            (FailureType.SERVER_ERROR, FailureSeverity.MEDIUM),
            (FailureType.UNKNOWN_ERROR, FailureSeverity.MEDIUM),
        ]

        for failure_type, expected_severity in test_cases:
            error = Exception("Test error")
            actual_severity = self.tracker._determine_severity(error, failure_type)
            self.assertEqual(
                actual_severity, expected_severity,
                f"Failed to determine severity for {failure_type}: expected {expected_severity}, got {actual_severity}"
            )


if __name__ == "__main__":
    unittest.main()