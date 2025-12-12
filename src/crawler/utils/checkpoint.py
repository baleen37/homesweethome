"""단순화된 체크포인트 관리자

완료된 구/군 목록만 텍스트 파일에 저장합니다.
한 줄에 하나의 구/군 이름이 기록됩니다.
"""

from pathlib import Path
from typing import Set

import structlog

logger = structlog.get_logger()


class SimpleCheckpointManager:
    """단순화된 체크포인트 관리자

    완료된 구/군 목록만 텍스트 파일에 저장하고 관리합니다.
    """

    def __init__(self, checkpoint_path: str):
        """SimpleCheckpointManager 초기화

        Args:
            checkpoint_path: 체크포인트 파일 경로 (.txt 확장자 권장)
        """
        self.checkpoint_path = Path(checkpoint_path)
        self._ensure_directory_exists()

    def _ensure_directory_exists(self) -> None:
        """체크포인트 디렉토리 생성"""
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    def add_completed_district(self, district_name: str) -> None:
        """완료된 구/군 추가

        Args:
            district_name: 완료된 구/군 이름
        """
        if not district_name or district_name.strip() == "":
            return

        district_name = district_name.strip()
        completed = self.get_completed_districts()

        if district_name not in completed:
            try:
                with open(self.checkpoint_path, "a", encoding="utf-8") as f:
                    f.write(f"{district_name}\n")
                logger.info("district_added_to_checkpoint", district=district_name)
            except IOError as e:
                logger.error("failed_to_save_checkpoint", error=str(e))
                raise

    def get_completed_districts(self) -> Set[str]:
        """완료된 구/군 목록 반환

        Returns:
            완료된 구/군 이름 집합
        """
        if not self.checkpoint_path.exists():
            return set()

        try:
            with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                completed = set()
                for line in f:
                    line = line.strip()
                    if line:  # 빈 줄 무시
                        completed.add(line)
                return completed
        except IOError as e:
            logger.error("failed_to_load_checkpoint", error=str(e))
            return set()

    def is_district_completed(self, district_name: str) -> bool:
        """특정 구/군이 완료되었는지 확인

        Args:
            district_name: 확인할 구/군 이름

        Returns:
            완료되었으면 True, 아니면 False
        """
        return district_name.strip() in self.get_completed_districts()

    def clear(self) -> None:
        """체크포인트 파일 삭제"""
        try:
            if self.checkpoint_path.exists():
                self.checkpoint_path.unlink()
                logger.info("checkpoint_cleared")
        except OSError as e:
            logger.error("failed_to_clear_checkpoint", error=str(e))
            raise

    def exists(self) -> bool:
        """체크포인트 파일 존재 여부 확인

        Returns:
            파일이 존재하면 True, 아니면 False
        """
        return self.checkpoint_path.exists()

    def get_stats(self) -> dict:
        """체크포인트 통계 정보 반환

        Returns:
            통계 정보 딕셔너리
        """
        completed = self.get_completed_districts()
        file_size = 0

        if self.checkpoint_path.exists():
            try:
                file_size = self.checkpoint_path.stat().st_size
            except OSError:
                pass

        return {
            "completed_districts_count": len(completed),
            "completed_districts": list(completed),
            "file_size_bytes": file_size,
            "file_path": str(self.checkpoint_path),
            "exists": self.checkpoint_path.exists(),
        }


# 하위 호환성을 위한 별칭
CheckpointManager = SimpleCheckpointManager
