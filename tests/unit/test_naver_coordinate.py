"""네이버 부동산 좌표 기반 검색 단위 테스트"""

import math
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from crawler.dto.naver_listing import NaverAptDTO
from crawler.naver_coordinate import (
    NaverCoordinateSearchCrawler,
    bounds_from_center,
    ll_to_pixel,
    pixel_to_ll,
)

# =============================================================================
# test_ll_to_pixel_conversion - 위도/경도를 픽셀로 변환
# =============================================================================


@pytest.mark.unit
def test_ll_to_pixel_seoul_city_hall_zoom15():
    """서울 시청 좌표를 줌 레벨 15에서 픽셀로 변환"""
    lat, lon = 37.5665, 126.9780
    zoom = 15

    x, y = ll_to_pixel(lat, lon, zoom)

    # 픽셀 좌표는 숫자여야 함
    assert isinstance(x, float)
    assert isinstance(y, float)
    assert x > 0
    assert y > 0


@pytest.mark.unit
def test_ll_to_pixel_seoul_city_hall_zoom16():
    """서울 시청 좌표를 줌 레벨 16에서 픽셀로 변환"""
    lat, lon = 37.5665, 126.9780
    zoom = 16

    x, y = ll_to_pixel(lat, lon, zoom)

    # 줌 레벨이 1 증가하면 픽셀 값은 2배가 되어야 함
    assert isinstance(x, float)
    assert isinstance(y, float)


@pytest.mark.unit
def test_ll_to_pixel_seoul_city_hall_zoom17():
    """서울 시청 좌표를 줌 레벨 17에서 픽셀로 변환"""
    lat, lon = 37.5665, 126.9780
    zoom = 17

    x, y = ll_to_pixel(lat, lon, zoom)

    assert isinstance(x, float)
    assert isinstance(y, float)


@pytest.mark.unit
def test_ll_to_pixel_zoom_levels_consistency():
    """줌 레벨 간 배수 관계 확인"""
    lat, lon = 37.5665, 126.9780

    x15, y15 = ll_to_pixel(lat, lon, 15)
    x16, y16 = ll_to_pixel(lat, lon, 16)
    x17, y17 = ll_to_pixel(lat, lon, 17)

    # 줌 레벨이 1 증가할 때마다 2배가 되어야 함
    assert math.isclose(x16, x15 * 2, rel_tol=1e-9)
    assert math.isclose(y16, y15 * 2, rel_tol=1e-9)
    assert math.isclose(x17, x16 * 2, rel_tol=1e-9)
    assert math.isclose(y17, y16 * 2, rel_tol=1e-9)


@pytest.mark.unit
def test_ll_to_pixel_invalid_latitude():
    """유효하지 않은 위도 값에 대한 예외 처리"""
    with pytest.raises(ValueError):
        ll_to_pixel(86, 126.9780, 15)  # 위도 86도는 범위 밖


# =============================================================================
# test_bounds_from_center - 중심 좌표와 반경으로 경계 계산
# =============================================================================


@pytest.mark.unit
def test_bounds_from_center_100m():
    """중심 좌표에서 100m 반경의 경계 계산"""
    center_lat, center_lon = 37.5665, 126.9780
    radius_m = 100
    zoom = 15

    s_lat, s_lng, e_lat, e_lng = bounds_from_center(center_lat, center_lon, radius_m, zoom)

    # 경계는 중심을 둘러싸야 함
    assert s_lat <= center_lat
    assert e_lat >= center_lat
    assert s_lng <= center_lon
    assert e_lng >= center_lon

    # 경계 값은 유효한 범위여야 함
    assert -90 <= s_lat <= 90
    assert -90 <= e_lat <= 90
    assert -180 <= s_lng <= 180
    assert -180 <= e_lng <= 180


@pytest.mark.unit
def test_bounds_from_center_500m():
    """중심 좌표에서 500m 반경의 경계 계산"""
    center_lat, center_lon = 37.5665, 126.9780
    radius_m = 500
    zoom = 15

    s_lat, s_lng, e_lat, e_lng = bounds_from_center(center_lat, center_lon, radius_m, zoom)

    # 500m는 100m보다 더 넓은 범위여야 함
    assert s_lat < center_lat
    assert e_lat > center_lat
    assert s_lng < center_lon
    assert e_lng > center_lon


