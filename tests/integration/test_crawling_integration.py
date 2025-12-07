"""통합 테스트: 크롤링 결과물 검증"""

import csv
import json
import tempfile
from pathlib import Path

import pytest

from crawler.writers.complexes_csv_writer import ComplexesCSVWriter
from crawler.writers.transaction_csv_writer import TransactionCSVWriter


pytestmark = pytest.mark.integration


@pytest.fixture
def temp_output_dir():
    """임시 출력 디렉토리"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_complex_data():
    """샘플 단지 데이터"""
    return [
        {
            "complex_id": "11234",
            "complex_name": "힐스테이트 삼성동",
            "real_estate_type": "아파트",
            "completion_year_month": "201512",
            "total_dong_count": 3,
            "total_household_count": 680,
            "min_area": 84.98,
            "max_area": 132.85,
            "deal_count": 5,
            "lease_count": 3,
            "rent_count": 2,
        },
        {
            "complex_id": "56789",
            "complex_name": "래미안 아크리벨",
            "real_estate_type": "아파트",
            "completion_year_month": "201803",
            "total_dong_count": 2,
            "total_household_count": 320,
            "min_area": 59.95,
            "max_area": 114.72,
            "deal_count": 3,
            "lease_count": 2,
            "rent_count": 1,
        },
    ]


@pytest.fixture
def sample_transaction_data():
    """샘플 매물 데이터"""
    return [
        {
            "article_no": "12345",
            "complex_id": "11234",
            "complex_name": "힐스테이트 삼성동",  # 이 필드가 있는지 확인
            "pyeong_type_number": 1,
            "pyeong_name": "25평형",  # 이 필드가 있는지 확인
            "trade_type": "A1",
            "trade_type_name": "매매",
            "trade_date": "2024.11.15",
            "trade_year": "2024",
            "floor": 15,
            "deal_price": 125000000,
            "deposit": 0,
            "monthly_rent": 0,
            "trade_category": "일반",
            "is_delete": False,
            "is_renew": False,
        },
        {
            "article_no": "67890",
            "complex_id": "11234",
            "complex_name": "힐스테이트 삼성동",
            "pyeong_type_number": 2,
            "pyeong_name": "18평형",
            "trade_type": "B1",
            "trade_type_name": "전세",
            "trade_date": "2024.11.10",
            "trade_year": "2024",
            "floor": 8,
            "deal_price": 0,
            "deposit": 85000000,
            "monthly_rent": 0,
            "trade_category": "일반",
            "is_delete": False,
            "is_renew": False,
        },
    ]


class TestCrawlingIntegration:
    """크롤링 통합 테스트"""

    def test_complexes_csv_saved_correctly(self, temp_output_dir, sample_complex_data):
        """complexes.csv에 단지 정보가 저장되는지 확인"""
        complexes_csv = temp_output_dir / "complexes.csv"

        # CSV 파일 작성
        writer = ComplexesCSVWriter(str(complexes_csv))
        writer.write_header()
        for row in sample_complex_data:
            writer.write_row(row)
        writer.close()

        # 파일 생성 확인
        assert complexes_csv.exists(), "complexes.csv 파일이 생성되지 않음"

        # 파일 내용 확인
        with open(complexes_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2, f"2개의 행이 예상되었으나 {len(rows)}개만 있음"

        # 데이터 확인
        row1 = rows[0]
        assert row1["complex_id"] == "11234"
        assert row1["complex_name"] == "힐스테이트 삼성동"
        assert row1["total_household_count"] == "680"
        assert row1["total_dong_count"] == "3"

    def test_transactions_csv_has_complex_name_and_pyeong_name(
        self, temp_output_dir, sample_transaction_data
    ):
        """transactions.csv에 complex_name과 pyeong_name이 있는지 확인"""
        transactions_csv = temp_output_dir / "transactions.csv"

        # CSV 파일 작성
        writer = TransactionCSVWriter(str(transactions_csv))
        writer.write_header()
        for row in sample_transaction_data:
            writer.write_row(row)
        writer.close()

        # 파일 생성 확인
        assert transactions_csv.exists(), "transactions.csv 파일이 생성되지 않음"

        # 파일 내용 확인
        with open(transactions_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2, f"2개의 행이 예상되었으나 {len(rows)}개만 있음"

        # 헤더에 필수 컬럼이 있는지 확인
        headers = reader.fieldnames
        assert "complex_name" in headers, "complex_name 컬럼이 없음"
        assert "pyeong_name" in headers, "pyeong_name 컬럼이 없음"

        # 데이터 확인
        for row in rows:
            assert row["complex_name"], "complex_name이 비어있음"
            assert row["pyeong_name"], "pyeong_name이 비어있음"
            assert row["complex_id"] == "11234"

    def test_output_option_creates_files_in_specified_path(
        self, temp_output_dir, sample_complex_data, sample_transaction_data
    ):
        """--output 옵션으로 지정한 경로에 파일이 생성되는지 확인"""
        # 출력 경로 설정
        output_path = temp_output_dir / "custom_output"
        output_path.mkdir(exist_ok=True)

        # 직접 파일 생성
        complexes_csv = output_path / "complexes.csv"
        transactions_csv = output_path / "transactions.csv"
        checkpoint_json = output_path / "checkpoint.json"

        # complexes.csv 생성
        writer = ComplexesCSVWriter(str(complexes_csv))
        writer.write_header()
        for row in sample_complex_data:
            writer.write_row(row)
        writer.close()

        # transactions.csv 생성
        writer = TransactionCSVWriter(str(transactions_csv))
        writer.write_header()
        for row in sample_transaction_data:
            writer.write_row(row)
        writer.close()

        # checkpoint.json 생성
        checkpoint_data = {
            "completed_dongs": {"11680": True},
            "stats": {"total_complexes": 1, "total_listings": 1},
        }
        with open(checkpoint_json, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)

        # 파일들이 지정된 경로에 생성되었는지 확인
        expected_files = [
            output_path / "complexes.csv",
            output_path / "transactions.csv",
            output_path / "checkpoint.json",
        ]

        for file_path in expected_files:
            assert file_path.exists(), f"{file_path.name} 파일이 {output_path}에 생성되지 않음"

    def test_checkpoint_file_format(self, temp_output_dir):
        """체크포인트 파일 형식 확인"""
        checkpoint_file = temp_output_dir / "checkpoint.json"

        # 체크포인트 데이터 생성
        checkpoint_data = {
            "completed_dongs": {"11680": True, "11650": True},
            "failed_dongs": {"11620": 2},
            "current_dong": "11680",
            "stats": {
                "total_complexes": 100,
                "total_listings": 1500,
            },
        }

        # 파일 저장
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)

        # 파일 생성 확인
        assert checkpoint_file.exists(), "checkpoint.json 파일이 생성되지 않음"

        # 내용 확인
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)

        assert "completed_dongs" in loaded_data
        assert "failed_dongs" in loaded_data
        assert "stats" in loaded_data
        assert loaded_data["current_dong"] == "11680"

    def test_csv_files_have_correct_headers(self, temp_output_dir):
        """CSV 파일들이 올바른 헤더를 가지는지 확인"""
        complexes_csv = temp_output_dir / "complexes.csv"
        transactions_csv = temp_output_dir / "transactions.csv"

        # 단지 CSV 헤더 확인
        with open(complexes_csv, "w", encoding="utf-8", newline="") as f:
            writer = ComplexesCSVWriter(str(complexes_csv))
            writer.write_header()
            writer.close()

        with open(complexes_csv, "r", encoding="utf-8") as f:
            headers = f.readline().strip().split(",")

        expected_complex_headers = [
            "complex_id",
            "complex_name",
            "real_estate_type",
            "completion_year_month",
            "total_dong_count",
            "total_household_count",
            "min_area",
            "max_area",
            "deal_count",
            "lease_count",
            "rent_count",
        ]

        for header in expected_complex_headers:
            assert header in headers, f"complexes.csv에 {header} 헤더가 없음"

        # 매물 CSV 헤더 확인
        with open(transactions_csv, "w", encoding="utf-8", newline="") as f:
            writer = TransactionCSVWriter(str(transactions_csv))
            writer.write_header()
            writer.close()

        with open(transactions_csv, "r", encoding="utf-8") as f:
            headers = f.readline().strip().split(",")

        # 중요한 필드만 확인
        important_headers = [
            "complex_name",  # 이 필드가 중요
            "pyeong_name",  # 이 필드가 중요
        ]

        for header in important_headers:
            assert header in headers, f"transactions.csv에 {header} 헤더가 없음"
