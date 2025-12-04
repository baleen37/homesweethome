# HomeSweetHome Crawler Boilerplate 디자인

**작성일**: 2025-12-04

## 개요

Python 크롤링 + CSV 저장 보일러플레이트. 정적/동적 사이트 모두 지원하며, 새로운 사이트 크롤러를 쉽게 추가할 수 있는 구조.

## 핵심 방향

- uv 기반 프로젝트 관리
- src layout 구조
- 정적 사이트(requests + BeautifulSoup) / 동적 사이트(Playwright) 지원
- 설정 파일(`.env`) + CLI 인자 조합
- CSV 출력 (표준 라이브러리 csv 모듈)
- 동기 방식 (간단하고 명확한 구조)

## 기술 스택

### 크롤링
- **정적 사이트**: requests + BeautifulSoup + lxml
- **동적 사이트**: playwright (sync API)

### 데이터 처리
- Python 표준 csv 모듈
- dataclasses로 데이터 모델링

### 설정/로깅
- python-dotenv (`.env` 파일)
- structlog (구조화된 로깅)
- argparse (CLI)

### 개발 도구
- ruff (linting + formatting)
- mypy (type checking)
- pytest (testing)
- pre-commit (코드 품질 자동 검사)

## 프로젝트 구조

```
homesweethome/
├── .github/
│   └── workflows/
│       └── ci.yml                # GitHub Actions CI
├── src/
│   └── crawler/
│       ├── __init__.py
│       ├── config.py             # 설정 관리
│       ├── models.py             # 데이터 모델
│       ├── crawlers/
│       │   ├── __init__.py
│       │   ├── base.py           # 추상 베이스 크롤러
│       │   ├── static.py         # requests 기반
│       │   └── dynamic.py        # playwright 기반
│       ├── parsers/
│       │   ├── __init__.py
│       │   └── html.py           # HTML 파싱 유틸
│       └── writers/
│           ├── __init__.py
│           └── csv_writer.py     # CSV 저장
├── tests/
│   ├── conftest.py
│   ├── unit/
│   └── integration/
├── scripts/
│   └── main.py                   # 실행 엔트리포인트
├── docs/
│   └── plans/
├── output/                       # 출력 디렉토리 (git ignore)
├── .env                          # 환경 설정 (git ignore)
├── .env.example                  # 환경 설정 예시
├── .pre-commit-config.yaml       # pre-commit 설정
├── .gitignore
├── pyproject.toml
├── uv.lock
└── README.md
```

## 코어 컴포넌트

### 1. 설정 관리 (`config.py`)

**최소한의 설정만 유지:**

```python
from dataclasses import dataclass
from dotenv import load_dotenv
import os

@dataclass
class CrawlerConfig:
    timeout: int = 30
    headless: bool = True
    output_dir: str = "output"

    @classmethod
    def from_env(cls, **overrides):
        """Load from .env file + CLI overrides"""
        load_dotenv()
        config = {
            'timeout': int(os.getenv('TIMEOUT', 30)),
            'headless': os.getenv('HEADLESS', 'true').lower() == 'true',
            'output_dir': os.getenv('OUTPUT_DIR', 'output'),
        }
        config.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**config)
```

**`.env` 파일 예시:**
```
TIMEOUT=30
HEADLESS=true
OUTPUT_DIR=output
```

### 2. 크롤러 베이스 (`crawlers/base.py`)

```python
from abc import ABC, abstractmethod
import structlog

class BaseCrawler(ABC):
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.logger = structlog.get_logger()

    @abstractmethod
    def fetch(self, url: str) -> str:
        """HTML 가져오기"""
        pass

    @abstractmethod
    def parse(self, html: str) -> list[dict]:
        """HTML 파싱 - 사이트별 구현"""
        pass

    def crawl(self) -> list[dict]:
        """크롤링 + 파싱 (URL은 각 크롤러에서 정의)"""
        url = self.get_url()
        html = self.fetch(url)
        return self.parse(html)

    @abstractmethod
    def get_url(self) -> str:
        """크롤링할 URL 반환"""
        pass
```

### 3. 정적 크롤러 (`crawlers/static.py`)

```python
import requests
from bs4 import BeautifulSoup
from .base import BaseCrawler

class StaticCrawler(BaseCrawler):
    def get_url(self) -> str:
        # TODO: 실제 URL로 변경
        return "https://example.com"

    def fetch(self, url: str) -> str:
        """requests로 HTML 가져오기"""
        self.logger.info("fetching_url", url=url)
        response = requests.get(url, timeout=self.config.timeout)
        response.raise_for_status()
        return response.text

    def parse(self, html: str) -> list[dict]:
        """BeautifulSoup으로 파싱"""
        soup = BeautifulSoup(html, 'lxml')

        # TODO: 실제 사이트 구조에 맞게 수정
        items = soup.select('.item')
        results = []

        for item in items:
            results.append({
                'title': item.select_one('.title').text.strip(),
                'price': item.select_one('.price').text.strip(),
            })

        self.logger.info("parsed_items", count=len(results))
        return results
```

### 4. 동적 크롤러 (`crawlers/dynamic.py`)

