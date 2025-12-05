"""Enhanced Naver Real Estate crawler with comprehensive error handling.

This module integrates all the error handling components into the crawler
to make it more resilient for long-running crawling operations.
"""

import json
import time
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import structlog
from playwright.sync_api import sync_playwright

from crawler.config import CrawlerConfig
from crawler.rate_limiter import AdaptiveRateLimiter
from crawler.utils.checkpoint import CheckpointManager
from crawler.coordinator import CrawlCoordinator
from crawler.utils.circuit_breaker import CircuitBreaker, NaverAPIBreaker
from crawler.utils.retry import retry_rate_limit, retry_transient_errors
from crawler.utils.failure_tracker import FailureTracker, FailureType, FailureSeverity
from crawler.utils.timeout import api_timeout, TimeoutError, MultiTimeout
from crawler.utils.health_check import HealthChecker, HealthStatus
from crawler.utils.degradation import GracefulDegradationManager, with_fallback
from crawler.utils.error_logger import ErrorLogger, ErrorCategory, ErrorSeverity


class EnhancedNaverRealEstateCrawler:
    """
    Enhanced Naver Real Estate crawler with comprehensive error handling.

    Features:
    - Circuit breaker pattern for API failures
    - Retry with exponential backoff
    - Timeout protection for all operations
    - Health monitoring
    - Graceful degradation
    - Detailed error tracking and logging
    """

    def __init__(self, config: CrawlerConfig) -> None:
        """Initialize the enhanced crawler."""
        self.config = config
        self.logger = structlog.get_logger().bind(component="enhanced_naver_crawler")

        # Initialize error handling components
        self.circuit_breaker = NaverAPIBreaker()
        self.failure_tracker = FailureTracker(
            max_records=5000,
            persistence_file=Path(config.output_dir) / "failures.json",
        )
        self.health_checker = HealthChecker()
        self.degradation_manager = GracefulDegradationManager()
        self.error_logger = ErrorLogger(
            component="naver_crawler",
            log_file=Path(config.output_dir) / "errors.jsonl",
        )

        # Initialize core components
        self.checkpoint_manager = CheckpointManager("output/checkpoint.json")
        self.districts_data = self._load_districts_data()
        self.page: Any = None
        self.rate_limiter = AdaptiveRateLimiter()

        # Register features for degradation
        self._register_degradation_features()

        # Register health checks
        self._register_health_checks()

        self.logger.info("enhanced_crawler_initialized")

    def _register_degradation_features(self) -> None:
        """Register features that can be degraded."""
        # Complex detail fetching
        self.degradation_manager.register_feature(
            feature="complex_detail",
            fallback=self._fallback_complex_detail,
            max_failures=5,
            recovery_timeout=300.0,
            required=False,  # Can continue without complex details
        )

        # Transaction history fetching
        self.degradation_manager.register_feature(
            feature="transaction_history",
            fallback=self._fallback_transaction_history,
            max_failures=10,
            recovery_timeout=600.0,
            required=False,  # Can continue without transaction history
        )

        # Image fetching (if implemented)
        self.degradation_manager.register_feature(
            feature="image_fetch",
            fallback=None,
            max_failures=3,
            recovery_timeout=180.0,
            required=False,
        )

    def _register_health_checks(self) -> None:
        """Register custom health checks."""
        # Check if we have active circuit breakers
        def check_circuit_breakers() -> Any:
            if self.circuit_breaker.state.value == "open":
                return self.health_checker.CheckResult(
                    name="circuit_breaker",
                    status=HealthStatus.DEGRADED,
                    message="Circuit breaker is open",
                    details={"state": self.circuit_breaker.state.value},
                )
            return self.health_checker.CheckResult(
                name="circuit_breaker",
                status=HealthStatus.HEALTHY,
                message="Circuit breaker is closed",
            )

        self.health_checker.register_check("circuit_breaker", check_circuit_breakers)

    def _load_districts_data(self) -> dict[str, Any]:
        """Load Seoul districts data."""
        try:
            data_path = Path(__file__).parent.parent / "data" / "seoul_districts.json"
            with open(data_path, encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
                return data
        except Exception as e:
            correlation_id = self.error_logger.log_error(
                error=e,
                operation="load_districts_data",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
            )
            raise RuntimeError(f"Failed to load districts data (CID: {correlation_id})") from e

    @with_fallback("complex_detail")
    @retry_rate_limit(max_attempts=5, base_delay=5.0, max_delay=120.0)
    @api_timeout(timeout_seconds=60.0)
    def fetch_complex_detail(self, complex_id: str) -> dict[str, Any]:
        """
        Fetch complex details with enhanced error handling.

        Args:
            complex_id: The complex ID to fetch

        Returns:
            Complex detail data
        """
        correlation_id = self.error_logger.logger.new(correlation_id=str(uuid4()))

        self.logger.info(
            "fetching_complex_detail",
            complex_id=complex_id,
            correlation_id=correlation_id,
        )

        try:
            # Use circuit breaker
            result = self.circuit_breaker.call(self._fetch_complex_detail_impl, complex_id)

            self.degradation_manager.record_feature_success("complex_detail")
            return result

        except Exception as e:
            # Record failure
            correlation_id = self.error_logger.log_error(
                error=e,
                operation="fetch_complex_detail",
                item_id=complex_id,
                metadata={"correlation_id": correlation_id},
            )

            # Track failure
            self.failure_tracker.record_failure(
                item_id=complex_id,
                item_type="complex",
                operation="fetch_complex_detail",
                error=e,
                context={"url": f"https://fin.land.naver.com/complexes/{complex_id}"},
            )

            # Notify degradation manager
            self.degradation_manager.record_feature_failure("complex_detail", e)

            raise

    def _fetch_complex_detail_impl(self, complex_id: str) -> dict[str, Any]:
        """Implementation of complex detail fetching."""
        # Existing implementation logic here
        # This is a placeholder - actual implementation would be from the original crawler
        pass

    @with_fallback("transaction_history")
    @retry_rate_limit(max_attempts=10, base_delay=5.0, max_delay=120.0)
    @api_timeout(timeout_seconds=45.0)
    def fetch_transaction_history(
        self,
        complex_id: str,
        pyeong_type_number: int,
        trade_type: str,
        complex_name: str = "",
        pyeong_name: str = "",
    ) -> list[dict[str, Any]]:
        """
        Fetch transaction history with enhanced error handling.

        Args:
            complex_id: Complex ID
            pyeong_type_number: Pyeong type number
            trade_type: Trade type (A1, B1, B2)
            complex_name: Complex name (optional)
            pyeong_name: Pyeong name (optional)

        Returns:
            List of transaction records
        """
        self.logger.info(
            "fetching_transaction_history",
            complex_id=complex_id,
            pyeong_type_number=pyeong_type_number,
            trade_type=trade_type,
        )

        try:
            # Use circuit breaker
            result = self.circuit_breaker.call(
                self._fetch_transaction_history_impl,
                complex_id,
                pyeong_type_number,
                trade_type,
                complex_name,
                pyeong_name,
            )

            self.degradation_manager.record_feature_success("transaction_history")
            return result

        except Exception as e:
            # Record failure
            self.error_logger.log_error(
                error=e,
                operation="fetch_transaction_history",
                item_id=f"{complex_id}-{pyeong_type_number}-{trade_type}",
                metadata={
                    "complex_id": complex_id,
                    "pyeong_type_number": pyeong_type_number,
                    "trade_type": trade_type,
                },
            )

            # Track failure
            self.failure_tracker.record_failure(
                item_id=f"{complex_id}-{pyeong_type_number}-{trade_type}",
                item_type="transaction",
                operation="fetch_transaction_history",
                error=e,
                context={
                    "complex_id": complex_id,
                    "pyeong_type_number": pyeong_type_number,
                    "trade_type": trade_type,
                },
            )

            # Notify degradation manager
            self.degradation_manager.record_feature_failure("transaction_history", e)

            raise

    def _fetch_transaction_history_impl(
        self,
        complex_id: str,
        pyeong_type_number: int,
        trade_type: str,
        complex_name: str = "",
        pyeong_name: str = "",
    ) -> list[dict[str, Any]]:
        """Implementation of transaction history fetching."""
        # Existing implementation logic here
        # This is a placeholder - actual implementation would be from the original crawler
        pass

    def _fallback_complex_detail(self) -> dict[str, Any]:
        """Fallback implementation for complex detail."""
        self.logger.warning("using_complex_detail_fallback")
        return {
            "error": "Complex detail service unavailable",
            "fallback_used": True,
        }

    def _fallback_transaction_history(self) -> list[dict[str, Any]]:
        """Fallback implementation for transaction history."""
        self.logger.warning("using_transaction_history_fallback")
        return []

    def crawl_with_health_check(self) -> dict[str, Any]:
        """
        Perform crawling with continuous health monitoring.

        Returns:
            Crawl results with health status
        """
        # Initial health check
        health_report = self.health_checker.check_all()
        if health_report["status"] != HealthStatus.HEALTHY.value:
            self.logger.warning(
                "starting_with_degraded_health",
                status=health_report["status"],
            )

        try:
            # Perform crawl with timeout protection
            with MultiTimeout(api=30, db=60):
                results = self._perform_crawl()

        except TimeoutError as e:
            self.error_logger.log_error(
                error=e,
                operation="crawl_with_health_check",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
            )
            results = {
                "error": "Crawl timed out",
                "timeout": True,
                "partial_results": getattr(self, "_partial_results", {}),
            }

        # Final health check
        final_health = self.health_checker.check_all()

        # Add health and degradation status to results
        results["health_status"] = final_health
        results["degradation_status"] = self.degradation_manager.get_system_status()
        results["failure_summary"] = self.failure_tracker.generate_report()

        return results

    def _perform_crawl(self) -> dict[str, Any]:
        """Perform the actual crawling operation."""
        # This would contain the main crawling logic from the original crawler
        # with error handling integrated throughout
        pass

    def get_system_status(self) -> dict[str, Any]:
        """Get comprehensive system status."""
        return {
            "health": self.health_checker.check_all(),
            "degradation": self.degradation_manager.get_system_status(),
            "circuit_breaker": self.circuit_breaker.get_state(),
            "failures": self.failure_tracker.generate_report(),
            "rate_limiter": {
                "current_delay": self.rate_limiter.current_delay,
                "success_count": self.rate_limiter.success_count,
                "error_count": self.rate_limiter.error_count,
            },
        }