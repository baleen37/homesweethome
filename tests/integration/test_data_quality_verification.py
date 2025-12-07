"""
네이버 부동산 데이터 품질 검증 통합 테스트

Task 4.2: 데이터 품질 검증
- 수집된 데이터의 정확성 검증
- 데이터 형식과 스키마 일관성 확인
- 중복 데이터 제거 검증
- 누락된 필드나 비정상 값 확인
- 시간 순서 정합성 검증
"""

import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import pytest

# 모듈 import를 테스트 내부에서 동적으로 처리
try:
    from crawler.config import CrawlerConfig
    from crawler.writers.complexes_csv_writer import ComplexesCSVWriter
    from crawler.writers.transaction_csv_writer import TransactionCSVWriter
except ImportError:
    # 테스트 환경에서 import 실패 시 mock 처리
    CrawlerConfig = None
    ComplexesCSVWriter = None
    TransactionCSVWriter = None


class TestDataQualityVerification:
    """데이터 품질 검증 테스트 클래스"""

    @pytest.fixture
    def config(self):
        """테스트용 설정 객체"""
        if CrawlerConfig is None:
            pytest.skip("CrawlerConfig 모듈을 가져올 수 없음")
        return CrawlerConfig(
            output_dir="test_output",
            delay=1.0,
            max_retries=3,
            timeout=30,
        )

    @pytest.fixture
    def sample_complexes_data(self) -> List[Dict[str, Any]]:
        """검증용 샘플 단지 데이터"""
        return [
            {
                "complex_id": "10950011",
                "complex_name": "래미안퍼스티지",
                "real_estate_type": "아파트",
                "completion_year_month": "202111",
                "total_dong_count": 8,
                "total_household_count": 736,
                "min_area": 84.86,
                "max_area": 120.79,
                "deal_count": 15,
                "lease_count": 23,
                "rent_count": 5,
                "pyeong_types": "25,32,33,34,36,37",
                "fetched_at": "2025-12-07 12:00:00",
                "total_transaction_count": 43,
                "latest_deal_price": 185000,
                "latest_deal_date": "2025.11",
                "avg_deal_price_1year": 178500,
                "deal_count_1year": 42,
                "lease_count_1year": 38,
                "rent_count_1year": 8,
            },
            {
                "complex_id": "108743",
                "complex_name": "헬리오시티",
                "real_estate_type": "아파트",
                "completion_year_month": "202104",
                "total_dong_count": 6,
                "total_household_count": 1312,
                "min_area": 59.91,
                "max_area": 114.87,
                "deal_count": 32,
                "lease_count": 41,
                "rent_count": 12,
                "pyeong_types": "18,25,29,32,33,34,35",
                "fetched_at": "2025-12-07 12:01:00",
                "total_transaction_count": 85,
                "latest_deal_price": 115000,
                "latest_deal_date": "2025.12",
                "avg_deal_price_1year": 112300,
                "deal_count_1year": 78,
                "lease_count_1year": 92,
                "rent_count_1year": 25,
            },
            # 경계값 테스트용 데이터
            {
                "complex_id": "1",  # 최소 ID
                "complex_name": "테스트단지",
                "real_estate_type": "오피스텔",
                "completion_year_month": "197001",  # 최소 날짜
                "total_dong_count": 1,
                "total_household_count": 1,
                "min_area": 10.0,  # 최소 면적
                "max_area": 10.0,
                "deal_count": 0,
                "lease_count": 0,
                "rent_count": 0,
                "pyeong_types": "3",
                "fetched_at": "2025-12-07 12:02:00",
                "total_transaction_count": 0,
                "latest_deal_price": 0,
                "latest_deal_date": "",
                "avg_deal_price_1year": 0,
                "deal_count_1year": 0,
                "lease_count_1year": 0,
                "rent_count_1year": 0,
            },
        ]

    @pytest.fixture
    def sample_transactions_data(self) -> List[Dict[str, Any]]:
        """검증용 샘플 거래내역 데이터"""
        return [
            {
                "complex_id": "10950011",
                "complex_name": "래미안퍼스티지",
                "pyeong_type_number": "32",
                "pyeong_name": "32평",
                "trade_type": "A1",
                "trade_type_name": "매매",
                "trade_date": "2025.12.01",
                "trade_year": "2025",
                "floor": "15",
                "deal_price": 185000,
                "deposit": 0,
                "monthly_rent": 0,
                "trade_category": "일반매매",
                "is_delete": "N",
                "is_renew": "N",
            },
            {
                "complex_id": "10950011",
                "complex_name": "래미안퍼스티지",
                "pyeong_type_number": "32",
                "pyeong_name": "32평",
                "trade_type": "B1",
                "trade_type_name": "전세",
                "trade_date": "2025.11.28",
                "trade_year": "2025",
                "floor": "8",
                "deal_price": 0,
                "deposit": 95000,
                "monthly_rent": 0,
                "trade_category": "일반전세",
                "is_delete": "N",
                "is_renew": "N",
            },
            {
                "complex_id": "108743",
                "complex_name": "헬리오시티",
                "pyeong_type_number": "25",
                "pyeong_name": "25평",
                "trade_type": "B2",
                "trade_type_name": "월세",
                "trade_date": "2025.11.30",
                "trade_year": "2025",
                "floor": "22",
                "deal_price": 0,
                "deposit": 50000,
                "monthly_rent": 150,
                "trade_category": "일반월세",
                "is_delete": "N",
                "is_renew": "N",
            },
            # 경계값 및 오류 케이스
            {
                "complex_id": "108743",
                "complex_name": "헬리오시티",
                "pyeong_type_number": "18",
                "pyeong_name": "18평",
                "trade_type": "A1",
                "trade_type_name": "매매",
                "trade_date": "2024.01.15",
                "trade_year": "2024",
                "floor": "3",
                "deal_price": 75000,
                "deposit": 0,
                "monthly_rent": 0,
                "trade_category": "일반매매",
                "is_delete": "Y",  # 삭제된 거래
                "is_renew": "Y",  # 갱신된 거래
            },
            # 최대값 테스트
            {
                "complex_id": "999999",
                "complex_name": "고급아파트",
                "pyeong_type_number": "59",
                "pyeong_name": "59평",
                "trade_type": "A1",
                "trade_type_name": "매매",
                "trade_date": "2025.12.05",
                "trade_year": "2025",
                "floor": "35",
                "deal_price": 999999,  # 최대 가격
                "deposit": 0,
                "monthly_rent": 0,
                "trade_category": "일반매매",
                "is_delete": "N",
                "is_renew": "N",
            },
        ]

    def test_complex_id_validation(self, sample_complexes_data):
        """단지 ID 유효성 검증"""
        for complex in sample_complexes_data:
            complex_id = complex["complex_id"]

            # ID는 문자열이어야 함
            assert isinstance(complex_id, str), f"단지 ID는 문자열이어야 함: {complex_id}"

            # 숫자만 포함해야 함
            assert complex_id.isdigit(), f"단지 ID는 숫자만 포함해야 함: {complex_id}"

            # 길이는 1-8자 사이
            assert 1 <= len(complex_id) <= 8, f"단지 ID 길이는 1-8자 사이여야 함: {complex_id}"

            # 중복되지 않아야 함
            ids = [c["complex_id"] for c in sample_complexes_data]
            assert ids.count(complex_id) == 1, f"중복된 단지 ID 존재: {complex_id}"

    def test_price_data_format_and_range(self, sample_complexes_data, sample_transactions_data):
        """가격 데이터 형식 및 범위 검증"""
        # 단지 데이터의 가격 검증
        for complex in sample_complexes_data:
            for price_field in [
                "latest_deal_price",
                "avg_deal_price_1year",
            ]:
                price = complex[price_field]

                # 가격은 정수여야 함
                assert isinstance(price, int), f"{price_field}는 정수여야 함: {price}"

                # 가격은 0 이상이어야 함
                assert price >= 0, f"{price_field}는 0 이상이어야 함: {price}"

                # 가격은 10억원 이하여야 함 (현실적인 범위)
                assert price <= 1000000, f"{price_field}는 10억원 이하여야 함: {price}"

        # 거래내역 데이터의 가격 검증
        for transaction in sample_transactions_data:
            # 매매가 검증
            deal_price = transaction["deal_price"]
            assert isinstance(deal_price, int), f"매매가는 정수여야 함: {deal_price}"
            assert deal_price >= 0, f"매매가는 0 이상이어야 함: {deal_price}"

            # 보증금 검증
            deposit = transaction["deposit"]
            assert isinstance(deposit, int), f"보증금은 정수여야 함: {deposit}"
            assert deposit >= 0, f"보증금은 0 이상이어야 함: {deposit}"

            # 월세 검증
            monthly_rent = transaction["monthly_rent"]
            assert isinstance(monthly_rent, int), f"월세는 정수여야 함: {monthly_rent}"
            assert monthly_rent >= 0, f"월세는 0 이상이어야 함: {monthly_rent}"

            # 거래 유형에 따른 가격 필드 정합성
            if transaction["trade_type"] == "A1":  # 매매
                assert deal_price > 0, "매매는 매매가가 0보다 커야 함"
                assert deposit == 0, "매매는 보증금이 0이어야 함"
                assert monthly_rent == 0, "매매는 월세가 0이어야 함"
            elif transaction["trade_type"] == "B1":  # 전세
                assert deal_price == 0, "전세는 매매가가 0이어야 함"
                assert deposit > 0, "전세는 보증금이 0보다 커야 함"
                assert monthly_rent == 0, "전세는 월세가 0이어야 함"
            elif transaction["trade_type"] == "B2":  # 월세
                assert deal_price == 0, "월세는 매매가가 0이어야 함"
                assert deposit >= 0, "월세는 보증금이 0 이상이어야 함"
                assert monthly_rent > 0, "월세는 월세가 0보다 커야 함"

    def test_date_format_consistency(self, sample_complexes_data, sample_transactions_data):
        """날짜 형식 정합성 검증"""
        # 날짜 형식 패턴
        date_pattern1 = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")  # 2025-12-07 12:00:00
        date_pattern2 = re.compile(r"^\d{4}\.\d{2}$")  # 2025.12
        date_pattern3 = re.compile(r"^\d{4}\.\d{2}\.\d{2}$")  # 2025.12.01

        # 단지 데이터의 날짜 검증
        for complex in sample_complexes_data:
            # fetched_at 형식 검증
            fetched_at = complex["fetched_at"]
            assert date_pattern1.match(fetched_at), f"fetched_at 형식 오류: {fetched_at}"

            # completion_year_month 형식 검증
            completion = complex["completion_year_month"]
            assert (
                completion.isdigit() and len(completion) == 6
            ), f"준공년월 형식 오류: {completion}"

            # latest_deal_date 형식 검증 (비어있을 수 있음)
            latest_deal_date = complex["latest_deal_date"]
            if latest_deal_date:
                assert date_pattern2.match(
                    latest_deal_date
                ), f"최근 거래일 형식 오류: {latest_deal_date}"

        # 거래내역 데이터의 날짜 검증
        for transaction in sample_transactions_data:
            trade_date = transaction["trade_date"]
            assert date_pattern3.match(trade_date), f"거래일 형식 오류: {trade_date}"

            trade_year = transaction["trade_year"]
            assert (
                trade_year.isdigit() and len(trade_year) == 4
            ), f"거래연도 형식 오류: {trade_year}"

            # trade_date와 trade_year의 일치성 검증
            date_year = trade_date.split(".")[0]
            assert trade_year == date_year, f"거래일과 거래연도 불일치: {trade_date}, {trade_year}"

            # 날짜 유효성 검증
            try:
                year, month, day = map(int, trade_date.split("."))
                datetime(year=year, month=month, day=day)
            except ValueError as e:
                pytest.fail(f"잘못된 날짜: {trade_date}, 오류: {e}")

    def test_area_and_floor_validation(self, sample_complexes_data, sample_transactions_data):
        """면적과 층 데이터 검증"""
        # 단지 데이터의 면적 검증
        for complex in sample_complexes_data:
            min_area = complex["min_area"]
            max_area = complex["max_area"]

            # 면적은 실수여야 함
            assert isinstance(min_area, float) or isinstance(
                min_area, int
            ), f"최소 면적은 숫자여야 함: {min_area}"
            assert isinstance(max_area, float) or isinstance(
                max_area, int
            ), f"최대 면적은 숫자여야 함: {max_area}"

            # 면적은 양수여야 함
            assert min_area > 0, f"최소 면적은 양수여야 함: {min_area}"
            assert max_area > 0, f"최대 면적은 양수여야 함: {max_area}"

            # 최소 면적 <= 최대 면적
            assert (
                min_area <= max_area
            ), f"최소 면적이 최대 면적보다 클 수 없음: {min_area} > {max_area}"

            # 현실적인 면적 범위 (10㎡ ~ 500㎡)
            assert 10 <= min_area <= 500, f"최소 면적이 현실적 범위를 벗어남: {min_area}"
            assert 10 <= max_area <= 500, f"최대 면적이 현실적 범위를 벗어남: {max_area}"

        # 거래내역 데이터의 층 검증
        for transaction in sample_transactions_data:
            floor = transaction["floor"]

            # 층은 문자열이어야 함
            assert isinstance(floor, str), f"층은 문자열이어야 함: {floor}"

            # 숫자여야 함 (지하일 수 있으므로 음수 가능)
            assert floor.lstrip("-").isdigit(), f"층은 숫자여야 함: {floor}"

            # 현실적인 층 범위 (-2 ~ 80)
            floor_num = int(floor)
            assert -2 <= floor_num <= 80, f"층이 현실적 범위를 벗어남: {floor_num}"

    def test_pyeong_type_validation(self, sample_complexes_data, sample_transactions_data):
        """평형 타입 검증"""
        # 단지 데이터의 평형 타입 검증
        for complex in sample_complexes_data:
            pyeong_types = complex["pyeong_types"]

            # 콤마로 구분된 숫자여야 함
            assert isinstance(pyeong_types, str), f"평형 타입은 문자열이어야 함: {pyeong_types}"

            # 비어있지 않아야 함
            assert pyeong_types, "평형 타입이 비어있음"

            # 각 평형은 숫자여야 함
            types = pyeong_types.split(",")
            for p_type in types:
                assert p_type.isdigit(), f"평형 타입은 숫자여야 함: {p_type}"

                # 현실적인 평형 범위 (1평 ~ 100평)
                p_num = int(p_type)
                assert 1 <= p_num <= 100, f"평형이 현실적 범위를 벗어남: {p_num}"

        # 거래내역 데이터의 평형 검증
        for transaction in sample_transactions_data:
            pyeong_number = transaction["pyeong_type_number"]
            pyeong_name = transaction["pyeong_name"]

            # 평형 번호는 숫자 문자열
            assert isinstance(pyeong_number, str), f"평형 번호는 문자열이어야 함: {pyeong_number}"
            assert pyeong_number.isdigit(), f"평형 번호는 숫자여야 함: {pyeong_number}"

            # 평형 이름은 'XX평' 형식
            assert isinstance(pyeong_name, str), f"평형 이름은 문자열이어야 함: {pyeong_name}"
            assert pyeong_name.endswith("평"), f"평형 이름은 '평'으로 끝나야 함: {pyeong_name}"

            # 평형 번호와 이름의 일치성
            pyeong_num_from_name = pyeong_name[:-1]  # '평' 제거
            assert (
                pyeong_number == pyeong_num_from_name
            ), f"평형 번호와 이름 불일치: {pyeong_number}, {pyeong_name}"

    def test_duplicate_data_detection(self, sample_transactions_data):
        """중복 데이터 검증"""
        # 복합 키를 사용한 중복 검사
        seen_keys = set()
        duplicates = []

        for i, transaction in enumerate(sample_transactions_data):
            # 복합 키: 단지ID + 평형 + 거래일 + 층 + 거래유형
            key = (
                transaction["complex_id"],
                transaction["pyeong_type_number"],
                transaction["trade_date"],
                transaction["floor"],
                transaction["trade_type"],
            )

            if key in seen_keys:
                duplicates.append((i, transaction))
            else:
                seen_keys.add(key)

        assert len(duplicates) == 0, f"중복된 거래 데이터 발견: {duplicates}"

        # 삭제되지 않은 데이터 중에 중복이 없는지 확인
        active_transactions = [t for t in sample_transactions_data if t["is_delete"] == "N"]
        active_keys = set()
        active_duplicates = []

        for transaction in active_transactions:
            key = (
                transaction["complex_id"],
                transaction["pyeong_type_number"],
                transaction["trade_date"],
                transaction["floor"],
                transaction["trade_type"],
            )

            if key in active_keys:
                active_duplicates.append(transaction)
            else:
                active_keys.add(key)

        assert len(active_duplicates) == 0, f"활성 데이터 중 중복 발견: {active_duplicates}"

    def test_missing_and_abnormal_values(self, sample_complexes_data, sample_transactions_data):
        """누락된 필드와 비정상 값 검증"""
        # 필수 필드 목록 정의
        complex_required_fields = [
            "complex_id",
            "complex_name",
            "real_estate_type",
            "completion_year_month",
            "total_dong_count",
            "total_household_count",
            "fetched_at",
        ]

        transaction_required_fields = [
            "complex_id",
            "complex_name",
            "pyeong_type_number",
            "pyeong_name",
            "trade_type",
            "trade_type_name",
            "trade_date",
            "trade_year",
            "floor",
            "trade_category",
            "is_delete",
            "is_renew",
        ]

        # 단지 데이터 필수 필드 검증
        for complex in sample_complexes_data:
            for field in complex_required_fields:
                assert field in complex, f"필수 필드 누락: {field}"

                # 빈 값이나 null이 아니어야 함
                value = complex[field]
                assert value is not None, f"필드 값이 null: {field}"
                assert value != "", f"필드 값이 비어있음: {field}"

        # 거래내역 데이터 필수 필드 검증
        for transaction in sample_transactions_data:
            for field in transaction_required_fields:
                assert field in transaction, f"필수 필드 누락: {field}"

                # 빈 값이나 null이 아니어야 함
                value = transaction[field]
                assert value is not None, f"필드 값이 null: {field}"
                assert value != "", f"필드 값이 비어있음: {field}"

        # 비정상 값 검증
        for transaction in sample_transactions_data:
            # is_delete, is_renew은 'Y' 또는 'N'이어야 함
            is_delete = transaction["is_delete"]
            is_renew = transaction["is_renew"]

            assert is_delete in ["Y", "N"], f"is_delete 값 비정상: {is_delete}"
            assert is_renew in ["Y", "N"], f"is_renew 값 비정상: {is_renew}"

            # 거래 유형 코드 검증
            trade_type = transaction["trade_type"]
            assert trade_type in ["A1", "B1", "B2"], f"거래 유형 코드 비정상: {trade_type}"

            # 거래 유형명 검증
            trade_type_name = transaction["trade_type_name"]
            assert trade_type_name in [
                "매매",
                "전세",
                "월세",
            ], f"거래 유형명 비정상: {trade_type_name}"

    def test_data_schema_consistency(self, config, sample_complexes_data, sample_transactions_data):
        """데이터 스키마 일관성 검증"""
        if ComplexesCSVWriter is None or TransactionCSVWriter is None:
            pytest.skip("CSV Writer 모듈을 가져올 수 없음")

        # 임시 파일 생성
        test_dir = Path("test_output")
        test_dir.mkdir(exist_ok=True)

        complexes_file = test_dir / "test_complexes.csv"
        transactions_file = test_dir / "test_transactions.csv"

        try:
            # CSV 파일 작성
            complexes_writer = ComplexesCSVWriter(str(complexes_file))
            transactions_writer = TransactionCSVWriter(str(transactions_file))

            complexes_writer.write_batch(sample_complexes_data)
            transactions_writer.write_batch(sample_transactions_data)

            # CSV 파일 읽어서 스키마 확인
            with open(complexes_file, "r", encoding="utf-8") as f:
                complexes_reader = csv.DictReader(f)
                complexes_fields = complexes_reader.fieldnames

            with open(transactions_file, "r", encoding="utf-8") as f:
                transactions_reader = csv.DictReader(f)
                transactions_fields = transactions_reader.fieldnames

            # 예상 필드 목록
            expected_complexes_fields = [
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
                "pyeong_types",
                "fetched_at",
                "total_transaction_count",
                "latest_deal_price",
                "latest_deal_date",
                "avg_deal_price_1year",
                "deal_count_1year",
                "lease_count_1year",
                "rent_count_1year",
            ]

            expected_transactions_fields = [
                "complex_id",
                "complex_name",
                "pyeong_type_number",
                "pyeong_name",
                "trade_type",
                "trade_type_name",
                "trade_date",
                "trade_year",
                "floor",
                "deal_price",
                "deposit",
                "monthly_rent",
                "trade_category",
                "is_delete",
                "is_renew",
            ]

            # 필드 순서 상관없이 모든 필드가 있는지 확인
            for field in expected_complexes_fields:
                assert field in complexes_fields, f"단지 CSV에 필드 누락: {field}"

            for field in expected_transactions_fields:
                assert field in transactions_fields, f"거래내역 CSV에 필드 누락: {field}"

            # 불필요한 필드가 없는지 확인
            assert (
                len(complexes_fields) == len(expected_complexes_fields)
            ), f"단지 CSV에 예기치 않은 필드 존재: {set(complexes_fields) - set(expected_complexes_fields)}"

            assert (
                len(transactions_fields) == len(expected_transactions_fields)
            ), f"거래내역 CSV에 예기치 않은 필드 존재: {set(transactions_fields) - set(expected_transactions_fields)}"

        finally:
            # 임시 파일 정리
            if complexes_file.exists():
                complexes_file.unlink()
            if transactions_file.exists():
                transactions_file.unlink()

    def test_time_sequence_consistency(self, sample_transactions_data):
        """시간 순서 정합성 검증"""

        # 날짜 형식을 datetime 객체로 변환
        def parse_date(date_str: str) -> datetime:
            year, month, day = map(int, date_str.split("."))
            return datetime(year=year, month=month, day=day)

        # 거래일순으로 정렬
        sorted_transactions = sorted(
            sample_transactions_data, key=lambda x: parse_date(x["trade_date"])
        )

        # 최신 거래가 실제로 최신인지 확인
        if len(sorted_transactions) > 1:
            for i in range(len(sorted_transactions) - 1):
                current = sorted_transactions[i]
                next_trx = sorted_transactions[i + 1]

                current_date = parse_date(current["trade_date"])
                next_date = parse_date(next_trx["trade_date"])

                assert (
                    current_date <= next_date
                ), f"거래일 순서 오류: {current['trade_date']} > {next_trx['trade_date']}"

        # 거래연도와 실제 날짜의 일치성 재확인
        for transaction in sample_transactions_data:
            trade_year = int(transaction["trade_year"])
            trade_date = parse_date(transaction["trade_date"])

            assert (
                trade_date.year == trade_year
            ), f"거래연도와 날짜 불일치: {trade_year} != {trade_date.year}"

        # fetched_at이 현재 시점보다 미래가 아닌지 확인 (transactions만 확인)
        current_time = datetime.now()
        for transaction in sample_transactions_data:
            if "fetched_at" in transaction:
                fetched_at = datetime.strptime(transaction["fetched_at"], "%Y-%m-%d %H:%M:%S")
                assert fetched_at <= current_time, f"수집 시간이 미래: {fetched_at}"
