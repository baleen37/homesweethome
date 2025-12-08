import subprocess
import time
import json
from pathlib import Path


def test_integration_test_runner():
    """Test that the integration test runner script works correctly"""
    runner_path = Path("scripts/run_integration_tests.py")

    # Verify runner exists and is executable
    assert runner_path.exists(), "Integration test runner should exist"
    assert runner_path.is_file(), "Runner should be a file"

    # Note: We don't actually run the full suite here as it would take too long
    # This test just verifies the runner script is valid Python

    # Check that runner script has valid Python syntax
    result = subprocess.run(["python", "-m", "py_compile", str(runner_path)], capture_output=True)

    assert result.returncode == 0, f"Runner script should have valid Python syntax: {result.stderr}"


def test_report_generator_class():
    """Test that the report generator class can be instantiated"""
    from .reporting.test_report_generator import IntegrationTestReportGenerator

    # Create a dummy report file for testing
    test_report_data = {
        "timestamp": time.time(),
        "total_duration": 120.5,
        "phases": {
            "Test Phase 1": {
                "success": True,
                "duration": 30.2,
                "stdout": "All tests passed",
                "stderr": "",
            },
            "Test Phase 2": {
                "success": False,
                "duration": 45.7,
                "stdout": "Some tests failed",
                "stderr": "AssertionError: Test failed",
            },
        },
        "summary": {"total_phases": 2, "passed_phases": 1, "failed_phases": 1},
    }

    # Write test report
    test_report_file = Path("output/test-integration/test_report.json")
    test_report_file.parent.mkdir(parents=True, exist_ok=True)

    with open(test_report_file, "w") as f:
        json.dump(test_report_data, f, indent=2)

    # Test report generator
    generator = IntegrationTestReportGenerator(test_report_file)

    # Test HTML generation
    html = generator.generate_html_report()
    assert "Crawling System Integration Test Report" in html
    assert "PASSED" in html
    assert "FAILED" in html
    assert "120.50 seconds" in html

    # Test HTML saving
    html_output = test_report_file.parent / "test_report.html"
    generator.save_html_report(html_output)
    assert html_output.exists(), "HTML report should be created"

    # Cleanup
    if test_report_file.exists():
        test_report_file.unlink()
    if html_output.exists():
        html_output.unlink()
