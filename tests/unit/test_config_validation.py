"""CrawlerConfig 검증 기능 테스트"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from crawler.config import CrawlerConfig


class TestConfigValidation:
    """CrawlerConfig 검증 기능 테스트"""

    def test_invalid_page_size_validation(self):
        """유효하지 않은 page_size 값 검증"""
        # page_size가 1 미만인 경우
        with pytest.raises(ValueError, match="page_size은 1 이상이어야 합니다"):
            CrawlerConfig(page_size=0)

        # page_size가 100 초과인 경우
        with pytest.raises(ValueError, match="page_size은 100 이하여야 합니다"):
            CrawlerConfig(page_size=101)

    def test_negative_timeout_validation(self):
        """음수 timeout 값 검증"""
        # timeout이 0 미만인 경우
        with pytest.raises(ValueError, match="timeout은 0 이상이어야 합니다"):
            CrawlerConfig(timeout=-1)

        # timeout이 300 초과인 경우
        with pytest.raises(ValueError, match="timeout은 300 이하여야 합니다"):
            CrawlerConfig(timeout=301)

    def test_invalid_retry_attempts(self):
        """유효하지 않은 retry_attempts 값 검증"""
        # retry_attempts가 0 미만인 경우
        with pytest.raises(ValueError, match="retry_attempts은 0 이상이어야 합니다"):
            CrawlerConfig(retry_attempts=-1)

        # retry_attempts가 10 초과인 경우
        with pytest.raises(ValueError, match="retry_attempts은 10 이하여야 합니다"):
            CrawlerConfig(retry_attempts=11)

    @patch.dict(
        os.environ,
        {
            "CRAWLER_PAGE_SIZE": "0",
            "CRAWLER_TIMEOUT": "301",
            "CRAWLER_RETRY_ATTEMPTS": "-1",
            "CRAWLER_DELAY_SECONDS": "0.1",
            "CRAWLER_MAX_WORKERS": "0",
        },
    )
    def test_config_from_env_with_invalid_values(self):
        """환경 변수에서 유효하지 않은 값으로 설정 생성 시 검증"""
        with pytest.raises(ValueError):
            CrawlerConfig.from_env()

    def test_output_path_generation(self):
        """output_file이 없을 때 자동 생성 테스트"""
        config = CrawlerConfig()
        generated_path = config.create_output_path()

        # output 디렉토리에 생성되어야 함
        assert generated_path.parent == Path("output")
        # 타임스탬프가 포함되어야 함
        assert "data_" in generated_path.name
        assert generated_path.suffix == ".csv"

    def test_output_path_generation_with_custom_dir(self):
        """사용자 정의 디렉토리에 output_path 생성 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = CrawlerConfig()
            generated_path = config.create_output_path(base_dir=temp_dir)

            assert generated_path.parent == Path(temp_dir)
            assert generated_path.name.startswith("data_")
            assert generated_path.suffix == ".csv"

    def test_config_compatibility_validation(self):
        """설정 간 호환성 검증"""
        # 너무 많은 worker와 너무 짧은 delay 조합
        with pytest.raises(
            ValidationError, match="너무 많은 worker와 짧은 delay는 서버에 부하를 줄 수 있습니다"
        ):
            CrawlerConfig(max_workers=10, delay_seconds=0.1, use_threading=True)

        # timeout이 retry_attempts * retry_delay보다 작은 경우
        with pytest.raises(ValidationError, match="timeout.*전체 재시도 시간"):
            CrawlerConfig(timeout=5, retry_attempts=3, retry_delay=2)

    def test_valid_config_values(self):
        """유효한 설정값으로 생성 성공 테스트"""
        # 모든 유효한 값으로 설정 생성
        config = CrawlerConfig(
            page_size=50,
            timeout=30,
            retry_attempts=3,
            retry_delay=1,
            delay_seconds=1.0,
            max_workers=4,
            use_threading=True,
        )

        assert config.page_size == 50
        assert config.timeout == 30
        assert config.retry_attempts == 3
        assert config.retry_delay == 1
        assert config.delay_seconds == 1.0
        assert config.max_workers == 4
        assert config.use_threading is True

    def test_output_file_validation(self):
        """output_file 경로 검증"""
        # 존재하지 않는 디렉토리에 파일 지정
        with pytest.raises(ValueError, match="output_file의 상위 디렉토리가 존재하지 않습니다"):
            CrawlerConfig(output_file="/nonexistent/directory/data.csv")

    def test_delay_range_validation(self):
        """delay_seconds 범위 검증"""
        # delay_seconds가 0.1 미만인 경우
        with pytest.raises(ValueError, match="delay_seconds은 0.1 이상이어야 합니다"):
            CrawlerConfig(delay_seconds=0.05)

        # delay_seconds가 60 초과인 경우
        with pytest.raises(ValueError, match="delay_seconds은 60 이하여야 합니다"):
            CrawlerConfig(delay_seconds=61)

    def test_max_workers_validation(self):
        """max_workers 범위 검증"""
        # max_workers가 1 미만인 경우
        with pytest.raises(ValueError, match="max_workers은 1 이상이어야 합니다"):
            CrawlerConfig(max_workers=0)

        # max_workers가 20 초과인 경우
        with pytest.raises(ValueError, match="max_workers은 20 이하여야 합니다"):
            CrawlerConfig(max_workers=21)
