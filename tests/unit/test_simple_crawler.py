"""SimpleCrawler 단위 테스트"""

from unittest.mock import Mock, patch
import pytest

from crawler.crawlers.simple_crawler import SimpleCrawler
from crawler.api.hogangnono_client import APIResponse


@pytest.fixture
def temp_output_dir(tmp_path):
    """임시 출력 디렉토리"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def simple_crawler(temp_output_dir):
    """테스트용 SimpleCrawler 객체"""
    return SimpleCrawler(
        output_dir=str(temp_output_dir),
        region_bounds=(37.5, 126.9, 37.6, 127.0),
    )


class TestSimpleCrawler:
    """SimpleCrawler 테스트 클래스"""

    def test_init(self, simple_crawler, temp_output_dir):
        """초기화 테스트"""
        assert simple_crawler.region_bounds == (37.5, 126.9, 37.6, 127.0)
        assert simple_crawler.output_dir == temp_output_dir
        assert simple_crawler.output_dir.exists()
        assert simple_crawler.base_url == "https://hogangnono.com"

    def test_get_endpoint(self, simple_crawler):
        """엔드포인트 조회 테스트"""
        assert simple_crawler.get_endpoint() == "/api/apt/bounding"

    def test_get_params(self, simple_crawler):
        """파라미터 조회 테스트"""
        params = simple_crawler.get_params()
        assert params["lat_min"] == 37.5
        assert params["lng_min"] == 126.9
        assert params["lat_max"] == 37.6
        assert params["lng_max"] == 127.0
        assert params["zoom"] == 14
        assert params["limit"] == 100
        assert params["apt_type"] == "apart"

    def test_divide_bbox_simple(self, simple_crawler):
        """단순 bbox 분할 테스트"""
        bboxes = simple_crawler.divide_bbox_simple(37.5, 126.9, 37.7, 127.1, grid_size=2)

        # 2x2 그리드는 4개의 bbox 생성
        assert len(bboxes) == 4

        # 첫 번째 bbox 확인
        assert bboxes[0] == (37.5, 126.9, 37.6, 127.0)

        # 마지막 bbox 확인
        assert bboxes[3] == (37.6, 127.0, 37.7, 127.1)

    @patch("crawler.crawlers.simple_crawler.HogangnonoAPIClient")
    def test_fetch_apartments_from_bbox_success(self, mock_api_client_class, simple_crawler):
        """bbox에서 아파트 조회 성공 테스트"""
        # Mock API 클라이언트 설정
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        # Mock 응답 설정
        mock_response = APIResponse(
            success=True,
            data={
                "data": [
                    {"id": "1", "name": "테스트아파트", "category": 2, "address": "서울시"},
                    {"id": "2", "name": "상가A", "category": 1},  # 카테고리가 1이고 아파트가 아님
                ]
            },
        )
        mock_api_client.get_apartments_bounding.return_value = mock_response

        # SimpleCrawler의 api_client를 mock으로 교체
        simple_crawler.api_client = mock_api_client

        # bbox에서 아파트 조회
        apartments = simple_crawler.fetch_apartments_from_bbox((37.5, 126.9, 37.6, 127.0))

        # 결과 확인
        assert len(apartments) == 1
        assert apartments[0]["name"] == "테스트아파트"
        assert apartments[0]["id"] == "1"

    @patch("crawler.crawlers.simple_crawler.HogangnonoAPIClient")
    def test_fetch_apartments_from_bbox_failure(self, mock_api_client_class, simple_crawler):
        """bbox에서 아파트 조회 실패 테스트"""
        # Mock API 클라이언트 설정
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        # 실패 응답 설정
        mock_response = APIResponse(success=False, error="API Error")
        mock_api_client.get_apartments_bounding.return_value = mock_response

        # SimpleCrawler의 api_client를 mock으로 교체
        simple_crawler.api_client = mock_api_client

        # bbox에서 아파트 조회
        apartments = simple_crawler.fetch_apartments_from_bbox((37.5, 126.9, 37.6, 127.0))

        # 결과 확인
        assert len(apartments) == 0

    @patch("crawler.crawlers.simple_crawler.HogangnonoCSVWriter")
    @patch("crawler.crawlers.simple_crawler.HogangnonoDataMapper")
    def test_save_apartment_info(
        self, mock_data_mapper_class, mock_csv_writer_class, simple_crawler
    ):
        """아파트 정보 저장 테스트"""
        # Mock 설정
        mock_csv_writer = Mock()
        mock_csv_writer_class.return_value = mock_csv_writer

        simple_crawler.csv_writer = mock_csv_writer

        # 테스트 데이터
        apt = {
            "id": "123",
            "name": "테스트아파트",
            "address": "서울시 강남구",
            "lng": "127.0",
            "lat": "37.5",
            "category": "2",
            "description": "테스트",
            "dong": "개포동",
        }

        # 아파트 정보 저장
        simple_crawler.save_apartment_info(apt, "강남구")

        # 저장 함수 호출 확인
        mock_csv_writer.save_complexes.assert_called_once()
        args = mock_csv_writer.save_complexes.call_args[0][0]
        assert len(args) == 1
        assert args[0]["aptName"] == "테스트아파트"
        assert args[0]["aptSeq"] == "APT_123"
        assert args[0]["districtName"] == "강남구"

    @patch("crawler.crawlers.simple_crawler.HogangnonoAPIClient")
    @patch("crawler.crawlers.simple_crawler.HogangnonoCSVWriter")
    def test_fetch_and_save_transactions(
        self, mock_csv_writer_class, mock_api_client_class, simple_crawler
    ):
        """실거래 내역 조회 및 저장 테스트"""
        # Mock 설정
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client
        simple_crawler.api_client = mock_api_client

        mock_csv_writer = Mock()
        mock_csv_writer_class.return_value = mock_csv_writer
        simple_crawler.csv_writer = mock_csv_writer

        # Mock 응답 설정
        mock_response = APIResponse(
            success=True,
            data={
                "shortTermReport": [
                    {
                        "date": "2024-01-15",
                        "averagePrice": 100000,
                        "minPrice": 90000,
                        "maxPrice": 110000,
                        "volume": 5,
                    }
                ]
            },
        )
        mock_api_client.get_apartment_transactions.return_value = mock_response

        # 실거래 내역 조회 및 저장
        simple_crawler.fetch_and_save_transactions("123", "테스트아파트")

        # API 호출 확인
        mock_api_client.get_apartment_transactions.assert_called_once()

        # 저장 함수 호출 확인
        mock_csv_writer.save_transactions.assert_called_once()
        transactions = mock_csv_writer.save_transactions.call_args[0][0]
        assert len(transactions) == 1
        assert transactions[0]["complex_id"] == "123"
        assert transactions[0]["complex_name"] == "테스트아파트"
        assert transactions[0]["deal_price"] == 100000

    def test_fetch_and_save_transactions_invalid_id(self, simple_crawler):
        """유효하지 않은 ID로 실거래 내역 조회 테스트"""
        # ID가 숫자가 아닌 경우
        simple_crawler.fetch_and_save_transactions("invalid", "테스트아파트")

        # 이미 실패 기록이 있는 ID
        simple_crawler.invalid_apartments.add("456")
        simple_crawler.fetch_and_save_transactions("456", "테스트아파트2")

    @patch("crawler.crawlers.simple_crawler.HogangnonoAPIClient")
    @patch("crawler.crawlers.simple_crawler.CheckpointManager")
    def test_filter_districts_default(
        self, mock_checkpoint_class, mock_api_client_class, simple_crawler
    ):
        """지역 필터링 기본값 테스트 (서울만)"""
        # Mock API 클라이언트 설정
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        # Mock 응답 설정
        mock_response = APIResponse(
            success=True,
            data={
                "regionList": [
                    {
                        "regionCode": "11",
                        "name": "서울특별시",
                        "children": [
                            {"regionCode": "11010", "name": "종로구"},
                            {"regionCode": "11020", "name": "중구"},
                        ],
                    },
                    {
                        "regionCode": "41",
                        "name": "경기도",
                        "children": [
                            {"regionCode": "41110", "name": "수원시"},
                        ],
                    },
                ]
            },
        )
        mock_api_client.get_regions.return_value = mock_response
        simple_crawler.api_client = mock_api_client

        # 지역 필터링
        districts = simple_crawler._filter_districts(
            mock_response.data, regions=None, districts=None
        )

        # 서울의 구만 반환되는지 확인
        assert len(districts) == 2
        assert districts[0]["name"] == "종로구"
        assert districts[1]["name"] == "중구"

    @patch("crawler.crawlers.simple_crawler.HogangnonoAPIClient")
    @patch("crawler.crawlers.simple_crawler.CheckpointManager")
    def test_filter_districts_with_districts(
        self, mock_checkpoint_class, mock_api_client_class, simple_crawler
    ):
        """특정 구/군 필터링 테스트"""
        # Mock API 클라이언트 설정
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        # Mock 응답 설정
        mock_response = APIResponse(
            success=True,
            data={
                "regionList": [
                    {
                        "regionCode": "11",
                        "name": "서울특별시",
                        "children": [
                            {"regionCode": "11010", "name": "종로구"},
                            {"regionCode": "11020", "name": "중구"},
                            {"regionCode": "11040", "name": "용산구"},
                        ],
                    }
                ]
            },
        )
        mock_api_client.get_regions.return_value = mock_response
        simple_crawler.api_client = mock_api_client

        # 특정 구만 필터링
        districts = simple_crawler._filter_districts(
            mock_response.data, regions=None, districts=["종로구", "용산구"]
        )

        # 선택된 구만 반환되는지 확인
        assert len(districts) == 2
        assert districts[0]["name"] == "종로구"
        assert districts[1]["name"] == "용산구"
