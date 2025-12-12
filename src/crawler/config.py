"""
크롤러 설정 관리 모듈

간단한 하드코딩된 설정을 제공합니다.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

# Export classes for explicit imports
__all__ = ["Config"]


class Config:
    """간단한 크롤러 설정 (하드코딩된 값)"""

    # 기본 설정
    BASE_URL = "https://hogangnono.com"
    TIMEOUT = 30
    HEADLESS = True
    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"

    # Rate Limiting 설정
    RATE_LIMIT_DELAY = 2.0  # 요청 간 대기 시간 (초)
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 1.0

    # 페이징 설정
    PAGE_SIZE = 50

    # 쓰레딩 설정
    USE_THREADING = False
    MAX_WORKERS = 4

    # 필터링 기본값
    DEFAULT_PROPERTY_TYPE = "apartment"
    DEFAULT_TRANSACTION_TYPE = "sale"

    # 출력 디렉토리
    OUTPUT_DIR = "output"

    # 로그 레벨
    LOG_LEVEL = "INFO"

    # 지역 경계 (서울)
    REGION_BOUNDS = [37.413294, 126.734086, 37.715133, 127.183394]

    def __init__(self):
        """설정 초기화"""
        pass

    @classmethod
    def for_integration_test(cls, output_dir: str) -> "Config":
        """통합 테스트용 설정 생성"""
        config = cls()
        config.OUTPUT_DIR = output_dir
        config.TIMEOUT = 30
        config.RATE_LIMIT_DELAY = 2.0
        config.PAGE_SIZE = 20
        config.USE_THREADING = False
        config.MAX_WORKERS = 1
        config.RETRY_ATTEMPTS = 3
        config.RETRY_DELAY = 1.0
        return config

    def create_output_path(self, base_dir: Optional[str] = None) -> Path:
        """타임스탬프가 포함된 출력 파일 경로 생성"""
        if base_dir is None:
            base_dir = self.OUTPUT_DIR

        # 디렉토리 생성
        Path(base_dir).mkdir(parents=True, exist_ok=True)

        # 타임스탬프 형식: data_YYYYMMDD_HHMMSS.csv
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data_{timestamp}.csv"

        return Path(base_dir) / filename


# 간단한 user_agent 정의
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"

# Backward compatibility alias
HogangnonoConfig = Config
CrawlerConfig = Config
