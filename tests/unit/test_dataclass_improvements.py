"""Test cases demonstrating data class improvements

These tests show how data classes solve the problems demonstrated
in test_dictionary_problems.py
"""

import sys

sys.path.append("/Users/jito.hello/dev/wooto/homesweethome/src")

from crawler.models.api_responses import (
    ComplexInfo,
    POIInfo,
    TradeInfo,
    complex_info_from_api_response,
)
from crawler.models.csv_models import (
    ComplexCSVRow,
    TransactionCSVRow,
)
from crawler.models.validators import (
    ValidationError,
    validate_coordinates,
    validate_price,
    validate_year,
)


def test_dataclass_type_safety():
    """Demonstrate type safety with data classes"""
    # Data classes provide compile-time type checking
    try:
        # This will fail type checking with mypy
        complex_info = ComplexInfo(
            id=123,
            name="테스트 아파트",
            address="서울시 강남구 테스트동 123-45",
            latitude=37.1234,
            longitude=127.5678,  # Correct key name
            build_year=2020,  # Correct key name
            households=100,
        )
        print(f"✓ ComplexInfo created: {complex_info.name}")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Validation errors are caught early
    try:
        # This will raise ValidationError
        ComplexInfo(
            id=123,
            name="테스트 아파트",
            address="서울시 강남구 테스트동 123-45",
            latitude=91.0,  # Invalid latitude (> 90)
            longitude=127.5678,
        )
    except ValidationError as e:
        print(f"✓ Validation caught error: {e}")


def test_dataclass_consistent_structure():
    """Demonstrate consistent data structure with data classes"""
    # Different API responses produce the same data class
    api_response_1 = {
        "id": 123,
        "apt_name": "아파트 A",
        "address": "서울시 강남구 테스트동",
        "trade": {"price": 50000, "type": "sale"},
    }

    api_response_2 = {
        "complex_id": "456",  # Different key name
        "name": "아파트 B",  # Different key name
        "address": "서울시 강남구 테스트동",
        "recent_trade": {  # Different key name
            "deal_price": 30000,  # Different key name
            "trade_type": "jeonse",  # Different key name
        },
    }

    # Factory function handles different field names
    complex1 = complex_info_from_api_response(api_response_1)
    complex2 = complex_info_from_api_response(api_response_2)

    # Both have the same structure
    assert isinstance(complex1, ComplexInfo)
    assert isinstance(complex2, ComplexInfo)

    print(f"✓ Complex 1: {complex1.name}")
    print(f"✓ Complex 2: {complex2.name}")


def test_dataclass_automatic_validation():
    """Demonstrate automatic validation with data classes"""
    # Invalid coordinates
    try:
        validate_coordinates(91.0, 0.0)  # Invalid latitude
    except ValidationError as e:
        print(f"✓ Coordinate validation: {e}")

    # Invalid price format
    try:
        validate_price("50,0a0")  # Invalid format
    except ValidationError as e:
        print(f"✓ Price validation: {e}")

    # Invalid year
    try:
        validate_year(1799)  # Too early
    except ValidationError as e:
        print(f"✓ Year validation: {e}")


def test_dataclass_csv_generation():
    """Demonstrate consistent CSV generation with data classes"""
    # Create a complex info
    complex_info = ComplexInfo(
        id="123",
        name="테스트 단지",
        address="서울시 강남구 테스트동",
        latitude=37.1234,
        longitude=127.5678,
        build_year=2020,
        households=100,
        floors=20,
    )

    # Convert to CSV row
    csv_row = ComplexCSVRow.from_complex_info(complex_info)

    # Get field names - always consistent!
    fieldnames = ComplexCSVRow.get_fieldnames()
    print(f"✓ CSV fieldnames: {fieldnames}")

    # Convert to dict - always same structure
    csv_dict = csv_row.to_dict()
    print(f"✓ CSV data: {csv_dict}")

    # No missing fields, no extra fields
    assert all(field in csv_dict for field in fieldnames)


def test_dataclass_ide_support():
    """Demonstrate IDE autocomplete support with data classes"""
    # When you type `complex_info.`, IDE shows all available fields
    complex_info = ComplexInfo(
        id="123",
        name="테스트",
        address="서울시",
    )

    # No typos possible - IDE autocomplete helps
    # complex_info.lattitude  # Would be flagged as error
    # complex_info.latitude    # Correct - IDE suggests this

    # All fields are documented with types
    print(f"✓ ID: {complex_info.id}")  # str
    print(f"✓ Name: {complex_info.name}")  # str
    print(f"✓ Latitude: {complex_info.latitude}")  # Optional[float]


def test_dataclass_nested_structures():
    """Demonstrate handling nested structures with data classes"""
    # Complex with trade information
    complex_data = {
        "id": "123",
        "name": "테스트 아파트",
        "address": "서울시 강남구",
        "trade": {
            "type": "sale",
            "price": 50000,
            "exclusive_area": 84.95,
            "floor": "5층",
            "date": "2024-01-15",
        },
    }

    complex_info = complex_info_from_api_response(complex_data)

    # Access nested data safely
    if complex_info.trade_info:
        print(f"✓ Trade type: {complex_info.trade_info.trade_type}")
        print(f"✓ Price: {complex_info.trade_info.price}")
        print(f"✓ Area: {complex_info.trade_info.exclusive_area} m²")

        # Generate transaction CSV rows
        transaction_rows = TransactionCSVRow.from_complex_info(complex_info)
        print(f"✓ Generated {len(transaction_rows)} transaction rows")


