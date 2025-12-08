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


@pytest.mark.integration
def test_integration_test_directory_setup(integration_test_dir):
    """Verify integration test directory is properly set up"""
    assert integration_test_dir.exists()
    assert integration_test_dir.is_dir()
    assert (integration_test_dir / "csv").exists()
    assert (integration_test_dir / "logs").exists()
