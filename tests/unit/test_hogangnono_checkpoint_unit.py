"""호갱노노 크롤러 체크포인트 기능 단위 테스트

체크포인트 관리자의 개별 기능들을 단위 테스트합니다.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from crawler.crawlers.hogangnono import HogangnonoCrawler
from crawler.utils.checkpoint import CheckpointManager


class TestHogangnonoCheckpointUnit:
    """호갱노노 크롤러 체크포인트 단위 테스트"""

    @pytest.fixture
    def temp_dir(self):
        """임시 디렉토리 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def checkpoint_manager(self, temp_dir):
        """테스트용 CheckpointManager 생성"""
        checkpoint_path = temp_dir / "test_checkpoint.json"
        return CheckpointManager(str(checkpoint_path))

    @pytest.fixture
    def mock_crawler(self, temp_dir):
        """Mock HogangnonoCrawler 생성"""
        crawler = MagicMock(spec=HogangnonoCrawler)
        crawler.checkpoint_manager = CheckpointManager(str(temp_dir / "checkpoint.json"))
        crawler.logger = MagicMock()
        crawler.rate_limiter = MagicMock()
        crawler.rate_limiter.current_delay = 2.5
        crawler.rate_limiter.success_count = 0
        crawler.rate_limiter.error_count = 0
        return crawler

    def test_checkpoint_manager_initialization(self, checkpoint_manager):
        """CheckpointManager 초기화 테스트"""
        # 디렉토리는 생성되지만 파일은 데이터 저장 시 생성됨
        assert checkpoint_manager.checkpoint_path.parent.exists()
        assert isinstance(checkpoint_manager.checkpoint, dict)
        assert "last_dong" in checkpoint_manager.checkpoint
        assert "failed_dongs" in checkpoint_manager.checkpoint

    def test_checkpoint_save_and_load(self, checkpoint_manager):
        """체크포인트 저장 및 로드 테스트"""
        test_data = {
            "test_key": {
                "district": "강남구",
                "dong": "역삼동",
                "listings_count": 10,
            }
        }

        # 저장
        checkpoint_manager.save("test_key", test_data["test_key"])
        assert checkpoint_manager.is_processed("test_key")

        # 로드
        loaded_data = checkpoint_manager.get("test_key")
        assert loaded_data == test_data["test_key"]

    def test_checkpoint_update(self, checkpoint_manager):
        """체크포인트 업데이트 테스트"""
        # 초기 데이터 저장
        checkpoint_manager.save("region1", {"count": 1})

        # 업데이트
        checkpoint_manager.update({"region1": {"count": 2}, "region2": {"count": 1}})

        # 확인
        assert checkpoint_manager.get("region1")["count"] == 2
        assert checkpoint_manager.get("region2")["count"] == 1

    def test_checkpoint_remove(self, checkpoint_manager):
        """체크포인트 삭제 테스트"""
        # 데이터 저장
        checkpoint_manager.save("test_region", {"data": "test"})

        # 삭제
        removed = checkpoint_manager.remove("test_region")
        assert removed is True
        assert not checkpoint_manager.is_processed("test_region")

        # 없는 데이터 삭제
        removed = checkpoint_manager.remove("nonexistent")
        assert removed is False

    def test_checkpoint_clear(self, checkpoint_manager):
        """체크포인트 전체 삭제 테스트"""
        # 데이터 저장
        checkpoint_manager.save("region1", {"data": "test1"})
        checkpoint_manager.save("region2", {"data": "test2"})

        # 전체 삭제
        checkpoint_manager.clear()
        assert not checkpoint_manager.exists()
        assert checkpoint_manager.load() is None

    def test_checkpoint_stats(self, checkpoint_manager):
        """체크포인트 통계 정보 테스트"""
        # 데이터 저장
        for i in range(3):
            checkpoint_manager.save(f"region_{i}", {"data": f"test_{i}"})

        stats = checkpoint_manager.get_stats()
        assert stats["keys_count"] == 3
        assert stats["file_size_bytes"] > 0
        assert stats["exists"] is True
        assert "file_path" in stats

    def test_add_failed_dong(self, checkpoint_manager):
        """실패한 동 추가 테스트"""
        dong_code = "강남구_논현동"
        error = "Network timeout"

        # 실패 동 추가
        checkpoint_manager.add_failed_dong(dong_code, error)

        # 확인
        checkpoint_data = checkpoint_manager.load()
        failed_dongs = checkpoint_data.get("failed_dongs", [])
        assert len(failed_dongs) == 1
        assert failed_dongs[0]["dong_code"] == dong_code
        assert failed_dongs[0]["error"] == error
        assert "timestamp" in failed_dongs[0]

    def test_duplicate_failed_dong_prevention(self, checkpoint_manager):
        """중복된 실패 동 방지 테스트"""
        dong_code = "강남구_논현동"

        # 같은 동으로 여러 번 실패 기록
        checkpoint_manager.add_failed_dong(dong_code, "Error 1")
        checkpoint_manager.add_failed_dong(dong_code, "Error 2")

        # 중복되지 않았는지 확인
        checkpoint_data = checkpoint_manager.load()
        failed_dongs = checkpoint_data.get("failed_dongs", [])
        assert len(failed_dongs) == 1

    def test_get_processed_keys(self, checkpoint_manager):
        """처리된 키 목록 반환 테스트"""
        # 데이터 저장
        keys = ["region1", "region2", "region3"]
        for key in keys:
            checkpoint_manager.save(key, {"data": f"test_{key}"})

        # 처리된 키 목록 확인
        processed_keys = checkpoint_manager.get_processed_keys()
        assert set(processed_keys) == set(keys)

    def test_legacy_checkpoint_save(self, checkpoint_manager):
        """레거시 체크포인트 저장 테스트 (호환성)"""
        # 레거시 방식으로 저장
        checkpoint_manager.save(
            last_dong="강남구_역삼동",
            increment_complexes=True,
            increment_transactions=5,
        )

        # 확인
        assert checkpoint_manager.checkpoint["last_dong"] == "강남구_역삼동"
        assert checkpoint_manager.checkpoint["total_complexes_processed"] == 1
        assert checkpoint_manager.checkpoint["total_transactions_collected"] == 5
        assert checkpoint_manager.checkpoint["last_updated_at"] is not None

    def test_should_skip_dong_legacy(self, checkpoint_manager):
        """레거시 동 건너뛰기 확인 테스트"""
        # last_dong 설정
        checkpoint_manager.checkpoint["last_dong"] = "강남구_역삼동"

        # 현재 구현에서는 항상 False 반환
        assert checkpoint_manager.should_skip_dong("강남구_개포동") is False

    def test_progress_summary(self, checkpoint_manager):
        """진행 상황 요약 테스트"""
        # 데이터 설정
        checkpoint_manager.checkpoint.update(
            {
                "last_dong": "강남구_역삼동",
                "total_complexes_processed": 10,
                "total_transactions_collected": 50,
                "started_at": "2024-01-01T00:00:00",
                "last_updated_at": "2024-01-01T01:00:00",
                "failed_dongs": [{"dong_code": "강남구_논현동", "error": "Network error"}],
            }
        )

        # 요약 정보 확인
        summary = checkpoint_manager.get_progress_summary()
        assert summary["last_dong"] == "강남구_역삼동"
        assert summary["total_complexes_processed"] == 10
        assert summary["total_transactions_collected"] == 50
        assert summary["failed_dongs_count"] == 1

    @patch("crawler.crawlers.hogangnono.HogangnonoAPIClient")
    @patch("crawler.crawlers.hogangnono.BrowserManager")
    def test_crawler_with_checkpoint_integration(
        self, mock_browser_manager, mock_api_client, temp_dir
    ):
        """크롤러와 체크포인트 통합 테스트"""
        from crawler.config import CrawlerConfig

        # 설정
        config = CrawlerConfig(
            site_name="hogangnono",
            output_file=str(temp_dir / "output.csv"),
        )

        # 크롤러 생성
        crawler = HogangnonoCrawler(config)

        # 체크포인트 매니저가 초기화되었는지 확인
        assert crawler.checkpoint_manager is not None
        assert isinstance(crawler.checkpoint_manager, CheckpointManager)

        # should_skip_region 메서드 테스트
        assert hasattr(crawler, "should_skip_region")
        assert crawler.should_skip_region("강남구") is False

        # get_checkpoint_summary 메서드 테스트
        assert hasattr(crawler, "get_checkpoint_summary")
        summary = crawler.get_checkpoint_summary()
        assert isinstance(summary, dict)

    def test_atomic_write_safety(self, checkpoint_manager):
        """원자적 쓰기 안전성 테스트"""
        import threading
        import time

        results = []
        errors = []

        def concurrent_write(thread_id):
            try:
                for i in range(10):
                    data = {
                        f"thread_{thread_id}": {
                            "iteration": i,
                            "data": f"test_data_{thread_id}_{i}",
                        }
                    }
                    checkpoint_manager.save(data)
                    time.sleep(0.001)
                results.append(thread_id)
            except Exception as e:
                errors.append((thread_id, str(e)))

        # 여러 스레드에서 동시 쓰기
        threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_write, args=(i,))
            threads.append(thread)
            thread.start()

        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()

        # 에러 확인
        assert len(errors) == 0, f"Concurrent write errors: {errors}"

        # 데이터 무결성 확인
        loaded_data = checkpoint_manager.load()
        assert loaded_data is not None
        assert isinstance(loaded_data, dict)

        # 파일 크기가 0보다 커야 함 (손상되지 않았음)
        file_size = checkpoint_manager.checkpoint_path.stat().st_size
        assert file_size > 0

    def test_checkpoint_file_backup_on_corruption(self, checkpoint_manager):
        """체크포인트 파일 손상 시 백업 테스트"""
        # 정상 데이터 저장
        checkpoint_manager.save("test", {"data": "important"})

        # 파일 손상시키기 (유효하지 않은 JSON)
        with open(checkpoint_manager.checkpoint_path, "w") as f:
            f.write("{ invalid json")

        # 로드 시도 (백업 생성됨)
        loaded = checkpoint_manager.load()
        assert loaded is None

        # 백업 파일 생성 확인
        backup_path = checkpoint_manager.checkpoint_path.with_suffix(".json.backup")
        assert backup_path.exists()

    def test_checkpoint_directory_creation(self, temp_dir):
        """체크포인트 디렉토리 자동 생성 테스트"""
        nested_path = temp_dir / "nested" / "directory" / "checkpoint.json"

        # 디렉토리가 없는 경로로 CheckpointManager 생성
        CheckpointManager(str(nested_path))

        # 디렉토리가 자동 생성되었는지 확인
        assert nested_path.parent.exists()
        assert nested_path.parent.is_dir()
