"""
Memory profiling utilities for crawler performance optimization.
"""

import gc
import logging
import os
import psutil
import time
import tracemalloc
import weakref
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, List, Optional, Tuple, Set

import numpy as np


@dataclass
class MemorySnapshot:
    """Represents a memory usage snapshot."""

    timestamp: float
    rss_mb: float  # Resident Set Size in MB
    vms_mb: float  # Virtual Memory Size in MB
    percent: float  # Memory usage percentage
    active_objects: int
    tracemalloc_current: int = 0
    tracemalloc_peak: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "rss_mb": self.rss_mb,
            "vms_mb": self.vms_mb,
            "percent": self.percent,
            "active_objects": self.active_objects,
            "tracemalloc_current": self.tracemalloc_current,
            "tracemalloc_peak": self.tracemalloc_peak,
        }


@dataclass
class MemoryStats:
    """Memory usage statistics."""

    initial: MemorySnapshot
    peak: MemorySnapshot
    final: MemorySnapshot
    snapshots: List[MemorySnapshot] = field(default_factory=list)

    def get_max_rss(self) -> float:
        """Get maximum RSS usage."""
        return max(s.rss_mb for s in self.snapshots + [self.initial, self.peak, self.final])

    def get_memory_growth(self) -> float:
        """Get memory growth from initial to final."""
        return self.final.rss_mb - self.initial.rss_mb

    def get_object_growth(self) -> int:
        """Get object count growth."""
        return self.final.active_objects - self.initial.active_objects

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial": self.initial.to_dict(),
            "peak": self.peak.to_dict(),
            "final": self.final.to_dict(),
            "max_rss_mb": self.get_max_rss(),
            "memory_growth_mb": self.get_memory_growth(),
            "object_growth": self.get_object_growth(),
            "snapshot_count": len(self.snapshots),
        }


