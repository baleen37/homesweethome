"""
크롤러를 위한 간단한 팩토리 모듈

이 모듈은 다음과 같은 기능을 제공합니다:
1. 크롤러 인스턴스 생성
2. 기본 설정 관리
"""

from pathlib import Path
from typing import Optional

from .config import CrawlerConfig
from .crawlers.hogangnono import HogangnonoCrawler


def create_crawler(
    output_dir: Optional[Path] = None,
    region_bounds: Optional[tuple] = None,
) -> HogangnonoCrawler:
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
        config = CrawlerConfig()
        output_dir_str = config.output_dir or "output"

    # 크롤러 생성 및 반환
    config = CrawlerConfig()
    return HogangnonoCrawler(
        config=config,
        output_dir=output_dir_str,
        region_bounds=region_bounds,
    )


def create_test_crawler(output_dir: Path) -> HogangnonoCrawler:
    """테스트용 크롤러 생성

    Args:
        output_dir: 테스트 출력 디렉토리

    Returns:
        테스트용 크롤러
    """
    config = CrawlerConfig()
    return HogangnonoCrawler(
        config=config,
        output_dir=str(output_dir),
        region_bounds=(37.413294, 126.734086, 37.715133, 127.183394),  # 서울시
    )
