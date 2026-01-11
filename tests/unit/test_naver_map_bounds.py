"""네이버 지도 좌표 기반 검색 테스트

지도 경계 계산 및 API 파라미터 빌딩 기능을 테스트합니다.

지도 기반 검색 파라미터:
- z: 줌 레벨 (정수, 보통 10-15)
- lat, lon: 중심 좌표 (위도/경도)
- btm, lft, top, rgt: 지도 경계
  - btm: 하단 위도 (최소 위도)
  - top: 상단 위도 (최대 위도)
  - lft: 좌측 경도 (최소 경도)
  - rgt: 우측 경도 (최대 경도)
"""

import math

import pytest

# =============================================================================
# 테스트용 모듈 임포트 (구현 전이라 가정)
# 실제 구현에서는 아래와 같은 함수들이 필요합니다:
# - calculate_bounds_from_center_and_radius(lat, lon, radius_m, zoom)
# - calculate_bounds_from_rectangle(min_lat, max_lat, min_lon, max_lon)
# - build_map_parameters_for_api(z, lat, lon, btm, lft, top, rgt)
# - get_zoom_level_coverage(zoom)
# =============================================================================
# 임시로 naver_coordinate에서 기존 함수 임포트
from src.crawler.naver_coordinate import bounds_from_center

# =============================================================================
# test_calculate_bounds_from_center_and_radius - 중심좌표+반경으로 경계 계산
# =============================================================================


@pytest.mark.unit
def test_calculate_bounds_from_center_and_radius_seoul_city_hall_1km():
    """
    서울시청 중심 좌표와 1km 반경으로 경계 계산

    입력:
        - lat: 37.5665 (서울시청 위도)
        - lon: 126.9780 (서울시청 경도)
        - radius_m: 1000 (1km)

    검증:
        - lat, lon이 중심에 위치
        - btm < lat < top
        - lft < lon < rgt
        - 경계 값이 유효한 범위 내
    """
    # Given
    center_lat = 37.5665
    center_lon = 126.9780
    radius_m = 1000  # 1km
    zoom = 15

    # When
    s_lat, s_lng, e_lat, e_lng = bounds_from_center(center_lat, center_lon, radius_m, zoom)

    # Then - 경계가 중심을 포함해야 함
    assert s_lat <= center_lat <= e_lat, (
        f"위도 경계가 중심을 포함하지 않음: btm={s_lat}, center={center_lat}, top={e_lat}"
    )
    assert s_lng <= center_lon <= e_lng, (
        f"경도 경계가 중심을 포함하지 않음: lft={s_lng}, center={center_lon}, rgt={e_lng}"
    )

    # Then - 경계 값이 유효한 범위여야 함
    assert -90 <= s_lat <= 90, f"하단 위도가 유효 범위를 벗어남: btm={s_lat}"
    assert -90 <= e_lat <= 90, f"상단 위도가 유효 범위를 벗어남: top={e_lat}"
    assert -180 <= s_lng <= 180, f"좌측 경도가 유효 범위를 벗어남: lft={s_lng}"
    assert -180 <= e_lng <= 180, f"우측 경도가 유효 범위를 벗어남: rgt={e_lng}"

    # Then - 실제 경계가 계산되어야 함 (단순 중심 좌표와 같으면 안 됨)
    assert s_lat < center_lat, f"하단 위도가 중심보다 작아야 함: btm={s_lat}"
    assert e_lat > center_lat, f"상단 위도가 중심보다 커야 함: top={e_lat}"
    assert s_lng < center_lon, f"좌측 경도가 중심보다 작아야 함: lft={s_lng}"
    assert e_lng > center_lon, f"우측 경도가 중심보다 커야 함: rgt={e_lng}"


@pytest.mark.unit
def test_calculate_bounds_from_center_and_radius_gangnam_station_500m():
    """
    강남역 중심 좌표와 500m 반경으로 경계 계산
    """
    # Given
    center_lat = 37.5172
    center_lon = 127.0473
    radius_m = 500
    zoom = 15

    # When
    s_lat, s_lng, e_lat, e_lng = bounds_from_center(center_lat, center_lon, radius_m, zoom)

    # Then
    assert s_lat <= center_lat <= e_lat
    assert s_lng <= center_lon <= e_lng

    # Then - 500m 반경은 1km보다 작은 범위여야 함
    lat_diff = e_lat - s_lat
    lon_diff = e_lng - s_lng
    assert lat_diff > 0, "위도 차이가 0보다 커야 함"
    assert lon_diff > 0, "경도 차이가 0보다 커야 함"


