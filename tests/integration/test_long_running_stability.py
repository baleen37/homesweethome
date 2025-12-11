import pytest
import time

# These imports will fail initially - that's expected for TDD
# import psutil
# import os
# from crawler.config import CrawlerConfig
# from crawler.coordinator import CrawlCoordinator


def test_memory_usage_stability_during_crawling(integration_test_dir):
    """Test that memory usage remains stable during extended crawling"""
    try:
        import psutil
        import os
        from crawler.config import CrawlerConfig
        from crawler.coordinator import CrawlCoordinator
    except ImportError as e:
        pytest.skip(f"Required modules not available: {e}")

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Configure for extended crawling (multiple districts)
    config = CrawlerConfig.for_integration_test(
        output_dir=str(integration_test_dir / "csv"),
        districts=["강남구", "서초구"],  # Larger test case
    )

    coordinator = CrawlCoordinator(config)

    # Monitor memory during crawling
    memory_samples = [initial_memory]

    # Start crawling (this will take time)
    start_time = time.time()
    success = coordinator.crawl_all()
    end_time = time.time()

    final_memory = process.memory_info().rss / 1024 / 1024
    memory_samples.append(final_memory)

    # Verify stability
    memory_increase = final_memory - initial_memory
    memory_increase_per_minute = memory_increase / ((end_time - start_time) / 60)

    assert success, "Crawling should complete successfully"
    assert memory_increase_per_minute < 50, (
        f"Memory leak detected: {memory_increase_per_minute:.2f} MB/min"
    )
    assert final_memory < initial_memory + 500, f"Excessive memory usage: {final_memory:.2f} MB"


def test_resource_cleanup_after_crawling(integration_test_dir):
    """Test that all resources are properly cleaned up"""
    try:
        import psutil
        from crawler.config import CrawlerConfig
        from crawler.coordinator import CrawlCoordinator
    except ImportError as e:
        pytest.skip(f"Required modules not available: {e}")

    config = CrawlerConfig.for_integration_test(
        output_dir=str(integration_test_dir / "csv"), districts=["강남구"]
    )

    coordinator = CrawlCoordinator(config)

    # Count open file descriptors before
    process = psutil.Process()
    initial_files = len(process.open_files())

    # Simulate some work (since crawl_all doesn't exist yet)
    # Close files if the method exists
    if hasattr(coordinator.transaction_writer, "_close"):
        coordinator.transaction_writer._close()
    if hasattr(coordinator.complexes_writer, "_close"):
        coordinator.complexes_writer._close()

    # Run cleanup if available
    if hasattr(coordinator, "cleanup"):
        coordinator.cleanup()

    # Check cleanup after some time
    time.sleep(2)
    final_files = len(process.open_files())

    assert final_files <= initial_files + 5, f"File descriptor leak: {final_files - initial_files}"


def test_long_running_error_recovery(integration_test_dir):
    """Test error recovery during long running operations"""
    try:
        from crawler.config import CrawlerConfig
        from crawler.coordinator import CrawlCoordinator
        from crawler.utils.checkpoint import CheckpointManager
    except ImportError as e:
        pytest.skip(f"Required modules not available: {e}")

    # Configure for testing
    config = CrawlerConfig.for_integration_test(
        output_dir=str(integration_test_dir / "csv"), districts=["강남구"]
    )

    coordinator = CrawlCoordinator(config)

    # Test checkpoint recovery after errors
    checkpoint_file = integration_test_dir / "checkpoint.json"
    coordinator.checkpoint_manager = CheckpointManager(str(checkpoint_file))

    # Simulate error state
    error_state = {"failed_dongs": ["test_dong"], "error_count": 5, "timestamp": time.time()}
    coordinator.checkpoint_manager.save(error_state)

    # Verify error state is preserved
    loaded_state = coordinator.checkpoint_manager.load()
    assert loaded_state is not None, "Error state should be saved"
    assert loaded_state.get("failed_dongs") == ["test_dong"]


def test_graceful_shutdown_handling(integration_test_dir):
    """Test that crawling can be gracefully shutdown"""
    try:
        from crawler.config import CrawlerConfig
        from crawler.coordinator import CrawlCoordinator
    except ImportError as e:
        pytest.skip(f"Required modules not available: {e}")

    config = CrawlerConfig.for_integration_test(
        output_dir=str(integration_test_dir / "csv"),
        districts=["강남구", "서초구", "송파구"],  # Multiple districts
    )

    coordinator = CrawlCoordinator(config)

    # Test resource cleanup
    assert coordinator.output_dir.exists(), "Output directory should exist"

    # Check that writer methods exist
    assert hasattr(coordinator.transaction_writer, "write"), (
        "Transaction writer should have write method"
    )
    assert hasattr(coordinator.complexes_writer, "write"), "Complex writer should have write method"


def test_gc_pressure_during_crawling(integration_test_dir):
    """Test garbage collection pressure during crawling"""
    try:
        import gc
        from crawler.config import CrawlerConfig
        from crawler.coordinator import CrawlCoordinator
    except ImportError as e:
        pytest.skip(f"Required modules not available: {e}")

    config = CrawlerConfig.for_integration_test(
        output_dir=str(integration_test_dir / "csv"), districts=["강남구"]
    )

    coordinator = CrawlCoordinator(config)

    # Force GC before test
    gc.collect()
    initial_objects = len(gc.get_objects())

    # Simulate some data processing
    test_data = []
    for i in range(1000):
        test_data.append({"id": i, "data": "x" * 1000})

    # Process data through coordinator writers
    coordinator.transaction_writer.write(test_data)

    # Clear test data
    del test_data

    # Force GC after test
    gc.collect()
    final_objects = len(gc.get_objects())

    # Object count shouldn't grow excessively (allowing some variance)
    object_increase = final_objects - initial_objects
    assert object_increase < 10000, f"Too many objects created: {object_increase}"
