import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class CrawlerConfig:
    timeout: int = 30
    headless: bool = True
    output_dir: str = "output"
    # API 관련 설정
    api_key: str | None = None
    region_code: str | None = None  # 법정동코드 (예: 11680: 서울 강남구)
    start_date: str | None = None  # 조회 시작일 (YYYY-MM 형식)
    end_date: str | None = None    # 조회 종료일 (YYYY-MM 형식)
    page_size: int = 1000          # 한 페이지당 조회 건수

    @classmethod
    def from_env(cls, **overrides: int | bool | str | None) -> "CrawlerConfig":
        """Load from .env file + CLI overrides"""
        load_dotenv()
        config = {
            "timeout": int(os.getenv("TIMEOUT", "30")),
            "headless": os.getenv("HEADLESS", "true").lower() == "true",
            "output_dir": os.getenv("OUTPUT_DIR", "output"),
            "api_key": os.getenv("API_KEY"),
            "region_code": os.getenv("REGION_CODE"),
            "start_date": os.getenv("START_DATE"),
            "end_date": os.getenv("END_DATE"),
            "page_size": int(os.getenv("PAGE_SIZE", "1000")),
        }
        config.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**config)  # type: ignore
