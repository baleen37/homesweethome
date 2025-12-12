"""Tests for CSV writer refactoring - verify existing behavior before refactoring."""

import pytest
from pathlib import Path
import tempfile
import json
import sys

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from crawler.writers import HogangnonoCSVWriter


class TestHogangnonoCSVWriterBehavior:
    """Test existing behavior of HogangnonoCSVWriter before refactoring."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_complexes_data(self):
        """Sample complexes data for testing."""
        return [
            {
                "aptSeq": "12345",
                "aptName": "테스트 아파트",
                "buildYear": "2020",
                "householdCnt": "500",
                "dealCnt": "10",
                "lat": "37.123",
                "lng": "127.456",
                "address": "서울시 강남구 테헤란로",
            },
            {
                "aptSeq": "67890",
                "aptName": "샘플 아파트",
                "buildYear": "2019",
                "householdCnt": "300",
                "dealCnt": "5",
                "lat": "37.789",
                "lng": "127.012",
                "address": "서울시 서초구 강남대로",
            },
        ]

    @pytest.fixture
    def sample_transactions_data(self):
        """Sample transactions data for testing."""
        return [
            {
                "aptSeq": "12345",
                "aptName": "테스트 아파트",
                "dealType": "매매",
                "dealAmount": "100,000",
                "dealDate": "2024.01.15",
                "floor": "5",
                "pyeong": "33",
                "pyeongName": "33평",
                "area": "109",
            },
            {
                "aptSeq": "12345",
                "aptName": "테스트 아파트",
                "dealType": "전세",
                "deposit": "50,000",
                "dealDate": "2024.02.20",
                "floor": "3",
                "pyeong": "25",
                "pyeongName": "25평",
                "area": "83",
            },
        ]

    def test_hogangnono_csv_writer_initialization(self, temp_output_dir):
        """Test HogangnonoCSVWriter initialization."""
        writer = HogangnonoCSVWriter(str(temp_output_dir))

        assert writer.output_dir == temp_output_dir
        assert writer.complexes_path == temp_output_dir / "complexes.csv"
        assert writer.transactions_path == temp_output_dir / "transactions.csv"
        assert writer.complexes_writer is not None
        assert writer.transactions_writer is not None

    def test_save_complexes_creates_csv(self, temp_output_dir, sample_complexes_data):
        """Test save_complexes creates correct CSV file."""
        writer = HogangnonoCSVWriter(str(temp_output_dir))
        writer.save_complexes(sample_complexes_data)

        # Check file was created
        assert (temp_output_dir / "complexes.csv").exists()

        # Check file content
        import csv

        with open(temp_output_dir / "complexes.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["complex_id"] == "12345"
        assert rows[0]["complex_name"] == "테스트 아파트"
        assert rows[1]["complex_id"] == "67890"
        assert rows[1]["complex_name"] == "샘플 아파트"

    def test_save_transactions_creates_csv(self, temp_output_dir, sample_transactions_data):
        """Test save_transactions creates correct CSV file."""
        writer = HogangnonoCSVWriter(str(temp_output_dir))
        writer.save_transactions(sample_transactions_data)

        # Check file was created
        assert (temp_output_dir / "transactions.csv").exists()

        # Check file content
        import csv

        with open(temp_output_dir / "transactions.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["complex_id"] == "12345"
        assert rows[0]["trade_type"] == "매매"
        assert rows[1]["trade_type"] == "전세"

    def test_transform_complex_to_naver_format(self, temp_output_dir, sample_complexes_data):
        """Test transform_complex_to_naver_format method."""
        writer = HogangnonoCSVWriter(str(temp_output_dir))

        # Transform first complex
        transformed = writer.transform_complex_to_naver_format(sample_complexes_data[0])

        # Check field mappings
        assert transformed["complex_id"] == "12345"
        assert transformed["complex_name"] == "테스트 아파트"
        assert transformed["real_estate_type"] == "아파트"
        assert transformed["total_household_count"] == "500"
        assert transformed["deal_count"] == "10"
        assert transformed["completion_year_month"] == "20200101"

    def test_transform_transaction_to_naver_format(self, temp_output_dir, sample_transactions_data):
        """Test transform_transaction_to_naver_format method."""
        writer = HogangnonoCSVWriter(str(temp_output_dir))

        # Transform first transaction
        transformed = writer.transform_transaction_to_naver_format(sample_transactions_data[0])

        # Check field mappings
        assert transformed["complex_id"] == "12345"
        assert transformed["trade_type"] == "매매"
        assert transformed["trade_year"] == 2024
        assert transformed["floor"] == 5
        assert transformed["deal_price"] == 100000

    def test_parse_floor(self, temp_output_dir):
        """Test floor parsing logic."""
        writer = HogangnonoCSVWriter(str(temp_output_dir))

        # Test various floor formats
        assert writer._parse_floor("5") == 5
        assert writer._parse_floor("5/15") == 5
        assert writer._parse_floor("B1") == 0
        assert writer._parse_floor("지하1층") == 0
        assert writer._parse_floor("") == 0
        assert writer._parse_floor(None) == 0

    def test_parse_money_amount(self, temp_output_dir):
        """Test money amount parsing logic."""
        writer = HogangnonoCSVWriter(str(temp_output_dir))

        # Test various money formats
        assert writer._parse_money_amount("100,000") == 100000
        assert writer._parse_money_amount("100000") == 100000
        assert writer._parse_money_amount("45억") == 45
        assert writer._parse_money_amount("") == 0
        assert writer._parse_money_amount(None) == 0

    def test_get_stats(self, temp_output_dir, sample_complexes_data, sample_transactions_data):
        """Test get_stats method."""
        writer = HogangnonoCSVWriter(str(temp_output_dir))

        # Save some data
        writer.save_complexes(sample_complexes_data)
        writer.save_transactions(sample_transactions_data)

        # Get stats
        stats = writer.get_stats()

        assert "complexes_file_size" in stats
        assert "transactions_file_size" in stats
        assert "complexes_record_count" in stats
        assert "transactions_record_count" in stats
        assert stats["complexes_record_count"] == 2
        assert stats["transactions_record_count"] == 2

    def test_save_from_json_file(self, temp_output_dir, sample_complexes_data):
        """Test save_from_json_file method."""
        writer = HogangnonoCSVWriter(str(temp_output_dir))

        # Create JSON file
        json_file = temp_output_dir / "test_data.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(sample_complexes_data, f, ensure_ascii=False)

        # Save from JSON
        writer.save_from_json_file(str(json_file), data_type="complex")

        # Check result
        assert (temp_output_dir / "complexes.csv").exists()

        import csv

        with open(temp_output_dir / "complexes.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2


class TestIndividualWritersBehavior:
    """Test behavior of individual writers before refactoring."""

    @pytest.fixture
    def temp_csv_file(self):
        """Create temporary CSV file path."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            yield Path(f.name)

    def test_hogangnono_writer_initialization(self, temp_output_dir):
        """Test HogangnonoCSVWriter initialization."""
        writer = HogangnonoCSVWriter(str(temp_output_dir))

        assert writer.output_dir == temp_output_dir
        assert writer.complexes_path == temp_output_dir / "complexes.csv"
        assert writer.transactions_path == temp_output_dir / "transactions.csv"
        assert hasattr(writer, "COMPLEXES_FIELDNAMES")
        assert hasattr(writer, "TRANSACTIONS_FIELDNAMES")

    def test_hogangnono_writer_fieldnames(self, temp_output_dir):
        """Test that HogangnonoCSVWriter has correct fieldnames."""
        writer = HogangnonoCSVWriter(str(temp_output_dir))

        complexes_fields = set(writer.COMPLEXES_FIELDNAMES)
        transactions_fields = set(writer.TRANSACTIONS_FIELDNAMES)

        # They should have different fields
        assert complexes_fields != transactions_fields

        # Complexes should have complex-specific fields
        assert "total_household_count" in complexes_fields
        assert "completion_year_month" in complexes_fields

        # Transactions should have transaction-specific fields
        assert "trade_type" in transactions_fields
        assert "deal_price" in transactions_fields
        assert "trade_date" in transactions_fields
