"""로깅 설정 관련 테스트"""

import logging
from pathlib import Path
from unittest.mock import Mock, patch


from crawler.utils.logging_config import (
    CrawlLogger,
    SensitiveDataFilter,
    configure_logging,
    sensitive_data_processor,
)


class TestSensitiveDataFilter:
    """SensitiveDataFilter 테스트"""

    def test_email_masking(self):
        """이메일 주소 마스킹 테스트"""
        filter_obj = SensitiveDataFilter()

        # 기본 이메일
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="User email: user@example.com",
            args=(),
            exc_info=None,
        )

        result = filter_obj.filter(record)
        assert result is True
        assert "user@example.com" not in record.msg
        assert "u***@example.com" in record.msg or "***@example.com" in record.msg

    def test_phone_masking(self):
        """전화번호 마스킹 테스트"""
        filter_obj = SensitiveDataFilter()

        # 여러 전화번호 형식
        test_cases = [
            ("Phone: 010-1234-5678", "010-****-5678"),
            ("Contact: 01112345678", "011****5678"),
            ("Tel: +82-10-1234-5678", "+82-10-****-5678"),
        ]

        for original, expected_mask in test_cases:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=original,
                args=(),
                exc_info=None,
            )

            filter_obj.filter(record)
            assert expected_mask in record.msg or "****" in record.msg

    def test_token_masking(self):
        """토큰 및 API 키 마스킹 테스트"""
        filter_obj = SensitiveDataFilter()

        # Bearer 토큰
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Authorization: Bearer abc123def456ghi789",
            args=(),
            exc_info=None,
        )

        result = filter_obj.filter(record)
        assert result is True
        assert "abc123def456ghi789" not in record.msg
        # Authorization: Bearer abc123def... -> Authorization: [REDACTED]
        assert "[REDACTED]" in record.msg

        # API 키
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="API key: sk-1234567890abcdef",
            args=(),
            exc_info=None,
        )

        filter_obj.filter(record)
        assert "1234567890abcdef" not in record.msg
        assert "[REDACTED]" in record.msg or "sk-***" in record.msg

    def test_structlog_processor(self):
        """structlog용 프로세서 함수 테스트"""

        info_dict = {
            "user_email": "test@example.com",
            "phone": "010-1234-5678",
            "api_key": "sk-1234567890",
            "normal_field": "normal_value",
        }

        result = sensitive_data_processor(None, "info", info_dict)

        # 민감 데이터는 마스킹되어야 함
        assert "test@example.com" not in str(result)
        assert "010-1234-5678" not in str(result)
        assert "sk-1234567890" not in str(result)

        # 일반 데이터는 유지되어야 함
        assert "normal_value" in str(result)


class TestConfigureLogging:
    """configure_logging 함수 테스트"""

    @patch("crawler.utils.logging_config.logging.getLogger")
    def test_configure_logging_setup(self, mock_get_logger):
        """로깅 설정이 올바르게 적용되는지 테스트"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # 임시 로그 디렉토리 설정
        log_dir = Path("/tmp/test_logs")

        configure_logging(log_dir=str(log_dir), level="INFO")

        # getLogger가 호출되었는지 확인
        mock_get_logger.assert_called()

        # 로거에 핸들러가 추가되었는지 확인
        assert mock_logger.addHandler.called
        assert mock_logger.setLevel.called


class TestCrawlLogger:
    """CrawlLogger 테스트"""

    def test_init(self):
        """CrawlLogger 초기화 테스트"""
        crawl_logger = CrawlLogger("test_crawler")
        assert crawl_logger.crawler_name == "test_crawler"
        assert crawl_logger.request_count == 0
        assert crawl_logger.start_time > 0

    def test_log_api_call_increments_count(self):
        """API 호출 시 request_count 증가 확인"""
        # structlog Mock 설정
        with patch("crawler.utils.logging_config.structlog.get_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            crawl_logger = CrawlLogger("test_crawler")
            initial_count = crawl_logger.request_count

            crawl_logger.log_api_call("/api/test")

            assert crawl_logger.request_count == initial_count + 1
            # 메서드 호출 확인
            mock_logger.info.assert_called()

    def test_log_retry_with_context(self):
        """재시도 로깅 테스트"""
        with patch("crawler.utils.logging_config.structlog.get_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            crawl_logger = CrawlLogger("test_crawler")
            crawl_logger.log_retry(
                attempt=3,
                max_attempts=5,
                error="Connection timeout",
                delay=2.0,
            )

            # warning 메서드가 호출되었는지 확인
            mock_logger.warning.assert_called()

    def test_log_progress_calculation(self):
        """진행률 계산 테스트"""
        with patch("crawler.utils.logging_config.structlog.get_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            crawl_logger = CrawlLogger("test_crawler")
            crawl_logger.log_progress(current=50, total=100)

            # info 메서드가 호출되었는지 확인
            mock_logger.info.assert_called()

    def test_log_resource_usage(self):
        """리소스 사용량 로깅 테스트"""
        with patch("crawler.utils.logging_config.structlog.get_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            crawl_logger = CrawlLogger("test_crawler")
            crawl_logger.log_resource_usage(
                memory_mb=256.5,
                cpu_percent=45.2,
            )

            # info 메서드가 호출되었는지 확인
            mock_logger.info.assert_called()

    def test_error_with_context_type(self):
        """에러 타입 저장 테스트"""
        with patch("crawler.utils.logging_config.structlog.get_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            crawl_logger = CrawlLogger("test_crawler")

            try:
                raise ValueError("Test error")
            except Exception as e:
                crawl_logger.error_with_context(
                    error=e,
                    context={"url": "https://example.com"},
                )

                # error 메서드가 호출되었는지 확인
                mock_logger.error.assert_called()

    def test_crawl_lifecycle_methods(self):
        """크롤링 생명주기 메서드 테스트"""
        with patch("crawler.utils.logging_config.structlog.get_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            crawl_logger = CrawlLogger("test_crawler")

            # 시작 로그
            crawl_logger.log_crawl_start(total_items=100)
            mock_logger.info.assert_called()

            # 종료 로그
            crawl_logger.log_crawl_end(items_processed=95, success=True)
            # info 메서드가 총 2번 호출되어야 함 (시작 + 종료)
            assert mock_logger.info.call_count == 2
