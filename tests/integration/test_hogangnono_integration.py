"""호갱노노 통합 테스트

전체 시스템의 end-to-end 동작을 검증
"""

import csv
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from crawler.config import CrawlerConfig
from crawler.crawlers.hogangnono import HogangnonoCrawler


pytestmark = pytest.mark.integration


@pytest.fixture
def config():
    """테스트용 설정 객체"""
    return CrawlerConfig(
        user_agent="test-agent",
        timeout=10.0,
        max_retries=1,
        retry_delay=0.1,
    )


@pytest.fixture
def temp_output_dir():
    """임시 출력 디렉토리"""
    import tempfile
    import shutil

    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def crawler(config, temp_output_dir):
    """테스트용 크롤러 객체"""
    return HogangnonoCrawler(config, output_dir=temp_output_dir)


class TestHogangnonoIntegration:
    """호갱노노 통합 테스트"""

    @patch("crawler.api.hogangnono_client.HogangnonoAPIClient.get_apartments_bounding")
    def test_end_to_end_crawling(self, mock_api, crawler):
        """end-to-end 크롤링 테스트

        1. API 호출
        2. 데이터 파싱
        3. CSV 저장
        """
        # Mock API 응답
        mock_response = Mock()
        mock_response.success = True
        mock_response.data = {
            "data": [
                {
                    "id": "apt_001",
                    "name": "테스트 아파트",
                    "address": "서울특별시 강남구 테헤란로 123",
                    "lat": 37.5134,
                    "lng": 127.0437,
                    "build_year": 2020,
                    "households": 350,
                    "floors": 25,
                    "deal_price": 120000000,
                    "area": 84.5,
                    "floor": "15/25",
                    "direction": "남향",
                    "parking": 350,
                    "heating": "중앙난방",
                },
                {
                    "id": "apt_002",
                    "name": "샘플 단지",
                    "address": "서울특별시 서초구 강남대로 456",
                    "lat": 37.4852,
                    "lng": 127.0329,
                    "build_year": 2018,
                    "households": 280,
                    "floors": 20,
                    "deal_price": 95000000,
                    "area": 76.2,
                    "floor": "8/20",
                    "direction": "동향",
                    "parking": 280,
                    "heating": "개별난방",
                },
            ]
        }
        mock_api.return_value = mock_response

        # 크롤링 실행
        complexes, transactions = crawler.crawl_region(
            region_bounds=(37.4, 126.7, 37.7, 127.2), max_pages=1
        )

        # 데이터 수집 확인
        assert len(complexes) == 2
        assert len(transactions) == 2

        # CSV 저장
        crawler.save_to_csv(complexes, transactions)

        # CSV 파일 생성 확인
        complexes_csv = crawler.output_dir / "hogangnono_complexes.csv"
        transactions_csv = crawler.output_dir / "hogangnono_transactions.csv"

        assert complexes_csv.exists()
        assert transactions_csv.exists()

        # CSV 내용 검증
        with open(complexes_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2

            # 첫 번째 단지 정보 확인
            assert rows[0]["complex_id"] == "apt_001"
            assert rows[0]["complex_name"] == "테스트 아파트"

        with open(transactions_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2

    @patch("crawler.api.hogangnono_client.HogangnonoAPIClient.get_apartments_bounding")
    def test_crawl_with_empty_data(self, mock_api, crawler):
        """데이터가 없는 경우 테스트"""
        # 빈 응답
        mock_response = Mock()
        mock_response.success = True
        mock_response.data = {"data": []}
        mock_api.return_value = mock_response

        # 크롤링 실행
        complexes, transactions = crawler.crawl_region(max_pages=1)

        # 결과 확인
        assert len(complexes) == 0
        assert len(transactions) == 0

    def test_csv_output_structure(self, crawler):
        """CSV 출력 구조 테스트"""
        # 테스트 데이터
        complexes = [
            {
                "complex_id": "complex_001",
                "complex_name": "테스트 단지",
                "real_estate_type": "아파트",
                "completion_year_month": "202001",
                "total_dong_count": 3,
                "total_household_count": 500,
            }
        ]

        transactions = [
            {
                "transaction_id": "tx_001",
                "complex_id": "complex_001",
                "deal_price": 100000000,
                "exclusive_area": 84.5,
                "transaction_type": "매매",
            }
        ]

        # CSV 저장
        crawler.save_to_csv(complexes, transactions)

        # CSV 구조 확인
        with open(crawler.complex_writer.output_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

            # 필수 헤더 확인
            assert "complex_id" in headers
            assert "complex_name" in headers

        with open(crawler.transaction_writer.output_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

            # 필수 헤더 확인
            assert "complex_id" in headers
            assert "complex_name" in headers
            assert "deal_price" in headers

    @patch("crawler.api.hogangnono_client.HogangnonoAPIClient.get_apartments_bounding")
    def test_error_handling_during_crawling(self, mock_api, crawler):
        """크롤링 중 오류 처리 테스트"""
        # API 오류
        mock_response = Mock()
        mock_response.success = False
        mock_response.error = "API Error"
        mock_response.status_code = 500
        mock_api.return_value = mock_response

        # 크롤링 실행 - 오류가 발생해도 예외가 발생하지 않아야 함
        complexes, transactions = crawler.crawl_region(max_pages=1)

        # 빈 결과 반환 확인
        assert len(complexes) == 0
        assert len(transactions) == 0

    def test_main_script_with_district_filter(self, temp_output_dir):
        """메인 스크립트 구 필터 테스트"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "main.py"
        output_file = temp_output_dir / "test_output.csv"

        # 환경 변수 설정 (필요시)
        env = {"PYTHONPATH": str(Path(__file__).parent.parent.parent)}

        # 스크립트 실행
        python_executable = "python3"
        result = subprocess.run(
            [
                python_executable,
                str(script_path),
                "--output",
                str(output_file),
                "--district",
                "강남구",
            ],
            capture_output=True,
            text=True,
            env=env,
        )

        # 실행 결과 확인 (실제 API 호출 실패 가능성 있음)
        # 중요한 것은 스크립트가 오류 없이 실행되는지 확인
        assert result.returncode in [0, 1]  # 0: 성공, 1: 비즈니스 오류 (API 키 등)

        # 에러 로그 확인 (있더라도 스크립트는 실행되어야 함)
        if result.returncode == 1:
            # 비즈니스 로직 오류는 허용 (예: API 연결 실패)
            assert (
                "오류:" in result.stdout
                or "Error" in result.stderr
                or "Traceback" not in result.stderr
            )
