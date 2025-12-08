# Crawling System Integration Tests Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create comprehensive integration tests for the crawling system using real APIs to verify stable operation

**Architecture:** Multi-agent approach with parallel execution of test phases, using real 호갱노노 API endpoints with actual data processing and CSV output validation

**Tech Stack:** Python 3.11+, pytest, Playwright, requests, structlog, csv, asyncio

---

### Phase 1: Integration Test Infrastructure (Agent 1)

**Files:**
- Create: `tests/integration/conftest_integration.py`
- Create: `tests/integration/helpers/test_helpers.py`
- Create: `tests/integration/helpers/data_validator.py`
- Create: `tests/integration/helpers/performance_monitor.py`
- Modify: `tests/conftest.py` (add integration fixtures)

**Step 1: Write the failing test for test infrastructure**

```python
# tests/integration/conftest_integration.py
import pytest
from pathlib import Path

def test_integration_test_directory_setup(integration_test_dir):
    """Verify integration test directory is properly set up"""
    assert integration_test_dir.exists()
    assert integration_test_dir.is_dir()
    assert (integration_test_dir / "csv").exists()
    assert (integration_test_dir / "logs").exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/conftest_integration.py::test_integration_test_directory_setup -v`
Expected: FAIL with "integration_test_dir not defined"

**Step 3: Write minimal implementation**

```python
# tests/integration/conftest_integration.py
import pytest
import tempfile
import shutil
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/conftest_integration.py::test_integration_test_directory_setup -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/integration/conftest_integration.py
git commit -m "feat: add integration test infrastructure setup"
```

**Step 6: Write data validator helper tests**

```python
# tests/integration/helpers/test_data_validator.py
import pytest
from .data_validator import DataValidator

def test_data_validator_initialization():
    validator = DataValidator()
    assert validator is not None
    assert hasattr(validator, 'validate_csv_format')

def test_validate_csv_format_with_valid_data():
    validator = DataValidator()
    # Test with valid CSV structure
    pass  # Implementation in next step
```

**Step 7: Run tests to verify they fail**

Run: `pytest tests/integration/helpers/test_data_validator.py -v`
Expected: FAIL with "DataValidator not found"

**Step 8: Implement DataValidator class**

```python
# tests/integration/helpers/data_validator.py
import csv
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any

class DataValidator:
    """Validates crawled data integrity and format"""

    def __init__(self):
        self.required_columns = {
            'transactions': ['id', 'name', 'size', 'floor', 'price', 'contract_date'],
            'complexes': ['id', 'name', 'address', 'build_year', 'households']
        }

    def validate_csv_format(self, csv_path: Path, data_type: str) -> List[str]:
        """Validate CSV format and required columns"""
        errors = []

        if not csv_path.exists():
            errors.append(f"CSV file not found: {csv_path}")
            return errors

        try:
            df = pd.read_csv(csv_path)
            required = self.required_columns.get(data_type, [])
            missing = [col for col in required if col not in df.columns]

            if missing:
                errors.append(f"Missing required columns: {missing}")

            if df.empty:
                errors.append("CSV file is empty")

        except Exception as e:
            errors.append(f"Error reading CSV: {str(e)}")

        return errors
```

**Step 9: Run tests to verify they pass**

Run: `pytest tests/integration/helpers/test_data_validator.py -v`
Expected: PASS

**Step 10: Commit**

```bash
git add tests/integration/helpers/data_validator.py tests/integration/helpers/test_data_validator.py
git commit -m "feat: add data validator for integration tests"
```

---

### Phase 2: End-to-End Crawling Workflow Tests (Agent 2)

**Files:**
- Create: `tests/integration/test_e2e_crawling.py`
- Create: `tests/integration/test_real_api_endpoints.py`
- Modify: `src/crawler/config.py` (add test configuration)

**Step 1: Write failing E2E test for Gangnam district**

```python
# tests/integration/test_e2e_crawling.py
import pytest
from crawler.config import CrawlerConfig
from crawler.coordinator import CrawlCoordinator
from crawler.writers.csv_writer import CSVWriter

def test_full_gangnam_crawling_workflow(integration_test_dir):
    """Test complete crawling workflow for Gangnam district"""
    # This should crawl actual Gangnam data and save to CSV
    config = CrawlerConfig(
        output_dir=str(integration_test_dir / "csv"),
        districts=["강남구"],
        property_types=["apartment"],
        trade_types=["sale", "jeonse"]
    )

    coordinator = CrawlCoordinator(config)
    success = coordinator.crawl_all()

    assert success, "Crawling should complete successfully"

    # Verify output files
    transactions_csv = integration_test_dir / "csv" / "transactions.csv"
    complexes_csv = integration_test_dir / "csv" / "complexes.csv"

    assert transactions_csv.exists(), "Transactions CSV should be created"
    assert complexes_csv.exists(), "Complexes CSV should be created"

    # Verify data quality
    assert transactions_csv.stat().st_size > 0, "Transactions CSV should not be empty"
    assert complexes_csv.stat().st_size > 0, "Complexes CSV should not be empty"
```

