import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def integration_test_dir():
    """Create isolated directory for integration tests"""
    test_dir = Path("output/test-integration")
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / "csv").mkdir(exist_ok=True)
    (test_dir / "logs").mkdir(exist_ok=True)
    yield test_dir
    # Cleanup is optional for debugging
