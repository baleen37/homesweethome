"""
Tests for memory profiler utilities.
"""

import time
from unittest.mock import MagicMock, patch

from crawler.utils.memory_profiler import (
    CircularBuffer,
    MemoryProfiler,
    MemorySnapshot,
    MemoryStats,
    ObjectTracker,
    PerformanceMetrics,
    check_memory_usage,
    force_garbage_collection,
    profile_memory,
)


class TestMemorySnapshot:
    """Test MemorySnapshot dataclass."""

    def test_memory_snapshot_creation(self):
        """Test memory snapshot creation."""
        snapshot = MemorySnapshot(
            timestamp=1234567890.0,
            rss_mb=100.5,
            vms_mb=200.0,
            percent=10.5,
            active_objects=1000,
            tracemalloc_current=1024,
            tracemalloc_peak=2048,
        )

        assert snapshot.timestamp == 1234567890.0
        assert snapshot.rss_mb == 100.5
        assert snapshot.vms_mb == 200.0
        assert snapshot.percent == 10.5
        assert snapshot.active_objects == 1000
        assert snapshot.tracemalloc_current == 1024
        assert snapshot.tracemalloc_peak == 2048

    def test_to_dict(self):
        """Test converting snapshot to dictionary."""
        snapshot = MemorySnapshot(
            timestamp=1234567890.0,
            rss_mb=100.5,
            vms_mb=200.0,
            percent=10.5,
            active_objects=1000,
        )

        data = snapshot.to_dict()
        expected = {
            "timestamp": 1234567890.0,
            "rss_mb": 100.5,
            "vms_mb": 200.0,
            "percent": 10.5,
            "active_objects": 1000,
            "tracemalloc_current": 0,
            "tracemalloc_peak": 0,
        }

        assert data == expected


class TestMemoryStats:
    """Test MemoryStats dataclass."""

    def test_memory_stats_creation(self):
        """Test memory stats creation."""
        initial = MemorySnapshot(0, 100, 200, 10, 1000)
        peak = MemorySnapshot(1, 150, 250, 15, 1200)
        final = MemorySnapshot(2, 120, 220, 12, 1100)

        stats = MemoryStats(initial=initial, peak=peak, final=final)

        assert stats.initial == initial
        assert stats.peak == peak
        assert stats.final == final
        assert stats.snapshots == []

    def test_get_max_rss(self):
        """Test getting maximum RSS usage."""
        snapshots = [
            MemorySnapshot(0, 100, 200, 10, 1000),
            MemorySnapshot(1, 150, 250, 15, 1200),
            MemorySnapshot(2, 120, 220, 12, 1100),
        ]

        stats = MemoryStats(
            initial=snapshots[0],
            peak=snapshots[1],
            final=snapshots[2],
            snapshots=snapshots,
        )

        assert stats.get_max_rss() == 150.0

    def test_get_memory_growth(self):
        """Test getting memory growth."""
        initial = MemorySnapshot(0, 100, 200, 10, 1000)
        final = MemorySnapshot(2, 120, 220, 12, 1100)

        stats = MemoryStats(initial=initial, peak=final, final=final)

        assert stats.get_memory_growth() == 20.0

    def test_get_object_growth(self):
        """Test getting object growth."""
        initial = MemorySnapshot(0, 100, 200, 10, 1000)
        final = MemorySnapshot(2, 120, 220, 12, 1500)

        stats = MemoryStats(initial=initial, peak=final, final=final)

        assert stats.get_object_growth() == 500


