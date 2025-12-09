"""HogangnonoCrawler 기본 동작 테스트 (Smoke Tests)

MVP 접근법에 따른 기본적인 기능 검증 테스트
"""

import csv
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from crawler.config import CrawlerConfig
from crawler.crawlers.hogangnono import HogangnonoCrawler


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
def crawler(config):
    """테스트용 크롤러 객체"""
    # 임시 디렉토리 사용
    import tempfile
    import shutil

    temp_dir = Path(tempfile.mkdtemp())
    yield HogangnonoCrawler(config, output_dir=temp_dir)
    # 정리
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestHogangnonoCrawlerSmoke:
    """HogangnonoCrawler 기본 동작 테스트"""

    def test_crawler_initialization(self, crawler):
        """크롤러 초기화 테스트"""
        assert crawler is not None
        assert crawler.output_dir.exists()
        assert crawler.region_bounds is not None
        assert len(crawler.region_bounds) == 4  # lat_min, lng_min, lat_max, lng_max

    def test_get_endpoint(self, crawler):
        """API 엔드포인트 조회 테스트"""
        endpoint = crawler.get_endpoint()
        assert endpoint == "/api/apt/bounding"

    def test_get_params(self, crawler):
        """API 요청 파라미터 생성 테스트"""
        params = crawler.get_params()
        assert "lat_min" in params
        assert "lng_min" in params
        assert "lat_max" in params
        assert "lng_max" in params
        assert "zoom" in params
        assert "limit" in params
        assert params["apt_type"] == "apart"

    @patch("crawler.api.hogangnono_client.HogangnonoAPIClient.get_apartments_bounding")
    def test_parse_response_with_data(self, mock_api_call, crawler):
        """API 응답 파싱 테스트 - 데이터 있는 경우"""
        # Mock API 응답
        mock_response = Mock()
        mock_response.success = True
        mock_response.data = {
            "data": [
                {
                    "id": "test_id",
                    "name": "테스트 아파트",
                    "address": "서울시 강남구",
                    "lat": 37.5,
                    "lng": 127.0,
                    "build_year": 2020,
                    "households": 500,
                }
            ]
        }
        mock_api_call.return_value = mock_response

        # 파싱 테스트
        parsed = crawler.parse_response(mock_response.data)
        assert len(parsed) == 1
        assert parsed[0]["id"] == "test_id"
        assert parsed[0]["name"] == "테스트 아파트"

    def test_parse_response_empty_data(self, crawler):
        """API 응답 파싱 테스트 - 빈 데이터"""
        # 빈 응답
        parsed = crawler.parse_response({})
        assert len(parsed) == 0

        # 빈 리스트 응답
        parsed = crawler.parse_response([])
        assert len(parsed) == 0

    @patch("crawler.api.hogangnono_client.HogangnonoAPIClient.get_apartments_bounding")
    def test_crawl_region_success(self, mock_api_call, crawler):
        """지역 크롤링 성공 테스트"""
        # Mock API 응답 설정
        mock_response = Mock()
        mock_response.success = True
        mock_response.data = {
            "data": [
                {
                    "id": "complex_1",
                    "name": "테스트 단지",
                    "address": "서울시 강남구 테헤란로",
                    "lat": 37.5,
                    "lng": 127.0,
                    "build_year": 2020,
                    "households": 300,
                    "floors": 20,
                    "price": 100000000,
                    "area": 84.5,
                }
            ]
        }
        mock_api_call.return_value = mock_response

        # 크롤링 실행
        complexes, transactions = crawler.crawl_region(
            region_bounds=(37.4, 126.7, 37.7, 127.2), max_pages=1
        )

        # 결과 검증
        assert len(complexes) == 1
        assert complexes[0]["complex_id"] == "complex_1"
        assert complexes[0]["complex_name"] == "테스트 단지"

        assert len(transactions) == 1
        assert transactions[0]["id"] == "complex_1"

    def test_save_to_csv_creates_files(self, crawler):
        """CSV 저장 테스트 - 파일 생성"""
        # 테스트 데이터 (CSV 스키마에 맞는 필드명 사용)
        complexes = [
            {
                "complex_id": "test_complex",
                "complex_name": "테스트 단지",
                "real_estate_type": "아파트",
                "completion_year_month": "202001",
                "total_dong_count": 3,
                "total_household_count": 500,
            }
        ]

        transactions = [
            {
                "transaction_id": "test_tx",
                "complex_id": "test_complex",
                "deal_price": 100000000,
                "exclusive_area": 84.5,
                "transaction_type": "매매",
            }
        ]

        # CSV 저장
        crawler.save_to_csv(complexes, transactions)

        # 파일 생성 확인
        assert crawler.complex_writer.output_path.exists()
        assert crawler.transaction_writer.output_path.exists()

        # CSV 내용 확인
        with open(crawler.complex_writer.output_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["complex_id"] == "test_complex"

    @patch("crawler.api.hogangnono_client.HogangnonoAPIClient.get_apartments_bounding")
    def test_crawl_method_returns_stats(self, mock_api_call, crawler):
        """crawl 메서드 통계 반환 테스트"""
        # Mock 설정
        mock_response = Mock()
        mock_response.success = True
        mock_response.data = {"data": []}
        mock_api_call.return_value = mock_response

        # crawl 실행
        stats = crawler.crawl()

        # 통계 정보 확인
        assert "dongs_processed" in stats
        assert "total_complexes" in stats
        assert "total_transactions_collected" in stats
        assert isinstance(stats["dongs_processed"], int)
        assert isinstance(stats["total_complexes"], int)
        assert isinstance(stats["total_transactions_collected"], int)

    def test_fetch_apartments_bounding_returns_dummy_data(self, crawler):
        """fetch_apartments_bounding 더미 데이터 반환 테스트"""
        result = crawler.fetch_apartments_bounding("강남구")

        assert "status" in result
        assert "data" in result
        assert result["status"] == "success"
        assert result["data"]["district"] == "강남구"

    def test_parse_apartment_data_returns_dummy_data(self, crawler):
        """parse_apartment_data 더미 데이터 반환 테스트"""
        params = {"district": "강남구"}
        result = crawler.parse_apartment_data(None, params)

        assert len(result) > 0
        assert result[0]["name"] == "더미 아파트"
        assert "강남구" in result[0]["address"]

    def test_crawl_dynamic_with_url(self, crawler):
        """crawl_dynamic URL 테스트"""
        with patch("requests.get") as mock_get:
            # Mock 응답
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # headers 속성을 추가해야 함
            crawler.headers = {"User-Agent": "test-agent"}

            result = crawler.crawl_dynamic("http://example.com")

            assert len(result) > 0
            assert result[0]["url"] == "http://example.com"
            assert result[0]["status_code"] == 200

    def test_handle_rate_limit(self, crawler):
        """Rate limiting 처리 테스트"""
        import time

        start = time.time()
        crawler.handle_rate_limit()
        elapsed = time.time() - start

        # 최소 1초 대기 확인
        assert elapsed >= 1.0

    def test_validate_apartment_data(self, crawler):
        """아파트 데이터 검증 테스트"""
        # 유효한 데이터
        valid_data = {
            "id": "test",
            "name": "테스트",
            "address": "주소",
        }
        assert crawler.validate_apartment_data(valid_data) is True

        # 유효하지 않은 데이터
        invalid_data = {
            "id": "test",
            "name": "테스트",
            # address 누락
        }
        assert crawler.validate_apartment_data(invalid_data) is False
