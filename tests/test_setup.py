"""
Common test setup module that provides necessary mocking and path configuration.

This module should be imported at the beginning of all test files to ensure:
1. src/ is in Python path
2. structlog is properly mocked
3. Other optional dependencies are mocked as needed
"""

import sys
from pathlib import Path
from unittest.mock import Mock

# Add src to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Mock structlog before importing any crawler modules
try:
    import structlog  # noqa: F401
except ImportError:
    # Create a mock module
    mock_structlog = Mock()

    # Mock get_logger function
    def mock_get_logger(**kwargs):
        logger = Mock()
        logger.info = Mock()
        logger.warning = Mock()
        logger.debug = Mock()
        logger.error = Mock()
        logger.bind = lambda **kwargs: logger
        return logger

    mock_structlog.get_logger = mock_get_logger
    sys.modules["structlog"] = mock_structlog

# Mock other optional dependencies that might not be installed
try:
    from dotenv import load_dotenv  # noqa: F401
except ImportError:
    # Create a mock load_dotenv function
    mock_dotenv = Mock()
    mock_dotenv.load_dotenv = Mock()
    sys.modules["dotenv"] = mock_dotenv

try:
    from pydantic import BaseModel  # noqa: F401
except ImportError:
    # Create a minimal mock for pydantic
    mock_pydantic = Mock()

    # Mock BaseModel
    class MockBaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        def model_dump(self):
            return self.__dict__

    mock_pydantic.BaseModel = MockBaseModel
    mock_pydantic.Field = lambda default=None, **kwargs: default
    mock_pydantic.field_validator = lambda field_name, **kwargs: lambda func: func
    mock_pydantic.model_validator = lambda mode, **kwargs: lambda func: func
    mock_pydantic.ValidationError = ValueError

    sys.modules["pydantic"] = mock_pydantic

# Mock pandas if needed
try:
    import pandas  # noqa: F401
except ImportError:
    mock_pandas = Mock()
    mock_pandas.DataFrame = Mock()
    mock_pandas.read_csv = Mock()
    sys.modules["pandas"] = mock_pandas

# Mock playwright if needed
try:
    import playwright  # noqa: F401
except ImportError:
    mock_playwright = Mock()
    sys.modules["playwright"] = mock_playwright
    sys.modules["playwright.async_api"] = Mock()
    sys.modules["playwright.sync_api"] = Mock()

# Export commonly used modules for convenience
__all__ = [
    "Mock",
    "sys",
    "Path",
]
