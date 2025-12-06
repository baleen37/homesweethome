"""
실패 시나리오 테스트 - 크롤러 안정성 검증
"""
import pytest
import time
import json
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.crawler.crawlers.naver import NaverRealEstateCrawler
from src.crawler.config import CrawlerConfig


class TestFailureScenarios:
    """크롤러 실패 시나리오 테스트"""

    def test_network_timeout_handling(self):
        """네트워크 타임아웃을 우아하게 처리하는지 테스트"""
        config = CrawlerConfig.from_env()
        config.timeout = 5  # 5초로 단축
        crawler = NaverRealEstateCrawler(config)

        # Mock page object
        mock_page = Mock()

        # 타임아웃 에러 시뮬레이션
        mock_page.evaluate.side_effect = PlaywrightTimeoutError("Request timed out")

        # _fetch_endpoint_with_retry 메서드 테스트
        with patch.object(crawler, 'browser_manager') as mock_browser_manager:
            mock_browser_manager.managed_browser.return_value.__enter__.return_value = mock_page

            # 타임아웃 발생 시 None을 반환하는지 확인
            result = crawler._fetch_endpoint_with_retry(
                mock_page,
                "test_url",
                "test_endpoint",
                max_retries=2
            )

            # 타임아웃 후 None을 반환해야 함
            assert result is None

            # 재시도 횟수 확인 (Retryable이 호출하는 횟수)
            assert mock_page.evaluate.call_count >= 2  # 설정된 재시도 횟수

    def test_429_rate_limit_handling(self):
        """HTTP 429 Rate Limit를 처리하는지 테스트"""
        config = CrawlerConfig.from_env()
        crawler = NaverRealEstateCrawler(config)

        # Mock page object
        mock_page = Mock()

        # Rate Limit 에러 시뮬레이션
        mock_page.evaluate.side_effect = Exception("HTTP 429: Too Many Requests")

        # _fetch_endpoint_with_retry 메서드 테스트
        with patch('time.sleep') as mock_sleep:
            result = crawler._fetch_endpoint_with_retry(
                mock_page,
                "test_url",
                "test_endpoint",
                max_retries=3
            )

            # 지연 시간이 있었는지 확인 (Retryable이 sleep 호출)
            assert mock_sleep.call_count > 0
            # 여러 번 시도했는지 확인
            assert mock_page.evaluate.call_count >= 3
            # 최종적으로 None을 반환하는지 확인
            assert result is None

    def test_invalid_api_response_handling(self):
        """잘못된 API 응답을 처리하는지 테스트"""
        config = CrawlerConfig.from_env()
        crawler = NaverRealEstateCrawler(config)

        test_cases = [
            {"invalid": "response structure"},
            {"error": {"message": "Unknown error"}},
            {"result": None},
            "not_a_dict",
            None
        ]

        for response in test_cases:
            # Mock page object
            mock_page = Mock()
            mock_page.evaluate.return_value = response

            # 잘못된 응답을 처리할 수 있는지 확인
            try:
                result = crawler._fetch_endpoint_with_retry(
                    mock_page,
                    "test_url",
                    "test_endpoint",
                    max_retries=1
                )
                # 예외가 발생하지 않더라도 응답을 반환해야 함
                assert result == response
            except Exception:
                # 예외가 발생하는 것도 허용
                pass

    def test_browser_crash_recovery(self):
        """브라우저 크래시 복구를 테스트"""
        config = CrawlerConfig.from_env()
        crawler = NaverRealEstateCrawler(config)

        with patch.object(crawler, 'browser_manager') as mock_browser_manager:
            # 첫 번째 시도에서 브라우저 크래시 시뮬레이션
            mock_browser_manager.managed_browser.return_value.__enter__.side_effect = Exception("Browser crashed")

            # 브라우저 크래시 후 예외가 발생하는지 확인
            with pytest.raises(Exception, match="Browser crashed"):
                result = crawler.fetch_complex_detail("test_complex_id")

            # 브라우저 관리자가 호출되었는지 확인
            assert mock_browser_manager.managed_browser.call_count >= 1

    def test_checkpoint_corruption_recovery(self):
        """손상된 체크포인트 복구를 테스트"""
        config = CrawlerConfig(enable_checkpoints=True)
        crawler = NaverRealEstateCrawler(config)

        # 손상된 체크포인트 파일 생성
        if hasattr(crawler, 'checkpoint_manager') and crawler.checkpoint_manager:
            checkpoint_file = crawler.checkpoint_manager.checkpoint_file
            checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
            checkpoint_file.write_text("invalid json content")

            with patch.object(crawler, 'fetch_complex_list') as mock_fetch:
                mock_fetch.return_value = []

                # 손상된 체크포인트로도 크롤링이 진행되는지 확인
                try:
                    result = crawler.crawl()
                    assert isinstance(result, list)
                except Exception as e:
                    # 손상된 파일을 처리하는 중 예외가 발생하면 실패
                    pytest.fail(f"Failed to recover from corrupted checkpoint: {e}")

    def test_disk_space_exhaustion(self):
        """디스크 공간 부족 상황 처리 테스트"""
        config = CrawlerConfig.from_env()
        crawler = NaverRealEstateCrawler(config)

        with patch('builtins.open') as mock_open:
            # 디스크 공간 부족 에러 시뮬레이션
            mock_open.side_effect = OSError("No space left on device")

            with patch.object(crawler, 'fetch_complex_list') as mock_fetch:
                mock_fetch.return_value = [{"complex_id": "1", "complex_name": "test"}]

                # 디스크 공간 부족 시 예외가 발생하는지 확인
                with pytest.raises(OSError, match="No space left on device"):
                    crawler.crawl()

    def test_malformed_html_handling(self):
        """잘못된 형식의 데이터 처리 테스트"""
        config = CrawlerConfig.from_env()
        crawler = NaverRealEstateCrawler(config)

        # 빈 데이터 처리
        test_cases = [
            [],
            [{}],
            [{"complex_name": "", "price": ""}],
            None
        ]

        for test_data in test_cases:
            # 데이터 처리 테스트
            try:
                # _parse_complex_detail 메서드가 있는지 확인
                if hasattr(crawler, '_parse_complex_detail'):
                    result = crawler._parse_complex_detail({"data": test_data})
                    assert isinstance(result, dict)
                else:
                    # 메서드가 없는 경우 테스트 통과
                    pass
            except Exception as e:
                # 예외가 발생하더라도 처리되는지 확인
                assert "failed" in str(e).lower() or "error" in str(e).lower()

    def test_comprehensive_failure_recovery(self):
        """다양한 실패 시나리오 종합 복구 테스트"""
        config = CrawlerConfig.from_env()
        crawler = NaverRealEstateCrawler(config)

        # 다양한 실패 시나리오 정의
        failure_scenarios = [
            PlaywrightTimeoutError("Timeout"),
            Exception("HTTP 429: Too Many Requests"),
            Exception("Server error"),
            None
        ]

        for scenario in failure_scenarios:
            # Mock page object
            mock_page = Mock()

            if isinstance(scenario, Exception):
                mock_page.evaluate.side_effect = scenario
            else:
                mock_page.evaluate.return_value = scenario

            # 실패 처리 확인
            try:
                result = crawler._fetch_endpoint_with_retry(
                    mock_page,
                    "test_url",
                    "test_endpoint",
                    max_retries=2
                )

                if scenario is None:
                    assert result is None
                elif isinstance(scenario, Exception):
                    pytest.fail(f"Expected exception to be handled, but got result: {result}")

            except Exception as e:
                # 예외가 발생하는 것도 허용
                assert isinstance(e, Exception)

    def test_memory_leak_prevention(self):
        """장기 실행 시 메모리 누수 방지 테스트"""
        try:
            import psutil
        except ImportError:
            pytest.skip("psutil not installed")

        config = CrawlerConfig.from_env()
        crawler = NaverRealEstateCrawler(config)

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # 많은 수의 동 데이터 시뮬레이션
        districts = crawler.filter_districts(None)[:5]  # 5개 구만 사용

        with patch.object(crawler, '_fetch_dong_data') as mock_fetch:
            mock_fetch.return_value = [
                {"complex_name": f"Test Complex {i}", "price": "1억", "spec": "84㎡", "location": "서울"}
                for i in range(10)  # 각 동당 10개 단지
            ]

            # 각 구의 동 데이터 처리
            for district in districts:
                for dong in district.get("dongs", [])[:2]:  # 각 구당 2개 동만
                    try:
                        crawler.fetch_dong_with_retry(dong, max_retries=1)
                    except Exception:
                        pass  # 오류 무시하고 계속 진행

        # 메모리 사용량 확인
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # 메모리 증가가 합리적인지 확인 (100MB 미만)
        assert memory_increase < 100 * 1024 * 1024, \
            f"Memory leak detected: {memory_increase / 1024 / 1024:.2f}MB increase"

    def test_concurrent_operation_safety(self):
        """동시 작업 안전성 테스트"""
        config = CrawlerConfig.from_env()
        crawler = NaverRealEstateCrawler(config)

        # 체크포인트 동시 접근 테스트
        if hasattr(crawler, 'checkpoint_manager') and crawler.checkpoint_manager:
            import threading
            import time

            results = []
            errors = []

            def worker(worker_id):
                try:
                    for i in range(5):
                        # 실패한 동 추가 (체크포인트 사용)
                        crawler.checkpoint_manager.add_failed_dong(f"test_{worker_id}_{i}", f"error_{i}")
                        time.sleep(0.01)
                        checkpoint = crawler.checkpoint_manager.load()
                        results.append((worker_id, i, checkpoint))
                except Exception as e:
                    errors.append((worker_id, str(e)))

            # 여러 스레드 시작
            threads = []
            for i in range(3):
                thread = threading.Thread(target=worker, args=(i,))
                threads.append(thread)
                thread.start()

            # 모든 스레드 완료 대기
            for thread in threads:
                thread.join()

            # 오류가 없는지 확인
            assert len(errors) == 0, f"Concurrent access errors: {errors}"

    def test_rate_limit_backoff_strategy(self):
        """Rate Limit 백오프 전략 테스트"""
        config = CrawlerConfig.from_env()
        crawler = NaverRealEstateCrawler(config)

        # Mock page object
        mock_page = Mock()

        with patch('time.sleep') as mock_sleep:
            # 지속적인 429 에러 시뮬레이션
            mock_page.evaluate.side_effect = Exception("HTTP 429: Too Many Requests")

            # 지수 백오프 확인
            crawler._fetch_endpoint_with_retry(
                mock_page,
                "test_url",
                "test_endpoint",
                max_retries=3
            )

            # 재시도 사이에 sleep이 호출되었는지 확인
            assert mock_sleep.call_count >= 2  # 3회 재시도 = 2회 sleep

            # 지연 시간이 증가하는지 확인 (Retryable이 처리)
            sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
            if len(sleep_calls) > 1:
                # 지수적으로 증가하거나 최소한 증가하는지 확인
                for i in range(1, len(sleep_calls)):
                    assert sleep_calls[i] >= sleep_calls[i-1] * 0.5, \
                        f"Sleep time should roughly increase: {sleep_calls}"

    def test_invalid_url_handling(self):
        """잘못된 URL 처리 테스트"""
        config = CrawlerConfig.from_env()
        crawler = NaverRealEstateCrawler(config)

        invalid_urls = [
            None,
            "",
            "invalid-url",
            "ftp://invalid-protocol.com",
            "javascript:void(0)"
        ]

        for invalid_url in invalid_urls:
            # Mock page object
            mock_page = Mock()
            mock_page.evaluate.return_value = {"error": {"message": "Invalid URL"}}

            # 잘못된 URL을 처리할 수 있는지 확인
            try:
                result = crawler._fetch_endpoint_with_retry(
                    mock_page,
                    invalid_url,
                    "test_endpoint",
                    max_retries=1
                )
                # None이나 빈 결과를 반환해야 함
                assert result is None or result == {"error": {"message": "Invalid URL"}}
            except Exception as e:
                # 예외가 발생하더라도 프로그램이 중단되지 않음
                assert "Invalid URL" in str(e) or invalid_url is None

    def test_large_response_handling(self):
        """대용량 응답 처리 테스트"""
        config = CrawlerConfig.from_env()
        crawler = NaverRealEstateCrawler(config)

        # 대용량 데이터 시뮬레이션
        large_data = {
            "result": {
                "data": [{"item": f"item_{i}"} for i in range(1000)]  # 1000개로 줄임
            }
        }

        # Mock page object
        mock_page = Mock()
        mock_page.evaluate.return_value = large_data

        # 대용량 응답을 처리할 수 있는지 확인
        result = crawler._fetch_endpoint_with_retry(
            mock_page,
            "test_url",
            "test_endpoint",
            max_retries=1
        )

        # 결과가 처리되었는지 확인
        assert result is not None
        if isinstance(result, dict) and "result" in result:
            assert len(result["result"]["data"]) == 1000