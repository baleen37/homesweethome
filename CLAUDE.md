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

# Run example script
uv run python scripts/main.py

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
scripts/            # Executable example scripts
docs/plans/         # Design documents and development plans
output/             # CSV output (gitignored)
```

## Code Conventions

- **Language**: Korean for comments, documentation, and commit messages
- **Line length**: 100 characters (enforced by ruff)
- **Python version**: 3.11+
- **TDD**: Tests must be written before implementation
- **Pre-commit**: ruff runs automatically on commit (do not bypass)
