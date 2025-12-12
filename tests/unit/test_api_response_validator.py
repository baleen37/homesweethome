"""Tests for API response validator."""

from unittest.mock import patch
from crawler.validators.api_response_validator import (
    APIResponseValidator,
    FieldValidator,
    ValidationResult,
    ValidationReport,
    ValidationSeverity,
    validate_api_response,
    safe_get_nested_value,
    sanitize_api_data,
)


class TestFieldValidator:
    """Test FieldValidator class."""

    def test_validate_required_success(self):
        """Test successful required field validation."""
        result = FieldValidator.validate_required("test_value", "test_field")
        assert result.is_valid is True
        assert result.severity == ValidationSeverity.INFO
        assert "present" in result.message

    def test_validate_required_failure_empty_string(self):
        """Test failed required field validation with empty string."""
        result = FieldValidator.validate_required("", "test_field")
        assert result.is_valid is False
        assert result.severity == ValidationSeverity.ERROR
        assert "missing or empty" in result.message

    def test_validate_required_failure_none(self):
        """Test failed required field validation with None."""
        result = FieldValidator.validate_required(None, "test_field")
        assert result.is_valid is False
        assert result.severity == ValidationSeverity.ERROR
        assert "missing or empty" in result.message

    def test_validate_type_success(self):
        """Test successful type validation."""
        result = FieldValidator.validate_type("test", str, "test_field")
        assert result.is_valid is True
        assert result.severity == ValidationSeverity.INFO

    def test_validate_type_failure(self):
        """Test failed type validation."""
        result = FieldValidator.validate_type("test", int, "test_field")
        assert result.is_valid is False
        assert result.severity == ValidationSeverity.WARNING
        assert "wrong type" in result.message

    def test_validate_range_success(self):
        """Test successful range validation."""
        result = FieldValidator.validate_range(50, 0, 100, "test_field")
        assert result.is_valid is True
        assert result.severity == ValidationSeverity.INFO

    def test_validate_range_failure_out_of_range(self):
        """Test failed range validation - out of range."""
        result = FieldValidator.validate_range(150, 0, 100, "test_field")
        assert result.is_valid is False
        assert result.severity == ValidationSeverity.WARNING
        assert "out of range" in result.message

    def test_validate_range_failure_invalid_number(self):
        """Test failed range validation - invalid number."""
        result = FieldValidator.validate_range("invalid", 0, 100, "test_field")
        assert result.is_valid is False
        assert result.severity == ValidationSeverity.ERROR
        assert "not a valid number" in result.message

    def test_validate_string_length_success(self):
        """Test successful string length validation."""
        result = FieldValidator.validate_string_length("test", 1, 10, "test_field")
        assert result.is_valid is True
        assert result.severity == ValidationSeverity.INFO

    def test_validate_string_length_failure(self):
        """Test failed string length validation."""
        result = FieldValidator.validate_string_length("this is too long", 1, 5, "test_field")
        assert result.is_valid is False
        assert result.severity == ValidationSeverity.WARNING
        assert "length is out of range" in result.message

    def test_validate_pattern_success(self):
        """Test successful pattern validation."""
        result = FieldValidator.validate_pattern("APT_123", r"^APT_\d+$", "test_field")
        assert result.is_valid is True
        assert result.severity == ValidationSeverity.INFO

    def test_validate_pattern_failure(self):
        """Test failed pattern validation."""
        result = FieldValidator.validate_pattern("invalid", r"^APT_\d+$", "test_field")
        assert result.is_valid is False
        assert result.severity == ValidationSeverity.WARNING
        assert "does not match expected pattern" in result.message


