"""
Error injection utilities for testing stability and error recovery
"""

import random
import time
from typing import Any, Callable, Dict
from unittest.mock import Mock


class ErrorInjector:
    """Inject various types of errors into functions for testing"""

    def __init__(self):
        self.error_config: Dict[str, Any] = {}
        self.call_count: Dict[str, int] = {}

    def configure_error(self, func_name: str, error_type: str, **kwargs):
        """Configure an error to inject for a specific function"""
        self.error_config[func_name] = {"type": error_type, "params": kwargs}
        self.call_count[func_name] = 0

    def should_inject_error(self, func_name: str) -> bool:
        """Check if error should be injected based on configuration"""
        if func_name not in self.error_config:
            return False

        config = self.error_config[func_name]
        self.call_count[func_name] += 1

        # Check probability
        if "probability" in config["params"]:
            if random.random() > config["params"]["probability"]:
                return False

        # Check call count conditions
        if "after_calls" in config["params"]:
            if self.call_count[func_name] <= config["params"]["after_calls"]:
                return False

        if "every_n_calls" in config["params"]:
            if self.call_count[func_name] % config["params"]["every_n_calls"] != 0:
                return False

        return True

    def inject_error(self, func_name: str):
        """Inject the configured error"""
        if func_name not in self.error_config:
            return

        config = self.error_config[func_name]
        error_type = config["type"]

        if error_type == "timeout":
            raise TimeoutError("Simulated timeout")
        elif error_type == "connection_error":
            raise ConnectionError("Simulated connection error")
        elif error_type == "rate_limit":
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.text = "Rate limit exceeded"
            return mock_response
        elif error_type == "server_error":
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal server error"
            return mock_response
        elif error_type == "memory_error":
            raise MemoryError("Simulated memory error")
        elif error_type == "delay":
            delay = config["params"].get("duration", 1)
            time.sleep(delay)
        else:
            raise RuntimeError(f"Unknown error type: {error_type}")


def inject_network_errors(func: Callable) -> Callable:
    """Decorator to inject network errors into API calls"""

    def wrapper(*args, **kwargs):
        # Simulate occasional network errors
        if random.random() < 0.1:  # 10% chance
            error_types = [
                ConnectionError("Network unreachable"),
                TimeoutError("Request timed out"),
                ConnectionResetError("Connection reset"),
            ]
            raise random.choice(error_types)

        return func(*args, **kwargs)

    return wrapper


def create_failing_api_client():
    """Create a mock API client that fails according to configuration"""
    injector = ErrorInjector()

    # Configure some errors
    injector.configure_error("get", "rate_limit", probability=0.2, after_calls=3)
    injector.configure_error("get", "timeout", probability=0.1)
    injector.configure_error("get", "server_error", probability=0.05, every_n_calls=10)

    class FailingAPIClient:
        def __init__(self):
            self.injector = injector

        def get(self, url, params=None):
            if self.injector.should_inject_error("get"):
                return self.injector.inject_error("get")

            # Return successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": []}
            return mock_response

    return FailingAPIClient()


def simulate_memory_leak():
    """Simulate a memory leak for testing"""
    leaky_data = []

    def add_data(size_mb=1):
        """Add data to simulate memory leak"""
        # Create data approximately size_mb MB
        data = b"x" * (1024 * 1024 * size_mb)
        leaky_data.append(data)
        return len(leaky_data)

    def get_leak_size():
        """Get current leak size in MB"""
        return len(leaky_data)

    return add_data, get_leak_size


class ChaosMonkey:
    """Inject random chaos into the system for testing"""

    def __init__(self):
        self.enabled = False
        self.chance = 0.05  # 5% chance of chaos

    def enable(self):
        """Enable chaos injection"""
        self.enabled = True

    def disable(self):
        """Disable chaos injection"""
        self.enabled = False

    def maybe_inject_chaos(self):
        """Maybe inject chaos if enabled"""
        if not self.enabled:
            return

        if random.random() < self.chance:
            chaos_type = random.choice([self._inject_delay, self._inject_gc, self._inject_high_cpu])
            chaos_type()

    def _inject_delay(self):
        """Inject random delay"""
        time.sleep(random.uniform(0.1, 0.5))

    def _inject_gc(self):
        """Force garbage collection"""
        import gc

        gc.collect()

    def _inject_high_cpu(self):
        """Consume CPU for a short time"""
        start = time.time()
        while time.time() - start < 0.1:
            _ = sum(i * i for i in range(1000))
