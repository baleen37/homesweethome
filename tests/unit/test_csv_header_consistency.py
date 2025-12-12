"""Tests for CSV header consistency across different writers and strategies.

This test module verifies that all CSV outputs have consistent headers
regardless of which writer or strategy is used.
"""

import unittest
import tempfile
from pathlib import Path

from crawler.writers.csv_header_standard import (
    CSVType,
    HeaderStandardRegistry,
)
from crawler.writers.hogangnono_complexes_writer import HogangnonoComplexesCSVWriter
from crawler.writers.hogangnono_transactions_writer import HogangnonoTransactionsCSVWriter
from crawler.writers.hogangnono_strategy import (
    HogangnonoComplexStrategy,
    HogangnonoTransactionStrategy,
)


class TestCSVHeaderConsistency(unittest.TestCase):
    """Test CSV header consistency across different writers."""

    def test_complexes_header_standard_definition(self):
        """Test that complexes header standard is properly defined."""
        # Get standard fieldnames
        standard_fieldnames = HeaderStandardRegistry.get_fieldnames(CSVType.COMPLEXES)

        # Verify required fields are present
        required_fields = HeaderStandardRegistry.get_required_fields(CSVType.COMPLEXES)

        assert len(standard_fieldnames) > 0, "Complexes header standard should have fields"
        assert len(required_fields) > 0, "Complexes header standard should have required fields"

        # Check for essential fields
        essential_fields = {"complex_id", "complex_name", "real_estate_type", "fetched_at"}
        assert essential_fields.issubset(set(standard_fieldnames)), (
            f"Missing essential fields: {essential_fields - set(standard_fieldnames)}"
        )

    def test_transactions_header_standard_definition(self):
        """Test that transactions header standard is properly defined."""
        # Get standard fieldnames
        standard_fieldnames = HeaderStandardRegistry.get_fieldnames(CSVType.TRANSACTIONS)

        # Verify required fields are present
        required_fields = HeaderStandardRegistry.get_required_fields(CSVType.TRANSACTIONS)

        assert len(standard_fieldnames) > 0, "Transactions header standard should have fields"
        assert len(required_fields) > 0, "Transactions header standard should have required fields"

        # Check for essential fields
        essential_fields = {"complex_id", "complex_name", "trade_type", "trade_date"}
        assert essential_fields.issubset(set(standard_fieldnames)), (
            f"Missing essential fields: {essential_fields - set(standard_fieldnames)}"
        )

    def test_hogangnono_complex_strategy_headers_match_standard(self):
        """Test that HogangnonoComplexStrategy fieldnames match the standard."""
        strategy = HogangnonoComplexStrategy()
        strategy_fieldnames = strategy.get_fieldnames()

        standard_fieldnames = HeaderStandardRegistry.get_fieldnames(CSVType.COMPLEXES)

        # Check that strategy has all required standard fields
        required_fields = HeaderStandardRegistry.get_required_fields(CSVType.COMPLEXES)
        for field in required_fields:
            assert field in strategy_fieldnames, f"Strategy missing required field: {field}"

        # Check that strategy fields are a superset of standard (for additional POI fields)
        strategy_set = set(strategy_fieldnames)
        standard_set = set(standard_fieldnames)

        # Strategy should have all standard fields
        assert standard_set.issubset(strategy_set), (
            f"Strategy missing standard fields: {standard_set - strategy_set}"
        )

    def test_hogangnono_transaction_strategy_headers_match_standard(self):
        """Test that HogangnonoTransactionStrategy fieldnames match the standard."""
        strategy = HogangnonoTransactionStrategy()
        strategy_fieldnames = strategy.get_fieldnames()

        standard_fieldnames = HeaderStandardRegistry.get_fieldnames(CSVType.TRANSACTIONS)

        # Check that strategy has all required standard fields
        required_fields = HeaderStandardRegistry.get_required_fields(CSVType.TRANSACTIONS)
        for field in required_fields:
            assert field in strategy_fieldnames, f"Strategy missing required field: {field}"

        # Check that strategy fields match standard exactly
        assert set(strategy_fieldnames) == set(standard_fieldnames), (
            f"Strategy fieldnames don't match standard:\nStrategy: {strategy_fieldnames}\nStandard: {standard_fieldnames}"
        )

    def test_complexes_writer_uses_standard_headers(self):
        """Test that HogangnonoComplexesCSVWriter uses standard headers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_complexes.csv"
            writer = HogangnonoComplexesCSVWriter(output_path)

            # Get fieldnames from writer
            writer_fieldnames = writer.get_fieldnames()

            # Check that writer has all required standard fields
            required_fields = HeaderStandardRegistry.get_required_fields(CSVType.COMPLEXES)
            for field in required_fields:
                assert field in writer_fieldnames, f"Writer missing required field: {field}"

    def test_transactions_writer_uses_standard_headers(self):
        """Test that HogangnonoTransactionsCSVWriter uses standard headers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_transactions.csv"
            writer = HogangnonoTransactionsCSVWriter(output_path)

            # Get fieldnames from writer
            writer_fieldnames = writer.get_fieldnames()

            # Check that writer has all required standard fields
            required_fields = HeaderStandardRegistry.get_required_fields(CSVType.TRANSACTIONS)
            for field in required_fields:
                assert field in writer_fieldnames, f"Writer missing required field: {field}"

    def test_header_consistency_across_writers(self):
        """Test that all writers for the same CSV type use consistent headers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create complexes writers
            complexes_writer = HogangnonoComplexesCSVWriter(Path(tmpdir) / "complexes1.csv")
            complexes_strategy = HogangnonoComplexStrategy()

            # Compare fieldnames
            writer_fieldnames = complexes_writer.get_fieldnames()
            strategy_fieldnames = complexes_strategy.get_fieldnames()
            standard_fieldnames = HeaderStandardRegistry.get_fieldnames(CSVType.COMPLEXES)

            # All should have the same required fields
            required_fields = HeaderStandardRegistry.get_required_fields(CSVType.COMPLEXES)

            for field in required_fields:
                assert field in writer_fieldnames, f"Writer missing: {field}"
                assert field in strategy_fieldnames, f"Strategy missing: {field}"
                assert field in standard_fieldnames, f"Standard missing: {field}"

    def test_data_transform_preserves_header_order(self):
        """Test that data transformation preserves header field order."""
        # Create test data
        test_data = [
            {
                "aptSeq": "12345",
                "aptName": "테스트아파트",
                "householdCnt": "100",
                "dealCnt": "5",
                "buildYear": "2020",
            }
        ]

        # Test complexes transformation
        strategy = HogangnonoComplexStrategy()
        fieldnames = strategy.get_fieldnames()

        # Transform data
        transformed = strategy.transform(test_data[0], fieldnames)

        # Check that all expected fields are present
        for field in fieldnames:
            assert field in transformed, f"Transformed data missing field: {field}"

        # Check field order matches
        assert list(transformed.keys()) == fieldnames, (
            "Field order in transformed data doesn't match expected order"
        )

    def test_missing_required_fields_are_detected(self):
        """Test that missing required fields are properly detected."""
        from crawler.validators.csv_validator import create_complexes_validator

        validator = create_complexes_validator()

        # Create data with missing required fields
        invalid_data = [
            {
                "complex_name": "테스트아파트",
                # Missing complex_id (required)
            }
        ]

        # Validate should fail
        result = validator.validate_row(invalid_data[0], row_number=1)

        assert result.status.value == "failed", "Validation should fail for missing required fields"
        assert result.error_count > 0, "Should have validation errors"

        # Check that the error mentions the missing field
        error_messages = [e.error_message for e in result.errors]
        assert any("complex_id" in msg for msg in error_messages), (
            "Error should mention missing complex_id field"
        )

    def test_extra_fields_are_handled_gracefully(self):
        """Test that extra fields in data are handled gracefully."""
        from crawler.writers.csv_header_standard import ensure_header_consistency

        # Create data with extra fields
        data_with_extras = {
            "complex_id": "12345",
            "complex_name": "테스트아파트",
            "real_estate_type": "아파트",
            "fetched_at": "2024-01-01 12:00:00",
            # Extra fields not in standard
            "extra_field_1": "extra1",
            "extra_field_2": "extra2",
        }

        # Apply header consistency
        cleaned_data = ensure_header_consistency(data_with_extras, CSVType.COMPLEXES)

        # Check that extra fields are removed
        assert "extra_field_1" not in cleaned_data, "Extra field 1 should be removed"
        assert "extra_field_2" not in cleaned_data, "Extra field 2 should be removed"

        # Check that standard fields are preserved
        assert cleaned_data["complex_id"] == "12345", "Standard field should be preserved"
        assert cleaned_data["complex_name"] == "테스트아파트", "Standard field should be preserved"

    def test_csv_output_has_correct_headers(self):
        """Test that actual CSV output has correct headers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_output.csv"
            writer = HogangnonoComplexesCSVWriter(output_path)

            # Write header only
            writer.write_header()

            # Read CSV and check headers
            with open(output_path, "r", encoding="utf-8") as f:
                header_line = f.readline().strip()

            csv_headers = header_line.split(",")
            expected_headers = writer.get_fieldnames()

            assert csv_headers == expected_headers, (
                f"CSV headers don't match expected:\nCSV: {csv_headers}\nExpected: {expected_headers}"
            )
