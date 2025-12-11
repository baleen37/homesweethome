"""Tests for CrawlCoordinator module.

Tests the incremental saving functionality and checkpoint management.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from crawler.coordinator import CrawlCoordinator
from crawler.writers.complexes_csv_writer import ComplexesCSVWriter
from crawler.writers.transaction_csv_writer import TransactionCSVWriter


class TestCrawlCoordinator:
    """CrawlCoordinator 테스트 클래스"""

    @pytest.fixture
    def temp_dir(self):
        """임시 디렉토리 fixture"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_fetch_functions(self):
        """모의 fetch 함수 fixture"""
        mock_detail = Mock(
            return_value={
                "complex_id": "111515",
                "pyeong_types": [
                    {"pyeong_type_number": 1, "pyeong_name": "84A"},
                    {"pyeong_type_number": 2, "pyeong_name": "84B"},
                ],
            }
        )

        mock_transactions = Mock(
            side_effect=lambda complex_id, pyeong_type, trade_type: [
                {
                    "complex_id": complex_id,
                    "complex_name": "헬리오시티",
                    "pyeong_type_number": pyeong_type,
                    "pyeong_name": f"84{['A', 'B'][pyeong_type - 1]}",
                    "trade_type": trade_type,
                    "trade_type_name": {"A1": "매매", "B1": "전세", "B2": "월세"}[trade_type],
                    "trade_date": "2025-11-14",
                    "trade_year": "2025",
                    "floor": "15",
                    "deal_price": "1700000000" if trade_type == "A1" else "0",
                    "deposit": "0" if trade_type == "A1" else "800000000",
                    "monthly_rent": "0" if trade_type in ["A1", "B1"] else "2000000",
                    "trade_category": "중개거래",
                    "is_delete": False,
                    "is_renew": False,
                }
            ]
        )

        return mock_detail, mock_transactions

    @pytest.fixture
    def sample_dong_complexes(self):
        """샘플 동별 단지 데이터 fixture"""
        return [
            {
                "dong_code": "1154510200",
                "dong_name": "역삼1동",
                "complexes": [
                    {
                        "complex_id": "111515",
                        "complex_name": "헬리오시티",
                        "real_estate_type": "아파트",
                    },
                    {
                        "complex_id": "111516",
                        "complex_name": "역삼푸르지오",
                        "real_estate_type": "아파트",
                    },
                ],
            },
            {
                "dong_code": "1154510300",
                "dong_name": "역삼2동",
                "complexes": [
                    {
                        "complex_id": "111517",
                        "complex_name": "역삼자이",
                        "real_estate_type": "아파트",
                    },
                ],
            },
        ]

    def test_init_creates_output_directory(self, temp_dir):
        """초기화 시 출력 디렉토리를 생성하는지 테스트"""
        output_dir = temp_dir / "output"
        CrawlCoordinator(output_dir)

        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_init_creates_csv_writers(self, temp_dir):
        """CSV Writer들이 올바르게 초기화되는지 테스트"""
        coordinator = CrawlCoordinator(temp_dir)

        assert isinstance(coordinator.transaction_writer, TransactionCSVWriter)
        assert isinstance(coordinator.complexes_writer, ComplexesCSVWriter)
        assert coordinator.transaction_writer.output_path == temp_dir / "transactions.csv"
        assert coordinator.complexes_writer.output_path == temp_dir / "complexes.csv"

    def test_crawl_single_dong_saves_incrementally(
        self, temp_dir, mock_fetch_functions, sample_dong_complexes
    ):
        """단일 동 크롤링 시 데이터가 점진적으로 저장되는지 테스트"""
        mock_detail, mock_transactions = mock_fetch_functions
        coordinator = CrawlCoordinator(temp_dir)

        dong_data = sample_dong_complexes[0]  # 역삼1동
        result = coordinator.crawl_dong(
            dong_code=dong_data["dong_code"],
            dong_name=dong_data["dong_name"],
            complexes=dong_data["complexes"],
            fetch_complex_detail=mock_detail,
            fetch_transaction_history=mock_transactions,
        )

        # 결과 검증
        assert result["dong_code"] == "1154510200"
        assert result["complexes_processed"] == 2
        assert result["transactions_collected"] == 12  # 2 complexes * 2 pyeongs * 3 trade types

        # CSV 파일이 생성되었는지 확인
        assert (temp_dir / "transactions.csv").exists()
        assert (temp_dir / "complexes.csv").exists()

        # 거래내역 CSV 내용 확인
        transactions_csv = (temp_dir / "transactions.csv").read_text(encoding="utf-8")
        lines = transactions_csv.strip().split("\n")
        assert len(lines) == 13  # header + 12 transactions
        assert "complex_id,complex_name,pyeong_type_number" in lines[0]  # header

        # 단지 CSV 내용 확인
        complexes_csv = (temp_dir / "complexes.csv").read_text(encoding="utf-8")
        assert len(complexes_csv.strip().split("\n")) == 3  # header + 2 complexes

    def test_crawl_multiple_dongs_with_resume(
        self, temp_dir, mock_fetch_functions, sample_dong_complexes
    ):
        """여러 동 크롤링 시 이어서 진행(resume) 기능이 동작하는지 테스트"""
        mock_detail, mock_transactions = mock_fetch_functions
        checkpoint_path = temp_dir / "checkpoint.json"

        # 첫 번째 실행 (첫 번째 동까지만)
        coordinator1 = CrawlCoordinator(
            temp_dir,
            checkpoint_path=checkpoint_path,
            initial_delay=0.1,  # 테스트를 위해 짧은 지연
        )
        result1 = coordinator1.crawl_multiple_dongs(
            dong_complexes=sample_dong_complexes,
            fetch_complex_detail=mock_detail,
            fetch_transaction_history=mock_transactions,
            resume=False,
        )

        assert result1["dongs_processed"] == 2  # 두 동 모두 처리
        assert checkpoint_path.exists()

        # 체크포인트 확인
        checkpoint_data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        assert checkpoint_data["last_dong"] == "1154510300"  # 마지막 동

        # CSV 파일들 확인
        transactions_csv = (temp_dir / "transactions.csv").read_text(encoding="utf-8")
        complexes_csv = (temp_dir / "complexes.csv").read_text(encoding="utf-8")

        # 두 번째 실행 (이어서 진행 - 이미 전부 처리했으므로 건너뛰어야 함)
        mock_detail.reset_mock()
        mock_transactions.reset_mock()

        coordinator2 = CrawlCoordinator(
            temp_dir,
            checkpoint_path=checkpoint_path,
            initial_delay=0.1,
        )
        result2 = coordinator2.crawl_multiple_dongs(
            dong_complexes=sample_dong_complexes,
            fetch_complex_detail=mock_detail,
            fetch_transaction_history=mock_transactions,
            resume=True,
        )

        # 이미 전부 처리했으므로 추가 처리 없음
        assert result2["dongs_processed"] == 0
        assert mock_detail.call_count == 0
        assert mock_transactions.call_count == 0

        # CSV 파일이 변경되지 않았는지 확인
        assert (temp_dir / "transactions.csv").read_text(encoding="utf-8") == transactions_csv
        assert (temp_dir / "complexes.csv").read_text(encoding="utf-8") == complexes_csv

    def test_checkpoint_saves_after_each_dong(
        self, temp_dir, mock_fetch_functions, sample_dong_complexes
    ):
        """각 동 완료 후 체크포인트가 저장되는지 테스트"""
        mock_detail, mock_transactions = mock_fetch_functions
        checkpoint_path = temp_dir / "checkpoint.json"

        # fetch 함수가 호출될 때마다 체크포인트를 확인
        checkpoint_checks = []

        def check_checkpoint():
            if checkpoint_path.exists():
                checkpoint_checks.append(json.loads(checkpoint_path.read_text(encoding="utf-8")))

        coordinator = CrawlCoordinator(
            temp_dir,
            checkpoint_path=checkpoint_path,
            initial_delay=0.01,
        )

        # 원래 함수에 체크포인트 확인 로직 추가
        original_fetch_detail = mock_detail

        def fetch_detail_with_check(complex_id):
            check_checkpoint()
            return original_fetch_detail(complex_id)

        coordinator.crawl_multiple_dongs(
            dong_complexes=sample_dong_complexes,
            fetch_complex_detail=fetch_detail_with_check,
            fetch_transaction_history=mock_transactions,
            resume=False,
        )

        # 최종 체크포인트 확인
        final_checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        assert final_checkpoint["last_dong"] == "1154510300"
        assert "last_updated_at" in final_checkpoint

    def test_error_handling_and_statistics(self, temp_dir, sample_dong_complexes):
        """에러 발생 시 통계가 올바르게 기록되는지 테스트"""

        # 에러를 발생시키는 모의 함수
        def failing_fetch_detail(complex_id):
            if complex_id == "111515":  # 첫 번째 단지만 실패
                raise Exception("Network error")
            return {
                "complex_id": complex_id,
                "pyeong_types": [{"pyeong_type_number": 1, "pyeong_name": "84A"}],  # 평형 추가
            }

        def failing_fetch_history(complex_id, pyeong_type, trade_type):
            if complex_id == "111516":  # 두 번째 단지만 실패
                raise Exception("API error")
            return []

        coordinator = CrawlCoordinator(
            temp_dir,
            initial_delay=0.01,
        )

        result = coordinator.crawl_dong(
            dong_code="1154510200",
            dong_name="역삼1동",
            complexes=sample_dong_complexes[0]["complexes"],
            fetch_complex_detail=failing_fetch_detail,
            fetch_transaction_history=failing_fetch_history,
        )

        # 에러가 기록되었는지 확인
        assert result["complexes_processed"] == 0  # 모두 실패
        assert len(result["errors"]) == 2  # 두 단지 모두 에러
        assert "Network error" in result["errors"][0]
        assert "API error" in result["errors"][1]

        # 코디네이터 통계 확인
        stats = coordinator.get_statistics()
        assert stats["total_complexes_processed"] == 0
        assert len(stats["errors"]) == 2

    def test_rate_limiter_integration(self, temp_dir, mock_fetch_functions, sample_dong_complexes):
        """Rate limiter가 올바르게 동작하는지 테스트"""
        mock_detail, mock_transactions = mock_fetch_functions
        coordinator = CrawlCoordinator(
            temp_dir,
            initial_delay=0.01,
            max_delay=0.05,
        )

        start_time = None

        def timed_fetch_detail(complex_id):
            nonlocal start_time
            if start_time is None:
                start_time = time.time()
            return mock_detail(complex_id)

        import time

        coordinator.crawl_dong(
            dong_code="1154510200",
            dong_name="역삼1동",
            complexes=sample_dong_complexes[0]["complexes"][:1],  # 하나만 처리
            fetch_complex_detail=timed_fetch_detail,
            fetch_transaction_history=mock_transactions,
        )

        # Rate limiter 상태 확인
        stats = coordinator.get_statistics()
        rate_limiter_state = stats["rate_limiter_state"]
        assert rate_limiter_state["current_delay"] <= 0.05  # max_delay 이하
        assert rate_limiter_state["success_count"] > 0
        assert rate_limiter_state["error_count"] == 0


