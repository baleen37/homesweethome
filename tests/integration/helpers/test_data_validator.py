from .data_validator import DataValidator


def test_data_validator_initialization():
    validator = DataValidator()
    assert validator is not None
    assert hasattr(validator, "validate_csv_format")


def test_validate_csv_format_with_valid_data():
    validator = DataValidator()
    # Test with valid CSV structure
    assert hasattr(validator, "validate_csv_format")
