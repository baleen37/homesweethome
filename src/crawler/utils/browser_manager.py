"""Browser resource management utilities."""

import structlog
from contextlib import contextmanager
from typing import Any, Generator

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
        """
        browser: Browser | None = None
        context: BrowserContext | None = None
        page: Page | None = None

        try:
            self.logger.info("starting_browser")
            playwright = sync_playwright().start()

            # Launch browser
            browser = playwright.chromium.launch(
                headless=self.config.headless,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )

            # Create context
            context = browser.new_context(
                user_agent=(
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                viewport={'width': 1920, 'height': 1080}
            )

            # Create page
            page = context.new_page()

            self.logger.info("browser_started_successfully")
            yield page

        except Exception as e:
            self.logger.error("browser_operation_failed", error=str(e))
            raise
        finally:
            # Clean up resources in reverse order
            if page:
                try:
                    page.close()
                    self.logger.debug("page_closed")
                except Exception as e:
                    self.logger.warning("failed_to_close_page", error=str(e))

            if context:
                try:
                    context.close()
                    self.logger.debug("context_closed")
                except Exception as e:
                    self.logger.warning("failed_to_close_context", error=str(e))

            if browser:
                try:
                    browser.close()
                    self.logger.debug("browser_closed")
                except Exception as e:
                    self.logger.warning("failed_to_close_browser", error=str(e))

            # Note: playwright instance automatically managed by context manager
            self.logger.info("browser_cleanup_complete")