"""호갱노노 크롤러 체크포인트 기능 테스트

체크포인트 관리, 이어하기 기능, 실패한 지역 재시도 등을 테스트합니다.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from crawler.config import CrawlerConfig
from crawler.crawlers.hogangnono import HogangnonoCrawler
from crawler.utils.checkpoint import CheckpointManager


class TestHogangnonoCheckpointIntegration:
    """호갱노노 크롤러 체크포인트 통합 테스트"""

    @pytest.fixture
    def temp_dir(self):
        """임시 디렉토리 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def test_config(self, temp_dir):
        """테스트용 CrawlerConfig 생성"""
        return CrawlerConfig(
            site_name="hogangnono",
            base_url="https://hogangnono.com",
            output_file=str(temp_dir / "test_output.csv"),
            headers={},
            max_retries=3,
            retry_delay=1.0,
            timeout=30.0,
            rate_limit_delay=1.0,
        )

    @pytest.fixture
    def crawler(self, test_config):
        """테스트용 HogangnonoCrawler 생성"""
        with patch("crawler.crawlers.hogangnono.HogangnonoAPIClient"):
            with patch("crawler.crawlers.hogangnono.BrowserManager"):
                crawler = HogangnonoCrawler(test_config)
                return crawler

    def test_checkpoint_initialization(self, crawler):
        """체크포인트 초기화 테스트"""
        assert crawler.checkpoint_manager is not None
        assert isinstance(crawler.checkpoint_manager, CheckpointManager)
        # 디렉토리는 생성되지만 파일은 데이터 저장 시 생성됨
        assert crawler.checkpoint_manager.checkpoint_path.parent.exists()

    def test_region_key_generation(self, crawler):
        """지역 키 생성 테스트"""
        # district만 있는 경우
        assert crawler.should_skip_region("강남구") is False

        # district와 dong이 있는 경우
        assert crawler.should_skip_region("강남구", "역삼동") is False

    def test_region_checkpoint_saving(self, crawler):
        """지역 완료 시 체크포인트 저장 테스트"""
        # Mock the browser manager and parse method
        with patch.object(crawler, "parse", return_value=[]):
            with patch.object(crawler, "browser_manager") as mock_browser_manager:
                mock_browser_manager.managed_browser.return_value.__enter__.return_value = (
                    MagicMock()
                )

                # 지역 크롤링 실행
                crawler.crawl_region("강남구", "역삼동")

                # 체크포인트에 저장되었는지 확인
                region_key = "강남구_역삼동"
                assert crawler.checkpoint_manager.is_processed(region_key)

                # 저장된 데이터 확인
                saved_data = crawler.checkpoint_manager.get(region_key)
                assert saved_data is not None
                assert saved_data["district"] == "강남구"
                assert saved_data["dong"] == "역삼동"

    def test_should_skip_region(self, crawler):
        """이미 처리된 지역 건너뛰기 테스트"""
        # 체크포인트에 데이터 저장
        region_key = "강남구_역삼동"
        crawler.checkpoint_manager.save(
            region_key,
            {
                "district": "강남구",
                "dong": "역삼동",
                "listings_count": 10,
            },
        )

        # 건너뛰기 확인
        assert crawler.should_skip_region("강남구", "역삼동") is True
        assert crawler.should_skip_region("강남구", "개포동") is False

    def test_crawl_multiple_regions_with_resume(self, crawler):
        """여러 지역 크롤링 및 이어하기 테스트"""
        # 크롤링할 지역 목록
        regions = [
            {"district": "강남구", "dong": "역삼동"},
            {"district": "강남구", "dong": "개포동"},
        ]

        # 첫 번째 지역은 직접 체크포인트에 저장 (처리된 것으로 간주)
        crawler.checkpoint_manager.save(
            "강남구_역삼동",
            {
                "district": "강남구",
                "dong": "역삼동",
                "listings_count": 5,
            },
        )

        # crawl_region mock
        with patch.object(crawler, "crawl_region") as mock_crawl:
            mock_crawl.return_value = [{"apt_id": "2", "complex_name": "개포아파트"}]

            # resume=True이므로 이미 처리된 역삼동은 건너뛰어야 함
            stats = crawler.crawl_multiple_regions(regions, resume=True)

            # 역삼동은 건너뛰고 개포동만 처리
            assert mock_crawl.call_count == 1  # 개포동만 호출
            assert mock_crawl.call_args[0] == ("강남구", "개포동")  # 개포동으로 호출되었는지 확인
            assert stats["regions_skipped"] == 1
            assert stats["regions_processed"] == 1

    def test_failed_region_tracking(self, crawler):
        """실패한 지역 추적 테스트"""
        # 실패한 지역 기록
        region_key = "강남구_논현동"
        error_msg = "Network timeout"

        crawler.checkpoint_manager.add_failed_dong(region_key, error_msg)

        # 실패 목록 확인
        checkpoint_data = crawler.checkpoint_manager.load()
        failed_dongs = checkpoint_data.get("failed_dongs", [])

        assert len(failed_dongs) > 0
        assert any(entry["dong_code"] == region_key for entry in failed_dongs)
        assert any(entry["error"] == error_msg for entry in failed_dongs)

    def test_retry_failed_regions(self, crawler):
        """실패한 지역 재시도 테스트"""
        # 실패한 지역 추가
        region_key = "강남구_논현동"
        crawler.checkpoint_manager.add_failed_dong(region_key, "Network error")

        # Mock 성공적인 재시도
        with patch.object(crawler, "crawl_region", return_value=[{"apt_id": "3"}]) as mock_crawl:
            stats = crawler.retry_failed_regions(max_retries=1)

            assert stats["total_retried"] == 1
            assert region_key in stats["retry_success"]
            assert mock_crawl.called

            # 재시도 성공 후 실패 목록에서 제거되었는지 확인
            checkpoint_data = crawler.checkpoint_manager.load()
            failed_dongs = checkpoint_data.get("failed_dongs", [])
            assert not any(entry["dong_code"] == region_key for entry in failed_dongs)

    def test_checkpoint_summary(self, crawler):
        """체크포인트 요약 정보 테스트"""
        # 일부 데이터 추가
        crawler.checkpoint_manager.save(
            "강남구_역삼동",
            {
                "district": "강남구",
                "dong": "역삼동",
                "listings_count": 10,
            },
        )
        crawler.checkpoint_manager.add_failed_dong("강남구_논현동", "Network error")

        # 요약 정보 확인
        summary = crawler.get_checkpoint_summary()

        assert "last_dong" in summary
        assert "total_complexes_processed" in summary
        assert "failed_dongs_count" in summary
        assert summary["failed_dongs_count"] > 0

    def test_rate_limiter_state_persistence(self, crawler):
        """Rate limiter 상태 저장/복원 테스트"""
        # Rate limiter 상태 변경
        crawler.rate_limiter.current_delay = 8.0  # 기본값인 5.0과 다른 값으로 변경
        crawler.rate_limiter.success_count = 10
        crawler.rate_limiter.error_count = 2

        # 상태 저장
        crawler.checkpoint_manager._save_legacy(rate_limiter=crawler.rate_limiter)

        # 새 rate limiter 생성
        new_rate_limiter = type(crawler.rate_limiter)()
        assert new_rate_limiter.current_delay != 8.0

        # 상태 복원
        restored = crawler.checkpoint_manager.restore_rate_limiter_state(new_rate_limiter)
        assert restored is True
        assert new_rate_limiter.current_delay == 8.0
        assert new_rate_limiter.success_count == 10
        assert new_rate_limiter.error_count == 2

    def test_checkpoint_data_integrity(self, crawler, temp_dir):
        """체크포인트 데이터 무결성 테스트"""
        # 여러 지역 데이터 저장
        regions_data = {
            "강남구_역삼동": {"district": "강남구", "dong": "역삼동", "listings_count": 10},
            "강남구_개포동": {"district": "강남구", "dong": "개포동", "listings_count": 15},
            "강남구_논현동": {"district": "강남구", "dong": "논현동", "listings_count": 8},
        }

        for region_key, data in regions_data.items():
            crawler.checkpoint_manager.save(region_key, data)

        # 파일 직접 읽어서 데이터 확인
        checkpoint_path = crawler.checkpoint_manager.checkpoint_path
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        # 모든 데이터가 올바르게 저장되었는지 확인
        for region_key, expected_data in regions_data.items():
            assert region_key in saved_data
            assert saved_data[region_key]["district"] == expected_data["district"]
            assert saved_data[region_key]["dong"] == expected_data["dong"]
            assert saved_data[region_key]["listings_count"] == expected_data["listings_count"]

    def test_concurrent_checkpoint_access(self, crawler, temp_dir):
        """동시 체크포인트 접근 테스트 (스레드 세이프티)"""
        import threading
        import time

        results = []
        errors = []

        def update_checkpoint(region_id):
            try:
                for i in range(5):
                    crawler.checkpoint_manager.save(
                        f"region_{region_id}",
                        {
                            "region_id": region_id,
                            "update_count": i + 1,
                            "timestamp": time.time(),
                        },
                    )
                    time.sleep(0.01)  # 짧은 대기
                results.append(region_id)
            except Exception as e:
                errors.append((region_id, str(e)))

        # 여러 스레드에서 동시에 업데이트
        threads = []
        for i in range(3):
            thread = threading.Thread(target=update_checkpoint, args=(i,))
            threads.append(thread)
            thread.start()

        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()

        # 에러 없이 완료되었는지 확인
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 3

        # 모든 데이터가 올바르게 저장되었는지 확인
        checkpoint_data = crawler.checkpoint_manager.load()
        for i in range(3):
            region_key = f"region_{i}"
            assert region_key in checkpoint_data
            assert checkpoint_data[region_key]["update_count"] == 5
