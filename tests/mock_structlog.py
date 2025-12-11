"""Mock implementation of structlog for testing purposes.

This module provides a minimal mock implementation of structlog
that provides the basic logging functionality needed by the code.
"""

import sys
from typing import Any, Dict
from unittest.mock import Mock


class MockLogger:
    """Mock logger that mimics structlog logger behavior."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize mock logger."""
        self._bound = kwargs.copy()
        self._calls = []  # Track all method calls for testing

    def bind(self, **kwargs: Any) -> "MockLogger":
        """Return a new logger with bound values."""
        new_logger = MockLogger(**self._bound)
        new_logger._bound.update(kwargs)
        return new_logger

    def info(self, event: str, **kwargs: Any) -> None:
        """Log info message."""
        self._calls.append(("info", event, kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._calls.append(("warning", event, kwargs))

    def debug(self, event: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._calls.append(("debug", event, kwargs))

    def error(self, event: str, **kwargs: Any) -> None:
        """Log error message."""
        self._calls.append(("error", event, kwargs))


# Create a module-level mock
_logger_instances: Dict[str, MockLogger] = {}


def get_logger(**kwargs: Any) -> MockLogger:
    """Get or create a logger instance.

    Mimics structlog.get_logger() behavior.
    """
    # Create a unique key based on kwargs
    key = str(sorted(kwargs.items()))

    if key not in _logger_instances:
        _logger_instances[key] = MockLogger(**kwargs)

    return _logger_instances[key]


# Install the mock into sys.modules if structlog is not installed
def install_mock() -> None:
    """Install the mock structlog into sys.modules."""
    # Create a mock module
    mock_module = Mock()
    mock_module.get_logger = get_logger

    # Add it to sys.modules
    sys.modules["structlog"] = mock_module


# Auto-install if imported
if "structlog" not in sys.modules:
    install_mock()
