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
        """
        browser: Browser | None = None
        context: BrowserContext | None = None
        page: Page | None = None

        try:
            self.logger.info("starting_browser")

            # Use sync_playwright context manager for proper resource management
            with sync_playwright() as playwright:
                # Launch browser
                browser = playwright.chromium.launch(
                    headless=self.config.headless,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                    ],
                )

                # Create context
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1920, "height": 1080},
                )

                # Create page
                page = context.new_page()

                self.logger.info("browser_started_successfully")
                yield page

        except Exception as e:
            self.logger.error("browser_operation_failed", error=str(e))
            raise
        finally:
            # The sync_playwright context manager handles cleanup automatically
            # We only log cleanup completion here
            self.logger.info("browser_cleanup_complete")
