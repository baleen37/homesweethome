"""Performance monitoring utilities for integration tests"""

import time
import psutil
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from contextlib import contextmanager


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""

    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_peak_mb: float = 0.0
    disk_io_read_mb: float = 0.0
    disk_io_write_mb: float = 0.0
    network_bytes_sent: float = 0.0
    network_bytes_recv: float = 0.0
    duration_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "memory_peak_mb": self.memory_peak_mb,
            "disk_io_read_mb": self.disk_io_read_mb,
            "disk_io_write_mb": self.disk_io_write_mb,
            "network_bytes_sent": self.network_bytes_sent,
            "network_bytes_recv": self.network_bytes_recv,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp,
        }


class PerformanceMonitor:
    """Monitor system performance during tests"""

    def __init__(self, sample_interval: float = 1.0):
        self.sample_interval = sample_interval
        self.process = psutil.Process(os.getpid())
        self.metrics: List[PerformanceMetrics] = []
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

        # Store initial counters
        self.initial_io = self.process.io_counters()
        self.initial_net = psutil.net_io_counters()

    def start(self) -> None:
        """Start performance monitoring"""
        if self.monitoring:
            return

        self.monitoring = True
        self.start_time = time.time()
        self.metrics.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop(self) -> None:
        """Stop performance monitoring"""
        if not self.monitoring:
            return

        self.monitoring = False
        self.end_time = time.time()

        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)

    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self.monitoring:
            try:
                # CPU and memory
                cpu_percent = self.process.cpu_percent()
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024

                # Disk I/O
                io_counters = self.process.io_counters()
                disk_read_mb = (io_counters.read_bytes - self.initial_io.read_bytes) / 1024 / 1024
                disk_write_mb = (
                    (io_counters.write_bytes - self.initial_io.write_bytes) / 1024 / 1024
                )

                # Network I/O
                net_counters = psutil.net_io_counters()
                net_sent = net_counters.bytes_sent - self.initial_net.bytes_sent
                net_recv = net_counters.bytes_recv - self.initial_net.bytes_recv

                # Create metrics
                metrics = PerformanceMetrics(
                    cpu_percent=cpu_percent,
                    memory_mb=memory_mb,
                    disk_io_read_mb=disk_read_mb,
                    disk_io_write_mb=disk_write_mb,
                    network_bytes_sent=net_sent,
                    network_bytes_recv=net_recv,
                )

                self.metrics.append(metrics)
                time.sleep(self.sample_interval)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Process might have ended
                break
            except Exception as e:
                print(f"Monitoring error: {e}")
                break

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.metrics:
            return {}

        duration = (self.end_time or time.time()) - (self.start_time or 0)

        # Calculate statistics
        cpu_values = [m.cpu_percent for m in self.metrics]
        memory_values = [m.memory_mb for m in self.metrics]

        summary = {
            "duration_seconds": duration,
            "sample_count": len(self.metrics),
            "cpu": {
                "avg": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                "max": max(cpu_values) if cpu_values else 0,
                "min": min(cpu_values) if cpu_values else 0,
            },
            "memory_mb": {
                "avg": sum(memory_values) / len(memory_values) if memory_values else 0,
                "max": max(memory_values) if memory_values else 0,
                "min": min(memory_values) if memory_values else 0,
                "peak": max(m.memory_peak_mb for m in self.metrics) if self.metrics else 0,
            },
            "disk_io_mb": {
                "total_read": self.metrics[-1].disk_io_read_mb if self.metrics else 0,
                "total_write": self.metrics[-1].disk_io_write_mb if self.metrics else 0,
            },
            "network_bytes": {
                "total_sent": self.metrics[-1].network_bytes_sent if self.metrics else 0,
                "total_recv": self.metrics[-1].network_bytes_recv if self.metrics else 0,
            },
        }

        return summary

    def save_metrics(self, file_path: Path) -> None:
        """Save metrics to JSON file"""
        import json

        data = {
            "summary": self.get_summary(),
            "metrics": [m.to_dict() for m in self.metrics],
        }

        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def check_memory_leak(self, threshold_mb: float = 50.0) -> bool:
        """Check for potential memory leak"""
        if len(self.metrics) < 10:
            return False

        # Check if memory consistently increases
        memory_trend = [
            self.metrics[i].memory_mb - self.metrics[i - 1].memory_mb
            for i in range(1, len(self.metrics))
        ]

        # Calculate average increase
        avg_increase = sum(memory_trend) / len(memory_trend)

        return avg_increase > threshold_mb / len(self.metrics)

    def check_cpu_overload(self, threshold_percent: float = 80.0) -> bool:
        """Check for CPU overload"""
        if not self.metrics:
            return False

        avg_cpu = sum(m.cpu_percent for m in self.metrics) / len(self.metrics)
        return avg_cpu > threshold_percent

    def check_disk_io_intensity(self, threshold_mb_per_sec: float = 10.0) -> bool:
        """Check for excessive disk I/O"""
        if len(self.metrics) < 2 or not self.start_time or not self.end_time:
            return False

        total_io = self.metrics[-1].disk_io_read_mb + self.metrics[-1].disk_io_write_mb
        duration = self.end_time - self.start_time

        io_rate = total_io / duration if duration > 0 else 0
        return io_rate > threshold_mb_per_sec


@contextmanager
def monitor_performance(
    monitor_name: str,
    sample_interval: float = 1.0,
    save_to_file: bool = True,
    output_dir: Optional[Path] = None,
):
    """Context manager for performance monitoring"""
    monitor = PerformanceMonitor(sample_interval=sample_interval)

    try:
        monitor.start()
        yield monitor
    finally:
        monitor.stop()

        if save_to_file:
            output_path = output_dir or Path("output/test-integration/performance")
            output_path.mkdir(parents=True, exist_ok=True)
            monitor.save_metrics(output_path / f"{monitor_name}_metrics.json")
