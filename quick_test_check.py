#!/usr/bin/env python3
"""Quick test to check current test status."""

import sys
from pathlib import Path

# Add src and tests to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "tests"))

# Import test_setup first

# Now import and run a few specific tests
import unittest

# Import a few test modules to check
from unit.test_adaptive_rate_limiter import TestAdaptiveRateLimiter
from unit.test_base_csv_writer import TestBaseCSVWriter
from unit.test_apartment_data_models import TestApartmentComplex

# Create a test suite
loader = unittest.TestLoader()
suite = unittest.TestSuite()
suite.addTest(loader.loadTestsFromTestCase(TestAdaptiveRateLimiter))
suite.addTest(loader.loadTestsFromTestCase(TestBaseCSVWriter))
suite.addTest(loader.loadTestsFromTestCase(TestApartmentComplex))

# Run the tests
runner = unittest.TextTestRunner(verbosity=1)
result = runner.run(suite)

print("\nTest Results:")
print(f"Tests run: {result.testsRun}")
print(f"Failures: {len(result.failures)}")
print(f"Errors: {len(result.errors)}")

if result.failures:
    print("\nFailures:")
    for test, traceback in result.failures:
        print(f"  - {test}")

if result.errors:
    print("\nErrors:")
    for test, traceback in result.errors:
        print(f"  - {test}")