class TestValidationReport:
    """Test ValidationReport class."""

    def test_add_result(self):
        """Test adding validation result."""
        report = ValidationReport()
        result = ValidationResult(True, ValidationSeverity.INFO, "test")
        report.add_result(result)
        assert len(report.results) == 1
        assert report.results[0] == result

    def test_has_errors_true(self):
        """Test has_errors returns True when errors exist."""
        report = ValidationReport()
        report.add_result(ValidationResult(False, ValidationSeverity.ERROR, "error"))
        assert report.has_errors() is True

    def test_has_errors_false(self):
        """Test has_errors returns False when no errors exist."""
        report = ValidationReport()
        report.add_result(ValidationResult(False, ValidationSeverity.WARNING, "warning"))
        assert report.has_errors() is False

    def test_has_errors_critical(self):
        """Test has_errors returns True for critical errors."""
        report = ValidationReport()
        report.add_result(ValidationResult(False, ValidationSeverity.CRITICAL, "critical"))
        assert report.has_errors() is True

    def test_get_errors(self):
        """Test getting only error results."""
        report = ValidationReport()
        report.add_result(ValidationResult(False, ValidationSeverity.ERROR, "error"))
        report.add_result(ValidationResult(False, ValidationSeverity.WARNING, "warning"))
        report.add_result(ValidationResult(True, ValidationSeverity.INFO, "info"))

        errors = report.get_errors()
        assert len(errors) == 1
        assert errors[0].severity == ValidationSeverity.ERROR

    def test_get_warnings(self):
        """Test getting only warning results."""
        report = ValidationReport()
        report.add_result(ValidationResult(False, ValidationSeverity.ERROR, "error"))
        report.add_result(ValidationResult(False, ValidationSeverity.WARNING, "warning"))
        report.add_result(ValidationResult(True, ValidationSeverity.INFO, "info"))

        warnings = report.get_warnings()
        assert len(warnings) == 1
        assert warnings[0].severity == ValidationSeverity.WARNING


class TestAPIResponseValidator:
    """Test APIResponseValidator class."""

    def test_init(self):
        """Test validator initialization."""
        validator = APIResponseValidator()
        assert validator.logger is not None
        assert isinstance(validator.report, ValidationReport)

    def test_validate_poi_response_success(self):
        """Test successful POI response validation."""
        validator = APIResponseValidator()
        data = [
            {
                "id": "APT_123",
                "name": "Test Apartment",
                "lat": 37.5,
                "lng": 127.0,
                "address": "Test Address",
            },
            {
                "id": "456",
                "name": "Test Apartment 2",
                "lat": 37.6,
                "lng": 127.1,
                "address": "Test Address 2",
            },
        ]

        report = validator.validate_poi_response(data)
        assert isinstance(report, ValidationReport)
        # Should not have errors for valid data
        critical_errors = [
            e for e in report.get_errors() if e.severity == ValidationSeverity.CRITICAL
        ]
        assert len(critical_errors) == 0

    def test_validate_poi_response_with_data_wrapper(self):
        """Test POI response validation with data wrapper."""
        validator = APIResponseValidator()
        data = {"data": [{"id": "APT_123", "name": "Test Apartment", "lat": 37.5, "lng": 127.0}]}

        report = validator.validate_poi_response(data)
        assert isinstance(report, ValidationReport)

    def test_validate_poi_response_null(self):
        """Test POI response validation with null data."""
        validator = APIResponseValidator()
        report = validator.validate_poi_response(None)
        assert report.has_errors() is True
        critical_errors = report.get_errors()
        assert len(critical_errors) > 0
        assert any("null" in e.message for e in critical_errors)

    def test_validate_poi_response_invalid_structure(self):
        """Test POI response validation with invalid structure."""
        validator = APIResponseValidator()
        report = validator.validate_poi_response("invalid")
        assert report.has_errors() is True

    def test_validate_poi_response_missing_fields(self):
        """Test POI response validation with missing required fields."""
        validator = APIResponseValidator()
        data = [
            {
                "name": "Test Apartment",
                # Missing id, lat, lng
            }
        ]

        report = validator.validate_poi_response(data)
        # Should have errors for missing required fields
        errors = report.get_errors()
        assert len(errors) >= 3  # id, lat, lng are required

    def test_validate_poi_response_invalid_coordinates(self):
        """Test POI response validation with invalid coordinates."""
        validator = APIResponseValidator()
        data = [
            {
                "id": "APT_123",
                "name": "Test Apartment",
                "lat": 91.0,  # Invalid latitude
                "lng": 127.0,
            }
        ]

        report = validator.validate_poi_response(data)
        # Should have warnings for invalid coordinates
        warnings = report.get_warnings()
        assert len(warnings) > 0

    def test_validate_complex_response_success(self):
        """Test successful complex response validation."""
        validator = APIResponseValidator()
        data = {
            "id": "123",
            "name": "Test Complex",
            "build_year": 2020,
            "households": 100,
            "latitude": 37.5,
            "longitude": 127.0,
        }

        report = validator.validate_complex_response(data)
        assert isinstance(report, ValidationReport)

    def test_validate_transaction_response_success(self):
        """Test successful transaction response validation."""
        validator = APIResponseValidator()
        data = {
            "data": {
                "shortTermReport": [
                    {
                        "date": "2025-01-31",
                        "minPrice": 300000,
                        "maxPrice": 400000,
                        "averagePrice": 350000,
                    }
                ]
            }
        }

        report = validator.validate_transaction_response(data)
        assert isinstance(report, ValidationReport)


