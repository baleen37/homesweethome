import json
from datetime import datetime
from pathlib import Path
from typing import Any


class CheckpointManager:
    """단순화된 체크포인트 관리자

    마지막으로 완료한 동과 실패한 동 목록만 추적
    """

    def __init__(self, checkpoint_path: str) -> None:
        self.filepath = Path(checkpoint_path)
        self.checkpoint: dict[str, Any] = {
            "last_dong": None,  # 마지막으로 완료한 동 코드
            "last_complex": None,  # 마지막으로 처리한 단지 ID (선택적)
            "failed_dongs": [],  # 실패한 동 코드 목록
            "last_updated": None,
        }

    def load(self) -> dict[str, Any] | None:
        """체크포인트 파일 로드"""
        if not self.filepath.exists():
            return None

        try:
            with open(self.filepath) as f:
                loaded_checkpoint = json.load(f)
                self.checkpoint.update(loaded_checkpoint)
            return self.checkpoint
        except (json.JSONDecodeError, KeyError) as e:
            # 손상된 파일은 무시
            return None

    def save(self, last_dong: str, last_complex: str | None = None) -> None:
        """체크포인트 저장

        Args:
            last_dong: 완료한 동 코드
            last_complex: 마지막으로 처리한 단지 ID (선택)
        """
        self.checkpoint["last_dong"] = last_dong
        if last_complex:
            self.checkpoint["last_complex"] = last_complex
        self.checkpoint["last_updated"] = datetime.now().isoformat()

        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump(self.checkpoint, f, indent=2, ensure_ascii=False)

    def should_skip_dong(self, dong_code: str) -> bool:
        """동이 이미 완료되었는지 확인

        체크포인트에 저장된 last_dong까지는 건너뛰고,
        그 다음 동부터 시작
        """
        last_dong = self.checkpoint.get("last_dong")
        if last_dong is None:
            return False

        # last_dong 이전의 모든 동은 건너뛰기
        # 실제로는 last_dong을 찾을 때까지 모든 동을 스킵해야 하므로,
        # crawl() 메서드에서 별도 로직으로 처리
        return False

    def should_skip_complex(self, dong_code: str, complex_id: str) -> bool:
        """단지가 이미 처리되었는지 확인 (현재는 미사용)"""
        # 현재 구현에서는 단지 레벨 체크포인트 미사용
        return False

    def add_failed_dong(self, dong_code: str, error: str) -> None:
        """실패한 동 추가"""
        failed_entry = {
            "dong_code": dong_code,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }

        # 중복 방지
        failed_dongs = self.checkpoint.get("failed_dongs", [])
        if not any(entry["dong_code"] == dong_code for entry in failed_dongs):
            failed_dongs.append(failed_entry)
            self.checkpoint["failed_dongs"] = failed_dongs

            # 즉시 저장
            self.checkpoint["last_updated"] = datetime.now().isoformat()
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, "w") as f:
                json.dump(self.checkpoint, f, indent=2, ensure_ascii=False)