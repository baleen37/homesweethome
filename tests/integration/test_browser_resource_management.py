"""
Browser resource management integration tests.

These tests verify that browser resources are properly cleaned up
even when exceptions occur during crawling.
"""

import psutil
import pytest

from crawler.crawlers.naver import NaverRealEstateCrawler
from crawler.config import CrawlerConfig


def get_chromium_process_count() -> int:
    """Count the number of Chromium processes running."""
    count = 0
    for proc in psutil.process_iter(["name"]):
        try:
            if "chromium" in proc.info["name"].lower():
                count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return count


class TestBrowserResourceManagement:
    """Test browser resource cleanup."""

    @pytest.mark.integration
    def test_browser_resource_cleanup_on_exception(self):
        """Test that browser resources are cleaned up even when exceptions occur."""
        # Count initial Chromium processes
        initial_count = get_chromium_process_count()

        # Create a crawler that will throw an exception
        config = CrawlerConfig()
        crawler = NaverRealEstateCrawler(config)

        # 실제 브라우저 생성 테스트 (Mock 제거)
        try:
            # 실제 브라우저를 생성하는 메서드 호출
            # 이 과정에서 브라우저가 생성되고 에러 발생 시 cleanup되어야 함
            crawler.fetch_complex_detail("101266")
        except Exception:
            # Expected to fail due to network issues or invalid ID
            # 하지만 브라우저는 제대로 정리되어야 함
            pass

        # Count Chromium processes after exception
        final_count = get_chromium_process_count()

        # Assert no new Chromium processes were leaked
        # Note: We allow some tolerance for existing browser processes
        # The key is that we don't have MORE processes than before
        assert (
            final_count <= initial_count
        ), f"Browser resource leak detected: {final_count} > {initial_count}"
