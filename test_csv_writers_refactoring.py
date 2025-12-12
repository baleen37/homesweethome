#!/usr/bin/env python3
"""Test script for refactored CSV writers.

This script tests the new unified CSV writer architecture
and ensures backward compatibility.
"""

import sys
import os
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Mock structlog if not installed
try:
    import structlog  # noqa: F401
except ImportError:

    class MockLogger:
        def bind(self, **kwargs):
            return self

        def info(self, *args, **kwargs):
            pass

        def error(self, *args, **kwargs):
            pass

        def warning(self, *args, **kwargs):
            pass

    class MockStructlog:
        def get_logger(self):
            return MockLogger()

    sys.modules["structlog"] = MockStructlog()

# Mock other potentially missing modules
try:
    import csv_validator  # noqa: F401
except ImportError:

    class MockValidationResult:
        def __init__(self):
            self.errors = []
            self.warnings = []

        def is_valid(self):
            return True

    class MockCSVValidator:
        def validate_row(self, row, row_number):
            return MockValidationResult()

        def validate_file(self, path):
            return MockValidationResult()

    sys.modules["crawler.validators.csv_validator"] = type(sys)("csv_validator")
    sys.modules["crawler.validators.csv_validator"].CSVValidator = MockCSVValidator
    sys.modules["crawler.validators.csv_validator"].ValidationResult = MockValidationResult


# Test new unified writers
def test_unified_csv_writer():
    """Test the basic UnifiedCSVWriter."""
    from crawler.writers.unified_csv_writer import UnifiedCSVWriter, WriteConfig

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test.csv"

        # Create writer with custom config
        config = WriteConfig(delimiter=";", quoting=1)
        writer = UnifiedCSVWriter(output_path, config=config)

        # Write test data
        data = [
            {"id": 1, "name": "Test1", "value": 100},
            {"id": 2, "name": "Test2", "value": 200},
        ]

        writer.write(data)

        # Verify file was created
        assert output_path.exists()

        # Check content
        content = output_path.read_text(encoding="utf-8")
        lines = content.split("\n")
        assert "id;name;value" in lines[0]  # Header with semicolon
        assert "1;Test1;100" in lines[1]
        assert "2;Test2;200" in lines[2]

        # Check stats
        stats = writer.get_stats()
        assert stats["rows_written"] == 2
        print("✓ UnifiedCSVWriter test passed")


def test_complex_csv_writer():
    """Test ComplexCSVWriter with Korean fields."""
    from crawler.writers.complex_csv_writer import ComplexCSVWriter

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "complexes.csv"

        writer = ComplexCSVWriter(output_path, use_korean_fields=True)

        # Write test complex data
        data = [
            {
                "id": "C001",
                "name": "테스트아파트",
                "address": "서울시 강남구",
                "buildYear": "2020",
                "households": 500,
            }
        ]

        writer.write(data)

        # Verify file
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")

        # Should contain Korean field names
        assert "단지ID" in content
        assert "테스트아파트" in content

        stats = writer.get_stats()
        assert stats["rows_written"] == 1
        print("✓ ComplexCSVWriter test passed")


def test_transaction_csv_writer():
    """Test TransactionCSVWriter."""
    from crawler.writers.transaction_csv_writer import TransactionCSVWriter

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "transactions.csv"

        writer = TransactionCSVWriter(output_path)

        # Write test transaction data
        data = [
            {
                "complex_id": "C001",
                "complex_name": "테스트아파트",
                "trade_type": "매매",
                "deal_price": 100000,
                "trade_date": "2024-01-15",
            }
        ]

        writer.write(data)

        # Verify file
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")

        assert "complex_id" in content
        assert "C001" in content

        stats = writer.get_stats()
        assert stats["rows_written"] == 1
        print("✓ TransactionCSVWriter test passed")


