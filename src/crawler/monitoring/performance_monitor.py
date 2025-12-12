"""
Performance monitoring system for crawler operations.
"""

import json
import logging
import time
import threading
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

import psutil

from crawler.utils.memory_profiler import MemoryProfiler, PerformanceMetrics


@dataclass
class PerformanceAlert:
    """Represents a performance alert."""

    timestamp: float
    metric_name: str
    current_value: float
    threshold: float
    message: str
    severity: str = "warning"  # 'info', 'warning', 'error', 'critical'


@dataclass
class MetricThreshold:
    """Threshold configuration for a metric."""

    warning: float
    error: float
    critical: float


class PerformanceMonitor:
    """Real-time performance monitoring system."""

    def __init__(
        self,
        sample_interval: float = 1.0,
        history_size: int = 1000,
        alert_callbacks: Optional[List[Callable]] = None,
    ):
        """Initialize the performance monitor.

        Args:
            sample_interval: Interval between samples in seconds
            history_size: Number of samples to keep in history
            alert_callbacks: List of callbacks to call on alerts
        """
        self.sample_interval = sample_interval
        self.history_size = history_size
        self.alert_callbacks = alert_callbacks or []

        # Thread safety locks
        self._data_lock = threading.RLock()  # Reentrant lock for nested calls
        self._monitoring_lock = threading.Lock()

        # Monitoring components
        self.memory_profiler = MemoryProfiler()
        self.performance_metrics = PerformanceMetrics()

        # Data storage
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_size))
        self.alerts_history: List[PerformanceAlert] = []
        self.process = psutil.Process()

        # Thresholds for alerts
        self.thresholds = {
            "memory_usage_mb": MetricThreshold(warning=500, error=1000, critical=2000),
            "memory_growth_mb": MetricThreshold(warning=100, error=200, critical=500),
            "cpu_percent": MetricThreshold(warning=70, error=85, critical=95),
            "response_time_ms": MetricThreshold(warning=1000, error=3000, critical=5000),
            "error_rate_percent": MetricThreshold(warning=5, error=10, critical=20),
        }

        # Monitoring state
        self._monitoring = False
        self._monitor_thread = None
        self._start_time = None
        self.logger = logging.getLogger(__name__)

    def start_monitoring(self) -> None:
        """Start performance monitoring in background thread."""
        with self._monitoring_lock:
            if self._monitoring:
                self.logger.warning("Performance monitoring already active")
                return

            self._monitoring = True
            self._start_time = time.time()
            self.memory_profiler.start()

            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()

            self.logger.info("Performance monitoring started")

    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return final statistics.

        Returns:
            Final monitoring statistics
        """
        with self._monitoring_lock:
            if not self._monitoring:
                self.logger.warning("Performance monitoring not active")
                return {}

            self._monitoring = False

        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)

        memory_stats = self.memory_profiler.stop()

        with self._data_lock:
            perf_stats = self.performance_metrics.get_stats()
            alerts_count = len(self.alerts_history)
            metrics_collected = {k: len(v) for k, v in self.metrics_history.items()}

        # Generate final report
        report = {
            "monitoring_duration": time.time() - self._start_time if self._start_time else 0,
            "memory_stats": {
                "peak_rss_mb": memory_stats.get_max_rss(),
                "memory_growth_mb": memory_stats.get_memory_growth(),
                "object_growth": memory_stats.get_object_growth(),
            },
            "performance_stats": perf_stats,
            "alerts_count": alerts_count,
            "metrics_collected": metrics_collected,
        }

        self.logger.info("Performance monitoring stopped")
        return report

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                self._collect_metrics()
                time.sleep(self.sample_interval)
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")

    def _collect_metrics(self) -> None:
        """Collect current performance metrics."""
        timestamp = time.time()

        # System metrics
        memory_info = self.process.memory_info()
        cpu_percent = self.process.cpu_percent()
        threads_count = self.process.num_threads()

        # Memory metrics
        memory_rss_mb = memory_info.rss / (1024 * 1024)
        memory_vms_mb = memory_info.vms / (1024 * 1024)
        memory_percent = self.process.memory_percent()

        # Update metrics history with thread safety
        with self._data_lock:
            self.metrics_history["memory_rss_mb"].append((timestamp, memory_rss_mb))
            self.metrics_history["memory_vms_mb"].append((timestamp, memory_vms_mb))
            self.metrics_history["memory_percent"].append((timestamp, memory_percent))
            self.metrics_history["cpu_percent"].append((timestamp, cpu_percent))
            self.metrics_history["threads_count"].append((timestamp, threads_count))

            # System-wide metrics
            system_memory = psutil.virtual_memory()
            self.metrics_history["system_memory_available_mb"].append(
                (timestamp, system_memory.available / (1024 * 1024))
            )
            self.metrics_history["system_memory_percent"].append((timestamp, system_memory.percent))

        # Check for alerts (this will acquire its own lock for alerts_history)
        self._check_alerts(timestamp, memory_rss_mb, cpu_percent)

    def _check_alerts(self, timestamp: float, memory_mb: float, cpu_percent: float) -> None:
        """Check if any metrics exceed thresholds and generate alerts.

        Args:
            timestamp: Current timestamp
            memory_mb: Memory usage in MB
            cpu_percent: CPU usage percentage
        """
        # Check memory usage
        self._check_threshold_alert(
            timestamp, "memory_usage_mb", memory_mb, self.thresholds["memory_usage_mb"]
        )

        # Check CPU usage
        self._check_threshold_alert(
            timestamp, "cpu_percent", cpu_percent, self.thresholds["cpu_percent"]
        )

        # Check memory growth (calculate from history with thread safety)
        with self._data_lock:
            if len(self.metrics_history["memory_rss_mb"]) > 10:
                recent = list(self.metrics_history["memory_rss_mb"])[-10:]
                growth_mb = recent[-1][1] - recent[0][1]
                self._check_threshold_alert(
                    timestamp, "memory_growth_mb", growth_mb, self.thresholds["memory_growth_mb"]
                )

    def _check_threshold_alert(
        self, timestamp: float, metric_name: str, value: float, threshold: MetricThreshold
    ) -> None:
        """Check if a metric exceeds threshold and create alert.

        Args:
            timestamp: Current timestamp
            metric_name: Name of the metric
            value: Current metric value
            threshold: Threshold configuration
        """
        severity = None
        if value >= threshold.critical:
            severity = "critical"
        elif value >= threshold.error:
            severity = "error"
        elif value >= threshold.warning:
            severity = "warning"

        if severity:
            alert = PerformanceAlert(
                timestamp=timestamp,
                metric_name=metric_name,
                current_value=value,
                threshold=getattr(threshold, severity),
                message=f"{metric_name} is {value:.2f} (threshold: {getattr(threshold, severity)})",
                severity=severity,
            )

            # Thread-safe alert handling
            with self._data_lock:
                self.alerts_history.append(alert)
            self._handle_alert(alert)

    def _handle_alert(self, alert: PerformanceAlert) -> None:
        """Handle a performance alert.

        Args:
            alert: Alert to handle
        """
        self.logger.warning(f"Performance alert [{alert.severity}]: {alert.message}")

        # Call alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Error in alert callback: {e}")

    def record_operation_time(self, operation_name: str, duration: float) -> None:
        """Record operation execution time.

        Args:
            operation_name: Name of the operation
            duration: Duration in seconds
        """
        self.performance_metrics.record_time(operation_name, duration)
        timestamp = time.time()

        # Thread-safe metrics update
        with self._data_lock:
            self.metrics_history[f"operation_{operation_name}_time"].append(
                (timestamp, duration * 1000)  # Convert to milliseconds
            )

        # Check for slow operation alerts
        metric_name = f"operation_{operation_name}_response_time_ms"
        if metric_name in self.thresholds:
            self._check_threshold_alert(
                timestamp, metric_name, duration * 1000, self.thresholds[metric_name]
            )

    def record_error_rate(self, operation_name: str, error_rate: float) -> None:
        """Record error rate for an operation.

        Args:
            operation_name: Name of the operation
            error_rate: Error rate as percentage (0-100)
        """
        timestamp = time.time()

        # Thread-safe metrics update
        with self._data_lock:
            self.metrics_history[f"error_rate_{operation_name}"].append((timestamp, error_rate))

        # Check for high error rate alerts
        metric_name = "error_rate_percent"
        if metric_name in self.thresholds:
            self._check_threshold_alert(
                timestamp, metric_name, error_rate, self.thresholds[metric_name]
            )

    def get_current_metrics(self) -> Dict[str, float]:
        """Get current metric values.

        Returns:
            Dictionary of current metric values
        """
        current = {}

        # Thread-safe read of metrics
        with self._data_lock:
            for metric_name, history in self.metrics_history.items():
                if history:
                    current[metric_name] = history[-1][1]

        return current

    def get_metric_summary(self, metric_name: str, window_minutes: int = 5) -> Dict[str, float]:
        """Get summary statistics for a metric over a time window.

        Args:
            metric_name: Name of the metric
            window_minutes: Time window in minutes

        Returns:
            Summary statistics
        """
        cutoff_time = time.time() - (window_minutes * 60)

        # Thread-safe read of metrics
        with self._data_lock:
            if metric_name not in self.metrics_history:
                return {}

            values = [
                value
                for timestamp, value in self.metrics_history[metric_name]
                if timestamp >= cutoff_time
            ]

        if not values:
            return {}

        import numpy as np

        return {
            "mean": np.mean(values),
            "median": np.median(values),
            "std": np.std(values),
            "min": np.min(values),
            "max": np.max(values),
            "count": len(values),
        }

    def export_metrics(self, file_path: Path) -> None:
        """Export metrics history to a file.

        Args:
            file_path: Path to export file
        """
        # Thread-safe read of all data
        with self._data_lock:
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "metrics_history": {
                    metric: [(ts, val) for ts, val in history]
                    for metric, history in self.metrics_history.items()
                },
                "alerts": [
                    {
                        "timestamp": alert.timestamp,
                        "metric_name": alert.metric_name,
                        "current_value": alert.current_value,
                        "threshold": alert.threshold,
                        "message": alert.message,
                        "severity": alert.severity,
                    }
                    for alert in self.alerts_history
                ],
            }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2)

        self.logger.info(f"Metrics exported to {file_path}")


class MonitoringDashboard:
    """Simple monitoring dashboard for real-time visualization."""

    def __init__(self, monitor: PerformanceMonitor):
        """Initialize the dashboard.

        Args:
            monitor: Performance monitor instance
        """
        self.monitor = monitor

    def print_summary(self) -> None:
        """Print a summary of current performance metrics."""
        current = self.monitor.get_current_metrics()

        print("\n=== Performance Monitor Summary ===")
        print(f"Memory RSS: {current.get('memory_rss_mb', 0):.2f} MB")
        print(f"Memory Percent: {current.get('memory_percent', 0):.2f}%")
        print(f"CPU Usage: {current.get('cpu_percent', 0):.2f}%")
        print(f"Threads: {current.get('threads_count', 0)}")
        print(f"System Memory Available: {current.get('system_memory_available_mb', 0):.2f} MB")

        # Recent alerts
        recent_alerts = [
            alert
            for alert in self.monitor.alerts_history
            if time.time() - alert.timestamp < 300  # Last 5 minutes
        ]

        if recent_alerts:
            print("\nRecent Alerts:")
            for alert in recent_alerts[-5:]:  # Show last 5
                print(f"  [{alert.severity.upper()}] {alert.message}")

    def start_dashboard(self, refresh_interval: int = 10) -> None:
        """Start a simple text dashboard.

        Args:
            refresh_interval: Refresh interval in seconds
        """
        import itertools

        try:
            for _ in itertools.count():
                self.print_summary()
                time.sleep(refresh_interval)
        except KeyboardInterrupt:
            print("\nDashboard stopped")


# Alert callback examples
def log_alert_callback(alert: PerformanceAlert) -> None:
    """Simple alert callback that logs to a file."""
    log_entry = {
        "timestamp": datetime.fromtimestamp(alert.timestamp).isoformat(),
        "severity": alert.severity,
        "metric": alert.metric_name,
        "value": alert.current_value,
        "threshold": alert.threshold,
        "message": alert.message,
    }

    with open("performance_alerts.log", "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")


def email_alert_callback(alert: PerformanceAlert) -> None:
    """Alert callback that sends email for critical alerts."""
    if alert.severity == "critical":
        # Implementation would depend on email service
        print(f"CRITICAL ALERT: {alert.message} - would send email notification")


# Context manager for monitoring
@contextmanager
def monitor_performance(operation_name: str, monitor: Optional[PerformanceMonitor] = None):
    """Context manager for monitoring an operation.

    Args:
        operation_name: Name of the operation being monitored
        monitor: Performance monitor instance
    """
    if monitor is None:
        monitor = PerformanceMonitor()

    start_time = time.time()
    try:
        yield monitor
    finally:
        duration = time.time() - start_time
        monitor.record_operation_time(operation_name, duration)
