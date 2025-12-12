"""
크롤러 의존성 주입을 위한 팩토리 모듈

이 모듈은 다음과 같은 기능을 제공합니다:
1. 의존성 주입을 위한 팩토리 클래스
2. 환경별 설정 지원
3. 테스트를 위한 Mock 객체 생성
"""

import json
import logging
import yaml
from pathlib import Path
from typing import Dict, Optional
from dependency_injector import containers, providers

from .config import HogangnonoConfig
from .api.hogangnono_client import HogangnonoAPIClient
from .data_mappers import HogangnonoDataMapper
from .validators.data_validator import ApartmentValidator
from .utils.enhanced_error_handler import EnhancedErrorHandler
from .utils.bbox_division import BBoxDivision
from .utils.checkpoint import CheckpointManager
from .writers.hogangnono_csv_writer import HogangnonoCSVWriter
from .crawlers.improved_hogangnono_crawler import ImprovedHogangnonoCrawler, CrawlerDependencies


class Container(containers.DeclarativeContainer):
    """의존성 주입 컨테이너"""

    # Configuration
    config = providers.Configuration()

    # Core providers
    logger = providers.Singleton(logging.getLogger, "improved_hogangnono_crawler")

    # API Client
    api_client = providers.Singleton(HogangnonoAPIClient, config=config)

    # Data Mapper
    data_mapper = providers.Singleton(
        HogangnonoDataMapper, dong_code_mapping_file=config.output_dir / "dong_code_mapping.json"
    )

    # Validator
    validator = providers.Singleton(ApartmentValidator)

    # Error Handler
    error_handler = providers.Singleton(
        EnhancedErrorHandler, max_retries=config.retry_attempts, retry_delay=config.retry_delay
    )

    # BBox Divider
    bbox_divider = providers.Singleton(BBoxDivision, max_pois_per_bbox=900)

    # Checkpoint Manager
    checkpoint_manager = providers.Singleton(
        CheckpointManager, checkpoint_path=config.output_dir / "checkpoint.json"
    )

    # CSV Writer
    csv_writer = providers.Singleton(HogangnonoCSVWriter, output_dir=str(config.output_dir))

    # Dependencies
    dependencies = providers.Singleton(
        CrawlerDependencies,
        config=config,
        api_client=api_client,
        data_mapper=data_mapper,
        validator=validator,
        error_handler=error_handler,
        bbox_divider=bbox_divider,
        checkpoint_manager=checkpoint_manager,
        csv_writer=csv_writer,
        logger=logger,
    )

    # Crawler
    crawler = providers.Singleton(
        ImprovedHogangnonoCrawler,
        dependencies=dependencies,
        output_dir=config.output_dir,
        region_bounds=config.region_bounds,
    )