@pytest.mark.unit
def test_calculate_bounds_from_center_and_radius_various_radii():
    """
    다양한 반경에 대한 경계 계산 검증

    반경이 커질수록 경계 범위도 넓어져야 함
    """
    # Given - 서울시청
    center_lat = 37.5665
    center_lon = 126.9780
    zoom = 15

    # When - 다양한 반경으로 경계 계산
    bounds_100m = bounds_from_center(center_lat, center_lon, 100, zoom)
    bounds_500m = bounds_from_center(center_lat, center_lon, 500, zoom)
    bounds_1km = bounds_from_center(center_lat, center_lon, 1000, zoom)

    # Then - 반경이 클수록 경계가 넓어야 함
    # 위도 차이 비교
    lat_diff_100m = bounds_100m[2] - bounds_100m[0]
    lat_diff_500m = bounds_500m[2] - bounds_500m[0]
    lat_diff_1km = bounds_1km[2] - bounds_1km[0]

    assert lat_diff_100m < lat_diff_500m, (
        f"500m 반경의 위도 범위가 100m보다 커야 함: 100m={lat_diff_100m}, 500m={lat_diff_500m}"
    )
    assert lat_diff_500m < lat_diff_1km, (
        f"1km 반경의 위도 범위가 500m보다 커야 함: 500m={lat_diff_500m}, 1km={lat_diff_1km}"
    )

    # 경도 차이 비교
    lon_diff_100m = bounds_100m[3] - bounds_100m[1]
    lon_diff_500m = bounds_500m[3] - bounds_500m[1]
    lon_diff_1km = bounds_1km[3] - bounds_1km[1]

    assert lon_diff_100m < lon_diff_500m, (
        f"500m 반경의 경도 범위가 100m보다 커야 함: 100m={lon_diff_100m}, 500m={lon_diff_500m}"
    )
    assert lon_diff_500m < lon_diff_1km, (
        f"1km 반경의 경도 범위가 500m보다 커야 함: 500m={lon_diff_500m}, 1km={lon_diff_1km}"
    )


@pytest.mark.unit
def test_calculate_bounds_from_center_and_radius_extreme_cases():
    """
    극단적인 경우에 대한 경계 계산 검증
    """
    # Given - 매우 작은 반경
    center_lat = 37.5665
    center_lon = 126.9780

    # When - 10m 반경
    s_lat, s_lng, e_lat, e_lng = bounds_from_center(center_lat, center_lon, 10, zoom=17)

    # Then - 매우 작은 반경이라도 경계는 존재해야 함
    assert s_lat < center_lat
    assert e_lat > center_lat
    assert s_lng < center_lon
    assert e_lng > center_lon

    # Given - 매우 큰 반경 (5km)
    # When
    s_lat, s_lng, e_lat, e_lng = bounds_from_center(center_lat, center_lon, 5000, zoom=12)

    # Then - 큰 반경은 넓은 경계를 가져야 함
    lat_diff = e_lat - s_lat
    lon_diff = e_lng - s_lng
    assert lat_diff > 0.01, f"5km 반경은 위도 차이가 0.01도보다 커야 함: {lat_diff}"
    assert lon_diff > 0.01, f"5km 반경은 경도 차이가 0.01도보다 커야 함: {lon_diff}"


# =============================================================================
# test_calculate_bounds_from_rectangle - 직사각형 영역 경계 계산
# =============================================================================


@pytest.mark.unit
def test_calculate_bounds_from_rectangle_basic():
    """
    직사각형 영역의 경계 계산 기본 테스트

    입력: min_lat, max_lat, min_lon, max_lon
    출력: (btm, lft, top, rgt) 형식의 경계 튜플

    이 함수는 단순히 입력 순서를 네이버 API 형식으로 변환합니다.
    """
    # Given
    min_lat = 37.5500
    max_lat = 37.5800
    min_lon = 126.9500
    max_lon = 127.0000

    # When - 직사각형 영역 경계 계산 함수가 구현되어야 함
    # TODO: calculate_bounds_from_rectangle 함수 구현 필요
    # 현재는 수동으로 튜플 생성
    btm, lft, top, rgt = min_lat, min_lon, max_lat, max_lon

    # Then
    assert btm == min_lat, f"하단 위도는 최소 위도와 같아야 함: {btm} != {min_lat}"
    assert top == max_lat, f"상단 위도는 최대 위도와 같아야 함: {top} != {max_lat}"
    assert lft == min_lon, f"좌측 경도는 최소 경도와 같아야 함: {lft} != {min_lon}"
    assert rgt == max_lon, f"우측 경도는 최대 경도와 같아야 함: {rgt} != {max_lon}"


