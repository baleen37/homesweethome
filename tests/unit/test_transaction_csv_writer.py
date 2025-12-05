import csv
import tempfile
from pathlib import Path
from unittest import TestCase

from crawler.writers.transaction_csv_writer import TransactionCSVWriter


class TestTransactionCSVWriter(TestCase):
    """TransactionCSVWriter 단위 테스트"""

    def setUp(self) -> None:
        """테스트 환경 설정"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.csv_path = self.temp_dir / "transactions.csv"
        self.writer = TransactionCSVWriter(self.csv_path)

        # 샘플 데이터
        self.sample_transactions = [
            {
                "complex_id": "111515",
                "complex_name": "헬리오시티",
                "pyeong_type_number": 1,
                "pyeong_name": "84A",
                "trade_type": "A1",
                "trade_type_name": "매매",
                "trade_date": "2025-11-14",
                "trade_year": "2025",
                "floor": 21,
                "deal_price": 1700000000,
                "deposit": 0,
                "monthly_rent": 0,
                "trade_category": "중개거래",
                "is_delete": False,
                "is_renew": False,
            },
            {
                "complex_id": "111515",
                "complex_name": "헬리오시티",
                "pyeong_type_number": 1,
                "pyeong_name": "84A",
                "trade_type": "B1",
                "trade_type_name": "전세",
                "trade_date": "2025-10-20",
                "trade_year": "2025",
                "floor": 15,
                "deal_price": 0,
                "deposit": 800000000,
                "monthly_rent": 0,
                "trade_category": "중개거래",
                "is_delete": False,
                "is_renew": False,
            },
            {
                "complex_id": "111515",
                "complex_name": "헬리오시티",
                "pyeong_type_number": 1,
                "pyeong_name": "84A",
                "trade_type": "B2",
                "trade_type_name": "월세",
                "trade_date": "2025-09-10",
                "trade_year": "2025",
                "floor": 8,
                "deal_price": 0,
                "deposit": 100000000,
                "monthly_rent": 2000000,
                "trade_category": "중개거래",
                "is_delete": True,
                "is_renew": True,
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
            self.assertEqual(reader.fieldnames, TransactionCSVWriter.FIELDNAMES)

    def test_write_creates_file_with_data_and_headers(self) -> None:
        """새 파일에 데이터 작성 테스트"""
        self.writer.write(self.sample_transactions[:1])

        # 파일이 생성되었는지 확인
        self.assertTrue(self.csv_path.exists())

        # 내용 확인
        with open(self.csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # 헤더 확인
            self.assertEqual(reader.fieldnames, TransactionCSVWriter.FIELDNAMES)

            # 데이터 확인
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["complex_id"], "111515")
            self.assertEqual(rows[0]["complex_name"], "헬리오시티")
            self.assertEqual(rows[0]["trade_type_name"], "매매")
            self.assertEqual(rows[0]["deal_price"], "1700000000")

    def test_append_adds_data_to_existing_file(self) -> None:
        """기존 파일에 데이터 추가 테스트"""
        # 첫 번째 데이터 작성
        self.writer.write(self.sample_transactions[:1])

        # 추가 데이터 작성
        self.writer.append(self.sample_transactions[1:2])

        # 파일 내용 확인
        with open(self.csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # 총 2개 행인지 확인 (헤더 제외)
            self.assertEqual(len(rows), 2)

            # 첫 번째 데이터 확인
            self.assertEqual(rows[0]["trade_type_name"], "매매")
            self.assertEqual(rows[0]["deal_price"], "1700000000")

            # 두 번째 데이터 확인
            self.assertEqual(rows[1]["trade_type_name"], "전세")
            self.assertEqual(rows[1]["deposit"], "800000000")

    def test_append_creates_file_if_not_exists(self) -> None:
        """파일이 없을 때 append가 새 파일을 생성하는지 테스트"""
        # 파일이 없는 상태에서 append 호출
        self.assertFalse(self.csv_path.exists())
        self.writer.append(self.sample_transactions[:1])

        # 파일이 생성되었는지 확인
        self.assertTrue(self.csv_path.exists())

        # 내용 확인
        with open(self.csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(reader.fieldnames, TransactionCSVWriter.FIELDNAMES)

    def test_normalize_transaction_handles_missing_fields(self) -> None:
        """누락된 필드가 있는 데이터 정규화 테스트"""
        incomplete_transaction = {
            "complex_id": "111515",
            "complex_name": "헬리오시티",
            # 다른 필드들은 누락
        }

        normalized = self.writer._normalize_transaction(incomplete_transaction)

        # 모든 필드가 있는지 확인
        for field in TransactionCSVWriter.FIELDNAMES:
            self.assertIn(field, normalized)

        # 누락된 필드가 기본값으로 채워졌는지 확인
        self.assertEqual(normalized["pyeong_type_number"], 0)
        self.assertEqual(normalized["deal_price"], 0)
        self.assertEqual(normalized["deposit"], 0)
        self.assertEqual(normalized["monthly_rent"], 0)
        self.assertEqual(normalized["is_delete"], False)
        self.assertEqual(normalized["is_renew"], False)
        self.assertEqual(normalized["trade_type"], "")
        self.assertEqual(normalized["trade_type_name"], "")

    def test_normalize_transaction_handles_boolean_fields(self) -> None:
        """boolean 필드 정규화 테스트"""
        # 다양한 boolean 값 테스트
        test_cases = [
            {"is_delete": True, "is_renew": False},
            {"is_delete": "true", "is_renew": "false"},
            {"is_delete": "True", "is_renew": "False"},
            {"is_delete": 1, "is_renew": 0},
            {"is_delete": None, "is_renew": ""},
        ]

        for i, case in enumerate(test_cases):
            normalized = self.writer._normalize_transaction(case)
            self.assertEqual(
                normalized["is_delete"],
                True if str(case.get("is_delete", "")).lower() in ("true", "1") else False,
                f"Test case {i} failed for is_delete",
            )
            self.assertEqual(
                normalized["is_renew"],
                True if str(case.get("is_renew", "")).lower() in ("true", "1") else False,
                f"Test case {i} failed for is_renew",
            )

    def test_write_with_empty_data_does_nothing(self) -> None:
        """빈 데이터 리스트를 전달했을 때 아무것도 하지 않는지 테스트"""
        self.writer.write([])
        self.assertFalse(self.csv_path.exists())

    def test_append_with_empty_data_does_nothing(self) -> None:
        """빈 데이터 리스트를 append했을 때 아무것도 하지 않는지 테스트"""
        # 먼저 파일을 생성
        self.writer.write_header()

        # 빈 데이터를 append
        original_size = self.csv_path.stat().st_size
        self.writer.append([])

        # 파일 크기가 변하지 않았는지 확인
        self.assertEqual(self.csv_path.stat().st_size, original_size)

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
        self.writer.write(self.sample_transactions[:1])
        original_size = self.csv_path.stat().st_size

        # ensure_file_exists 호출
        self.writer.ensure_file_exists()

        # 파일 크기가 변하지 않았는지 확인
        self.assertEqual(self.csv_path.stat().st_size, original_size)

    def test_all_trade_types_in_sample_data(self) -> None:
        """모든 거래 유형(매매/전세/월세)이 올바르게 저장되는지 테스트"""
        self.writer.write(self.sample_transactions)

        with open(self.csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            # 3개의 거래내역이 있는지 확인
            self.assertEqual(len(rows), 3)

            # 각 거래 유형 확인
            trade_types = [row["trade_type_name"] for row in rows]
            self.assertIn("매매", trade_types)
            self.assertIn("전세", trade_types)
            self.assertIn("월세", trade_types)

            # 매매 거래 확인
            deal_row = next(row for row in rows if row["trade_type_name"] == "매매")
            self.assertEqual(deal_row["deal_price"], "1700000000")
            self.assertEqual(deal_row["deposit"], "0")

            # 전세 거래 확인
            lease_row = next(row for row in rows if row["trade_type_name"] == "전세")
            self.assertEqual(lease_row["deal_price"], "0")
            self.assertEqual(lease_row["deposit"], "800000000")

            # 월세 거래 확인
            rent_row = next(row for row in rows if row["trade_type_name"] == "월세")
            self.assertEqual(rent_row["deal_price"], "0")
            self.assertEqual(rent_row["deposit"], "100000000")
            self.assertEqual(rent_row["monthly_rent"], "2000000")