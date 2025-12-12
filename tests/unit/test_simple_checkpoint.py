"""단순화된 체크포인트 관리자 테스트"""

import tempfile
from pathlib import Path


from crawler.utils.checkpoint import SimpleCheckpointManager


class TestSimpleCheckpointManager:
    """SimpleCheckpointManager 테스트"""

    def test_init_creates_directory(self):
        """초기화 시 디렉토리가 생성되는지 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_path = Path(temp_dir) / "checkpoints" / "test_checkpoint.txt"
            manager = SimpleCheckpointManager(str(checkpoint_path))

            assert manager.checkpoint_path.exists() is False  # 파일은 아직 생성되지 않음
            assert checkpoint_path.parent.exists() is True  # 디렉토리는 생성됨

    def test_add_completed_district(self):
        """완료된 구/군 추가 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_path = Path(temp_dir) / "test_checkpoint.txt"
            manager = SimpleCheckpointManager(str(checkpoint_path))

            # 구/군 추가
            manager.add_completed_district("강남구")

            # 파일이 생성되고 내용 확인
            assert checkpoint_path.exists() is True
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                content = f.read()
                assert "강남구\n" in content

    def test_add_multiple_districts(self):
        """여러 구/군 추가 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_path = Path(temp_dir) / "test_checkpoint.txt"
            manager = SimpleCheckpointManager(str(checkpoint_path))

            # 여러 구/군 추가
            manager.add_completed_district("강남구")
            manager.add_completed_district("서초구")
            manager.add_completed_district("송파구")

            # 완료된 구/군 목록 확인
            completed = manager.get_completed_districts()
            assert completed == {"강남구", "서초구", "송파구"}

    def test_add_duplicate_district(self):
        """중복된 구/군 추가 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_path = Path(temp_dir) / "test_checkpoint.txt"
            manager = SimpleCheckpointManager(str(checkpoint_path))

            # 동일한 구/군 두 번 추가
            manager.add_completed_district("강남구")
            manager.add_completed_district("강남구")

            # 중복되지 않은 것을 확인
            completed = manager.get_completed_districts()
            assert completed == {"강남구"}

            # 파일 내용 확인 (한 줄만 있는지)
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                assert len(lines) == 1
                assert lines[0].strip() == "강남구"

    def test_get_completed_districts_empty(self):
        """빈 체크포인트 파일에서 완료된 구/군 목록 가져오기 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_path = Path(temp_dir) / "test_checkpoint.txt"
            manager = SimpleCheckpointManager(str(checkpoint_path))

            # 파일이 없을 때 빈 집합 반환
            completed = manager.get_completed_districts()
            assert completed == set()

    def test_is_district_completed(self):
        """구/군 완료 여부 확인 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_path = Path(temp_dir) / "test_checkpoint.txt"
            manager = SimpleCheckpointManager(str(checkpoint_path))

            # 추가 전
            assert manager.is_district_completed("강남구") is False

            # 추가 후
            manager.add_completed_district("강남구")
            assert manager.is_district_completed("강남구") is True
            assert manager.is_district_completed("서초구") is False

    def test_is_district_completed_with_whitespace(self):
        """공백이 포함된 구/군 이름 처리 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_path = Path(temp_dir) / "test_checkpoint.txt"
            manager = SimpleCheckpointManager(str(checkpoint_path))

            # 공백 포함된 이름으로 추가
            manager.add_completed_district("  강남구  ")

            # 공백 제거 후 확인
            assert manager.is_district_completed("강남구") is True
            assert manager.is_district_completed("  강남구  ") is True

    def test_add_empty_district_name(self):
        """빈 구/군 이름 추가 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_path = Path(temp_dir) / "test_checkpoint.txt"
            manager = SimpleCheckpointManager(str(checkpoint_path))

            # 빈 문자열 및 공백 추가
            manager.add_completed_district("")
            manager.add_completed_district("   ")
            manager.add_completed_district(None)  # type: ignore

            # 파일이 생성되지 않아야 함
            assert checkpoint_path.exists() is False

    def test_clear(self):
        """체크포인트 파일 삭제 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_path = Path(temp_dir) / "test_checkpoint.txt"
            manager = SimpleCheckpointManager(str(checkpoint_path))

            # 구/군 추가
            manager.add_completed_district("강남구")
            assert checkpoint_path.exists() is True

            # 삭제
            manager.clear()
            assert checkpoint_path.exists() is False

    def test_exists(self):
        """체크포인트 파일 존재 여부 확인 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_path = Path(temp_dir) / "test_checkpoint.txt"
            manager = SimpleCheckpointManager(str(checkpoint_path))

            # 초기 상태
            assert manager.exists() is False

            # 구/군 추가 후
            manager.add_completed_district("강남구")
            assert manager.exists() is True

    def test_get_stats(self):
        """체크포인트 통계 정보 확인 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_path = Path(temp_dir) / "test_checkpoint.txt"
            manager = SimpleCheckpointManager(str(checkpoint_path))

            # 초기 통계
            stats = manager.get_stats()
            assert stats["completed_districts_count"] == 0
            assert stats["completed_districts"] == []
            assert stats["file_size_bytes"] == 0
            assert stats["exists"] is False
            assert stats["file_path"] == str(checkpoint_path)

            # 구/군 추가 후
            manager.add_completed_district("강남구")
            manager.add_completed_district("서초구")

            stats = manager.get_stats()
            assert stats["completed_districts_count"] == 2
            assert set(stats["completed_districts"]) == {"강남구", "서초구"}
            assert stats["file_size_bytes"] > 0
            assert stats["exists"] is True

    def test_persistence(self):
        """체크포인트 데이터 지속성 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_path = Path(temp_dir) / "test_checkpoint.txt"

            # 첫 번째 관리자 인스턴스
            manager1 = SimpleCheckpointManager(str(checkpoint_path))
            manager1.add_completed_district("강남구")
            manager1.add_completed_district("서초구")

            # 두 번째 관리자 인스턴스 (동일 파일 로드)
            manager2 = SimpleCheckpointManager(str(checkpoint_path))
            completed = manager2.get_completed_districts()

            assert completed == {"강남구", "서초구"}

    def test_handles_empty_lines(self):
        """파일의 빈 줄 처리 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_path = Path(temp_dir) / "test_checkpoint.txt"

            # 수동으로 빈 줄이 있는 파일 생성
            with open(checkpoint_path, "w", encoding="utf-8") as f:
                f.write("강남구\n")
                f.write("\n")  # 빈 줄
                f.write("서초구\n")
                f.write("   \n")  # 공백만 있는 줄

            manager = SimpleCheckpointManager(str(checkpoint_path))
            completed = manager.get_completed_districts()

            # 빈 줄은 무시되어야 함
            assert completed == {"강남구", "서초구"}

    def test_korean_district_names(self):
        """한글 구/군 이름 처리 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_path = Path(temp_dir) / "test_checkpoint.txt"
            manager = SimpleCheckpointManager(str(checkpoint_path))

            # 다양한 한글 구/군 이름
            districts = [
                "강남구",
                "강동구",
                "강북구",
                "강서구",
                "관악구",
                "광진구",
                "구로구",
                "금천구",
                "노원구",
                "도봉구",
                "동대문구",
                "동작구",
                "마포구",
                "서대문구",
                "서초구",
                "성동구",
                "성북구",
                "송파구",
                "양천구",
                "영등포구",
                "용산구",
                "은평구",
                "종로구",
                "중구",
                "중랑구",
            ]

            for district in districts:
                manager.add_completed_district(district)

            completed = manager.get_completed_districts()
            assert completed == set(districts)

            # 파일 인코딩 확인
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                content = f.read()
                for district in districts:
                    assert district in content