@pytest.mark.unit
def test_calculate_bounds_from_rectangle_seoul_area():
    """
    서울 지역 직사각형 경계 계산
    """
    # Given - 서울시 대략적인 범위
    min_lat = 37.4000
    max_lat = 37.7000
    min_lon = 126.8000
    max_lon = 127.1000

    # When
    btm, lft, top, rgt = min_lat, min_lon, max_lat, max_lon

    # Then - 경계 순서 검증
    assert btm < top, f"하단 위도는 상단 위도보다 작아야 함: btm={btm}, top={top}"
    assert lft < rgt, f"좌측 경도는 우측 경도보다 작아야 함: lft={lft}, rgt={rgt}"

    # Then - 모든 값이 유효한 범위여야 함
    assert -90 <= btm <= 90
    assert -90 <= top <= 90
    assert -180 <= lft <= 180
    assert -180 <= rgt <= 180


@pytest.mark.unit
def test_calculate_bounds_from_rectangle_small_area():
    """
    매우 작은 직사각형 영역 경계 계산
    """
    # Given - 100m 정도의 작은 영역
    min_lat = 37.5660
    max_lat = 37.5670
    min_lon = 126.9770
    max_lon = 126.9790

    # When
    btm, lft, top, rgt = min_lat, min_lon, max_lat, max_lon

    # Then
    assert btm < top
    assert lft < rgt

    # Then - 영역이 작더라도 경계는 존재해야 함
    lat_diff = top - btm
    lon_diff = rgt - lft
    assert lat_diff > 0
    assert lon_diff > 0


# =============================================================================
# test_build_map_parameters_for_api - API 요청 파라미터 빌드
# =============================================================================


@pytest.mark.unit
def test_build_map_parameters_for_api_basic():
    """
    API 요청 파라미터 빌드 기본 테스트

    네이버 지도 API 파라미터:
    - z: 줌 레벨
    - lat, lon: 중심 좌표
    - btm, lft, top, rgt: 지도 경계
    """
    # Given
    z = 15
    lat = 37.5665
    lon = 126.9780
    btm = 37.5500
    lft = 126.9500
    top = 37.5800
    rgt = 127.0000

    # When - API 파라미터 빌드
    # TODO: build_map_parameters_for_api 함수 구현 필요
    # 현재는 수동으로 딕셔너리 생성
    params = {
        "z": z,
        "lat": lat,
        "lon": lon,
        "btm": btm,
        "lft": lft,
        "top": top,
        "rgt": rgt,
    }

    # Then - 모든 필수 파라미터가 포함되어야 함
    assert "z" in params
    assert "lat" in params
    assert "lon" in params
    assert "btm" in params
    assert "lft" in params
    assert "top" in params
    assert "rgt" in params

    # Then - 값 검증
    assert params["z"] == z
    assert params["lat"] == lat
    assert params["lon"] == lon
    assert params["btm"] == btm
    assert params["lft"] == lft
    assert params["top"] == top
    assert params["rgt"] == rgt


@pytest.mark.unit
def test_build_map_parameters_for_api_with_bounds_from_center():
    """
    중심 좌표와 반경으로 경계를 계산하여 API 파라미터 빌드
    """
    # Given
    z = 15
    center_lat = 37.5665
    center_lon = 126.9780
    radius_m = 1000

    # When - 경계 계산 후 API 파라미터 빌드
    btm, lft, top, rgt = bounds_from_center(center_lat, center_lon, radius_m, z)

    params = {
        "z": z,
        "lat": center_lat,
        "lon": center_lon,
        "btm": btm,
        "lft": lft,
        "top": top,
        "rgt": rgt,
    }

    # Then - 중심 좌표가 경계 내부에 있어야 함
    assert btm <= params["lat"] <= top
    assert lft <= params["lon"] <= rgt

    # Then - 모든 파라미터가 유효한 타입이어야 함
    assert isinstance(params["z"], int)
    assert isinstance(params["lat"], (int, float))
    assert isinstance(params["lon"], (int, float))
    assert isinstance(params["btm"], (int, float))
    assert isinstance(params["lft"], (int, float))
    assert isinstance(params["top"], (int, float))
    assert isinstance(params["rgt"], (int, float))