class TestMemoryProfiler:
    """Test MemoryProfiler class."""

    @patch("crawler.utils.memory_profiler.psutil.Process")
    @patch("crawler.utils.memory_profiler.tracemalloc")
    def test_profiler_initialization(self, mock_tracemalloc, mock_process):
        """Test profiler initialization."""
        mock_process.return_value.memory_info.return_value = MagicMock(
            rss=1024 * 1024 * 100, vms=1024 * 1024 * 200
        )
        mock_process.return_value.memory_percent.return_value = 10.5
        mock_tracemalloc.is_tracing.return_value = False

        profiler = MemoryProfiler(sample_interval=0.5)
        assert profiler.sample_interval == 0.5
        assert profiler.snapshots == []

    @patch("crawler.utils.memory_profiler.psutil.Process")
    @patch("crawler.utils.memory_profiler.tracemalloc")
    def test_start_profiling(self, mock_tracemalloc, mock_process):
        """Test starting memory profiling."""
        mock_process.return_value.memory_info.return_value = MagicMock(
            rss=1024 * 1024 * 100, vms=1024 * 1024 * 200
        )
        mock_process.return_value.memory_percent.return_value = 10.5
        mock_tracemalloc.is_tracing.return_value = False

        profiler = MemoryProfiler()
        profiler.start()

        assert profiler._active is True
        assert len(profiler.snapshots) == 1
        mock_tracemalloc.start.assert_called_once()

    @patch("crawler.utils.memory_profiler.psutil.Process")
    @patch("crawler.utils.memory_profiler.tracemalloc")
    def test_stop_profiling(self, mock_tracemalloc, mock_process):
        """Test stopping memory profiling."""
        mock_process.return_value.memory_info.return_value = MagicMock(
            rss=1024 * 1024 * 100, vms=1024 * 1024 * 200
        )
        mock_process.return_value.memory_percent.return_value = 10.5
        mock_tracemalloc.is_tracing.return_value = True
        mock_tracemalloc.get_traced_memory.return_value = (1024, 2048)

        profiler = MemoryProfiler()
        profiler.start()
        time.sleep(0.01)  # Small delay
        profiler.snapshot()

        stats = profiler.stop()

        assert profiler._active is False
        assert isinstance(stats, MemoryStats)
        assert stats.initial is not None
        assert stats.final is not None

    def test_context_manager(self):
        """Test profiler as context manager."""
        with (
            patch("crawler.utils.memory_profiler.psutil.Process"),
            patch("crawler.utils.memory_profiler.tracemalloc"),
        ):
            with profile_memory() as profiler:
                assert profiler._active is True

            # Context should auto-stop
            assert profiler._active is False


class TestObjectTracker:
    """Test ObjectTracker class."""

    def test_tracker_initialization(self):
        """Test tracker initialization."""
        tracker = ObjectTracker()
        assert tracker.track_types == []
        assert tracker.object_counts == {}
        assert tracker.objects == {}

        tracker = ObjectTracker(track_types=[list, dict])
        assert tracker.track_types == [list, dict]

    def test_track_object(self):
        """Test object tracking."""
        tracker = ObjectTracker(track_types=[list])

        # Track list
        my_list = [1, 2, 3]
        tracker.track_object(my_list)
        assert tracker.object_counts[list] == 1
        assert id(my_list) in tracker.objects[list]

        # Don't track dict (not in track_types)
        my_dict = {"a": 1}
        tracker.track_object(my_dict)
        assert dict not in tracker.object_counts

    def test_untrack_object(self):
        """Test object untracking."""
        tracker = ObjectTracker()
        my_list = [1, 2, 3]

        tracker.track_object(my_list)
        assert tracker.object_counts[list] == 1

        tracker.untrack_object(my_list)
        assert tracker.object_counts[list] == 0
        assert len(tracker.objects[list]) == 0

    def test_get_counts(self):
        """Test getting object counts."""
        tracker = ObjectTracker()
        list1 = [1, 2]
        list2 = [3, 4]

        tracker.track_object(list1)
        tracker.track_object(list2)

        counts = tracker.get_counts()
        assert counts[list] == 2

    def test_get_leaked_objects(self):
        """Test getting leaked objects."""
        tracker = ObjectTracker()
        list1 = [1, 2]
        list2 = [3, 4]

        tracker.track_object(list1)
        tracker.track_object(list2)

        leaked = tracker.get_leaked_objects()
        assert list in leaked
        assert len(leaked[list]) == 2

        # Untrack one object
        tracker.untrack_object(list1)
        leaked = tracker.get_leaked_objects()
        assert len(leaked[list]) == 1

    def test_clear(self):
        """Test clearing tracker."""
        tracker = ObjectTracker()
        tracker.track_object([1, 2])
        tracker.track_object({"a": 1})

        tracker.clear()
        assert tracker.object_counts == {}
        assert tracker.objects == {}


