"""
Memory-optimized CSV writer for handling large datasets efficiently.
"""

import csv
import gc
import io
import logging
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from concurrent.futures import ThreadPoolExecutor
import threading

from crawler.writers.csv_header_standard import CSVType, HeaderStandard


class MemoryOptimizedCSVWriter:
    """Memory-optimized CSV writer using streaming and chunked writing."""

    def __init__(
        self,
        output_path: Path,
        csv_type: CSVType,
        chunk_size: int = 5000,
        buffer_size: int = 8192,
        parallel_writes: bool = False,
        max_workers: int = 2,
    ):
        """Initialize the memory-optimized CSV writer.

        Args:
            output_path: Path to output CSV file
            csv_type: Type of CSV to write
            chunk_size: Number of records to process in each chunk
            buffer_size: Size of write buffer in bytes
            parallel_writes: Whether to enable parallel writing
            max_workers: Number of worker threads for parallel writes
        """
        self.output_path = output_path
        self.csv_type = csv_type
        self.chunk_size = chunk_size
        self.buffer_size = buffer_size
        self.parallel_writes = parallel_writes
        self.max_workers = max_workers

        self.fieldnames = HeaderStandard.get_fieldnames(csv_type)
        self._lock = threading.Lock()
        self._write_buffer = io.StringIO()
        self._records_written = 0
        self._chunks_written = 0
        self.logger = logging.getLogger(__name__)

    def write_streaming(
        self, records: Iterator[Dict[str, Any]], transform_func: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Write records to CSV using streaming to minimize memory usage.

        Args:
            records: Iterator of records to write
            transform_func: Optional function to transform records

        Returns:
            Writing statistics
        """
        stats = {"records_processed": 0, "chunks_written": 0, "bytes_written": 0, "errors": 0}

        # Create file with optimal settings
        with open(
            self.output_path, "w", newline="", encoding="utf-8", buffering=self.buffer_size
        ) as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames, extrasaction="ignore")

            # Write header
            writer.writeheader()
            stats["bytes_written"] = csvfile.tell()

            # Process records in chunks
            chunk = []
            for record in records:
                try:
                    # Apply transformation if provided
                    if transform_func:
                        record = transform_func(record)

                    chunk.append(record)
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
                    self.logger.error(f"Error writing record: {e}")
                    stats["errors"] += 1
                    continue

            # Write remaining records
            if chunk:
                self._write_chunk(writer, chunk)
                stats["chunks_written"] += 1
                stats["bytes_written"] = csvfile.tell()

        self._records_written = stats["records_processed"]
        self._chunks_written = stats["chunks_written"]

        return stats

    def _write_chunk(self, writer: csv.DictWriter, chunk: List[Dict[str, Any]]) -> None:
        """Write a chunk of records to CSV.

        Args:
            writer: CSV writer instance
            chunk: Chunk of records to write
        """
        # Validate and normalize records
        valid_records = []
        for record in chunk:
            # Ensure all required fields are present
            normalized = {}
            for field in self.fieldnames:
                normalized[field] = record.get(field, "")
            valid_records.append(normalized)

        # Write all records in chunk
        writer.writerows(valid_records)

    def write_parallel(
        self, records: Iterator[Dict[str, Any]], transform_func: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Write records using parallel processing for better performance.

        Args:
            records: Iterator of records to write
            transform_func: Optional function to transform records

        Returns:
            Writing statistics
        """
        if not self.parallel_writes:
            return self.write_streaming(records, transform_func)

        stats = {"records_processed": 0, "chunks_written": 0, "bytes_written": 0, "errors": 0}

        # Create temporary files for parallel writing
        temp_files = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Split records into chunks for parallel processing
            futures = []
            chunk = []
            chunk_id = 0

            for record in records:
                try:
                    if transform_func:
                        record = transform_func(record)

                    chunk.append(record)
                    stats["records_processed"] += 1

                    if len(chunk) >= self.chunk_size:
                        temp_path = self.output_path.with_suffix(f".tmp_{chunk_id}.csv")
                        temp_files.append(temp_path)

                        future = executor.submit(self._write_chunk_to_file, temp_path, chunk)
                        futures.append(future)

                        chunk = []
                        chunk_id += 1

                except Exception as e:
                    self.logger.error(f"Error processing record: {e}")
                    stats["errors"] += 1
                    continue

            # Process remaining records
            if chunk:
                temp_path = self.output_path.with_suffix(f".tmp_{chunk_id}.csv")
                temp_files.append(temp_path)

                future = executor.submit(self._write_chunk_to_file, temp_path, chunk)
                futures.append(future)

            # Wait for all chunks to be written
            for future in futures:
                future.result()

        # Merge all temporary files
        self._merge_temp_files(temp_files, stats)

        # Clean up temporary files
        for temp_path in temp_files:
            temp_path.unlink(missing_ok=True)

        return stats

    def _write_chunk_to_file(self, file_path: Path, chunk: List[Dict[str, Any]]) -> None:
        """Write a chunk of records to a temporary file.

        Args:
            file_path: Path to temporary file
            chunk: Chunk of records to write
        """
        with open(
            file_path, "w", newline="", encoding="utf-8", buffering=self.buffer_size
        ) as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames, extrasaction="ignore")

            # Write chunk (no header for temp files)
            self._write_chunk(writer, chunk)

    def _merge_temp_files(self, temp_files: List[Path], stats: Dict[str, Any]) -> None:
        """Merge temporary files into final output.

        Args:
            temp_files: List of temporary file paths
            stats: Statistics dictionary to update
        """
        with open(
            self.output_path, "w", newline="", encoding="utf-8", buffering=self.buffer_size
        ) as outfile:
            writer = csv.DictWriter(outfile, fieldnames=self.fieldnames, extrasaction="ignore")

            # Write header
            writer.writeheader()

            # Merge all temp files
            for temp_path in temp_files:
                with open(temp_path, "r", encoding="utf-8") as infile:
                    # Copy content line by line to minimize memory usage
                    for line in infile:
                        outfile.write(line)

                stats["chunks_written"] += 1
                stats["bytes_written"] = outfile.tell()

    def write_batch_compressed(
        self, records: Iterator[Dict[str, Any]], compression_level: int = 6
    ) -> Dict[str, Any]:
        """Write records with on-the-fly compression.

        Args:
            records: Iterator of records to write
            compression_level: Compression level (1-9)

        Returns:
            Writing statistics
        """
        import gzip

        output_path = self.output_path.with_suffix(".csv.gz")
        stats = {
            "records_processed": 0,
            "chunks_written": 0,
            "bytes_written": 0,
            "errors": 0,
            "compression_ratio": 0.0,
        }

        # Write compressed CSV
        with gzip.open(
            output_path, "wt", encoding="utf-8", compresslevel=compression_level
        ) as gzipfile:
            writer = csv.DictWriter(gzipfile, fieldnames=self.fieldnames, extrasaction="ignore")

            # Write header
            writer.writeheader()

            # Process records in chunks
            chunk = []
            for record in records:
                try:
                    chunk.append(record)
                    stats["records_processed"] += 1

                    if len(chunk) >= self.chunk_size:
                        self._write_chunk(writer, chunk)
                        stats["chunks_written"] += 1
                        chunk.clear()

                        gc.collect()

                except Exception as e:
                    self.logger.error(f"Error writing record: {e}")
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

        return stats

    def get_memory_estimate(self, record_count: int) -> Dict[str, float]:
        """Estimate memory usage for writing records.

        Args:
            record_count: Number of records to write

        Returns:
            Memory usage estimates in MB
        """
        # Estimates based on profiling
        bytes_per_record = 200  # Average record size
        chunk_memory = (self.chunk_size * bytes_per_record) / (1024 * 1024)
        buffer_memory = self.buffer_size / (1024 * 1024)

        return {
            "chunk_memory_mb": chunk_memory,
            "buffer_memory_mb": buffer_memory,
            "total_estimated_mb": chunk_memory + buffer_memory,
            "recommended_chunk_size": min(
                self.chunk_size,
                int(50 * 1024 * 1024 / bytes_per_record),  # Target 50MB per chunk
            ),
        }

    @property
    def records_written(self) -> int:
        """Get total number of records written."""
        return self._records_written

    @property
    def chunks_written(self) -> int:
        """Get number of chunks written."""
        return self._chunks_written