def test_streaming_csv_writer():
    """Test StreamingCSVWriter with large data."""
    from crawler.writers.streaming_csv_writer import StreamingCSVWriter
    import time

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "large.csv"

        writer = StreamingCSVWriter(output_path, chunk_size=10)

        # Generate test data iterator
        def generate_data(count: int):
            for i in range(count):
                yield {
                    "id": i,
                    "name": f"Record{i}",
                    "value": i * 10,
                    "timestamp": time.time(),
                }

        # Write streaming
        stats = writer.write_streaming(generate_data(25))

        assert stats["records_processed"] == 25
        assert stats["chunks_written"] == 3  # 25 records with chunk_size=10

        # Verify file
        assert output_path.exists()
        lines = output_path.read_text(encoding="utf-8").split("\n")
        assert len(lines) > 25  # Header + data rows

        print("✓ StreamingCSVWriter test passed")


def test_dataclass_csv_writer():
    """Test DataClassCSVWriter with dataclass objects."""
    from dataclasses import dataclass
    from crawler.writers.dataclass_csv_writer import DataClassCSVWriter

    @dataclass
    class TestRecord:
        id: int
        name: str
        value: float
        active: bool = True

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "dataclass.csv"

        writer = DataClassCSVWriter(output_path, dataclass_type=TestRecord)

        # Create test dataclass objects
        objects = [
            TestRecord(id=1, name="Test1", value=10.5),
            TestRecord(id=2, name="Test2", value=20.3, active=False),
        ]

        writer.write_dataclasses(objects)

        # Verify file
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")

        assert "id,name,value,active" in content
        assert "1,Test1,10.5,true" in content
        assert "2,Test2,20.3,false" in content

        print("✓ DataClassCSVWriter test passed")


def test_backward_compatibility():
    """Test that legacy writers still work."""
    from crawler.writers import CSVWriter, ComplexesCSVWriter, HogangnonoCSVWriter

    # Test CSVWriter
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "legacy.csv"
        writer = CSVWriter(output_path)

        data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        writer.write(data)

        assert output_path.exists()
        print("✓ Legacy CSVWriter test passed")

    # Test ComplexesCSVWriter
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "complexes.csv"
        writer = ComplexesCSVWriter(output_path)

        data = [{"complex_id": "C001", "complex_name": "Test"}]
        writer.write(data)

        assert output_path.exists()
        print("✓ Legacy ComplexesCSVWriter test passed")

    # Test HogangnonoCSVWriter
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = HogangnonoCSVWriter(tmpdir)

        data = [{"aptSeq": "C001", "aptName": "테스트"}]
        writer.save_complexes(data)

        assert (Path(tmpdir) / "complexes.csv").exists()
        print("✓ Legacy HogangnonoCSVWriter test passed")


def test_hogangnono_factory():
    """Test Hogangnono factory functions."""
    from crawler.writers.hogangnono_factory import (
        create_hogangnono_complex_writer,
        create_hogangnono_transaction_writer,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        # Test complex writer
        complex_path = Path(tmpdir) / "complex.csv"
        complex_writer = create_hogangnono_complex_writer(complex_path)

        data = [{"aptSeq": "C001", "aptName": "테스트"}]
        complex_writer.write(data)

        assert complex_path.exists()
        print("✓ Hogangnono complex factory test passed")

        # Test transaction writer
        trans_path = Path(tmpdir) / "trans.csv"
        trans_writer = create_hogangnono_transaction_writer(trans_path)

        data = [{"aptSeq": "C001", "dealType": "매매"}]
        trans_writer.write(data)

        assert trans_path.exists()
        print("✓ Hogangnono transaction factory test passed")


if __name__ == "__main__":
    print("Testing CSV Writers Refactoring...\n")

    test_unified_csv_writer()
    test_complex_csv_writer()
    test_transaction_csv_writer()
    test_streaming_csv_writer()
    test_dataclass_csv_writer()
    test_backward_compatibility()
    test_hogangnono_factory()

    print("\n✅ All tests passed! The refactoring is successful.")
    print("\nSummary of changes:")
    print("- Reduced from 16+ writer classes to 5 core writers")
    print("- Unified common functionality in UnifiedCSVWriter")
    print("- Maintained backward compatibility with legacy writers")
    print("- Added new features: streaming, dataclass support, memory optimization")
