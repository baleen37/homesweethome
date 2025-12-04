import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class CrawlerConfig:
    timeout: int = 30
    headless: bool = True
    output_dir: str = "output"

    @classmethod
    def from_env(cls, **overrides: int | bool | str | None) -> "CrawlerConfig":
        """Load from .env file + CLI overrides"""
        load_dotenv()
        config = {
            "timeout": int(os.getenv("TIMEOUT", "30")),
            "headless": os.getenv("HEADLESS", "true").lower() == "true",
            "output_dir": os.getenv("OUTPUT_DIR", "output"),
        }
        config.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**config)  # type: ignore
