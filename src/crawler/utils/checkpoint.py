import json
from datetime import datetime
from pathlib import Path
from typing import Any

from crawler.rate_limiter import AdaptiveRateLimiter


class CheckpointManager:
    """체크포인트 관리자

    서울시 전체 아파트 크롤링을 위한 진행 상황 추적
    - 동(洞) 단위 진행 상황
    - 단지 처리 현황
    - 거래내역 수집 통계
    - Rate limiter 상태 보존
    """

    def __init__(self, checkpoint_path: str) -> None:
        self.filepath = Path(checkpoint_path)
        self.checkpoint: dict[str, Any] = {
            # 기본 위치 정보
            "last_dong": None,  # 마지막으로 처리된 동 ID
            "last_complex": None,  # 마지막으로 처리된 단지 ID

            # 처리 통계
            "total_complexes_processed": 0,  # 처리된 총 단지 수
            "total_transactions_collected": 0,  # 수집된 총 거래내역 수

            # 시간 정보
            "started_at": None,  # 시작 시각
            "last_updated_at": None,  # 마지막 업데이트 시각

            # 실패 기록
            "failed_dongs": [],  # 실패한 동 코드 목록

            # Rate limiter 상태
            "rate_limiter_state": None,
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
        except (json.JSONDecodeError, KeyError):
            # 손상된 파일은 무시
            return None

    def save(
        self,
        last_dong: str | None = None,
        last_complex: str | None = None,
        increment_complexes: bool = False,
        increment_transactions: int = 0,
        rate_limiter: AdaptiveRateLimiter | None = None,
    ) -> None:
        """체크포인트 저장

        Args:
            last_dong: 완료한 동 코드 (선택적)
            last_complex: 마지막으로 처리한 단지 ID (선택적)
            increment_complexes: 처리된 단지 수 증가 여부
            increment_transactions: 수집된 거래내역 수 증가분
            rate_limiter: Rate limiter 상태 저장을 위한 객체
        """
        # 위치 정보 업데이트
        if last_dong:
            self.checkpoint["last_dong"] = last_dong
            # 첫 시작 시 started_at 설정
            if not self.checkpoint["started_at"]:
                self.checkpoint["started_at"] = datetime.now().isoformat()

        if last_complex:
            self.checkpoint["last_complex"] = last_complex

        # 통계 정보 업데이트
        if increment_complexes:
            self.checkpoint["total_complexes_processed"] += 1

        if increment_transactions > 0:
            self.checkpoint["total_transactions_collected"] += increment_transactions

        # Rate limiter 상태 저장
        if rate_limiter:
            self.checkpoint["rate_limiter_state"] = {
                "current_delay": rate_limiter.current_delay,
                "success_count": rate_limiter.success_count,
                "error_count": rate_limiter.error_count,
            }

        # 항상 마지막 업데이트 시각 갱신
        self.checkpoint["last_updated_at"] = datetime.now().isoformat()

        # 파일에 저장
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

    def restore_rate_limiter_state(self, rate_limiter: AdaptiveRateLimiter) -> bool:
        """체크포인트에 저장된 Rate limiter 상태 복원

        Args:
            rate_limiter: 상태를 복원할 Rate limiter 객체

        Returns:
            성공 여부
        """
        state = self.checkpoint.get("rate_limiter_state")
        if not state:
            return False

        try:
            rate_limiter.current_delay = state.get("current_delay", 2.5)
            rate_limiter.success_count = state.get("success_count", 0)
            rate_limiter.error_count = state.get("error_count", 0)
            return True
        except (KeyError, TypeError):
            return False

    def get_progress_summary(self) -> dict[str, Any]:
        """진행 상황 요약 정보 반환

        Returns:
            진행 상황 통계
        """
        return {
            "last_dong": self.checkpoint.get("last_dong"),
            "last_complex": self.checkpoint.get("last_complex"),
            "total_complexes_processed": self.checkpoint.get("total_complexes_processed", 0),
            "total_transactions_collected": self.checkpoint.get("total_transactions_collected", 0),
            "started_at": self.checkpoint.get("started_at"),
            "last_updated_at": self.checkpoint.get("last_updated_at"),
            "failed_dongs_count": len(self.checkpoint.get("failed_dongs", [])),
        }

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
            self.checkpoint["last_updated_at"] = datetime.now().isoformat()
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, "w") as f:
                json.dump(self.checkpoint, f, indent=2, ensure_ascii=False)