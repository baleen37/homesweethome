"""Unit tests for CSV validation functionality"""

import tempfile
import unittest
from pathlib import Path

from crawler.validators.csv_validator import (
    CSVValidator,
    FieldDefinition,
    DataType,
    ValidationStatus,
    create_complexes_validator,
    create_transactions_validator,
)
from crawler.writers import HogangnonoCSVWriter


class TestFieldDefinition(unittest.TestCase):
    """Test FieldDefinition dataclass"""

    def test_field_definition_creation(self):
        """Test creating a field definition"""
        field = FieldDefinition(
            name="test_field",
            data_type=DataType.STRING,
            required=True,
            min_length=1,
            max_length=100,
        )
        self.assertEqual(field.name, "test_field")
        self.assertEqual(field.data_type, DataType.STRING)
        self.assertTrue(field.required)
        self.assertEqual(field.min_length, 1)
        self.assertEqual(field.max_length, 100)

    def test_field_definition_optional_params(self):
        """Test field definition with optional parameters"""
        field = FieldDefinition(name="optional_field", data_type=DataType.INTEGER, required=False)
        self.assertFalse(field.required)
        self.assertIsNone(field.min_length)
        self.assertIsNone(field.max_value)


class TestCSVValidator(unittest.TestCase):
    """Test CSVValidator class"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_fields = [
            FieldDefinition("id", DataType.STRING, required=True, min_length=1),
            FieldDefinition("name", DataType.STRING, required=True, max_length=50),
            FieldDefinition("age", DataType.INTEGER, required=False, min_value=0, max_value=150),
            FieldDefinition("email", DataType.EMAIL, required=False),
            FieldDefinition("active", DataType.BOOLEAN, required=True),
        ]
        self.validator = CSVValidator(self.test_fields)

    def test_validate_row_success(self):
        """Test successful row validation"""
        row = {
            "id": "123",
            "name": "Test User",
            "age": "30",
            "email": "test@example.com",
            "active": "true",
        }
        result = self.validator.validate_row(row, 1)
        self.assertEqual(result.status, ValidationStatus.PASSED)
        self.assertEqual(result.valid_rows, 1)
        self.assertEqual(len(result.errors), 0)

    def test_validate_row_missing_required(self):
        """Test validation failure for missing required fields"""
        row = {"name": "Test User", "age": "30"}
        result = self.validator.validate_row(row, 1)
        self.assertEqual(result.status, ValidationStatus.FAILED)
        self.assertEqual(result.valid_rows, 0)
        self.assertGreater(len(result.errors), 0)

        # Check for specific error
        error_messages = [e.error_message for e in result.errors]
        self.assertTrue(any("id" in msg and "missing" in msg.lower() for msg in error_messages))
        self.assertTrue(any("active" in msg and "missing" in msg.lower() for msg in error_messages))

    def test_validate_row_invalid_type(self):
        """Test validation failure for invalid data types"""
        row = {"id": "123", "name": "Test User", "age": "not_a_number", "active": "maybe"}
        result = self.validator.validate_row(row, 1)
        self.assertEqual(result.status, ValidationStatus.FAILED)

        # Check for type errors
        error_messages = [e.error_message for e in result.errors]
        self.assertTrue(
            any("age" in msg and "not a valid integer" in msg for msg in error_messages)
        )
        self.assertTrue(
            any("active" in msg and "not a valid boolean" in msg for msg in error_messages)
        )

    def test_validate_row_out_of_range(self):
        """Test validation failure for out of range values"""
        row = {
            "id": "123",
            "name": "Test User",
            "age": "200",  # Above max_value of 150
            "active": "true",
        }
        result = self.validator.validate_row(row, 1)
        self.assertEqual(result.status, ValidationStatus.FAILED)

        # Check for range error
        error_messages = [e.error_message for e in result.errors]
        self.assertTrue(any("age" in msg and "above maximum" in msg for msg in error_messages))

    def test_validate_row_invalid_email(self):
        """Test validation failure for invalid email format"""
        row = {
            "id": "123",
            "name": "Test User",
            "age": "30",
            "email": "invalid_email",
            "active": "true",
        }
        result = self.validator.validate_row(row, 1)
        self.assertEqual(result.status, ValidationStatus.PASSED)  # Email is optional

        # Test with required email
        required_email_fields = [
            FieldDefinition("id", DataType.STRING, required=True),
            FieldDefinition("email", DataType.EMAIL, required=True),
        ]
        validator_with_email = CSVValidator(required_email_fields)

        row = {"id": "123", "email": "invalid_email"}
        result = validator_with_email.validate_row(row, 1)
        self.assertEqual(result.status, ValidationStatus.FAILED)
        error_messages = [e.error_message for e in result.errors]
        self.assertTrue(
            any("email" in msg and "not a valid email" in msg for msg in error_messages)
        )

    def test_validate_file_success(self):
        """Test successful file validation"""
        # Create a temporary CSV file
        csv_content = """id,name,age,email,active
1,John Doe,30,john@example.com,true
2,Jane Smith,25,jane@example.com,false
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            temp_path = Path(f.name)

        try:
            result = self.validator.validate_file(temp_path)
            self.assertEqual(result.status, ValidationStatus.PASSED)
            self.assertEqual(result.total_rows, 2)
            self.assertEqual(result.valid_rows, 2)
            self.assertEqual(len(result.errors), 0)
        finally:
            temp_path.unlink()

    def test_validate_file_missing_headers(self):
        """Test file validation with missing headers"""
        # Create CSV with missing required headers
        csv_content = """name,age
John Doe,30
Jane Smith,25
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            temp_path = Path(f.name)

        try:
            result = self.validator.validate_file(temp_path)
            self.assertEqual(result.status, ValidationStatus.FAILED)
            self.assertIn("id", result.missing_headers)
            self.assertIn("active", result.missing_headers)
        finally:
            temp_path.unlink()

    def test_validate_file_extra_headers(self):
        """Test file validation with extra headers"""
        # Create CSV with extra headers
        csv_content = """id,name,age,email,active,extra_field1,extra_field2