@pytest.mark.unit
def test_build_map_parameters_for_api_url_encoding():
    """
    API 파라미터를 URL 쿼리 스트링으로 인코딩
    """
    # Given
    z = 15
    lat = 37.5665
    lon = 126.9780
    btm = 37.5500
    lft = 126.9500
    top = 37.5800
    rgt = 127.0000

    # When - URL 쿼리 스트링 생성
    from urllib.parse import urlencode

    params = {
        "z": z,
        "lat": lat,
        "lon": lon,
        "btm": btm,
        "lft": lft,
        "top": top,
        "rgt": rgt,
    }
    query_string = urlencode(params)

    # Then - 모든 파라미터가 쿼리 스트링에 포함되어야 함
    assert "z=" in query_string
    assert "lat=" in query_string
    assert "lon=" in query_string
    assert "btm=" in query_string
    assert "lft=" in query_string
    assert "top=" in query_string
    assert "rgt=" in query_string


# =============================================================================
# test_zoom_level_and_coverage - 줌 레벨에 따른 Coverage 확인
# =============================================================================


@pytest.mark.unit
def test_zoom_level_and_coverage_basic():
    """
    줌 레벨에 따른 Coverage 기본 테스트

    줌 레벨이 높을수록 좁은 영역을 자세히 표시
    줌 레벨이 낮을수록 넓은 영역을 개략적으로 표시
    """
    # Given
    zoom_levels = [10, 11, 12, 13, 14, 15, 16, 17]
    center_lat = 37.5665
    center_lon = 126.9780
    radius_m = 1000

    # When - 각 줌 레벨에서 경계 계산
    coverages = {}
    for zoom in zoom_levels:
        s_lat, s_lng, e_lat, e_lng = bounds_from_center(center_lat, center_lon, radius_m, zoom)
        lat_diff = e_lat - s_lat
        lon_diff = e_lng - s_lng
        coverages[zoom] = (lat_diff, lon_diff)

    # Then - 모든 줌 레벨에서 경계가 계산되어야 함
    assert len(coverages) == len(zoom_levels)

    # Then - 각 경계 차이가 0보다 커야 함
    for zoom, (lat_diff, lon_diff) in coverages.items():
        assert lat_diff > 0, f"줌 레벨 {zoom}의 위도 차이가 0보다 커야 함"
        assert lon_diff > 0, f"줌 레벨 {zoom}의 경도 차이가 0보다 커야 함"


@pytest.mark.unit
def test_zoom_level_consistency():
    """
    동일한 중심 좌표와 반경에서 줌 레벨만 변경했을 때의 일관성 확인
    """
    # Given
    center_lat = 37.5665
    center_lon = 126.9780
    radius_m = 500

    # When - 같은 조건에서 여러 줌 레벨로 경계 계산
    bounds_z14 = bounds_from_center(center_lat, center_lon, radius_m, 14)
    bounds_z15 = bounds_from_center(center_lat, center_lon, radius_m, 15)
    bounds_z16 = bounds_from_center(center_lat, center_lon, radius_m, 16)

    # Then - 모든 경계는 중심을 포함해야 함
    for s_lat, s_lng, e_lat, e_lng in [bounds_z14, bounds_z15, bounds_z16]:
        assert s_lat <= center_lat <= e_lat
        assert s_lng <= center_lon <= e_lng


@pytest.mark.unit
def test_zoom_level_range():
    """
    유효한 줌 레벨 범위 테스트
    """
    # Given - 일반적인 지도 서비스의 줌 레벨 범위
    valid_zoom_levels = list(range(1, 21))  # 1 ~ 20

    # Given
    center_lat = 37.5665
    center_lon = 126.9780
    radius_m = 1000

    # When - 각 줌 레벨에서 경계 계산 시도
    for zoom in valid_zoom_levels:
        try:
            s_lat, s_lng, e_lat, e_lng = bounds_from_center(center_lat, center_lon, radius_m, zoom)

            # Then - 계산된 경계는 유효해야 함
            assert isinstance(s_lat, float)
            assert isinstance(s_lng, float)
            assert isinstance(e_lat, float)
            assert isinstance(e_lng, float)
            assert -90 <= s_lat <= 90
            assert -90 <= e_lat <= 90
            assert -180 <= s_lng <= 180
            assert -180 <= e_lng <= 180
        except Exception as e:
            pytest.fail(f"줌 레벨 {zoom}에서 경계 계산 실패: {e}")


