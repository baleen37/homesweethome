"""체크포인트 동시성 관리를 위한 스레드 세이프 체크포인트 매니저"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Dict

import structlog

from crawler.rate_limiter import AdaptiveRateLimiter

logger = structlog.get_logger()


class CheckpointManager:
    """스레드 세이프한 체크포인트 관리자

    원자적 파일 쓰기와 동시성 제어를 통해 데이터 무결성 보장
    """

    def __init__(self, checkpoint_path: str):
        """CheckpointManager 초기화

        Args:
            checkpoint_path: 체크포인트 파일 경로
        """
        self.checkpoint_path = Path(checkpoint_path)
        self.filepath = self.checkpoint_path  # 기존 API 호환성
        self._lock = RLock()  # Reentrant Lock
        self._ensure_directory_exists()

        # 기존 API 호환성을 위한 checkpoint 초기화
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

        # 초기에 체크포인트 로드
        self.load_checkpoint()

    def _ensure_directory_exists(self) -> None:
        """체크포인트 디렉토리 생성"""
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        """체크포인트 데이터 로드 (새 API)

        Returns:
            체크포인트 데이터 딕셔너리. 파일이 없거나 손상된 경우 빈 딕셔너리 반환
        """
        with self._lock:
            if not self.checkpoint_path.exists():
                logger.debug("checkpoint_file_not_found", path=str(self.checkpoint_path))
                return {}

            try:
                with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.debug(
                        "checkpoint_loaded", path=str(self.checkpoint_path), keys=len(data)
                    )
                    return data
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("checkpoint_corrupted", path=str(self.checkpoint_path), error=str(e))
                # 손상된 파일 백업
                self._backup_corrupted_file()
                return {}

    def _backup_corrupted_file(self) -> None:
        """손상된 체크포인트 파일 백업"""
        if self.checkpoint_path.exists():
            backup_path = self.checkpoint_path.with_suffix(".json.backup")
            try:
                # 기존 백업이 있으면 타임스탬프 추가
                if backup_path.exists():
                    import time

                    timestamp = int(time.time())
                    backup_path = backup_path.with_suffix(f".json.backup.{timestamp}")

                self.checkpoint_path.rename(backup_path)
                logger.info(
                    "checkpoint_backed_up",
                    original=str(self.checkpoint_path),
                    backup=str(backup_path),
                )
            except OSError as e:
                logger.error("backup_failed", path=str(self.checkpoint_path), error=str(e))

    def _atomic_write(self, data: Dict[str, Any]) -> None:
        """원자적 파일 쓰기 (임시 파일 + rename)

        Args:
            data: 저장할 데이터
        """
        # 임시 파일에 쓰기
        fd, temp_path = tempfile.mkstemp(
            suffix=".tmp", prefix="checkpoint_", dir=self.checkpoint_path.parent
        )

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, separators=(",", ": "))
                f.flush()  # 디스크에 즉시 쓰기
                os.fsync(f.fileno())  # 파일 시스템 동기화

            # 원자적 rename
            os.replace(temp_path, self.checkpoint_path)
            logger.debug("checkpoint_saved", path=str(self.checkpoint_path), keys=len(data))
        except Exception as e:
            # 오류 발생 시 임시 파일 삭제
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            logger.error("checkpoint_save_failed", path=str(self.checkpoint_path), error=str(e))
            raise

    def is_processed(self, key: str) -> bool:
        """특정 키가 이미 처리되었는지 확인

        Args:
            key: 확인할 키

        Returns:
            키가 존재하면 True, 아니면 False
        """
        with self._lock:
            data = self.load()
            return key in data

    def get_processed_keys(self) -> set[str]:
        """처리된 모든 키 목록 반환

        Returns:
            처리된 키의 집합
        """
        with self._lock:
            data = self.load()
            return set(data.keys())

    def clear(self) -> None:
        """체크포인트 데이터 전체 삭제"""
        with self._lock:
            if self.checkpoint_path.exists():
                try:
                    self.checkpoint_path.unlink()
                    logger.debug("checkpoint_cleared", path=str(self.checkpoint_path))
                except OSError as e:
                    logger.error(
                        "checkpoint_clear_failed", path=str(self.checkpoint_path), error=str(e)
                    )
                    raise

    def get(self, key: str, default: Any = None) -> Any:
        """특정 키의 값 가져오기

        Args:
            key: 가져올 키
            default: 키가 없을 때 반환할 기본값

        Returns:
            키에 해당하는 값 또는 기본값
        """
        with self._lock:
            data = self.load()
            return data.get(key, default)

    def remove(self, key: str) -> bool:
        """특정 키 삭제

        Args:
            key: 삭제할 키

        Returns:
            키가 존재했으면 True, 아니면 False
        """
        with self._lock:
            data = self.load()
            if key in data:
                del data[key]
                self._atomic_write(data)
                return True
            return False

    def exists(self) -> bool:
        """체크포인트 파일 존재 여부 확인

        Returns:
            파일 존재 여부
        """
        return self.checkpoint_path.exists()

    def update(self, updates: Dict[str, Any]) -> None:
        """여러 키-값 쌍 한 번에 업데이트

        Args:
            updates: 업데이트할 키-값 쌍 딕셔너리
        """
        with self._lock:
            current_data = self.load()
            current_data.update(updates)
            self._atomic_write(current_data)

    def get_stats(self) -> Dict[str, Any]:
        """체크포인트 통계 정보 반환

        Returns:
            체크포인트 통계 정보
        """
        with self._lock:
            data = self.load()
            file_size = self.checkpoint_path.stat().st_size if self.checkpoint_path.exists() else 0

            return {
                "keys_count": len(data),
                "file_size_bytes": file_size,
                "file_path": str(self.checkpoint_path),
                "exists": self.checkpoint_path.exists(),
            }

    # 기존 API 호환성 메서드들 (naver.py에서 사용)
    def load_checkpoint(self) -> dict[str, Any] | None:
        """체크포인트 파일 로드 (기존 API 호환성)"""
        with self._lock:
            if not self.checkpoint_path.exists():
                return None

            try:
                with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                    loaded_checkpoint = json.load(f)
                    self.checkpoint.update(loaded_checkpoint)
                return self.checkpoint
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("checkpoint_corrupted", path=str(self.checkpoint_path), error=str(e))
                # 손상된 파일 백업
                self._backup_corrupted_file()
                return None

    def save_checkpoint(self) -> None:
        """체크포인트 저장 (기존 API 호환성)"""
        with self._lock:
            # 항상 마지막 업데이트 시각 갱신
            self.checkpoint["last_updated_at"] = datetime.now().isoformat()

            # 원자적 쓰기
            self._atomic_write(self.checkpoint)

    def save(self, *args, **kwargs) -> None:
        """다중 정의: 기존 API와 새 API 모두 지원

        새 API용: save(key, data)
        기존 API용: save(last_dong=None, last_complex=None, ...)
        """
        # 새 API 호출 (key, data)
        if len(args) == 2 and not kwargs:
            key, data = args
            with self._lock:
                current_data = self.load()
                current_data[key] = data
                self._atomic_write(current_data)
        # 기존 API 호출
        else:
            self._save_legacy(*args, **kwargs)

    def _save_legacy(
        self,
        last_dong: str | None = None,
        last_complex: str | None = None,
        increment_complexes: bool = False,
        increment_transactions: int = 0,
        rate_limiter: AdaptiveRateLimiter | None = None,
    ) -> None:
        """체크포인트 저장 (기존 API)"""
        with self._lock:
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

            # 원자적 쓰기
            self._atomic_write(self.checkpoint)

    def should_skip_dong(self, dong_code: str) -> bool:
        """동이 이미 완료되었는지 확인 (기존 API 호환성)"""
        with self._lock:
            last_dong = self.checkpoint.get("last_dong")
            if last_dong is None:
                return False

            # last_dong 이전의 모든 동은 건너뛰기
            # 실제로는 last_dong을 찾을 때까지 모든 동을 스킵해야 하므로,
            # crawl() 메서드에서 별도 로직으로 처리
            return False

    def should_skip_complex(self, dong_code: str, complex_id: str) -> bool:
        """단지가 이미 처리되었는지 확인 (기존 API 호환성)"""
        # 현재 구현에서는 단지 레벨 체크포인트 미사용
        return False

    def restore_rate_limiter_state(self, rate_limiter: AdaptiveRateLimiter) -> bool:
        """체크포인트에 저장된 Rate limiter 상태 복원 (기존 API 호환성)"""
        with self._lock:
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
        """진행 상황 요약 정보 반환 (기존 API 호환성)"""
        with self._lock:
            return {
                "last_dong": self.checkpoint.get("last_dong"),
                "last_complex": self.checkpoint.get("last_complex"),
                "total_complexes_processed": self.checkpoint.get("total_complexes_processed", 0),
                "total_transactions_collected": self.checkpoint.get(
                    "total_transactions_collected", 0
                ),
                "started_at": self.checkpoint.get("started_at"),
                "last_updated_at": self.checkpoint.get("last_updated_at"),
                "failed_dongs_count": len(self.checkpoint.get("failed_dongs", [])),
            }

    def add_failed_dong(self, dong_code: str, error: str) -> None:
        """실패한 동 추가 (기존 API 호환성)"""
        with self._lock:
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
                self._atomic_write(self.checkpoint)
