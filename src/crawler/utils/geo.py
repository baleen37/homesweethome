"""Mercator projection 지리 좌표 변환 유틸리티"""

import math


def ll_to_pixel(lat: float, lon: float, zoom: float) -> tuple[float, float]:
    """
    위도/경도를 픽셀 좌표로 변환 (Mercator projection).

    Args:
        lat: 위도 (-85 ~ 85)
        lon: 경도 (-180 ~ 180)
        zoom: 줌 레벨 (1 ~ 20)

    Returns:
        (x, y) 픽셀 좌표

    Raises:
        ValueError: 위도가 유효 범위를 벗어날 때
    """
    if abs(lat) > 85:
        raise ValueError(f"위도는 ±85도까지만 유효함: {lat}")

    scale = 256 * (2**zoom)
    x = (lon + 180.0) / 360.0 * scale

    siny = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + siny) / (1 - siny)) / (4 * math.pi)) * scale

    return x, y


def pixel_to_ll(x: float, y: float, zoom: float) -> tuple[float, float]:
    """
    픽셀 좌표를 위도/경도로 변환 (Mercator projection).

    Args:
        x: 픽셀 x 좌표
        y: 픽셀 y 좌표
        zoom: 줌 레벨 (1 ~ 20)

    Returns:
        (lat, lon) 튜플
    """
    scale = 256 * (2**zoom)
    lon = x / scale * 360.0 - 180.0

    y = y / scale
    lat = math.asin(2 ** (2 * y - 1) - 1) * 2 / math.pi
    # Fix lat calculation
    n = math.pi - 2 * math.pi * y / scale
    lat = math.atan(0.5 * (math.exp(n) - math.exp(-n))) * 180 / math.pi

    return lat, lon


def bounds_from_center(
    lat: float, lon: float, radius_m: int, zoom: int
) -> tuple[float, float, float, float]:
    """
    중심 좌표와 반경으로 지도 경계 계산

    Args:
        lat: 중심 위도
        lon: 중심 경도
        radius_m: 반경 (미터)
        zoom: 줌 레벨

    Returns:
        (s_lat, s_lng, e_lat, e_lng) 튜플 - 남서쪽, 북동쪽 좌표
    """
    # 대략적인 미터당 도 계산 (위도 1도 ≈ 111km)
    lat_delta = radius_m / 111000.0
    # 경도는 위도에 따라 다름 (cos(lat) 비례)
    lon_delta = radius_m / (111000.0 * math.cos(math.radians(lat)))

    return (
        lat - lat_delta,
        lon - lon_delta,
        lat + lat_delta,
        lon + lon_delta,
    )
