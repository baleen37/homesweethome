"""Common utilities for CSV writers."""

from typing import Any, Dict, List


def normalize_row_legacy(row: Dict[str, Any], fieldnames: List[str]) -> Dict[str, Any]:
    """Legacy normalization method for backward compatibility.

    This function provides a common implementation for normalizing rows
    across different CSV writers. It handles various data types and formats
    them appropriately for CSV output.

    Args:
        row: Raw data row to normalize
        fieldnames: List of field names to include in the output

    Returns:
        Normalized data row with all fields present
    """
    normalized = {}

    for field in fieldnames:
        value = row.get(field, "")

        # Handle different value types
        if value is None or value == "":
            normalized[field] = ""
        elif isinstance(value, bool):
            normalized[field] = str(value).lower()
        elif isinstance(value, (int, float)):
            # Format based on field name
            if any(keyword in field.lower() for keyword in ["가", "price", "amount", "fee"]):
                normalized[field] = f"{int(value):,}"
            elif "율" in field or "rate" in field.lower():
                normalized[field] = f"{float(value):.2f}"
            else:
                normalized[field] = str(value)
        else:
            normalized[field] = str(value)

    return normalized
