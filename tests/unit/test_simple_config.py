"""단순화된 설정 클래스 테스트"""

from pathlib import Path
from unittest.mock import patch, MagicMock

from crawler.config import Config, USER_AGENT


class TestConfig:
    """Config 클래스 테스트"""

    def test_config_initialization(self):
        """Config 기본 초기화 테스트"""
        config = Config()

        # 하드코딩된 기본값 확인
        assert config.BASE_URL == "https://hogangnono.com"
        assert config.TIMEOUT == 30
        assert config.HEADLESS is True
        assert config.RATE_LIMIT_DELAY == 2.0
        assert config.RETRY_ATTEMPTS == 3
        assert config.RETRY_DELAY == 1.0
        assert config.PAGE_SIZE == 50
        assert config.USE_THREADING is False
        assert config.MAX_WORKERS == 4
        assert config.DEFAULT_PROPERTY_TYPE == "apartment"
        assert config.DEFAULT_TRANSACTION_TYPE == "sale"
        assert config.OUTPUT_DIR == "output"
        assert config.LOG_LEVEL == "INFO"
        assert config.REGION_BOUNDS == [37.413294, 126.734086, 37.715133, 127.183394]

    def test_user_agent_constant(self):
        """USER_AGENT 상수 테스트"""
        assert "Mozilla" in USER_AGENT
        assert "Chrome" in USER_AGENT
        assert "Safari" in USER_AGENT

    def test_create_output_path(self):
        """출력 파일 경로 생성 테스트"""
        config = Config()

        # 기본 출력 디렉토리 사용
        path = config.create_output_path()
        assert path.parent == Path("output")
        assert path.suffix == ".csv"
        assert "data_" in path.name

        # 사용자 지정 출력 디렉토리 사용
        custom_path = config.create_output_path("custom_output")
        assert custom_path.parent == Path("custom_output")
        assert custom_path.suffix == ".csv"

    @patch("crawler.config.Path")
    def test_create_output_path_makes_directory(self, mock_path):
        """create_output_path가 디렉토리를 생성하는지 테스트"""
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance

        config = Config()
        config.create_output_path("test_dir")

        mock_path_instance.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_for_integration_test(self):
        """통합 테스트용 설정 생성 테스트"""
        config = Config.for_integration_test("/tmp/test")

        # 통합 테스트용 설정값 확인
        assert config.OUTPUT_DIR == "/tmp/test"
        assert config.TIMEOUT == 30
        assert config.RATE_LIMIT_DELAY == 2.0
        assert config.PAGE_SIZE == 20
        assert config.USE_THREADING is False
        assert config.MAX_WORKERS == 1
        assert config.RETRY_ATTEMPTS == 3
        assert config.RETRY_DELAY == 1.0

    def test_backward_compatibility_aliases(self):
        """하위 호환성 별칭 테스트"""
        from crawler.config import HogangnonoConfig, CrawlerConfig

        # 별칭이 Config 클래스와 동일한지 확인
        assert HogangnonoConfig is Config
        assert CrawlerConfig is Config

        # 별칭으로 인스턴스 생성 테스트
        hogangnono_config = HogangnonoConfig()
        crawler_config = CrawlerConfig()

        assert isinstance(hogangnono_config, Config)
        assert isinstance(crawler_config, Config)

        # 동일한 설정값을 가지는지 확인
        assert hogangnono_config.BASE_URL == crawler_config.BASE_URL
        assert hogangnono_config.TIMEOUT == crawler_config.TIMEOUT
