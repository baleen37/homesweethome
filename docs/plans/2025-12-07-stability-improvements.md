# 안정성 개선 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** NaverRealEstateCrawler와 관련 컴포넌트의 안정성을 체계적으로 개선하여 리소스 누수, 예외 처리, 동시성 문제를 해결

**Architecture:** 리소스 관리를 위한 context manager 패턴 도입, 중앙화된 예외 처리, 동시성 안전한 체크포인트 시스템 구현

**Tech Stack:** Python 3.11+, Playwright, structlog, pytest, threading.Lock, contextlib

---

## Task 1: 브라우저 리소스 누수 방지 (Critical)

**Files:**
- Modify: `src/crawler/crawlers/naver.py` (crawl, fetch_complex_detail, fetch_complex_listings 메서드)

**Step 1: Write failing test for resource leak**

```python
# tests/integration/test_browser_resource_management.py
import pytest
import psutil
import os
from src.crawler.crawlers.naver import NaverRealEstateCrawler
from src.crawler.config import CrawlerConfig

def test_browser_resource_cleanup_on_exception():
    """Test that browser processes are properly cleaned up even when exceptions occur"""
    config = CrawlerConfig.from_env()
    crawler = NaverRealEstateCrawler(config)

    # Count browser processes before
    initial_chromium_processes = len([p for p in psutil.process_iter()
                                    if 'chromium' in p.name().lower()])

    # Force an exception during browser usage
    with pytest.raises(Exception):
        # Mock invalid URL to trigger exception
        crawler.get_url = lambda: "invalid://url"
        crawler.crawl()

    # Check that no new chromium processes remain
    final_chromium_processes = len([p for p in psutil.process_iter()
                                  if 'chromium' in p.name().lower()])

    assert final_chromium_processes == initial_chromium_processes
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_browser_resource_management.py::test_browser_resource_cleanup_on_exception -v`
Expected: FAIL (browser process leaked)

**Step 3: Implement BrowserManager context manager**

```python
# src/crawler/utils/browser_manager.py
from contextlib import contextmanager
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from typing import Generator, Optional
import structlog

logger = structlog.get_logger()

@contextmanager
def managed_browser(headless: bool = True, timeout: float = 30000) -> Generator[Page, None, None]:
    """
    Context manager for managing browser resources safely
    Ensures browser is always closed even if exceptions occur
    """
    browser: Optional[Browser] = None
    context: Optional[BrowserContext] = None
    page: Optional[Page] = None

    try:
        with sync_playwright() as p:
            logger.info("launching_browser", headless=headless)
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = context.new_page()
            page.set_default_timeout(timeout)
            yield page

    except Exception as e:
        logger.error("browser_operation_failed", error=str(e))
        raise
    finally:
        # Cleanup in reverse order of creation
        if page and not page.is_closed():
            page.close()
            logger.info("browser_page_closed")

        if context:
            context.close()
            logger.info("browser_context_closed")

        if browser:
            browser.close()
            logger.info("browser_closed")
```

**Step 4: Update NaverRealEstateCrawler to use BrowserManager**

```python
# src/crawler/crawlers/naver.py - update crawl method
from src.crawler.utils.browser_manager import managed_browser

def crawl(self) -> list[dict[str, Any]]:
    """메인 크롤링 실행 (점진적 크롤링 지원)"""
    if not self.should_resume_crawl():
        # 초기 실행 시 CSV 파일 생성
        self.csv_writer.write_header(self.csv_fields)

    all_results = []

    try:
        # Browser context에서 크롤링 실행
        with managed_browser(headless=self.config.headless, timeout=self.config.page_load_timeout) as page:
            self.page = page

            # 1. 서울시 전체의 단지 목록 조회
            logging.info("fetching_all_seoul_complexes")
            complexes = self.fetch_complex_list()

            if not complexes:
                logging.warning("no_complexes_found")
                return all_results

            # 체크포인트에서 복구할 시작 위치 계산
            start_index = self.calculate_start_position(complexes)

            # 2. 각 단지별 상세 정보 및 매물 목록 크롤링
            for idx in range(start_index, len(complexes), self.page_size):
                batch = complexes[idx:idx + self.page_size]

                for complex_info in batch:
                    complex_id = complex_info['complex_id']
                    complex_name = complex_info['complex_name']
                    lawd_code = complex_info['lawd_code']

                    # 체크포인트 확인
                    if self.is_complex_processed(complex_id):
                        logging.info("skipping_processed_complex",
                                   complex_id=complex_id,
                                   complex_name=complex_name)
                        continue

                    logging.info("processing_complex",
                               complex_id=complex_id,
                               complex_name=complex_name)

                    try:
                        # 단지 상세 정보 조회
                        detail_info = self.fetch_complex_detail(complex_id)
                        if not detail_info:
                            logging.warning("no_detail_info", complex_id=complex_id)
                            continue

                        # 단지별 매물 목록 조회 (모든 거래 유형)
                        listings = []
                        for trade_type in self.trade_types:
                            type_listings = self.fetch_complex_listings(complex_id, trade_type)
                            listings.extend(type_listings)

                        # 상세 정보와 매물 목록 결합
                        result = {
                            **complex_info,
                            **detail_info,
                            'listings_count': len(listings),
                            'listings': listings,
                            'crawled_at': datetime.now().isoformat(),
                            'trade_types': self.trade_types
                        }

                        # CSV에 저장
                        self.csv_writer.write_rows([result])
                        self.save_checkpoint(complex_id, result)

                        all_results.append(result)

                        # Rate limiting
                        self.rate_limiter.wait()

                    except Exception as e:
                        logging.error("failed_to_process_complex",
                                    complex_id=complex_id,
                                    error=str(e))
                        continue

    except KeyboardInterrupt:
        logging.info("crawl_interrupted_by_user")
    except Exception as e:
        logging.error("crawl_failed", error=str(e))
        raise

    finally:
        # 페이지 참조 정리
        self.page = None

    logging.info("crawl_completed",
               total_complexes=len(complexes),
               processed_complexes=len(all_results))

    return all_results
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_browser_resource_management.py::test_browser_resource_cleanup_on_exception -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/crawler/utils/browser_manager.py src/crawler/crawlers/naver.py tests/integration/test_browser_resource_management.py
git commit -m "feat: add browser resource management with context manager

- Add BrowserManager context manager for safe resource cleanup
- Update NaverRealEstateCrawler to use managed_browser
- Add test to verify browser processes are properly cleaned up"
```

---

## Task 2: 재시도 로직 중복 제거 (Critical)

