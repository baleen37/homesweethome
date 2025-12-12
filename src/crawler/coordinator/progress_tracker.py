"""Progress tracker for crawler operations.

간단한 진행 상황 추적 기능을 제공합니다.
"""

import logging
import json
import time
from pathlib import Path
from typing import Dict, Any, Set, List

logger = logging.getLogger(__name__)


class ProgressTracker:
    """진행 상황 추적기

    체크포인트 관리와 수집된 아파트 ID 추적 기능을 제공합니다.
    """

    def __init__(self, checkpoint_file: Path | str):
        """초기화

        Args:
            checkpoint_file: 체크포인트 파일 경로
        """
        self.checkpoint_file = Path(checkpoint_file)
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

        # 메모리 상태
        self.collected_apt_ids: Set[str] = set()
        self.processed_dongs: Set[str] = set()
        self.processed_keywords: Set[str] = set()
        self.start_time = time.time()

        # 체크포인트 로드
        self._load_checkpoint()

        logger.info(
            "progress_tracker_initialized",
            checkpoint_file=str(self.checkpoint_file),
            collected_apartments=len(self.collected_apt_ids),
        )

    def _load_checkpoint(self):
        """체크포인트 파일에서 상태 로드"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.collected_apt_ids = set(data.get("collected_apt_ids", []))
                self.processed_dongs = set(data.get("processed_dongs", []))
                self.processed_keywords = set(data.get("processed_keywords", []))

                logger.info(
                    "checkpoint_loaded",
                    apartments=len(self.collected_apt_ids),
                    dongs=len(self.processed_dongs),
                    keywords=len(self.processed_keywords),
                )
            except Exception as e:
                logger.warning("failed_to_load_checkpoint", error=str(e))

    def save_checkpoint(self):
        """현재 상태를 체크포인트 파일에 저장"""
        try:
            data = {
                "collected_apt_ids": list(self.collected_apt_ids),
                "processed_dongs": list(self.processed_dongs),
                "processed_keywords": list(self.processed_keywords),
                "last_updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "elapsed_seconds": time.time() - self.start_time,
            }

            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.debug("checkpoint_saved", file=str(self.checkpoint_file))

        except Exception as e:
            logger.error("failed_to_save_checkpoint", error=str(e))

    def add_apartment(self, apt_id: str):
        """아파트 ID 추가"""
        if apt_id and apt_id not in self.collected_apt_ids:
            self.collected_apt_ids.add(apt_id)
            logger.debug("apartment_added", apt_id=apt_id, total=len(self.collected_apt_ids))

    def add_apartments(self, apt_ids: List[str]):
        """여러 아파트 ID 일괄 추가"""
        new_ids = [apt_id for apt_id in apt_ids if apt_id and apt_id not in self.collected_apt_ids]
        self.collected_apt_ids.update(new_ids)
        if new_ids:
            logger.debug("apartments_added", count=len(new_ids), total=len(self.collected_apt_ids))

    def mark_dong_processed(self, dong_code: str):
        """동 처리 완료 표시"""
        if dong_code not in self.processed_dongs:
            self.processed_dongs.add(dong_code)
            logger.debug("dong_processed", dong_code=dong_code, total=len(self.processed_dongs))

    def mark_keyword_processed(self, keyword: str):
        """키워드 처리 완료 표시"""
        if keyword not in self.processed_keywords:
            self.processed_keywords.add(keyword)
            logger.debug("keyword_processed", keyword=keyword, total=len(self.processed_keywords))

    def is_apartment_collected(self, apt_id: str) -> bool:
        """아파트 수집 여부 확인"""
        return apt_id in self.collected_apt_ids

    def is_dong_processed(self, dong_code: str) -> bool:
        """동 처리 여부 확인"""
        return dong_code in self.processed_dongs

    def is_keyword_processed(self, keyword: str) -> bool:
        """키워드 처리 여부 확인"""
        return keyword in self.processed_keywords

    def get_statistics(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        return {
            "collected_apartments": len(self.collected_apt_ids),
            "processed_dongs": len(self.processed_dongs),
            "processed_keywords": len(self.processed_keywords),
            "elapsed_seconds": time.time() - self.start_time,
            "checkpoint_file": str(self.checkpoint_file),
        }

    def reset(self):
        """모든 상태 초기화"""
        self.collected_apt_ids.clear()
        self.processed_dongs.clear()
        self.processed_keywords.clear()
        self.start_time = time.time()

        # 체크포인트 파일 삭제
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()

        logger.info("progress_tracker_reset")

    def __enter__(self):
        """컨텍스트 매니저 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료 시 체크포인트 저장"""
        self.save_checkpoint()
        if exc_type:
            logger.error("progress_tracker_exited_with_error", error=str(exc_val))
