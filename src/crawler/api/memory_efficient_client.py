"""
Memory-efficient API client with connection pooling and response streaming.
"""

import gc
import json
import logging
import time
from typing import Any, Dict, Iterator, List, Optional
from dataclasses import dataclass
import asyncio
import aiohttp
from aiohttp import ClientTimeout, TCPConnector

from crawler.api.hogangnono_client import HogangnonoAPIClient
from crawler.utils.memory_profiler import CircularBuffer


@dataclass
class ClientConfig:
    """Configuration for memory-efficient API client."""

    max_concurrent_requests: int = 10
    request_timeout: float = 30.0
    connection_pool_size: int = 100
    keepalive_timeout: float = 30.0
    response_buffer_size: int = 8192
    enable_compression: bool = True
    max_response_size_mb: int = 50
    memory_threshold_mb: float = 500.0


class MemoryEfficientAPIClient:
    """Memory-efficient API client with streaming and connection pooling."""

    def __init__(
        self,
        config: Optional[ClientConfig] = None,
        base_client: Optional[HogangnonoAPIClient] = None,
    ):
        """Initialize the memory-efficient API client.

        Args:
            config: Client configuration
            base_client: Base API client instance
        """
        self.config = config or ClientConfig()
        self.base_client = base_client
        self.logger = logging.getLogger(__name__)

        # Initialize connection pool
        self._session = None
        self._connector = None

        # Response caching with circular buffer
        self._response_cache = CircularBuffer(max_size=1000)
        self._request_count = 0
        self._memory_usage_mb = 0.0

    async def __aenter__(self):
        """Async context manager entry."""
        await self._init_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _init_session(self) -> None:
        """Initialize aiohttp session with connection pooling."""
        self._connector = TCPConnector(
            limit=self.config.connection_pool_size,
            keepalive_timeout=self.config.keepalive_timeout,
            enable_cleanup_closed=True,
        )

        timeout = ClientTimeout(total=self.config.request_timeout)

        self._session = aiohttp.ClientSession(
            connector=self._connector,
            timeout=timeout,
            headers={"Accept-Encoding": "gzip, deflate"} if self.config.enable_compression else {},
        )

    async def close(self) -> None:
        """Close the session and cleanup resources."""
        if self._session:
            await self._session.close()
            self._session = None
        if self._connector:
            await self._connector.close()
            self._connector = None

    async def fetch_streaming(
        self, url: str, params: Optional[Dict[str, Any]] = None, chunk_size: int = 1024
    ) -> Iterator[Dict[str, Any]]:
        """Fetch API response in streaming fashion.

        Args:
            url: API endpoint URL
            params: Query parameters
            chunk_size: Size of response chunks to process

        Yields:
            Parsed JSON objects from the response
        """
        if not self._session:
            await self._init_session()

        try:
            async with self._session.get(url, params=params) as response:
                response.raise_for_status()

                # Check response size
                content_length = response.headers.get("content-length")
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb > self.config.max_response_size_mb:
                        self.logger.warning(
                            f"Response size {size_mb:.2f}MB exceeds threshold "
                            f"{self.config.max_response_size_mb}MB"
                        )

                # Stream response content
                buffer = ""
                async for chunk in response.content.iter_chunked(chunk_size):
                    buffer += chunk.decode("utf-8")

                    # Process complete JSON objects
                    while True:
                        try:
                            # Try to parse a complete JSON object
                            obj, idx = json.JSONDecoder().raw_decode(buffer)
                            yield obj
                            buffer = buffer[idx:].lstrip()
                        except json.JSONDecodeError:
                            # Incomplete JSON, wait for more data
                            break

                # Process any remaining data
                if buffer.strip():
                    try:
                        obj = json.loads(buffer)
                        yield obj
                    except json.JSONDecodeError:
                        self.logger.error(f"Failed to parse remaining data: {buffer[:100]}")

        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
            raise

    async def fetch_batch_concurrent(
        self, requests: List[Dict[str, Any]]
    ) -> Iterator[Dict[str, Any]]:
        """Fetch multiple API requests concurrently with controlled concurrency.

        Args:
            requests: List of request dictionaries with 'url' and 'params'

        Yields:
            Responses from the API
        """
        if not self._session:
            await self._init_session()

        semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)

        async def fetch_single(request):
            async with semaphore:
                return await self._fetch_single(request)

        # Create tasks for all requests
        tasks = [fetch_single(req) for req in requests]

        # Process results as they complete
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                yield result
            except Exception as e:
                self.logger.error(f"Error in concurrent request: {e}")

    async def _fetch_single(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch a single API request.

        Args:
            request: Request dictionary with 'url' and 'params'

        Returns:
            Parsed JSON response
        """
        url = request["url"]
        params = request.get("params")

        # Check cache first
        cache_key = f"{url}:{str(params)}"
        for cached_key, cached_response in self._response_cache:
            if cached_key == cache_key:
                self.logger.debug(f"Cache hit for {url}")
                return cached_response

        # Fetch from API
        async with self._session.get(url, params=params) as response:
            response.raise_for_status()

            # Stream response to minimize memory usage
            content = await response.text()

            # Parse JSON
            data = json.loads(content)

            # Cache response
            self._response_cache.append((cache_key, data))

            # Update metrics
            self._request_count += 1
            self._memory_usage_mb = self._estimate_memory_usage()

            # Check memory threshold
            if self._memory_usage_mb > self.config.memory_threshold_mb:
                self.logger.warning(
                    f"Memory usage {self._memory_usage_mb:.2f}MB exceeds threshold "
                    f"{self.config.memory_threshold_mb}MB"
                )
                # Force garbage collection
                gc.collect()

            return data

    def _estimate_memory_usage(self) -> float:
        """Estimate current memory usage in MB.

        Returns:
            Estimated memory usage in MB
        """
        # Rough estimation based on request count and cache size
        bytes_per_request = 1024  # Estimate
        cache_size = len(self._response_cache) * 2048  # Estimate

        total_bytes = (self._request_count * bytes_per_request) + cache_size
        return total_bytes / (1024 * 1024)

    async def process_large_dataset(
        self,
        base_url: str,
        params_generator: Iterator[Dict[str, Any]],
        process_func: callable,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """Process a large dataset in memory-efficient batches.

        Args:
            base_url: Base API URL
            params_generator: Generator yielding request parameters
            process_func: Function to process each response
            batch_size: Number of requests to process in each batch

        Returns:
            Processing statistics
        """
        stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "items_processed": 0,
            "start_time": time.time(),
            "end_time": None,
        }

        # Process in batches
        batch = []
        for params in params_generator:
            batch.append({"url": base_url, "params": params})
            stats["total_requests"] += 1

            if len(batch) >= batch_size:
                await self._process_batch(batch, process_func, stats)
                batch.clear()

                # Periodic cleanup
                if stats["total_requests"] % (batch_size * 10) == 0:
                    gc.collect()

        # Process remaining requests
        if batch:
            await self._process_batch(batch, process_func, stats)

        stats["end_time"] = time.time()
        stats["duration"] = stats["end_time"] - stats["start_time"]

        return stats

    async def _process_batch(
        self, batch: List[Dict[str, Any]], process_func: callable, stats: Dict[str, Any]
    ) -> None:
        """Process a batch of requests.

        Args:
            batch: Batch of requests to process
            process_func: Function to process responses
            stats: Statistics dictionary to update
        """
        async for response in self.fetch_batch_concurrent(batch):
            try:
                # Process response
                items_processed = await process_func(response)
                stats["successful_requests"] += 1
                stats["items_processed"] += items_processed

            except Exception as e:
                self.logger.error(f"Error processing response: {e}")
                stats["failed_requests"] += 1


class ResponseCache:
    """Memory-efficient response cache with LRU eviction."""

    def __init__(self, max_size: int = 1000, max_memory_mb: float = 100.0):
        """Initialize the response cache.

        Args:
            max_size: Maximum number of cached responses
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_size = max_size
        self.max_memory_mb = max_memory_mb
        self._cache = CircularBuffer(max_size)
        self._memory_usage = 0.0

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached response.

        Args:
            key: Cache key

        Returns:
            Cached response or None
        """
        for cached_key, cached_value in self._cache:
            if cached_key == key:
                return cached_value
        return None

    def put(self, key: str, value: Dict[str, Any]) -> None:
        """Cache a response.

        Args:
            key: Cache key
            value: Response to cache
        """
        # Estimate response size
        response_size = len(json.dumps(value).encode("utf-8"))
        response_size_mb = response_size / (1024 * 1024)

        # Check memory limit
        if self._memory_usage + response_size_mb > self.max_memory_mb:
            self._evict_oldest()

        # Add to cache
        self._cache.append((key, value))
        self._memory_usage += response_size_mb

    def _evict_oldest(self) -> None:
        """Evict oldest entries to free memory."""
        # Evict 10% of entries when memory limit is exceeded
        evict_count = max(1, self.max_size // 10)

        # Create new buffer with evicted entries removed
        new_buffer = CircularBuffer(self.max_size)
        items = list(self._cache)
        for key, value in items[evict_count:]:
            new_buffer.append((key, value))

        self._cache = new_buffer


# Utility function to create parameter generators
def create_params_generator(
    base_params: Dict[str, Any], varying_params: List[Dict[str, Any]]
) -> Iterator[Dict[str, Any]]:
    """Create a generator for API request parameters.

    Args:
        base_params: Base parameters for all requests
        varying_params: List of parameter variations

    Yields:
        Combined parameter dictionaries
    """
    for variation in varying_params:
        params = base_params.copy()
        params.update(variation)
        yield params