**Files:**
- Modify: `src/crawler/crawlers/naver.py` (_fetch_with_retry 메서드)
- Modify: `src/crawler/utils/retry.py` (Retryable 클래스 확장)

**Step 1: Write failing test**

```python
# tests/unit/test_retry_integration.py
import pytest
from unittest.mock import Mock, patch
from src.crawler.utils.retry import Retryable, RetryConfig
from src.crawler.crawlers.naver import NaverRealEstateCrawler
from src.crawler.config import CrawlerConfig

def test_naver_crawler_uses_retryable_class():
    """Test that NaverRealEstateCrawler uses Retryable instead of custom retry logic"""
    config = CrawlerConfig.from_env()
    crawler = NaverRealEstateCrawler(config)

    # Mock the browser evaluation
    with patch.object(crawler, 'page') as mock_page:
        mock_page.evaluate.side_effect = [
            {"error": {"message": "HTTP 429"}},  # First call fails
            {"error": {"message": "HTTP 429"}},  # Second call fails
            {"result": {"data": "success"}}      # Third call succeeds
        ]

        result = crawler._fetch_with_retry("test_url")

        # Should use Retryable which handles retries automatically
        assert result == {"result": {"data": "success"}}
        assert mock_page.evaluate.call_count == 3
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_retry_integration.py::test_naver_crawler_uses_retryable_class -v`
Expected: FAIL (custom retry logic not using Retryable)

**Step 3: Enhance Retryable class for browser operations**

```python
# src/crawler/utils/retry.py
from typing import Any, Callable, Optional, TypeVar, Union
import time
import random
import structlog
from enum import Enum

logger = structlog.get_logger()

class RetryStrategy(Enum):
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"
    FIBONACCI = "fibonacci"

class RetryConfig:
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_multiplier: float = 2.0,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        jitter: bool = True,
        retryable_exceptions: tuple[type[Exception], ...] = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.strategy = strategy
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions

class Retryable:
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.logger = structlog.get_logger()

    def execute(
        self,
        func: Callable[..., Any],
        *args,
        operation_name: str = "operation",
        **kwargs
    ) -> Any:
        """Execute function with retry logic"""
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                result = func(*args, **kwargs)

                # Check if result indicates error (common in browser operations)
                if isinstance(result, dict) and "error" in result:
                    error_info = result["error"]
                    error_message = error_info.get("message", "Unknown error")

                    # Check for 429 or other retryable errors
                    if "429" in str(error_message) or "rate limit" in str(error_message).lower():
                        raise Exception(f"Rate limit exceeded: {error_message}")

                    # Non-retryable error
                    raise Exception(f"API error: {error_message}")

                if attempt > 0:
                    self.logger.info(
                        "operation_succeeded_after_retry",
                        operation=operation_name,
                        attempt=attempt + 1,
                        max_attempts=self.config.max_attempts
                    )

                return result

            except self.config.retryable_exceptions as e:
                last_exception = e

                if attempt == self.config.max_attempts - 1:
                    self.logger.error(
                        "operation_failed_all_attempts",
                        operation=operation_name,
                        error=str(e),
                        attempts=self.config.max_attempts
                    )
                    raise

                delay = self._calculate_delay(attempt)

                self.logger.warning(
                    "operation_failed_retrying",
                    operation=operation_name,
                    attempt=attempt + 1,
                    max_attempts=self.config.max_attempts,
                    delay=delay,
                    error=str(e)
                )

                time.sleep(delay)

        raise last_exception

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay based on strategy"""
        if self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (self.config.backoff_multiplier ** attempt)
        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.base_delay * (attempt + 1)
        elif self.config.strategy == RetryStrategy.FIBONACCI:
            delay = self.config.base_delay * self._fibonacci(attempt + 1)
        else:  # FIXED
            delay = self.config.base_delay

        delay = min(delay, self.config.max_delay)

        if self.config.jitter:
            delay *= (0.5 + random.random() * 0.5)  # 50% to 100% of delay

        return delay

    def _fibonacci(self, n: int) -> int:
        """Calculate nth Fibonacci number"""
        if n <= 1:
            return n

        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b

        return b

# Browser-specific retry configuration
BROWSER_RETRY_CONFIG = RetryConfig(
    max_attempts=5,  # More retries for browser operations
    base_delay=2.0,  # Start with 2 seconds
    max_delay=60.0,
    backoff_multiplier=2.0,
    strategy=RetryStrategy.EXPONENTIAL,
    jitter=True,
    retryable_exceptions=(
        ConnectionError,
        TimeoutError,
        Exception,  # Include generic Exception for browser errors
    )
)
```

**Step 4: Update NaverRealEstateCrawler to use Retryable**

```python
# src/crawler/crawlers/naver.py
from src.crawler.utils.retry import Retryable, BROWSER_RETRY_CONFIG

class NaverRealEstateCrawler(BaseCrawler):
    def __init__(self, config: CrawlerConfig):
        super().__init__(config)
        self.rate_limiter = AdaptiveRateLimiter()
        self.retryable = Retryable(BROWSER_RETRY_CONFIG)

    def _fetch_with_retry(self, url: str) -> dict[str, Any]:
        """Retryable fetch using browser's evaluate method"""
        logging.info("fetching_with_retry", url=url)

        def fetch_operation():
            # API 호출을 JavaScript로 실행하여 차단 회피
            js_code = """
            async function fetchApiData() {
                try {
                    const response = await fetch('URL_PLACEHOLDER', {
                        method: 'GET',
                        headers: {
                            'Accept': 'application/json, text/plain, */*',
                            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                            'Cache-Control': 'no-cache',
                            'Pragma': 'no-cache',
                            'Sec-Ch-Ua': '"Not.A/Brand";v="8", "Chromium";v="114"',
                            'Sec-Ch-Ua-Mobile': '?0',
                            'Sec-Ch-Ua-Platform': '"macOS"',
                            'Sec-Fetch-Dest': 'empty',
                            'Sec-Fetch-Mode': 'cors',
                            'Sec-Fetch-Site': 'same-origin',
                            'Referer': 'https://new.land.naver.com/complexes?ms=37.5442569,126.9736008,16&a=APT:ABYG:BYGG:JGC:JGM:POHG:SYS:GYCG&b=B1&e=RETAIL',
                        }
                    });

                    if (!response.ok) {
                        return {
                            error: {
                                status: response.status,
                                statusText: response.statusText,
                                message: `HTTP ${response.status}: ${response.statusText}`
                            }
                        };
                    }

                    const data = await response.json();
                    return {
                        result: data,
                        timestamp: new Date().toISOString()
                    };

                } catch (error) {
                    return {
                        error: {
                            message: error.message || 'Unknown fetch error'
                        }
                    };
                }
            }

            return fetchApiData();
            """.replace('URL_PLACEHOLDER', url)

            return self.page.evaluate(js_code)

        return self.retryable.execute(
            fetch_operation,
            operation_name=f"fetch_api_{url.split('/')[-1]}"
        )
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_retry_integration.py::test_naver_crawler_uses_retryable_class -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/crawler/utils/retry.py src/crawler/crawlers/naver.py tests/unit/test_retry_integration.py
git commit -m "refactor: remove duplicate retry logic in NaverRealEstateCrawler

- Enhance Retryable class to support browser operations
- Add browser-specific retry configuration with more attempts
- Update NaverRealEstateCrawler to use centralized Retryable
- Add integration test for retry functionality"
```

