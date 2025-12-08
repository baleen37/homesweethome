import csv
from pathlib import Path
from typing import Any

# Re-export for backward compatibility


class CSVWriter:
    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path

    def write(self, data: list[dict[str, Any]], mode: str = "w", write_header: bool = True) -> None:
        """데이터를 CSV로 저장"""
        if not data:
            return

        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # 데이터를 CSV 호환 형식으로 변환
        normalized_data = []
        for item in data:
            normalized_item = {}
            for key, value in item.items():
                if isinstance(value, bool):
                    normalized_item[key] = str(value).lower()
                elif isinstance(value, (int, float)):
                    normalized_item[key] = value
                else:
                    normalized_item[key] = str(value) if value is not None else ""
            normalized_data.append(normalized_item)

        fieldnames = normalized_data[0].keys()
        with open(self.output_path, mode, newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if mode == "w" and write_header:
                writer.writeheader()
            writer.writerows(normalized_data)

    def append(self, data: list[dict[str, Any]]) -> None:
        """기존 파일에 추가"""
        self.write(data, mode="a", write_header=False)