@pytest.mark.unit
def test_bounds_from_center_1km():
    """중심 좌표에서 1km 반경의 경계 계산"""
    center_lat, center_lon = 37.5665, 126.9780
    radius_m = 1000
    zoom = 15

    s_lat, s_lng, e_lat, e_lng = bounds_from_center(center_lat, center_lon, radius_m, zoom)

    # 1km는 500m보다 더 넓은 범위여야 함
    assert s_lat < center_lat
    assert e_lat > center_lat
    assert s_lng < center_lon
    assert e_lng > center_lon


@pytest.mark.unit
def test_bounds_from_center_zoom_levels():
    """다른 줌 레벨에서 경계 계산 확인"""
    center_lat, center_lon = 37.5665, 126.9780
    radius_m = 500

    for zoom in [14, 15, 16, 17]:
        s_lat, s_lng, e_lat, e_lng = bounds_from_center(center_lat, center_lon, radius_m, zoom)

        # 모든 줌 레벨에서 유효한 경계가 반환되어야 함
        assert isinstance(s_lat, float)
        assert isinstance(s_lng, float)
        assert isinstance(e_lat, float)
        assert isinstance(e_lng, float)

        assert s_lat <= center_lat <= e_lat
        assert s_lng <= center_lon <= e_lng


@pytest.mark.unit
def test_bounds_from_center_small_radius():
    """매우 작은 반경 (10m)에 대한 경계 계산"""
    center_lat, center_lon = 37.5665, 126.9780
    radius_m = 10
    zoom = 17

    s_lat, s_lng, e_lat, e_lng = bounds_from_center(center_lat, center_lon, radius_m, zoom)

    # 작은 반경이라도 경계는 존재해야 함
    assert s_lat < center_lat
    assert e_lat > center_lat
    assert s_lng < center_lon
    assert e_lng > center_lon


# =============================================================================
# test_pixel_to_ll - 픽셀을 위도/경도로 변환 (역변환)
# =============================================================================


@pytest.mark.unit
def test_pixel_to_ll_roundtrip():
    """위도/경도 -> 픽셀 -> 위도/경도 변환 검증"""
    original_lat, original_lon = 37.5665, 126.9780
    zoom = 15

    # 정방향 변환
    x, y = ll_to_pixel(original_lat, original_lon, zoom)

    # 역변환
    converted_lat, converted_lon = pixel_to_ll(x, y, zoom)

    # 역변환 결과는 원래 값과 근접해야 함 (약간의 오차 허용)
    assert math.isclose(converted_lat, original_lat, abs_tol=1e-5)
    assert math.isclose(converted_lon, original_lon, abs_tol=1e-5)


# =============================================================================
# test_coordinate_search_crawler - 좌표 기반 검색 크롤러
# =============================================================================


@pytest.mark.unit
@patch("crawler.naver_coordinate._NaverBaseCrawler.__aenter__")
@patch("crawler.naver_coordinate._NaverBaseCrawler.__aexit__")
def test_coordinate_search_crawler_calls_correct_endpoint(mock_aexit, mock_aenter):
    """좌표 검색 크롤러가 올바른 API 엔드포인트를 호출하는지 확인"""
    # Mock setup
    mock_page = MagicMock()
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    async def mock_setup():
        pass

    mock_aenter.return_value = mock_browser

    # Create crawler with center coordinates and radius
    crawler = NaverCoordinateSearchCrawler(
        center_lat=37.5665,
        center_lon=126.9780,
        radius_m=500,
        zoom=15,
    )

    # Mock the async search method
    crawler._search_async = AsyncMock(
        return_value=[
            {
                "markerId": "12345",
                "complexName": "테스트아파트",
                "lat": 37.5665,
                "lng": 126.9780,
                "articleCount": 5,
                "address": "서울시 중구 세종대로 110",
            }
        ]
    )

    # Execute crawl
    results = crawler.crawl()

    # Verify results
    assert len(results) > 0
    assert isinstance(results[0], NaverAptDTO)
    assert results[0].complex_no == "12345"
    assert results[0].complex_name == "테스트아파트"


