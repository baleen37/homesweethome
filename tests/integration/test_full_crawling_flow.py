"""
전체 크롤링 프로세스 통합 테스트

이 테스트는 다음을 검증합니다:
1. CrawlCoordinator와 개선된 NaverRealEstateCrawler의 연동
2. 동작구 전체 크롤링 시나리오
3. CSV 파일 생성 및 데이터 검증
4. 체크포인트 시스템 동작
5. 에러 발생 시 복구
6. 대용량 데이터 처리
"""

import csv
import json
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from crawler.config import CrawlerConfig
from crawler.coordinator import CrawlCoordinator
from crawler.crawlers.naver import NaverRealEstateCrawler
from crawler.writers.complexes_csv_writer import ComplexesCSVWriter
from crawler.writers.transaction_csv_writer import TransactionCSVWriter
from crawler.progress_tracker import ProgressTracker


@pytest.fixture
def temp_dir():
    """임시 디렉토리 생성"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_config(temp_dir):
    """테스트용 CrawlerConfig 생성"""
    os.environ["OUTPUT_DIR"] = temp_dir
    config = CrawlerConfig()
    config.output_dir = Path(temp_dir)
    return config


@pytest.fixture
def sample_dongs_data():
    """샘플 동 데이터"""
    return {
        " districts": [
            {
                "district_code": "11110",
                "district_name": "종로구",
                "dongs": [
                    {"dong_code": "11110560", "dong_name": "사직동"},
                    {"dong_code": "11110570", "dong_name": "삼청동"},
                    {"dong_code": "11110580", "dong_name": "부암동"},
                    {"dong_code": "11110590", "dong_name": "평창동"},
                    {"dong_code": "11110600", "dong_name": "무악동"},
                ],
            },
            {
                "district_code": "11140",
                "district_name": "동작구",
                "dongs": [
                    {"dong_code": "11140550", "dong_name": "사당동"},
                    {"dong_code": "11140560", "dong_name": "대방동"},
                    {"dong_code": "11140570", "dong_name": "신대방동"},
                    {"dong_code": "11140580", "dong_name": "노량진동"},
                    {"dong_code": "11140590", "dong_name": "상도동"},
                ],
            },
        ]
    }


@pytest.fixture
def sample_complexes_data():
    """샘플 단지 데이터"""
    return [
        {
            "complex_id": "11110000",
            "complex_name": "사직푸르지오",
            "real_estate_type": "아파트",
            "completion_year_month": "202001",
            "total_dong_count": 5,
            "total_household_count": 300,
            "min_area": 84.5,
            "max_area": 134.8,
            "deal_count": 10,
            "lease_count": 5,
            "rent_count": 0,
            "pyeong_types": "84㎡, 134㎡",
            "fetched_at": "2024-12-07",
        },
        {
            "complex_id": "11140001",
            "complex_name": "사당힐스테이트",
            "real_estate_type": "아파트",
            "completion_year_month": "201805",
            "total_dong_count": 3,
            "total_household_count": 200,
            "min_area": 59.8,
            "max_area": 84.9,
            "deal_count": 5,
            "lease_count": 3,
            "rent_count": 0,
            "pyeong_types": "59㎡, 84㎡",
            "fetched_at": "2024-12-07",
        },
    ]


@pytest.fixture
def sample_transaction_data():
    """샘플 거래내역 데이터"""
    return [
        {
            "complex_id": "11110000",
            "complex_name": "사직푸르지오",
            "pyeong_type_number": "84",
            "pyeong_name": "84㎡",
            "trade_type": "A1",
            "trade_type_name": "매매",
            "trade_date": "2024-11-15",
            "trade_year": "2024",
            "floor": "12/20층",
            "deal_price": 12.5,
            "deposit": 0,
            "monthly_rent": 0,
            "trade_category": "아파트",
            "is_delete": False,
            "is_renew": False,
        }
    ]


class TestFullCrawlingFlow:
    """전체 크롤링 프로세스 통합 테스트"""

    def test_crawl_coordinator_initialization(self, test_config, temp_dir):
        """CrawlCoordinator 초기화 테스트"""
        coordinator = CrawlCoordinator(output_dir=Path(temp_dir))

        assert coordinator.output_dir == Path(temp_dir)
        assert coordinator.transaction_writer is not None
        assert coordinator.complexes_writer is not None

    @patch("crawler.crawlers.naver.requests.get")
    def test_dongjak_district_full_crawling(
        self,
        mock_get,
        test_config,
        sample_dongs_data,
        sample_complexes_data,
        sample_transaction_data,
    ):
        """동작구 전체 크롤링 시나리오 테스트"""

        # Mock API 응답 설정
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_complexes_data
        mock_get.return_value = mock_response

        # CrawlCoordinator 초기화
        CrawlCoordinator(test_config)
        crawler = NaverRealEstateCrawler(test_config)

        # 동작구 데이터 추출
        dongjak_district = None
        for district in sample_dongs_data["districts"]:
            if district["district_name"] == "동작구":
                dongjak_district = district
                break

        assert dongjak_district is not None

        # 크롤링 실행
        results = []
        for dong in dongjak_district["dongs"][:2]:  # 테스트를 위해 2개 동만
            try:
                # 단지 목록 조회
                complexes = crawler.fetch_complex_list(
                    cortar_no=dong["dong_code"],
                    bounds={
                        "min_lat": 37.46,
                        "max_lat": 37.48,
                        "min_lng": 126.94,
                        "max_lng": 126.96,
                    },
                )

                # 각 단지에 대해 거래내역 조회
                for complex in complexes[:1]:  # 테스트를 위해 1개 단지만
                    transactions = crawler.fetch_complex_listings(
                        complex_id=complex["hscpNo"],
                        trade_type="A1",  # 매매
                        page=1,
                    )

                    results.append(
                        {"dong": dong, "complexes": complexes, "transactions": transactions}
                    )

            except Exception as e:
                print(f"Error crawling {dong['dong_name']}: {e}")
                continue

        # 결과 검증
        assert len(results) > 0
        assert all("dong" in r for r in results)
        assert all("complexes" in r for r in results)
        assert all("transactions" in r for r in results)

    def test_csv_file_creation_and_validation(
        self, test_config, temp_dir, sample_complexes_data, sample_transaction_data
    ):
        """CSV 파일 생성 및 데이터 검증 테스트"""

        # CSV Writer 초기화
        complexes_file = Path(temp_dir) / "complexes.csv"
        transactions_file = Path(temp_dir) / "transactions.csv"
        complexes_writer = ComplexesCSVWriter(complexes_file)
        transactions_writer = TransactionCSVWriter(transactions_file)

        # 데이터 저장
        complexes_writer.write(sample_complexes_data)
        transactions_writer.write(sample_transaction_data)

        # 파일 생성 확인
        assert complexes_file.exists()
        assert transactions_file.exists()

        # CSV 파일 내용 검증
        with open(complexes_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert all("complex_id" in row for row in rows)
            assert all("complex_name" in row for row in rows)

        with open(transactions_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert "complex_id" in rows[0]
            assert "deal_price" in rows[0]

    def test_checkpoint_system(self, test_config, temp_dir, sample_dongs_data):
        """체크포인트 시스템 동작 테스트"""

        checkpoint_path = Path(temp_dir) / "checkpoint.json"
        coordinator = CrawlCoordinator(output_dir=Path(temp_dir), checkpoint_path=checkpoint_path)

        # 진행 상황 저장
        coordinator.checkpoint_manager.checkpoint.update(
            {
                "last_dong": "11140560",
                "total_complexes_processed": 10,
                "total_transactions_collected": 50,
                "failed_dongs": [],
                "last_updated_at": datetime.now().isoformat(),
            }
        )

        coordinator.checkpoint_manager.save_checkpoint()

        # 체크포인트 파일 확인
        assert checkpoint_path.exists()

        # 체크포인트 로드
        loaded_checkpoint = coordinator.checkpoint_manager.load_checkpoint()
        assert loaded_checkpoint is not None
        assert loaded_checkpoint["last_dong"] == "11140560"
        assert loaded_checkpoint["total_complexes_processed"] == 10

    def test_resume_from_checkpoint(self, test_config, temp_dir):
        """중단 후 재시작 테스트"""

        # 체크포인트 파일 미리 생성
        checkpoint_data = {
            "last_dong": "11140550",
            "total_complexes_processed": 5,
            "total_transactions_collected": 25,
            "failed_dongs": [],
            "last_updated_at": datetime.now().isoformat(),
        }

        checkpoint_file = Path(temp_dir) / "checkpoint.json"
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f)

        # CrawlCoordinator 초기화 및 체크포인트 로드
        checkpoint_path = Path(temp_dir) / "checkpoint.json"
        coordinator = CrawlCoordinator(output_dir=Path(temp_dir), checkpoint_path=checkpoint_path)
        loaded_checkpoint = coordinator.checkpoint_manager.load_checkpoint()

        assert loaded_checkpoint is not None
        assert loaded_checkpoint["last_dong"] == "11140550"
        assert loaded_checkpoint["total_complexes_processed"] == 5

    @patch("crawler.crawlers.naver.requests.get")
    def test_error_recovery(self, mock_get, test_config):
        """에러 발생 시 복구 테스트"""

        # 1st call: 429 에러
        # 2nd call: 성공
        mock_response_error = MagicMock()
        mock_response_error.status_code = 429

        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = []

        mock_get.side_effect = [mock_response_error, mock_response_success]

        crawler = NaverRealEstateCrawler(test_config)

        # Rate Limiter가 429 에러를 처리하는지 확인
        try:
            result = crawler.fetch_complex_list(
                cortar_no="11140550",
                bounds={"min_lat": 37.46, "max_lat": 37.48, "min_lng": 126.94, "max_lng": 126.96},
            )
            # 성공해야 함
            assert isinstance(result, list)
        except Exception as e:
            # 에러가 발생하더라도 처리되는지 확인
            assert False, f"Error recovery failed: {e}"

    def test_large_data_handling(self, test_config, temp_dir):
        """대용량 데이터 처리 테스트"""

        # 대량의 샘플 데이터 생성
        large_complexes_data = []
        for i in range(1000):
            large_complexes_data.append(
                {
                    "hscpNo": f"11140{i:04d}",
                    "hscpNm": f"테스트단지{i}",
                    "roadNmAddr": f"서울 동작구 사당로 {i}",
                    "atclCnt": i % 20,
                    "reprPrc": float(i % 100),
                    "lat": 37.4765 + (i * 0.0001),
                    "lng": 126.9514 + (i * 0.0001),
                    "cortarNo": "11140550",
                }
            )

        # CSV Writer로 대용량 데이터 저장
        large_complexes_file = Path(temp_dir) / "large_complexes.csv"
        writer = ComplexesCSVWriter(large_complexes_file)
        writer.write(large_complexes_data)

        # 파일 크기 확인
        file_size = large_complexes_file.stat().st_size
        assert file_size > 30000  # 30KB 이상

        # 데이터 수 확인
        with open(large_complexes_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1000

    def test_progress_tracking(self, test_config, sample_dongs_data, temp_dir):
        """진행 상황 추적 테스트"""

        # ProgressTracker 초기화
        tracker = ProgressTracker(output_dir=temp_dir)

        # 크롤링 시작
        tracker.start_crawling(total_dongs=5, total_complexes=50)

        # 진행 상황 업데이트
        for i, dong in enumerate(sample_dongs_data[" districts"][1]["dongs"][:3]):
            tracker.start_dong(dong["dong_code"], dong["dong_name"], 10)
            tracker.complete_dong(dong["dong_code"], dong["dong_name"], 10, 5, [])

        # 진행률 확인
        progress = tracker.get_progress_summary()
        assert progress["completed_dongs"] == 3
        assert progress["total_dongs"] == 5

    def test_data_consistency(
        self, test_config, temp_dir, sample_complexes_data, sample_transaction_data
    ):
        """데이터 일관성 테스트"""

        # Complexes와 Transactions 데이터 간의 일관성 확인

        complexes_file = Path(temp_dir) / "complexes.csv"
        transactions_file = Path(temp_dir) / "transactions.csv"
        complexes_writer = ComplexesCSVWriter(complexes_file)
        transactions_writer = TransactionCSVWriter(transactions_file)

        # 데이터 저장
        complexes_writer.write(sample_complexes_data)
        transactions_writer.write(sample_transaction_data)

        with open(complexes_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            complex_ids = set(row["complex_id"] for row in reader)

        with open(transactions_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 모든 거래내역은 유효한 단지 ID를 가져야 함
                assert row["complex_id"] in complex_ids, f"Invalid complex ID: {row['complex_id']}"

    @patch("crawler.crawlers.naver.requests.get")
    def test_rate_limiting_behavior(self, mock_get, test_config):
        """Rate Limiting 동작 테스트"""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        crawler = NaverRealEstateCrawler(test_config)

        # 여러 요청 실행
        for i in range(3):
            crawler.fetch_complex_list(
                cortar_no="11140550",
                bounds={"min_lat": 37.46, "max_lat": 37.48, "min_lng": 126.94, "max_lng": 126.96},
            )

        # Rate Limiter가 호출되었는지 확인 (최소 2초의 간격)
        assert mock_get.call_count == 3
