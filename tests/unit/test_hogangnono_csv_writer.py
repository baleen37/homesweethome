"""단위 테스트 for HogangnonoCSVWriter"""

import csv
import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from crawler.writers.hogangnono_csv_writer import HogangnonoCSVWriter

# Import test setup to configure path and mocks


class TestHogangnonoCSVWriter:
    """HogangnonoCSVWriter 테스트 클래스"""

    @pytest.fixture
    def temp_output_dir(self):
        """임시 출력 디렉토리"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def writer(self, temp_output_dir):
        """HogangnonoCSVWriter 인스턴스"""
        return HogangnonoCSVWriter(str(temp_output_dir))

    @pytest.fixture
    def sample_complex_data(self):
        """샘플 단지 데이터"""
        return [
            {
                "aptSeq": "APT_123",
                "aptName": "테스트아파트",
                "address": "서울특별시 강남구 테스트동",
                "buildYear": "2020",
                "dealCnt": 50,
                "realPrice": "45000",
                "realPriceYear": "2024",
                "realPriceQuarter": "4",
                "recentDealPrice": "48000",
                "recentDealDate": "2024-12-01",
                "lng": "127.0628",
                "lat": "37.5326",
                "householdCnt": "1500",
                "parkingCnt": "1200",
            },
            {
                "aptSeq": "APT_456",
                "aptName": "새로운아파트",
                "address": "경기도 성남시 분당구 분당동",
                "buildYear": "2022",
                "dealCnt": 30,
                "realPrice": "38000",
                "realPriceYear": "2024",
                "realPriceQuarter": "4",
                "recentDealPrice": "40000",
                "recentDealDate": "2024-11-25",
                "lng": "127.1055",
                "lat": "37.4422",
                "householdCnt": "800",
                "parkingCnt": "600",
            },
        ]

    @pytest.fixture
    def sample_transaction_data(self):
        """샘플 거래내역 데이터"""
        return [
            {
                "aptSeq": "APT_123",
                "aptName": "테스트아파트",
                "dong": "테스트동",
                "ho": "101",
                "pyeong": "33",
                "pyeongName": "33㎡",
                "floor": "5/25",
                "dealType": "매매",
                "dealAmount": "45000",
                "deposit": "",
                "monthlyRent": "",
                "dealDate": "2024-11-25",
                "area": "33.12",
                "pyeongTypeNumber": "33",
            },
            {
                "aptSeq": "APT_123",
                "aptName": "테스트아파트",
                "dong": "테스트동",
                "ho": "201",
                "pyeong": "59",
                "pyeongName": "59㎡",
                "floor": "12/25",
                "dealType": "전세",
                "dealAmount": "",
                "deposit": "30000",
                "monthlyRent": "",
                "dealDate": "2024-11-20",
                "area": "58.92",
                "pyeongTypeNumber": "59",
            },
            {
                "aptSeq": "APT_456",
                "aptName": "새로운아파트",
                "dong": "분당동",
                "ho": "305",
                "pyeong": "84",
                "pyeongName": "84㎡",
                "floor": "15/30",
                "dealType": "월세",
                "dealAmount": "",
                "deposit": "80000",
                "monthlyRent": "400",
                "dealDate": "2024-11-15",
                "area": "83.76",
                "pyeongTypeNumber": "84",
            },
        ]

    def test_init(self, writer, temp_output_dir):
        """HogangnonoCSVWriter 초기화 테스트"""
        assert writer.output_dir == temp_output_dir
        assert writer.complexes_path == temp_output_dir / "complexes.csv"
        assert writer.transactions_path == temp_output_dir / "transactions.csv"

    def test_save_complexes(self, writer, sample_complex_data):
        """단지 데이터 저장 테스트"""
        # 첫 저장 (헤더 포함)
        writer.save_complexes(sample_complex_data)

        # 파일 확인
        assert writer.complexes_path.exists()

        # CSV 내용 확인
        with open(writer.complexes_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            assert len(rows) == len(sample_complex_data)

            # 첫 번째 행 검증
            first_row = rows[0]
            assert first_row["complex_id"] == "APT_123"
            assert first_row["complex_name"] == "테스트아파트"
            assert first_row["completion_year_month"] == "20200101"
            assert first_row["total_household_count"] == "1500"  # CSV는 문자열 저장
            assert first_row["real_estate_type"] == "아파트"
            assert first_row["fetched_at"] != ""

    def test_save_transactions(self, writer, sample_transaction_data):
        """거래내역 데이터 저장 테스트"""
        # 첫 저장 (헤더 포함)
        writer.save_transactions(sample_transaction_data)

        # 파일 확인
        assert writer.transactions_path.exists()

        # CSV 내용 확인
        with open(writer.transactions_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            assert len(rows) == len(sample_transaction_data)

            # 첫 번째 행 검증 (매매)
            first_row = rows[0]
            assert first_row["complex_id"] == "APT_123"
            assert first_row["complex_name"] == "테스트아파트"
            assert first_row["trade_type"] == "매매"
            assert first_row["trade_type_name"] == "일반거래"
            assert first_row["deal_price"] == "45000"  # CSV는 문자열 저장
            assert first_row["deposit"] == "0"
            assert first_row["monthly_rent"] == "0"
            assert first_row["is_delete"] == "false"
            assert first_row["is_renew"] == "false"

            # 두 번째 행 검증 (전세)
            second_row = rows[1]
            assert second_row["trade_type"] == "전세"
            assert second_row["deposit"] == "30000"  # CSV는 문자열 저장
            assert second_row["monthly_rent"] == "0"

            # 세 번째 행 검증 (월세)
            third_row = rows[2]
            assert third_row["trade_type"] == "월세"
            assert third_row["deposit"] == "80000"  # CSV는 문자열 저장
            assert third_row["monthly_rent"] == "400"

    def test_append_data(self, writer, sample_complex_data):
        """데이터 추가 저장 테스트"""
        # 첫 저장
        writer.save_complexes(sample_complex_data[:1])

        # 추가 저장 (헤더 없이)
        writer.save_complexes(sample_complex_data[1:])

        # 전체 레코드 수 확인
        stats = writer.get_stats()
        assert stats["complexes_record_count"] == len(sample_complex_data)

    def test_transform_complex_to_naver_format(self, writer, sample_complex_data):
        """단지 데이터 변환 테스트"""
        transformed = writer.transform_complex_to_naver_format(sample_complex_data[0])

        # 필드 존재 확인
        assert all(field in transformed for field in writer.COMPLEXES_FIELDNAMES)

        # 타입 변환 확인
        assert isinstance(transformed["complex_id"], str)
        assert isinstance(transformed["total_household_count"], str)  # 문자열로 변환
        assert isinstance(transformed["deal_count"], str)
        assert isinstance(transformed["min_area"], str)
        assert transformed["completion_year_month"] == "20200101"

    def test_transform_transaction_to_naver_format(self, writer, sample_transaction_data):
        """거래내역 데이터 변환 테스트"""
        transformed = writer.transform_transaction_to_naver_format(sample_transaction_data[0])

        # 필드 존재 확인
        assert all(field in transformed for field in writer.TRANSACTIONS_FIELDNAMES)

        # 타입 변환 확인
        assert isinstance(transformed["complex_id"], str)
        assert isinstance(transformed["floor"], int)
        assert isinstance(transformed["deal_price"], int)
        assert isinstance(transformed["deposit"], int)
        assert isinstance(transformed["monthly_rent"], int)
        assert isinstance(transformed["trade_year"], int)
        assert not transformed["is_delete"]
        assert not transformed["is_renew"]

    def test_parse_floor(self, writer):
        """층수 파싱 테스트"""
        assert writer._parse_floor("5") == 5
        assert writer._parse_floor("5/15") == 5
        assert writer._parse_floor("B1") == 0  # B1은 지하 1층이지만 0으로 처리
        assert writer._parse_floor("") == 0
        assert writer._parse_floor("15") == 15
        assert writer._parse_floor("15F") == 15
        assert writer._parse_floor("지하1층") == 0  # 숫자가 없으면 0

    def test_parse_money_amount(self, writer):
        """금액 파싱 테스트"""
        assert writer._parse_money_amount("45,000") == 45000
        assert writer._parse_money_amount("45억") == 45
        assert writer._parse_money_amount("30000") == 30000
        assert writer._parse_money_amount("") == 0
        assert writer._parse_money_amount("50") == 50

    def test_trade_type_mapping(self, writer):
        """거래 유형 매핑 테스트"""
        # 매매
        transformed = writer.transform_transaction_to_naver_format(
            {"dealType": "매매", "dealAmount": "45000"}
        )
        assert transformed["trade_type"] == "매매"

        # 전세
        transformed = writer.transform_transaction_to_naver_format(
            {"dealType": "전세", "deposit": "30000"}
        )
        assert transformed["trade_type"] == "전세"

        # 월세
        transformed = writer.transform_transaction_to_naver_format(
            {"dealType": "월세", "deposit": "80000", "monthlyRent": "400"}
        )
        assert transformed["trade_type"] == "월세"

    def test_deal_date_parsing(self, writer):
        """거래일 파싱 테스트"""
        # YYYY-MM-DD 형식
        transformed = writer.transform_transaction_to_naver_format({"dealDate": "2024-11-25"})
        assert transformed["trade_year"] == 2024
        assert transformed["trade_date"] == "2024-11-25"

        # YYYY.MM.DD 형식
        transformed = writer.transform_transaction_to_naver_format({"dealDate": "2024.11.25"})
        assert transformed["trade_year"] == 2024
        assert transformed["trade_date"] == "2024-11-25"

        # 없는 경우
        transformed = writer.transform_transaction_to_naver_format({})
        assert transformed["trade_year"] == datetime.now().year
        assert transformed["trade_date"] == ""

    def test_get_stats(self, writer, sample_complex_data, sample_transaction_data):
        """통계 정보 테스트"""
        # 데이터 저장
        writer.save_complexes(sample_complex_data)
        writer.save_transactions(sample_transaction_data)

        # 통계 확인
        stats = writer.get_stats()

        assert stats["complexes_record_count"] == len(sample_complex_data)
        assert stats["transactions_record_count"] == len(sample_transaction_data)
        assert stats["complexes_file_size"] > 0
        assert stats["transactions_file_size"] > 0

    def test_save_from_json_file(self, writer, temp_output_dir):
        """JSON 파일에서 데이터 읽기 테스트"""
        # 테스트용 JSON 파일 생성
        test_data = {
            "data": {
                "aptSeq": "APT_JSON",
                "aptName": "JSON 테스트 아파트",
                "address": "JSON 주소",
                "buildYear": "2023",
                "dealCnt": 25,
                "householdCnt": 1000,
                "parkingCnt": 800,
            }
        }

        json_file = temp_output_dir / "test.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)

        # JSON 파일에서 데이터 읽어서 저장
        writer.save_from_json_file(str(json_file), data_type="complex")

        # 결과 확인
        stats = writer.get_stats()
        assert stats["complexes_record_count"] == 1

    def test_empty_data_handling(self, writer):
        """빈 데이터 처리 테스트"""
        # 빈 데이터 저장 시 오류 없음
        writer.save_complexes([])
        writer.save_transactions([])

        # 파일이 생성되지 않음
        assert not writer.complexes_path.exists()
        assert not writer.transactions_path.exists()

    def test_output_dir_creation(self, temp_output_dir):
        """출력 디렉토리 생성 테스트"""
        # 서브 디렉토리 지정
        sub_dir = temp_output_dir / "sub" / "dir"
        writer = HogangnonoCSVWriter(str(sub_dir))

        sample_data = [
            {
                "aptSeq": "APT_SUB",
                "aptName": "서브 디렉토리 테스트",
                "address": "주소",
                "buildYear": "2020",
                "dealCnt": 10,
                "householdCnt": 100,
                "parkingCnt": 80,
            }
        ]

        writer.save_complexes(sample_data)

        # 디렉토리와 파일이 생성되었는지 확인
        assert sub_dir.exists()
        assert writer.complexes_path.exists()

    def test_normalize_complex_data(self, writer, sample_complex_data):
        """단지 데이터 정규화 테스트"""
        # 필드 누락된 데이터 테스트
        incomplete_data = {
            "aptSeq": "APT_INCOMPLETE"
            # 필드 대부분 누락
        }

        transformed = writer.transform_complex_to_naver_format(incomplete_data)

        # 모든 필드에 기본값이 설정되었는지 확인
        # 필드 매핑을 통해 aptSeq가 complex_id로 매핑됨
        assert transformed["complex_id"] == "APT_INCOMPLETE"
        assert transformed["complex_name"] == ""  # aptName이 없으므로 빈 문자열
        assert transformed["real_estate_type"] == "아파트"  # 기본값
        assert transformed["total_dong_count"] == "1"  # 기본값 (문자열)
        assert transformed["completion_year_month"] == ""
        assert transformed["fetched_at"] != ""

    def test_normalize_transaction_data(self, writer):
        """거래내역 데이터 정규화 테스트"""
        # 필드 누락된 데이터 테스트
        incomplete_data = {
            "aptSeq": "APT_INCOMPLETE",
            "dealType": "매매",
            # 필드 대부분 누락
        }

        transformed = writer.transform_transaction_to_naver_format(incomplete_data)

        # 기본값 확인
        assert transformed["complex_name"] == ""
        assert transformed["deal_price"] == 0
        assert transformed["deposit"] == 0
        assert transformed["floor"] == 0
        assert not transformed["is_delete"]
        assert not transformed["is_renew"]
