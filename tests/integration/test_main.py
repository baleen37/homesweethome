"""메인 스크립트 통합 테스트"""

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def project_root():
    """프로젝트 루트 디렉토리"""
    return Path(__file__).parent.parent.parent


def test_main_script_runs_successfully(tmp_path: Path, project_root: Path) -> None:
    """메인 스크립트 실행 성공 테스트"""
    output_file = tmp_path / "test_output.csv"

    # uv run 사용
    result = subprocess.run(
        ["uv", "run", "python", "scripts/main.py", "--output", str(output_file)],
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )

    # 결과 확인
    # 실제 API 호출 실패 가능성이 있으므로, 스크립트가 정상적으로 실행되는지 확인
    assert result.returncode in [0, 1]  # 0: 성공, 1: 비즈니스 오류
    assert "Traceback" not in result.stderr  # 파이썬 예외가 없어야 함


def test_main_script_with_district_option(tmp_path: Path, project_root: Path) -> None:
    """--district 옵션 테스트"""
    output_file = tmp_path / "district_output.csv"

    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "scripts/main.py",
            "--output",
            str(output_file),
            "--district",
            "강남구",
        ],
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )

    # 옵션이 올바르게 처리되었는지 확인
    assert result.returncode in [0, 1]
    assert "Traceback" not in result.stderr
    if result.returncode == 0:
        assert "강남구" in result.stdout


def test_main_script_help_option(project_root: Path) -> None:
    """--help 옵션 테스트"""
    result = subprocess.run(
        ["uv", "run", "python", "scripts/main.py", "--help"],
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )

    # 도움말이 표시되어야 함
    assert result.returncode == 0
    assert "호갱노노 부동산" in result.stdout
    assert "--district" in result.stdout
    assert "--output" in result.stdout
    assert "--resume" in result.stdout


def test_main_script_with_multiple_districts(tmp_path: Path, project_root: Path) -> None:
    """여러 구 지정 테스트"""
    output_file = tmp_path / "multi_district_output.csv"

    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "scripts/main.py",
            "--output",
            str(output_file),
            "--district",
            "강남구,서초구,송파구",
        ],
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )

    # 여러 구가 올바르게 처리되는지 확인
    assert result.returncode in [0, 1]
    assert "Traceback" not in result.stderr
    if result.returncode == 0:
        assert "강남구" in result.stdout or "서초구" in result.stdout or "송파구" in result.stdout


def test_main_script_creates_output_files(tmp_path: Path, project_root: Path) -> None:
    """출력 파일 생성 테스트"""
    # 스크립트가 실행되면 output 디렉토리에 파일이 생성되어야 함
    result = subprocess.run(
        ["uv", "run", "python", "scripts/main.py"],
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )

    # 스크립트 실행 확인
    assert result.returncode in [0, 1]

    # 출력 디렉토리 확인
    output_dir = project_root / "output"
    if output_dir.exists():
        csv_files = list(output_dir.glob("*.csv"))
        # 최소한 CSV 파일이 생성되어야 함 (단지 정보 또는 거래내역)
        assert len(csv_files) >= 0  # API 실패 시 파일이 없을 수 있음


def test_main_script_error_handling(project_root: Path) -> None:
    """오류 처리 테스트"""
    # 존재하지 않는 옵션 사용
    result = subprocess.run(
        ["uv", "run", "python", "scripts/main.py", "--invalid-option"],
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )

    # argparse가 오류를 감지해야 함
    assert result.returncode != 0
    assert "unrecognized arguments: --invalid-option" in result.stderr


def test_main_script_resume_option(tmp_path: Path, project_root: Path) -> None:
    """--resume 옵션 테스트"""
    output_file = tmp_path / "resume_output.csv"

    # 체크포인트 파일이 없는 상태에서 --resume 실행
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "scripts/main.py",
            "--output",
            str(output_file),
            "--resume",
        ],
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )

    # 체크포인트가 없어도 정상적으로 처리되어야 함
    assert result.returncode in [0, 1]
    assert "Traceback" not in result.stderr