class MemoryProfiler:
    """Memory profiler for crawler operations."""

    def __init__(self, sample_interval: float = 0.1):
        self.sample_interval = sample_interval
        self.snapshots: List[MemorySnapshot] = []
        self.process = psutil.Process(os.getpid())
        self.logger = logging.getLogger(__name__)
        self._active = False

    def start(self) -> None:
        """Start memory profiling."""
        if self._active:
            self.logger.warning("Memory profiler already active")
            return

        self._active = True
        self.snapshots.clear()

        # Start tracemalloc for detailed memory tracking
        if not tracemalloc.is_tracing():
            tracemalloc.start()

        # Take initial snapshot
        self._take_snapshot()
        self.logger.info("Memory profiling started")

    def stop(self) -> MemoryStats:
        """Stop memory profiling and return statistics."""
        if not self._active:
            self.logger.warning("Memory profiler not active")
            return MemoryStats(
                initial=self._create_snapshot(),
                peak=self._create_snapshot(),
                final=self._create_snapshot(),
            )

        self._active = False

        # Take final snapshot
        final_snapshot = self._take_snapshot()

        # Create statistics
        stats = MemoryStats(
            initial=self.snapshots[0] if self.snapshots else final_snapshot,
            peak=max(self.snapshots, key=lambda s: s.rss_mb) if self.snapshots else final_snapshot,
            final=final_snapshot,
            snapshots=self.snapshots.copy(),
        )

        self.logger.info(f"Memory profiling stopped. Peak RSS: {stats.get_max_rss():.2f} MB")
        return stats

    def snapshot(self) -> MemorySnapshot:
        """Take a memory snapshot."""
        return self._take_snapshot()

    def _take_snapshot(self) -> MemorySnapshot:
        """Take and store a memory snapshot."""
        snapshot = self._create_snapshot()
        self.snapshots.append(snapshot)
        return snapshot

    def _create_snapshot(self) -> MemorySnapshot:
        """Create a memory snapshot."""
        # Get process memory info
        memory_info = self.process.memory_info()
        memory_percent = self.process.memory_percent()

        # Get object count
        gc.collect()  # Force garbage collection for accurate count
        object_count = len(gc.get_objects())

        # Get tracemalloc info if available
        current, peak = (0, 0)
        if tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()

        return MemorySnapshot(
            timestamp=time.time(),
            rss_mb=memory_info.rss / 1024 / 1024,
            vms_mb=memory_info.vms / 1024 / 1024,
            percent=memory_percent,
            active_objects=object_count,
            tracemalloc_current=current,
            tracemalloc_peak=peak,
        )

    def get_top_allocators(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get top memory allocators."""
        if not tracemalloc.is_tracing():
            return []

        snapshot = tracemalloc.take_snapshot()
        statistics = snapshot.statistics("lineno")

        top_stats = []
        for stat in statistics[:limit]:
            top_stats.append(
                (
                    f"{stat.filename}:{stat.lineno}",
                    stat.size / 1024,  # Convert to KB
                )
            )

        return top_stats


@contextmanager
def profile_memory(profiler: Optional[MemoryProfiler] = None) -> Generator[MemoryStats, None, None]:
    """Context manager for memory profiling."""
    if profiler is None:
        profiler = MemoryProfiler()

    profiler.start()
    try:
        yield profiler
    finally:
        stats = profiler.stop()
        # Log summary
        logger = logging.getLogger(__name__)
        logger.info("Memory profiling summary:")
        logger.info(f"  Peak RSS: {stats.get_max_rss():.2f} MB")
        logger.info(f"  Memory growth: {stats.get_memory_growth():.2f} MB")
        logger.info(f"  Object growth: {stats.get_object_growth()}")


class ObjectTracker:
    """Tracks object creation and deletion for memory leak detection."""

    def __init__(self, track_types: Optional[List[type]] = None):
        self.track_types = track_types or []
        self.object_counts: Dict[type, int] = defaultdict(int)
        # Use weak references to prevent memory leaks
        self.objects: Dict[type, Set] = defaultdict(set)  # Can contain weakref.ref or int
        self.logger = logging.getLogger(__name__)

    def track_object(self, obj: Any) -> None:
        """Track an object using weak reference."""
        obj_type = type(obj)

        # Only track specified types or all if none specified
        if self.track_types and obj_type not in self.track_types:
            return

        self.object_counts[obj_type] += 1

        # Try to create weak reference, fallback to ID if not possible
        try:
            obj_ref = weakref.ref(obj)
            self.objects[obj_type].add(obj_ref)
        except TypeError:
            # Object type doesn't support weak references (e.g., dict, int, str)
            # Fall back to storing the object ID for these types
            self.objects[obj_type].add(id(obj))

    def untrack_object(self, obj: Any) -> None:
        """Untrack an object."""
        obj_type = type(obj)

        # Try weak reference first
        try:
            obj_ref = weakref.ref(obj)
            if obj_ref in self.objects[obj_type]:
                self.objects[obj_type].remove(obj_ref)
                self.object_counts[obj_type] -= 1
        except TypeError:
            # Fall back to object ID
            obj_id = id(obj)
            if obj_id in self.objects[obj_type]:
                self.objects[obj_type].remove(obj_id)
                self.object_counts[obj_type] -= 1

    def get_counts(self) -> Dict[type, int]:
        """Get current object counts, cleaning up dead references."""
        # Clean up dead weak references before returning counts
        self._cleanup_dead_references()
        return dict(self.object_counts)

    def get_leaked_objects(self) -> Dict[type, int]:
        """Get count of potentially leaked objects (still tracked and alive)."""
        self._cleanup_dead_references()
        return {t: len(refs) for t, refs in self.objects.items() if refs}

    def _cleanup_dead_references(self) -> None:
        """Clean up dead weak references and update counts."""
        for obj_type in list(self.objects.keys()):
            # Separate weak references from IDs
            weak_refs = set()
            obj_ids = set()

            for ref_or_id in self.objects[obj_type]:
                if isinstance(ref_or_id, weakref.ref):
                    weak_refs.add(ref_or_id)
                else:
                    obj_ids.add(ref_or_id)

            # Clean up dead weak references
            alive_weak_refs = {ref for ref in weak_refs if ref() is not None}
            dead_count = len(weak_refs) - len(alive_weak_refs)

            # Rebuild the set with alive weak refs and IDs
            self.objects[obj_type] = alive_weak_refs.union(obj_ids)

            if dead_count > 0:
                self.object_counts[obj_type] = max(0, self.object_counts[obj_type] - dead_count)
                self.logger.debug(f"Cleaned up {dead_count} dead references for {obj_type}")

    def clear(self) -> None:
        """Clear all tracked objects."""
        self.object_counts.clear()
        self.objects.clear()


class PerformanceMetrics:
    """Collects and manages performance metrics."""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = defaultdict(list)
        self.counters: Dict[str, int] = defaultdict(int)
        self.timers: Dict[str, float] = {}
        self.logger = logging.getLogger(__name__)

    def record_time(self, name: str, duration: float) -> None:
        """Record a timing metric."""
        self.metrics[f"{name}_time"].append(duration)

    def record_count(self, name: str, count: int = 1) -> None:
        """Record a counter metric."""
        self.counters[name] += count

    def start_timer(self, name: str) -> None:
        """Start a named timer."""
        self.timers[name] = time.time()

    def stop_timer(self, name: str) -> float:
        """Stop a named timer and record the duration."""
        if name not in self.timers:
            self.logger.warning(f"Timer '{name}' not started")
            return 0.0

        duration = time.time() - self.timers[name]
        self.record_time(name, duration)
        del self.timers[name]
        return duration

    @contextmanager
    def timer(self, name: str) -> Generator[None, None, None]:
        """Context manager for timing operations."""
        self.start_timer(name)
        try:
            yield
        finally:
            self.stop_timer(name)

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        stats = {}

        # Timing statistics
        for key, values in self.metrics.items():
            if values:
                stats[f"{key}_mean"] = np.mean(values)
                stats[f"{key}_std"] = np.std(values)
                stats[f"{key}_min"] = min(values)
                stats[f"{key}_max"] = max(values)
                stats[f"{key}_count"] = len(values)

        # Counter statistics
        stats.update(self.counters)

        return stats

    def reset(self) -> None:
        """Reset all metrics."""
        self.metrics.clear()
        self.counters.clear()
        self.timers.clear()


class CircularBuffer:
    """Memory-efficient circular buffer for storing data."""

    def __init__(self, max_size: int, maxlen: Optional[int] = None):
        # Support both max_size and maxlen parameters
        if maxlen is not None:
            self.max_size = maxlen
        else:
            self.max_size = max_size
        self.buffer: List[Any] = []
        self.index = 0
        self.is_full = False

    def append(self, item: Any) -> None:
        """Append item to buffer."""
        if len(self.buffer) < self.max_size:
            self.buffer.append(item)
        else:
            self.buffer[self.index] = item
            self.index = (self.index + 1) % self.max_size
            self.is_full = True

    def __len__(self) -> int:
        """Get current buffer size."""
        return len(self.buffer)

    def __iter__(self) -> Generator[Any, None, None]:
        """Iterate over buffer items in order."""
        if self.is_full:
            # Yield items from current index to end, then from start to index
            for item in self.buffer[self.index :]:
                yield item
            for item in self.buffer[: self.index]:
                yield item
        else:
            # Just yield buffer contents
            for item in self.buffer:
                yield item


def get_memory_limit() -> float:
    """Get system memory limit in GB."""
    return psutil.virtual_memory().total / (1024**3)


def check_memory_usage(threshold_mb: float = 1000.0) -> bool:
    """Check if memory usage exceeds threshold."""
    process = psutil.Process(os.getpid())
    rss_mb = process.memory_info().rss / 1024 / 1024
    return rss_mb > threshold_mb


def force_garbage_collection() -> Dict[str, int]:
    """Force garbage collection and return statistics."""
    before = len(gc.get_objects())
    collected = gc.collect()
    after = len(gc.get_objects())

    return {
        "objects_before": before,
        "objects_after": after,
        "objects_collected": before - after,
        "gc_cycles_run": collected,
    }
