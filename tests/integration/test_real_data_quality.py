"""
실제 수집된 데이터 품질 검증 테스트

네이버 API를 통해 실제로 수집된 데이터의 품질을 검증합니다.
"""

import csv
import json
import os
from pathlib import Path

import pytest

from crawler.config import CrawlerConfig


class TestRealDataQuality:
    """실제 데이터 품질 검증 테스트"""

    @pytest.fixture
    def config(self):
        """테스트용 설정"""
        return CrawlerConfig.from_env()

    @pytest.fixture
    def output_dir(self):
        """출력 디렉토리 경로"""
        return Path(os.getenv("OUTPUT_DIR", "output"))

    def test_csv_files_exist(self, output_dir):
        """CSV 파일이 존재하는지 확인"""
        complexes_file = output_dir / "complexes.csv"
        transactions_file = output_dir / "transactions.csv"

        assert complexes_file.exists(), "단지 정보 CSV 파일이 존재하지 않음"
        assert transactions_file.exists(), "거래내역 CSV 파일이 존재하지 않음"

    def test_csv_files_have_data(self, output_dir):
        """CSV 파일에 데이터가 있는지 확인"""
        complexes_file = output_dir / "complexes.csv"
        transactions_file = output_dir / "transactions.csv"

        # 파일 크기 확인 (헤더만 있는 경우 제외)
        assert complexes_file.stat().st_size > 200, "단지 정보 CSV 파일에 데이터가 거의 없음"
        assert transactions_file.stat().st_size > 200, "거래내역 CSV 파일에 데이터가 거의 없음"

        # 라인 수 확인
        with open(complexes_file, "r", encoding="utf-8") as f:
            complexes_lines = sum(1 for _ in f)

        with open(transactions_file, "r", encoding="utf-8") as f:
            transactions_lines = sum(1 for _ in f)

        # 헤더를 제외하고 최소 1개 이상의 데이터가 있어야 함
        assert complexes_lines > 1, f"단지 정보가 없음 (총 라인 수: {complexes_lines})"
        assert transactions_lines > 1, f"거래내역이 없음 (총 라인 수: {transactions_lines})"

    @pytest.fixture
    def complexes_data(self, output_dir):
        """단지 데이터 로드"""
        complexes_file = output_dir / "complexes.csv"
        data = []

        with open(complexes_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 빈 행 건너뛰기
                if any(row.values()):
                    data.append(row)

        return data

    @pytest.fixture
    def transactions_data(self, output_dir):
        """거래내역 데이터 로드"""
        transactions_file = output_dir / "transactions.csv"
        data = []

        with open(transactions_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 빈 행 건너뛰기
                if any(row.values()):
                    data.append(row)

        return data

    def test_complex_data_quality(self, complexes_data):
        """단지 데이터 품질 검증"""
        if not complexes_data:
            pytest.skip("수집된 단지 데이터가 없음")

        # 데이터 샘플링 (최대 100개)
        sample_size = min(100, len(complexes_data))
        sample = complexes_data[:sample_size]

        issues = []

        for complex in sample:
            # 필수 필드 확인
            required_fields = [
                "complex_id",
                "complex_name",
                "real_estate_type",
                "completion_year_month",
                "total_dong_count",
                "total_household_count",
                "fetched_at",
            ]

            for field in required_fields:
                if not complex.get(field):
                    issues.append(
                        f"단지 ID {complex.get('complex_id', 'Unknown')}: 필수 필드 누락 - {field}"
                    )

            # 데이터 형식 검증
            try:
                # complex_id
                complex_id = complex.get("complex_id", "")
                if not complex_id.isdigit():
                    issues.append(f"단지 ID 형식 오류: {complex_id}")

                # completion_year_month
                completion = complex.get("completion_year_month", "")
                if completion and (not completion.isdigit() or len(completion) != 6):
                    issues.append(f"준공년월 형식 오류: {completion}")

                # 숫자 필드
                for field in ["total_dong_count", "total_household_count"]:
                    value = complex.get(field, "0")
                    if value and not value.isdigit():
                        issues.append(f"{field} 형식 오류: {value}")

                # 실수 필드
                for field in ["min_area", "max_area"]:
                    value = complex.get(field, "0")
                    if value:
                        try:
                            float(value)
                        except ValueError:
                            issues.append(f"{field} 형식 오류: {value}")

            except Exception as e:
                issues.append(f"데이터 파싱 오류: {str(e)}")

        # 이슈가 10% 이하이어야 함
        max_issues = len(sample) * 0.1
        assert (
            len(issues) <= max_issues
        ), f"데이터 품질 이슈过多: {len(issues)}개 (최대 허용: {max_issues}개)\n이슈 목록: {issues[:10]}"

    def test_transaction_data_quality(self, transactions_data):
        """거래내역 데이터 품질 검증"""
        if not transactions_data:
            pytest.skip("수집된 거래내역 데이터가 없음")

        # 데이터 샘플링 (최대 100개)
        sample_size = min(100, len(transactions_data))
        sample = transactions_data[:sample_size]

        issues = []

        for transaction in sample:
            # 필수 필드 확인
            required_fields = [
                "complex_id",
                "complex_name",
                "pyeong_type_number",
                "trade_type",
                "trade_date",
                "trade_year",
                "floor",
            ]

            for field in required_fields:
                if not transaction.get(field):
                    issues.append(f"거래 데이터 필수 필드 누락: {field}")

            # 데이터 형식 검증
            try:
                # trade_type
                trade_type = transaction.get("trade_type", "")
                if trade_type not in ["A1", "B1", "B2"]:
                    issues.append(f"거래 유형 코드 오류: {trade_type}")

                # trade_date
                trade_date = transaction.get("trade_date", "")
                if trade_date:
                    parts = trade_date.split(".")
                    if len(parts) != 3:
                        issues.append(f"거래일 형식 오류: {trade_date}")
                    else:
                        try:
                            year, month, day = map(int, parts)
                            assert 1 <= month <= 12
                            assert 1 <= day <= 31
                        except ValueError:
                            issues.append(f"거래일 값 오류: {trade_date}")

                # 숫자 필드
                for field in ["deal_price", "deposit", "monthly_rent"]:
                    value = transaction.get(field, "0")
                    if value:
                        try:
                            int(value)
                        except ValueError:
                            issues.append(f"{field} 형식 오류: {value}")

                # floor
                floor = transaction.get("floor", "")
                if floor and not floor.lstrip("-").isdigit():
                    issues.append(f"층 정보 형식 오류: {floor}")

            except Exception as e:
                issues.append(f"데이터 파싱 오류: {str(e)}")

        # 이슈가 10% 이하이어야 함
        max_issues = len(sample) * 0.1
        assert (
            len(issues) <= max_issues
        ), f"데이터 품질 이슈过多: {len(issues)}개 (최대 허용: {max_issues}개)\n이슈 목록: {issues[:10]}"

    def test_data_consistency(self, complexes_data, transactions_data):
        """단지와 거래내역 데이터 일관성 검증"""
        if not complexes_data or not transactions_data:
            pytest.skip("데이터가 충분하지 않음")

        # 단지 ID 집합
        complex_ids = {c.get("complex_id") for c in complexes_data if c.get("complex_id")}
        transaction_complex_ids = {
            t.get("complex_id") for t in transactions_data if t.get("complex_id")
        }

        # 거래내역에 있는 단지 ID가 단지 정보에 있는지 확인
        orphan_transactions = transaction_complex_ids - complex_ids
        assert (
            len(orphan_transactions) == 0
        ), f"단지 정보가 없는 거래내역 존재: {list(orphan_transactions)[:10]}"

        # 각 단지의 거래 유형별 개수 집계
        complex_trade_counts = {}
        for transaction in transactions_data[:1000]:  # 샘플링
            complex_id = transaction.get("complex_id")
            trade_type = transaction.get("trade_type")

            if complex_id and trade_type:
                if complex_id not in complex_trade_counts:
                    complex_trade_counts[complex_id] = {"A1": 0, "B1": 0, "B2": 0}
                complex_trade_counts[complex_id][trade_type] += 1

        # 데이터의 합리성 검증
        inconsistencies = []
        for complex_id, counts in list(complex_trade_counts.items())[:50]:  # 샘플링
            total = sum(counts.values())
            if total == 0:
                continue

            # 매매가 있는데 전세나 월세가 하나도 없는 경우는 드물지만 가능
            # 모든 거래 유형이 0인 경우만 체크
            if all(count == 0 for count in counts.values()):
                inconsistencies.append(f"단지 {complex_id}: 모든 거래 유형 개수가 0")

        assert (
            len(inconsistencies) <= len(complex_trade_counts) * 0.05
        ), f"데이터 일관성 이슈: {len(inconsistencies)}개"

    def test_checkpoint_file_quality(self, output_dir):
        """체크포인트 파일 품질 검증"""
        checkpoint_file = output_dir / "checkpoint.json"

        if not checkpoint_file.exists():
            pytest.skip("체크포인트 파일이 없음")

        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)

            # 필수 필드 확인
            required_fields = [
                "start_time",
                "current_time",
                "total_dongs",
                "completed_dongs",
                "total_complexes",
                "completed_complexes",
                "error_count",
                "summary",
            ]

            for field in required_fields:
                assert field in checkpoint, f"체크포인트 필드 누락: {field}"

            # summary 필드 검증
            summary = checkpoint["summary"]
            summary_fields = [
                "elapsed_time_formatted",
                "dong_progress_percent",
                "complex_progress_percent",
                "error_rate_percent",
                "last_updated",
            ]

            for field in summary_fields:
                assert field in summary, f"summary 필드 누락: {field}"

            # 진행률 합리성 검증
            dong_progress = summary.get("dong_progress_percent", 0)
            complex_progress = summary.get("complex_progress_percent", 0)

            assert 0 <= dong_progress <= 100, f"동 진행률 범위 오류: {dong_progress}"
            assert 0 <= complex_progress <= 100, f"단지 진행률 범위 오류: {complex_progress}"

            # 오류율 합리성 검증
            error_rate = summary.get("error_rate_percent", 0)
            assert 0 <= error_rate <= 100, f"오류율 범위 오류: {error_rate}"

        except json.JSONDecodeError as e:
            pytest.fail(f"체크포인트 파일 JSON 파싱 오류: {e}")

    def test_data_volume_acceptance(self, complexes_data, transactions_data):
        """데이터 수량 검증"""
        if not complexes_data:
            pytest.skip("수집된 단지 데이터가 없음")

        # 최소 데이터 수량 확인
        min_complexes = 10
        min_transactions = 10

        assert (
            len(complexes_data) >= min_complexes
        ), f"단지 데이터 수량 부족: {len(complexes_data)} < {min_complexes}"

        if transactions_data:
            assert (
                len(transactions_data) >= min_transactions
            ), f"거래내역 데이터 수량 부족: {len(transactions_data)} < {min_transactions}"

        # 평균 거래내역 수 확인
        avg_transactions_per_complex = (
            len(transactions_data) / len(complexes_data) if complexes_data else 0
        )

        # 최소 1개의 거래내역이 있어야 함 (데이터가 있다면)
        if len(complexes_data) > 0:
            assert (
                avg_transactions_per_complex >= 0.1
            ), f"평균 거래내역 수 부족: {avg_transactions_per_complex:.2f}"
