import json
from pathlib import Path

import pytest

from crawler.utils.checkpoint import CheckpointManager


@pytest.fixture
def temp_checkpoint_file(tmp_path: Path) -> Path:
    return tmp_path / "checkpoint.json"


def test_load_returns_none_when_file_does_not_exist(temp_checkpoint_file: Path) -> None:
    manager = CheckpointManager(str(temp_checkpoint_file))
    result = manager.load()
    assert result is None


def test_save_creates_checkpoint_file(temp_checkpoint_file: Path) -> None:
    manager = CheckpointManager(str(temp_checkpoint_file))
    checkpoint = {
        "last_completed": {"district": "강남구", "dong": "삼성동"},
        "completed_dongs": ["1168010100"],
        "failed_dongs": [],
        "total_complexes_crawled": 26,
    }
    manager.save(checkpoint)

    assert temp_checkpoint_file.exists()
    with open(temp_checkpoint_file) as f:
        saved = json.load(f)
    assert saved["last_completed"]["district"] == "강남구"
    assert saved["total_complexes_crawled"] == 26


def test_load_returns_saved_checkpoint(temp_checkpoint_file: Path) -> None:
    checkpoint = {
        "last_completed": {"district": "서초구", "dong": "반포동"},
        "completed_dongs": ["1165010100", "1165010200"],
        "failed_dongs": [],
        "total_complexes_crawled": 52,
    }
    with open(temp_checkpoint_file, "w") as f:
        json.dump(checkpoint, f)

    manager = CheckpointManager(str(temp_checkpoint_file))
    result = manager.load()

    assert result is not None
    assert result["last_completed"]["dong"] == "반포동"
    assert len(result["completed_dongs"]) == 2


def test_should_skip_dong_returns_true_for_completed(temp_checkpoint_file: Path) -> None:
    checkpoint = {
        "completed_dongs": ["1168010100", "1168010200"],
        "failed_dongs": [],
    }
    with open(temp_checkpoint_file, "w") as f:
        json.dump(checkpoint, f)

    manager = CheckpointManager(str(temp_checkpoint_file))
    manager.load()

    assert manager.should_skip_dong("1168010100") is True
    assert manager.should_skip_dong("1168010999") is False


def test_add_failed_dong_records_failure(temp_checkpoint_file: Path) -> None:
    manager = CheckpointManager(str(temp_checkpoint_file))
    manager.checkpoint = {
        "completed_dongs": [],
        "failed_dongs": [],
    }

    dong = {"cortarNo": "1168010300", "dong_name": "역삼동"}
    manager.add_failed_dong(dong, "API timeout")

    assert len(manager.checkpoint["failed_dongs"]) == 1
    assert manager.checkpoint["failed_dongs"][0]["cortarNo"] == "1168010300"
    assert manager.checkpoint["failed_dongs"][0]["error"] == "API timeout"
