#!/usr/bin/env python3
"""
Integration test runner for crawling system
"""

import sys
import subprocess
import time
import json
from pathlib import Path

# Add the project root to the Python path for report generator
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    """Run all integration tests and generate report"""
    print("Starting crawling system integration tests...")

    # Create output directory
    output_dir = Path("output/test-integration")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run tests in phases
    phases = [
        ("Infrastructure", "tests/integration/test_integration_infrastructure.py"),
        ("API Connectivity", "tests/integration/test_real_api_endpoints.py"),
        ("E2E Crawling", "tests/integration/test_e2e_crawling.py"),
        (
            "Stability",
            "tests/integration/test_checkpoint_recovery.py tests/integration/test_rate_limiting_adaptation.py",
        ),
        ("Long Running", "tests/integration/test_long_running_stability.py"),
    ]

    results = {}
    start_time = time.time()

    for phase_name, test_path in phases:
        print(f"\n=== Running {phase_name} Tests ===")
        phase_start = time.time()

        try:
            # Handle multiple test files
            if " " in test_path:
                test_files = test_path.split()
            else:
                test_files = [test_path]

            cmd = ["pytest", "-v", "--tb=short", "--run-integration"] + test_files
            result = subprocess.run(cmd, capture_output=True, text=True)

            phase_time = time.time() - phase_start
            results[phase_name] = {
                "success": result.returncode == 0,
                "duration": phase_time,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            if result.returncode == 0:
                print(f"✅ {phase_name} tests passed ({phase_time:.2f}s)")
            else:
                print(f"❌ {phase_name} tests failed")
                print(result.stderr)

        except Exception as e:
            print(f"❌ Error running {phase_name}: {e}")
            results[phase_name] = {"success": False, "error": str(e)}

    total_time = time.time() - start_time

    # Generate report
    report = {
        "timestamp": time.time(),
        "total_duration": total_time,
        "phases": results,
        "summary": {
            "total_phases": len(phases),
            "passed_phases": sum(1 for r in results.values() if r.get("success", False)),
            "failed_phases": sum(1 for r in results.values() if not r.get("success", False)),
        },
    }

    # Save report
    report_file = output_dir / "integration_test_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("\n=== Test Summary ===")
    print(f"Total time: {total_time:.2f}s")
    print(
        f"Phases passed: {report['summary']['passed_phases']}/{report['summary']['total_phases']}"
    )
    print(f"Report saved to: {report_file}")

    return report["summary"]["failed_phases"] == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
