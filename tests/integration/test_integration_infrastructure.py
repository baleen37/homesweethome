# Import test setup to configure path and mocks

import pytest


@pytest.mark.integration
def test_integration_test_directory_setup(integration_test_dir):
    """Verify integration test directory is properly set up"""
    assert integration_test_dir.exists()
    assert integration_test_dir.is_dir()
    assert (integration_test_dir / "csv").exists()
    assert (integration_test_dir / "logs").exists()
