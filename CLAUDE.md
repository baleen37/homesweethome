# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

HomeSweetHome is a Python-based web crawling framework optimized for Korean real estate data collection, particularly from Hogangnono. The project follows a clean n-tier architecture with dependency injection patterns and is currently undergoing active refactoring to improve code quality and performance.

## Development Commands

### Environment Setup

```bash
# Install dependencies (using uv)
uv sync

# Install Playwright browser
uv run playwright install chromium

# Setup pre-commit hooks
uv run pre-commit install

# With Nix/direnv (recommended)
direnv allow  # First time only
```

### Testing

```bash
# Run all tests
uv run pytest -v

# Run unit tests only
uv run pytest tests/unit/ -v

# Run integration tests (exclude slow tests)
uv run pytest tests/integration/ -v -m "not slow"

# Run specific test
uv run pytest tests/unit/test_enhanced_error_handler.py -v

# Run with coverage
uv run pytest --cov=src/crawler --cov-report=term-missing
```

### Code Quality

```bash
# Lint and fix
uv run ruff check .
uv run ruff format .

# Type checking
uv run mypy src/

# Find dead code
uv run vulture src/
```

### Running the Crawler

```bash
# Basic run
uv run python scripts/main.py

# With specific crawling method
uv run python scripts/main.py --method bbox

# Specific districts
uv run python scripts/main.py --district 강남구,서초구

# Full period data collection
uv run python scripts/main.py --full-period

# With custom output directory
uv run python scripts/main.py --output results/20251212

# Resume from checkpoint
uv run python scripts/main.py --resume

# Crawl specific region
uv run python scripts/main.py --region gangnam
```

## Architecture Overview

The project follows a layered architecture with clear separation of concerns:

### Core Layers

1. **API Layer** (`src/crawler/api/`)
   - `BaseAPIClient`: Foundation with retry logic and error handling
   - `HogangnonoAPIClient`: Hogangnono-specific API implementation

2. **Crawler Layer** (`src/crawler/crawlers/`)
   - `ImprovedHogangnonoCrawler`: Main production crawler with DI
   - `HogangnonoCrawler`: Legacy implementation
   - `ApartmentSearchCrawler`: Specialized search functionality

3. **Data Layer**
   - **Models** (`src/crawler/models/`): Pydantic models for data validation
   - **Data Mappers** (`src/crawler/data_mappers/`): Transform API responses to domain models
   - **Validators** (`src/crawler/validators/`): Data validation logic

4. **Writer Layer** (`src/crawler/writers/`)
   - Multiple CSV writing strategies (currently being refactored)
   - Factory pattern for writer selection

5. **Utilities** (`src/crawler/utils/`)
   - `bbox_divider`: Split regions to bypass API limits
   - `checkpoint`: Resume functionality
   - `error_handler`: Centralized error handling
   - `retry`: Robust retry logic

### Key Design Patterns

- **Dependency Injection**: Using `dependency-injector` for loose coupling
- **Factory Pattern**: For crawler and writer creation
- **Strategy Pattern**: For different CSV writing approaches
- **Circuit Breaker**: To prevent cascade failures
- **Caching**: Apartment data and district codes to reduce API calls

## Configuration Management

The project supports environment-based configuration:

- `config/development.yaml`: Development settings
- `config/staging.yaml`: Staging environment
- `config/production.yaml`: Production settings

Key configuration sections:
- Rate limiting and retry policies
- Batch processing sizes
- Error handling thresholds
- Caching strategies

## Current Refactoring (2025-12-12)

The codebase is undergoing active refactoring focusing on:

1. **Error Handling Enhancement**: Automatic 404 skipping, error categorization
2. **Code Deduplication**: Reducing 16 CSV writer classes to 5
3. **Dependency Cleanup**: Removing 5 unused dependencies
4. **Performance Optimization**: 10x throughput, 70% memory reduction

## Testing Infrastructure

- **Framework**: pytest with asyncio support
- **Markers**: `@integration` for API tests, `@slow` for rate-limited tests
- **Coverage**: Currently 6%, targeting 30%
- **Mock Support**: Test crawlers with mock APIs for isolated testing

## Special Notes

- **Playwright Browsers**: Use external installation path, not Nix version (outdated)
- **Nix Support**: Fully supported with direnv for development
- **Korean Language**: All code comments, logs, and documentation should be in Korean
- **API Rate Limits**: Built-in rate limiting to respect external API constraints
- **Checkpoint System**: All operations are resumable via checkpoint files

## Data Flow

```
User Request
    ↓
Factory creates crawler (with DI)
    ↓
Crawler processes districts in parallel
    ↓
For each district:
  - Divide bbox into chunks
  - Fetch POIs (with caching)
  - Fetch apartment details
  - Fetch transactions
    ↓
Write results to CSV (batch processing)
    ↓
Update checkpoint
```

## Common Debugging Commands

```python
# Check crawler statistics
stats = crawler.get_crawler_statistics()
print(f"Cache hit rate: {stats['cache_stats']}")
print(f"Error rates: {stats['error_stats']}")

# Load checkpoint
from crawler.utils.checkpoint import CheckpointManager
cp = CheckpointManager("output/checkpoint.json")
print(f"Completed: {cp.get_stats()['completed_districts']}")
```

## Performance Considerations

- Batch size: 50 items per batch for optimal memory usage
- Workers: Adjust based on API rate limits
- Bbox division: Automatic splitting for POI API 1000-item limit
- Caching: Automatic caching of apartment data and district codes