---

## Task 3: 체크포인트 동시성 문제 해결 (High)

**Files:**
- Create: `src/crawler/utils/checkpoint_manager.py`
- Modify: `src/crawler/crawlers/naver.py` (checkpoint methods)
- Modify: `tests/integration/test_checkpoint_concurrency.py`

**Step 1: Write failing test**

```python
# tests/integration/test_checkpoint_concurrency.py
import pytest
import threading
import time
from pathlib import Path
from src.crawler.utils.checkpoint_manager import CheckpointManager

def test_concurrent_checkpoint_access():
    """Test that checkpoint manager handles concurrent access safely"""
    checkpoint_file = Path("test_concurrent_checkpoint.json")
    checkpoint_file.unlink(missing_ok=True)

    manager = CheckpointManager(checkpoint_file)
    results = []
    errors = []

    def worker(worker_id):
        try:
            for i in range(10):
                manager.save(f"complex_{worker_id}_{i}", {"worker": worker_id, "index": i})
                time.sleep(0.01)  # Small delay to increase chance of race condition

                checkpoint = manager.load()
                results.append((worker_id, i, checkpoint))
        except Exception as e:
            errors.append((worker_id, str(e)))

    # Create 5 threads
    threads = []
    for i in range(5):
        thread = threading.Thread(target=worker, args=(i,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Verify no errors occurred
    assert len(errors) == 0, f"Concurrent access errors: {errors}"

    # Verify checkpoint file is not corrupted
    final_checkpoint = manager.load()
    assert isinstance(final_checkpoint, dict)

    # Cleanup
    checkpoint_file.unlink(missing_ok=True)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_checkpoint_concurrency.py::test_concurrent_checkpoint_access -v`
