"""
크롤러를 위한 간단한 팩토리 모듈

이 모듈은 다음과 같은 기능을 제공합니다:
1. 크롤러 인스턴스 생성
2. 기본 설정 관리
"""

import logging
from pathlib import Path
from typing import Optional

from .config import Config
from .api.hogangnono_client import HogangnonoAPIClient
from .data_mappers import HogangnonoDataMapper
from .validators.data_validator import ApartmentValidator
from .utils.enhanced_error_handler import EnhancedErrorHandler
from .utils.bbox_division import BBoxDivision
from .utils.checkpoint import CheckpointManager
from .writers.hogangnono_csv_writer import HogangnonoCSVWriter
from .crawlers.improved_hogangnono_crawler import ImprovedHogangnonoCrawler, CrawlerDependencies


def create_crawler(
    output_dir: Optional[Path] = None,
    region_bounds: Optional[tuple] = None,
) -> ImprovedHogangnonoCrawler:
    """설정된 크롤러 인스턴스 생성

    Args:
        output_dir: 출력 디렉토리 (선택)
        region_bounds: 크롤링 지역 경계 (선택)

    Returns:
        초기화된 크롤러 인스턴스
    """
    config = Config()

    # 출력 디렉토리 설정
    if output_dir:
        output_dir = Path(output_dir)
    else:
        output_dir = Path(config.OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 지역 경계 설정
    if not region_bounds:
        region_bounds = tuple(config.REGION_BOUNDS)  # 서울시

    # 로거 생성
    logger = logging.getLogger("improved_hogangnono_crawler")

    # 의존성 생성
    api_client = HogangnonoAPIClient(config)
    data_mapper = HogangnonoDataMapper(dong_code_mapping_file=output_dir / "dong_code_mapping.json")
    validator = ApartmentValidator()
    error_handler = EnhancedErrorHandler(
        max_retries=config.RETRY_ATTEMPTS, retry_delay=config.RETRY_DELAY
    )
    bbox_divider = BBoxDivision(max_pois_per_bbox=900)
    checkpoint_manager = CheckpointManager(checkpoint_path=output_dir / "checkpoint.json")
    csv_writer = HogangnonoCSVWriter(output_dir=str(output_dir))

    # 의존성 묶음 생성
    dependencies = CrawlerDependencies(
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

    # 크롤러 생성 및 반환
    return ImprovedHogangnonoCrawler(
        dependencies=dependencies,
        output_dir=output_dir,
        region_bounds=region_bounds,
    )


def create_test_crawler(output_dir: Path, mock_api: bool = True) -> ImprovedHogangnonoCrawler:
    """테스트용 크롤러 생성

    Args:
        output_dir: 테스트 출력 디렉토리
        mock_api: API를 Mock으로 사용할지 여부

    Returns:
        테스트용 크롤러
    """
    config = Config.for_integration_test(str(output_dir))

    # 로거 생성
    logger = logging.getLogger("test_hogangnono_crawler")

    # API 클라이언트 생성
    if mock_api:
        from unittest.mock import Mock

        api_client = Mock(spec=HogangnonoAPIClient)
    else:
        api_client = HogangnonoAPIClient(config)

    # 공통 의존성 생성
    dependencies = _create_test_dependencies(
        config=config, api_client=api_client, output_dir=output_dir, logger=logger
    )

    # 크롤러 생성 및 반환
    return ImprovedHogangnonoCrawler(
        dependencies=dependencies,
        output_dir=output_dir,
        region_bounds=(37.413294, 126.734086, 37.715133, 127.183394),  # 서울시
    )


def _create_test_dependencies(
    config: Config,
    api_client,
    output_dir: Path,
    logger: logging.Logger,
) -> CrawlerDependencies:
    """테스트용 의존성 생성 (공통 코드)

    Args:
        config: 설정 객체
        api_client: API 클라이언트 (Mock 또는 실제)
        output_dir: 출력 디렉토리
        logger: 로거

    Returns:
        생성된 의존성 묶음
    """
    data_mapper = HogangnonoDataMapper(dong_code_mapping_file=output_dir / "dong_code_mapping.json")
    validator = ApartmentValidator()
    error_handler = EnhancedErrorHandler(
        max_retries=config.RETRY_ATTEMPTS, retry_delay=config.RETRY_DELAY
    )
    bbox_divider = BBoxDivision(max_pois_per_bbox=900)
    checkpoint_manager = CheckpointManager(checkpoint_path=output_dir / "checkpoint.json")
    csv_writer = HogangnonoCSVWriter(output_dir=str(output_dir))

    return CrawlerDependencies(
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
