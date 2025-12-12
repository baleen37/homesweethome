"""Tests for FileLogHandler functionality."""

import json
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import ANY, patch

# Import test setup FIRST to configure path and mocks

# Now import crawler modules
from crawler.file_log_handler import FileLogHandler


class TestFileLogHandler(TestCase):
    """FileLogHandler 테스트 클래스"""

    def setUp(self):
        """테스트 메서드 실행 전 설정"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.handler = FileLogHandler(output_dir=self.temp_dir)

    def tearDown(self):
        """테스트 메서드 실행 후 정리"""
        # 임시 파일 정리
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_without_log_file(self):
        """로그 파일 없이 초기화 테스트"""
        assert self.handler.output_dir == self.temp_dir
        assert self.handler.log_file is None
        assert self.handler.progress_file == self.temp_dir / "progress.json"

    def test_init_with_log_file(self):
        """로그 파일과 함께 초기화 테스트"""
        handler = FileLogHandler(output_dir=self.temp_dir, log_file="test.log")
        assert handler.log_file is not None
        assert (self.temp_dir / "test.log").exists()

        # 초기 로그 메시지 확인
        with open(self.temp_dir / "test.log", "r", encoding="utf-8") as f:
            log_content = f.read()
            logs = [json.loads(line) for line in log_content.strip().split("\n") if line]
            assert len(logs) == 1
            assert logs[0]["event"] == "progress_tracking_started"

        handler.close()

    def test_save_progress(self):
        """진행 상황 저장 테스트"""
        progress_data = {
            "total_dongs": 10,
            "completed_dongs": 5,
            "total_complexes": 100,
            "completed_complexes": 50,
        }

        self.handler.save_progress(progress_data)

        # 파일이 생성되었는지 확인
        progress_file = self.temp_dir / "progress.json"
        assert progress_file.exists()

        # 내용 확인
        with open(progress_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
            assert saved_data["total_dongs"] == 10
            assert saved_data["completed_dongs"] == 5
            assert "current_time" in saved_data
            assert saved_data["current_time"] > 0

    def test_load_progress(self):
        """진행 상황 로드 테스트"""
        # 먼저 저장
        progress_data = {
            "total_dongs": 10,
            "completed_dongs": 5,
            "total_complexes": 100,
            "completed_complexes": 50,
        }
        self.handler.save_progress(progress_data)

        # 로드
        loaded_data = self.handler.load_progress()
        assert loaded_data is not None
        assert loaded_data["total_dongs"] == 10
        assert loaded_data["completed_dongs"] == 5
        assert loaded_data["total_complexes"] == 100
        assert loaded_data["completed_complexes"] == 50

    def test_load_progress_no_file(self):
        """파일이 없을 때 진행 상황 로드 테스트"""
        loaded_data = self.handler.load_progress()
        assert loaded_data is None

    def test_load_progress_invalid_json(self):
        """잘못된 JSON 파일 로드 테스트"""
        # 잘못된 JSON 파일 생성
        progress_file = self.temp_dir / "progress.json"
        with open(progress_file, "w", encoding="utf-8") as f:
            f.write("invalid json")

        # 로드 시도 - None을 반환해야 함
        loaded_data = self.handler.load_progress()
        assert loaded_data is None

    def test_log_dong_started(self):
        """동 시작 로그 작성 테스트"""
        handler = FileLogHandler(output_dir=self.temp_dir, log_file="test.log")

        handler.log_dong_started("12345", "역삼1동", 10)

        # 로그 확인
        with open(self.temp_dir / "test.log", "r", encoding="utf-8") as f:
            log_content = f.read()
            logs = [json.loads(line) for line in log_content.strip().split("\n") if line]

            # 초기 로그 + 동 시작 로그
            assert len(logs) == 2
            dong_log = logs[1]
            assert dong_log["event"] == "dong_started"
            assert dong_log["dong_code"] == "12345"
            assert dong_log["dong_name"] == "역삼1동"
            assert dong_log["complex_count"] == 10

        handler.close()

    def test_log_error(self):
        """에러 로그 작성 테스트"""
        handler = FileLogHandler(output_dir=self.temp_dir, log_file="test.log")

        handler.log_error("Test error message")

        # 로그 확인
        with open(self.temp_dir / "test.log", "r", encoding="utf-8") as f:
            log_content = f.read()
            logs = [json.loads(line) for line in log_content.strip().split("\n") if line]

            # 초기 로그 + 에러 로그
            assert len(logs) == 2
            error_log = logs[1]
            assert error_log["event"] == "error_occurred"
            assert error_log["error"] == "Test error message"
            assert error_log["level"] == "ERROR"

        handler.close()

    def test_log_progress_report(self):
        """진행 상황 리포트 로그 작성 테스트"""
        handler = FileLogHandler(output_dir=self.temp_dir, log_file="test.log")

        summary = {
            "completed_dongs": 5,
            "total_dongs": 10,
            "dong_progress_percent": 50.0,
        }

        handler.log_progress_report(summary)

        # 로그 확인
        with open(self.temp_dir / "test.log", "r", encoding="utf-8") as f:
            log_content = f.read()
            logs = [json.loads(line) for line in log_content.strip().split("\n") if line]

            # 초기 로그 + 진행 상황 리포트 로그
            assert len(logs) == 2
            report_log = logs[1]
            assert report_log["event"] == "progress_report"
            assert report_log["summary"]["completed_dongs"] == 5

        handler.close()

    def test_log_crawling_finished(self):
        """크롤링 완료 로그 작성 테스트"""
        handler = FileLogHandler(output_dir=self.temp_dir, log_file="test.log")

        final_summary = {
            "completed_dongs": 10,
            "total_dongs": 10,
            "total_errors": 0,
        }

        handler.log_crawling_finished(final_summary)

        # 로그 확인
        with open(self.temp_dir / "test.log", "r", encoding="utf-8") as f:
            log_content = f.read()
            logs = [json.loads(line) for line in log_content.strip().split("\n") if line]

            # 초기 로그 + 크롤링 완료 로그
            assert len(logs) == 2
            finish_log = logs[1]
            assert finish_log["event"] == "crawling_finished"
            assert finish_log["final_summary"]["completed_dongs"] == 10

        handler.close()

    def test_close(self):
        """로그 파일 닫기 테스트"""
        handler = FileLogHandler(output_dir=self.temp_dir, log_file="test.log")

        assert handler.log_file is not None
        assert not handler.log_file.closed

        handler.close()
        assert handler.log_file is None

    def test_context_manager(self):
        """Context manager 사용 테스트"""
        with FileLogHandler(output_dir=self.temp_dir, log_file="test.log") as handler:
            assert handler.log_file is not None
            handler.log_dong_started("12345", "테스트동", 5)

        # context manager 종료 후 파일이 닫혔는지 확인
        assert handler.log_file is None

        # 로그가 제대로 작성되었는지 확인
        with open(self.temp_dir / "test.log", "r", encoding="utf-8") as f:
            log_content = f.read()
            assert "progress_tracking_started" in log_content
            assert "dong_started" in log_content

    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    def test_log_file_open_failure(self, mock_open):
        """로그 파일 열기 실패 테스트"""
        with patch("crawler.file_log_handler.structlog.get_logger") as mock_logger:
            mock_logger_instance = mock_logger.return_value

            handler = FileLogHandler(output_dir=self.temp_dir, log_file="test.log")

            # 로그 파일이 없어야 함
            assert handler.log_file is None

            # 경고 로그가 기록되었는지 확인
            mock_logger_instance.warning.assert_called_once()

    def test_save_progress_failure(self):
        """진행 상황 저장 실패 테스트"""
        # 읽기 전용 디렉토리로 설정
        read_only_dir = self.temp_dir / "readonly"
        read_only_dir.mkdir()
        read_only_dir.chmod(0o444)

        # Patch structlog at the module level before creating FileLogHandler
        with patch("crawler.file_log_handler.structlog") as mock_structlog:
            mock_logger = mock_structlog.get_logger.return_value

            handler = FileLogHandler(output_dir=read_only_dir)

            # 저장 시도
            handler.save_progress({"test": "data"})

            # 경고 로그가 기록되어야 함
            mock_logger.warning.assert_called_once_with(
                "failed_to_save_progress",
                error=ANY,
                progress_file=str(read_only_dir / "progress.json"),
            )

        # 권한 복원
        read_only_dir.chmod(0o755)
