"""Browser resource management utilities."""

import structlog
from contextlib import contextmanager
from typing import Generator

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

from crawler.config import CrawlerConfig


logger = structlog.get_logger()


class BrowserManager:
    """Manages browser resources with proper cleanup."""

    def __init__(self, config: CrawlerConfig) -> None:
        """Initialize browser manager with configuration."""
        self.config = config
        self.logger = structlog.get_logger()

    @contextmanager
    def managed_browser(self) -> Generator[Page, None, None]:
        """Context manager for browser resource management.

        Yields:
            Page: A Playwright page object

        Ensures:
            - Browser, context, and page are properly closed
            - Resources are cleaned up even if an exception occurs
            - Memory is properly released after use
        """
        browser: Browser | None = None
        context: BrowserContext | None = None
        page: Page | None = None
        playwright_instance = None

        try:
            self.logger.info("starting_browser")

            # Use sync_playwright context manager for proper resource management
            playwright_instance = sync_playwright().start()

            # Launch browser with memory optimization flags
            browser = playwright_instance.chromium.launch(
                headless=self.config.headless,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    # Memory optimization flags
                    "--memory-pressure-off",
                    "--max_old_space_size=4096",
                    "--disable-background-timer-throttling",
                    "--disable-renderer-backgrounding",
                    "--disable-backgrounding-occluded-windows",
                    # Additional cleanup flags
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-default-apps",
                ],
            )

            # Create context with memory optimization
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
                # Memory optimization settings
                java_script_enabled=True,
                ignore_https_errors=True,
                # Reduce memory usage
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                },
            )

            # Create page
            page = context.new_page()

            # Set up automatic garbage collection
            page.on("response", lambda response: self._cleanup_page_resources(page))

            self.logger.info("browser_started_successfully")
            yield page

        except Exception as e:
            self.logger.error("browser_operation_failed", error=str(e))
            raise
        finally:
            # Explicit cleanup in reverse order
            try:
                if page:
                    # Clear cookies, localStorage, sessionStorage
                    page.evaluate("""
                        () => {
                            // Clear storage
                            localStorage.clear();
                            sessionStorage.clear();

                            // Force garbage collection if available
                            if (window.gc) {
                                window.gc();
                            }
                        }
                    """)
                    page.close()
                    self.logger.debug("page_closed")
            except Exception as e:
                self.logger.warning("page_close_error", error=str(e))

            try:
                if context:
                    context.close()
                    self.logger.debug("context_closed")
            except Exception as e:
                self.logger.warning("context_close_error", error=str(e))

            try:
                if browser:
                    browser.close()
                    self.logger.debug("browser_closed")
            except Exception as e:
                self.logger.warning("browser_close_error", error=str(e))

            try:
                if playwright_instance:
                    playwright_instance.stop()
                    self.logger.debug("playwright_stopped")
            except Exception as e:
                self.logger.warning("playwright_stop_error", error=str(e))

            self.logger.info("browser_cleanup_complete")

    def _cleanup_page_resources(self, page: Page) -> None:
        """Clean up page resources to reduce memory usage."""
        try:
            # Force garbage collection periodically
            page.evaluate("""
                () => {
                    // Run garbage collection if available
                    if (window.gc) {
                        window.gc();
                    }

                    // Clear any console logs to reduce memory
                    console.clear();
                }
            """)
        except Exception as e:
            self.logger.debug("resource_cleanup_error", error=str(e))
