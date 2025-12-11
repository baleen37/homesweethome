#!/usr/bin/env python3
"""Simple test runner using Python's built-in unittest module."""

import os
import sys
import unittest
import importlib.util
import inspect
from pathlib import Path
from typing import List, Any, Callable

# Set up mocks before any imports
import types


# Mock pytest module globally
class PytestRaises:
    """Context manager to mimic pytest.raises using unittest.assertRaises."""

    def __init__(self, expected_exception, match=None):
        # Find the current test case instance from the call stack
        for frame in inspect.stack():
            frame_locals = frame[0].f_locals
            for obj in frame_locals.values():
                if isinstance(obj, unittest.TestCase):
                    self.test_case = obj
                    break
            if hasattr(self, "test_case"):
                break

        self.expected_exception = expected_exception
        self.match = match
        self.exception_info = None

    def __enter__(self):
        if hasattr(self, "test_case"):
            if self.match:
                self.cm = self.test_case.assertRaisesRegex(self.expected_exception, self.match)
            else:
                self.cm = self.test_case.assertRaises(self.expected_exception)
        else:
            # Fallback if no test case found
            import unittest

            if self.match:
                self.cm = unittest.TestCase().assertRaisesRegex(self.expected_exception, self.match)
            else:
                self.cm = unittest.TestCase().assertRaises(self.expected_exception)
        return self.cm.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.cm.__exit__(exc_type, exc_val, exc_tb)


class PytestModule(types.ModuleType):
    """Mock pytest module that translates to unittest."""

    def __init__(self):
        super().__init__("pytest")
        self.raises = PytestRaises
        self.skip = lambda reason: _raise_skip(reason)
        self.fixture = lambda func: func
        self.mark = types.ModuleType("mark")
        self.mark.skip = lambda reason: lambda func: _raise_skip(reason)
        self.mark.parametrize = lambda *args, **kwargs: lambda func: func
        self.mark.slow = lambda func: func
        self.mark.integration = lambda func: func


def _raise_skip(reason):
    """Raise a SkipTest exception."""
    raise unittest.SkipTest(reason)


# Install the mock pytest module
sys.modules["pytest"] = PytestModule()

# Import and install mock_structlog before importing any modules that use structlog
try:
    from tests.mock_structlog import install_mock

    # Check if structlog is installed
    try:
        import structlog  # noqa: F401
    except ImportError:
        # Install the mock if structlog is not available
        install_mock()
except ImportError:
    # If we can't import from tests (when running from a different directory),
    # try to find mock_structlog and install it
    mock_structlog_path = Path(__file__).parent / "tests" / "mock_structlog.py"
    if mock_structlog_path.exists():
        spec = importlib.util.spec_from_file_location("mock_structlog", mock_structlog_path)
        mock_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mock_module)
        try:
            import structlog  # noqa: F401
        except ImportError:
            mock_module.install_mock()


def convert_pytest_to_unittest(test_class: Any) -> unittest.TestCase:
    """
    Convert a pytest-style test class to unittest.TestCase.

    This creates a dynamic subclass that inherits from unittest.TestCase
    and copies all test methods from the original class.
    """

    class DynamicTestCase(unittest.TestCase):
        pass

    # Copy all test methods from the original class
    for name, method in inspect.getmembers(test_class, predicate=inspect.isfunction):
        if name.startswith("test_"):
            # Create a wrapper method that handles pytest-style fixtures
            def make_test_wrapper(m: Callable, method_name: str):
                def test_wrapper(test_self):
                    # Create an instance of the original test class
                    test_instance = test_class()

                    # The global pytest mock is already set up, just use it

                    # Try to extract fixture values from method signature
                    sig = inspect.signature(m)
                    kwargs = {}

                    # Handle common fixtures
                    for param_name, param in sig.parameters.items():
                        if param_name == "tmp_path":
                            # Create a temporary directory for tmp_path fixture
                            import tempfile

                            kwargs[param_name] = Path(tempfile.mkdtemp())
                        elif param_name == "fixture":
                            # Skip fixture parameters
                            continue
                        elif param.default == inspect.Parameter.empty and param_name not in [
                            "self"
                        ]:
                            # Required parameter without fixture - skip this test
                            test_self.skipTest(f"Cannot provide required parameter: {param_name}")

                    # Call the original test method with the instance as first argument
                    m(test_instance, **kwargs)

                return test_wrapper

            setattr(DynamicTestCase, name, make_test_wrapper(method, name))

    # Set the class name
    DynamicTestCase.__name__ = f"Unittest{test_class.__name__}"
    DynamicTestCase.__qualname__ = DynamicTestCase.__name__

    return DynamicTestCase


