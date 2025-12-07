"""Tests for ComplexesCSVWriter."""

import csv
import tempfile
from pathlib import Path
from unittest import TestCase

from crawler.writers.complexes_csv_writer import ComplexesCSVWriter


class TestComplexesCSVWriter(TestCase):
    """ComplexesCSVWriter 단위 테스트"""

    def setUp(self) -> None:
        """테스트 환경 설정"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.csv_path = self.temp_dir / "complexes.csv"
        self.writer = ComplexesCSVWriter(self.csv_path)

        # 샘플 데이터
        self.sample_complex_data = {
            "complex_id": "111515",
            "complex_name": "헬리오시티",
            "real_estate_type": "아파트",
            "completion_year_month": "2021-12",
            "total_dong_count": 8,
            "total_household_count": 1247,
            "min_area": 59.91,
            "max_area": 114.88,
            "deal_count": 10,
            "lease_count": 5,
            "rent_count": 3,
            "pyeong_types": '[{"pyeong_type_number": 1, "pyeong_name": "84A"}]',
            "fetched_at": "2025-12-06T10:00:00",
        }

        # 샘플 거래내역 데이터
        self.sample_transactions = [
            {
                "trade_type": "A1",
                "trade_date": "2025-11-14",
                "deal_price": 1700000000,
                "is_delete": False,
            },
            {
                "trade_type": "B1",
                "trade_date": "2025-10-20",
                "deal_price": 0,
                "deposit": 800000000,
                "is_delete": False,
            },
        ]

    def test_write_header_creates_file_with_correct_headers(self) -> None:
        """헤더 작성 테스트"""
        self.writer.write_header()

        # 파일이 생성되었는지 확인
        self.assertTrue(self.csv_path.exists())

        # 헤더 내용 확인
        with open(self.csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, ComplexesCSVWriter.FIELDNAMES)

    def test_write_creates_file_with_data_and_headers(self) -> None:
        """새 파일에 데이터 작성 테스트"""
        # 데이터에 통계 필드 추가
        data = {
            **self.sample_complex_data,
            "total_transaction_count": 8,
            "latest_deal_price": 1700000000,
            "latest_deal_date": "2025-11-14",
            "avg_deal_price_1year": 1650000000,
            "deal_count_1year": 3,
            "lease_count_1year": 2,
            "rent_count_1year": 1,
        }

        self.writer.write([data])

        # 파일이 생성되었는지 확인
        self.assertTrue(self.csv_path.exists())

        # 내용 확인
        with open(self.csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # 헤더 확인
            self.assertEqual(reader.fieldnames, ComplexesCSVWriter.FIELDNAMES)

            # 데이터 확인
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["complex_id"], "111515")
            self.assertEqual(rows[0]["complex_name"], "헬리오시티")
            self.assertEqual(rows[0]["total_transaction_count"], "8")
            self.assertEqual(rows[0]["latest_deal_price"], "1700000000")

    def test_append_with_statistics(self) -> None:
        """통계 계산과 함께 추가하는 기능 테스트"""
        self.writer.append_with_statistics(self.sample_complex_data, self.sample_transactions)

        # 파일이 생성되었는지 확인
        self.assertTrue(self.csv_path.exists())

        # 내용 확인
        with open(self.csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            self.assertEqual(len(rows), 1)
            row = rows[0]

            # 기본 정보 확인
            self.assertEqual(row["complex_id"], "111515")
            self.assertEqual(row["complex_name"], "헬리오시티")

            # 통계 정보 확인
            self.assertEqual(row["total_transaction_count"], "2")
            self.assertEqual(row["latest_deal_price"], "1700000000")  # Latest deal is 매매
            self.assertEqual(row["latest_deal_date"], "2025-11-14")
            self.assertEqual(row["deal_count_1year"], "1")  # One 매매 in last year
            self.assertEqual(row["lease_count_1year"], "1")  # One 전세 in last year
            self.assertEqual(row["rent_count_1year"], "0")  # No 월세

    def test_normalize_complex_data_handles_missing_fields(self) -> None:
        """누락된 필드가 있는 데이터 정규화 테스트"""
        incomplete_data = {
            "complex_id": "111515",
            "complex_name": "헬리오시티",
            # 다른 필드들은 누락
        }

        normalized = self.writer._normalize_complex_data(incomplete_data)

        # 모든 필드가 있는지 확인
        for field in ComplexesCSVWriter.FIELDNAMES:
            self.assertIn(field, normalized)

        # 누락된 필드가 기본값으로 채워졌는지 확인
        self.assertEqual(normalized["total_transaction_count"], 0)
        self.assertEqual(normalized["latest_deal_price"], 0)
        self.assertEqual(normalized["latest_deal_date"], "")

    def test_all_fields_in_fieldnames(self) -> None:
        """FIELDNAMES에 모든 필드가 포함되어 있는지 확인"""
        expected_fields = [
            # 기본 필드
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
            # 상세 정보 필드
            "pyeong_types",
            "fetched_at",
            # 통계 필드
            "total_transaction_count",
            "latest_deal_price",
            "latest_deal_date",
            "avg_deal_price_1year",
            "deal_count_1year",
            "lease_count_1year",
            "rent_count_1year",
        ]

        for field in expected_fields:
            self.assertIn(field, ComplexesCSVWriter.FIELDNAMES)

    def test_append_creates_file_if_not_exists(self) -> None:
        """파일이 없을 때 append가 새 파일을 생성하는지 테스트"""
        # 파일이 없는 상태에서 append 호출
        self.assertFalse(self.csv_path.exists())

        data = {
            **self.sample_complex_data,
            "total_transaction_count": 0,
            "latest_deal_price": 0,
            "latest_deal_date": "",
            "avg_deal_price_1year": 0,
            "deal_count_1year": 0,
            "lease_count_1year": 0,
            "rent_count_1year": 0,
        }

        self.writer.append([data])

        # 파일이 생성되었는지 확인
        self.assertTrue(self.csv_path.exists())

        # 내용 확인
        with open(self.csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(reader.fieldnames, ComplexesCSVWriter.FIELDNAMES)

    def test_ensure_file_exists_creates_file_when_missing(self) -> None:
        """ensure_file_exists가 없는 파일을 생성하는지 테스트"""
        self.assertFalse(self.csv_path.exists())
        self.writer.ensure_file_exists()
        self.assertTrue(self.csv_path.exists())

        # 헤더만 있는 파일인지 확인
        with open(self.csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.assertEqual(list(reader), [])

    def test_ensure_file_exists_does_nothing_when_file_exists(self) -> None:
        """ensure_file_exists가 기존 파일을 건드리지 않는지 테스트"""
        # 파일 생성 및 데이터 작성
        data = {
            **self.sample_complex_data,
            "total_transaction_count": 0,
            "latest_deal_price": 0,
            "latest_deal_date": "",
            "avg_deal_price_1year": 0,
            "deal_count_1year": 0,
            "lease_count_1year": 0,
            "rent_count_1year": 0,
        }

        self.writer.write([data])
        original_size = self.csv_path.stat().st_size

        # ensure_file_exists 호출
        self.writer.ensure_file_exists()

        # 파일 크기가 변하지 않았는지 확인
        self.assertEqual(self.csv_path.stat().st_size, original_size)