class CrawlerFactory:
    """크롤러 팩토리 클래스"""

    def __init__(self):
        self.containers: Dict[str, Container] = {}

    def create_container(
        self, environment: str = "production", config_path: Optional[Path] = None, **overrides
    ) -> Container:
        """환경에 맞는 컨테이너 생성

        Args:
            environment: 환경 이름 (development, staging, production, test)
            config_path: 설정 파일 경로 (선택)
            **overrides: 설정 오버라이드

        Returns:
            설정된 컨테이너
        """
        # 설정 로드
        if environment == "development":
            config = self._load_dev_config(**overrides)
        elif environment == "staging":
            config = self._load_staging_config(**overrides)
        elif environment == "test":
            config = self._load_test_config(**overrides)
        else:  # production
            config = self._load_prod_config(**overrides)

        # 설정 파일에서 로드 (제공된 경우)
        if config_path and config_path.exists():
            config = self._load_config_from_file(config_path, config)

        # 컨테이너 생성 및 설정
        container = Container()
        container.config.from_value(config)

        # 캐싱
        self.containers[environment] = container

        return container

    def get_crawler(
        self,
        environment: str = "production",
        output_dir: Optional[Path] = None,
        region_bounds: Optional[tuple] = None,
        **config_overrides,
    ) -> ImprovedHogangnonoCrawler:
        """설정된 크롤러 인스턴스 반환

        Args:
            environment: 환경 이름
            output_dir: 출력 디렉토리 (선택)
            region_bounds: 크롤링 지역 경계 (선택)
            **config_overrides: 설정 오버라이드

        Returns:
            초기화된 크롤러 인스턴스
        """
        # 컨테이너 가져오기 또는 생성
        if environment not in self.containers:
            self.create_container(environment, **config_overrides)

        container = self.containers[environment]

        # 출력 디렉토리 설정
        if output_dir:
            container.config.output_dir.from_value(output_dir)

        # 지역 경계 설정
        if region_bounds:
            container.config.region_bounds.from_value(region_bounds)

        # 크롤러 반환
        return container.crawler()

    def create_test_crawler(
        self, output_dir: Path, mock_api: bool = True
    ) -> ImprovedHogangnonoCrawler:
        """테스트용 크롤러 생성

        Args:
            output_dir: 테스트 출력 디렉토리
            mock_api: API를 Mock으로 사용할지 여부

        Returns:
            테스트용 크롤러
        """
        config = self._load_test_config(output_dir=output_dir)

        if mock_api:
            # Mock API 클라이언트 생성
            from unittest.mock import Mock

            mock_client = Mock(spec=HogangnonoAPIClient)
            container = self._create_container_with_mocks(config, mock_client)
        else:
            container = self.create_container("test", **config.__dict__)

        return container.crawler()

    def _load_dev_config(self, **overrides) -> HogangnonoConfig:
        """개발 환경 설정 로드"""
        config_dict = {
            "base_url": "https://hogangnono.com",
            "timeout": 60,
            "rate_limit_delay": 1.0,
            "page_size": 20,
            "retry_attempts": 2,
            "retry_delay": 0.5,
            "use_threading": True,
            "max_workers": 2,
            "headless": False,  # 개발에서는 브라우저 보이기
        }
        config_dict.update(overrides)
        return HogangnonoConfig(**config_dict)

    def _load_staging_config(self, **overrides) -> HogangnonoConfig:
        """스테이징 환경 설정 로드"""
        config_dict = {
            "base_url": "https://staging-hogangnono.com",
            "timeout": 30,
            "rate_limit_delay": 2.0,
            "page_size": 50,
            "retry_attempts": 3,
            "retry_delay": 1.0,
            "use_threading": True,
            "max_workers": 4,
            "headless": True,
        }
        config_dict.update(overrides)
        return HogangnonoConfig(**config_dict)

    def _load_prod_config(self, **overrides) -> HogangnonoConfig:
        """프로덕션 환경 설정 로드"""
        config_dict = {
            "base_url": "https://hogangnono.com",
            "timeout": 30,
            "rate_limit_delay": 2.0,
            "page_size": 100,
            "retry_attempts": 3,
            "retry_delay": 1.0,
            "use_threading": True,
            "max_workers": 8,
            "headless": True,
            "daily_request_limit": 50000,
        }
        config_dict.update(overrides)
        return HogangnonoConfig(**config_dict)

    def _load_test_config(self, **overrides) -> HogangnonoConfig:
        """테스트 환경 설정 로드"""
        config_dict = {
            "base_url": "https://api.test.com",
            "timeout": 10,
            "rate_limit_delay": 0.1,
            "page_size": 5,
            "retry_attempts": 1,
            "retry_delay": 0.1,
            "use_threading": False,
            "max_workers": 1,
            "headless": True,
        }
        config_dict.update(overrides)
        return HogangnonoConfig(**config_dict)

    def _load_config_from_file(
        self, config_path: Path, default_config: HogangnonoConfig
    ) -> HogangnonoConfig:
        """파일에서 설정 로드

        Args:
            config_path: 설정 파일 경로 (YAML 또는 JSON)
            default_config: 기본 설정

        Returns:
            로드된 설정
        """
        import yaml
        import json

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                if config_path.suffix.lower() == ".yaml" or config_path.suffix.lower() == ".yml":
                    config_data = yaml.safe_load(f)
                else:
                    config_data = json.load(f)

            # 기본 설정과 병합
            config_dict = default_config.model_dump()
            config_dict.update(config_data)

            return HogangnonoConfig(**config_dict)

        except Exception as e:
            logging.warning(f"Failed to load config from {config_path}: {e}. Using default config.")
            return default_config

    def _create_container_with_mocks(self, config: HogangnonoConfig, mock_api_client) -> Container:
        """Mock 객체가 포함된 컨테이너 생성"""
        container = Container()
        container.config.from_value(config)

        # API 클라이언트를 Mock으로 교체
        container.api_client.override(providers.Object(mock_api_client))

        return container


class ConfigurationManager:
    """설정 관리자 - 여러 환경의 설정을 중앙에서 관리"""

    def __init__(self, config_dir: Path = Path("config")):
        """설정 관리자 초기화

        Args:
            config_dir: 설정 파일 디렉토리
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.configs: Dict[str, HogangnonoConfig] = {}

    def save_config(self, environment: str, config: HogangnonoConfig, format: str = "yaml") -> None:
        """환경 설정 저장

        Args:
            environment: 환경 이름
            config: 저장할 설정
            format: 저장 형식 (yaml 또는 json)
        """

        config_path = self.config_dir / f"{environment}.{format}"
        config_dict = config.model_dump()

        with open(config_path, "w", encoding="utf-8") as f:
            if format == "yaml":
                yaml.dump(config_dict, f, allow_unicode=True, default_flow_style=False)
            else:
                json.dump(config_dict, f, ensure_ascii=False, indent=2)

        self.configs[environment] = config

    def load_config(self, environment: str, format: str = "yaml") -> Optional[HogangnonoConfig]:
        """환경 설정 로드

        Args:
            environment: 환경 이름
            format: 파일 형식 (yaml 또는 json)

        Returns:
            로드된 설정 또는 None
        """
        if environment in self.configs:
            return self.configs[environment]

        config_path = self.config_dir / f"{environment}.{format}"
        if not config_path.exists():
            return None

        factory = CrawlerFactory()
        config = factory._load_config_from_file(
            config_path,
            HogangnonoConfig(),  # 빈 기본 설정
        )

        self.configs[environment] = config
        return config

    def list_environments(self) -> list:
        """사용 가능한 환경 목록 반환"""
        environments = []
        for file_path in self.config_dir.glob("*.yaml"):
            environments.append(file_path.stem)
        for file_path in self.config_dir.glob("*.yml"):
            environments.append(file_path.stem)
        for file_path in self.config_dir.glob("*.json"):
            environments.append(file_path.stem)
        return sorted(set(environments))


# 전역 팩토리 인스턴스
crawler_factory = CrawlerFactory()
config_manager = ConfigurationManager()
