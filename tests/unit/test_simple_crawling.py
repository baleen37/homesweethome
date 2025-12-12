"""단순화된 크롤링 기능 테스트"""

from unittest.mock import patch

from crawler.config import Config
from crawler.api.hogangnono_client import HogangnonoAPIClient
from crawler.utils.bbox_division import BBoxDivision


class TestSimpleCrawling:
    """성능 최적화 제거 후 기본 크롤링 기능 테스트"""

    def test_bbox_division_fixed_grid(self):
        """BBox 분할이 고정 4x4 그리드로 동작하는지 확인"""
        divider = BBoxDivision()

        # 서울 지역 좌표
        lat_min, lng_min = 37.413294, 126.734086
        lat_max, lng_max = 37.715133, 127.183394

        bboxes = divider.divide_bbox(lat_min, lng_min, lat_max, lng_max)

        # 정확히 16개(4x4) 그리드로 분할되어야 함
        assert len(bboxes) == 16

        # 첫 번째 bbox 확인
        first_bbox = bboxes[0]
        assert len(first_bbox) == 4
        assert first_bbox[0] == lat_min  # sub_lat_min
        assert first_bbox[1] == lng_min  # sub_lng_min

        # 마지막 bbox 확인
        last_bbox = bboxes[-1]
        assert len(last_bbox) == 4
        assert last_bbox[2] == lat_max  # sub_lat_max
        assert last_bbox[3] == lng_max  # sub_lng_max

    def test_api_client_basic_delay(self):
        """API 클라이언트가 기본 딜레이를 적용하는지 확인"""
        config = Config()
        client = HogangnonoAPIClient(config)

        with patch("time.sleep") as mock_sleep:
            # API 호출 시도 - 실패해도 상관없음
            try:
                client._make_request("GET", "/test")
            except Exception:
                pass

            # sleep이 1초로 호출되었는지 확인
            mock_sleep.assert_called_with(1.0)

    def test_no_cache_in_api_client(self):
        """API 클라이언트에 캐시 기능이 없는지 확인"""
        config = Config()
        client = HogangnonoAPIClient(config)

        # 캐시 관련 속성이 없어야 함
        assert not hasattr(client, "cache")
        assert not hasattr(client, "cache_dir")

    def test_api_client_removed_statistics(self):
        """API 클라이언트에 통계 수집 기능이 없는지 확인"""
        config = Config()
        client = HogangnonoAPIClient(config)

        # 통계 관련 메서드가 없어야 함
        assert not hasattr(client, "get_api_stats")
        assert not hasattr(client, "response_stats")

    def test_simple_error_handler_exists(self):
        """단순화된 에러 핸들러가 존재하는지 확인"""
        from crawler.utils.simple_error_handler import SimpleErrorHandler

        # SimpleErrorHandler가 임포트되어야 함
        assert SimpleErrorHandler is not None

        # 인스턴스 생성 테스트
        error_handler = SimpleErrorHandler(max_retries=3, retry_delay=1.0)
        assert error_handler.max_retries == 3
        assert error_handler.retry_delay == 1.0
