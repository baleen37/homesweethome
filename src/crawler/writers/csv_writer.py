import csv
from pathlib import Path
from typing import Any

# Re-export for backward compatibility


class CSVWriter:
    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path

    def write(self, data: list[dict[str, Any]], mode: str = "w") -> None:
        """데이터를 CSV로 저장"""
        if not data:
            return

        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = data[0].keys()
        with open(self.output_path, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if mode == "w":
                writer.writeheader()
            writer.writerows(data)

    def append(self, data: list[dict[str, Any]]) -> None:
        """기존 파일에 추가"""
        self.write(data, mode="a")