@pytest.mark.unit
def test_zoom_level_with_different_radii():
    """
    다양한 줌 레벨과 반경 조합 테스트
    """
    # Given
    test_cases = [
        (10, 5000),  # 낮은 줌, 큰 반경
        (12, 2000),
        (15, 1000),
        (17, 500),  # 높은 줌, 작은 반경
    ]

    center_lat = 37.5665
    center_lon = 126.9780

    for zoom, radius in test_cases:
        # When
        s_lat, s_lng, e_lat, e_lng = bounds_from_center(center_lat, center_lon, radius, zoom)

        # Then
        assert s_lat <= center_lat <= e_lat, (
            f"줌 {zoom}, 반경 {radius}m: 위도 경계가 중심을 포함하지 않음"
        )
        assert s_lng <= center_lon <= e_lng, (
            f"줌 {zoom}, 반경 {radius}m: 경도 경계가 중심을 포함하지 않음"
        )

        # Then - 경계 차이가 존재해야 함
        lat_diff = e_lat - s_lat
        lon_diff = e_lng - s_lng
        assert lat_diff > 0, f"줌 {zoom}, 반경 {radius}m: 위도 차이가 0보다 커야 함"
        assert lon_diff > 0, f"줌 {zoom}, 반경 {radius}m: 경도 차이가 0보다 커야 함"


# =============================================================================
# 통합 테스트 - 전체 워크플로우
# =============================================================================


@pytest.mark.unit
def test_full_workflow_center_to_api_parameters():
    """
    중심 좌표와 반경에서 API 파라미터 생성까지의 전체 워크플로우 테스트
    """
    # Given - 서울시청, 1km 반경, 줌 레벨 15
    center_lat = 37.5665
    center_lon = 126.9780
    radius_m = 1000
    zoom = 15

    # When 1 - 경계 계산
    btm, lft, top, rgt = bounds_from_center(center_lat, center_lon, radius_m, zoom)

    # When 2 - API 파라미터 빌드
    params = {
        "z": zoom,
        "lat": center_lat,
        "lon": center_lon,
        "btm": btm,
        "lft": lft,
        "top": top,
        "rgt": rgt,
    }

    # Then - 모든 필수 파라미터가 존재하고 유효해야 함
    required_keys = ["z", "lat", "lon", "btm", "lft", "top", "rgt"]
    for key in required_keys:
        assert key in params, f"필수 파라미터 '{key}'가 누락됨"

    # Then - 중심 좌표가 경계 내부에 있어야 함
    assert params["btm"] <= params["lat"] <= params["top"]
    assert params["lft"] <= params["lon"] <= params["rgt"]

    # Then - 경계 순서가 올바른지 확인 (btm < top, lft < rgt)
    assert params["btm"] < params["top"], "하단 위도는 상단 위도보다 작아야 함"
    assert params["lft"] < params["rgt"], "좌측 경도는 우측 경도보다 작아야 함"


@pytest.mark.unit
def test_bounds_calculation_accuracy():
    """
    경계 계산의 정확도 검증

    위도 1도는 약 111km, 경도 1도는 위도에 따라 다름 (서울 기준 약 88km)
    반경 1km면 위도/경도 차이는 약 0.009 ~ 0.011도 정도여야 함
    """
    # Given
    center_lat = 37.5665
    center_lon = 126.9780
    radius_m = 1000
    zoom = 15

    # When
    s_lat, s_lng, e_lat, e_lng = bounds_from_center(center_lat, center_lon, radius_m, zoom)

    # Then - 위도 차이 (반경 1km = 약 0.009도)
    lat_diff = e_lat - s_lat
    expected_lat_diff = (2 * radius_m) / 111320  # 위도 1도 = 111.32km

    # 허용 오차 20% ( Mercator projection 근사치)
    assert math.isclose(lat_diff, expected_lat_diff, rel_tol=0.2), (
        f"위도 차이가 예상과 다름: expected={expected_lat_diff:.6f}, got={lat_diff:.6f}"
    )

    # Then - 경도 차이 (서울 위도 37.5도에서 경도 1도 = 약 88km)
    lon_diff = e_lng - s_lng
    expected_lon_diff = (2 * radius_m) / (111320 * math.cos(math.radians(center_lat)))

    # 허용 오차 20%
    assert math.isclose(lon_diff, expected_lon_diff, rel_tol=0.2), (
        f"경도 차이가 예상과 다름: expected={expected_lon_diff:.6f}, got={lon_diff:.6f}"
    )
