import subprocess
from pathlib import Path


def test_main_script_runs_successfully(tmp_path: Path) -> None:
    output_file = tmp_path / "test_output.csv"

    result = subprocess.run(
        ["python", "scripts/main.py", "--output", str(output_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "저장했습니다" in result.stdout
