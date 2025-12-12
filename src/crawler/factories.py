"""
크롤러를 위한 간단한 팩토리 모듈

이 모듈은 다음과 같은 기능을 제공합니다:
1. 크롤러 인스턴스 생성
2. 기본 설정 관리
"""

from pathlib import Path
from typing import Optional

from .config import Config
from .crawlers.simple_crawler import SimpleCrawler


def create_crawler(
    output_dir: Optional[Path] = None,
    region_bounds: Optional[tuple] = None,
) -> SimpleCrawler:
    """설정된 크롤러 인스턴스 생성

    Args:
        output_dir: 출력 디렉토리 (선택)
        region_bounds: 크롤링 지역 경계 (선택)

    Returns:
        초기화된 크롤러 인스턴스
    """
    # 출력 디렉토리 설정
    if output_dir:
        output_dir_str = str(output_dir)
    else:
        config = Config()
        output_dir_str = config.OUTPUT_DIR

    # 크롤러 생성 및 반환
    return SimpleCrawler(
        output_dir=output_dir_str,
        region_bounds=region_bounds,
    )


def create_test_crawler(output_dir: Path, mock_api: bool = True) -> SimpleCrawler:
    """테스트용 크롤러 생성

    Args:
        output_dir: 테스트 출력 디렉토리
        mock_api: API를 Mock으로 사용할지 여부 (SimpleCrawler에서는 무시됨)

    Returns:
        테스트용 크롤러
    """
    # SimpleCrawler는 내부적으로 직접 의존성을 생성하므로 mock_api는 무시됨
    return SimpleCrawler(
        output_dir=str(output_dir),
        region_bounds=(37.413294, 126.734086, 37.715133, 127.183394),  # 서울시
    )