**Step 2: Run test to verify it fails (may pass partially but need validation)**

Run: `pytest tests/integration/test_e2e_crawling.py::test_full_gangnam_crawling_workflow -v -s`
Expected: May partially work but lacks proper validation and cleanup

**Step 3: Implement test configuration in CrawlerConfig**

```python
# src/crawler/config.py (add to existing class)
@classmethod
def for_integration_test(cls, output_dir: str, districts: List[str]) -> 'CrawlerConfig':
    """Create config for integration testing"""
    return cls(
        output_dir=output_dir,
        districts=districts,
        property_types=["apartment"],
        trade_types=["sale", "jeonse"],
        max_workers=1,  # Single thread for stable testing
        timeout=30,
        checkpoint_file="output/test-integration/checkpoint.json"
    )
```

**Step 4: Write API endpoint validation test**

```python
# tests/integration/test_real_api_endpoints.py
import pytest
import requests
from src.crawler.api.hogangnono_client import HogangnonoAPIClient

def test_real_hogangnono_api_availability():
    """Test that real 호갱노노 API endpoints are accessible"""
    client = HogangnonoAPIClient()

    # Test basic connectivity
    response = client.get("https://hogangnono.com/api/v2/ranks/rolling")
    assert response.status_code == 200

    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)

def test_bounding_box_api_with_real_coordinates():
    """Test bounding box API with Seoul coordinates"""
    client = HogangnonoAPIClient()

    # Gangnam area bounding box
    params = {
        "bounds": "127.044,37.514,127.106,37.527",
        "type": "apartment",
        "trade": "sale"
    }

    response = client.get("https://hogangnono.com/api/v2/pois-bounding", params=params)
    assert response.status_code == 200

    data = response.json()
    assert len(data) > 0, "Should return at least some results"
```

**Step 5: Run API tests to verify real connectivity**

Run: `pytest tests/integration/test_real_api_endpoints.py -v -s`
Expected: Should pass if API is accessible

**Step 6: Update E2E test with proper cleanup and validation**

```python
# tests/integration/test_e2e_crawling.py (updated test)
@pytest.mark.integration
def test_full_gangnam_crawling_workflow(integration_test_dir):
    """Test complete crawling workflow for Gangnam district"""
    from ..helpers.data_validator import DataValidator

    # Setup test config
    config = CrawlerConfig.for_integration_test(
        output_dir=str(integration_test_dir / "csv"),
        districts=["강남구"]
    )

    coordinator = CrawlCoordinator(config)
    validator = DataValidator()

    try:
        # Run crawling
        success = coordinator.crawl_all()
        assert success, "Crawling should complete successfully"

        # Verify output files exist
        transactions_csv = integration_test_dir / "csv" / "transactions.csv"
        complexes_csv = integration_test_dir / "csv" / "complexes.csv"

        assert transactions_csv.exists(), "Transactions CSV should be created"
        assert complexes_csv.exists(), "Complexes CSV should be created"

        # Validate data format
        transaction_errors = validator.validate_csv_format(transactions_csv, 'transactions')
        complex_errors = validator.validate_csv_format(complexes_csv, 'complexes')

        assert len(transaction_errors) == 0, f"Transaction CSV errors: {transaction_errors}"
        assert len(complex_errors) == 0, f"Complex CSV errors: {complex_errors}"

        # Verify data content
        import pandas as pd
        df_trans = pd.read_csv(transactions_csv)
        df_comp = pd.read_csv(complexes_csv)

        assert len(df_trans) > 0, "Should have transaction data"
        assert len(df_comp) > 0, "Should have complex data"
        assert '강남구' in str(df_comp['address'].values), "Should contain Gangnam addresses"

    finally:
        # Cleanup checkpoint file
        checkpoint_file = integration_test_dir / "csv" / "checkpoint.json"
        if checkpoint_file.exists():
            checkpoint_file.unlink()
```

**Step 7: Run updated E2E test**

Run: `pytest tests/integration/test_e2e_crawling.py::test_full_gangnam_crawling_workflow -v -s`
Expected: Should pass with proper validation

