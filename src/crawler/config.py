"""
크롤러 설정 관리 모듈

이 모듈은 호갱노노 크롤러 설정을 관리합니다.
환경 변수를 통해 설정을 로드할 수 있습니다.

사용 예시:
    # 기본 설정
    config = HogangnonoConfig()
    print(config.base_url)  # https://hogangnono.com

    # 환경 변수에서 설정 로드
    config = HogangnonoConfig.from_env()
"""

import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator, model_validator


class HogangnonoConfig(BaseModel):
    """호갱노노 크롤러 설정"""

    # 기본 설정
    base_url: str = Field(default="https://hogangnono.com", description="호갱노노 기본 URL")
    timeout: int = Field(default=30, description="요청 타임아웃 (초)")
    headless: bool = Field(default=True, description="헤드리스 모드 사용 여부")
    output_file: str | None = Field(default=None, description="출력 파일 경로")

    # API 인증
    api_key: str | None = Field(default=None, description="호갱노노 API 키")

    # Rate Limiting 설정
    rate_limit_delay: float = Field(default=2.0, description="요청 간 대기 시간 (초)")
    rate_limit_min: float = Field(default=0.1, description="최소 대기 시간 (초)")
    rate_limit_max: float = Field(default=10.0, description="최대 대기 시간 (초)")
    rate_limit_increment: float = Field(default=0.5, description="429 에러 시 증가량 (초)")
    rate_limit_decrement_after: int = Field(
        default=10, description="성공 시 감소까지의 연속 성공 횟수"
    )
    daily_request_limit: int = Field(default=10000, description="일일 최대 요청 수")

    # 페이징 설정
    page_size: int = Field(default=50, description="한 페이지당 조회 건수")
    max_page: int = Field(default=200, description="최대 조회 페이지")

    # 재시도 설정
    retry_attempts: int = Field(default=3, description="재시도 횟수")
    retry_delay: float = Field(default=1.0, description="재시도 대기 시간 (초)")

    # 쓰레딩 설정
    use_threading: bool = Field(default=False, description="멀티쓰레딩 사용 여부")
    max_workers: int = Field(default=4, description="최대 작업자 수")

    # User-Agent 설정
    user_agent: str = Field(
        default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        description="HTTP 요청 User-Agent",
    )

    # 지역 설정
    region_code: str | None = Field(default=None, description="법정동코드 (예: 11680: 서울 강남구)")
    start_date: str | None = Field(default=None, description="조회 시작일 (YYYY-MM 형식)")
    end_date: str | None = Field(default=None, description="조회 종료일 (YYYY-MM 형식)")

    # 필터링 기본값
    default_property_type: str = Field(default="apartment", description="기본 매물 타입")
    default_transaction_type: str = Field(default="sale", description="기본 거래 타입")

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str | None) -> str | None:
        """api_key 필수 여부 검증"""
        if v is not None and len(v.strip()) == 0:
            raise ValueError("api_key가 비어있습니다")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """timeout 범위 검증"""
        if v < 1:
            raise ValueError("timeout은 1 이상이어야 합니다")
        if v > 300:
            raise ValueError("timeout은 300 이하여야 합니다")
        return v

    @field_validator("rate_limit_delay")
    @classmethod
    def validate_rate_limit_delay(cls, v: float) -> float:
        """rate_limit_delay 범위 검증"""
        if v < 0.1:
            raise ValueError("rate_limit_delay는 0.1 이상이어야 합니다")
        if v > 60:
            raise ValueError("rate_limit_delay는 60 이하여야 합니다")
        return v

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, v: int) -> int:
        """page_size 범위 검증"""
        if v < 1:
            raise ValueError("page_size은 1 이상이어야 합니다")
        if v > 200:
            raise ValueError("page_size은 200 이하여야 합니다")
        return v

    @field_validator("retry_attempts")
    @classmethod
    def validate_retry_attempts(cls, v: int) -> int:
        """retry_attempts 범위 검증"""
        if v < 0:
            raise ValueError("retry_attempts은 0 이상이어야 합니다")
        if v > 10:
            raise ValueError("retry_attempts은 10 이하여야 합니다")
        return v

    @field_validator("retry_delay")
    @classmethod
    def validate_retry_delay(cls, v: float) -> float:
        """retry_delay 범위 검증"""
        if v < 0.1:
            raise ValueError("retry_delay는 0.1 이상이어야 합니다")
        if v > 10:
            raise ValueError("retry_delay는 10 이하여야 합니다")
        return v

    @field_validator("max_workers")
    @classmethod
    def validate_max_workers(cls, v: int) -> int:
        """max_workers 범위 검증"""
        if v < 1:
            raise ValueError("max_workers은 1 이상이어야 합니다")
        if v > 20:
            raise ValueError("max_workers은 20 이하여야 합니다")
        return v

    @field_validator("output_file")
    @classmethod
    def validate_output_file(cls, v: str | None) -> str | None:
        """output_file 경로 검증"""
        if v is not None:
            path = Path(v)
            if not path.parent.exists():
                raise ValueError("output_file의 상위 디렉토리가 존재하지 않습니다")
        return v

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, v: str | None) -> str | None:
        """날짜 형식 검증 (YYYY-MM)"""
        if v is not None:
            try:
                datetime.strptime(v, "%Y-%m")
            except ValueError:
                raise ValueError("날짜는 YYYY-MM 형식이어야 합니다")
        return v

    @model_validator(mode="after")
    def validate_compatibility(self) -> "HogangnonoConfig":
        """설정 간 호환성 검증"""
        # 너무 많은 worker와 너무 짧은 delay 조합 검증
        if self.use_threading and self.max_workers > 5 and self.rate_limit_delay < 0.5:
            raise ValueError("너무 많은 worker와 짧은 delay는 서버에 부하를 줄 수 있습니다")

        # timeout이 전체 재시도 시간보다 작은 경우 검증
        total_retry_time = self.retry_attempts * self.retry_delay
        if self.timeout < total_retry_time:
            raise ValueError(
                f"timeout({self.timeout}s)은 전체 재시도 시간({total_retry_time}s)보다 커야 합니다"
            )

        return self

    @classmethod
    def from_env(cls, **overrides: int | bool | str | None) -> "HogangnonoConfig":
        """환경 변수에서 설정 로드"""
        load_dotenv()

        # 기본 설정 (기존 CRAWLER_* 변수들)
        config_dict = {
            "base_url": os.getenv("HOGANGNONO_BASE_URL", "https://hogangnono.com"),
            "timeout": int(os.getenv("CRAWLER_TIMEOUT", os.getenv("HOGANGNONO_TIMEOUT", "30"))),
            "headless": os.getenv("CRAWLER_HEADLESS", "true").lower() == "true",
            "output_file": os.getenv("CRAWLER_OUTPUT_FILE"),
            "api_key": os.getenv("HOGANGNONO_API_KEY", os.getenv("CRAWLER_API_KEY")),
            "rate_limit_delay": float(os.getenv("HOGANGNONO_RATE_LIMIT", "2.0")),
            "rate_limit_min": float(os.getenv("HOGANGNONO_RATE_LIMIT_MIN", "0.1")),
            "rate_limit_max": float(os.getenv("HOGANGNONO_RATE_LIMIT_MAX", "10.0")),
            "rate_limit_increment": float(os.getenv("HOGANGNONO_RATE_LIMIT_INCREMENT", "0.5")),
            "rate_limit_decrement_after": int(
                os.getenv("HOGANGNONO_RATE_LIMIT_DECREMENT_AFTER", "10")
            ),
            "daily_request_limit": int(os.getenv("HOGANGNONO_DAILY_REQUEST_LIMIT", "10000")),
            "page_size": int(os.getenv("HOGANGNONO_PAGE_SIZE", "50")),
            "max_page": int(os.getenv("HOGANGNONO_MAX_PAGE", "200")),
            "retry_attempts": int(os.getenv("CRAWLER_RETRY_ATTEMPTS", "3")),
            "retry_delay": float(os.getenv("CRAWLER_RETRY_DELAY", "1.0")),
            "use_threading": os.getenv("CRAWLER_USE_THREADING", "false").lower() == "true",
            "max_workers": int(os.getenv("CRAWLER_MAX_WORKERS", "4")),
            "user_agent": os.getenv(
                "CRAWLER_USER_AGENT",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            ),
            "region_code": os.getenv("CRAWLER_REGION_CODE"),
            "start_date": os.getenv("CRAWLER_START_DATE"),
            "end_date": os.getenv("CRAWLER_END_DATE"),
            "default_property_type": os.getenv("HOGANGNONO_DEFAULT_PROPERTY_TYPE", "apartment"),
            "default_transaction_type": os.getenv("HOGANGNONO_DEFAULT_TRANSACTION_TYPE", "sale"),
        }

        # CLI 오버라이드 적용
        config_dict.update({k: v for k, v in overrides.items() if v is not None})

        try:
            return cls(**config_dict)
        except ValueError as e:
            raise ValueError(f"환경 변수 설정 오류: {e}")

    @classmethod
    def for_integration_test(cls, output_dir: str, districts: list[str]) -> "HogangnonoConfig":
        """Create config for integration testing"""
        return cls(
            timeout=30,
            rate_limit_delay=2.0,
            page_size=20,
            headless=True,
            use_threading=False,
            max_workers=1,
            retry_attempts=3,
            retry_delay=1.0,
            output_file=f"{output_dir}/test_output.csv",
        )

    def create_output_path(self, base_dir: str = "output") -> Path:
        """타임스탬프가 포함된 출력 파일 경로 생성"""
        # 디렉토리 생성
        Path(base_dir).mkdir(parents=True, exist_ok=True)

        # 타임스탬프 형식: data_YYYYMMDD_HHMMSS.csv
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data_{timestamp}.csv"

        return Path(base_dir) / filename


# Backward compatibility alias
CrawlerConfig = HogangnonoConfig
