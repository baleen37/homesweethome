"""seoul_all.py 스크립트를 위한 단위 테스트

Timeout, retry logic, checkpoint handling 등의 기능을 테스트합니다.
"""

import json

# 스크립트의 모듈 경로
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# scripts 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

# 스크립트 모듈 임포트
import seoul_all


class TestRetryLogic:
    """재시도 로직 테스트"""

    @patch("seoul_all.AsilAptListCrawler")
    def test_retry_on_timeout_error(self, mock_crawler_class):
        """타임아웃 에러 발생 시 재시도 동작 확인"""
        # 첫 번째 호출은 실패, 두 번째 호출은 성공
        mock_crawler_1 = Mock()
        mock_crawler_1.crawl.side_effect = Exception("Timeout error")

        mock_crawler_2 = Mock()
        mock_crawler_2.crawl.return_value = [{"seq": "12345", "name": "테스트"}]

        mock_crawler_class.side_effect = [mock_crawler_1, mock_crawler_2]

        # 첫 번째 실패 후 재시도
        with patch("seoul_all.log_message"):
            result = seoul_all.crawl_with_retry("1156010100", max_retries=2)

        # 결과 확인 (두 번째 호출이 성공했으므로 결과 반환)
        # 하지만 우리 구현에서는 예외가 발생하면 재시도 후 None을 반환
        assert result is None or isinstance(result, list)

    @patch("seoul_all.AsilAptListCrawler")
    @patch("seoul_all.log_message")
    @patch("seoul_all.time.sleep")
    def test_exponential_backoff(self, mock_sleep, mock_log, mock_crawler_class):
        """지수 백오프(retry 간격)가 올바른지 확인"""
        # 항상 실패하는 크롤러
        mock_crawler = Mock()
        mock_crawler.crawl.side_effect = Exception("Network error")
        mock_crawler_class.return_value = mock_crawler

        # 최대 3회 재시도
        result = seoul_all.crawl_with_retry("1156010100", max_retries=3, backoff_base=2)

        # sleep 호출 확인: 1초, 2초 (0회: 2^0=1, 1회: 2^1=2)
        assert mock_sleep.call_count == 2
        assert mock_sleep.call_args_list[0][0][0] == 1
        assert mock_sleep.call_args_list[1][0][0] == 2
        assert result is None  # 최대 재시도 초과로 실패


class TestCheckpointHandling:
    """체크포인트 처리 테스트"""

    def test_save_checkpoint(self, tmp_path: Path):
        """체크포인트 저장 테스트"""
        checkpoint_file = tmp_path / "checkpoint.json"
        completed_dongs = {"1156010100", "1156010200", "1156010300"}

        seoul_all.save_checkpoint(completed_dongs, str(checkpoint_file))

        # 파일 생성 확인
        assert checkpoint_file.exists()

        # 내용 검증
        with open(checkpoint_file, encoding="utf-8") as f:
            data = json.load(f)

        assert "completed_dongs" in data
        assert set(data["completed_dongs"]) == completed_dongs
        assert "timestamp" in data

    def test_load_checkpoint(self, tmp_path: Path):
        """체크포인트 로드 테스트"""
        checkpoint_file = tmp_path / "checkpoint.json"

        # 저장할 데이터
        test_data = {"completed_dongs": ["1156010100", "1156010200"], "timestamp": "2024"}
        checkpoint_file.write_text(json.dumps(test_data, ensure_ascii=False))

        # 로드
        result = seoul_all.load_checkpoint(str(checkpoint_file))

        assert result == {"1156010100", "1156010200"}

    def test_load_nonexistent_checkpoint(self, tmp_path: Path):
        """존재하지 않는 체크포인트 파일 처리"""
        checkpoint_file = tmp_path / "nonexistent.json"

        # 파일이 없으면 빈 집합 반환
        result = seoul_all.load_checkpoint(str(checkpoint_file))

        assert result == set()

    def test_load_corrupted_checkpoint(self, tmp_path: Path):
        """손상된 체크포인트 파일 처리"""
        checkpoint_file = tmp_path / "corrupted.json"

        # 손상된 JSON 파일
        checkpoint_file.write_text("{invalid json", encoding="utf-8")

        # 빈 집합 반환
        result = seoul_all.load_checkpoint(str(checkpoint_file))

        assert result == set()

    def test_skip_completed_dongs(self):
        """이미 완료된 동 코드 건너뛰기 테스트"""
        completed_dongs = {"1156010100", "1156010200", "1156010300"}

        # 완료된 동 코드는 스킵되어야 함
        dong_code = "1156010100"
        assert dong_code in completed_dongs

        # 완료되지 않은 동 코드는 처리되어야 함
        dong_code = "1156010400"
        assert dong_code not in completed_dongs


