import pandas as pd
from pathlib import Path
from typing import List


class DataValidator:
    """Validates crawled data integrity and format"""

    def __init__(self):
        self.required_columns = {
            "transactions": ["id", "name", "size", "floor", "price", "contract_date"],
            "complexes": ["id", "name", "address", "build_year", "households"],
        }

    def validate_csv_format(self, csv_path: Path, data_type: str) -> List[str]:
        """Validate CSV format and required columns"""
        errors = []

        if not csv_path.exists():
            errors.append(f"CSV file not found: {csv_path}")
            return errors

        try:
            df = pd.read_csv(csv_path)
            required = self.required_columns.get(data_type, [])
            missing = [col for col in required if col not in df.columns]

            if missing:
                errors.append(f"Missing required columns: {missing}")

            if df.empty:
                errors.append("CSV file is empty")

        except Exception as e:
            errors.append(f"Error reading CSV: {str(e)}")

        return errors