**Step 8: Commit**

```bash
git add tests/integration/test_e2e_crawling.py tests/integration/test_real_api_endpoints.py src/crawler/config.py
git commit -m "feat: implement end-to-end crawling integration tests"
```

---

### Phase 3: Stability and Error Recovery Tests (Agent 3)

**Files:**
- Create: `tests/integration/test_checkpoint_recovery.py`
- Create: `tests/integration/test_rate_limiting_adaptation.py`
- Create: `tests/integration/test_long_running_stability.py`
- Create: `tests/integration/helpers/error_injector.py`

**Step 1: Write checkpoint/recovery test**

```python
# tests/integration/test_checkpoint_recovery.py
import pytest
import json
import time
from pathlib import Path
from crawler.config import CrawlerConfig
from crawler.coordinator import CrawlCoordinator
from crawler.utils.checkpoint import CheckpointManager

def test_checkpoint_and_recovery_mechanism(integration_test_dir):
    """Test that crawling can be paused and resumed from checkpoint"""
    checkpoint_file = integration_test_dir / "checkpoint.json"

    # Initial setup - crawl partially
    config1 = CrawlerConfig.for_integration_test(
        output_dir=str(integration_test_dir / "csv"),
        districts=["강남구"]
    )
    config1.checkpoint_file = str(checkpoint_file)

    # Create initial checkpoint
    checkpoint_manager = CheckpointManager(checkpoint_file)
    test_data = {
        "completed_dongs": ["역삼동"],
        "current_dong": "강남동",
        "progress": 0.3,
        "timestamp": time.time()
    }
    checkpoint_manager.save(test_data)

    # Verify checkpoint exists
    assert checkpoint_file.exists(), "Checkpoint file should be created"

    # Test recovery
    config2 = CrawlerConfig.for_integration_test(
        output_dir=str(integration_test_dir / "csv"),
        districts=["강남구"]
    )
    config2.checkpoint_file = str(checkpoint_file)

    recovered_data = checkpoint_manager.load()
    assert recovered_data is not None, "Should be able to load checkpoint"
    assert recovered_data["completed_dongs"] == ["역삼동"], "Should preserve completed dongs"
    assert recovered_data["current_dong"] == "강남동", "Should preserve current state"
```

**Step 2: Run checkpoint test**

Run: `pytest tests/integration/test_checkpoint_recovery.py::test_checkpoint_and_recovery_mechanism -v`
Expected: Should pass

**Step 3: Write rate limiting adaptation test**

```python
# tests/integration/test_rate_limiting_adaptation.py
import pytest
import time
from crawler.rate_limiter import AdaptiveRateLimiter

def test_rate_limiter_adapts_to_real_api_responses(integration_test_dir):
    """Test that rate limiter adapts to actual API responses"""
    limiter = AdaptiveRateLimiter(initial_delay=1.0)  # Start with 1 second delay

    # Simulate successful requests
    for i in range(10):
        limiter.record_success()
        start_time = time.time()
        limiter.wait_if_needed()
        wait_time = time.time() - start_time

        # After 10 successes, delay should decrease
        if i >= 5:
            assert wait_time < 1.0, f"Delay should decrease after successes, got {wait_time}"

    # Simulate rate limit error
    limiter.record_rate_limit_error()

    # Delay should increase significantly
    start_time = time.time()
    limiter.wait_if_needed()
    wait_time = time.time() - start_time

    assert wait_time > 1.5, f"Delay should increase after rate limit, got {wait_time}"

def test_rate_limiting_with_real_api_calls(integration_test_dir):
    """Test rate limiting behavior with actual API calls"""
    from src.crawler.api.hogangnono_client import HogangnonoAPIClient

    client = HogangnonoAPIClient()
    limiter = AdaptiveRateLimiter(initial_delay=2.0)

    # Make multiple rapid requests to test adaptation
    response_times = []
    for i in range(5):
        start_time = time.time()
        response = client.get("https://hogangnono.com/api/v2/ranks/rolling")

        if response.status_code == 200:
            limiter.record_success()
        elif response.status_code == 429:
            limiter.record_rate_limit_error()

        limiter.wait_if_needed()
        total_time = time.time() - start_time
        response_times.append(total_time)

    # Verify rate limiting is working (requests should be spaced out)
    assert all(t > 1.5 for t in response_times), "Rate limiting should enforce minimum delays"
```

**Step 4: Run rate limiting tests**

Run: `pytest tests/integration/test_rate_limiting_adaptation.py -v -s`
Expected: Should pass with actual timing verification

