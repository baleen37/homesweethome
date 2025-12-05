"""Graceful degradation utilities for handling component failures.

This module provides mechanisms to degrade functionality gracefully
when components fail, allowing the system to continue operating
with reduced capabilities.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar

import structlog

logger = structlog.get_logger()

T = TypeVar("T")


class DegradationLevel(Enum):
    """Levels of system degradation."""
    NONE = "none"           # Full functionality
    MINIMAL = "minimal"     # Slightly reduced
    MODERATE = "moderate"   # Significantly reduced
    SEVERE = "severe"       # Major limitations
    CRITICAL = "critical"   # Emergency mode only


@dataclass
class DegradationPolicy:
    """Policy for degrading a specific feature."""
    feature: str
    enabled: bool = True
    fallback: Optional[Callable[[], Any]] = None
    max_failures: int = 3
    recovery_timeout: float = 300.0  # 5 minutes
    required: bool = False  # If True, system cannot operate without this
    dependencies: List[str] = field(default_factory=list)  # Other features this depends on


class FeatureMonitor:
    """Monitors feature health and triggers degradation."""

    def __init__(self, feature: str, policy: DegradationPolicy) -> None:
        self.feature = feature
        self.policy = policy
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.degraded = False
        self.degraded_at: Optional[float] = None

        self.logger = structlog.get_logger().bind(
            feature_monitor=id(self),
            feature=feature,
        )

    def record_failure(self, error: Exception) -> None:
        """Record a failure for this feature."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        self.logger.warning(
            "feature_failure",
            failure_count=self.failure_count,
            max_failures=self.policy.max_failures,
            error=str(error),
        )

        # Check if we should degrade
        if self.failure_count >= self.policy.max_failures:
            self._degrade()

    def record_success(self) -> None:
        """Record a successful operation."""
        if self.degraded:
            # Check if we should recover
            if self.last_failure_time and (
                time.time() - self.last_failure_time >= self.policy.recovery_timeout
            ):
                self._recover()
        else:
            # Reset failure count on success
            if self.failure_count > 0:
                self.failure_count = 0
                self.logger.debug("feature_failure_count_reset")

    def _degrade(self) -> None:
        """Degrade the feature."""
        if not self.degraded:
            self.degraded = True
            self.degraded_at = time.time()
            self.logger.warning(
                "feature_degraded",
                failure_count=self.failure_count,
                has_fallback=self.policy.fallback is not None,
            )

    def _recover(self) -> None:
        """Recover from degraded state."""
        if self.degraded:
            self.degraded = False
            self.failure_count = 0
            self.last_failure_time = None
            self.logger.info("feature_recovered")

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the feature."""
        return {
            "feature": self.feature,
            "degraded": self.degraded,
            "failure_count": self.failure_count,
            "max_failures": self.policy.max_failures,
            "last_failure_time": self.last_failure_time,
            "degraded_at": self.degraded_at,
            "can_recover": (
                self.degraded and
                self.last_failure_time is not None and
                time.time() - self.last_failure_time >= self.policy.recovery_timeout
            ),
        }


class GracefulDegradationManager:
    """
    Manages graceful degradation of system features.

    This component monitors feature health and automatically degrades
    functionality when failures occur, allowing the system to continue
    operating with reduced capabilities.
    """

    def __init__(self) -> None:
        """Initialize degradation manager."""
        self.policies: Dict[str, DegradationPolicy] = {}
        self.monitors: Dict[str, FeatureMonitor] = {}
        self.current_level = DegradationLevel.NONE
        self.degraded_features: set[str] = set()

        self.logger = structlog.get_logger().bind(
            degradation_manager=id(self),
        )

    def register_feature(
        self,
        feature: str,
        fallback: Optional[Callable[[], Any]] = None,
        max_failures: int = 3,
        recovery_timeout: float = 300.0,
        required: bool = False,
        dependencies: Optional[List[str]] = None,
    ) -> None:
        """
        Register a feature for degradation monitoring.

        Args:
            feature: Feature name
            fallback: Fallback function to call when degraded
            max_failures: Number of failures before degrading
            recovery_timeout: Time to wait before attempting recovery
            required: Whether this feature is required for operation
            dependencies: Other features this feature depends on
        """
        policy = DegradationPolicy(
            feature=feature,
            fallback=fallback,
            max_failures=max_failures,
            recovery_timeout=recovery_timeout,
            required=required,
            dependencies=dependencies or [],
        )

        self.policies[feature] = policy
        self.monitors[feature] = FeatureMonitor(feature, policy)

        self.logger.info(
            "feature_registered",
            feature=feature,
            required=required,
            has_fallback=fallback is not None,
            dependencies=dependencies,
        )

    def execute_with_fallback(
        self,
        feature: str,
        func: Callable[[], T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        Execute a function with fallback if feature is degraded.

        Args:
            feature: Name of the feature
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Result of func or fallback

        Raises:
            RuntimeError: If feature is required and no fallback available
        """
        monitor = self.monitors.get(feature)
        if not monitor:
            self.logger.warning("feature_not_registered", feature=feature)
            return func(*args, **kwargs)

        # Check if feature is degraded
        if monitor.degraded:
            if monitor.policy.fallback:
                self.logger.info(
                    "using_fallback",
                    feature=feature,
                )
                try:
                    return monitor.policy.fallback()
                except Exception as e:
                    self.logger.error(
                        "fallback_failed",
                        feature=feature,
                        error=str(e),
                    )
                    if monitor.policy.required:
                        raise RuntimeError(f"Required feature '{feature}' failed and fallback failed")
                    # Return None for non-required features
                    return None  # type: ignore
            else:
                if monitor.policy.required:
                    raise RuntimeError(f"Required feature '{feature}' is degraded and no fallback available")
                self.logger.warning(
                    "feature_degraded_no_fallback",
                    feature=feature,
                )
                return None  # type: ignore

        # Execute the function
        try:
            result = func(*args, **kwargs)
            monitor.record_success()
            return result
        except Exception as e:
            monitor.record_failure(e)
            raise

    def record_feature_failure(self, feature: str, error: Exception) -> None:
        """Manually record a feature failure."""
        monitor = self.monitors.get(feature)
        if monitor:
            monitor.record_failure(error)
            self._update_degradation_level()

    def record_feature_success(self, feature: str) -> None:
        """Manually record a feature success."""
        monitor = self.monitors.get(feature)
        if monitor:
            monitor.record_success()
            self._update_degradation_level()

    def can_proceed(self, feature: str) -> bool:
        """
        Check if we can proceed with a feature.

        Args:
            feature: Feature name

        Returns:
            True if feature is available or has fallback
        """
        monitor = self.monitors.get(feature)
        if not monitor:
            return True

        if monitor.degraded:
            return monitor.policy.fallback is not None

        return True

    def get_degradation_level(self) -> DegradationLevel:
        """Get current system degradation level."""
        return self.current_level

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system degradation status."""
        feature_statuses = {}
        for name, monitor in self.monitors.items():
            feature_statuses[name] = monitor.get_status()

        return {
            "degradation_level": self.current_level.value,
            "degraded_features": list(self.degraded_features),
            "total_features": len(self.policies),
            "required_features_degraded": [
                name for name, monitor in self.monitors.items()
                if monitor.degraded and monitor.policy.required
            ],
            "feature_statuses": feature_statuses,
        }

    def force_degrade(self, feature: str) -> None:
        """Force a feature into degraded state (for testing)."""
        monitor = self.monitors.get(feature)
        if monitor:
            monitor._degrade()
            self._update_degradation_level()
            self.logger.info("feature_force_degraded", feature=feature)

    def force_recover(self, feature: str) -> None:
        """Force a feature to recover (for testing)."""
        monitor = self.monitors.get(feature)
        if monitor:
            monitor._recover()
            self._update_degradation_level()
            self.logger.info("feature_force_recovered", feature=feature)

    def _update_degradation_level(self) -> None:
        """Update overall degradation level based on feature states."""
        degraded_required = [
            name for name, monitor in self.monitors.items()
            if monitor.degraded and monitor.policy.required
        ]
        degraded_optional = [
            name for name, monitor in self.monitors.items()
            if monitor.degraded and not monitor.policy.required
        ]

        self.degraded_features = set(degraded_required + degraded_optional)

        if len(degraded_required) > 0:
            if len(degraded_required) == len(self.policies):
                self.current_level = DegradationLevel.CRITICAL
            elif len(degraded_required) > len(self.policies) / 2:
                self.current_level = DegradationLevel.SEVERE
            else:
                self.current_level = DegradationLevel.MODERATE
        elif len(degraded_optional) > 0:
            if len(degraded_optional) > len(self.policies) / 2:
                self.current_level = DegradationLevel.MODERATE
            else:
                self.current_level = DegradationLevel.MINIMAL
        else:
            self.current_level = DegradationLevel.NONE

        if self.current_level != DegradationLevel.NONE:
            self.logger.warning(
                "system_degraded",
                level=self.current_level.value,
                required_degraded=len(degraded_required),
                optional_degraded=len(degraded_optional),
            )


# Decorator for automatic degradation
def with_fallback(
    feature: str,
    fallback: Optional[Callable[[], Any]] = None,
    manager: Optional[GracefulDegradationManager] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to automatically apply fallback on feature failure.

    Args:
        feature: Feature name
        fallback: Fallback function
        manager: Degradation manager instance
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Use global manager if none provided
            mgr = manager or getattr(with_fallback, '_default_manager', None)
            if not mgr:
                # No manager, just execute function
                return func(*args, **kwargs)

            return mgr.execute_with_fallback(feature, func, *args, **kwargs)
        return wrapper
    return decorator


# Default global manager instance
_default_manager = GracefulDegradationManager()
with_fallback._default_manager = _default_manager  # type: ignore