class TestPerformanceMetrics:
    """Test PerformanceMetrics class."""

    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = PerformanceMetrics()
        assert metrics.metrics == {}
        assert metrics.counters == {}
        assert metrics.timers == {}

    def test_record_time(self):
        """Test recording timing metrics."""
        metrics = PerformanceMetrics()
        metrics.record_time("operation", 1.5)
        metrics.record_time("operation", 2.0)

        assert len(metrics.metrics["operation_time"]) == 2
        assert metrics.metrics["operation_time"] == [1.5, 2.0]

    def test_record_count(self):
        """Test recording counter metrics."""
        metrics = PerformanceMetrics()
        metrics.record_count("requests", 5)
        metrics.record_count("requests", 3)

        assert metrics.counters["requests"] == 8

    def test_timer(self):
        """Test timer functionality."""
        metrics = PerformanceMetrics()

        metrics.start_timer("test")
        time.sleep(0.01)  # Small delay
        duration = metrics.stop_timer("test")

        assert duration > 0
        assert "test_time" in metrics.metrics
        assert len(metrics.metrics["test_time"]) == 1

    def test_timer_context_manager(self):
        """Test timer as context manager."""
        metrics = PerformanceMetrics()

        with metrics.timer("test"):
            time.sleep(0.01)

        assert "test_time" in metrics.metrics
        assert len(metrics.metrics["test_time"]) == 1
        assert metrics.metrics["test_time"][0] > 0

    def test_get_stats(self):
        """Test getting performance statistics."""
        metrics = PerformanceMetrics()

        # Add timing data
        metrics.record_time("op1", 1.0)
        metrics.record_time("op1", 2.0)
        metrics.record_time("op1", 3.0)

        # Add counter data
        metrics.record_count("events", 10)
        metrics.record_count("events", 5)

        stats = metrics.get_stats()

        assert "op1_time_mean" in stats
        assert stats["op1_time_mean"] == 2.0
        assert "op1_time_std" in stats
        assert "events" in stats
        assert stats["events"] == 15

    def test_reset(self):
        """Test resetting metrics."""
        metrics = PerformanceMetrics()
        metrics.record_time("op", 1.0)
        metrics.record_count("cnt", 5)
        metrics.start_timer("timer")

        metrics.reset()

        assert metrics.metrics == {}
        assert metrics.counters == {}
        assert metrics.timers == {}


class TestCircularBuffer:
    """Test CircularBuffer class."""

    def test_buffer_creation(self):
        """Test buffer creation."""
        buffer = CircularBuffer(max_size=5)
        assert buffer.max_size == 5
        assert buffer.buffer == []
        assert buffer.index == 0
        assert buffer.is_full is False

    def test_append_under_capacity(self):
        """Test appending when under capacity."""
        buffer = CircularBuffer(max_size=3)
        buffer.append(1)
        buffer.append(2)

        assert len(buffer) == 2
        assert buffer.buffer == [1, 2]
        assert buffer.is_full is False

    def test_append_at_capacity(self):
        """Test appending when at capacity."""
        buffer = CircularBuffer(max_size=3)
        buffer.append(1)
        buffer.append(2)
        buffer.append(3)

        assert len(buffer) == 3
        assert buffer.buffer == [1, 2, 3]
        assert buffer.is_full is True

    def test_append_over_capacity(self):
        """Test appending when over capacity."""
        buffer = CircularBuffer(max_size=3)
        buffer.append(1)
        buffer.append(2)
        buffer.append(3)
        buffer.append(4)  # Should overwrite 1

        assert len(buffer) == 3
        assert buffer.buffer == [4, 2, 3]
        assert buffer.index == 1
        assert buffer.is_full is True

    def test_iteration(self):
        """Test buffer iteration."""
        buffer = CircularBuffer(max_size=3)
        buffer.append(1)
        buffer.append(2)
        buffer.append(3)
        buffer.append(4)
        buffer.append(5)  # Should have [5, 4, 3] in order

        items = list(buffer)
        assert items == [4, 3, 5]

    def test_iteration_not_full(self):
        """Test iteration when buffer not full."""
        buffer = CircularBuffer(max_size=5)
        buffer.append(1)
        buffer.append(2)
        buffer.append(3)

        items = list(buffer)
        assert items == [1, 2, 3]


class TestUtilityFunctions:
    """Test utility functions."""

    @patch("crawler.utils.memory_profiler.psutil.virtual_memory")
    def test_get_memory_limit(self, mock_virtual_memory):
        """Test getting memory limit."""
        mock_virtual_memory.return_value.total = 8 * 1024**3  # 8 GB

        from crawler.utils.memory_profiler import get_memory_limit

        limit = get_memory_limit()

        assert limit == 8.0

    @patch("crawler.utils.memory_profiler.psutil.Process")
    def test_check_memory_usage(self, mock_process):
        """Test checking memory usage."""
        # Test under threshold
        mock_process.return_value.memory_info.return_value.rss = 500 * 1024 * 1024  # 500 MB
        with patch("crawler.utils.memory_profiler.psutil.Process", mock_process):
            result = check_memory_usage(1000.0)
            assert result is False

        # Test over threshold
        mock_process.return_value.memory_info.return_value.rss = 1500 * 1024 * 1024  # 1500 MB
        with patch("crawler.utils.memory_profiler.psutil.Process", mock_process):
            result = check_memory_usage(1000.0)
            assert result is True

    def test_force_garbage_collection(self):
        """Test forcing garbage collection."""
        # Create some objects
        objects = []
        for _ in range(100):
            objects.append({"key": i for i in range(10)})

        # Force collection
        result = force_garbage_collection()

        assert "objects_before" in result
        assert "objects_after" in result
        assert "objects_collected" in result
        assert "gc_cycles_run" in result
        assert isinstance(result["objects_before"], int)
        assert isinstance(result["objects_after"], int)