```python
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from .base import BaseCrawler

class DynamicCrawler(BaseCrawler):
    def get_url(self) -> str:
        # TODO: 실제 URL로 변경
        return "https://spa-example.com"

    def fetch(self, url: str) -> str:
        """Playwright로 JavaScript 실행 후 HTML 가져오기"""
        self.logger.info("fetching_dynamic_url", url=url)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.config.headless)
            page = browser.new_page()
            page.goto(url, timeout=self.config.timeout * 1000)
            page.wait_for_load_state('networkidle')
            html = page.content()
            browser.close()
            return html

    def parse(self, html: str) -> list[dict]:
        """BeautifulSoup으로 파싱 (정적 크롤러와 동일 가능)"""
        soup = BeautifulSoup(html, 'lxml')

        # TODO: 실제 사이트 구조에 맞게 수정
        results = []
        # ... 파싱 로직

        self.logger.info("parsed_items", count=len(results))
        return results
```

### 5. CSV Writer (`writers/csv_writer.py`)

```python
import csv
from pathlib import Path
from typing import Any

class CSVWriter:
    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, data: list[dict[str, Any]], mode: str = 'w') -> None:
        """데이터를 CSV로 저장"""
        if not data:
            return

        fieldnames = data[0].keys()
        with open(self.output_path, mode, newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if mode == 'w':
                writer.writeheader()
            writer.writerows(data)

    def append(self, data: list[dict[str, Any]]) -> None:
        """기존 파일에 추가"""
        self.write(data, mode='a')
```

### 6. 메인 스크립트 (`scripts/main.py`)

```python
import argparse
from pathlib import Path
from crawler.config import CrawlerConfig
from crawler.writers.csv_writer import CSVWriter

def main():
    parser = argparse.ArgumentParser(description='HomeSweetHome Crawler')
    parser.add_argument('--output', type=Path, default='output/data.csv',
                       help='출력 파일 경로 (기본: output/data.csv)')

    args = parser.parse_args()

    # 설정 로드
    config = CrawlerConfig.from_env()

    # 크롤러 실행
    from crawler.crawlers.static import StaticCrawler
    crawler = StaticCrawler(config)

    # 크롤링
    results = crawler.crawl()

    # CSV 저장
    writer = CSVWriter(args.output)
    writer.write(results)

    print(f"✓ {len(results)}개 데이터를 {args.output}에 저장했습니다.")

if __name__ == '__main__':
    main()
```

## 개발 환경 설정

### pre-commit (`.pre-commit-config.yaml`)

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

### GitHub Actions (`.github/workflows/ci.yml`)

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Sync dependencies
        run: uv sync --locked

      - name: Run ruff
        run: uv run ruff check .

      - name: Run mypy
        run: uv run mypy src/

      - name: Run tests
        run: uv run pytest
```

### pyproject.toml 구조

```toml
[build-system]
requires = ["hatchling>=1.26"]
build-backend = "hatchling.build"

[project]
name = "homesweethome"
version = "0.1.0"
description = "Python web crawler boilerplate with CSV export"
requires-python = ">=3.11"
dependencies = [
    "requests>=2.31.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.0.0",
    "playwright>=1.40.0",
    "python-dotenv>=1.0.0",
    "structlog>=24.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "ruff>=0.4.0",
    "mypy>=1.10.0",
    "pre-commit>=3.5.0",
    "types-requests>=2.31.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = "src"
```

## 초기 설정 단계

```bash
# 1. 프로젝트 초기화 (현재 디렉토리에서)
uv init

# 2. 의존성 추가
uv add requests beautifulsoup4 lxml playwright python-dotenv structlog

# 3. 개발 의존성 추가
uv add --dev pytest ruff mypy pre-commit types-requests

# 4. Playwright 브라우저 설치
uv run playwright install chromium

# 5. pre-commit 설치
uv run pre-commit install

# 6. .env 파일 생성
cp .env.example .env
```

## 사용 방법

```bash
# 기본 사용
python scripts/main.py

# 출력 파일 지정
python scripts/main.py --output results/my_data.csv
```

## 새 사이트 크롤러 추가 방법

1. `src/crawler/crawlers/` 아래에 새 파일 생성 (예: `naver.py`)
2. `BaseCrawler` 상속
3. 필수 메서드 구현:
   - `get_url()`: 크롤링할 URL 반환
   - `parse()`: HTML 파싱 로직
4. 정적 사이트면 `fetch()`는 `StaticCrawler`에서 상속
5. 동적 사이트면 `fetch()`는 `DynamicCrawler`에서 상속

## 테스트 전략

- **Unit 테스트**: 파싱 로직, CSV writer
- **Integration 테스트**: 실제 크롤링 (테스트 페이지 활용)
- pytest fixtures로 공통 설정 관리

## 확장 고려사항

향후 필요 시 추가 가능한 기능들:

- Rate limiting (요청 간 딜레이)
- Retry 로직 (재시도 메커니즘)
- 프록시 지원
- User-Agent rotation
- 비동기 크롤링 (현재는 동기 방식)
- 멀티 프로세싱
- 데이터 검증 레이어

현재는 최소한의 구조로 시작하고, 실제 필요에 따라 확장.
