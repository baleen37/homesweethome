"""HogangnonoCSVWriter에 대한 통합 테스트

이 테스트는 TDD 방식으로 작성되었으며,
1. 실패하는 테스트를 먼저 작성 (RED)
2. 최소한의 코드로 테스트 통과 (GREEN)
3. 코드를 리팩토링하여 개선 (REFACTOR)
"""

import pytest
import tempfile
from pathlib import Path

from crawler.writers.hogangnono_csv_writer import HogangnonoCSVWriter


class TestHogangnonoCSVWriterIntegration:
    """HogangnonoCSVWriter 통합 테스트"""

    @pytest.fixture
    def temp_output_dir(self):
        """임시 출력 디렉토리"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def writer(self, temp_output_dir):
        """HogangnonoCSVWriter 인스턴스"""
        return HogangnonoCSVWriter(str(temp_output_dir))

    def test_save_complexes_creates_file(self, writer, temp_output_dir):
        """단지 데이터 저장 시 파일이 생성되는지 확인"""
        # Given: 테스트 데이터
        sample_data = [
            {
                "aptSeq": "APT_001",
                "aptName": "테스트아파트",
                "address": "서울시 강남구",
                "buildYear": "2020",
                "dealCnt": 10,
                "householdCnt": 100,
            }
        ]

        # When: 데이터 저장
        writer.save_complexes(sample_data)

        # Then: 파일이 생성되었는지 확인
        complexes_file = temp_output_dir / "complexes.csv"
        assert complexes_file.exists(), "complexes.csv 파일이 생성되어야 함"

        # And: 파일 크기가 0보다 커야 함
        assert complexes_file.stat().st_size > 0, "파일에 데이터가 있어야 함"

        # And: 헤더와 최소 1개의 행이 있어야 함
        with open(complexes_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) >= 2, "헤더와 최소 1개의 데이터 행이 있어야 함"

    def test_save_transactions_creates_file(self, writer, temp_output_dir):
        """거래내역 데이터 저장 시 파일이 생성되는지 확인"""
        # Given: 테스트 데이터
        sample_data = [
            {
                "aptSeq": "APT_001",
                "aptName": "테스트아파트",
                "dong": "101동",
                "ho": "101호",
                "dealAmount": "50000",
                "dealDate": "2024-01-01",
            }
        ]

        # When: 데이터 저장
        writer.save_transactions(sample_data)

        # Then: 파일이 생성되었는지 확인
        transactions_file = temp_output_dir / "transactions.csv"
        assert transactions_file.exists(), "transactions.csv 파일이 생성되어야 함"

        # And: 파일 크기가 0보다 커야 함
        assert transactions_file.stat().st_size > 0, "파일에 데이터가 있어야 함"

        # And: 헤더와 최소 1개의 행이 있어야 함
        with open(transactions_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) >= 2, "헤더와 최소 1개의 데이터 행이 있어야 함"

    def test_get_stats_returns_correct_counts(self, writer, temp_output_dir):
        """get_stats가 올바른 레코드 수를 반환하는지 확인"""
        # Given: 데이터 저장
        complexes_data = [
            {"aptSeq": "APT_001", "aptName": "아파트1"},
            {"aptSeq": "APT_002", "aptName": "아파트2"},
        ]
        transactions_data = [
            {"aptSeq": "APT_001", "dealAmount": "50000"},
            {"aptSeq": "APT_001", "dealAmount": "55000"},
            {"aptSeq": "APT_002", "dealAmount": "60000"},
        ]

        # When: 데이터 저장
        writer.save_complexes(complexes_data)
        writer.save_transactions(transactions_data)

        # Then: 통계 확인
        stats = writer.get_stats()
        assert stats["complexes_record_count"] == 2, "단지 레코드 수는 2개여야 함"
        assert stats["transactions_record_count"] == 3, "거래내역 레코드 수는 3개여야 함"
