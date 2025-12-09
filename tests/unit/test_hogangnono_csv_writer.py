"""단위 테스트 for HogangnonoCSVWriter"""

import csv
import json
import pytest
import tempfile
from pathlib import Path

from crawler.writers.hogangnono_csv_writer import HogangnonoCSVWriter


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
                "id": "APT_123",
                "name": "테스트아파트",
                "address": "서울특별시 강남구 테스트동",
                "build_year": "2020",
                "lat": "37.5326",
                "lng": "127.0628",
                "households": "1500",
                "floors": "20",
            },
            {
                "id": "APT_456",
                "name": "새로운아파트",
                "address": "경기도 성남시 분당구 분당동",
                "build_year": "2022",
                "lat": "37.4422",
                "lng": "127.1055",
                "households": "800",
                "floors": "15",
            },
        ]

    @pytest.fixture
    def sample_transaction_data(self):
        """샘플 거래내역 데이터"""
        return [
            {
                "id": "APT_123",
                "name": "테스트아파트",
                "address": "서울특별시 강남구 테스트동",
                "build_year": "2020",
                "lat": "37.5326",
                "lng": "127.0628",
                "households": "1500",
                "floors": "20",
                "trade_type": "매매",
                "deal_price": "45000",
                "deposit": "",
                "monthly_rent": "",
                "deal_date": "2024-11-25",
                "area": "33.12",
                "floor": "5/25",
            },
            {
                "id": "APT_123",
                "name": "테스트아파트",
                "address": "서울특별시 강남구 테스트동",
                "build_year": "2020",
                "lat": "37.5326",
                "lng": "127.0628",
                "households": "1500",
                "floors": "20",
                "trade_type": "전세",
                "deal_price": "",
                "deposit": "30000",
                "monthly_rent": "",
                "deal_date": "2024-11-20",
                "area": "58.92",
                "floor": "12/25",
            },
            {
                "id": "APT_456",
                "name": "새로운아파트",
                "address": "경기도 성남시 분당구 분당동",
                "build_year": "2022",
                "lat": "37.4422",
                "lng": "127.1055",
                "households": "800",
                "floors": "15",
                "trade_type": "월세",
                "deal_price": "",
                "deposit": "80000",
                "monthly_rent": "400",
                "deal_date": "2024-11-15",
                "area": "83.76",
                "floor": "15/30",
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
            assert first_row["id"] == "APT_123"
            assert first_row["name"] == "테스트아파트"
            assert first_row["build_year"] == "2020"
            assert first_row["households"] == "1500"

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
            assert first_row["id"] == "APT_123"
            assert first_row["name"] == "테스트아파트"
            assert first_row["trade_type"] == "매매"
            assert first_row["deal_price"] == "45000"
            assert first_row["deposit"] == ""
            assert first_row["monthly_rent"] == ""

            # 두 번째 행 검증 (전세)
            second_row = rows[1]
            assert second_row["trade_type"] == "전세"
            assert second_row["deposit"] == "30000"
            assert second_row["monthly_rent"] == ""

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