**Step 5: Write long-running stability test**

```python
# tests/integration/test_long_running_stability.py
import pytest
import time
import psutil
import os
from crawler.config import CrawlerConfig
from crawler.coordinator import CrawlCoordinator

def test_memory_usage_stability_during_crawling(integration_test_dir):
    """Test that memory usage remains stable during extended crawling"""
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Configure for extended crawling (multiple districts)
    config = CrawlerConfig.for_integration_test(
        output_dir=str(integration_test_dir / "csv"),
        districts=["강남구", "서초구"]  # Larger test case
    )

    coordinator = CrawlCoordinator(config)

    # Monitor memory during crawling
    memory_samples = [initial_memory]

    # Start crawling (this will take time)
    start_time = time.time()
    success = coordinator.crawl_all()
    end_time = time.time()

    final_memory = process.memory_info().rss / 1024 / 1024
    memory_samples.append(final_memory)

    # Verify stability
    memory_increase = final_memory - initial_memory
    memory_increase_per_minute = memory_increase / ((end_time - start_time) / 60)

    assert success, "Crawling should complete successfully"
    assert memory_increase_per_minute < 50, f"Memory leak detected: {memory_increase_per_minute:.2f} MB/min"
    assert final_memory < initial_memory + 500, f"Excessive memory usage: {final_memory:.2f} MB"

def test_resource_cleanup_after_crawling(integration_test_dir):
    """Test that all resources are properly cleaned up"""
    config = CrawlerConfig.for_integration_test(
        output_dir=str(integration_test_dir / "csv"),
        districts=["강남구"]
    )

    coordinator = CrawlCoordinator(config)

    # Count open file descriptors before
    process = psutil.Process()
    initial_files = len(process.open_files())

    # Run crawling
    success = coordinator.crawl_all()

    # Check cleanup after some time
    time.sleep(2)
    final_files = len(process.open_files())

    assert success, "Crawling should complete successfully"
    assert final_files <= initial_files + 5, f"File descriptor leak: {final_files - initial_files}"
```

**Step 6: Run stability tests**

Run: `pytest tests/integration/test_long_running_stability.py -v -s`
Expected: Should pass but may take time

**Step 7: Commit**

```bash
git add tests/integration/test_checkpoint_recovery.py tests/integration/test_rate_limiting_adaptation.py tests/integration/test_long_running_stability.py
git commit -m "feat: add stability and error recovery integration tests"
```

---

### Phase 4: Test Execution and Reporting (Agent 4)

**Files:**
- Create: `scripts/run_integration_tests.py`
- Create: `tests/integration/test_runner.py`
- Create: `tests/integration/reporting/test_report_generator.py`

**Step 1: Write integration test runner script**

```python
# scripts/run_integration_tests.py
#!/usr/bin/env python3
"""
Integration test runner for crawling system
"""
import sys
import subprocess
import time
import json
from pathlib import Path

def main():
    """Run all integration tests and generate report"""
    print("Starting crawling system integration tests...")

    # Create output directory
    output_dir = Path("output/test-integration")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run tests in phases
    phases = [
        ("Infrastructure", "tests/integration/conftest_integration.py tests/integration/helpers/"),
        ("API Connectivity", "tests/integration/test_real_api_endpoints.py"),
        ("E2E Crawling", "tests/integration/test_e2e_crawling.py"),
        ("Stability", "tests/integration/test_checkpoint_recovery.py tests/integration/test_rate_limiting_adaptation.py"),
        ("Long Running", "tests/integration/test_long_running_stability.py")
    ]

    results = {}
    start_time = time.time()

    for phase_name, test_path in phases:
        print(f"\n=== Running {phase_name} Tests ===")
        phase_start = time.time()

        try:
            cmd = ["pytest", "-v", "--tb=short", test_path]
            result = subprocess.run(cmd, capture_output=True, text=True)

            phase_time = time.time() - phase_start
            results[phase_name] = {
                "success": result.returncode == 0,
                "duration": phase_time,
                "stdout": result.stdout,
                "stderr": result.stderr
            }

            if result.returncode == 0:
                print(f"✅ {phase_name} tests passed ({phase_time:.2f}s)")
            else:
                print(f"❌ {phase_name} tests failed")
                print(result.stderr)

        except Exception as e:
            print(f"❌ Error running {phase_name}: {e}")
            results[phase_name] = {
                "success": False,
                "error": str(e)
            }

    total_time = time.time() - start_time

    # Generate report
    report = {
        "timestamp": time.time(),
        "total_duration": total_time,
        "phases": results,
        "summary": {
            "total_phases": len(phases),
            "passed_phases": sum(1 for r in results.values() if r.get("success", False)),
            "failed_phases": sum(1 for r in results.values() if not r.get("success", False))
        }
    }

    # Save report
    report_file = output_dir / "integration_test_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    # Print summary
    print(f"\n=== Test Summary ===")
    print(f"Total time: {total_time:.2f}s")
    print(f"Phases passed: {report['summary']['passed_phases']}/{report['summary']['total_phases']}")
    print(f"Report saved to: {report_file}")

    return report['summary']['failed_phases'] == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

**Step 2: Make runner script executable**

Run: `chmod +x scripts/run_integration_tests.py`

**Step 3: Write report generator**

```python
# tests/integration/reporting/test_report_generator.py
import json
import pandas as pd
from datetime import datetime
from pathlib import Path

