"""
Memory-optimized data mapper for handling large datasets efficiently.
"""

import gc
from typing import Any, Dict, Iterator, List, Optional
from dataclasses import dataclass


from crawler.data_mappers.hogangnono_data_mapper import HogangnonoDataMapper


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    batch_size: int = 1000
    flush_interval: int = 10  # Flush every N batches
    memory_threshold_mb: float = 500.0


class MemoryOptimizedMapper:
    """Memory-optimized data mapper using generators and batch processing."""

    def __init__(
        self,
        base_mapper: Optional[HogangnonoDataMapper] = None,
        batch_config: Optional[BatchConfig] = None,
    ):
        """Initialize the memory-optimized mapper.

        Args:
            base_mapper: Base mapper instance
            batch_config: Batch processing configuration
        """
        self.base_mapper = base_mapper or HogangnonoDataMapper()
        self.batch_config = batch_config or BatchConfig()
        self._processed_count = 0
        self._batch_count = 0

    def process_records_streaming(
        self, records: Iterator[Dict[str, Any]], output_callback: Optional[callable] = None
    ) -> Iterator[Dict[str, Any]]:
        """Process records in streaming fashion to minimize memory usage.

        Args:
            records: Iterator of input records
            output_callback: Optional callback to handle processed records

        Yields:
            Processed records one at a time
        """
        batch = []

        for record in records:
            # Process single record
            try:
                processed = self.base_mapper.map_to_naver_format(record)
                if processed:
                    batch.append(processed)
                    self._processed_count += 1

                    # Yield immediately if callback provided
                    if output_callback:
                        output_callback(processed)
                    else:
                        yield processed

                    # Check batch size and flush
                    if len(batch) >= self.batch_config.batch_size:
                        self._batch_count += 1
                        batch.clear()

                        # Periodic garbage collection
                        if self._batch_count % self.batch_config.flush_interval == 0:
                            gc.collect()

            except Exception as e:
                # Log error but continue processing
                print(f"Error processing record: {e}")
                continue

        # Process any remaining records in batch
        if batch:
            for processed in batch:
                if output_callback:
                    output_callback(processed)
                else:
                    yield processed

    def process_batch_optimized(
        self, records: List[Dict[str, Any]]
    ) -> Iterator[List[Dict[str, Any]]]:
        """Process records in optimized batches.

        Args:
            records: List of input records

        Yields:
            Batches of processed records
        """
        # Use numpy for efficient array operations if possible
        if len(records) > 10000:
            # For large datasets, use chunked processing
            chunk_size = min(self.batch_config.batch_size, len(records) // 10)

            for i in range(0, len(records), chunk_size):
                chunk = records[i : i + chunk_size]

                # Process chunk
                processed_batch = []
                for record in chunk:
                    try:
                        processed = self.base_mapper.map_to_naver_format(record)
                        if processed:
                            processed_batch.append(processed)
                    except Exception:
                        continue

                if processed_batch:
                    yield processed_batch

                # Memory management
                del chunk
                if i % (chunk_size * 10) == 0:
                    gc.collect()
        else:
            # For smaller datasets, use regular batch processing
            for i in range(0, len(records), self.batch_config.batch_size):
                batch = records[i : i + self.batch_config.batch_size]

                processed_batch = []
                for record in batch:
                    try:
                        processed = self.base_mapper.map_to_naver_format(record)
                        if processed:
                            processed_batch.append(processed)
                    except Exception:
                        continue

                if processed_batch:
                    yield processed_batch

    def get_memory_efficient_fields(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Extract only essential fields to reduce memory footprint.

        Args:
            record: Input record

        Returns:
            Record with only essential fields
        """
        essential_fields = [
            "일련번호",
            "아파트명",
            "법정동주소",
            "건축년도",
            "전용면적",
            "층",
            "거래금액",
            "년",
            "월",
            "일",
        ]

        return {field: record.get(field, "") for field in essential_fields if field in record}

    def pre_filter_records(self, records: Iterator[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
        """Filter out invalid records early to save processing time.

        Args:
            records: Iterator of input records

        Yields:
            Valid records
        """
        required_fields = ["일련번호", "아파트명"]

        for record in records:
            # Quick validation
            if all(field in record and record[field] for field in required_fields):
                # Return memory-efficient version
                yield self.get_memory_efficient_fields(record)

    @property
    def processed_count(self) -> int:
        """Get total number of processed records."""
        return self._processed_count

    @property
    def batch_count(self) -> int:
        """Get number of batches processed."""
        return self._batch_count

    def reset_counters(self) -> None:
        """Reset processing counters."""
        self._processed_count = 0
        self._batch_count = 0


class StreamingDataProcessor:
    """Streaming data processor for very large datasets."""

    def __init__(self, mapper: MemoryOptimizedMapper):
        """Initialize the streaming processor.

        Args:
            mapper: Memory-optimized mapper instance
        """
        self.mapper = mapper

    def process_from_generator(
        self,
        data_generator: Iterator[Dict[str, Any]],
        output_file_path: str,
        write_callback: callable,
    ) -> Dict[str, Any]:
        """Process data from a generator and write to file.

        Args:
            data_generator: Generator yielding data records
            output_file_path: Path to output file
            write_callback: Callback to write records to file

        Returns:
            Processing statistics
        """
        stats = {
            "total_records": 0,
            "processed_records": 0,
            "batches_processed": 0,
            "start_time": None,
            "end_time": None,
        }

        import time

        stats["start_time"] = time.time()

        # Pre-filter and process
        filtered_records = self.mapper.pre_filter_records(data_generator)

        # Process in streaming fashion
        for batch in self.mapper.process_batch_optimized(list(filtered_records)):
            stats["batches_processed"] += 1
            stats["total_records"] += len(batch)

            # Write batch
            write_callback(batch, output_file_path)
            stats["processed_records"] += len(batch)

        stats["end_time"] = time.time()
        stats["duration"] = stats["end_time"] - stats["start_time"]

        return stats

    def estimate_memory_usage(self, record_count: int) -> Dict[str, float]:
        """Estimate memory usage for a given number of records.

        Args:
            record_count: Number of records to process

        Returns:
            Memory usage estimates in MB
        """
        # Base estimates from profiling
        bytes_per_record = 1024  # Rough estimate
        batch_overhead = 1.5  # Batch processing overhead

        batch_size = self.mapper.batch_config.batch_size

        # Memory for batch processing
        batch_memory = (batch_size * bytes_per_record) / (1024 * 1024) * batch_overhead

        # Memory for streaming processing (minimal)
        streaming_memory = (bytes_per_record * 10) / (1024 * 1024)  # Only 10 records at a time

        return {
            "batch_processing_mb": batch_memory,
            "streaming_processing_mb": streaming_memory,
            "recommended_batch_size": min(
                batch_size,
                int(100 * 1024 * 1024 / bytes_per_record),  # Target 100MB per batch
            ),
        }