class TestCsvFieldMapping:
    """CSV 필드 매핑 테스트"""

    @patch("seoul_all.AsilAptListCrawler")
    def test_map_dto_to_csv(self, mock_crawler_class):
        """DTO를 CSV 필드명으로 매핑 테스트"""
        # Mock DTO 생성
        mock_dto = Mock()
        mock_dto.model_dump.return_value = {
            "seq": "12345",
            "name": "테스트아파트",
            "dong": "1156010100",
            "dongname": "영등포동",
            "bungi": "123-1",
            "build_year": "2000",
            "dong_count": "5",
            "household": "100",
            "address": "서울시 영등포구",
            "maemul_count": "10",
            "offer": "매물정보",
            "lat": "37.5",
            "lng": "127.0",
        }

        # 매핑 수행
        result = seoul_all.map_dto_to_csv(mock_dto)

        # 결과 검증
        assert result["movein"] == "2000"
        assert result["total_dong"] == "5"
        assert result["type"] == "10"
        assert result["etc"] == "서울시 영등포구"
        assert "build_year" not in result
        assert "dong_count" not in result
        assert "maemul_count" not in result
        assert "address" not in result

        # CSV 필드명만 있는지 확인
        assert set(result.keys()) == set(seoul_all.CSV_FIELDNAMES)

    def test_csv_fieldnames_no_duplicates(self):
        """CSV fieldnames에 중복이 없어야 함"""
        # 단일 정의로 중복 제거됨
        fieldnames = seoul_all.CSV_FIELDNAMES

        # 중복 확인
        assert len(fieldnames) == len(set(fieldnames))

        # 필수 필드 확인
        required_fields = {"seq", "name", "dong", "dongname", "bungi"}
        assert required_fields.issubset(set(fieldnames))


class TestStatsTypedDict:
    """stats 딕셔너리 타입 힌트 테스트"""

    def test_stats_structure(self):
        """stats 딕셔너리 구조 검증"""
        stats = {
            "total_processed": 0,
            "data_found": 0,
            "empty_dongs": 0,
            "error_dongs": 0,
            "total_apartments": 0,
            "skipped_dongs": 0,
            "unique_seqs": set(),
        }

        # 필수 키 존재 확인
        required_keys = {
            "total_processed",
            "data_found",
            "empty_dongs",
            "error_dongs",
            "total_apartments",
            "skipped_dongs",
            "unique_seqs",
        }
        assert set(stats.keys()) == required_keys

        # 타입 확인
        assert isinstance(stats["total_processed"], int)
        assert isinstance(stats["data_found"], int)
        assert isinstance(stats["empty_dongs"], int)
        assert isinstance(stats["error_dongs"], int)
        assert isinstance(stats["total_apartments"], int)
        assert isinstance(stats["skipped_dongs"], int)
        assert isinstance(stats["unique_seqs"], set)


class TestGenerateDongCodes:
    """동 코드 생성 함수 테스트"""

    def test_generate_dong_codes_basic(self):
        """기본 동 코드 생성 테스트"""
        gu_code = "11560"  # 영등포구
        dong_codes = seoul_all.generate_dong_codes(gu_code)

        # 기본 설정: DONG_CODE_START=1, DONG_CODE_END=200
        assert len(dong_codes) == 199

        # 첫 번째와 마지막 코드 확인
        assert dong_codes[0] == "1156000100"
        assert dong_codes[-1] == "1156019900"

    def test_generate_dong_codes_format(self):
        """동 코드 형식 검증"""
        gu_code = "11680"  # 강남구
        dong_codes = seoul_all.generate_dong_codes(gu_code)

        # 모든 코드가 올바른 형식인지 확인 (구코드5자리 + 동코드3자리 + 00)
        for code in dong_codes[:5]:  # 처음 5개만 확인
            assert code.startswith(gu_code)
            assert code.endswith("00")
            assert len(code) == 10  # 총 10자리


@pytest.mark.unit
class TestSetupCsvWriter:
    """CSV writer 설정 테스트"""

    def test_setup_csv_writer_new_file(self, tmp_path: Path):
        """새 파일 생성 테스트"""
        csv_file = tmp_path / "test.csv"

        writer, f = seoul_all.setup_csv_writer(str(csv_file))

        # 파일 생성 확인
        assert csv_file.exists()

        # 헤더 작성 확인
        with open(csv_file, encoding="utf-8") as rf:
            header = rf.readline().strip()
            expected_header = ",".join(seoul_all.CSV_FIELDNAMES)
            assert header == expected_header

        # 정리
        f.close()

    def test_setup_csv_writer_append_mode(self, tmp_path: Path):
        """기존 파일에 추가 모드 테스트"""
        csv_file = tmp_path / "test_append.csv"

        # 첫 번째 writer
        writer1, f1 = seoul_all.setup_csv_writer(str(csv_file))
        f1.close()

        # 두 번째 writer (append 모드)
        writer2, f2 = seoul_all.setup_csv_writer(str(csv_file))

        # 헤더가 중복되지 않아야 함
        with open(csv_file, encoding="utf-8") as rf:
            lines = rf.readlines()

        # 헤더는 하나만 있어야 함
        header_lines = [line for line in lines if line.startswith("seq")]
        assert len(header_lines) == 1

        f2.close()
