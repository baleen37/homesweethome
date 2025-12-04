import json
from datetime import datetime
from pathlib import Path
from typing import Any


class CheckpointManager:
    def __init__(self, filepath: str) -> None:
        self.filepath = Path(filepath)
        self.checkpoint: dict[str, Any] = {
            "last_completed": {},
            "completed_dongs": [],
            "failed_dongs": [],
            "total_complexes_crawled": 0,
            "last_updated": None,
        }

    def load(self) -> dict[str, Any] | None:
        if not self.filepath.exists():
            return None

        with open(self.filepath) as f:
            self.checkpoint = json.load(f)
        return self.checkpoint

    def save(self, checkpoint: dict[str, Any]) -> None:
        self.checkpoint = checkpoint
        self.checkpoint["last_updated"] = datetime.now().isoformat()

        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump(self.checkpoint, f, indent=2, ensure_ascii=False)

    def should_skip_dong(self, cortar_no: str) -> bool:
        return cortar_no in self.checkpoint.get("completed_dongs", [])

    def add_failed_dong(self, dong: dict[str, Any], error: str) -> None:
        self.checkpoint.setdefault("failed_dongs", []).append(
            {
                "cortarNo": dong["cortarNo"],
                "dong_name": dong.get("dong_name", ""),
                "error": error,
                "timestamp": datetime.now().isoformat(),
            }
        )
