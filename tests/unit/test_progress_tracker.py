"""Tests for ProgressTracker functionality."""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crawler.progress_tracker import ProgressTracker


class TestProgressTracker:
    """ProgressTracker 테스트 클래스"""

    def setup_method(self):
        """테스트 메서드 실행 전 설정"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.tracker = ProgressTracker(
            output_dir=self.temp_dir,
            report_interval=1,  # 1초 간격으로 리포트
        )

    def teardown_method(self):
        """테스트 메서드 실행 후 정리"""
        # 임시 파일 정리
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self):
        """초기화 테스트"""
        assert self.tracker.output_dir == self.temp_dir
        assert self.tracker.report_interval == 1
        assert self.tracker.stats["total_dongs"] == 0
        assert self.tracker.stats["completed_dongs"] == 0
        assert self.tracker.stats["total_complexes"] == 0
        assert self.tracker.stats["completed_complexes"] == 0

    def test_start_crawling(self):
        """크롤링 시작 기록 테스트"""
        self.tracker.start_crawling(total_dongs=10, total_complexes=100)

        assert self.tracker.stats["start_time"] > 0
        assert self.tracker.stats["total_dongs"] == 10
        assert self.tracker.stats["total_complexes"] == 100

        # 진행 상황 파일이 생성되었는지 확인
        progress_file = self.temp_dir / "progress.json"
        assert progress_file.exists()

    def test_start_and_complete_dong(self):
        """동 처리 시작 및 완료 테스트"""
        # 크롤링 시작
        self.tracker.start_crawling(total_dongs=5, total_complexes=50)

        # 동 처리 시작
        self.tracker.start_dong("12345", "역삼1동", 10)
        assert self.tracker.current_dong_start > 0

        # 약간의 시간 경과
        time.sleep(0.1)

        # 동 처리 완료
        self.tracker.complete_dong(
            dong_code="12345",
            dong_name="역삼1동",
            complexes_processed=10,
            transactions_collected=100,
            errors=["Test error"],
        )

        # 통계 확인
        assert self.tracker.stats["completed_dongs"] == 1
        assert self.tracker.stats["collected_transactions"] == 100
        assert self.tracker.stats["error_count"] == 1
        assert len(self.tracker.stats["errors"]) == 1
        assert self.tracker.stats["errors"][0] == "Test error"

        # 타이밍 정보 확인
        assert len(self.tracker.timings) == 1
        assert self.tracker.timings[0]["type"] == "dong"
        assert self.tracker.timings[0]["duration"] >= 0.1
        assert self.tracker.timings[0]["complexes"] == 10
        assert self.tracker.timings[0]["transactions"] == 100

    def test_start_and_complete_complex(self):
        """단지 처리 시작 및 완료 테스트"""
        # 크롤링 시작
        self.tracker.start_crawling(total_dongs=1, total_complexes=5)

        # 단지 처리 시작
        self.tracker.start_complex("111515", "헬리오시티")
        assert self.tracker.current_complex_start > 0

        # 약간의 시간 경과
        time.sleep(0.05)

        # 단지 처리 완료
        self.tracker.complete_complex(
            complex_id="111515",
            complex_name="헬리오시티",
            transactions_collected=20,
        )

        # 통계 확인
        assert self.tracker.stats["completed_complexes"] == 1

        # 타이밍 정보 확인
        complex_timings = [t for t in self.tracker.timings if t["type"] == "complex"]
        assert len(complex_timings) == 1
        assert complex_timings[0]["duration"] >= 0.05
        assert complex_timings[0]["transactions"] == 20

    def test_update_rate_limiter_delay(self):
        """Rate limiter 지연 시간 업데이트 테스트"""
        self.tracker.update_rate_limiter_delay(5.0)
        assert self.tracker.stats["rate_limiter_delay"] == 5.0

    def test_add_error(self):
        """에러 추가 테스트"""
        self.tracker.add_error("Test error message")

        assert self.tracker.stats["error_count"] == 1
        assert len(self.tracker.stats["errors"]) == 1
        assert self.tracker.stats["errors"][0] == "Test error message"

    def test_get_progress_summary(self):
        """진행 상황 요약 테스트"""
        # 초기 상태
        self.tracker.start_crawling(total_dongs=10, total_complexes=100)

        # 일부 진행
        self.tracker.start_dong("12345", "역삼1동", 10)
        # 약간의 시간 경과를 보장
        time.sleep(0.01)
        self.tracker.complete_dong(
            dong_code="12345",
            dong_name="역삼1동",
            complexes_processed=10,
            transactions_collected=100,
            errors=[],
        )

        self.tracker.start_complex("111515", "헬리오시티")
        # 약간의 시간 경과를 보장
        time.sleep(0.01)
        self.tracker.complete_complex(
            complex_id="111515",
            complex_name="헬리오시티",
            transactions_collected=20,
        )

        summary = self.tracker.get_progress_summary()

        # 진행률 확인
        assert summary["completed_dongs"] == 1
        assert summary["total_dongs"] == 10
        assert summary["dong_progress_percent"] == 10.0
        assert summary["completed_complexes"] == 1
        assert summary["total_complexes"] == 100
        assert summary["complex_progress_percent"] == 1.0

        # 수집된 데이터
        assert summary["collected_transactions"] == 120  # 100 + 20

        # 성능 지표
        assert summary["avg_complex_time_seconds"] >= 0  # 0 이상
        assert summary["avg_dong_time_seconds"] >= 0  # 0 이상
        assert summary["complexes_per_hour"] >= 0
        assert summary["transactions_per_hour"] >= 0

        # 시간 정보
        assert "elapsed_time_formatted" in summary
        assert "eta_formatted" in summary

    @patch('sys.stdout')
    def test_print_progress_report(self, mock_stdout):
        """진행 상황 리포트 출력 테스트"""
        self.tracker.start_crawling(total_dongs=10, total_complexes=100)

        # 강제 출력
        self.tracker.print_progress_report(force=True)

        # stdout.write가 호출되었는지 확인
        mock_stdout.flush.assert_called()

    def test_format_duration(self):
        """시간 형식화 테스트"""
        # 초
        assert self.tracker._format_duration(30) == "30초"
        assert self.tracker._format_duration(59) == "59초"

        # 분
        assert self.tracker._format_duration(60) == "1분"
        assert self.tracker._format_duration(90) == "2분"
        assert self.tracker._format_duration(3599) == "60분"

        # 시간
        assert self.tracker._format_duration(3600) == "1.0시간"
        assert self.tracker._format_duration(5400) == "1.5시간"
        assert self.tracker._format_duration(86399) == "24.0시간"

        # 일
        assert self.tracker._format_duration(86400) == "1.0일"
        assert self.tracker._format_duration(172800) == "2.0일"

    def test_finish_crawling(self):
        """크롤링 완료 테스트"""
        self.tracker.start_crawling(total_dongs=5, total_complexes=50)
        self.tracker.start_dong("12345", "역삼1동", 10)
        self.tracker.complete_dong(
            dong_code="12345",
            dong_name="역삼1동",
            complexes_processed=10,
            transactions_collected=100,
            errors=[],
        )

        # 로그 파일 활성화
        self.tracker._setup_file_logging()

        # 크롤링 완료
        self.tracker.finish_crawling()

        # 진행 상황 파일이 업데이트되었는지 확인
        progress_file = self.temp_dir / "progress.json"
        assert progress_file.exists()

        with open(progress_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert "summary" in data
            assert data["summary"]["completed_dongs"] == 1

    def test_load_progress(self):
        """진행 상황 로드 테스트"""
        # 먼저 저장
        self.tracker.start_crawling(total_dongs=5, total_complexes=50)
        self.tracker._save_progress()

        # 새 인스턴스로 로드
        new_tracker = ProgressTracker(output_dir=self.temp_dir)
        loaded_data = new_tracker.load_progress()

        assert loaded_data is not None
        assert loaded_data["total_dongs"] == 5
        assert loaded_data["total_complexes"] == 50
        assert "summary" in loaded_data

    def test_load_progress_no_file(self):
        """파일이 없을 때 진행 상황 로드 테스트"""
        new_tracker = ProgressTracker(output_dir=self.temp_dir)
        loaded_data = new_tracker.load_progress()
        assert loaded_data is None

    def test_multiple_dongs_averages(self):
        """여러 동 처리 시 평균 계산 테스트"""
        self.tracker.start_crawling(total_dongs=3, total_complexes=30)

        # 첫 번째 동 (빠름)
        self.tracker.start_dong("11111", "동1", 10)
        time.sleep(0.05)
        self.tracker.complete_dong("11111", "동1", 10, 50, [])

        # 두 번째 동 (보통)
        self.tracker.start_dong("22222", "동2", 10)
        time.sleep(0.1)
        self.tracker.complete_dong("22222", "동2", 10, 60, [])

        # 세 번째 동 (느림)
        self.tracker.start_dong("33333", "동3", 10)
        time.sleep(0.15)
        self.tracker.complete_dong("33333", "동3", 10, 70, [])

        # 평균 확인 (3개 동의 평균 시간)
        avg_dong_time = self.tracker.stats["avg_dong_time"]
        # 최근 10개의 동 타이밍을 사용하므로 모두 포함됨
        # 평균은 (0.05 + 0.1 + 0.15) / 3 = 0.1초
        assert 0.08 < avg_dong_time < 0.12  # 약 0.1초 평균

        # ETA 계산 확인 (모든 동이 완료되었으므로 남은 동이 없음)
        summary = self.tracker.get_progress_summary()
        # 모든 동을 완료했으므로 ETA는 0 또는 아주 작은 값
        assert summary["eta_seconds"] >= 0