class TestCrawlCoordinatorHelpers:
    """CrawlCoordinator 헬퍼 메서드 테스트 클래스"""

    @pytest.fixture
    def temp_dir(self):
        """임시 디렉토리 fixture"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def coordinator(self, temp_dir):
        """CrawlCoordinator fixture"""
        return CrawlCoordinator(temp_dir)

    def test_extract_pyeong_type_numbers_dict(self, coordinator):
        """딕셔너리 형태의 pyeong_types에서 평형 번호 추출 테스트"""
        detail = {
            "pyeong_types": {
                "1": {"pyeong_name": "84A"},
                "2": {"pyeong_name": "84B"},
            }
        }
        result = coordinator._extract_pyeong_type_numbers(detail, "C001")
        assert result == ["1", "2"]

    def test_extract_pyeong_type_numbers_list(self, coordinator):
        """리스트 형태의 pyeong_types에서 평형 번호 추출 테스트"""
        detail = {
            "pyeong_types": [
                {"pyeong_type_number": "1", "pyeong_name": "84A"},
                {"pyeong_type_number": "2", "pyeong_name": "84B"},
                {"pyeongTypeNo": "3", "pyeong_name": "84C"},  # 다른 필드명
            ]
        }
        result = coordinator._extract_pyeong_type_numbers(detail, "C001")
        assert result == ["1", "2", "3"]

    def test_extract_pyeong_type_numbers_empty(self, coordinator):
        """빈 pyeong_types 처리 테스트"""
        detail = {"pyeong_types": []}
        result = coordinator._extract_pyeong_type_numbers(detail, "C001")
        assert result == []

        detail = {"pyeong_types": None}
        result = coordinator._extract_pyeong_type_numbers(detail, "C001")
        assert result == []

    def test_extract_pyeong_type_numbers_invalid_type(self, coordinator):
        """잘못된 타입의 pyeong_types 처리 테스트"""
        detail = {"pyeong_types": "invalid"}
        result = coordinator._extract_pyeong_type_numbers(detail, "C001")
        assert result == []

    def test_collect_transactions_for_complex(self, coordinator):
        """단지의 거래내역 수집 테스트"""
        # Mock fetch function
        mock_fetch = Mock(
            side_effect=lambda complex_id, pyeong_type, trade_type: [
                {
                    "complex_id": complex_id,
                    "pyeong_type_number": pyeong_type,
                    "trade_type": trade_type,
                    "trade_price": "100000000",
                }
            ]
        )

        # Mock transaction writer
        coordinator.transaction_writer = Mock()
        coordinator.transaction_writer.append = Mock()

        pyeong_type_numbers = ["1", "2"]
        result = coordinator._collect_transactions_for_complex(
            "C001", pyeong_type_numbers, mock_fetch
        )

        # 2 pyeong_types * 3 trade_types = 6 calls
        assert mock_fetch.call_count == 6
        assert len(result) == 6
        # append is called for each fetch call that returns transactions (all 6 calls)
        assert coordinator.transaction_writer.append.call_count == 6

    def test_collect_transactions_for_complex_empty(self, coordinator):
        """빈 평형 타입 목록으로 거래내역 수집 테스트"""
        mock_fetch = Mock()
        result = coordinator._collect_transactions_for_complex("C001", [], mock_fetch)

        assert mock_fetch.call_count == 0
        assert result == []

    def test_handle_complex_processing_error(self, coordinator, caplog):
        """단지 처리 에러 핸들링 테스트"""
        # Mock progress tracker
        coordinator.progress_tracker = Mock()
        coordinator.progress_tracker.add_error = Mock()

        error = Exception("Test error")
        complex_data = {"complex_id": "C001"}
        dong_stats = {"errors": []}

        coordinator._handle_complex_processing_error(error, complex_data, dong_stats)

        # 에러가 통계에 추가되었는지 확인
        assert len(dong_stats["errors"]) == 1
        assert "Test error" in dong_stats["errors"][0]

        # Progress tracker가 호출되었는지 확인
        coordinator.progress_tracker.add_error.assert_called_once()

    def test_update_progress_for_complex_no_tracker(self, coordinator):
        """Progress tracker가 없을 때 단지 진행 상황 업데이트 테스트"""
        coordinator.progress_tracker = None
        # Should not raise any error
        coordinator._update_progress_for_complex("C001", "Test Complex", [], is_start=True)
        coordinator._update_progress_for_complex("C001", "Test Complex", [], is_start=False)

    def test_update_progress_for_complex_with_tracker(self, coordinator):
        """Progress tracker가 있을 때 단지 진행 상황 업데이트 테스트"""
        coordinator.progress_tracker = Mock()
        coordinator.progress_tracker.start_complex = Mock()
        coordinator.progress_tracker.complete_complex = Mock()

        coordinator._update_progress_for_complex("C001", "Test Complex", [], is_start=True)
        coordinator.progress_tracker.start_complex.assert_called_once_with("C001", "Test Complex")

        coordinator._update_progress_for_complex(
            "C001", "Test Complex", [{"id": 1}], is_start=False
        )
        coordinator.progress_tracker.complete_complex.assert_called_once_with(
            "C001", "Test Complex", 1
        )

    def test_update_progress_for_dong_no_tracker(self, coordinator):
        """Progress tracker가 없을 때 동 진행 상황 업데이트 테스트"""
        coordinator.progress_tracker = None
        dong_stats = {
            "complexes_count": 5,
            "complexes_processed": 3,
            "transactions_collected": 10,
            "errors": [],
        }

        # Should not raise any error
        coordinator._update_progress_for_dong("D001", "Test Dong", dong_stats, is_start=True)
        coordinator._update_progress_for_dong("D001", "Test Dong", dong_stats, is_start=False)

    def test_update_progress_for_dong_with_tracker(self, coordinator):
        """Progress tracker가 있을 때 동 진행 상황 업데이트 테스트"""
        coordinator.progress_tracker = Mock()
        coordinator.progress_tracker.start_dong = Mock()
        coordinator.progress_tracker.complete_dong = Mock()
        coordinator.progress_tracker.update_rate_limiter_delay = Mock()

        # Mock rate limiter
        coordinator.rate_limiter = Mock()
        coordinator.rate_limiter.current_delay = 5.0

        dong_stats = {
            "complexes_count": 5,
            "complexes_processed": 3,
            "transactions_collected": 10,
            "errors": ["error1"],
        }

        coordinator._update_progress_for_dong("D001", "Test Dong", dong_stats, is_start=True)
        coordinator.progress_tracker.start_dong.assert_called_once_with("D001", "Test Dong", 5)

        coordinator._update_progress_for_dong("D001", "Test Dong", dong_stats, is_start=False)
        coordinator.progress_tracker.complete_dong.assert_called_once_with(
            "D001", "Test Dong", 3, 10, ["error1"]
        )
        coordinator.progress_tracker.update_rate_limiter_delay.assert_called_once_with(5.0)