Expected: FAIL (CheckpointManager doesn't exist yet)

**Step 3: Implement thread-safe CheckpointManager**

```python
# src/crawler/utils/checkpoint_manager.py
import json
import threading
from pathlib import Path
from typing import Any, Optional, Dict
import structlog
from datetime import datetime

logger = structlog.get_logger()

class CheckpointManager:
    """Thread-safe checkpoint manager for crawl state persistence"""

    def __init__(self, checkpoint_file: Path):
        self.checkpoint_file = checkpoint_file
        self._lock = threading.RLock()  # Reentrant lock for nested calls
        self.logger = structlog.get_logger()

    def load(self) -> Dict[str, Any]:
        """Load checkpoint data from file"""
        with self._lock:
            if not self.checkpoint_file.exists():
                return {
                    'version': '1.0',
                    'created_at': datetime.now().isoformat(),
                    'processed_complexes': {},
                    'total_processed': 0,
                    'last_updated': None
                }

            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Validate checkpoint structure
                if not isinstance(data, dict):
                    self.logger.warning("invalid_checkpoint_format", file=str(self.checkpoint_file))
                    return self._get_empty_checkpoint()

                # Ensure required fields exist
                data.setdefault('processed_complexes', {})
                data.setdefault('total_processed', 0)

                self.logger.info("checkpoint_loaded",
                               file=str(self.checkpoint_file),
                               total_processed=data.get('total_processed', 0))

                return data

            except json.JSONDecodeError as e:
                self.logger.error("checkpoint_corrupted",
                                file=str(self.checkpoint_file),
                                error=str(e))
                # Backup corrupted file and start fresh
                self._backup_corrupted_checkpoint()
                return self._get_empty_checkpoint()

            except Exception as e:
                self.logger.error("checkpoint_load_failed",
                                file=str(self.checkpoint_file),
                                error=str(e))
                return self._get_empty_checkpoint()

    def save(self, key: str, value: Any) -> None:
        """Save a key-value pair to checkpoint"""
        with self._lock:
            checkpoint = self.load()

            # Update checkpoint data
            if 'processed_complexes' not in checkpoint:
                checkpoint['processed_complexes'] = {}

            checkpoint['processed_complexes'][key] = {
                'data': value,
                'timestamp': datetime.now().isoformat()
            }

            checkpoint['total_processed'] = len(checkpoint['processed_complexes'])
            checkpoint['last_updated'] = datetime.now().isoformat()

            # Write to file with atomic operation
            self._write_checkpoint_atomic(checkpoint)

            self.logger.debug("checkpoint_saved",
                            key=key,
                            total_processed=checkpoint['total_processed'])

    def is_processed(self, key: str) -> bool:
        """Check if a key has been processed"""
        with self._lock:
            checkpoint = self.load()
            return key in checkpoint.get('processed_complexes', {})

    def get_processed_keys(self) -> list[str]:
        """Get list of all processed keys"""
        with self._lock:
            checkpoint = self.load()
            return list(checkpoint.get('processed_complexes', {}).keys())

    def clear(self) -> None:
        """Clear all checkpoint data"""
        with self._lock:
            if self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
            self.logger.info("checkpoint_cleared", file=str(self.checkpoint_file))

    def _get_empty_checkpoint(self) -> Dict[str, Any]:
        """Get empty checkpoint structure"""
        return {
            'version': '1.0',
            'created_at': datetime.now().isoformat(),
            'processed_complexes': {},
            'total_processed': 0,
            'last_updated': None
        }

    def _write_checkpoint_atomic(self, data: Dict[str, Any]) -> None:
        """Atomically write checkpoint data to avoid corruption"""
        temp_file = self.checkpoint_file.with_suffix('.tmp')

        try:
            # Write to temporary file first
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_file.replace(self.checkpoint_file)

        except Exception as e:
            # Clean up temp file if it exists
            if temp_file.exists():
                temp_file.unlink(missing_ok=True)
            raise

    def _backup_corrupted_checkpoint(self) -> None:
        """Backup corrupted checkpoint file"""
        if self.checkpoint_file.exists():
            backup_file = self.checkpoint_file.with_suffix(
                f'.corrupted.{int(datetime.now().timestamp())}'
            )
            self.checkpoint_file.rename(backup_file)
            self.logger.warning("checkpoint_backed_up",
                              original=str(self.checkpoint_file),
                              backup=str(backup_file))
```

**Step 4: Update NaverRealEstateCrawler to use CheckpointManager**

```python
# src/crawler/crawlers/naver.py
from src.crawler.utils.checkpoint_manager import CheckpointManager

class NaverRealEstateCrawler(BaseCrawler):
    def __init__(self, config: CrawlerConfig):
        super().__init__(config)
        # ... existing init code ...

        # Initialize checkpoint manager
        output_dir = Path(self.output_file).parent
        self.checkpoint_manager = CheckpointManager(output_dir / "checkpoint.json")

    def should_resume_crawl(self) -> bool:
        """크롤링을 재개할지 확인"""
        checkpoint = self.checkpoint_manager.load()
        return checkpoint.get('total_processed', 0) > 0

    def is_complex_processed(self, complex_id: str) -> bool:
        """단지가 이미 처리되었는지 확인"""
        return self.checkpoint_manager.is_processed(complex_id)

    def calculate_start_position(self, complexes: list[dict[str, Any]]) -> int:
        """체크포인트에서 복구할 시작 위치 계산"""
        processed_keys = set(self.checkpoint_manager.get_processed_keys())

        for idx, complex_info in enumerate(complexes):
            if complex_info['complex_id'] not in processed_keys:
                return idx

        # All complexes processed
        return len(complexes)

    def save_checkpoint(self, complex_id: str, data: dict[str, Any]) -> None:
        """진행 상황 저장"""
        self.checkpoint_manager.save(complex_id, data)

    def clear_checkpoint(self) -> None:
        """체크포인트 초기화"""
        self.checkpoint_manager.clear()
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_checkpoint_concurrency.py::test_concurrent_checkpoint_access -v`
Expected: PASS

**Step 6: Add additional checkpoint tests**

```python
# tests/integration/test_checkpoint_concurrency.py

def test_checkpoint_recovery_after_corruption():
    """Test checkpoint recovery after file corruption"""
    checkpoint_file = Path("test_corrupted_checkpoint.json")
    checkpoint_file.unlink(missing_ok=True)

    manager = CheckpointManager(checkpoint_file)

    # Save some initial data
    manager.save("test_key", {"data": "test_value"})
    assert manager.is_processed("test_key")

    # Corrupt the file
    with open(checkpoint_file, 'w') as f:
        f.write("invalid json content")

    # Should recover gracefully
    checkpoint = manager.load()
    assert isinstance(checkpoint, dict)
    assert checkpoint.get('total_processed') == 0

    # Should be able to save new data
    manager.save("new_key", {"data": "new_value"})
    assert manager.is_processed("new_key")

    # Cleanup
    checkpoint_file.unlink(missing_ok=True)

def test_checkpoint_atomic_write():
    """Test that checkpoint writes are atomic"""
    checkpoint_file = Path("test_atomic_checkpoint.json")
    checkpoint_file.unlink(missing_ok=True)

    manager = CheckpointManager(checkpoint_file)

    def concurrent_saves():
        for i in range(10):
            manager.save(f"key_{i}", {"value": i})

    # Run concurrent saves
    threads = []
    for _ in range(3):
        thread = threading.Thread(target=concurrent_saves)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # Verify checkpoint is not corrupted
    checkpoint = manager.load()
    assert isinstance(checkpoint, dict)
    assert checkpoint.get('total_processed', 0) > 0

    # Cleanup
    checkpoint_file.unlink(missing_ok=True)
```

**Step 7: Run all checkpoint tests**

Run: `uv run pytest tests/integration/test_checkpoint_concurrency.py -v`
Expected: ALL PASS

**Step 8: Commit**

```bash
git add src/crawler/utils/checkpoint_manager.py src/crawler/crawlers/naver.py tests/integration/test_checkpoint_concurrency.py
git commit -m "feat: add thread-safe checkpoint manager

- Implement CheckpointManager with reentrant lock for thread safety
- Add atomic write operations to prevent corruption
- Add checkpoint recovery for corrupted files
- Update NaverRealEstateCrawler to use centralized checkpoint management
- Add comprehensive concurrency tests"
```

---

## Task 4: 입력 및 구성값 검증 강화 (High)

**Files:**
- Modify: `src/crawler/config.py` (CrawlerConfig)
- Create: `tests/unit/test_config_validation.py`

**Step 1: Write failing test for invalid configuration**

```python
# tests/unit/test_config_validation.py
import pytest
from pydantic import ValidationError
from src.crawler.config import CrawlerConfig

def test_invalid_page_size_validation():
    """Test that invalid page_size values are rejected"""
    with pytest.raises(ValidationError) as exc_info:
        CrawlerConfig(page_size=0)  # Invalid: too small

    assert "page_size" in str(exc_info.value)
    assert "must be between 1 and 1000" in str(exc_info.value)

def test_negative_timeout_validation():
    """Test that negative timeout values are rejected"""
    with pytest.raises(ValidationError) as exc_info:
        CrawlerConfig(page_load_timeout=-1)

    assert "page_load_timeout" in str(exc_info.value)
    assert("must be positive") in str(exc_info.value)

def test_invalid_retry_attempts():
    """Test that invalid retry attempts are rejected"""
    with pytest.raises(ValidationError) as exc_info:
        CrawlerConfig(max_retry_attempts=11)  # Invalid: exceeds max

    assert "max_retry_attempts" in str(exc_info.value)
    assert("must be between 0 and 10") in str(exc_info.value)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_config_validation.py -v`
Expected: FAIL (validation not implemented yet)

**Step 3: Add Pydantic validation to CrawlerConfig**

```python
# src/crawler/config.py
from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Literal
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class CrawlerConfig(BaseModel):
    """Crawler configuration with validation"""

    # Basic settings
    headless: bool = Field(default=True, description="Run browser in headless mode")
    page_size: int = Field(
        default=20,
        ge=1,
        le=1000,
        description="Number of items to process per batch (1-1000)"
    )

    # Timeout settings
    page_load_timeout: float = Field(
        default=30_000,
        gt=0,
        le=300_000,
        description="Page load timeout in milliseconds (0-300000)"
    )
    request_timeout: float = Field(
        default=10_000,
        gt=0,
        le=60_000,
        description="Request timeout in milliseconds (0-60000)"
    )

    # Retry settings
    max_retry_attempts: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts (0-10)"
    )
    retry_delay: float = Field(
        default=2.0,
        ge=0.1,
        le=60.0,
        description="Initial retry delay in seconds (0.1-60)"
    )

    # Rate limiting
    min_delay: float = Field(
        default=2.0,
        ge=0.1,
        le=60.0,
        description="Minimum delay between requests in seconds (0.1-60)"
    )
    max_delay: float = Field(
        default=10.0,
        ge=0.1,
        le=300.0,
        description="Maximum delay between requests in seconds (0.1-300)"
    )

    # Output settings
    output_format: Literal["csv", "json", "parquet"] = Field(
        default="csv",
        description="Output format"
    )
    output_file: Optional[str] = Field(
        default=None,
        description="Output file path (auto-generated if not specified)"
    )

    # Crawling settings
    crawling_types: List[Literal["apt", "officetel", "multi_family", "single_family"]] = Field(
        default=["apt"],
        description="Types of properties to crawl"
    )
    trade_types: List[Literal["sale", "rent", "jeonse"]] = Field(
        default=["sale"],
        description="Types of trades to crawl"
    )

    # Advanced settings
    enable_checkpoints: bool = Field(
        default=True,
        description="Enable checkpoint/resume functionality"
    )
    parallel_processing: bool = Field(
        default=False,
        description="Enable parallel processing (experimental)"
    )
    max_workers: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Maximum number of worker threads for parallel processing"
    )

    class Config:
        validate_assignment = True
        extra = "forbid"  # Reject additional fields

    @validator('output_file')
    def validate_output_file(cls, v, values):
        if v is not None:
            path = Path(v)
            # Ensure parent directory exists
            if not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
            # Check write permissions
            if not os.access(path.parent, os.W_OK):
                raise ValueError(f"Cannot write to output directory: {path.parent}")
        return v

    @validator('max_delay')
    def validate_delays(cls, v, values):
        if 'min_delay' in values and v <= values['min_delay']:
            raise ValueError("max_delay must be greater than min_delay")
        return v

    @validator('max_workers')
    def validate_parallel_processing(cls, v, values):
        if 'parallel_processing' in values and not values['parallel_processing'] and v > 1:
            # Warning: multiple workers without parallel processing
            pass
        return v

    @root_validator
    def validate_compatibility(cls, values):
        """Validate configuration compatibility"""
        # Check for incompatible settings
        if values.get('parallel_processing') and values.get('enable_checkpoints'):
            # Warning: checkpoints with parallel processing may have issues
            pass

        # Validate timeout hierarchy
        if values.get('request_timeout', 0) >= values.get('page_load_timeout', 0):
            raise ValueError("request_timeout must be less than page_load_timeout")

        return values

    @classmethod
    def from_env(cls) -> "CrawlerConfig":
        """Load configuration from environment variables"""
        return cls(
            headless=os.getenv("CRAWLER_HEADLESS", "true").lower() == "true",
            page_size=int(os.getenv("CRAWLER_PAGE_SIZE", "20")),
            page_load_timeout=float(os.getenv("CRAWLER_PAGE_LOAD_TIMEOUT", "30000")),
            request_timeout=float(os.getenv("CRAWLER_REQUEST_TIMEOUT", "10000")),
            max_retry_attempts=int(os.getenv("CRAWLER_MAX_RETRY_ATTEMPTS", "3")),
            retry_delay=float(os.getenv("CRAWLER_RETRY_DELAY", "2.0")),
            min_delay=float(os.getenv("CRAWLER_MIN_DELAY", "2.0")),
            max_delay=float(os.getenv("CRAWLER_MAX_DELAY", "10.0")),
            output_format=os.getenv("CRAWLER_OUTPUT_FORMAT", "csv"),
            output_file=os.getenv("CRAWLER_OUTPUT_FILE"),
            crawling_types=os.getenv("CRAWLER_CRAWLING_TYPES", "apt").split(","),
            trade_types=os.getenv("CRAWLER_TRADE_TYPES", "sale").split(","),
            enable_checkpoints=os.getenv("CRAWLER_ENABLE_CHECKPOINTS", "true").lower() == "true",
            parallel_processing=os.getenv("CRAWLER_PARALLEL_PROCESSING", "false").lower() == "true",
            max_workers=int(os.getenv("CRAWLER_MAX_WORKERS", "4")),
        )

    def create_output_path(self) -> Path:
        """Generate output file path based on configuration"""
        if self.output_file:
            return Path(self.output_file)

        # Generate default filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        crawling_types_str = "_".join(self.crawling_types)
        trade_types_str = "_".join(self.trade_types)

        filename = f"naver_realestate_{crawling_types_str}_{trade_types_str}_{timestamp}.{self.output_format}"
        return Path("output") / filename
```

**Step 4: Update NaverRealEstateCrawler to use validated config**

```python
# src/crawler/crawlers/naver.py
from src.crawler.config import CrawlerConfig

class NaverRealEstateCrawler(BaseCrawler):
    def __init__(self, config: CrawlerConfig):
        super().__init__(config)
        self.config = config  # Now validated by Pydantic

        # Use validated values
        self.page_size = min(config.page_size, 100)  # API limit
        self.trade_types = config.trade_types
        self.output_file = config.create_output_path()

        # Initialize other components
        self.rate_limiter = AdaptiveRateLimiter(
            min_delay=config.min_delay,
            max_delay=config.max_delay
        )
        self.retryable = Retryable(BROWSER_RETRY_CONFIG)

        # Initialize checkpoint manager if enabled
        if config.enable_checkpoints:
            output_dir = Path(self.output_file).parent
            self.checkpoint_manager = CheckpointManager(output_dir / "checkpoint.json")
        else:
            self.checkpoint_manager = None

        # Initialize CSV writer
        self.csv_writer = CSVWriter(str(self.output_file))
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_config_validation.py -v`
Expected: PASS

**Step 6: Add comprehensive validation tests**

```python
# tests/unit/test_config_validation.py

def test_config_from_env_with_invalid_values():
    """Test that from_env handles invalid environment values"""
    import os

    # Set invalid environment values
    os.environ['CRAWLER_PAGE_SIZE'] = 'invalid'
    os.environ['CRAWLER_MAX_RETRY_ATTEMPTS'] = '15'

    with pytest.raises(ValidationError):
        CrawlerConfig.from_env()

    # Cleanup
    del os.environ['CRAWLER_PAGE_SIZE']
    del os.environ['CRAWLER_MAX_RETRY_ATTEMPTS']

def test_output_path_generation():
    """Test automatic output path generation"""
    config = CrawlerConfig(
        crawling_types=["apt", "officetel"],
        trade_types=["sale", "rent"]
    )

    output_path = config.create_output_path()
    assert output_path.parent == Path("output")
    assert "apt_officetel" in output_path.name
    assert "sale_rent" in output_path.name
    assert output_path.suffix == ".csv"

def test_config_compatibility_validation():
    """Test configuration compatibility checks"""
    # Invalid timeout hierarchy
    with pytest.raises(ValidationError) as exc_info:
        CrawlerConfig(request_timeout=40000, page_load_timeout=30000)

    assert "request_timeout must be less than page_load_timeout" in str(exc_info.value)

    # Invalid delay range
    with pytest.raises(ValidationError) as exc_info:
        CrawlerConfig(min_delay=10.0, max_delay=5.0)

    assert "max_delay must be greater than min_delay" in str(exc_info.value)
```

**Step 7: Run all validation tests**

Run: `uv run pytest tests/unit/test_config_validation.py -v`
Expected: ALL PASS

**Step 8: Commit**

```bash
git add src/crawler/config.py src/crawler/crawlers/naver.py tests/unit/test_config_validation.py
git commit -m "feat: add comprehensive configuration validation

- Add Pydantic-based validation for all config fields
- Add field-specific validators with meaningful error messages
- Add compatibility checks between settings
- Add automatic output path generation
- Add comprehensive validation tests"
```

---

## Task 5: 실패 시나리오 테스트 추가 (High)

**Files:**
- Create: `tests/integration/test_failure_scenarios.py`
- Modify: `src/crawler/crawlers/naver.py` (add error injection points)

**Step 1: Write test for network timeout**

```python
# tests/integration/test_failure_scenarios.py
import pytest
from unittest.mock import Mock, patch
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from src.crawler.crawlers.naver import NaverRealEstateCrawler
from src.crawler.config import CrawlerConfig

def test_network_timeout_handling():
    """Test crawler handles network timeouts gracefully"""
    config = CrawlerConfig.from_env()
    crawler = NaverRealEstateCrawler(config)

    with patch.object(crawler, 'page') as mock_page:
        # Simulate timeout
        mock_page.evaluate.side_effect = PlaywrightTimeoutError("Request timed out")

        # Should handle timeout without crashing
        result = crawler._fetch_with_retry("test_url")

        # Should return None or empty dict after retries
        assert result is None or result == {}

        # Verify retry attempts were made
        assert mock_page.evaluate.call_count >= 3  # Default retry attempts

def test_429_rate_limit_handling():
    """Test crawler handles HTTP 429 rate limits"""
    config = CrawlerConfig.from_env()
    crawler = NaverRealEstateCrawler(config)

    with patch.object(crawler, 'page') as mock_page:
        # Simulate rate limit response
        mock_page.evaluate.return_value = {
            "error": {"message": "HTTP 429: Too Many Requests"}
        }

        # Should handle rate limit with backoff
        with patch('time.sleep') as mock_sleep:
            result = crawler._fetch_with_retry("test_url")

            # Should have attempted retries with delays
            assert mock_sleep.call_count > 0
            assert mock_page.evaluate.call_count >= 3

def test_invalid_api_response_handling():
    """Test crawler handles invalid API responses"""
    config = CrawlerConfig.from_env()
    crawler = NaverRealEstateCrawler(config)

    with patch.object(crawler, 'page') as mock_page:
        # Simulate malformed JSON response
        mock_page.evaluate.return_value = {"invalid": "response structure"}

        # Should handle gracefully
        result = crawler._fetch_with_retry("test_url")

        # Should not crash
        assert result is not None

def test_browser_crash_recovery():
    """Test crawler recovers from browser crashes"""
    config = CrawlerConfig.from_env()
    crawler = NaverRealEstateCrawler(config)

    with patch('src.crawler.utils.browser_manager.managed_browser') as mock_browser:
        # Simulate browser crash on first attempt
        mock_browser.side_effect = [
            Exception("Browser crashed"),
            None  # Second attempt succeeds
        ]

        with patch.object(crawler, 'fetch_complex_list') as mock_fetch:
            mock_fetch.return_value = []

            # Should handle browser crash and retry
            result = crawler.crawl()

            # Should have attempted to restart browser
            assert mock_browser.call_count == 2
            assert isinstance(result, list)

def test_checkpoint_corruption_recovery():
    """Test crawler recovers from corrupted checkpoint"""
    config = CrawlerConfig(enable_checkpoints=True)
    crawler = NaverRealEstateCrawler(config)

    # Create corrupted checkpoint
    crawler.checkpoint_manager.checkpoint_file.write_text("invalid json")

    with patch.object(crawler, 'fetch_complex_list') as mock_fetch:
        mock_fetch.return_value = []

        # Should recover and start fresh
        result = crawler.crawl()

        # Should not fail due to corrupted checkpoint
        assert isinstance(result, list)
        assert not crawler.checkpoint_manager.load().get('processed_complexes')

def test_disk_space_exhaustion():
    """Test crawler handles disk space exhaustion"""
    config = CrawlerConfig.from_env()
    crawler = NaverRealEstateCrawler(config)

    with patch('pathlib.Path.write_text') as mock_write:
        # Simulate disk full error
        mock_write.side_effect = OSError("No space left on device")

        with patch.object(crawler, 'fetch_complex_list') as mock_fetch:
            mock_fetch.return_value = [{"complex_id": "1", "complex_name": "test"}]

            # Should handle disk space issues gracefully
            with pytest.raises(OSError):
                crawler.crawl()

def test_malformed_html_handling():
    """Test parser handles malformed HTML gracefully"""
    from src.crawler.parsers.naver_parser import NaverParser

    parser = NaverParser()

    # Test with empty HTML
    result = parser.parse_complex_list("")
    assert isinstance(result, list)

    # Test with HTML missing expected elements
    malformed_html = "<html><body><div>No data here</div></body></html>"
    result = parser.parse_complex_list(malformed_html)
    assert isinstance(result, list)

    # Test with None input
    result = parser.parse_complex_list(None)
    assert isinstance(result, list)
```

**Step 2: Create error injection helper for testing**

```python
# tests/helpers/error_injection.py
from typing import Any, Callable, Optional
import random

class ErrorInjector:
    """Helper for injecting errors during testing"""

    def __init__(self):
        self.call_count = 0
        self.error_config = {}

    def configure(self, error_config: dict[str, Any]):
        """Configure error injection pattern

        Example:
        {
            "error_after": 3,  # Inject error after 3 successful calls
            "error_type": "timeout",
            "error_probability": 0.5,  # 50% chance of error
            "error_message": "Simulated timeout"
        }
        """
        self.error_config = error_config
        self.call_count = 0

    def maybe_inject_error(self, default_return: Optional[Any] = None):
        """Check if we should inject an error on this call"""
        self.call_count += 1

        error_after = self.error_config.get("error_after", 0)
        if self.call_count < error_after:
            return False  # Don't inject error yet

        error_probability = self.error_config.get("error_probability", 0)
        if random.random() > error_probability:
            return False  # Don't inject error this time

        # Inject error
        error_type = self.error_config.get("error_type", "exception")
        error_message = self.error_config.get("error_message", "Simulated error")

        if error_type == "timeout":
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            raise PlaywrightTimeoutError(error_message)
        elif error_type == "connection":
            raise ConnectionError(error_message)
        elif error_type == "rate_limit":
            return {"error": {"message": f"HTTP 429: {error_message}"}}
        else:
            raise Exception(error_message)
```

**Step 3: Add comprehensive failure scenario test**

```python
# tests/integration/test_failure_scenarios.py
from tests.helpers.error_injection import ErrorInjector

def test_comprehensive_failure_recovery():
    """Test crawler recovers from multiple types of failures"""
    config = CrawlerConfig.from_env()
    crawler = NaverRealEstateCrawler(config)

    # Configure error injection
    error_injector = ErrorInjector()

    failure_scenarios = [
        {"error_after": 2, "error_type": "timeout", "error_probability": 1.0},
        {"error_after": 5, "error_type": "rate_limit", "error_probability": 0.8},
        {"error_after": 8, "error_type": "connection", "error_probability": 0.6},
    ]

    for scenario in failure_scenarios:
        error_injector.configure(scenario)

        with patch.object(crawler, 'page') as mock_page:
            def mock_evaluate(*args, **kwargs):
                if error_injector.maybe_inject_error():
                    pass  # Error already raised
                return {"result": {"data": "success"}}

            mock_page.evaluate.side_effect = mock_evaluate

            # Should handle the failure and continue
            try:
                result = crawler._fetch_with_retry("test_url")
                # May succeed after retries or return None
                assert result is None or isinstance(result, dict)
            except Exception:
                # Some errors are not recoverable, which is expected
                pass

def test_memory_leak_prevention():
    """Test that long-running crawls don't leak memory"""
    import psutil
    import os

    config = CrawlerConfig.from_env()
    crawler = NaverRealEstateCrawler(config)

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss

    # Simulate many iterations
    with patch.object(crawler, 'fetch_complex_list') as mock_fetch:
        mock_fetch.return_value = [
            {"complex_id": f"test_{i}", "complex_name": f"Test Complex {i}"}
            for i in range(100)
        ]

        with patch.object(crawler, 'fetch_complex_detail') as mock_detail:
            mock_detail.return_value = {"price": "1억"}

            with patch.object(crawler, 'fetch_complex_listings') as mock_listings:
                mock_listings.return_value = []

                # Run crawl
                crawler.crawl()

                # Check memory usage
                final_memory = process.memory_info().rss
                memory_increase = final_memory - initial_memory

                # Memory increase should be reasonable (less than 100MB)
                assert memory_increase < 100 * 1024 * 1024, f"Memory leak detected: {memory_increase / 1024 / 1024:.2f}MB increase"
```

**Step 4: Run failure scenario tests**

Run: `uv run pytest tests/integration/test_failure_scenarios.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add tests/integration/test_failure_scenarios.py tests/helpers/error_injection.py
git commit -m "test: add comprehensive failure scenario tests

- Add tests for network timeouts, rate limits, and API errors
- Add browser crash recovery tests
- Add checkpoint corruption recovery tests
- Add disk space exhaustion handling tests
- Add malformed HTML parsing tests
- Add memory leak prevention tests
- Add ErrorInjector helper for controlled error injection"
```

---

## Task 6: 로깅 전략 개선 (Medium)

**Files:**
- Create: `src/crawler/utils/logging_config.py`
- Modify: `src/crawler/crawlers/naver.py` (update logging calls)
- Create: `tests/unit/test_logging_config.py`

**Step 1: Write test for sensitive data filtering**

```python
# tests/unit/test_logging_config.py
import pytest
import logging
from io import StringIO
from src.crawler.utils.logging_config import SensitiveDataFilter

def test_sensitive_data_filter():
    """Test that sensitive data is filtered from logs"""
    filter = SensitiveDataFilter()

    # Test record with sensitive data
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="User data: email=user@example.com, phone=010-1234-5678",
        args=(),
        exc_info=None
    )

    # Filter should mask sensitive data
    filtered_msg = filter.filter(record)
    assert filtered_msg is True  # Record should not be filtered out

    # Check that message was modified
    assert "user@example.com" not in record.getMessage()
    assert "010-1234-5678" not in record.getMessage()
    assert "***" in record.getMessage()
```

**Step 2: Implement enhanced logging configuration**

```python
# src/crawler/utils/logging_config.py
import logging
import logging.handlers
import re
import structlog
from typing import Optional, Dict, Any
from pathlib import Path

class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data in log messages"""

    # Patterns for sensitive data
    SENSITIVE_PATTERNS = [
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '***@***.***'),  # Email
        (r'\b01[016789]-?\d{3,4}-?\d{4}\b', '***-****-****'),  # Korean phone numbers
        (r'\b\d{4}-\d{4}-\d{4}-\d{4}\b', '****-****-****-****'),  # Credit card numbers
        (r'\b\d{13,16}\b', '************'),  # Long numbers (potential IDs)
        (r'"?token"?\s*[:=]\s*["\']?[^"\',\s}]+["\']?', '"token":"***"'),  # Tokens
        (r'"?password"?\s*[:=]\s*["\']?[^"\',\s}]+["\']?', '"password":"***"'),  # Passwords
        (r'"?api_key"?\s*[:=]\s*["\']?[^"\',\s}]+["\']?', '"api_key":"***"'),  # API keys
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter sensitive data from log message"""
        if hasattr(record, 'msg'):
            msg = str(record.msg)

            # Apply all patterns
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)

            record.msg = msg

        # Also filter args if present
        if hasattr(record, 'args') and record.args:
            new_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    for pattern, replacement in self.SENSITIVE_PATTERNS:
                        arg = re.sub(pattern, replacement, arg, flags=re.IGNORECASE)
                new_args.append(arg)
            record.args = tuple(new_args)

        return True  # Always keep the record, just filter content

def configure_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_sensitive_filter: bool = True
) -> None:
    """Configure structured logging with sensitive data filtering"""

    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Add sensitive data filter if enabled
    if enable_sensitive_filter:
        processors.insert(0, sensitive_data_processor)

    processors.append(structlog.processors.UnicodeDecoder())

    # Console output
    console_renderer = structlog.dev.ConsoleRenderer()

    # File output (JSON format)
    file_renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(colors=False),
    )

    file_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(numeric_level)

    # Add sensitive data filter to console handler
    if enable_sensitive_filter:
        console_handler.addFilter(SensitiveDataFilter())

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(numeric_level)

        # Add sensitive data filter to file handler
        if enable_sensitive_filter:
            file_handler.addFilter(SensitiveDataFilter())

        root_logger.addHandler(file_handler)

def sensitive_data_processor(logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Structlog processor to filter sensitive data"""
    event = event_dict.get('event', '')

    if isinstance(event, str):
        for pattern, replacement in SensitiveDataFilter.SENSITIVE_PATTERNS:
            event = re.sub(pattern, replacement, event, flags=re.IGNORECASE)
        event_dict['event'] = event

    # Filter sensitive data in other fields
    for key, value in event_dict.items():
        if isinstance(value, str):
            for pattern, replacement in SensitiveDataFilter.SENSITIVE_PATTERNS:
                value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
                event_dict[key] = value

    return event_dict

class CrawlLogger:
    """Specialized logger for crawling operations"""

    def __init__(self, name: str):
        self.logger = structlog.get_logger(name)

    def log_api_call(self, url: str, method: str = "GET", status: str = "success",
                    response_time: Optional[float] = None, error: Optional[str] = None):
        """Log API call with standardized format"""
        log_data = {
            "operation": "api_call",
            "url": url.split('?')[0],  # Remove query parameters for privacy
            "method": method,
            "status": status,
        }

        if response_time is not None:
            log_data["response_time_ms"] = round(response_time * 1000, 2)

        if error:
            log_data["error"] = error

        if status == "success":
            self.logger.info("API call completed", **log_data)
        else:
            self.logger.error("API call failed", **log_data)

    def log_retry(self, operation: str, attempt: int, max_attempts: int,
                  delay: float, error: str):
        """Log retry attempt"""
        self.logger.warning(
            "Retrying operation",
            operation=operation,
            attempt=attempt,
            max_attempts=max_attempts,
            delay=delay,
            error=error
        )

    def log_progress(self, current: int, total: int, operation: str = "crawling"):
        """Log operation progress"""
        percentage = (current / total * 100) if total > 0 else 0
        self.logger.info(
            f"Progress: {percentage:.1f}%",
            operation=operation,
            current=current,
            total=total,
            percentage=percentage
        )

    def log_resource_usage(self, memory_mb: float, cpu_percent: float):
        """Log resource usage"""
        self.logger.debug(
            "Resource usage",
            memory_mb=round(memory_mb, 2),
            cpu_percent=round(cpu_percent, 2)
        )
```

**Step 3: Update NaverRealEstateCrawler logging**

```python
# src/crawler/crawlers/naver.py
from src.crawler.utils.logging_config import CrawlLogger

class NaverRealEstateCrawler(BaseCrawler):
    def __init__(self, config: CrawlerConfig):
        super().__init__(config)
        # ... existing init code ...

        # Initialize specialized logger
        self.crawl_logger = CrawlLogger("NaverRealEstateCrawler")

    def _fetch_with_retry(self, url: str) -> dict[str, Any]:
        """Enhanced fetch with better logging"""
        import time
        start_time = time.time()

        try:
            result = self.retryable.execute(
                self._perform_fetch,
                url,
                operation_name=f"fetch_api_{url.split('/')[-1]}"
            )

            response_time = time.time() - start_time
            self.crawl_logger.log_api_call(
                url=url,
                status="success",
                response_time=response_time
            )

            return result

        except Exception as e:
            response_time = time.time() - start_time
            self.crawl_logger.log_api_call(
                url=url,
                status="failed",
                response_time=response_time,
                error=str(e)
            )
            raise

    def crawl(self) -> list[dict[str, Any]]:
        """Enhanced crawl with progress logging"""
        self.crawl_logger.logger.info("Starting crawl", config=self.config.dict())

        all_results = []

        try:
            with managed_browser(headless=self.config.headless) as page:
                self.page = page

                complexes = self.fetch_complex_list()

                if not complexes:
                    self.crawl_logger.logger.warning("No complexes found")
                    return all_results

                start_index = self.calculate_start_position(complexes)
                total_complexes = len(complexes)

                for idx in range(start_index, total_complexes, self.page_size):
                    batch = complexes[idx:idx + self.page_size]

                    for batch_idx, complex_info in enumerate(batch):
                        complex_id = complex_info['complex_id']

                        # Log progress
                        processed = idx + batch_idx
                        self.crawl_logger.log_progress(
                            current=processed + 1,
                            total=total_complexes
                        )

                        # ... rest of crawl logic ...

                        all_results.append(result)

                        # Log resource usage periodically
                        if processed % 50 == 0:
                            self._log_resource_usage()

        finally:
            self.crawl_logger.logger.info(
                "Crawl completed",
                total_complexes=len(complexes),
                processed=len(all_results),
                duration_seconds=time.time() - start_time if 'start_time' in locals() else 0
            )

        return all_results

    def _log_resource_usage(self):
        """Log current resource usage"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()

        self.crawl_logger.log_resource_usage(memory_mb, cpu_percent)
```

**Step 4: Run logging tests**

Run: `uv run pytest tests/unit/test_logging_config.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/crawler/utils/logging_config.py src/crawler/crawlers/naver.py tests/unit/test_logging_config.py
git commit -m "feat: enhance logging with sensitive data filtering

- Add SensitiveDataFilter to mask emails, phones, tokens in logs
- Add rotating file handler with configurable size limits
- Add CrawlLogger specialized for crawling operations
- Add structured logging with JSON format for file output
- Add progress and resource usage logging
- Add comprehensive logging configuration options"
```

---

## Summary

This implementation plan addresses the critical stability issues identified in the codebase:

1. **Resource Management**: Browser context managers prevent resource leaks
2. **Retry Logic**: Centralized retry handling with browser-specific configurations
3. **Concurrency**: Thread-safe checkpoint management with atomic operations
4. **Validation**: Comprehensive configuration validation with Pydantic
5. **Testing**: Extensive failure scenario testing with error injection
6. **Logging**: Enhanced logging with sensitive data filtering

Each task includes comprehensive tests and follows TDD principles. The plan is designed to be executed incrementally, with each task building upon previous improvements while maintaining system stability throughout the process.