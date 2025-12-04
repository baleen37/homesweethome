# HomeSweetHome Crawler Boilerplate Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Python 크롤링 보일러플레이트 구축 - 정적/동적 사이트 지원, CSV 출력, uv 기반 프로젝트 관리

**Architecture:** src layout + 추상 베이스 크롤러 패턴. requests/BeautifulSoup으로 정적 사이트, Playwright로 동적 사이트 처리. 표준 csv 모듈로 데이터 저장.

**Tech Stack:** uv, requests, beautifulsoup4, lxml, playwright, python-dotenv, structlog, pytest, ruff, mypy, pre-commit

---

## Task 1: 프로젝트 초기 설정

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.python-version`
- Create: `README.md`

**Step 1: pyproject.toml 작성**

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

**Step 2: .gitignore 작성**

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
.venv/
venv/

# Output
output/
*.csv

# Environment
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store

# Testing
.pytest_cache/
.coverage
htmlcov/

# MyPy
.mypy_cache/
.dmypy.json

# Ruff
.ruff_cache/
```

**Step 3: .python-version 작성**

```
3.11
```

**Step 4: README.md 작성**

```markdown
# HomeSweetHome Crawler Boilerplate

Python 크롤링 + CSV 저장 보일러플레이트

## 설치

```bash
# 의존성 설치
uv sync

# Playwright 브라우저 설치
uv run playwright install chromium

# pre-commit 설치
uv run pre-commit install
```

## 사용

```bash
# 기본 사용
python scripts/main.py

# 출력 파일 지정
python scripts/main.py --output results/data.csv
```

## 새 크롤러 추가

1. `src/crawler/crawlers/` 아래에 파일 생성
2. `BaseCrawler` 상속
3. `get_url()`, `parse()` 메서드 구현
```

**Step 5: Commit**

```bash
git add pyproject.toml .gitignore .python-version README.md
git commit -m "chore: 프로젝트 초기 설정"
```

---

## Task 2: 의존성 설치 및 디렉토리 구조 생성

**Files:**
- Create: `src/crawler/__init__.py`
- Create: `src/crawler/crawlers/__init__.py`
- Create: `src/crawler/parsers/__init__.py`
- Create: `src/crawler/writers/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/unit/.gitkeep`
- Create: `tests/integration/.gitkeep`
- Create: `scripts/.gitkeep`

**Step 1: 의존성 설치**

Run: `uv sync`
Expected: 모든 의존성 설치 완료

**Step 2: Playwright 브라우저 설치**

Run: `uv run playwright install chromium`
Expected: Chromium 브라우저 다운로드 완료

**Step 3: src 디렉토리 구조 생성**

```bash
mkdir -p src/crawler/crawlers src/crawler/parsers src/crawler/writers
touch src/crawler/__init__.py
touch src/crawler/crawlers/__init__.py
touch src/crawler/parsers/__init__.py
touch src/crawler/writers/__init__.py
```

**Step 4: tests 디렉토리 구조 생성**

```bash
mkdir -p tests/unit tests/integration
touch tests/conftest.py
touch tests/unit/.gitkeep
touch tests/integration/.gitkeep
```

**Step 5: scripts 디렉토리 생성**

```bash
mkdir -p scripts
touch scripts/.gitkeep
```

**Step 6: Commit**

```bash
git add src/ tests/ scripts/
git commit -m "chore: 디렉토리 구조 생성"
```

---

## Task 3: 설정 관리 모듈 (config.py)

**Files:**
- Create: `tests/unit/test_config.py`
- Create: `src/crawler/config.py`
- Create: `.env.example`

**Step 1: 실패하는 테스트 작성**

Create `tests/unit/test_config.py`:

```python
from crawler.config import CrawlerConfig


def test_config_default_values():
    config = CrawlerConfig()
    assert config.timeout == 30
    assert config.headless is True
    assert config.output_dir == "output"


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("TIMEOUT", "60")
    monkeypatch.setenv("HEADLESS", "false")
    monkeypatch.setenv("OUTPUT_DIR", "results")

    config = CrawlerConfig.from_env()
    assert config.timeout == 60
    assert config.headless is False
    assert config.output_dir == "results"


def test_config_from_env_with_overrides(monkeypatch):
    monkeypatch.setenv("TIMEOUT", "60")

    config = CrawlerConfig.from_env(timeout=90)
    assert config.timeout == 90
```

