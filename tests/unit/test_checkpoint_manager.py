# Import test setup to configure path and mocks

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

# Import test setup to configure path and mocks

from crawler.rate_limiter import AdaptiveRateLimiter
from crawler.utils.checkpoint import CheckpointManager


@pytest.fixture
def temp_checkpoint_file(tmp_path: Path) -> Path:
    return tmp_path / "checkpoint.json"


def test_load_returns_empty_dict_when_file_does_not_exist(temp_checkpoint_file: Path) -> None:
    manager = CheckpointManager(str(temp_checkpoint_file))
    result = manager.load()
    assert result is None


def test_save_creates_checkpoint_file(temp_checkpoint_file: Path) -> None:
    manager = CheckpointManager(str(temp_checkpoint_file))
    manager.save(last_dong="1168010100", last_complex="111515")

    assert temp_checkpoint_file.exists()
    with open(temp_checkpoint_file) as f:
        saved = json.load(f)
    assert saved["last_dong"] == "1168010100"
    assert saved["last_complex"] == "111515"
    assert saved["total_complexes_processed"] == 0
    assert saved["total_transactions_collected"] == 0
    assert saved["started_at"] is not None
    assert saved["last_updated_at"] is not None


def test_load_returns_saved_checkpoint(temp_checkpoint_file: Path) -> None:
    checkpoint = {
        "last_dong": "1165010100",
        "last_complex": "111600",
        "total_complexes_processed": 52,
        "total_transactions_collected": 1250,
        "started_at": "2025-12-06T10:00:00",
        "last_updated_at": "2025-12-06T15:30:00",
        "failed_dongs": [],
        "rate_limiter_state": {"current_delay": 2.8, "success_count": 45, "error_count": 0},
    }
    with open(temp_checkpoint_file, "w") as f:
        json.dump(checkpoint, f)

    manager = CheckpointManager(str(temp_checkpoint_file))
    result = manager.load()

    assert result is not None
    assert result["last_dong"] == "1165010100"
    assert result["total_complexes_processed"] == 52
    assert result["total_transactions_collected"] == 1250


def test_save_with_statistics(temp_checkpoint_file: Path) -> None:
    """통계 정보 증가 테스트"""
    manager = CheckpointManager(str(temp_checkpoint_file))

    # 처음 저장
    manager.save(last_dong="1168010100", increment_complexes=True)

    # 두 번째 저장 (단지 수 추가)
    manager.save(increment_complexes=True)

    # 세 번째 저장 (거래내역 추가)
    manager.save(increment_transactions=50)

    with open(temp_checkpoint_file) as f:
        saved = json.load(f)

    assert saved["total_complexes_processed"] == 2
    assert saved["total_transactions_collected"] == 50


def test_save_with_rate_limiter_state(temp_checkpoint_file: Path) -> None:
    """Rate limiter 상태 저장 테스트"""
    manager = CheckpointManager(str(temp_checkpoint_file))

    # Mock rate limiter
    mock_rate_limiter = Mock(spec=AdaptiveRateLimiter)
    mock_rate_limiter.current_delay = 3.2
    mock_rate_limiter.success_count = 15
    mock_rate_limiter.error_count = 1

    manager.save(last_dong="1168010100", rate_limiter=mock_rate_limiter)

    with open(temp_checkpoint_file) as f:
        saved = json.load(f)

    assert saved["rate_limiter_state"]["current_delay"] == 3.2
    assert saved["rate_limiter_state"]["success_count"] == 15
    assert saved["rate_limiter_state"]["error_count"] == 1


def test_restore_rate_limiter_state(temp_checkpoint_file: Path) -> None:
    """Rate limiter 상태 복원 테스트"""
    # 저장된 상태로 파일 생성
    checkpoint = {
        "rate_limiter_state": {"current_delay": 4.5, "success_count": 25, "error_count": 2}
    }
    with open(temp_checkpoint_file, "w") as f:
        json.dump(checkpoint, f)

    manager = CheckpointManager(str(temp_checkpoint_file))
    manager.load()

    rate_limiter = AdaptiveRateLimiter()
    success = manager.restore_rate_limiter_state(rate_limiter)

    assert success is True
    assert rate_limiter.current_delay == 4.5
    assert rate_limiter.success_count == 25
    assert rate_limiter.error_count == 2


def test_restore_rate_limiter_state_no_state(temp_checkpoint_file: Path) -> None:
    """저장된 Rate limiter 상태가 없을 때 테스트"""
    manager = CheckpointManager(str(temp_checkpoint_file))
    rate_limiter = AdaptiveRateLimiter()
    initial_delay = rate_limiter.current_delay

    success = manager.restore_rate_limiter_state(rate_limiter)

    assert success is False
    assert rate_limiter.current_delay == initial_delay


def test_get_progress_summary(temp_checkpoint_file: Path) -> None:
    """진행 상황 요약 정보 테스트"""
    manager = CheckpointManager(str(temp_checkpoint_file))

    # 체크포인트 상태 설정
    manager.checkpoint = {
        "last_dong": "1168010500",
        "last_complex": "112345",
        "total_complexes_processed": 100,
        "total_transactions_collected": 2500,
        "started_at": "2025-12-06T10:00:00",
        "last_updated_at": "2025-12-06T15:30:00",
        "failed_dongs": [
            {"dong_code": "1168010100", "error": "Timeout"},
            {"dong_code": "1168010200", "error": "API Error"},
        ],
    }

    summary = manager.get_progress_summary()

    assert summary["last_dong"] == "1168010500"
    assert summary["last_complex"] == "112345"
    assert summary["total_complexes_processed"] == 100
    assert summary["total_transactions_collected"] == 2500
    assert summary["started_at"] == "2025-12-06T10:00:00"
    assert summary["last_updated_at"] == "2025-12-06T15:30:00"
    assert summary["failed_dongs_count"] == 2


def test_add_failed_dong_records_failure(temp_checkpoint_file: Path) -> None:
    manager = CheckpointManager(str(temp_checkpoint_file))
    manager.checkpoint = {
        "failed_dongs": [],
    }

    manager.add_failed_dong("1168010300", "API timeout")

    assert len(manager.checkpoint["failed_dongs"]) == 1
    assert manager.checkpoint["failed_dongs"][0]["dong_code"] == "1168010300"
    assert manager.checkpoint["failed_dongs"][0]["error"] == "API timeout"
    assert "timestamp" in manager.checkpoint["failed_dongs"][0]
