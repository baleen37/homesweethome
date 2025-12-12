"""
Optimized processor for handling large datasets efficiently.
"""

import gc
import logging
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing as mp

from crawler.data_mappers.memory_optimized_mapper import MemoryOptimizedMapper, BatchConfig
from crawler.writers.memory_optimized_csv_writer import MemoryOptimizedCSVWriter, ChunkedCSVWriter
from crawler.monitoring.performance_monitor import PerformanceMonitor
from crawler.utils.memory_profiler import check_memory_usage, force_garbage_collection


@dataclass
class ProcessingConfig:
    """Configuration for large dataset processing."""

    # Batch settings
    batch_size: int = 5000
    chunk_size: int = 10000
    parallel_workers: int = mp.cpu_count() - 1

    # Memory management
    memory_threshold_mb: float = 1000.0
    gc_frequency: int = 10  # Garbage collect every N batches
    checkpoint_frequency: int = 100  # Save checkpoint every N batches

    # I/O settings
    buffer_size: int = 32768  # 32KB buffer
    compression: bool = True
    max_file_size_mb: int = 500  # Split files if larger

    # Performance
    enable_monitoring: bool = True
    enable_parallel: bool = True


class LargeDatasetProcessor:
    """Optimized processor for handling large datasets efficiently."""

    def __init__(
        self, config: Optional[ProcessingConfig] = None, output_dir: Optional[Path] = None
    ):
        """Initialize the large dataset processor.

        Args:
            config: Processing configuration
            output_dir: Directory for output files
        """
        self.config = config or ProcessingConfig()
        self.output_dir = output_dir or Path("output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.mapper = MemoryOptimizedMapper(
            batch_config=BatchConfig(
                batch_size=self.config.batch_size,
                memory_threshold_mb=self.config.memory_threshold_mb,
            )
        )
        self.monitor = PerformanceMonitor() if self.config.enable_monitoring else None
        self.logger = logging.getLogger(__name__)

        # Processing state
        self._processing_stats = {
            "total_records": 0,
            "processed_records": 0,
            "failed_records": 0,
            "batches_processed": 0,
            "start_time": None,
            "end_time": None,
            "peak_memory_mb": 0.0,
            "files_created": [],
        }

    def process_large_dataset(
        self, data_source: Iterator[Dict[str, Any]], dataset_name: str
    ) -> Dict[str, Any]:
        """Process a large dataset with optimized memory usage.

        Args:
            data_source: Iterator of data records
            dataset_name: Name of the dataset

        Returns:
            Processing statistics
        """
        self.logger.info(f"Starting processing of large dataset: {dataset_name}")
        self._processing_stats["start_time"] = time.time()

        # Start monitoring if enabled
        if self.monitor:
            self.monitor.start_monitoring()

        try:
            # Process the dataset
            output_files = self._process_streaming(data_source, dataset_name)
            self._processing_stats["files_created"] = output_files

        except Exception as e:
            self.logger.error(f"Error processing dataset: {e}")
            raise

        finally:
            # Stop monitoring
            if self.monitor:
                monitor_stats = self.monitor.stop_monitoring()
                self._processing_stats["monitoring_stats"] = monitor_stats

            self._processing_stats["end_time"] = time.time()
            self._processing_stats["duration"] = (
                self._processing_stats["end_time"] - self._processing_stats["start_time"]
            )

        return self._generate_final_report()

    def _process_streaming(
        self, data_source: Iterator[Dict[str, Any]], dataset_name: str
    ) -> List[Path]:
        """Process dataset using streaming approach.

        Args:
            data_source: Iterator of data records
            dataset_name: Name of the dataset

        Returns:
            List of created output files
        """
        # Choose appropriate writer based on expected size
        if self._estimate_dataset_size(data_source) > 1000000:  # 1M+ records
            return self._process_with_chunking(data_source, dataset_name)
        else:
            return self._process_with_streaming(data_source, dataset_name)

    def _estimate_dataset_size(self, data_source: Iterator[Dict[str, Any]]) -> int:
        """Estimate the size of a dataset.

        Args:
            data_source: Iterator of data records

        Returns:
            Estimated number of records
        """
        # Sample first 1000 records to estimate
        sample_size = 0
        for i, record in enumerate(data_source):
            sample_size += 1
            if i >= 1000:
                break

        if sample_size == 0:
            return 0

        # Rough estimate based on sample
        # This is a simplification - real implementation would have better estimation
        return sample_size * 100  # Assume sample is 1% of total

    def _process_with_streaming(
        self, data_source: Iterator[Dict[str, Any]], dataset_name: str
    ) -> List[Path]:
        """Process dataset using memory-efficient streaming.

        Args:
            data_source: Iterator of data records
            dataset_name: Name of the dataset

        Returns:
            List of created output files
        """
        output_files = []

        # Create output file paths
        complexes_path = self.output_dir / f"{dataset_name}_complexes.csv"
        transactions_path = self.output_dir / f"{dataset_name}_transactions.csv"

        # Initialize writers
        if self.config.compression:
            complexes_path = complexes_path.with_suffix(".csv.gz")
            transactions_path = transactions_path.with_suffix(".csv.gz")

        # Process complexes data
        complexes_writer = MemoryOptimizedCSVWriter(
            complexes_path,
            csv_type="complexes",
            chunk_size=self.config.chunk_size,
            buffer_size=self.config.buffer_size,
        )

        # Filter and transform complexes
        complexes_data = self._filter_complexes(data_source)
        complexes_stats = complexes_writer.write_streaming(complexes_data)
        output_files.append(complexes_path)

        # Process transactions data
        transactions_writer = MemoryOptimizedCSVWriter(
            transactions_path,
            csv_type="transactions",
            chunk_size=self.config.chunk_size,
            buffer_size=self.config.buffer_size,
        )

        # Filter and transform transactions
        transactions_data = self._filter_transactions(data_source)
        transactions_stats = transactions_writer.write_streaming(transactions_data)
        output_files.append(transactions_path)

        # Update statistics
        self._processing_stats["processed_records"] += (
            complexes_stats["records_processed"] + transactions_stats["records_processed"]
        )
        self._processing_stats["batches_processed"] += (
            complexes_stats["chunks_written"] + transactions_stats["chunks_written"]
        )

        return output_files

    def _process_with_chunking(
        self, data_source: Iterator[Dict[str, Any]], dataset_name: str
    ) -> List[Path]:
        """Process very large dataset using file chunking.

        Args:
            data_source: Iterator of data records
            dataset_name: Name of the dataset

        Returns:
            List of created output files
        """
        output_files = []

        # Use chunked writer for very large datasets
        complexes_writer = ChunkedCSVWriter(
            self.output_dir / f"{dataset_name}_complexes.csv",
            csv_type="complexes",
            max_file_size_mb=self.config.max_file_size_mb,
        )

        transactions_writer = ChunkedCSVWriter(
            self.output_dir / f"{dataset_name}_transactions.csv",
            csv_type="transactions",
            max_file_size_mb=self.config.max_file_size_mb,
        )

        # Process in large chunks
        batch = []
        for record in data_source:
            batch.append(record)
            self._processing_stats["total_records"] += 1

            if len(batch) >= self.config.batch_size:
                self._process_batch(batch, complexes_writer, transactions_writer)
                batch.clear()

                # Periodic cleanup
                if self._processing_stats["batches_processed"] % self.config.gc_frequency == 0:
                    gc.collect()

                    # Check memory usage
                    if check_memory_usage(self.config.memory_threshold_mb):
                        self.logger.warning(
                            f"Memory usage exceeds {self.config.memory_threshold_mb}MB"
                        )
                        force_garbage_collection()

        # Process remaining records
        if batch:
            self._process_batch(batch, complexes_writer, transactions_writer)

        # Get all created files
        output_files.extend(complexes_writer.write_records(iter([])))
        output_files.extend(transactions_writer.write_records(iter([])))

        return output_files

    def _process_batch(
        self,
        batch: List[Dict[str, Any]],
        complexes_writer: ChunkedCSVWriter,
        transactions_writer: ChunkedCSVWriter,
    ) -> None:
        """Process a batch of records.

        Args:
            batch: Batch of records to process
            complexes_writer: Writer for complexes data
            transactions_writer: Writer for transactions data
        """
        self._processing_stats["batches_processed"] += 1

        # Separate complexes and transactions
        complexes_data = self._filter_complexes(iter(batch))
        transactions_data = self._filter_transactions(iter(batch))

        # Write to files
        complexes_writer.write_records(complexes_data)
        transactions_writer.write_records(transactions_data)

        self._processing_stats["processed_records"] += len(batch)

    def _filter_complexes(self, data_source: Iterator[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
        """Filter and transform complexes data.

        Args:
            data_source: Iterator of data records

        Yields:
            Complexes data records
        """
        seen_complexes = set()

        for record in data_source:
            # Extract complex information
            complex_id = record.get("일련번호", "")
            if complex_id and complex_id not in seen_complexes:
                seen_complexes.add(complex_id)

                # Transform to complexes format
                complex_record = {
                    "complex_id": complex_id,
                    "complex_name": record.get("아파트명", ""),
                    "address": record.get("법정동주소", ""),
                    "build_year": record.get("건축년도", ""),
                }

                yield complex_record

    def _filter_transactions(
        self, data_source: Iterator[Dict[str, Any]]
    ) -> Iterator[Dict[str, Any]]:
        """Filter and transform transaction data.

        Args:
            data_source: Iterator of data records

        Yields:
            Transaction data records
        """
        for record in data_source:
            # Transform to transaction format
            transaction_record = {
                "complex_id": record.get("일련번호", ""),
                "complex_name": record.get("아파트명", ""),
                "pyeong_type_number": str(int(float(record.get("전용면적", 0)) * 0.3025)),
                "trade_type": "A1",  # Assume sale
                "trade_date": f"{record.get('년', '')}-{record.get('월', '')}-{record.get('일', '')}",
                "trade_year": record.get("년", ""),
                "floor": record.get("층", ""),
                "deal_price": record.get("거래금액", "").replace(",", ""),
            }

            yield transaction_record

    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate final processing report.

        Returns:
            Processing statistics report
        """
        report = {
            "processing_stats": self._processing_stats,
            "performance_summary": {},
            "optimization_applied": {
                "memory_optimization": True,
                "streaming_processing": True,
                "batch_processing": True,
                "compression_enabled": self.config.compression,
                "parallel_processing": self.config.enable_parallel,
                "monitoring_enabled": self.config.enable_monitoring,
            },
        }

        # Add performance summary
        if self._processing_stats["duration"]:
            records_per_second = (
                self._processing_stats["processed_records"] / self._processing_stats["duration"]
            )
            report["performance_summary"] = {
                "records_per_second": records_per_second,
                "average_batch_time": (
                    self._processing_stats["duration"]
                    / max(1, self._processing_stats["batches_processed"])
                ),
                "throughput_mb_per_second": self._calculate_throughput(),
            }

        return report

    def _calculate_throughput(self) -> float:
        """Calculate data throughput in MB/s.

        Returns:
            Throughput in MB/s
        """
        if not self._processing_stats["files_created"]:
            return 0.0

        total_size = sum(
            file_path.stat().st_size if file_path.exists() else 0
            for file_path in self._processing_stats["files_created"]
        )

        duration = self._processing_stats["duration"] or 1.0
        return (total_size / (1024 * 1024)) / duration


# Utility functions for parallel processing
def parallel_map_data(
    data: List[Dict[str, Any]], map_func: callable, num_workers: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Apply mapping function to data in parallel.

    Args:
        data: List of data records
        map_func: Function to apply to each record
        num_workers: Number of worker processes

    Returns:
        List of mapped records
    """
    if not data:
        return []

    num_workers = num_workers or (mp.cpu_count() - 1)
    chunk_size = max(1, len(data) // num_workers)

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(map_func, chunk)
            for chunk in (data[i : i + chunk_size] for i in range(0, len(data), chunk_size))
        ]

        results = []
        for future in as_completed(futures):
            try:
                chunk_results = future.result()
                if chunk_results:
                    results.extend(chunk_results)
            except Exception as e:
                logging.error(f"Error in parallel mapping: {e}")

        return results


def create_data_generator(file_path: Path, chunk_size: int = 10000) -> Iterator[Dict[str, Any]]:
    """Create a memory-efficient data generator from file.

    Args:
        file_path: Path to data file
        chunk_size: Number of records to read at a time

    Yields:
        Data records
    """
    # Use pandas chunking for CSV files
    if file_path.suffix == ".csv":
        for chunk in pd.read_csv(file_path, chunksize=chunk_size):
            for _, row in chunk.iterrows():
                yield row.to_dict()

    # For JSON files, use streaming JSON parser
    elif file_path.suffix == ".json":
        import ijson

        with open(file_path, "rb") as f:
            for record in ijson.items(f, "item"):
                yield record

    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}")