**Step 2: 테스트 실행 및 실패 확인**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: FAIL (모듈 없음)

**Step 3: 최소 구현**

Create `src/crawler/config.py`:

```python
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
```

**Step 4: 테스트 실행 및 통과 확인**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: PASS

**Step 5: .env.example 작성**

Create `.env.example`:

```
TIMEOUT=30
HEADLESS=true
OUTPUT_DIR=output
```

**Step 6: Commit**

```bash
git add tests/unit/test_config.py src/crawler/config.py .env.example
git commit -m "feat: 설정 관리 모듈 구현"
```

---

## Task 4: CSV Writer

**Files:**
- Create: `tests/unit/test_csv_writer.py`
- Create: `src/crawler/writers/csv_writer.py`

**Step 1: 실패하는 테스트 작성**

Create `tests/unit/test_csv_writer.py`:

```python
from pathlib import Path

from crawler.writers.csv_writer import CSVWriter


def test_csv_writer_creates_file(tmp_path: Path):
    output_file = tmp_path / "test.csv"
    writer = CSVWriter(output_file)
    data = [{"name": "test", "value": 123}]

    writer.write(data)

    assert output_file.exists()


def test_csv_writer_writes_header_and_rows(tmp_path: Path):
    output_file = tmp_path / "test.csv"
    writer = CSVWriter(output_file)
    data = [{"name": "item1", "price": 100}, {"name": "item2", "price": 200}]

    writer.write(data)

    content = output_file.read_text()
    lines = content.strip().split("\n")
    assert len(lines) == 3
    assert "name,price" in lines[0]
    assert "item1,100" in lines[1]


def test_csv_writer_creates_parent_directory(tmp_path: Path):
    output_file = tmp_path / "subdir" / "nested" / "test.csv"
    writer = CSVWriter(output_file)
    data = [{"key": "value"}]

    writer.write(data)

    assert output_file.exists()


def test_csv_writer_handles_empty_data(tmp_path: Path):
    output_file = tmp_path / "test.csv"
    writer = CSVWriter(output_file)

    writer.write([])

    assert not output_file.exists()


def test_csv_writer_append_mode(tmp_path: Path):
    output_file = tmp_path / "test.csv"
    writer = CSVWriter(output_file)
    data1 = [{"name": "item1", "value": 1}]
    data2 = [{"name": "item2", "value": 2}]

    writer.write(data1)
    writer.append(data2)

    content = output_file.read_text()
    lines = content.strip().split("\n")
    assert len(lines) == 3
```

**Step 2: 테스트 실행 및 실패 확인**

Run: `uv run pytest tests/unit/test_csv_writer.py -v`
Expected: FAIL (모듈 없음)

**Step 3: 최소 구현**

Create `src/crawler/writers/csv_writer.py`:

```python
import csv
from pathlib import Path
from typing import Any


class CSVWriter:
    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path

    def write(self, data: list[dict[str, Any]], mode: str = "w") -> None:
        """데이터를 CSV로 저장"""
        if not data:
            return

        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = data[0].keys()
        with open(self.output_path, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if mode == "w":
                writer.writeheader()
            writer.writerows(data)

    def append(self, data: list[dict[str, Any]]) -> None:
        """기존 파일에 추가"""
        self.write(data, mode="a")
```

**Step 4: 테스트 실행 및 통과 확인**

Run: `uv run pytest tests/unit/test_csv_writer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_csv_writer.py src/crawler/writers/csv_writer.py
git commit -m "feat: CSV Writer 구현"
```

---

## Task 5: 크롤러 베이스 클래스

**Files:**
- Create: `tests/unit/test_base_crawler.py`
- Create: `src/crawler/crawlers/base.py`

**Step 1: 실패하는 테스트 작성**

Create `tests/unit/test_base_crawler.py`:

```python
from crawler.config import CrawlerConfig
from crawler.crawlers.base import BaseCrawler


class TestCrawler(BaseCrawler):
    def get_url(self) -> str:
        return "https://example.com"

    def fetch(self, url: str) -> str:
        return "<html><body>Test</body></html>"

    def parse(self, html: str) -> list[dict]:
        return [{"data": "test"}]


def test_base_crawler_has_config():
    config = CrawlerConfig()
    crawler = TestCrawler(config)
    assert crawler.config == config


def test_base_crawler_has_logger():
    config = CrawlerConfig()
    crawler = TestCrawler(config)
    assert crawler.logger is not None


def test_base_crawler_crawl_calls_methods():
    config = CrawlerConfig()
    crawler = TestCrawler(config)

    results = crawler.crawl()

    assert results == [{"data": "test"}]
```

