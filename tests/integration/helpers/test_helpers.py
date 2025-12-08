"""Integration test helper functions"""

import time
import shutil
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd


def create_sample_csv(csv_path: Path, data_type: str, num_rows: int = 10) -> None:
    """Create a sample CSV file for testing"""
    if data_type == "transactions":
        data = {
            "id": [f"trans_{i}" for i in range(num_rows)],
            "name": [f"단지{i}" for i in range(num_rows)],
            "size": [84.5 + i for i in range(num_rows)],
            "floor": [i % 20 + 1 for i in range(num_rows)],
            "price": [50000 + i * 1000 for i in range(num_rows)],
            "contract_date": ["2024-01-01" for _ in range(num_rows)],
        }
    elif data_type == "complexes":
        data = {
            "id": [f"complex_{i}" for i in range(num_rows)],
            "name": [f"아파트{i}" for i in range(num_rows)],
            "address": [f"서울시 강남구 테헤란로 {i}" for i in range(num_rows)],
            "build_year": [2000 + i for i in range(num_rows)],
            "households": [100 + i * 10 for i in range(num_rows)],
        }
    else:
        raise ValueError(f"Unknown data type: {data_type}")

    df = pd.DataFrame(data)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)


def wait_for_file_creation(file_path: Path, timeout: float = 10.0) -> bool:
    """Wait for a file to be created"""
    start_time = time.time()
    while not file_path.exists():
        if time.time() - start_time > timeout:
            return False
        time.sleep(0.1)
    return True


def count_csv_rows(csv_path: Path) -> int:
    """Count rows in CSV file (excluding header)"""
    if not csv_path.exists():
        return 0

    with open(csv_path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f) - 1  # Subtract header


def verify_csv_structure(csv_path: Path, required_columns: List[str]) -> Dict[str, Any]:
    """Verify CSV file structure and return validation results"""
    result = {
        "exists": csv_path.exists(),
        "readable": False,
        "columns": [],
        "missing_columns": [],
        "row_count": 0,
        "is_empty": True,
        "errors": [],
    }

    if not result["exists"]:
        result["errors"].append(f"File not found: {csv_path}")
        return result

    try:
        df = pd.read_csv(csv_path)
        result["readable"] = True
        result["columns"] = df.columns.tolist()
        result["row_count"] = len(df)
        result["is_empty"] = df.empty

        missing = [col for col in required_columns if col not in df.columns]
        result["missing_columns"] = missing

        if missing:
            result["errors"].append(f"Missing required columns: {missing}")

    except Exception as e:
        result["errors"].append(f"Error reading CSV: {str(e)}")

    return result


def cleanup_test_files(test_dir: Path) -> None:
    """Clean up test files and directories"""
    if test_dir.exists():
        shutil.rmtree(test_dir)


class IntegrationTestContext:
    """Context manager for integration tests"""

    def __init__(self, test_name: str):
        self.test_name = test_name
        self.test_dir = Path("output") / "test-integration" / test_name
        self.csv_dir = self.test_dir / "csv"
        self.log_dir = self.test_dir / "logs"

    def __enter__(self):
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.csv_dir.mkdir(exist_ok=True)
        self.log_dir.mkdir(exist_ok=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup is optional - comment out if you want to keep files for debugging
        # cleanup_test_files(self.test_dir)
        pass
