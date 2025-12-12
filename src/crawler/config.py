"""
크롤러 설정 관리 모듈

환경 변수를 지원하는 유연한 설정을 제공합니다.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

# Export classes for explicit imports
__all__ = ["Config"]


class Config:
    """환경 변수를 지원하는 크롤러 설정"""

    def __init__(self):
        """설정 초기화 - 환경 변수에서 값 읽기"""
        # 기본 설정
        self.BASE_URL = os.getenv("HOGANGNONO_BASE_URL", "https://hogangnono.com")
        self.TIMEOUT = int(os.getenv("CRAWLER_TIMEOUT", "30"))
        self.HEADLESS = os.getenv("CRAWLER_HEADLESS", "true").lower() == "true"
        self.USER_AGENT = os.getenv(
            "CRAWLER_USER_AGENT",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        )

        # Rate Limiting 설정
        self.RATE_LIMIT_DELAY = float(
            os.getenv("CRAWLER_RATE_LIMIT_DELAY", "2.0")
        )  # 요청 간 대기 시간 (초)
        self.RETRY_ATTEMPTS = int(os.getenv("CRAWLER_RETRY_ATTEMPTS", "3"))
        self.RETRY_DELAY = float(os.getenv("CRAWLER_RETRY_DELAY", "1.0"))

        # 페이징 설정
        self.PAGE_SIZE = int(os.getenv("CRAWLER_PAGE_SIZE", "50"))

        # 쓰레딩 설정
        self.USE_THREADING = os.getenv("CRAWLER_USE_THREADING", "false").lower() == "true"
        self.MAX_WORKERS = int(os.getenv("CRAWLER_MAX_WORKERS", "4"))

        # 필터링 기본값
        self.DEFAULT_PROPERTY_TYPE = os.getenv("CRAWLER_DEFAULT_PROPERTY_TYPE", "apartment")
        self.DEFAULT_TRANSACTION_TYPE = os.getenv("CRAWLER_DEFAULT_TRANSACTION_TYPE", "sale")

        # 출력 디렉토리
        self.OUTPUT_DIR = os.getenv("CRAWLER_OUTPUT_DIR", "output")

        # 로그 레벨
        self.LOG_LEVEL = os.getenv("CRAWLER_LOG_LEVEL", "INFO")

        # 지역 경계 (서울)
        self.REGION_BOUNDS = [37.413294, 126.734086, 37.715133, 127.183394]

    @classmethod
    def from_env(cls, output_file: Optional[str] = None) -> "Config":
        """환경 변수에서 설정을 생성하는 클래스 메서드"""
        config = cls()

        # output_file이 제공되면 OUTPUT_DIR 설정
        if output_file:
            # 파일 경로인지 디렉토리 경로인지 확인
            path = Path(output_file)
            if path.suffix:  # 파일 확장자가 있으면 디렉토리 추출
                config.OUTPUT_DIR = str(path.parent)
            else:  # 디렉토리 경로면 그대로 사용
                config.OUTPUT_DIR = output_file

        return config

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


class CrawlerConfig:
    """환경 변수를 지원하는 크롤러 설정 (향상된 버전)"""

    def __init__(self, **kwargs):
        """설정 초기화

        Args:
            page_size: 페이지 크기 (기본값: 환경 변수 또는 50)
            timeout: 타임아웃 (기본값: 환경 변수 또는 30)
            retry_attempts: 재시도 횟수 (기본값: 환경 변수 또는 3)
            retry_delay: 재시도 대기 시간 (기본값: 환경 변수 또는 1.0)
            rate_limit_delay: 요청 간 대기 시간 (기본값: 환경 변수 또는 2.0)
            max_workers: 최대 워커 수 (기본값: 환경 변수 또는 4)
            use_threading: 쓰레딩 사용 여부 (기본값: 환경 변수 또는 False)
            output_dir: 출력 디렉토리 (기본값: 환경 변수 또는 "output")
            output_file: 출력 파일 경로 (선택사항)
        """
        # 기본값 설정
        self.page_size = kwargs.get("page_size", int(os.getenv("CRAWLER_PAGE_SIZE", "50")))
        self.timeout = kwargs.get("timeout", int(os.getenv("CRAWLER_TIMEOUT", "30")))
        self.retry_attempts = kwargs.get(
            "retry_attempts", int(os.getenv("CRAWLER_RETRY_ATTEMPTS", "3"))
        )
        self.retry_delay = kwargs.get("retry_delay", float(os.getenv("CRAWLER_RETRY_DELAY", "1.0")))
        self.rate_limit_delay = kwargs.get(
            "rate_limit_delay", float(os.getenv("CRAWLER_RATE_LIMIT_DELAY", "2.0"))
        )
        self.max_workers = kwargs.get("max_workers", int(os.getenv("CRAWLER_MAX_WORKERS", "4")))
        self.use_threading = kwargs.get(
            "use_threading", os.getenv("CRAWLER_USE_THREADING", "false").lower() == "true"
        )
        self.output_dir = kwargs.get("output_dir", os.getenv("CRAWLER_OUTPUT_DIR", "output"))
        self.output_file = kwargs.get("output_file")

        # 유효성 검사
        self._validate()

        # Config와 호환성을 위한 속성 추가
        self.TIMEOUT = self.timeout
        self.RETRY_ATTEMPTS = self.retry_attempts
        self.RETRY_DELAY = self.retry_delay
        self.RATE_LIMIT_DELAY = self.rate_limit_delay
        self.MAX_WORKERS = self.max_workers
        self.USE_THREADING = self.use_threading
        self.OUTPUT_DIR = self.output_dir
        self.PAGE_SIZE = self.page_size

    @classmethod
    def from_env(cls, output_file: Optional[str] = None) -> "CrawlerConfig":
        """환경 변수에서 설정을 생성하는 클래스 메서드"""
        config = cls()
        return config

    def _validate(self):
        """설정값 유효성 검사"""
        if self.page_size < 1:
            raise ValueError("page_size은 1 이상이어야 합니다")
        if self.page_size > 200:
            raise ValueError("page_size은 200 이하여야 합니다")
        if self.timeout < 1:
            raise ValueError("timeout은 1 이상이어야 합니다")
        if self.timeout > 300:
            raise ValueError("timeout은 300 이하여야 합니다")
        if self.retry_attempts < 0:
            raise ValueError("retry_attempts은 0 이상이어야 합니다")
        if self.retry_attempts > 10:
            raise ValueError("retry_attempts은 10 이하여야 합니다")
        if self.rate_limit_delay < 0.1:
            raise ValueError("rate_limit_delay는 0.1 이상이어야 합니다")
        if self.rate_limit_delay > 60:
            raise ValueError("rate_limit_delay는 60 이하여야 합니다")
        if self.max_workers < 1:
            raise ValueError("max_workers은 1 이상이어야 합니다")
        if self.max_workers > 20:
            raise ValueError("max_workers은 20 이하여야 합니다")

        # output_file 경로 검증
        if self.output_file:
            output_path = Path(self.output_file)
            if not output_path.parent.exists():
                raise ValueError("output_file의 상위 디렉토리가 존재하지 않습니다")

        # 호환성 검증
        if self.max_workers > 10 and self.rate_limit_delay < 1.0:
            raise ValueError("너무 많은 worker와 짧은 delay는 서버에 부하를 줄 수 있습니다")

        # timeout이 전체 재시도 시간보다 작은 경우
        total_retry_time = self.retry_attempts * self.retry_delay
        if self.timeout < total_retry_time:
            raise ValueError(
                f"timeout({self.timeout})은 전체 재시도 시간({total_retry_time})보다 커야 합니다"
            )

    def create_output_path(self, base_dir: Optional[str] = None) -> Path:
        """타임스탬프가 포함된 출력 파일 경로 생성"""
        if base_dir is None:
            base_dir = self.output_dir

        # 디렉토리 생성
        Path(base_dir).mkdir(parents=True, exist_ok=True)

        # 타임스탬프 형식: data_YYYYMMDD_HHMMSS.csv
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data_{timestamp}.csv"

        # 항상 상대 경로로 반환
        base_path = Path(base_dir)
        if base_path.is_absolute():
            # 절대 경로를 상대 경로로 변환
            try:
                base_path = base_path.relative_to(Path.cwd())
            except ValueError:
                # 현재 디렉토리 밖에 있는 경우 그대로 사용
                pass

        return base_path / filename


# Backward compatibility alias
HogangnonoConfig = Config
