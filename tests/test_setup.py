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

# Mock pytest if not available
try:
    import pytest  # noqa: F401
except ImportError:
    mock_pytest = Mock()

    # Mock pytest.mark decorator
    class MockMark:
        def __call__(self, *args, **kwargs):
            return lambda func: func

        def parametrize(self, _param_names, _param_values):
            return lambda func: func

        def skip(self, _reason=""):
            return lambda func: func

        def skipif(self, _condition, _reason=""):
            return lambda func: func

        def xfail(self, _reason="", **kwargs):
            return lambda func: func

        def fixture(self, *args, **kwargs):
            """Mock fixture decorator that can handle both function and kwargs usage"""
            if args and callable(args[0]):
                # Direct decorator usage: @pytest.fixture
                func = args[0]
                return func
            else:
                # Decorator with params: @pytest.fixture()
                return lambda func: func

        def raises(self, _expected_exception, **kwargs):
            return MockContextManager()

    # Mock context manager for pytest.raises
    class MockContextManager:
        def __enter__(self):
            return self

        def __exit__(self, _exc_type, _exc_val, _exc_tb):
            return False

    mock_pytest.mark = MockMark()

    # Mock top-level fixture function
    def mock_fixture(*args, **kwargs):
        if args and callable(args[0]):
            return args[0]
        else:
            return lambda func: func

    mock_pytest.fixture = mock_fixture
    mock_pytest.raises = lambda expected_exception, **kwargs: MockContextManager()
    mock_pytest.skip = lambda reason="": None
    mock_pytest.xfail = lambda reason="": None

    sys.modules["pytest"] = mock_pytest

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

    # Create proper field_validator decorator
    def mock_field_validator(*field_names, **kwargs):
        """Mock field_validator decorator that can handle multiple field names"""

        def decorator(func):
            return func

        return decorator

    mock_pydantic.field_validator = mock_field_validator

    # Create proper model_validator decorator
    def mock_model_validator(mode, **kwargs):
        """Mock model_validator decorator that handles the mode parameter"""

        def decorator(func):
            return func

        return decorator

    mock_pydantic.model_validator = mock_model_validator

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

# Mock requests module with better defaults if needed
try:
    import requests  # noqa: F401

    # If requests is available, also try requests_mock
    try:
        import requests_mock  # noqa: F401
    except ImportError:
        # Create requests_mock mock
        mock_requests_mock = Mock()

        # Create a Mocker class
        class MockRequestsMocker:
            def __init__(self):
                self.get = Mock()
                self.post = Mock()
                self.put = Mock()
                self.delete = Mock()
                self.patch = Mock()
                self.request = Mock()
                self.register_uri = Mock()

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_requests_mock.Mocker = MockRequestsMocker
        mock_requests_mock.Adapter = Mock()
        mock_requests_mock.responses = Mock()
        mock_requests_mock.exceptions = Mock()

        sys.modules["requests_mock"] = mock_requests_mock
except ImportError:
    # Mock requests module
    mock_requests = Mock()

    # Create Mock Response class
    class MockResponse:
        def __init__(self, status_code=200, text="", json_data=None):
            self.status_code = status_code
            self.text = text
            self._json_data = json_data or {}
            self.headers = {}
            self.ok = status_code < 400

        def json(self):
            return self._json_data

        def raise_for_status(self):
            if not self.ok:
                raise requests.HTTPError(f"HTTP {self.status_code}")

    # Create Mock Session class
    class MockSession:
        def __init__(self):
            self.get = Mock(return_value=MockResponse())
            self.post = Mock(return_value=MockResponse())
            self.put = Mock(return_value=MockResponse())
            self.delete = Mock(return_value=MockResponse())
            self.patch = Mock(return_value=MockResponse())
            self.request = Mock(return_value=MockResponse())
            self.headers = {}

        def close(self):
            pass

    mock_requests.Response = MockResponse
    mock_requests.Session = MockSession
    mock_requests.get = Mock(return_value=MockResponse())
    mock_requests.post = Mock(return_value=MockResponse())
    mock_requests.exceptions = Mock()
    mock_requests.exceptions.HTTPError = Exception
    mock_requests.exceptions.ConnectionError = Exception
    mock_requests.exceptions.Timeout = Exception
    mock_requests.exceptions.RequestException = Exception

    sys.modules["requests"] = mock_requests

    # Also create requests_mock mock
    mock_requests_mock = Mock()

    # Create a Mocker class
    class MockRequestsMocker:
        def __init__(self):
            self.get = Mock()
            self.post = Mock()
            self.put = Mock()
            self.delete = Mock()
            self.patch = Mock()
            self.request = Mock()
            self.register_uri = Mock()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_requests_mock.Mocker = MockRequestsMocker
    mock_requests_mock.Adapter = Mock()
    mock_requests_mock.responses = Mock()
    mock_requests_mock.exceptions = Mock()

    sys.modules["requests_mock"] = mock_requests_mock

# Export commonly used modules for convenience
__all__ = [
    "Mock",
    "sys",
    "Path",
]