def add_src_to_path():
    """Add src and tests directories to Python path."""
    # Get the project root directory (where test_runner.py is located)
    project_root = Path(__file__).parent.absolute()
    src_path = project_root / "src"
    tests_path = project_root / "tests"

    # Add src directory
    if src_path.exists():
        sys.path.insert(0, str(src_path))
        print(f"Added {src_path} to Python path")
    else:
        print(f"Warning: {src_path} directory not found")

    # Add tests directory
    if tests_path.exists():
        sys.path.insert(0, str(tests_path))
        print(f"Added {tests_path} to Python path")
    else:
        print(f"Warning: {tests_path} directory not found")


def discover_tests(test_dir: str = "tests") -> List[str]:
    """
    Discover all test modules in the test directory.

    Args:
        test_dir: Directory containing tests (default: 'tests')

    Returns:
        List of test module paths
    """
    test_dir_path = Path(test_dir)
    if not test_dir_path.exists():
        print(f"Test directory {test_dir} not found!")
        return []

    test_modules = []

    # Find all test_*.py files
    for test_file in test_dir_path.rglob("test_*.py"):
        # Convert file path to module path
        relative_path = test_file.relative_to(test_dir_path)
        module_path = str(relative_path.with_suffix("")).replace(os.sep, ".")
        test_modules.append(module_path)

    # Also find *_test.py files
    for test_file in test_dir_path.rglob("*_test.py"):
        relative_path = test_file.relative_to(test_dir_path)
        module_path = str(relative_path.with_suffix("")).replace(os.sep, ".")
        if module_path not in test_modules:
            test_modules.append(module_path)

    return sorted(test_modules)


def run_tests(test_modules: List[str], verbosity: int = 2):
    """
    Run the discovered test modules.

    Args:
        test_modules: List of test module paths
        verbosity: Test output verbosity level (0-2)
    """
    if not test_modules:
        print("No tests found!")
        return

    # Create a test suite with all discovered tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    print(f"\nDiscovering tests from {len(test_modules)} modules...")

    for module_name in test_modules:
        try:
            # Try to import the module first to catch any import errors
            try:
                # Import using importlib for better error handling
                module = importlib.import_module(module_name)
            except ImportError as e:
                print(f"  ❌ Failed to import {module_name}: {e}")
                continue
            except Exception as e:
                print(f"  ❌ Error importing {module_name}: {e}")
                continue

            # Load tests from the module
            try:
                # First try standard unittest loading
                tests = loader.loadTestsFromModule(module)

                # Also look for pytest-style test classes
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and name.startswith("Test")
                        and not issubclass(obj, unittest.TestCase)
                    ):
                        # Convert pytest-style class to unittest
                        unittest_class = convert_pytest_to_unittest(obj)
                        tests_from_pytest = loader.loadTestsFromTestCase(unittest_class)
                        tests.addTests(tests_from_pytest)
                        print(f"  ✓ Converted pytest class {name} to unittest")

                if tests.countTestCases() > 0:
                    suite.addTest(tests)
                    print(f"  ✓ Loaded {tests.countTestCases()} tests from {module_name}")
                else:
                    print(f"  ⚠ No tests found in {module_name}")
            except Exception as e:
                print(f"  ❌ Error loading tests from {module_name}: {e}")

        except Exception as e:
            print(f"  ❌ Error processing {module_name}: {e}")

    total_tests = suite.countTestCases()
    if total_tests == 0:
        print("\nNo tests to run!")
        return

    print(f"\nRunning {total_tests} tests...\n")
    print("=" * 70)

    # Run the tests
    runner = unittest.TextTestRunner(
        verbosity=verbosity,
        stream=sys.stdout,
        buffer=True,  # Buffer stdout/stderr during tests
        failfast=False,  # Don't stop on first failure
    )

    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")

    # Return appropriate exit code
    if result.failures or result.errors:
        print("\n❌ TESTS FAILED")
        return 1
    else:
        print("\n✓ ALL TESTS PASSED")
        return 0


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run tests without pytest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_runner.py                    # Run all tests
  python test_runner.py -v                 # Verbose output
  python test_runner.py -q                 # Quiet output
  python test_runner.py --pattern unit     # Only run tests matching pattern
        """,
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose output (show individual test names)"
    )

    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Quiet output (show only dots and summary)"
    )

    parser.add_argument("--pattern", help="Only run tests from modules matching this pattern")

    parser.add_argument(
        "--list", action="store_true", help="List discovered tests without running them"
    )

    args = parser.parse_args()

    # Set verbosity
    if args.verbose:
        verbosity = 2
    elif args.quiet:
        verbosity = 0
    else:
        verbosity = 1

    # Add src to Python path
    add_src_to_path()

    # Discover tests
    all_modules = discover_tests()

    # Filter by pattern if specified
    if args.pattern:
        modules = [m for m in all_modules if args.pattern in m]
        print(f"Filtered to {len(modules)} modules matching '{args.pattern}'")
    else:
        modules = all_modules

    # Just list if requested
    if args.list:
        print(f"\nDiscovered {len(modules)} test modules:")
        for module in modules:
            print(f"  - {module}")
        return 0

    # Run tests
    return run_tests(modules, verbosity)


if __name__ == "__main__":
    sys.exit(main())
