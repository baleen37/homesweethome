"""Streaming CSV writer for large datasets.

This module provides StreamingCSVWriter that combines functionality from
MemoryOptimizedCSVWriter and ChunkedCSVWriter for efficient handling of
large datasets.
"""

import csv
import gc
import gzip
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Callable
import threading
import structlog

from crawler.writers.unified_csv_writer import UnifiedCSVWriter, WriteConfig
from crawler.writers.data_transformation_strategy import DataTransformationStrategy
from crawler.writers.csv_header_standard import CSVType

logger = structlog.get_logger().bind(component="StreamingCSVWriter")


class StreamingCSVWriter(UnifiedCSVWriter):
    """Memory-efficient CSV writer for large datasets.

    Features:
    - Streaming writes to minimize memory usage
    - Chunked processing with configurable sizes
    - Parallel writing support
    - On-the-fly compression
    - File splitting for very large datasets
    """

    def __init__(
        self,
        output_path: Path,
        strategy: Optional[DataTransformationStrategy] = None,
        csv_type: Optional[CSVType] = None,
        config: Optional[WriteConfig] = None,
        chunk_size: int = 5000,
        max_file_size_mb: int = 100,
        enable_parallel: bool = False,
        max_workers: int = 2,
    ):
        """Initialize StreamingCSVWriter.

        Args:
            output_path: Path to the output CSV file
            strategy: Data transformation strategy
            csv_type: Type of CSV for header standardization
            config: Write configuration
            chunk_size: Number of records per chunk
            max_file_size_mb: Maximum file size before splitting
            enable_parallel: Enable parallel processing
            max_workers: Number of worker threads
        """
        # Override config for streaming
        streaming_config = config or WriteConfig()
        streaming_config.buffer_size = max(streaming_config.buffer_size, 8192)

        super().__init__(
            output_path=output_path,
            strategy=strategy,
            csv_type=csv_type,
            config=streaming_config,
        )

        self.chunk_size = chunk_size
        self.max_file_size_mb = max_file_size_mb
        self.enable_parallel = enable_parallel
        self.max_workers = max_workers
        self._lock = threading.Lock()

    def write_streaming(
        self,
        records: Iterator[Dict[str, Any]],
        transform_func: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Write records using streaming to minimize memory usage.

        Args:
            records: Iterator of records to write
            transform_func: Optional custom transformation function

        Returns:
            Writing statistics
        """
        stats = {
            "records_processed": 0,
            "chunks_written": 0,
            "bytes_written": 0,
            "errors": 0,
            "files_created": [],
        }

        # Get fieldnames
        fieldnames = self.get_fieldnames()

        # Ensure directory exists
        self._ensure_directory()

        # Create file with optimal settings
        with open(
            self.output_path,
            "w",
            newline="",
            encoding=self.config.encoding,
            buffering=self.config.buffer_size,
        ) as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=fieldnames,
                delimiter=self.config.delimiter,
                quotechar=self.config.quotechar,
                quoting=self.config.quoting,
            )

            # Write header
            writer.writeheader()
            stats["bytes_written"] = csvfile.tell()

            # Process records in chunks
            chunk = []
            for record in records:
                try:
                    # Apply custom transformation if provided
                    if transform_func:
                        record = transform_func(record)

                    # Apply strategy transformation
                    if self._strategy:
                        transformed = self._strategy.transform(record, fieldnames)
                    else:
                        transformed = self._normalize_row_legacy(record, fieldnames)

                    chunk.append(transformed)
                    stats["records_processed"] += 1

                    # Write chunk when full
                    if len(chunk) >= self.chunk_size:
                        self._write_chunk(writer, chunk)
                        stats["chunks_written"] += 1
                        stats["bytes_written"] = csvfile.tell()
                        chunk.clear()

                        # Periodic garbage collection
                        if stats["chunks_written"] % 10 == 0:
                            gc.collect()

                except Exception as e:
                    logger.error("error_writing_record", error=str(e))
                    stats["errors"] += 1
                    continue

            # Write remaining records
            if chunk:
                self._write_chunk(writer, chunk)
                stats["chunks_written"] += 1
                stats["bytes_written"] = csvfile.tell()

        stats["files_created"].append(str(self.output_path))

        # Update internal stats
        self.stats.update(stats)

        return stats

    def write_parallel(
        self,
        records: Iterator[Dict[str, Any]],
        transform_func: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Write records using parallel processing.

        Args:
            records: Iterator of records to write
            transform_func: Optional custom transformation function

        Returns:
            Writing statistics
        """
        if not self.enable_parallel:
            return self.write_streaming(records, transform_func)

        stats = {
            "records_processed": 0,
            "chunks_written": 0,
            "bytes_written": 0,
            "errors": 0,
            "files_created": [],
        }

        # Create temporary files for parallel processing
        temp_files = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Split records into chunks
            futures = []
            chunk = []
            chunk_id = 0

            for record in records:
                try:
                    # Apply transformations
                    if transform_func:
                        record = transform_func(record)

                    chunk.append(record)
                    stats["records_processed"] += 1

                    if len(chunk) >= self.chunk_size:
                        temp_path = self.output_path.with_suffix(f".tmp_{chunk_id}.csv")
                        temp_files.append(temp_path)

                        future = executor.submit(
                            self._write_chunk_to_file,
                            temp_path,
                            chunk,
                        )
                        futures.append(future)

                        chunk = []
                        chunk_id += 1

                except Exception as e:
                    logger.error("error_processing_record", error=str(e))
                    stats["errors"] += 1
                    continue

            # Process remaining records
            if chunk:
                temp_path = self.output_path.with_suffix(f".tmp_{chunk_id}.csv")
                temp_files.append(temp_path)

                future = executor.submit(
                    self._write_chunk_to_file,
                    temp_path,
                    chunk,
                )
                futures.append(future)

            # Wait for all chunks to be written
            for future in futures:
                future.result()

        # Merge all temporary files
        self._merge_temp_files(temp_files, stats)

        # Clean up temporary files
        for temp_path in temp_files:
            temp_path.unlink(missing_ok=True)

        stats["files_created"].append(str(self.output_path))

        # Update internal stats
        self.stats.update(stats)

        return stats

    def write_compressed(
        self,
        records: Iterator[Dict[str, Any]],
        compression_level: int = 6,
        transform_func: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Write records with on-the-fly compression.

        Args:
            records: Iterator of records to write
            compression_level: Compression level (1-9)
            transform_func: Optional custom transformation function

        Returns:
            Writing statistics
        """
        output_path = self.output_path.with_suffix(".csv.gz")
        stats = {
            "records_processed": 0,
            "chunks_written": 0,
            "bytes_written": 0,
            "errors": 0,
            "compression_ratio": 0.0,
            "files_created": [],
        }

        # Get fieldnames
        fieldnames = self.get_fieldnames()

        # Write compressed CSV
        with gzip.open(
            output_path,
            "wt",
            encoding=self.config.encoding,
            compresslevel=compression_level,
        ) as gzipfile:
            writer = csv.DictWriter(
                gzipfile,
                fieldnames=fieldnames,
                delimiter=self.config.delimiter,
                quotechar=self.config.quotechar,
                quoting=self.config.quoting,
            )

            # Write header
            writer.writeheader()

            # Process records in chunks
            chunk = []
            for record in records:
                try:
                    # Apply transformations
                    if transform_func:
                        record = transform_func(record)

                    if self._strategy:
                        transformed = self._strategy.transform(record, fieldnames)
                    else:
                        transformed = self._normalize_row_legacy(record, fieldnames)

                    chunk.append(transformed)
                    stats["records_processed"] += 1

                    if len(chunk) >= self.chunk_size:
                        self._write_chunk(writer, chunk)
                        stats["chunks_written"] += 1
                        chunk.clear()

                        gc.collect()

                except Exception as e:
                    logger.error("error_writing_compressed", error=str(e))
                    stats["errors"] += 1
                    continue

            # Write remaining records
            if chunk:
                self._write_chunk(writer, chunk)
                stats["chunks_written"] += 1

        # Calculate compression ratio
        if output_path.exists():
            compressed_size = output_path.stat().st_size
            estimated_uncompressed = stats["records_processed"] * 200  # Rough estimate
            stats["compression_ratio"] = compressed_size / estimated_uncompressed
            stats["bytes_written"] = compressed_size

        stats["files_created"].append(str(output_path))

        # Update internal stats
        self.stats.update(stats)

        return stats

    def write_split_files(
        self,
        records: Iterator[Dict[str, Any]],
        transform_func: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Write records split into multiple files.

        Args:
            records: Iterator of records to write
            transform_func: Optional custom transformation function

        Returns:
            Writing statistics with list of created files
        """
        stats = {
            "records_processed": 0,
            "files_created": [],
            "errors": 0,
        }

        # Get fieldnames
        fieldnames = self.get_fieldnames()

        # Create base filename without extension
        base_path = self.output_path.with_suffix("")
        file_counter = 0
        records_in_file = 0
        current_file = None
        current_writer = None

        try:
            for record in records:
                # Check if we need a new file
                if current_file is None or records_in_file >= self.chunk_size:
                    # Close current file
                    if current_file:
                        current_file.close()
                        stats["files_created"].append(str(current_file.name))

                    # Create new file
                    file_counter += 1
                    file_path = base_path.with_suffix(f".part{file_counter:03d}.csv")
                    current_file = open(
                        file_path,
                        "w",
                        newline="",
                        encoding=self.config.encoding,
                        buffering=self.config.buffer_size,
                    )
                    current_writer = csv.DictWriter(
                        current_file,
                        fieldnames=fieldnames,
                        delimiter=self.config.delimiter,
                        quotechar=self.config.quotechar,
                        quoting=self.config.quoting,
                    )
                    current_writer.writeheader()
                    records_in_file = 0

                # Apply transformations and write
                try:
                    if transform_func:
                        record = transform_func(record)

                    if self._strategy:
                        transformed = self._strategy.transform(record, fieldnames)
                    else:
                        transformed = self._normalize_row_legacy(record, fieldnames)

                    current_writer.writerow(transformed)
                    records_in_file += 1
                    stats["records_processed"] += 1

                except Exception as e:
                    logger.error("error_writing_split_file", error=str(e))
                    stats["errors"] += 1
                    continue

            # Close final file
            if current_file:
                current_file.close()
                stats["files_created"].append(str(current_file.name))

        except Exception:
            # Ensure file is closed on error
            if current_file:
                current_file.close()
            raise

        # Update internal stats
        self.stats.update(stats)

        return stats

    def _write_chunk(
        self,
        writer: csv.DictWriter,
        chunk: List[Dict[str, Any]],
    ) -> None:
        """Write a chunk of records."""
        writer.writerows(chunk)

    def _write_chunk_to_file(
        self,
        file_path: Path,
        chunk: List[Dict[str, Any]],
    ) -> None:
        """Write a chunk to a temporary file."""
        fieldnames = self.get_fieldnames()

        with open(
            file_path,
            "w",
            newline="",
            encoding=self.config.encoding,
            buffering=self.config.buffer_size,
        ) as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=fieldnames,
                delimiter=self.config.delimiter,
                quotechar=self.config.quotechar,
                quoting=self.config.quoting,
            )

            # Write chunk (no header for temp files)
            self._write_chunk(writer, chunk)

    def _merge_temp_files(
        self,
        temp_files: List[Path],
        stats: Dict[str, Any],
    ) -> None:
        """Merge temporary files into final output."""
        fieldnames = self.get_fieldnames()

        with open(
            self.output_path,
            "w",
            newline="",
            encoding=self.config.encoding,
            buffering=self.config.buffer_size,
        ) as outfile:
            writer = csv.DictWriter(
                outfile,
                fieldnames=fieldnames,
                delimiter=self.config.delimiter,
                quotechar=self.config.quotechar,
                quoting=self.config.quoting,
            )

            # Write header
            writer.writeheader()

            # Merge all temp files
            for temp_path in temp_files:
                with open(temp_path, "r", encoding=self.config.encoding) as infile:
                    # Copy content line by line to minimize memory usage
                    for line in infile:
                        outfile.write(line)

                stats["chunks_written"] += 1
                stats["bytes_written"] = outfile.tell()

    def estimate_memory_usage(self, record_count: int) -> Dict[str, float]:
        """Estimate memory usage for writing records.

        Args:
            record_count: Number of records to write

        Returns:
            Memory usage estimates in MB
        """
        # Estimates based on profiling
        bytes_per_record = 200  # Average record size
        chunk_memory = (self.chunk_size * bytes_per_record) / (1024 * 1024)
        buffer_memory = self.config.buffer_size / (1024 * 1024)

        return {
            "chunk_memory_mb": chunk_memory,
            "buffer_memory_mb": buffer_memory,
            "total_estimated_mb": chunk_memory + buffer_memory,
            "recommended_chunk_size": min(
                self.chunk_size,
                int(50 * 1024 * 1024 / bytes_per_record),  # Target 50MB per chunk
            ),
        }
