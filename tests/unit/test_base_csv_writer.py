"""Tests for BaseCSVWriter class."""

import csv
from pathlib import Path
from typing import Any, Dict

import pytest

from crawler.writers.base_csv_writer import BaseCSVWriter


# Test concrete implementation of BaseCSVWriter
class ConcreteTestCSVWriter(BaseCSVWriter):
    """Test implementation of BaseCSVWriter for testing purposes."""

    FIELDNAMES = ["id", "name", "value", "active"]

    def _normalize_row_legacy(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Simple normalization for testing."""
        return self._normalize_common_fields(row)


class TestBaseCSVWriter:
    """Test cases for BaseCSVWriter."""

    def test_init(self, tmp_path: Path) -> None:
        """Test BaseCSVWriter initialization."""
        output_path = tmp_path / "test.csv"
        writer = ConcreteTestCSVWriter(output_path)

        assert writer.output_path == output_path
        assert writer._file_exists is False  # File doesn't exist yet

    def test_init_with_existing_file(self, tmp_path: Path) -> None:
        """Test BaseCSVWriter initialization with existing file."""
        output_path = tmp_path / "test.csv"

        # Create file first
        output_path.write_text("id,name,value,active\n", encoding="utf-8")

        writer = ConcreteTestCSVWriter(output_path)
        assert writer._file_exists is True

    def test_write_header(self, tmp_path: Path) -> None:
        """Test writing CSV header."""
        output_path = tmp_path / "test.csv"
        writer = ConcreteTestCSVWriter(output_path)

        writer.write_header()

        # Check file was created
        assert output_path.exists()
        assert writer._file_exists is True

        # Check header content
        content = output_path.read_text(encoding="utf-8")
        assert "id,name,value,active" in content

    def test_write_new_file_with_header(self, tmp_path: Path) -> None:
        """Test writing data to new file with header."""
        output_path = tmp_path / "test.csv"
        writer = ConcreteTestCSVWriter(output_path)

        data = [
            {"id": 1, "name": "test1", "value": 100, "active": True},
            {"id": 2, "name": "test2", "value": 200, "active": False},
        ]

        writer.write(data)

        # Check file content
        with open(output_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["id"] == "1"
        assert rows[0]["name"] == "test1"
        assert rows[0]["value"] == "100"
        assert rows[0]["active"] == "true"
        assert rows[1]["active"] == "false"

    def test_write_append_mode(self, tmp_path: Path) -> None:
        """Test appending data to existing file."""
        output_path = tmp_path / "test.csv"
        writer = ConcreteTestCSVWriter(output_path)

        # Write initial data
        initial_data = [{"id": 1, "name": "test1", "value": 100, "active": True}]
        writer.write(initial_data)

        # Append more data
        append_data = [{"id": 2, "name": "test2", "value": 200, "active": False}]
        writer.write(append_data, mode="a", write_header=False)

        # Check file content
        with open(output_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["id"] == "1"
        assert rows[1]["id"] == "2"

    def test_write_empty_data(self, tmp_path: Path) -> None:
        """Test writing empty data list."""
        output_path = tmp_path / "test.csv"
        writer = ConcreteTestCSVWriter(output_path)

        writer.write([])

        # File should not be created for empty data
        assert not output_path.exists()

    def test_append_new_file(self, tmp_path: Path) -> None:
        """Test append method creates new file with header."""
        output_path = tmp_path / "test.csv"
        writer = ConcreteTestCSVWriter(output_path)

        data = [{"id": 1, "name": "test1", "value": 100, "active": True}]
        writer.append(data)

        # Check file was created with header
        with open(output_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert reader.fieldnames == ["id", "name", "value", "active"]

    def test_append_existing_file(self, tmp_path: Path) -> None:
        """Test append method adds to existing file."""
        output_path = tmp_path / "test.csv"
        writer = ConcreteTestCSVWriter(output_path)

        # Create initial file
        initial_data = [{"id": 1, "name": "test1", "value": 100, "active": True}]
        writer.write(initial_data)

        # Append more data
        append_data = [{"id": 2, "name": "test2", "value": 200, "active": False}]
        writer.append(append_data)

        # Check file content
        with open(output_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["id"] == "1"
        assert rows[1]["id"] == "2"

    def test_ensure_file_exists(self, tmp_path: Path) -> None:
        """Test ensure_file_exists method."""
        output_path = tmp_path / "test.csv"
        writer = ConcreteTestCSVWriter(output_path)

        # File doesn't exist initially
        assert not output_path.exists()

        # Ensure file exists
        writer.ensure_file_exists()
        assert output_path.exists()
        assert writer._file_exists is True

        # Check header was written
        with open(output_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == ["id", "name", "value", "active"]

    def test_get_file_info_new_file(self, tmp_path: Path) -> None:
        """Test get_file_info for non-existent file."""
        output_path = tmp_path / "test.csv"
        writer = ConcreteTestCSVWriter(output_path)

        info = writer.get_file_info()

        assert info["file_path"] == str(output_path)
        assert info["file_exists"] is False
        assert info["file_size"] == 0
        assert info["record_count"] == 0
        assert info["fieldnames"] == ["id", "name", "value", "active"]

    def test_get_file_info_existing_file(self, tmp_path: Path) -> None:
        """Test get_file_info for existing file."""
        output_path = tmp_path / "test.csv"
        writer = ConcreteTestCSVWriter(output_path)

        # Write some data
        data = [
            {"id": 1, "name": "test1", "value": 100, "active": True},
            {"id": 2, "name": "test2", "value": 200, "active": False},
        ]
        writer.write(data)

        info = writer.get_file_info()

        assert info["file_path"] == str(output_path)
        assert info["file_exists"] is True
        assert info["file_size"] > 0
        assert info["record_count"] == 2
        assert info["fieldnames"] == ["id", "name", "value", "active"]

    def test_normalize_common_fields(self, tmp_path: Path) -> None:
        """Test _normalize_common_fields method."""
        output_path = tmp_path / "test.csv"
        writer = ConcreteTestCSVWriter(output_path)

        # Test various data types
        row = {
            "id": 1,
            "name": "test",
            "value": None,
            "active": True,
            "missing": "value",
        }

        normalized = writer._normalize_common_fields(row)

        assert normalized["id"] == 1
        assert normalized["name"] == "test"
        assert normalized["value"] == ""  # None becomes empty string
        assert normalized["active"] == "true"  # Boolean becomes lowercase string
        assert "missing" not in normalized  # Only fields in FIELDNAMES

    def test_abstract_class(self) -> None:
        """Test that BaseCSVWriter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseCSVWriter(Path("test.csv"))  # type: ignore
