"""Tests for CSV header consistency in HogangnonoCSVWriter.

This test module verifies that HogangnonoCSVWriter produces consistent headers
for both complexes and transactions CSV files.
"""

import unittest
import tempfile
from pathlib import Path

from crawler.writers import HogangnonoCSVWriter


class TestCSVHeaderConsistency(unittest.TestCase):
    """Test CSV header consistency in HogangnonoCSVWriter."""

    def test_complexes_header_has_required_fields(self):
        """Test that complexes CSV header has all required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = HogangnonoCSVWriter(tmpdir)

            # Get complexes fieldnames
            complexes_fieldnames = writer.COMPLEXES_FIELDNAMES

            # Check for essential fields
            essential_fields = {
                "complex_id",
                "complex_name",
                "real_estate_type",
                "address",
                "completion_year_month",
                "fetched_at",
            }
            missing_fields = essential_fields - set(complexes_fieldnames)
            self.assertEqual(
                len(missing_fields), 0, f"Missing essential fields in complexes: {missing_fields}"
            )

    def test_transactions_header_has_required_fields(self):
        """Test that transactions CSV header has all required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = HogangnonoCSVWriter(tmpdir)

            # Get transactions fieldnames
            transactions_fieldnames = writer.TRANSACTIONS_FIELDNAMES

            # Check for essential fields
            essential_fields = {
                "complex_id",
                "complex_name",
                "trade_type",
                "trade_date",
                "deal_price",
                "deposit",
                "monthly_rent",
                "floor",
            }
            missing_fields = essential_fields - set(transactions_fieldnames)
            self.assertEqual(
                len(missing_fields),
                0,
                f"Missing essential fields in transactions: {missing_fields}",
            )

    def test_csv_output_has_correct_headers(self):
        """Test that actual CSV output has correct headers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = HogangnonoCSVWriter(tmpdir)

            # Write headers
            writer.write_complexes_header()
            writer.write_transactions_header()

            # Check complexes CSV headers
            with open(writer.complexes_path, "r", encoding="utf-8") as f:
                complexes_header = f.readline().strip().split(",")

            self.assertEqual(
                complexes_header,
                writer.COMPLEXES_FIELDNAMES,
                "Complexes CSV headers don't match expected",
            )

            # Check transactions CSV headers
            with open(writer.transactions_path, "r", encoding="utf-8") as f:
                transactions_header = f.readline().strip().split(",")

            self.assertEqual(
                transactions_header,
                writer.TRANSACTIONS_FIELDNAMES,
                "Transactions CSV headers don't match expected",
            )

    def test_fieldnames_are_consistent_across_instances(self):
        """Test that fieldnames are consistent across different writer instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer1 = HogangnonoCSVWriter(tmpdir)
            writer2 = HogangnonoCSVWriter(str(Path(tmpdir) / "subdir"))

            # Both writers should have the same fieldnames
            self.assertEqual(
                writer1.COMPLEXES_FIELDNAMES,
                writer2.COMPLEXES_FIELDNAMES,
                "Complexes fieldnames should be consistent",
            )
            self.assertEqual(
                writer1.TRANSACTIONS_FIELDNAMES,
                writer2.TRANSACTIONS_FIELDNAMES,
                "Transactions fieldnames should be consistent",
            )

    def test_no_duplicate_fieldnames(self):
        """Test that there are no duplicate fieldnames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = HogangnonoCSVWriter(tmpdir)

            # Check for duplicates in complexes fieldnames
            complexes_set = set(writer.COMPLEXES_FIELDNAMES)
            self.assertEqual(
                len(complexes_set),
                len(writer.COMPLEXES_FIELDNAMES),
                "Complexes fieldnames should not have duplicates",
            )

            # Check for duplicates in transactions fieldnames
            transactions_set = set(writer.TRANSACTIONS_FIELDNAMES)
            self.assertEqual(
                len(transactions_set),
                len(writer.TRANSACTIONS_FIELDNAMES),
                "Transactions fieldnames should not have duplicates",
            )

    def test_fieldnames_follow_naming_convention(self):
        """Test that fieldnames follow snake_case convention."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = HogangnonoCSVWriter(tmpdir)

            # Check complexes fieldnames
            for field in writer.COMPLEXES_FIELDNAMES:
                self.assertRegex(
                    field,
                    r"^[a-z][a-z0-9_]*$",
                    f"Complexes field '{field}' should follow snake_case",
                )

            # Check transactions fieldnames
            for field in writer.TRANSACTIONS_FIELDNAMES:
                self.assertRegex(
                    field,
                    r"^[a-z][a-z0-9_]*$",
                    f"Transactions field '{field}' should follow snake_case",
                )
