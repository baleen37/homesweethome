# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

homesweethome is a TDD-based web crawling boilerplate for collecting Seoul apartment data. The project uses a Template Method pattern with an abstract base class that all concrete crawlers must inherit from.

## Development Commands

```bash
# Install dependencies
uv sync

# Install Playwright browser (required for integration/E2E tests)
uv run playwright install chromium

# Run tests (unit + integration only)
uv run pytest -v

# Run tests including E2E (against real websites)
uv run pytest -v -m e2e

# Run single test file
uv run pytest tests/unit/test_base_crawler.py -v

# Run single test function
uv run pytest tests/unit/test_base_crawler.py::test_function_name -v

# Run crawler (SINGLE ENTRY POINT - all crawling operations)
uv run python -m crawler.commands.crawl asil-naver --dong-code 1150010100 --radius 300
uv run python -m crawler.commands.crawl apt-list --dong-code 1150010100
uv run python -m crawler.commands.crawl apt-trade --dong-code 1150010100

# Code formatting and linting (auto-run via pre-commit)
uv run ruff check .
uv run ruff format .
```

## Architecture

### Core Design Pattern: Template Method

All crawlers inherit from `BaseCrawler` (src/crawler/base.py), which defines the crawling workflow:

- `get_url()`: Abstract - returns the URL to crawl
- `fetch(url)`: Abstract - fetches HTML/JSON content
- `parse(content)`: Abstract - extracts structured data from content
- `crawl()`: Template method - orchestrates fetch → parse workflow

### Test Structure (3 Layers)

1. **Unit tests** (`tests/unit/`): Use mocks to verify interfaces in isolation
2. **Integration tests** (`tests/integration/`): Test component interaction with Playwright
3. **E2E tests** (`tests/e2e/`): Full crawl against real websites, requires `-m e2e` flag

Test markers are defined in `tests/conftest.py` and pyproject.toml.

## Project Structure

```
src/crawler/        # Source code
tests/unit/         # Unit tests (mocked)
tests/integration/  # Integration tests (Playwright)
tests/e2e/          # E2E tests (real sites)
docs/plans/         # Design documents and development plans
output/             # CSV output (gitignored)
```

## Single Entry Point Policy

**IMPORTANT**: This project uses a SINGLE entry point for all crawling operations.

**Entry point**: `src/crawler/commands/crawl.py`

**Usage**:
```bash
uv run python -m crawler.commands.crawl <subcommand> [options]
```

**Available subcommands**:
- `asil-naver`: ASIL → Naver 매물 크롤링 (매물 목록 + 상세 정보)
- `apt-list`: ASIL 아파트 목록 크롤링
- `apt-trade`: 아파트 기본정보 + 실거래가 크롤링

**Do NOT**:
- Create new standalone scripts in `scripts/` (deprecated)
- Create separate CLI files under `src/crawler/commands/`
- Add new entry points to `pyproject.toml`

All new crawling functionality must be implemented as a subcommand under `crawl.py`.

## Code Conventions

- **Language**: Korean for comments, documentation, and commit messages
- **Line length**: 100 characters (enforced by ruff)
- **Python version**: 3.11+
- **TDD**: Tests must be written before implementation
- **Pre-commit**: ruff runs automatically on commit (do not bypass)

## Rate Limiting Policy

### 네이버 API Abuse 방지

네이버 부동산 API는 과도한 요청을 감지하면 `/error/abuse`로 리다이렉트합니다. 이를 방지하기 위해 다음 정책을 준수합니다:

1. **요청 간격**: 5~10초 랜덤 딜레이 (random jitter)
2. **Abuse 감지 시 Playwright 우회**:
   - `/error/abuse` 리다이렉트 감지 시 Playwright로 브라우저 자동화
   - 실제 브라우저 쿠키/토큰 획득 후 재시도

### CLI 실행 시 주의사항

```bash
# 단일 동 코드 테스트 (안전)
uv run python -m crawler.commands.crawl asil-naver --dong-code 1150010100

# 서울 전체 실행 (주의: 시간 오래 걸림)
uv run python -m crawler.commands.crawl asil-naver --all
```