class IntegrationTestReportGenerator:
    """Generate comprehensive integration test reports"""

    def __init__(self, report_file: Path):
        self.report_file = report_file

    def generate_html_report(self) -> str:
        """Generate HTML report from test results"""
        with open(self.report_file) as f:
            data = json.load(f)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Crawling Integration Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .phase {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .success {{ border-left: 5px solid #4CAF50; }}
                .failure {{ border-left: 5px solid #f44336; }}
                .summary {{ background: #e3f2fd; padding: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Crawling System Integration Test Report</h1>
                <p>Generated: {datetime.fromtimestamp(data['timestamp'])}</p>
                <p>Total Duration: {data['total_duration']:.2f} seconds</p>
            </div>

            <div class="summary">
                <h2>Summary</h2>
                <p>Passed: {data['summary']['passed_phases']}/{data['summary']['total_phases']} phases</p>
            </div>

            <h2>Phase Details</h2>
        """

        for phase_name, result in data['phases'].items():
            status_class = "success" if result.get('success') else "failure"
            status_text = "PASSED" if result.get('success') else "FAILED"

            html += f"""
            <div class="phase {status_class}">
                <h3>{phase_name} - {status_text}</h3>
                <p>Duration: {result.get('duration', 0):.2f} seconds</p>
                {f'<pre>{result["stderr"]}</pre>' if not result.get('success') else ''}
            </div>
            """

        html += """
        </body>
        </html>
        """

        return html

    def save_html_report(self, output_path: Path):
        """Save HTML report to file"""
        html = self.generate_html_report()
        with open(output_path, 'w') as f:
            f.write(html)
```

**Step 4: Test the complete integration test suite**

Run: `python scripts/run_integration_tests.py`
Expected: Should execute all phases and generate report

**Step 5: Verify report generation**

Run: `ls -la output/test-integration/`
Expected: Should see `integration_test_report.json` and HTML report

**Step 6: Commit**

```bash
git add scripts/run_integration_tests.py tests/integration/reporting/
git commit -m "feat: add integration test runner and reporting"
```

---

## Final Integration Test Execution

**Step 1: Run complete test suite**

```bash
# Execute all integration tests
python scripts/run_integration_tests.py

# Or run with pytest directly
pytest tests/integration/ -v -m integration
```

**Step 2: Review test results**

Check:
- `output/test-integration/integration_test_report.json` for detailed results
- HTML report for visual summary
- Generated CSV files for data quality
- Test logs for any failures

**Step 3: Validate crawling system**

Verify:
- ✅ Real API connectivity works
- ✅ End-to-end crawling produces valid CSV output
- ✅ Checkpoint/recovery mechanism functions
- ✅ Rate limiting adapts properly
- ✅ Memory usage remains stable
- ✅ Resources are cleaned up properly

**Step 4: Final commit with documentation**

```bash
git add docs/plans/2025-01-08-crawling-integration-tests.md
git commit -m "docs: add comprehensive integration test plan"
```

---

## Test Execution Commands Summary

```bash
# Run all integration tests
python scripts/run_integration_tests.py

# Run specific test categories
pytest tests/integration/test_e2e_crawling.py -v -s
pytest tests/integration/test_real_api_endpoints.py -v
pytest tests/integration/test_checkpoint_recovery.py -v

# Run with memory profiling
pytest tests/integration/test_long_running_stability.py -v -s

# Generate test coverage for integration tests
pytest tests/integration/ --cov=src --cov-report=html --cov-report=term
```

**This comprehensive plan provides:**
1. Isolated test environment setup
2. Real API integration testing
3. End-to-end workflow validation
4. Stability and error recovery verification
5. Automated execution and reporting
6. Detailed documentation and results tracking