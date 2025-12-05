"""Health check utilities for monitoring system and service health.

This module provides health check functionality to monitor
the status of various system components and external services.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import structlog

from crawler.utils.timeout import APITimeout, TimeoutError
from crawler.utils.circuit_breaker import CircuitState

logger = structlog.get_logger()


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CheckResult:
    """Result of a health check."""

    def __init__(
        self,
        name: str,
        status: HealthStatus,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        response_time: Optional[float] = None,
        timestamp: Optional[float] = None,
    ) -> None:
        """
        Initialize check result.

        Args:
            name: Name of the check
            status: Health status
            message: Descriptive message
            details: Additional details about the check
            response_time: Time taken to perform check (seconds)
            timestamp: When check was performed
        """
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.response_time = response_time
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "response_time": self.response_time,
            "timestamp": self.timestamp,
        }


class HealthChecker:
    """
    Performs health checks on various system components.

    Features:
    - Multiple built-in checks (disk space, memory, API endpoints)
    - Custom check registration
    - Aggregated health status
    - Response time tracking
    - Historical health data
    """

    def __init__(self) -> None:
        """Initialize health checker."""
        self.checks: Dict[str, Callable[[], CheckResult]] = {}
        self.results: List[CheckResult] = []
        self.history: List[Dict[str, Any]] = []
        self.max_history = 100  # Keep last 100 health snapshots

        self.logger = structlog.get_logger().bind(health_checker=id(self))

        # Register default checks
        self._register_default_checks()

    def register_check(
        self,
        name: str,
        check_func: Callable[[], CheckResult],
        overwrite: bool = False,
    ) -> None:
        """
        Register a custom health check.

        Args:
            name: Name of the check
            check_func: Function that performs the check
            overwrite: Whether to overwrite existing check
        """
        if name in self.checks and not overwrite:
            raise ValueError(f"Check '{name}' already exists. Use overwrite=True to replace.")

        self.checks[name] = check_func
        self.logger.info("health_check_registered", name=name)

    def unregister_check(self, name: str) -> None:
        """Unregister a health check."""
        if name in self.checks:
            del self.checks[name]
            self.logger.info("health_check_unregistered", name=name)

    def check(self, name: str) -> CheckResult:
        """
        Perform a specific health check.

        Args:
            name: Name of the check to perform

        Returns:
            Check result
        """
        if name not in self.checks:
            return CheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Check '{name}' not found",
            )

        start_time = time.time()
        try:
            result = self.checks[name]()
            if result.response_time is None:
                result.response_time = time.time() - start_time
            return result
        except Exception as e:
            self.logger.error(
                "health_check_failed",
                name=name,
                error=str(e),
            )
            return CheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                response_time=time.time() - start_time,
            )

    def check_all(self) -> Dict[str, Any]:
        """
        Perform all registered health checks.

        Returns:
            Aggregated health report
        """
        self.results = []
        start_time = time.time()

        # Run all checks
        for name in self.checks:
            result = self.check(name)
            self.results.append(result)

        # Calculate overall status
        overall_status = self._calculate_overall_status(self.results)

        # Create report
        report = {
            "status": overall_status.value,
            "timestamp": time.time(),
            "response_time": time.time() - start_time,
            "checks": [r.to_dict() for r in self.results],
            "summary": self._create_summary(self.results),
        }

        # Store in history
        self.history.append(report)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        self.logger.info(
            "health_check_completed",
            status=overall_status.value,
            checks_performed=len(self.results),
            response_time=report["response_time"],
        )

        return report

    def is_healthy(self) -> bool:
        """
        Check if system is healthy.

        Returns:
            True if all critical checks are healthy
        """
        report = self.check_all()
        return report["status"] == HealthStatus.HEALTHY.value

    def _calculate_overall_status(self, results: List[CheckResult]) -> HealthStatus:
        """Calculate overall health status from check results."""
        if not results:
            return HealthStatus.UNKNOWN

        # Check for any unhealthy results
        unhealthy = [r for r in results if r.status == HealthStatus.UNHEALTHY]
        if unhealthy:
            return HealthStatus.UNHEALTHY

        # Check for any degraded results
        degraded = [r for r in results if r.status == HealthStatus.DEGRADED]
        if degraded:
            return HealthStatus.DEGRADED

        # All must be healthy
        if all(r.status == HealthStatus.HEALTHY for r in results):
            return HealthStatus.HEALTHY

        return HealthStatus.UNKNOWN

    def _create_summary(self, results: List[CheckResult]) -> Dict[str, Any]:
        """Create summary of check results."""
        status_counts = {}
        for status in HealthStatus:
            status_counts[status.value] = sum(
                1 for r in results if r.status == status
            )

        avg_response_time = (
            sum(r.response_time or 0 for r in results) / len(results)
            if results else 0
        )

        return {
            "total_checks": len(results),
            "status_counts": status_counts,
            "average_response_time": avg_response_time,
            "slowest_check": max(results, key=lambda r: r.response_time or 0).name if results else None,
            "fastest_check": min(results, key=lambda r: r.response_time or float('inf')).name if results else None,
        }

    def _register_default_checks(self) -> None:
        """Register built-in health checks."""
        self.register_check("disk_space", self._check_disk_space)
        self.register_check("memory_usage", self._check_memory_usage)
        self.register_check("circuit_breakers", self._check_circuit_breakers)

    def _check_disk_space(self) -> CheckResult:
        """Check available disk space."""
        import shutil

        try:
            total, used, free = shutil.disk_usage(".")
            free_percent = (free / total) * 100

            if free_percent < 5:
                status = HealthStatus.UNHEALTHY
                message = f"Very low disk space: {free_percent:.1f}% free"
            elif free_percent < 10:
                status = HealthStatus.DEGRADED
                message = f"Low disk space: {free_percent:.1f}% free"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk space OK: {free_percent:.1f}% free"

            return CheckResult(
                name="disk_space",
                status=status,
                message=message,
                details={
                    "total_gb": total // (1024**3),
                    "used_gb": used // (1024**3),
                    "free_gb": free // (1024**3),
                    "free_percent": round(free_percent, 1),
                },
            )
        except Exception as e:
            return CheckResult(
                name="disk_space",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check disk space: {str(e)}",
            )

    def _check_memory_usage(self) -> CheckResult:
        """Check memory usage."""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()

            if memory_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"Very high memory usage: {memory_percent:.1f}%"
            elif memory_percent > 70:
                status = HealthStatus.DEGRADED
                message = f"High memory usage: {memory_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage OK: {memory_percent:.1f}%"

            return CheckResult(
                name="memory_usage",
                status=status,
                message=message,
                details={
                    "rss_mb": memory_info.rss // (1024**2),
                    "vms_mb": memory_info.vms // (1024**2),
                    "percent": round(memory_percent, 1),
                },
            )
        except Exception:
            # psutil not available or other error
            return CheckResult(
                name="memory_usage",
                status=HealthStatus.UNKNOWN,
                message="Memory check not available (psutil required)",
            )

    def _check_circuit_breakers(self) -> CheckResult:
        """Check status of all registered circuit breakers."""
        # This would need access to actual circuit breakers
        # For now, return a placeholder
        return CheckResult(
            name="circuit_breakers",
            status=HealthStatus.HEALTHY,
            message="No circuit breakers registered",
            details={"count": 0},
        )


class APIHealthChecker:
    """Specialized health checker for API endpoints."""

    def __init__(self, base_url: str) -> None:
        """
        Initialize API health checker.

        Args:
            base_url: Base URL of the API
        """
        self.base_url = base_url.rstrip("/")
        self.logger = structlog.get_logger().bind(api_health_checker=id(self))

    def check_endpoint(
        self,
        path: str,
        method: str = "GET",
        expected_status: int = 200,
        timeout: float = 10.0,
    ) -> CheckResult:
        """
        Check health of a specific API endpoint.

        Args:
            path: Endpoint path (e.g., "/health")
            method: HTTP method
            expected_status: Expected HTTP status code
            timeout: Request timeout

        Returns:
            Check result
        """
        import requests

        url = f"{self.base_url}{path}"
        start_time = time.time()

        try:
            with APITimeout(timeout):
                response = requests.request(method, url)
                response_time = time.time() - start_time

                if response.status_code == expected_status:
                    return CheckResult(
                        name=f"api_{method}_{path.replace('/', '_')}",
                        status=HealthStatus.HEALTHY,
                        message=f"Endpoint healthy (HTTP {response.status_code})",
                        details={
                            "url": url,
                            "status_code": response.status_code,
                            "response_time": response_time,
                        },
                        response_time=response_time,
                    )
                else:
                    return CheckResult(
                        name=f"api_{method}_{path.replace('/', '_')}",
                        status=HealthStatus.UNHEALTHY,
                        message=f"Unexpected status: HTTP {response.status_code} (expected {expected_status})",
                        details={
                            "url": url,
                            "status_code": response.status_code,
                            "expected_status": expected_status,
                            "response_time": response_time,
                        },
                        response_time=response_time,
                    )

        except TimeoutError:
            return CheckResult(
                name=f"api_{method}_{path.replace('/', '_')}",
                status=HealthStatus.UNHEALTHY,
                message=f"Endpoint timeout after {timeout}s",
                details={
                    "url": url,
                    "timeout": timeout,
                },
                response_time=timeout,
            )
        except Exception as e:
            return CheckResult(
                name=f"api_{method}_{path.replace('/', '_')}",
                status=HealthStatus.UNHEALTHY,
                message=f"Endpoint check failed: {str(e)}",
                details={
                    "url": url,
                    "error": str(e),
                },
                response_time=time.time() - start_time,
            )