class TestUtilityFunctions:
    """Test utility functions."""

    def test_validate_api_response_poi(self):
        """Test validate_api_response with POI type."""
        data = [{"id": "APT_123", "name": "Test", "lat": 37.5, "lng": 127.0}]
        report = validate_api_response(data, "poi")
        assert isinstance(report, ValidationReport)

    def test_validate_api_response_complex(self):
        """Test validate_api_response with complex type."""
        data = {"id": "123", "name": "Test"}
        report = validate_api_response(data, "complex")
        assert isinstance(report, ValidationReport)

    def test_validate_api_response_transaction(self):
        """Test validate_api_response with transaction type."""
        data = {"data": {"shortTermReport": []}}
        report = validate_api_response(data, "transaction")
        assert isinstance(report, ValidationReport)

    def test_validate_api_response_unknown(self):
        """Test validate_api_response with unknown type."""
        data = {"test": "value"}
        report = validate_api_response(data, "unknown")
        assert isinstance(report, ValidationReport)

    def test_safe_get_nested_value_success(self):
        """Test safe_get_nested_value successful access."""
        data = {"data": {"items": [{"name": "test"}]}}
        value = safe_get_nested_value(data, "data.items.0.name")
        assert value == "test"

    def test_safe_get_nested_value_default(self):
        """Test safe_get_nested_value with default value."""
        data = {"data": {"items": []}}
        value = safe_get_nested_value(data, "data.items.0.name", "default")
        assert value == "default"

    def test_safe_get_nested_value_invalid_path(self):
        """Test safe_get_nested_value with invalid path."""
        data = {"data": {"items": []}}
        value = safe_get_nested_value(data, "invalid.path", "default")
        assert value == "default"

    def test_sanitize_api_data_none(self):
        """Test sanitize_api_data with None."""
        result = sanitize_api_data(None, "test")
        assert result is None

    def test_sanitize_api_data_dict(self):
        """Test sanitize_api_data with dictionary."""
        data = {"name": " test ", "value": None, "keep": "value"}
        result = sanitize_api_data(data, "test")
        assert result["name"] == "test"  # Stripped
        assert "value" not in result  # None removed
        assert result["keep"] == "value"  # Preserved

    def test_sanitize_api_data_list(self):
        """Test sanitize_api_data with list."""
        data = [" test ", None, "value"]
        result = sanitize_api_data(data, "test")
        assert result[0] == "test"  # Stripped
        assert result[1] is None  # None preserved in list
        assert result[2] == "value"

    def test_sanitize_api_data_string(self):
        """Test sanitize_api_data with string."""
        data = " test string "
        result = sanitize_api_data(data, "test")
        assert result == "test string"  # Stripped

    @patch("unicodedata.normalize")
    def test_sanitize_api_data_unicode_error(self, mock_normalize):
        """Test sanitize_api_data handles unicode normalization error."""
        mock_normalize.side_effect = Exception("Unicode error")
        data = "test string"
        result = sanitize_api_data(data, "test")
        assert result == data  # Should return original on error