class ChunkedCSVWriter:
    """Alternative implementation using file chunks for very large datasets."""

    def __init__(self, output_path: Path, csv_type: CSVType, max_file_size_mb: int = 100):
        """Initialize chunked CSV writer.

        Args:
            output_path: Base path for output files
            csv_type: Type of CSV to write
            max_file_size_mb: Maximum size per file chunk
        """
        self.output_path = output_path
        self.csv_type = csv_type
        self.max_file_size_mb = max_file_size_mb
        self.fieldnames = HeaderStandard.get_fieldnames(csv_type)
        self._current_file = None
        self._current_writer = None
        self._file_counter = 0
        self._records_in_file = 0

    def write_records(self, records: Iterator[Dict[str, Any]]) -> List[Path]:
        """Write records split into multiple files.

        Args:
            records: Iterator of records to write

        Returns:
            List of created file paths
        """
        created_files = []

        for record in records:
            # Check if we need a new file
            if self._should_create_new_file():
                self._create_new_file()
                created_files.append(self._current_file)

            # Write record
            try:
                normalized = {field: record.get(field, "") for field in self.fieldnames}
                self._current_writer.writerow(normalized)
                self._records_in_file += 1
            except Exception as e:
                logging.error(f"Error writing record: {e}")

        # Close current file
        if self._current_file:
            self._current_file.close()
            self._current_file = None
            self._current_writer = None

        return created_files

    def _should_create_new_file(self) -> bool:
        """Check if a new file should be created."""
        if self._current_file is None:
            return True

        # Check file size
        self._current_file.flush()
        size_mb = self._current_file.tell() / (1024 * 1024)
        return size_mb >= self.max_file_size_mb

    def _create_new_file(self) -> None:
        """Create a new output file."""
        # Close existing file
        if self._current_file:
            self._current_file.close()

        # Create new file name
        self._file_counter += 1
        file_path = self.output_path.with_suffix(f".part{self._file_counter:03d}.csv")

        # Open new file
        self._current_file = open(file_path, "w", newline="", encoding="utf-8")
        self._current_writer = csv.DictWriter(
            self._current_file, fieldnames=self.fieldnames, extrasaction="ignore"
        )

        # Write header if first file
        if self._file_counter == 1:
            self._current_writer.writeheader()

        self._records_in_file = 0
