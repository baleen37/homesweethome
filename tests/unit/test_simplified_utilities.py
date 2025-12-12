"""단순화된 유틸리티 테스트

retry.py와 bbox_division.py의 단순화된 기능을 테스트합니다.
"""

import time
from unittest.mock import Mock, patch

import pytest

from crawler.utils.retry import retry_with_delay
from crawler.utils.bbox_division import BBoxDivision


class TestRetryWithDelay:
    """retry_with_delay 함수 테스트"""

    def test_success_on_first_attempt(self):
        """첫 시도에 성공하는 경우"""
        mock_func = Mock(return_value="success")

        result = retry_with_delay(mock_func, max_attempts=3, delay=0.1)

        assert result == "success"
        mock_func.assert_called_once()

    def test_success_on_retry(self):
        """재시도 후 성공하는 경우"""
        mock_func = Mock(side_effect=[Exception("fail"), "success"])

        with patch("builtins.print"):
            result = retry_with_delay(mock_func, max_attempts=3, delay=0.1)

        assert result == "success"
        assert mock_func.call_count == 2

    def test_all_attempts_fail(self):
        """모든 시도가 실패하는 경우"""
        mock_func = Mock(side_effect=Exception("fail"))

        with patch("builtins.print"):
            with pytest.raises(Exception, match="fail"):
                retry_with_delay(mock_func, max_attempts=3, delay=0.1)

        assert mock_func.call_count == 3

    def test_custom_max_attempts_and_delay(self):
        """커스텀 max_attempts와 delay 값 테스트"""
        mock_func = Mock(side_effect=[Exception("fail1"), Exception("fail2"), "success"])

        start_time = time.time()
        result = retry_with_delay(mock_func, max_attempts=5, delay=0.05)
        end_time = time.time()

        assert result == "success"
        assert mock_func.call_count == 3
        # 2번의 실패로 인한 지연 시간 확인 (0.05 * 2 = 0.1초)
        assert end_time - start_time >= 0.1

    def test_with_arguments(self):
        """함수에 인자를 전달하는 경우"""
        mock_func = Mock(return_value="result")

        result = retry_with_delay(
            mock_func, max_attempts=3, delay=0.1, arg1="value1", arg2="value2", kwarg1="kwvalue1"
        )

        assert result == "result"
        mock_func.assert_called_once_with(arg1="value1", arg2="value2", kwarg1="kwvalue1")


class TestBBoxDivision:
    """BBoxDivision 클래스 테스트"""

    def test_divide_bbox_basic(self):
        """기본 bbox 분할 테스트"""
        divider = BBoxDivision()

        # 서울의 일부 지역 좌표
        lat_min, lng_min = 37.5, 126.9
        lat_max, lng_max = 37.6, 127.0

        bboxes = divider.divide_bbox(lat_min, lng_min, lat_max, lng_max)

        # 4x4 그리드이므로 16개의 bbox가 생성되어야 함
        assert len(bboxes) == 16

        # 첫 번째 bbox 확인
        first_bbox = bboxes[0]
        assert len(first_bbox) == 4
        assert first_bbox[0] == lat_min  # sub_lat_min
        assert first_bbox[1] == lng_min  # sub_lng_min

        # 마지막 bbox 확인
        last_bbox = bboxes[-1]
        assert last_bbox[2] == lat_max  # sub_lat_max
        assert last_bbox[3] == lng_max  # sub_lng_max

    def test_divide_bbox_coordinates(self):
        """분할된 bbox의 좌표 정확성 테스트"""
        divider = BBoxDivision()

        lat_min, lng_min = 0.0, 0.0
        lat_max, lng_max = 1.0, 1.0

        bboxes = divider.divide_bbox(lat_min, lng_min, lat_max, lng_max)

        # 첫 번째 행, 첫 번째 열
        assert bboxes[0] == (0.0, 0.0, 0.25, 0.25)

        # 두 번째 행, 첫 번째 열
        assert bboxes[4] == (0.25, 0.0, 0.5, 0.25)

        # 마지막 행, 마지막 열
        assert bboxes[-1] == (0.75, 0.75, 1.0, 1.0)

    def test_divide_bbox_negative_coordinates(self):
        """음수 좌표를 가진 bbox 분할 테스트"""
        divider = BBoxDivision()

        lat_min, lng_min = -1.0, -2.0
        lat_max, lng_max = 1.0, 0.0

        bboxes = divider.divide_bbox(lat_min, lng_min, lat_max, lng_max)

        assert len(bboxes) == 16

        # 첫 bbox 확인
        assert bboxes[0][0] == -1.0  # lat_min
        assert bboxes[0][1] == -2.0  # lng_min

        # 마지막 bbox 확인
        assert bboxes[-1][2] == 1.0  # lat_max
        assert bboxes[-1][3] == 0.0  # lng_max

    def test_divide_bbox_small_area(self):
        """아주 작은 영역 분할 테스트"""
        divider = BBoxDivision()

        lat_min, lng_min = 37.5001, 126.9001
        lat_max, lng_max = 37.5002, 126.9002

        bboxes = divider.divide_bbox(lat_min, lng_min, lat_max, lng_max)

        assert len(bboxes) == 16

        # 모든 bbox가 원래 범위 내에 있어야 함
        for bbox in bboxes:
            assert lat_min <= bbox[0] <= lat_max
            assert lng_min <= bbox[1] <= lng_max
            assert lat_min <= bbox[2] <= lat_max
            assert lng_min <= bbox[3] <= lng_max
