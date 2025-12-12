"""
Type checking examples with data classes vs dictionaries

This file demonstrates how data classes enable static type checking,
while dictionaries do not.
"""

from typing import Any, Dict, List, NewType
from src.crawler.models.api_responses import ComplexInfo, TradeInfo
from src.crawler.models.csv_models import ComplexCSVRow


# Example 1: Dictionary - No type checking
def process_dict_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Process dictionary data - prone to errors"""
    # These look correct but mypy cannot verify
    # IDE cannot provide proper autocomplete
    # Typos only caught at runtime

    # Potential typo - mypy cannot catch this!
    lat = data.get("lattitude")  # Should be "latitude"

    # Type error - mypy cannot catch this!
    price = data.get("price") + 1000  # Might be string!

    # Missing field - mypy cannot catch this!
    floors = data["number_of_floors"]  # KeyError at runtime!

    return {
        "latitude": lat,
        "new_price": price,
        "total_floors": floors,
    }


# Example 2: Data Class - Full type checking
def process_dataclass_data(complex: ComplexInfo) -> ComplexCSVRow:
    """Process data class data - type safe"""
    # IDE provides full autocomplete
    # mypy can verify all field accesses
    # Typos caught at type checking time

    # No typo possible - IDE suggests correct field
    _lat = complex.latitude  # Correct spelling enforced by IDE

    # Type safe - mypy ensures proper type
    if complex.trade_info and complex.trade_info.price is not None:
        # mypy knows price is int, not str
        complex.trade_info.price + 1000

    # Safe access with type checking
    _floors = complex.floors or 0  # Proper Optional[int] handling

    # Type-safe conversion
    return ComplexCSVRow.from_complex_info(complex)


# Example 3: Type checking would catch these errors:
def type_checking_examples():
    """Examples of errors mypy would catch"""

    # Error 1: Type mismatch
    # complex: ComplexInfo = "not a complex"  # mypy: error!

    # Error 2: Wrong attribute name
    # complex = ComplexInfo(id="1", name="Test", address="Seoul")
    # lat = complex.lattitude  # mypy: error! No attribute 'lattitude'

    # Error 3: Wrong type assignment
    # complex.build_year = "2020"  # mypy: error! build_year expects Optional[int]

    # Error 4: Unsafe optional access
    # complex = ComplexInfo(id="1", name="Test", address="Seoul")
    # floors = complex.floors + 1  # mypy: error! floors might be None
    # floors = (complex.floors or 0) + 1  # Correct - mypy passes


# Example 4: Function signatures are self-documenting
def example_function_signatures():
    """Compare function signatures"""

    # Dictionary version - unclear what's expected
    def process_data_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """What fields are expected? What types? Who knows!"""
        pass

    # Data class version - clear contracts
    def process_data_class(complex: ComplexInfo) -> ComplexCSVRow:
        """Clear: expects ComplexInfo, returns ComplexCSVRow"""
        pass

    # IDE can show full documentation for ComplexInfo and ComplexCSVRow
    # No need to read implementation to understand the contract


# Example 5: Type-safe collections
def example_type_safe_collections():
    """Collections of data classes vs dictionaries"""

    # List of dictionaries - unclear structure
    [
        {"id": "1", "name": "A", "price": 100},
        {"id": "2", "name": "B", "prcie": 200},  # Typo!
    ]

    # List of data classes - enforced structure
    complex_list: List[ComplexInfo] = [
        ComplexInfo(id="1", name="A", address="Seoul"),
        ComplexInfo(id="2", name="B", address="Busan"),
    ]

    # Type-safe operations
    for complex in complex_list:
        # IDE knows exactly what fields are available
        print(f"{complex.name} is in {complex.address}")
        # No KeyError surprises!


# Example 6: Type aliases for clarity

# Create type aliases for even better documentation
ComplexID = NewType("ComplexID", str)
Price = NewType("Price", int)
Area = NewType("Area", float)


def process_with_type_aliases(complex_id: ComplexID, price: Price, area: Area) -> ComplexCSVRow:
    """Very clear what types are expected"""
    # mypy ensures correct types are passed
    complex = ComplexInfo(
        id=complex_id,
        name="Test",
        address="Seoul",
        trade_info=TradeInfo(type="sale", price=price, exclusive_area=area),
    )
    return ComplexCSVRow.from_complex_info(complex)


if __name__ == "__main__":
    print("Type checking examples")
    print("=" * 50)

    # Demonstrate dictionary issues
    print("\nDictionary processing (error-prone):")
    try:
        bad_data = {
            "id": "123",
            "name": "Test Apartment",
            "lattitude": 37.5,  # Typo!
            "price": "50,000",  # String!
            # Missing "number_of_floors"
        }
        result = process_dict_data(bad_data)
        print(f"Result: {result}")
    except KeyError as e:
        print(f"KeyError at runtime: {e}")
    except TypeError as e:
        print(f"TypeError at runtime: {e}")

    # Demonstrate data class safety
    print("\nData class processing (type-safe):")
    try:
        complex = ComplexInfo(
            id="123",
            name="Test Apartment",
            address="Seoul",
            latitude=37.5,  # Correct field
            trade_info=TradeInfo(
                type="sale",
                price=50000,  # Correct type
                exclusive_area=84.95,
            ),
        )
        result = process_dataclass_data(complex)
        print(f"✓ Success: {result.단지명}")
    except Exception as e:
        print(f"✗ Error: {e}")

    print("\nData classes provide:")
    print("✓ Compile-time type checking")
    print("✓ IDE autocomplete and documentation")
    print("✓ Early error detection")
    print("✓ Self-documenting code")
    print("✓ Type-safe operations")