1,John Doe,30,john@example.com,true,extra1,extra2
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            temp_path = Path(f.name)

        try:
            result = self.validator.validate_file(temp_path)
            self.assertEqual(result.status, ValidationStatus.PASSED)  # Extra headers are warnings
            self.assertIn("extra_field1", result.extra_headers)
            self.assertIn("extra_field2", result.extra_headers)
        finally:
            temp_path.unlink()


class TestComplexesValidator(unittest.TestCase):
    """Test complexes CSV validator"""

    def setUp(self):
        """Set up test fixtures"""
        self.validator = create_complexes_validator()

    def test_valid_complexes_data(self):
        """Test validation of valid complexes data"""
        row = {
            "complex_id": "APT001",
            "complex_name": "테스트 아파트",
            "address": "서울시 강남구 테스트동 123-45",
            "latitude": "37.5172",
            "longitude": "127.0473",
            "build_year": "2020",
            "households": "500",
            "floors": "20",
            "gu_code": "11680",
            "dong_code": "11750101",
            "real_estate_type": "아파트",
            "total_dong_count": "5",
            "min_area": "33.0",
            "max_area": "84.9",
            "pyeong_types": "33평, 59평",
            "deal_count": "10",
            "lease_count": "5",
            "rent_count": "2",
            "fetched_at": "2024-01-15 10:30:00",
        }
        result = self.validator.validate_row(row, 1)
        self.assertEqual(result.status, ValidationStatus.PASSED)

    def test_invalid_complexes_data(self):
        """Test validation of invalid complexes data"""
        row = {
            "complex_id": "",  # Empty required field
            "complex_name": "테스트 아파트",
            "address": "서울시 강남구",
            "latitude": "200.0",  # Invalid latitude
            "longitude": "300.0",  # Invalid longitude
            "build_year": "1800",  # Too old
            "households": "-1",  # Negative value
            "floors": "0",  # Invalid floor count
            "gu_code": "12",  # Invalid format
            "dong_code": "345",  # Invalid format
            "real_estate_type": "주택",  # Invalid type
            "fetched_at": "2024/01/15",  # Invalid date format
        }
        result = self.validator.validate_row(row, 1)
        self.assertEqual(result.status, ValidationStatus.FAILED)
        self.assertGreater(len(result.errors), 0)


class TestTransactionsValidator(unittest.TestCase):
    """Test transactions CSV validator"""

    def setUp(self):
        """Set up test fixtures"""
        self.validator = create_transactions_validator()

    def test_valid_transactions_data(self):
        """Test validation of valid transactions data"""
        row = {
            "complex_id": "APT001",
            "complex_name": "테스트 아파트",
            "pyeong_type_number": "33",
            "pyeong_name": "33평형",
            "trade_type": "매매",
            "trade_type_name": "일반거래",
            "trade_date": "2024-01-15",
            "trade_year": "2024",
            "floor": "5",
            "deal_price": "100000",
            "deposit": "",
            "monthly_rent": "",
            "trade_category": "일반거래",
            "is_delete": "false",
            "is_renew": "false",
        }
        result = self.validator.validate_row(row, 1)
        self.assertEqual(result.status, ValidationStatus.PASSED)

    def test_invalid_transactions_data(self):
        """Test validation of invalid transactions data"""
        row = {
            "complex_id": "",  # Empty required field
            "complex_name": "테스트 아파트",
            "pyeong_type_number": "0",  # Invalid value
            "trade_type": " swapping",  # Invalid trade type
            "trade_type_name": "특수거래",  # Invalid type name
            "trade_date": "24-01-15",  # Invalid date format
            "trade_year": "1999",  # Too old
            "floor": "101",  # Too high
            "deal_price": "-1000",  # Negative
            "trade_category": "기타",  # Invalid category
            "is_delete": "maybe",  # Invalid boolean
            "is_renew": "yes",  # Invalid boolean
        }
        result = self.validator.validate_row(row, 1)
        self.assertEqual(result.status, ValidationStatus.FAILED)
        self.assertGreater(len(result.errors), 0)


class TestHogangnonoCSVWriterFieldValidation(unittest.TestCase):
    """Test HogangnonoCSVWriter field validation"""

    def test_complexes_has_required_fields(self):
        """Test that complexes CSV has all required fields"""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = HogangnonoCSVWriter(tmpdir)

            # Check for essential complexes fields
            complexes_fields = writer.COMPLEXES_FIELDNAMES
            required_fields = ["complex_id", "complex_name", "address", "fetched_at"]

            for field in required_fields:
                self.assertIn(field, complexes_fields, f"Missing required field: {field}")

    def test_transactions_has_required_fields(self):
        """Test that transactions CSV has all required fields"""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = HogangnonoCSVWriter(tmpdir)

            # Check for essential transactions fields
            transactions_fields = writer.TRANSACTIONS_FIELDNAMES
            required_fields = ["complex_id", "trade_type", "trade_date", "deal_price"]

            for field in required_fields:
                self.assertIn(field, transactions_fields, f"Missing required field: {field}")


if __name__ == "__main__":
    unittest.main()