**Step 2: 테스트 실행 및 실패 확인**

Run: `uv run pytest tests/unit/test_base_crawler.py -v`
Expected: FAIL (모듈 없음)

**Step 3: 최소 구현**

Create `src/crawler/crawlers/base.py`:

```python
from abc import ABC, abstractmethod

import structlog

from crawler.config import CrawlerConfig


class BaseCrawler(ABC):
    def __init__(self, config: CrawlerConfig) -> None:
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

    @abstractmethod
    def get_url(self) -> str:
        """크롤링할 URL 반환"""
        pass

    def crawl(self) -> list[dict]:
        """크롤링 + 파싱"""
        url = self.get_url()
        html = self.fetch(url)
        return self.parse(html)
```

**Step 4: 테스트 실행 및 통과 확인**

Run: `uv run pytest tests/unit/test_base_crawler.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_base_crawler.py src/crawler/crawlers/base.py
git commit -m "feat: 크롤러 베이스 클래스 구현"
```

---

## Task 6: 정적 크롤러 (StaticCrawler)

**Files:**
- Create: `tests/unit/test_static_crawler.py`
- Create: `src/crawler/crawlers/static.py`

**Step 1: 실패하는 테스트 작성**

Create `tests/unit/test_static_crawler.py`:

```python
from unittest.mock import Mock, patch

from crawler.config import CrawlerConfig
from crawler.crawlers.static import StaticCrawler


def test_static_crawler_fetch_returns_html():
    config = CrawlerConfig()
    crawler = StaticCrawler(config)

    mock_response = Mock()
    mock_response.text = "<html><body>Test</body></html>"
    mock_response.raise_for_status = Mock()

    with patch("requests.get", return_value=mock_response) as mock_get:
        html = crawler.fetch("https://example.com")

        mock_get.assert_called_once_with("https://example.com", timeout=30)
        assert html == "<html><body>Test</body></html>"


def test_static_crawler_parse_extracts_data():
    config = CrawlerConfig()
    crawler = StaticCrawler(config)

    html = """
    <html>
        <body>
            <div class="item">
                <span class="title">Item 1</span>
                <span class="price">100</span>
            </div>
            <div class="item">
                <span class="title">Item 2</span>
                <span class="price">200</span>
            </div>
        </body>
    </html>
    """

    results = crawler.parse(html)

    assert len(results) == 2
    assert results[0]["title"] == "Item 1"
    assert results[0]["price"] == "100"
    assert results[1]["title"] == "Item 2"
    assert results[1]["price"] == "200"
```

**Step 2: 테스트 실행 및 실패 확인**

Run: `uv run pytest tests/unit/test_static_crawler.py -v`
Expected: FAIL (모듈 없음)

**Step 3: 최소 구현**

Create `src/crawler/crawlers/static.py`:

```python
import requests
from bs4 import BeautifulSoup

from crawler.crawlers.base import BaseCrawler


class StaticCrawler(BaseCrawler):
    def get_url(self) -> str:
        return "https://example.com"

    def fetch(self, url: str) -> str:
        """requests로 HTML 가져오기"""
        self.logger.info("fetching_url", url=url)
        response = requests.get(url, timeout=self.config.timeout)
        response.raise_for_status()
        return response.text

    def parse(self, html: str) -> list[dict]:
        """BeautifulSoup으로 파싱"""
        soup = BeautifulSoup(html, "lxml")

        items = soup.select(".item")
        results = []

        for item in items:
            title_elem = item.select_one(".title")
            price_elem = item.select_one(".price")

            if title_elem and price_elem:
                results.append({
                    "title": title_elem.text.strip(),
                    "price": price_elem.text.strip(),
                })

        self.logger.info("parsed_items", count=len(results))
        return results
```

**Step 4: 테스트 실행 및 통과 확인**

Run: `uv run pytest tests/unit/test_static_crawler.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_static_crawler.py src/crawler/crawlers/static.py
git commit -m "feat: 정적 크롤러 구현"
```

---

## Task 7: 동적 크롤러 (DynamicCrawler)

**Files:**
- Create: `tests/unit/test_dynamic_crawler.py`
- Create: `src/crawler/crawlers/dynamic.py`

