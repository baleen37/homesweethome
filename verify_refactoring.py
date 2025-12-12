#!/usr/bin/env python
"""Verify refactoring success"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_imports():
    """Test that imports work correctly"""
    print("Testing imports...")

    # Test importing from base_api_client
    try:
        from crawler.api.base_api_client import (  # noqa: F401
            BaseAPIClient as _BaseAPIClient,
            APIResponse as _APIResponse,
            APIResponseCache as _APIResponseCache,
            CacheEntry as _CacheEntry,
        )

        print("✓ base_api_client imports work")
    except ImportError as e:
        print(f"✗ base_api_client import failed: {e}")
        return False

    # Test importing from hogangnono_client
    try:
        from crawler.api.hogangnono_client import (  # noqa: F401
            HogangnonoAPIClient as _HogangnonoAPIClient,
            SearchParams as _SearchParams,
        )

        print("✓ hogangnono_client imports work")
    except ImportError as e:
        print(f"✗ hogangnono_client import failed: {e}")
        return False

    # Test that refactored file doesn't exist
    refactored_path = Path(__file__).parent / "src/crawler/api/hogangnono_client_refactored.py"
    if not refactored_path.exists():
        print("✓ hogangnono_client_refactored.py has been removed")
    else:
        print("✗ hogangnono_client_refactored.py still exists")
        return False

    return True


def test_inheritance():
    """Test that HogangnonoAPIClient properly inherits from BaseAPIClient"""
    print("\nTesting inheritance...")

    try:
        from crawler.api.base_api_client import BaseAPIClient
        from crawler.api.hogangnono_client import HogangnonoAPIClient

        # Check inheritance
        if issubclass(HogangnonoAPIClient, BaseAPIClient):
            print("✓ HogangnonoAPIClient inherits from BaseAPIClient")
        else:
            print("✗ HogangnonoAPIClient does not inherit from BaseAPIClient")
            return False

        # Check that required method exists
        if hasattr(HogangnonoAPIClient, "get_required_headers"):
            print("✓ get_required_headers method exists")
        else:
            print("✗ get_required_headers method missing")
            return False

        return True
    except Exception as e:
        print(f"✗ Inheritance test failed: {e}")
        return False


def test_search_params():
    """Test SearchParams class"""
    print("\nTesting SearchParams...")

    try:
        from crawler.api.hogangnono_client import SearchParams

        # Test valid params
        params = SearchParams(level=10, tradeType=1, aptType=0)
        assert params.level == 10
        assert params.tradeType == 1
        assert params.aptType == 0
        print("✓ SearchParams initialization works")

        # Test bbox conversion
        params = SearchParams(bbox=(126.0, 37.0, 127.0, 38.0))
        assert params.startX == 126.0
        assert params.endX == 127.0
        assert params.startY == 37.0
        assert params.endY == 38.0
        print("✓ SearchParams bbox conversion works")

        # Test to_dict
        params_dict = params.to_dict()
        assert "startX" in params_dict
        assert "level" in params_dict
        print("✓ SearchParams.to_dict() works")

        return True
    except Exception as e:
        print(f"✗ SearchParams test failed: {e}")
        return False


def check_for_duplicates():
    """Check for duplicate class definitions"""
    print("\nChecking for duplicates...")

    # Read hogangnono_client.py
    client_path = Path(__file__).parent / "src/crawler/api/hogangnono_client.py"
    content = client_path.read_text()

    # Check for duplicate classes
    duplicates = []

    if content.count("class APIResponse") > 0:
        duplicates.append("APIResponse")
    if content.count("class APIResponseCache") > 0:
        duplicates.append("APIResponseCache")
    if content.count("class CacheEntry") > 0:
        duplicates.append("CacheEntry")

    if duplicates:
        print(f"✗ Found duplicate classes: {', '.join(duplicates)}")
        return False
    else:
        print("✓ No duplicate classes found in hogangnono_client.py")

    # Check for proper imports
    if "from .base_api_client import" in content:
        print("✓ Proper import from base_api_client found")
    else:
        print("✗ Missing import from base_api_client")
        return False

    return True


def main():
    """Run all verification tests"""
    print("=" * 50)
    print("REFACTORING VERIFICATION")
    print("=" * 50)

    all_passed = True

    all_passed &= test_imports()
    all_passed &= test_inheritance()
    all_passed &= test_search_params()
    all_passed &= check_for_duplicates()

    print("\n" + "=" * 50)
    if all_passed:
        print("✓ ALL TESTS PASSED - Refactoring successful!")
    else:
        print("✗ Some tests failed - Please check the issues above")
    print("=" * 50)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
