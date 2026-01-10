"""Mercator projection 지리 좌표 변환 테스트"""

import pytest

from crawler.utils.geo import ll_to_pixel


@pytest.mark.unit
def test_ll_to_pixel_seoul():
    """서울 시청 좌표를 픽셀로 변환"""
    x, y = ll_to_pixel(37.5665, 126.9780, 15)
    # 줌 레벨 15에서 서울 시청 근처 픽셀 값
    assert isinstance(x, float)
    assert isinstance(y, float)
    assert x > 0
    assert y > 0


@pytest.mark.unit
def test_ll_to_pixel_equator():
    """적도 본초 자오선 교차점"""
    x, y = ll_to_pixel(0, 0, 1)
    # 줌 1에서 적도는 중앙
    scale = 256 * 2
    expected_x = 0.5 * scale
    expected_y = 0.5 * scale
    assert abs(x - expected_x) < 1
    assert abs(y - expected_y) < 1


@pytest.mark.unit
def test_ll_to_pixel_boundary():
    """위도 경계값 테스트 (85도 초과는 안 됨)"""
    # Mercator projection은 위도 ±85도까지만 유효
    with pytest.raises(ValueError):
        ll_to_pixel(86, 0, 10)
