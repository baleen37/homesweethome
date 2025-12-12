"""단순화된 HogangnonoCSVWriter 테스트"""

import pytest
import csv
from pathlib import Path
import tempfile
import shutil

from crawler.writers.hogangnono_csv_writer import HogangnonoCSVWriter


@pytest.fixture
def temp_output_dir():
    """임시 출력 디렉토리"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def writer(temp_output_dir):
    """테스트용 CSV Writer"""
    return HogangnonoCSVWriter(output_dir=str(temp_output_dir / "output"))


@pytest.fixture
def sample_complex_data():
    """샘플 단지 데이터"""
    return [
        {
            "aptSeq": "APT_001",
            "aptName": "테스트아파트",
            "address": "서울특별시 강남구 테스트동 123",
            "buildYear": "2020",
            "dealCnt": "10",
            "householdCnt": "500",
        },
        {
            "aptSeq": "APT_002",
            "aptName": "새아파트",
            "address": "경기도 성남시 분당구 분당동 456",
            "buildYear": "2022",
            "dealCnt": "5",
            "householdCnt": "300",
        },
    ]


@pytest.fixture
def sample_transaction_data():
    """샘플 거래내역 데이터"""
    return [
        {
            "aptSeq": "APT_001",
            "aptName": "테스트아파트",
            "dealType": "매매",
            "dealDate": "2023.12.01",
            "dealAmount": "45,000",
            "floor": "5/15",
            "pyeong": "33",
            "pyeongName": "33평",
        },
        {
            "aptSeq": "APT_001",
            "aptName": "테스트아파트",
            "dealType": "전세",
            "dealDate": "2023.11.15",
            "deposit": "30,000",
            "floor": "3/15",
            "pyeong": "25",
            "pyeongName": "25평",
        },
    ]


class TestHogangnonoCSVWriter:
    """단순화된 HogangnonoCSVWriter 테스트"""

    def test_init(self, writer):
        """초기화 테스트"""
        assert writer.output_dir.name == "output"
        assert writer.complexes_path.name == "complexes.csv"
        assert writer.transactions_path.name == "transactions.csv"
        assert isinstance(writer.output_dir, Path)

    def test_init_with_custom_dir(self, temp_output_dir):
        """커스텀 디렉토리로 초기화 테스트"""
        custom_dir = temp_output_dir / "custom"
        writer = HogangnonoCSVWriter(output_dir=str(custom_dir))
        assert writer.output_dir == custom_dir

    def test_save_complexes(self, writer, sample_complex_data, temp_output_dir):
        """단지 데이터 저장 테스트"""
        # 데이터 저장
        writer.save_complexes(sample_complex_data)

        # 파일 생성 확인
        complexes_file = temp_output_dir / "output" / "complexes.csv"
        assert complexes_file.exists()

        # CSV 내용 확인
        with open(complexes_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0]["complex_id"] == "APT_001"
            assert rows[0]["complex_name"] == "테스트아파트"
            assert rows[0]["real_estate_type"] == "아파트"

    def test_save_complexes_empty(self, writer, temp_output_dir):
        """빈 데이터 저장 테스트"""
        writer.save_complexes([])

        # 파일이 생성되지 않았는지 확인
        complexes_file = temp_output_dir / "output" / "complexes.csv"
        assert not complexes_file.exists()

    def test_save_transactions(self, writer, sample_transaction_data, temp_output_dir):
        """거래내역 저장 테스트"""
        # 데이터 저장
        writer.save_transactions(sample_transaction_data)

        # 파일 생성 확인
        transactions_file = temp_output_dir / "output" / "transactions.csv"
        assert transactions_file.exists()

        # CSV 내용 확인
        with open(transactions_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0]["complex_id"] == "APT_001"
            assert rows[0]["trade_type"] == "매매"
            assert rows[0]["floor"] == "5"
            assert rows[1]["trade_type"] == "전세"

    def test_save_transactions_empty(self, writer, temp_output_dir):
        """빈 거래내역 저장 테스트"""
        writer.save_transactions([])

        # 파일이 생성되지 않았는지 확인
        transactions_file = temp_output_dir / "output" / "transactions.csv"
        assert not transactions_file.exists()

    def test_append_to_existing_file(self, writer, sample_complex_data, temp_output_dir):
        """기존 파일에 데이터 추가 테스트"""
        # 첫 저장
        writer.save_complexes(sample_complex_data[:1])

        # 추가 저장
        writer.save_complexes(sample_complex_data[1:])

        # 전체 레코드 수 확인
        complexes_file = temp_output_dir / "output" / "complexes.csv"
        with open(complexes_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            # 헤더는 한 번만 작성되어야 함
            assert rows[0]["complex_id"] == "APT_001"
            assert rows[1]["complex_id"] == "APT_002"

    def test_transform_complex(self, writer):
        """단지 데이터 변환 테스트"""
        complex_data = {
            "aptSeq": "APT_TEST",
            "aptName": "테스트",
            "address": "주소",
            "buildYear": "2020",
            "dealCnt": "10",
            "householdCnt": "100",
        }

        result = writer._transform_complex(complex_data)

        assert result["complex_id"] == "APT_TEST"
        assert result["complex_name"] == "테스트"
        assert result["real_estate_type"] == "아파트"
        assert result["completion_year_month"] == "20200101"
        assert result["deal_count"] == "10"
        assert result["total_household_count"] == "100"

    def test_transform_complex_missing_fields(self, writer):
        """필드 누락된 단지 데이터 변환 테스트"""
        complex_data = {"aptSeq": "APT_TEST"}

        result = writer._transform_complex(complex_data)

        assert result["complex_id"] == "APT_TEST"
        assert result["complex_name"] == ""
        assert result["completion_year_month"] == ""
        assert result["deal_count"] == ""

    def test_transform_transaction(self, writer):
        """거래내역 데이터 변환 테스트"""
        transaction_data = {
            "aptSeq": "APT_001",
            "aptName": "테스트아파트",
            "dealType": "매매",
            "dealDate": "2023.12.01",
            "dealAmount": "45,000",
            "floor": "5/15",
            "pyeong": "33",
            "pyeongName": "33평",
        }

        result = writer._transform_transaction(transaction_data)

        assert result["complex_id"] == "APT_001"
        assert result["trade_type"] == "매매"
        assert result["trade_date"] == "2023-12-01"
        assert result["deal_price"] == 45000
        assert result["floor"] == 5
        assert result["pyeong_type_number"] == 33

    def test_parse_floor(self, writer):
        """층수 파싱 테스트"""
        assert writer._parse_floor("5") == 5
        assert writer._parse_floor("5/15") == 5
        assert writer._parse_floor("B1") == 0
        assert writer._parse_floor("지하1") == 0
        assert writer._parse_floor("") == 0
        assert writer._parse_floor("고층") == 0

    def test_parse_money(self, writer):
        """금액 파싱 테스트"""
        assert writer._parse_money("45,000") == 45000
        assert writer._parse_money("10억") == 10
        assert writer._parse_money("5,000만원") == 5000
        assert writer._parse_money("") == 0

    def test_format_completion_date(self, writer):
        """준공일자 형식화 테스트"""
        assert writer._format_completion_date("2020") == "20200101"
        assert writer._format_completion_date("202") == ""  # 유효하지 않은 년도
        assert writer._format_completion_date("") == ""
        assert writer._format_completion_date(None) == ""

    def test_output_dir_creation(self, temp_output_dir):
        """출력 디렉토리 자동 생성 테스트"""
        nested_dir = temp_output_dir / "nested" / "dir"
        writer = HogangnonoCSVWriter(output_dir=str(nested_dir))

        # 데이터 저장 시 디렉토리가 자동으로 생성되어야 함
        writer.save_complexes([{"aptSeq": "TEST"}])

        assert nested_dir.exists()
        assert (nested_dir / "complexes.csv").exists()
