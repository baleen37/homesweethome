import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError


class CrawlerConfig(BaseModel):
    """크롤러 설정을 관리하는 클래스"""

    # 기본 설정
    timeout: int = Field(
        default=30,
        description="요청 타임아웃 (초)"
    )
    headless: bool = Field(
        default=True,
        description="헤드리스 모드 사용 여부"
    )
    output_file: str | None = Field(
        default=None,
        description="출력 파일 경로"
    )

    # API 관련 설정
    api_key: str | None = Field(
        default=None,
        description="API 키"
    )
    region_code: str | None = Field(
        default=None,
        description="법정동코드 (예: 11680: 서울 강남구)"
    )
    start_date: str | None = Field(
        default=None,
        description="조회 시작일 (YYYY-MM 형식)"
    )
    end_date: str | None = Field(
        default=None,
        description="조회 종료일 (YYYY-MM 형식)"
    )

    # 크롤링 설정
    page_size: int = Field(
        default=20,
        description="한 페이지당 조회 건수"
    )
    retry_attempts: int = Field(
        default=3,
        description="재시도 횟수"
    )
    retry_delay: float = Field(
        default=1.0,
        description="재시도 대기 시간 (초)"
    )
    delay_seconds: float = Field(
        default=2.0,
        description="요청 간 대기 시간 (초)"
    )

    # 쓰레딩 설정
    use_threading: bool = Field(
        default=False,
        description="멀티쓰레딩 사용 여부"
    )
    max_workers: int = Field(
        default=4,
        description="최대 작업자 수"
    )

    @field_validator('timeout')
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """timeout 범위 검증"""
        if v < 0:
            raise ValueError("timeout은 0 이상이어야 합니다")
        if v > 300:
            raise ValueError("timeout은 300 이하여야 합니다")
        return v

    @field_validator('page_size')
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        """page_size 범위 검증"""
        if v < 1:
            raise ValueError("page_size은 1 이상이어야 합니다")
        if v > 100:
            raise ValueError("page_size은 100 이하여야 합니다")
        return v

    @field_validator('retry_attempts')
    @classmethod
    def validate_retry_attempts(cls, v: int) -> int:
        """retry_attempts 범위 검증"""
        if v < 0:
            raise ValueError("retry_attempts은 0 이상이어야 합니다")
        if v > 10:
            raise ValueError("retry_attempts은 10 이하여야 합니다")
        return v

    @field_validator('retry_delay')
    @classmethod
    def validate_retry_delay(cls, v: float) -> float:
        """retry_delay 범위 검증"""
        if v < 0.1:
            raise ValueError("retry_delay는 0.1 이상이어야 합니다")
        if v > 10:
            raise ValueError("retry_delay는 10 이하여야 합니다")
        return v

    @field_validator('delay_seconds')
    @classmethod
    def validate_delay_seconds(cls, v: float) -> float:
        """delay_seconds 범위 검증"""
        if v < 0.1:
            raise ValueError("delay_seconds은 0.1 이상이어야 합니다")
        if v > 60:
            raise ValueError("delay_seconds은 60 이하여야 합니다")
        return v

    @field_validator('max_workers')
    @classmethod
    def validate_max_workers(cls, v: int) -> int:
        """max_workers 범위 검증"""
        if v < 1:
            raise ValueError("max_workers은 1 이상이어야 합니다")
        if v > 20:
            raise ValueError("max_workers은 20 이하여야 합니다")
        return v

    @field_validator('output_file')
    @classmethod
    def validate_output_file(cls, v: str | None) -> str | None:
        """output_file 경로 검증"""
        if v is not None:
            path = Path(v)
            if not path.parent.exists():
                raise ValueError("output_file의 상위 디렉토리가 존재하지 않습니다")
        return v

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v: str | None) -> str | None:
        """날짜 형식 검증 (YYYY-MM)"""
        if v is not None:
            try:
                datetime.strptime(v, "%Y-%m")
            except ValueError:
                raise ValueError("날짜는 YYYY-MM 형식이어야 합니다")
        return v

    @model_validator(mode='after')
    def validate_compatibility(self) -> "CrawlerConfig":
        """설정 간 호환성 검증"""
        # 너무 많은 worker와 너무 짧은 delay 조합 검증
        if self.use_threading and self.max_workers > 5 and self.delay_seconds < 0.5:
            raise ValueError("너무 많은 worker와 짧은 delay는 서버에 부하를 줄 수 있습니다")

        # timeout이 전체 재시도 시간보다 작은 경우 검증
        total_retry_time = self.retry_attempts * self.retry_delay
        if self.timeout < total_retry_time:
            raise ValueError(
                f"timeout({self.timeout}s)은 전체 재시도 시간({total_retry_time}s)보다 커야 합니다"
            )

        return self

    @classmethod
    def from_env(cls, **overrides: int | bool | str | None) -> "CrawlerConfig":
        """환경 변수에서 설정 로드"""
        load_dotenv()

        # 환경 변수에서 설정값 읽기
        config = {
            "timeout": int(os.getenv("CRAWLER_TIMEOUT", "30")),
            "headless": os.getenv("CRAWLER_HEADLESS", "true").lower() == "true",
            "output_file": os.getenv("CRAWLER_OUTPUT_FILE"),
            "api_key": os.getenv("CRAWLER_API_KEY"),
            "region_code": os.getenv("CRAWLER_REGION_CODE"),
            "start_date": os.getenv("CRAWLER_START_DATE"),
            "end_date": os.getenv("CRAWLER_END_DATE"),
            "page_size": int(os.getenv("CRAWLER_PAGE_SIZE", "20")),
            "retry_attempts": int(os.getenv("CRAWLER_RETRY_ATTEMPTS", "3")),
            "retry_delay": float(os.getenv("CRAWLER_RETRY_DELAY", "1.0")),
            "delay_seconds": float(os.getenv("CRAWLER_DELAY_SECONDS", "2.0")),
            "use_threading": os.getenv("CRAWLER_USE_THREADING", "false").lower() == "true",
            "max_workers": int(os.getenv("CRAWLER_MAX_WORKERS", "4")),
        }

        # CLI 오버라이드 적용
        config.update({k: v for k, v in overrides.items() if v is not None})

        try:
            return cls(**config)
        except ValueError as e:
            raise ValueError(f"환경 변수 설정 오류: {e}")

    def create_output_path(self, base_dir: str = "output") -> Path:
        """타임스탬프가 포함된 출력 파일 경로 생성"""
        # 디렉토리 생성
        Path(base_dir).mkdir(parents=True, exist_ok=True)

        # 타임스탬프 형식: data_YYYYMMDD_HHMMSS.csv
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data_{timestamp}.csv"

        return Path(base_dir) / filename
