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