# New failing tests for data validation issues
def test_complex_info_validation_invalid_coordinates_should_fail():
    """This test should fail - invalid coordinates should be rejected"""
    # This should raise a validation error but currently doesn't
    try:
        ComplexInfo(
            id="test123",
            name="Test Apartment",
            address="서울시 강남구 테스트동",
            latitude=91.0,  # Invalid latitude (> 90)
            longitude=127.0,
        )
        print("✗ FAIL: Invalid coordinates were accepted")
        return False
    except (ValueError, ValidationError) as e:
        if "latitude" in str(e):
            print("✓ PASS: Invalid coordinates were rejected")
            return True
        else:
            print(f"✗ FAIL: Wrong error: {e}")
            return False


def test_trade_info_negative_price_should_fail():
    """This test should fail - negative prices should be rejected"""
    # This should raise a validation error but currently doesn't
    try:
        TradeInfo(
            trade_type="sale",
            price=-1000000,  # Negative price
        )
        print("✗ FAIL: Negative price was accepted")
        return False
    except (ValueError, ValidationError) as e:
        if "price" in str(e):
            print("✓ PASS: Negative price was rejected")
            return True
        else:
            print(f"✗ FAIL: Wrong error: {e}")
            return False


def test_poi_info_invalid_apartment_id_detection():
    """Test that subway station IDs are not valid apartments"""
    # Subway station ID should be detected as invalid apartment
    subway_poi = POIInfo(
        id="bi03",  # Subway station pattern
        name="테스트역",
        lat=37.5,
        lng=127.0,
        category=1,
    )

    # This should pass - it's a subway station
    assert subway_poi.is_transit(), "Should be identified as transit"
    assert not subway_poi.is_apartment(), "Should not be identified as apartment"
    assert not subway_poi.is_valid_apartment_id(), "Should not be valid apartment ID"
    print("✓ PASS: Subway station correctly identified as non-apartment")
    return True


def test_missing_required_fields_should_fail():
    """Missing required fields should cause errors"""
    # Missing required name field - should fail
    try:
        complex_info_from_api_response(
            {
                "id": "test123",
                # "name" is missing - this should fail
                "address": "서울시 강남구 테스트동",
            }
        )
        print("✗ FAIL: Missing required field was accepted")
        return False
    except (KeyError, ValueError, ValidationError):
        print("✓ PASS: Missing required field caused error")
        return True
    except Exception as e:
        print(f"? UNKNOWN: Got different error: {e}")
        return False


def test_data_immutability_should_fail():
    """Dataclass instances should be immutable"""
    complex_info = ComplexInfo(
        id="test123", name="Test Apartment", address="서울시 강남구 테스트동"
    )

    # Attempting to modify should raise FrozenInstanceError
    try:
        complex_info.name = "Modified Name"
        print("✗ FAIL: Dataclass was mutable")
        return False
    except Exception as e:
        if "FrozenInstanceError" in str(type(e)) or "cannot assign to field" in str(e):
            print("✓ PASS: Dataclass is immutable")
            return True
        else:
            print(f"? UNKNOWN: Got different error: {e}")
            return False


def test_invalid_build_year_should_fail():
    """Future or invalid build years should be rejected"""
    try:
        ComplexInfo(
            id="test123",
            name="Test Apartment",
            address="서울시 강남구 테스트동",
            build_year=2050,  # Future year
        )
        print("✗ FAIL: Future build year was accepted")
        return False
    except (ValueError, ValidationError) as e:
        if "year" in str(e):
            print("✓ PASS: Future build year was rejected")
            return True
        else:
            print(f"✗ FAIL: Wrong error: {e}")
            return False


def test_csv_row_consistency():
    """CSV rows should have consistent field structure"""
    # Test with minimal data
    csv_row = ComplexCSVRow(단지ID="test123", 단지명="Test Apartment")

    # All fields should be present even with minimal data
    dict_data = csv_row.to_dict()
    expected_fields = ComplexCSVRow.get_fieldnames()

    # No missing fields
    for field in expected_fields:
        if field not in dict_data:
            print(f"✗ FAIL: Missing field: {field}")
            return False

    print("✓ PASS: All fields present in CSV row")
    return True


def run_failing_tests():
    """Run all failing tests to demonstrate current issues"""
    print("Running failing tests to demonstrate data validation issues...")
    print()

    results = []
    results.append(test_complex_info_validation_invalid_coordinates_should_fail())
    print()
    results.append(test_trade_info_negative_price_should_fail())
    print()
    results.append(test_poi_info_invalid_apartment_id_detection())
    print()
    results.append(test_missing_required_fields_should_fail())
    print()
    results.append(test_data_immutability_should_fail())
    print()
    results.append(test_invalid_build_year_should_fail())
    print()
    results.append(test_csv_row_consistency())
    print()

    failed_count = sum(1 for r in results if not r)
    passed_count = len(results) - failed_count

    print(f"Results: {passed_count} passed, {failed_count} failed")
    if failed_count > 0:
        print("Some tests failed - data validation needs improvement!")
    else:
        print("All tests passed - data validation is working correctly!")

    return failed_count == 0


if __name__ == "__main__":
    """Run all data class improvement tests"""
    print("Running data class improvements test suite...")
    print()

    test_dataclass_type_safety()
    print()

    test_dataclass_consistent_structure()
    print()

    test_dataclass_automatic_validation()
    print()

    test_dataclass_csv_generation()
    print()

    test_dataclass_ide_support()
    print()

    test_dataclass_nested_structures()
    print()

    print("=" * 50)
    print()

    # Run failing tests to demonstrate issues
    success = run_failing_tests()

    if success:
        print("\n✓ All validation tests passed!")
    else:
        print("\n✗ Some validation tests failed - improvements needed!")