**Step 1: 실패하는 테스트 작성**

Create `tests/unit/test_dynamic_crawler.py`:

```python
from unittest.mock import Mock, patch

from crawler.config import CrawlerConfig
from crawler.crawlers.dynamic import DynamicCrawler


def test_dynamic_crawler_fetch_uses_playwright():
    config = CrawlerConfig(headless=True, timeout=30)
    crawler = DynamicCrawler(config)

    mock_page = Mock()
    mock_page.content.return_value = "<html><body>Dynamic Content</body></html>"
    mock_browser = Mock()
    mock_browser.new_page.return_value = mock_page
    mock_playwright = Mock()
    mock_playwright.chromium.launch.return_value = mock_browser

    with patch("crawler.crawlers.dynamic.sync_playwright") as mock_sync:
        mock_sync.return_value.__enter__.return_value = mock_playwright

        html = crawler.fetch("https://example.com")

        mock_playwright.chromium.launch.assert_called_once_with(headless=True)
        mock_page.goto.assert_called_once_with(
            "https://example.com", timeout=30000
        )
        mock_page.wait_for_load_state.assert_called_once_with("networkidle")
        assert html == "<html><body>Dynamic Content</body></html>"


def test_dynamic_crawler_parse_extracts_data():
    config = CrawlerConfig()
    crawler = DynamicCrawler(config)

    html = """
    <html>
        <body>
            <div class="item">
                <span class="title">Dynamic Item</span>
                <span class="price">500</span>
            </div>
        </body>
    </html>
    """

    results = crawler.parse(html)

    assert len(results) == 1
    assert results[0]["title"] == "Dynamic Item"
    assert results[0]["price"] == "500"
```

**Step 2: 테스트 실행 및 실패 확인**

Run: `uv run pytest tests/unit/test_dynamic_crawler.py -v`
Expected: FAIL (모듈 없음)

**Step 3: 최소 구현**

Create `src/crawler/crawlers/dynamic.py`:

```python
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from crawler.crawlers.base import BaseCrawler


class DynamicCrawler(BaseCrawler):
    def get_url(self) -> str:
        return "https://example.com"

    def fetch(self, url: str) -> str:
        """Playwright로 JavaScript 실행 후 HTML 가져오기"""
        self.logger.info("fetching_dynamic_url", url=url)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.config.headless)
            page = browser.new_page()
            page.goto(url, timeout=self.config.timeout * 1000)
            page.wait_for_load_state("networkidle")
            html = page.content()
            browser.close()
            return html

    def parse(self, html: str) -> list[dict]:
        """BeautifulSoup으로 파싱"""
        soup = BeautifulSoup(html, "lxml")

        items = soup.select(".item")
        results = []

        for item in items:
            title_elem = item.select_one(".title")
            price_elem = item.select_one(".price")

            if title_elem and price_elem:
                results.append({
                    "title": title_elem.text.strip(),
                    "price": price_elem.text.strip(),
                })

        self.logger.info("parsed_items", count=len(results))
        return results
```

**Step 4: 테스트 실행 및 통과 확인**

Run: `uv run pytest tests/unit/test_dynamic_crawler.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_dynamic_crawler.py src/crawler/crawlers/dynamic.py
git commit -m "feat: 동적 크롤러 구현"
```

---

## Task 8: 메인 스크립트

**Files:**
- Create: `tests/integration/test_main.py`
- Create: `scripts/main.py`

**Step 1: 실패하는 테스트 작성**

Create `tests/integration/test_main.py`:

```python
import subprocess
from pathlib import Path


def test_main_script_runs_successfully(tmp_path: Path):
    output_file = tmp_path / "test_output.csv"

    result = subprocess.run(
        ["python", "scripts/main.py", "--output", str(output_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "저장했습니다" in result.stdout
```

**Step 2: 테스트 실행 및 실패 확인**

Run: `uv run pytest tests/integration/test_main.py -v`
Expected: FAIL (스크립트 없음)

**Step 3: 최소 구현**

Create `scripts/main.py`:

```python
import argparse
from pathlib import Path

from crawler.config import CrawlerConfig
from crawler.crawlers.static import StaticCrawler
from crawler.writers.csv_writer import CSVWriter


def main() -> None:
    parser = argparse.ArgumentParser(description="HomeSweetHome Crawler")
    parser.add_argument(
        "--output",
        type=Path,
        default="output/data.csv",
        help="출력 파일 경로 (기본: output/data.csv)",
    )

    args = parser.parse_args()

    config = CrawlerConfig.from_env()

    crawler = StaticCrawler(config)

    results = crawler.crawl()

    writer = CSVWriter(args.output)
    writer.write(results)

    print(f"✓ {len(results)}개 데이터를 {args.output}에 저장했습니다.")


if __name__ == "__main__":
    main()
```

