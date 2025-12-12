"""Test cases demonstrating dictionary-based data handling problems

These tests show the issues with using raw dictionaries for API responses
and CSV data, motivating the need for data classes.
"""

# Use unittest instead of pytest if pytest is not available
try:
    import pytest
except ImportError:
    pytest = None
from typing import Any, Dict


def test_dictionary_typo_problems():
    """Demonstrate how typos in dictionary keys cause silent data loss"""

    # Simulate API response data
    api_data: Dict[str, Any] = {
        "id": 12345,
        "name": "테스트 아파트",
        "address": "서울시 강남구 테스트동 123-45",
        "latitude": 37.1234,
        "longitude": 127.5678,
        "build_year": 2020,
        "households": 100,
    }

    # Problem 1: Typo in key name causes silent data loss
    result = {
        "complex_id": api_data.get("id"),  # Correct
        "complex_name": api_data.get("name"),  # Correct
        "address": api_data.get("address"),  # Correct
        "lat": api_data.get("latitude"),  # Correct
        "lng": api_data.get("longtitude"),  # TYPO! Should be "longitude"
        "build_year": api_data.get("buildYear"),  # TYPO! Should be "build_year"
    }

    # The typo silently produces None - no error raised!
    assert result["lat"] == 37.1234  # Passes
    assert result["lng"] is None  # This should fail but silently passes!
    assert result["build_year"] is None  # This should fail but silently passes!

    # This data would be written to CSV with missing values


def test_dictionary_inconsistent_structure():
    """Demonstrate inconsistent data structure with dictionaries"""

    # Two API responses with different structures
    api_response_1 = {
        "data": {"id": 123, "apt_name": "아파트 A", "trade_info": {"price": 50000, "type": "sale"}}
    }

    api_response_2 = {
        "data": {
            "complex_id": 456,  # Different key name!
            "name": "아파트 B",  # Different key name!
            "recent_trade": {  # Different key name!
                "deal_price": 30000,  # Different key name!
                "trade_type": "jeonse",  # Different key name!
            },
        }
    }

    def extract_price(data: Dict[str, Any]) -> int:
        # This function has to handle multiple possible key names
        trade = data.get("trade_info") or data.get("recent_trade", {})
        price = trade.get("price") or trade.get("deal_price", 0)
        return int(price)

    # Works but is fragile and hard to maintain
    assert extract_price(api_response_1["data"]) == 50000
    assert extract_price(api_response_2["data"]) == 30000


def test_dictionary_no_type_validation():
    """Demonstrate lack of type validation with dictionaries"""

    # API returns unexpected data types
    problematic_data = {
        "id": "not-a-number",  # Should be int
        "price": "50,000",  # String with comma
        "area": None,  # None instead of float
        "floors": "high-rise",  # String instead of int
    }

    def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
        # No type checking - runtime errors will occur later
        return {
            "id": data["id"] * 2,  # TypeError at runtime!
            "price": data["price"] + 10000,  # TypeError!
            "area": data["area"] * 1.1,  # TypeError!
            "floors": data["floors"] + 1,  # TypeError!
        }

    # These will fail at runtime, not at development time
    try:
        process_data(problematic_data)
        assert False, "Expected TypeError"
    except TypeError:
        pass  # Expected


def test_dictionary_missing_required_fields():
    """Demonstrate missing required fields with dictionaries"""

    # Incomplete API response
    incomplete_data = {
        "id": 123,
        # Missing 'name' field
        "address": "서울시 어딘가",
        # Missing 'coordinates' field
        "price": 50000,
    }

    def create_csv_row(data: Dict[str, Any]) -> Dict[str, Any]:
        # No validation of required fields
        return {
            "ID": data["id"],
            "Name": data["name"],  # KeyError at runtime!
            "Address": data["address"],
            "Latitude": data["coordinates"]["lat"],  # KeyError at runtime!
            "Longitude": data["coordinates"]["lng"],  # KeyError at runtime!
            "Price": data["price"],
        }

    try:
        create_csv_row(incomplete_data)
        assert False, "Expected KeyError"
    except KeyError:
        pass  # Expected


def test_dictionary_no_autocomplete():
    """Demonstrate lack of IDE autocomplete with dictionaries"""

    # With dictionaries, IDE can't suggest field names
    api_response = {
        "complex_id": 123,
        "complex_name": "테스트 단지",
        "address": "서울시 강남구",
        # ... many more fields
    }

    def process_complex(data: Dict[str, Any]) -> Dict[str, Any]:
        # Developer has to remember all field names
        # No autocomplete, no type hints
        return {
            # Did I spell "address" correctly?
            # What other fields are available?
            # What are the expected types?
            "id": data["compllex_id"],  # Typo not caught by IDE
            "name": data["complex_name"],
            "addr": data["address"],  # Inconsistent naming
        }

    # These kinds of errors are only caught at runtime
    result = process_complex(api_response)
    assert result["id"] is None  # Because of the typo


def test_csv_field_order_issues():
    """Demonstrate CSV field order issues with dictionaries"""

    data = [
        {"id": 1, "name": "A", "price": 100},
        {"price": 200, "id": 2, "name": "B"},  # Different order!
        {"name": "C", "id": 3, "extra": "field", "price": 300},  # Extra field!
    ]

    # CSV will have columns in arbitrary order
    # Might miss fields or have inconsistent column order
    import csv
    import io

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "name", "price"])
    writer.writeheader()

    for row in data:
        writer.writerow(row)

    csv_content = output.getvalue()
    lines = csv_content.strip().split("\n")

    # The CSV structure is inconsistent and error-prone
    assert "id,name,price" in lines[0]
    assert len(lines) == 4  # header + 3 data rows


if __name__ == "__main__":
    """Run all tests"""
    print("Running dictionary problems test suite...")
    print()

    test_dictionary_typo_problems()
    print("✓ test_dictionary_typo_problems")

    test_dictionary_inconsistent_structure()
    print("✓ test_dictionary_inconsistent_structure")

    test_dictionary_no_type_validation()
    print("✓ test_dictionary_no_type_validation")

    test_dictionary_missing_required_fields()
    print("✓ test_dictionary_missing_required_fields")

    test_dictionary_no_autocomplete()
    print("✓ test_dictionary_no_autocomplete")

    test_csv_field_order_issues()
    print("✓ test_csv_field_order_issues")

    print()
    print("All tests passed! Dictionary problems demonstrated.")