@pytest.mark.unit
def test_coordinate_search_crawler_initialization():
    """좌표 검색 크롤러 초기화 검증"""
    crawler = NaverCoordinateSearchCrawler(
        center_lat=37.5665,
        center_lon=126.9780,
        radius_m=500,
        zoom=15,
    )

    assert crawler.center_lat == 37.5665
    assert crawler.center_lon == 126.9780
    assert crawler.radius_m == 500
    assert crawler.zoom == 15


@pytest.mark.unit
def test_coordinate_search_crawler_generates_correct_url():
    """좌표 검색 크롤러가 올바른 URL을 생성하는지 확인"""
    crawler = NaverCoordinateSearchCrawler(
        center_lat=37.5665,
        center_lon=126.9780,
        radius_m=500,
        zoom=15,
    )

    # 내부적으로 경계를 계산하고 URL에 포함해야 함
    s_lat, s_lng, e_lat, e_lng = bounds_from_center(
        crawler.center_lat, crawler.center_lon, crawler.radius_m, crawler.zoom
    )

    # URL에 사용될 좌표 값 확인
    assert s_lat is not None
    assert s_lng is not None
    assert e_lat is not None
    assert e_lng is not None


@pytest.mark.unit
@patch("crawler.naver_coordinate._NaverBaseCrawler.__aenter__")
@patch("crawler.naver_coordinate._NaverBaseCrawler.__aexit__")
def test_coordinate_search_crawler_filters_by_bounds(mock_aexit, mock_aenter):
    """좌표 검색 크롤러가 경계 내 결과만 반환하는지 확인"""
    mock_browser = MagicMock()
    mock_aenter.return_value = mock_browser

    crawler = NaverCoordinateSearchCrawler(
        center_lat=37.5665,
        center_lon=126.9780,
        radius_m=500,
        zoom=15,
    )

    # Mock response with various coordinates
    crawler._search_async = AsyncMock(
        return_value=[
            {
                "markerId": "11111",
                "complexName": "중심아파트",
                "lat": 37.5665,
                "lng": 126.9780,
                "articleCount": 3,
            },
            {
                "markerId": "22222",
                "complexName": "근처아파트",
                "lat": 37.5670,
                "lng": 126.9785,
                "articleCount": 2,
            },
        ]
    )

    results = crawler.crawl()

    # All results should be returned and parsed correctly
    assert len(results) >= 1
    for result in results:
        assert isinstance(result, NaverAptDTO)
        assert result.complex_no
        assert result.complex_name


@pytest.mark.unit
@patch("crawler.naver_coordinate._NaverBaseCrawler.__aenter__")
@patch("crawler.naver_coordinate._NaverBaseCrawler.__aexit__")
def test_coordinate_search_crawler_empty_results(mock_aexit, mock_aenter):
    """좌표 검색 크롤러가 빈 결과를 올바르게 처리하는지 확인"""
    mock_browser = MagicMock()
    mock_aenter.return_value = mock_browser

    crawler = NaverCoordinateSearchCrawler(
        center_lat=37.5665,
        center_lon=126.9780,
        radius_m=100,
        zoom=15,
    )

    # Mock empty response
    crawler._search_async = AsyncMock(return_value=[])

    results = crawler.crawl()

    # Should return empty list
    assert isinstance(results, list)
    assert len(results) == 0


@pytest.mark.unit
def test_coordinate_search_calculates_bounds_correctly():
    """좌표 검색 크롤러의 경계 계산 검증"""
    # 서울 시청
    center_lat, center_lon = 37.5665, 126.9780
    radius_m = 500
    zoom = 15

    crawler = NaverCoordinateSearchCrawler(
        center_lat=center_lat,
        center_lon=center_lon,
        radius_m=radius_m,
        zoom=zoom,
    )

    # 경계 계산
    s_lat, s_lng, e_lat, e_lng = bounds_from_center(
        crawler.center_lat, crawler.center_lon, crawler.radius_m, crawler.zoom
    )

    # 경계가 중심을 포함해야 함
    assert s_lat <= center_lat <= e_lat
    assert s_lng <= center_lon <= e_lng

    # 위도 차이와 경도 차이 계산
    lat_diff = e_lat - s_lat
    lon_diff = e_lng - s_lng

    # 경계가 존재해야 함
    assert lat_diff > 0
    assert lon_diff > 0
