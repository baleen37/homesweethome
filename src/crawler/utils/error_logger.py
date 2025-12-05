"""Enhanced error logging with detailed context and correlation.

This module provides enhanced error logging capabilities including:
- Structured error context
- Error correlation IDs
- Stack trace extraction
- Error categorization
- Persistent error logs
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import structlog


class ErrorCategory(Enum):
    """Categories of errors for better organization."""
    NETWORK = "network"
    API = "api"
    PARSING = "parsing"
    VALIDATION = "validation"
    SYSTEM = "system"
    BUSINESS = "business"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information associated with an error."""
    correlation_id: str
    timestamp: float
    category: ErrorCategory
    severity: ErrorSeverity
    component: str  # e.g., "naver_crawler", "csv_writer"
    operation: str  # e.g., "fetch_complex_detail"
    item_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["category"] = self.category.value
        data["severity"] = self.severity.value
        return data


class ErrorLogger:
    """
    Enhanced error logger with structured context and correlation.

    Features:
    - Automatic correlation ID generation
    - Detailed error context
    - Stack trace preservation
    - Error categorization
    - Persistent logging
    - Error aggregation and analysis
    """

    def __init__(
        self,
        component: str,
        log_file: Optional[Path] = None,
        max_log_entries: int = 10000,
        persist_errors: bool = True,
    ) -> None:
        """
        Initialize error logger.

        Args:
            component: Component name for log entries
            log_file: File to persist error logs
            max_log_entries: Maximum entries to keep in memory
            persist_errors: Whether to persist errors to disk
        """
        self.component = component
        self.log_file = log_file
        self.max_log_entries = max_log_entries
        self.persist_errors = persist_errors

        self.error_log: List[Dict[str, Any]] = []
        self.error_counts: Dict[str, int] = {}
        self.error_patterns: Dict[str, List[str]] = {}

        self.logger = structlog.get_logger().bind(
            component=component,
            error_logger=id(self),
        )

        # Ensure log directory exists
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_error(
        self,
        error: Exception,
        operation: str,
        category: Optional[ErrorCategory] = None,
        severity: Optional[ErrorSeverity] = None,
        item_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> str:
        """
        Log an error with enhanced context.

        Args:
            error: The exception that occurred
            operation: Operation being performed
            category: Error category
            severity: Error severity
            item_id: ID of the item being processed
            metadata: Additional context metadata
            correlation_id: Existing correlation ID (auto-generated if None)

        Returns:
            Correlation ID for the error
        """
        # Generate correlation ID if not provided
        if not correlation_id:
            correlation_id = str(uuid4())

        # Auto-categorize if not provided
        if not category:
            category = self._categorize_error(error)

        # Default severity if not provided
        if not severity:
            severity = ErrorSeverity.ERROR

        # Create context
        context = ErrorContext(
            correlation_id=correlation_id,
            timestamp=time.time(),
            category=category,
            severity=severity,
            component=self.component,
            operation=operation,
            item_id=item_id,
            metadata=metadata,
        )

        # Extract error details
        error_details = {
            "type": type(error).__name__,
            "message": str(error),
            "module": getattr(error, "__module__", ""),
            "args": getattr(error, "args", []),
        }

        # Extract stack trace
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if exc_traceback:
            error_details["stack_trace"] = traceback.format_exception(
                exc_type, exc_value, exc_traceback
            )
            error_details["stack_frames"] = self._extract_stack_frames(exc_traceback)

        # Create log entry
        log_entry = {
            "context": context.to_dict(),
            "error": error_details,
        }

        # Add to memory log
        self.error_log.append(log_entry)
        if len(self.error_log) > self.max_log_entries:
            self.error_log.pop(0)

        # Update statistics
        error_key = f"{category.value}:{operation}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

        # Track error patterns
        pattern = self._extract_error_pattern(error)
        if pattern not in self.error_patterns:
            self.error_patterns[pattern] = []
        self.error_patterns[pattern].append(correlation_id)

        # Log with structlog
        log_method = getattr(self.logger, severity.value)
        log_method(
            "error_occurred",
            correlation_id=correlation_id,
            category=category.value,
            operation=operation,
            error_type=error_details["type"],
            error_message=error_details["message"],
            item_id=item_id,
            **(metadata or {}),
        )

        # Persist if enabled
        if self.persist_errors:
            self._persist_error(log_entry)

        return correlation_id

    def log_warning(
        self,
        message: str,
        operation: str,
        item_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Log a warning message."""
        correlation_id = str(uuid4())
        context = ErrorContext(
            correlation_id=correlation_id,
            timestamp=time.time(),
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.WARNING,
            component=self.component,
            operation=operation,
            item_id=item_id,
            metadata=metadata,
        )

        self.logger.warning(
            message,
            correlation_id=correlation_id,
            operation=operation,
            item_id=item_id,
            **(metadata or {}),
        )

        return correlation_id

    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get summary of recent errors.

        Args:
            hours: Number of hours to look back

        Returns:
            Error summary statistics
        """
        cutoff_time = time.time() - (hours * 3600)
        recent_errors = [
            e for e in self.error_log
            if e["context"]["timestamp"] > cutoff_time
        ]

        # Count by category
        category_counts = {}
        severity_counts = {}
        operation_counts = {}

        for error in recent_errors:
            ctx = error["context"]
            category = ctx["category"]
            severity = ctx["severity"]
            operation = ctx["operation"]

            category_counts[category] = category_counts.get(category, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            operation_counts[operation] = operation_counts.get(operation, 0) + 1

        # Find most common errors
        error_types = {}
        for error in recent_errors:
            error_type = error["error"]["type"]
            error_types[error_type] = error_types.get(error_type, 0) + 1

        return {
            "timeframe_hours": hours,
            "total_errors": len(recent_errors),
            "errors_per_hour": len(recent_errors) / max(hours, 1),
            "by_category": category_counts,
            "by_severity": severity_counts,
            "by_operation": operation_counts,
            "by_type": dict(sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:10]),
            "unique_patterns": len(self.error_patterns),
        }

    def get_error_details(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed error information by correlation ID."""
        for error in self.error_log:
            if error["context"]["correlation_id"] == correlation_id:
                return error
        return None

    def get_errors_by_item(self, item_id: str) -> List[Dict[str, Any]]:
        """Get all errors for a specific item."""
        return [
            e for e in self.error_log
            if e["context"].get("item_id") == item_id
        ]

    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Automatically categorize an error."""
        error_type = type(error).__name__.lower()
        error_msg = str(error).lower()

        if any(k in error_type for k in ["connection", "timeout", "network"]):
            return ErrorCategory.NETWORK
        elif any(k in error_type for k in ["http", "api", "request"]):
            return ErrorCategory.API
        elif any(k in error_type for k in ["parse", "json", "decode"]):
            return ErrorCategory.PARSING
        elif any(k in error_type for k in ["validation", "value", "type"]):
            return ErrorCategory.VALIDATION
        elif any(k in error_type for k in ["os", "io", "file", "permission"]):
            return ErrorCategory.SYSTEM
        else:
            return ErrorCategory.UNKNOWN

    def _extract_stack_frames(self, tb: Any) -> List[Dict[str, Any]]:
        """Extract relevant frames from traceback."""
        frames = []
        current_tb = tb

        while current_tb:
            frame = current_tb.tb_frame
            frames.append({
                "filename": frame.f_code.co_filename,
                "function": frame.f_code.co_name,
                "line_number": tb.tb_lineno,
                "locals": {k: str(v)[:100] for k, v in frame.f_locals.items()
                          if not k.startswith('_') and not callable(v)},
            })
            current_tb = current_tb.tb_next

        # Return last 5 frames to avoid too much noise
        return frames[-5:] if len(frames) > 5 else frames

    def _extract_error_pattern(self, error: Exception) -> str:
        """Extract a pattern from the error for grouping similar errors."""
        error_type = type(error).__name__
        # Remove specific values from message to get pattern
        message = str(error)
        pattern = f"{error_type}: {message}"
        # Replace numbers and specific IDs with placeholders
        import re
        pattern = re.sub(r'\d+', '<N>', pattern)
        pattern = re.sub(r'[a-f0-9]{8,}', '<ID>', pattern)
        return pattern

    def _persist_error(self, log_entry: Dict[str, Any]) -> None:
        """Persist error to disk."""
        if not self.log_file:
            return

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                # Write as JSON lines for easier parsing
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.error(
                "failed_to_persist_error",
                error=str(e),
                log_file=str(self.log_file),
            )

    def cleanup_old_logs(self, hours: int = 168) -> int:  # Default: 1 week
        """Clean up old error logs."""
        cutoff_time = time.time() - (hours * 3600)
        initial_count = len(self.error_log)

        self.error_log = [
            e for e in self.error_log
            if e["context"]["timestamp"] > cutoff_time
        ]

        removed = initial_count - len(self.error_log)
        if removed > 0:
            self.logger.info(
                "cleaned_up_error_logs",
                removed=removed,
                remaining=len(self.error_log),
            )

        return removed


# Global error logger instance
_global_error_logger: Optional[ErrorLogger] = None


def get_error_logger(
    component: str,
    log_file: Optional[Path] = None,
) -> ErrorLogger:
    """Get or create an error logger instance."""
    global _global_error_logger

    if _global_error_logger is None:
        _global_error_logger = ErrorLogger(
            component=component,
            log_file=log_file,
        )

    return _global_error_logger


def log_error(
    error: Exception,
    operation: str,
    category: Optional[ErrorCategory] = None,
    severity: Optional[ErrorSeverity] = None,
    item_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Convenience function to log an error."""
    logger = get_error_logger("default")
    return logger.log_error(
        error=error,
        operation=operation,
        category=category,
        severity=severity,
        item_id=item_id,
        metadata=metadata,
    )


# Decorator for automatic error logging
def log_errors(
    operation: str,
    category: Optional[ErrorCategory] = None,
    severity: Optional[ErrorSeverity] = None,
    reraise: bool = True,
) -> Callable:
    """Decorator to automatically log function errors."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Extract item_id from kwargs if available
                item_id = kwargs.get("item_id") or kwargs.get("complex_id") or kwargs.get("dong_id")

                # Log the error
                log_error(
                    error=e,
                    operation=operation,
                    category=category,
                    severity=severity,
                    item_id=item_id,
                    metadata={"args_count": len(args), "kwargs_keys": list(kwargs.keys())},
                )

                if reraise:
                    raise
                return None
        return wrapper
    return decorator