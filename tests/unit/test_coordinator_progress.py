"""Tests for CrawlCoordinator progress tracking integration."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


from crawler.coordinator import CrawlCoordinator
from crawler.progress_tracker import ProgressTracker


class TestCrawlCoordinatorProgress:
    """CrawlCoordinator progress tracking 통합 테스트"""

    def setup_method(self):
        """테스트 메서드 실행 전 설정"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.checkpoint_path = self.temp_dir / "checkpoint.json"

    def teardown_method(self):
        """테스트 메서드 실행 후 정리"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_with_progress_tracking(self):
        """Progress tracking 활성화된 상태로 초기화 테스트"""
        coordinator = CrawlCoordinator(
            config_or_output_dir=self.temp_dir,
            checkpoint_path=self.checkpoint_path,
            enable_progress_tracking=True,
            progress_report_interval=30,
        )

        assert coordinator.progress_tracker is not None
        assert isinstance(coordinator.progress_tracker, ProgressTracker)
        assert coordinator.progress_tracker.report_interval == 30

    def test_init_without_progress_tracking(self):
        """Progress tracking 비활성화된 상태로 초기화 테스트"""
        coordinator = CrawlCoordinator(
            config_or_output_dir=self.temp_dir,
            checkpoint_path=self.checkpoint_path,
            enable_progress_tracking=False,
        )

        assert coordinator.progress_tracker is None

    @patch("crawler.coordinator.ProgressTracker")
    def test_crawl_dong_with_progress_tracking(self, mock_progress_tracker_class):
        """Progress tracking과 함께 동 크롤링 테스트"""
        # Mock ProgressTracker
        mock_tracker = MagicMock()
        mock_progress_tracker_class.return_value = mock_tracker

        # Coordinator 초기화
        coordinator = CrawlCoordinator(
            config_or_output_dir=self.temp_dir,
            checkpoint_path=self.checkpoint_path,
            enable_progress_tracking=True,
        )

        # Mock functions
        mock_fetch_detail = MagicMock(return_value={"pyeong_types": []})
        mock_fetch_transactions = MagicMock(return_value=[])

        # Mock complex data
        complexes = [
            {"complex_id": "111515", "complex_name": "단지1"},
            {"complex_id": "111516", "complex_name": "단지2"},
        ]

        # 동 크롤링 실행
        coordinator.crawl_dong(
            dong_code="12345",
            dong_name="테스트동",
            complexes=complexes,
            fetch_complex_detail=mock_fetch_detail,
            fetch_transaction_history=mock_fetch_transactions,
        )

        # Progress tracker 메서드 호출 확인
        assert mock_tracker.start_dong.call_count == 1
        assert mock_tracker.complete_dong.call_count == 1
        assert mock_tracker.start_complex.call_count == 2  # 2개 단지
        assert mock_tracker.complete_complex.call_count == 2
        assert mock_tracker.update_rate_limiter_delay.call_count == 1

        # 호출 인자 확인
        mock_tracker.start_dong.assert_called_with("12345", "테스트동", 2)
        mock_tracker.start_complex.assert_any_call("111515", "단지1")
        mock_tracker.start_complex.assert_any_call("111516", "단지2")

    def test_crawl_dong_with_error_and_progress_tracking(self):
        """에러 발생 시 Progress tracking 테스트"""
        # Coordinator 초기화 (실제 ProgressTracker 사용)
        coordinator = CrawlCoordinator(
            config_or_output_dir=self.temp_dir,
            checkpoint_path=self.checkpoint_path,
            enable_progress_tracking=True,
        )

        # Mock functions (첫 번째는 에러, 두 번째는 성공)
        mock_fetch_detail = MagicMock(side_effect=[None, {"pyeong_types": []}])
        mock_fetch_transactions = MagicMock(return_value=[])

        # Mock complex data
        complexes = [
            {"complex_id": "111515", "complex_name": "단지1"},
            {"complex_id": "111516", "complex_name": "단지2"},
        ]

        # 동 크롤링 실행
        result = coordinator.crawl_dong(
            dong_code="12345",
            dong_name="테스트동",
            complexes=complexes,
            fetch_complex_detail=mock_fetch_detail,
            fetch_transaction_history=mock_fetch_transactions,
        )

        # Progress tracker에 에러가 기록되었는지 확인
        assert coordinator.progress_tracker is not None
        assert coordinator.progress_tracker.stats["error_count"] > 0
        assert len(coordinator.progress_tracker.stats["errors"]) > 0

        # 결과 확인
        assert result["complexes_processed"] == 1  # 하나만 성공
        assert len(result["errors"]) == 1  # 에러 개수 확인

    @patch("crawler.coordinator.ProgressTracker")
    def test_crawl_multiple_dongs_with_progress_tracking(self, mock_progress_tracker_class):
        """여러 동 크롤링 시 Progress tracking 테스트"""
        # Mock ProgressTracker
        mock_tracker = MagicMock()
        mock_progress_tracker_class.return_value = mock_tracker

        # Coordinator 초기화
        coordinator = CrawlCoordinator(
            config_or_output_dir=self.temp_dir,
            checkpoint_path=self.checkpoint_path,
            enable_progress_tracking=True,
        )

        # Mock functions
        mock_fetch_detail = MagicMock(return_value={"pyeong_types": []})
        mock_fetch_transactions = MagicMock(return_value=[])

        # Mock 동별 단지 데이터
        dong_complexes = [
            {
                "dong_code": "11111",
                "dong_name": "동1",
                "complexes": [{"complex_id": "111515", "complex_name": "단지1"}],
            },
            {
                "dong_code": "22222",
                "dong_name": "동2",
                "complexes": [{"complex_id": "111516", "complex_name": "단지2"}],
            },
        ]

        # 여러 동 크롤링 실행
        coordinator.crawl_multiple_dongs(
            dong_complexes=dong_complexes,
            fetch_complex_detail=mock_fetch_detail,
            fetch_transaction_history=mock_fetch_transactions,
            resume=False,
        )

        # Progress tracker 메서드 호출 확인
        assert mock_tracker.start_crawling.call_count == 1
        mock_tracker.start_crawling.assert_called_with(total_dongs=2, total_complexes=2)

        assert mock_tracker.start_dong.call_count == 2
        assert mock_tracker.complete_dong.call_count == 2

        assert mock_tracker.finish_crawling.call_count == 1

    def test_progress_file_creation(self):
        """Progress 파일 생성 확인 테스트"""
        coordinator = CrawlCoordinator(
            config_or_output_dir=self.temp_dir,
            checkpoint_path=self.checkpoint_path,
            enable_progress_tracking=True,
            progress_report_interval=1,  # 1초 간격
        )

        # Mock functions
        MagicMock(return_value={"pyeong_types": []})
        MagicMock(return_value=[])

        # 진행 상황 파일이 초기에 생성되는지 확인
        progress_file = self.temp_dir / "progress.json"
        log_file = self.temp_dir / "progress.log"

        # start_crawling 호출 후 파일 생성 확인
        coordinator.progress_tracker.start_crawling(total_dongs=1, total_complexes=1)
        assert progress_file.exists()
        assert log_file.exists()

    def test_progress_log_content(self):
        """Progress 로그 내용 확인 테스트"""
        coordinator = CrawlCoordinator(
            config_or_output_dir=self.temp_dir,
            checkpoint_path=self.checkpoint_path,
            enable_progress_tracking=True,
        )

        # Mock functions
        mock_fetch_detail = MagicMock(return_value={"pyeong_types": []})
        mock_fetch_transactions = MagicMock(return_value=[])

        # 동 크롤링 실행
        complexes = [{"complex_id": "111515", "complex_name": "단지1"}]
        coordinator.crawl_dong(
            dong_code="12345",
            dong_name="테스트동",
            complexes=complexes,
            fetch_complex_detail=mock_fetch_detail,
            fetch_transaction_history=mock_fetch_transactions,
        )

        # 로그 파일 내용 확인
        log_file = self.temp_dir / "progress.log"
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8") as f:
                log_content = f.read()
                assert "progress_tracking_started" in log_content
                assert "dong_started" in log_content