**Step 4: 테스트 실행 및 통과 확인**

Run: `uv run pytest tests/integration/test_main.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/integration/test_main.py scripts/main.py
git commit -m "feat: 메인 스크립트 구현"
```

---

## Task 9: pre-commit 설정

**Files:**
- Create: `.pre-commit-config.yaml`

**Step 1: .pre-commit-config.yaml 작성**

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
        args: [--config-file=pyproject.toml]
```

**Step 2: pre-commit 설치**

Run: `uv run pre-commit install`
Expected: pre-commit hook 설치 완료

**Step 3: pre-commit 실행 테스트**

Run: `uv run pre-commit run --all-files`
Expected: 모든 체크 통과

**Step 4: Commit**

```bash
git add .pre-commit-config.yaml
git commit -m "chore: pre-commit 설정 추가"
```

---

## Task 10: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

**Step 1: CI 워크플로우 작성**

Create `.github/workflows/ci.yml`:

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

      - name: Add uv to PATH
        run: echo "$HOME/.cargo/bin" >> $GITHUB_PATH

      - name: Sync dependencies
        run: uv sync --locked

      - name: Install Playwright browsers
        run: uv run playwright install chromium

      - name: Run ruff check
        run: uv run ruff check .

      - name: Run ruff format check
        run: uv run ruff format --check .

      - name: Run mypy
        run: uv run mypy src/

      - name: Run tests
        run: uv run pytest -v
```

**Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: GitHub Actions 워크플로우 추가"
```

---

## Task 11: 최종 검증 및 문서화

**Step 1: 전체 테스트 실행**

Run: `uv run pytest -v`
Expected: 모든 테스트 PASS

**Step 2: Ruff 검사**

Run: `uv run ruff check .`
Expected: 이슈 없음

**Step 3: Ruff 포맷 검사**

Run: `uv run ruff format --check .`
Expected: 포맷 이슈 없음

**Step 4: MyPy 타입 체크**

Run: `uv run mypy src/`
Expected: 타입 에러 없음

**Step 5: README 업데이트**

Modify `README.md`에 다음 섹션 추가:

```markdown
## 개발

### 테스트 실행

```bash
uv run pytest -v
```

### 코드 품질 검사

```bash
# Linting
uv run ruff check .

# Formatting
uv run ruff format .

# Type checking
uv run mypy src/
```

### 새 크롤러 추가 예시

```python
# src/crawler/crawlers/my_site.py
from crawler.crawlers.base import BaseCrawler
from bs4 import BeautifulSoup
import requests

class MySiteCrawler(BaseCrawler):
    def get_url(self) -> str:
        return "https://mysite.com"

    def fetch(self, url: str) -> str:
        response = requests.get(url, timeout=self.config.timeout)
        response.raise_for_status()
        return response.text

    def parse(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        # 파싱 로직 구현
        return []
```
```

**Step 6: Commit**

```bash
git add README.md
git commit -m "docs: README 업데이트"
```

**Step 7: 최종 검증**

Run: `python scripts/main.py --output output/test.csv`
Expected: 실행 성공 및 CSV 파일 생성

---

## 완료 체크리스트

- [ ] Task 1: 프로젝트 초기 설정
- [ ] Task 2: 의존성 설치 및 디렉토리 구조
- [ ] Task 3: 설정 관리 모듈
- [ ] Task 4: CSV Writer
- [ ] Task 5: 크롤러 베이스 클래스
- [ ] Task 6: 정적 크롤러
- [ ] Task 7: 동적 크롤러
- [ ] Task 8: 메인 스크립트
- [ ] Task 9: pre-commit 설정
- [ ] Task 10: GitHub Actions CI
- [ ] Task 11: 최종 검증 및 문서화

## 주의사항

- 각 Task는 TDD 방식으로 진행: 테스트 작성 → 실패 확인 → 구현 → 통과 확인 → Commit
- 모든 코드는 type hints 포함
- Commit 메시지는 conventional commits 규칙 준수
- 각 단계마다 테스트가 통과하는지 확인
