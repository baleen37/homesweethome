"""
카카오맵 좌표계 변환 모듈

WGS84(위경도)와 WCONGNAMUL(카카오맵 좌표계) 간의 변환을 제공합니다.

참고:
- WCONGNAMUL은 카카오맵에서 사용하는 좌표계로, EPSG:5181 (중부원점 TM)에
  2.5배 스케일을 적용한 좌표계입니다.
- 이 모듈은 pyproj 없이 순수 Python으로 구현되었습니다.

변환 공식 출처: https://choiseokwon.tistory.com/407
"""

import math


class CoordinateConverter:
    """좌표계 변환 클래스"""

    # WGS84 타원체 상수
    WGS84_SEMI_MAJOR_AXIS = 6378137.0  # 반장축 (meters)
    WGS84_FLATTENING = 0.0033528106647474805  # 편평률

    # 한국 TM 투영 좌표계 상수 (EPSG:5181 기반)
    SCALE_FACTOR = 1.0  # 스케일 팩터
    FALSE_NORTHING = 500000.0  # 위도 방향 오프셋 (meters) - h in Go code (Y offset)
    FALSE_EASTING = 200000.0  # 경도 방향 오프셋 (meters) - f in Go code (X offset)
    LAT_ORIGIN = 38.0  # 기준 위도 (degrees) - l in Go code
    LON_ORIGIN = 127.0  # 기준 경도 (degrees) - m in Go code

    # WCONGNAMUL 스케일 팩터 (EPSG:5181 -> WCONGNAMUL)
    WCONGNAMUL_SCALE = 2.5

    @staticmethod
    def wgs84_to_wcongnamul(latitude: float, longitude: float) -> tuple[float, float]:
        """
        WGS84 좌표(위경도)를 WCONGNAMUL 좌표로 변환합니다.

        Args:
            latitude: 위도 (WGS84, decimal degrees)
            longitude: 경도 (WGS84, decimal degrees)

        Returns:
            Tuple[float, float]: (x, y) WCONGNAMUL 좌표

        Examples:
            >>> converter = CoordinateConverter()
            >>> x, y = converter.wgs84_to_wcongnamul(37.5665, 126.9780)  # 서울시청
            >>> print(f"X: {x}, Y: {y}")
        """
        # 1. WGS84 -> Korea TM (EPSG:5181)
        x_tm, y_tm = CoordinateConverter._transform_wgs84_to_korea_tm(
            latitude=latitude,
            longitude=longitude,
        )

        # 2. Korea TM -> WCONGNAMUL (2.5배 스케일)
        x_wcong = round(x_tm * CoordinateConverter.WCONGNAMUL_SCALE)
        y_wcong = round(y_tm * CoordinateConverter.WCONGNAMUL_SCALE)

        return x_wcong, y_wcong

    @staticmethod
    def wcongnamul_to_wgs84(x: float, y: float) -> tuple[float, float]:
        """
        WCONGNAMUL 좌표를 WGS84 좌표(위경도)로 변환합니다.

        Args:
            x: WCONGNAMUL X 좌표
            y: WCONGNAMUL Y 좌표

        Returns:
            Tuple[float, float]: (longitude, latitude) WGS84 좌표

        Examples:
            >>> converter = CoordinateConverter()
            >>> lon, lat = converter.wcongnamul_to_wgs84(160000, 500000)
            >>> print(f"Lat: {lat}, Lon: {lon}")
        """
        # 1. WCONGNAMUL -> Korea TM (2.5배 스케일 제거)
        x_tm = x / CoordinateConverter.WCONGNAMUL_SCALE
        y_tm = y / CoordinateConverter.WCONGNAMUL_SCALE

        # 2. Korea TM -> WGS84
        longitude, latitude = CoordinateConverter._transform_korea_tm_to_wgs84(
            x=x_tm,
            y=y_tm,
        )

        return longitude, latitude

    @staticmethod
    def _transform_wgs84_to_korea_tm(
        latitude: float,
        longitude: float,
    ) -> tuple[float, float]:
        """
        WGS84 좌표를 한국 TM 투영 좌표계로 변환합니다.

        Transverse Mercator 투영법을 사용합니다.

        Args:
            latitude: 위도 (decimal degrees)
            longitude: 경도 (decimal degrees)

        Returns:
            Tuple[float, float]: (x, y) TM 좌표
        """
        d = CoordinateConverter.WGS84_SEMI_MAJOR_AXIS
        e = CoordinateConverter.WGS84_FLATTENING
        h = CoordinateConverter.FALSE_NORTHING  # Y 오프셋 (h in Go code)
        f = CoordinateConverter.FALSE_EASTING  # X 오프셋 (f in Go code)
        c = CoordinateConverter.SCALE_FACTOR
        lat_origin = CoordinateConverter.LAT_ORIGIN
        m = CoordinateConverter.LON_ORIGIN
        lat = latitude
        lon = longitude

        # 각도를 라디안으로 변환
        a = math.pi / 180.0
        lat_rad = lat * a
        lon_rad = lon * a
        lat_origin_rad = lat_origin * a
        m_rad = m * a

        # 이심률 계산
        w = 1.0 / e if e <= 1.0 else e
        z = d * (w - 1.0) / w

        # 타원체 파라미터 계산
        g_param = 1.0 - (z * z) / (d * d)
        w = (d * d - z * z) / (z * z)
        z = (d - z) / (d + z)

        # 자오선 길이 계수
        e_var = d * (1.0 - z + 5.0 * (z * z - z**3) / 4.0 + 81.0 * (z**4 - z**5) / 64.0)
        i_var = 3.0 * d * (z - z**2 + 7.0 * (z**3 - z**4) / 8.0 + 55.0 * z**5 / 64.0) / 2.0
        j_var = 15.0 * d * (z**2 - z**3 + 3.0 * (z**4 - z**5) / 4.0) / 16.0
        l_var = 35.0 * d * (z**3 - z**4 + 11.0 * z**5 / 16.0) / 48.0
        m_var = 315.0 * d * (z**4 - z**5) / 512.0

        # 경도 차이
        d_lon = lon_rad - m_rad

        # 자오선 호 계산
        u = (
            e_var * lat_origin_rad
            - i_var * math.sin(2.0 * lat_origin_rad)
            + j_var * math.sin(4.0 * lat_origin_rad)
            - l_var * math.sin(6.0 * lat_origin_rad)
            + m_var * math.sin(8.0 * lat_origin_rad)
        )
        z = u * c

        # 위도 관련 계산
        sin_lat = math.sin(lat_rad)
        cos_lat = math.cos(lat_rad)
        t = sin_lat / cos_lat
        g_param = d / math.sqrt(1.0 - g_param * sin_lat * sin_lat)

        u = (
            e_var * lat_rad
            - i_var * math.sin(2.0 * lat_rad)
            + j_var * math.sin(4.0 * lat_rad)
            - l_var * math.sin(6.0 * lat_rad)
            + m_var * math.sin(8.0 * lat_rad)
        )
        o = u * c

        # Y 좌표 계산 (Northing)
        e_var = g_param * sin_lat * cos_lat * c / 2.0
        i_var = g_param * sin_lat * cos_lat**3 * c * (5.0 - t**2 + 9.0 * w + 4.0 * w**2) / 24.0
        j_var = (
            g_param
            * sin_lat
            * cos_lat**5
            * c
            * (
                61.0
                - 58.0 * t**2
                + t**4
                + 270.0 * w
                - 330.0 * t**2 * w
                + 445.0 * w**2
                + 324.0 * w**3
                - 680.0 * t**2 * w**2
                + 88.0 * w**4
                - 600.0 * t**2 * w**3
                - 192.0 * t**2 * w**4
            )
            / 720.0
        )
        h_var = (
            g_param
            * sin_lat
            * cos_lat**7
            * c
            * (1385.0 - 3111.0 * t**2 + 543.0 * t**4 - t**6)
            / 40320.0
        )
        o += d_lon**2 * e_var + d_lon**4 * i_var + d_lon**6 * j_var + d_lon**8 * h_var
        y = o - z + h

        # X 좌표 계산 (Easting)
        o = g_param * cos_lat * c
        z = g_param * cos_lat**3 * c * (1.0 - t**2 + w) / 6.0
        w = (
            g_param
            * cos_lat**5
            * c
            * (
                5.0
                - 18.0 * t**2
                + t**4
                + 14.0 * w
                - 58.0 * t**2 * w
                + 13.0 * w**2
                + 4.0 * w**3
                - 64.0 * t**2 * w**2
                - 24.0 * t**2 * w**3
            )
            / 120.0
        )
        u = g_param * cos_lat**7 * c * (61.0 - 479.0 * t**2 + 179.0 * t**4 - t**6) / 5040.0
        x = f + d_lon * o + d_lon**3 * z + d_lon**5 * w + d_lon**7 * u

        return x, y

    @staticmethod
    def _transform_korea_tm_to_wgs84(x: float, y: float) -> tuple[float, float]:
        """
        한국 TM 투영 좌표계를 WGS84 좌표로 변환합니다.

        Transverse Mercator 투영의 역변환입니다.

        Args:
            x: TM X 좌표 (Easting)
            y: TM Y 좌표 (Northing)

        Returns:
            Tuple[float, float]: (longitude, latitude) WGS84 좌표
        """
        d = CoordinateConverter.WGS84_SEMI_MAJOR_AXIS
        e = CoordinateConverter.WGS84_FLATTENING
        h = CoordinateConverter.FALSE_NORTHING  # Y 오프셋 (h in Go code)
        f = CoordinateConverter.FALSE_EASTING  # X 오프셋 (f in Go code)
        c = CoordinateConverter.SCALE_FACTOR
        lat_origin = CoordinateConverter.LAT_ORIGIN
        m = CoordinateConverter.LON_ORIGIN

        u = e if e <= 1.0 else 1.0 / e
        w = math.pi / 180.0  # 각도를 라디안으로 변환하는 팩터
        o = lat_origin * w
        d_lon = m * w
        u = 1.0 / u
        b = d * (u - 1.0) / u
        z = (d * d - b * b) / (d * d)
        u = (d * d - b * b) / (b * b)
        b = (d - b) / (d + b)

        # 자오선 길이 계수
        g_var = d * (1.0 - b + 5.0 * (b**2 - b**3) / 4.0 + 81.0 * (b**4 - b**5) / 64.0)
        e_var = 3.0 * d * (b - b**2 + 7.0 * (b**3 - b**4) / 8.0 + 55.0 * b**5 / 64.0) / 2.0
        i_var = 15.0 * d * (b**2 - b**3 + 3.0 * (b**4 - b**5) / 4.0) / 16.0
        j_var = 35.0 * d * (b**3 - b**4 + 11.0 * b**5 / 16.0) / 48.0
        l_var = 315.0 * d * (b**4 - b**5) / 512.0

        # 자오선 호 계산
        o = (
            g_var * o
            - e_var * math.sin(2.0 * o)
            + i_var * math.sin(4.0 * o)
            - j_var * math.sin(6.0 * o)
            + l_var * math.sin(8.0 * o)
        )
        o *= c
        o = y + o - h

        # 위도 계산 (Newton-Raphson 반복법)
        m_var = o / c
        h_var = d * (1.0 - z) / math.sqrt(1.0 - z * math.sin(0.0) ** 2) ** 3
        o = m_var / h_var

        for _ in range(5):
            b = (
                g_var * o
                - e_var * math.sin(2.0 * o)
                + i_var * math.sin(4.0 * o)
                - j_var * math.sin(6.0 * o)
                + l_var * math.sin(8.0 * o)
            )
            h_var = d * (1.0 - z) / math.sqrt(1.0 - z * math.sin(o) ** 2) ** 3
            o += (m_var - b) / h_var

        # 위도 계산 완료
        h_var = d * (1.0 - z) / math.sqrt(1.0 - z * math.sin(o) ** 2) ** 3
        g_var = d / math.sqrt(1.0 - z * math.sin(o) ** 2)
        b = math.sin(o)
        z = math.cos(o)
        e_var = b / z
        u *= z * z
        a = x - f
        b = e_var / (2.0 * h_var * g_var * c**2)
        i_var = (
            e_var
            * (5.0 + 3.0 * e_var**2 + u - 4.0 * u**2 - 9.0 * e_var**2 * u)
            / (24.0 * h_var * g_var**3 * c**4)
        )
        j_var = (
            e_var
            * (
                61.0
                + 90.0 * e_var**2
                + 46.0 * u
                + 45.0 * e_var**4
                - 252.0 * e_var**2 * u
                - 3.0 * u**2
                + 100.0 * u**3
                - 66.0 * e_var**2 * u**2
                - 90.0 * e_var**4 * u
                + 88.0 * u**4
                + 225.0 * e_var**4 * u**2
                + 84.0 * e_var**2 * u**3
                - 192.0 * e_var**2 * u**4
            )
            / (720.0 * h_var * g_var**5 * c**6)
        )
        h_var = (
            e_var
            * (1385.0 + 3633.0 * e_var**2 + 4095.0 * e_var**4 + 1575.0 * e_var**6)
            / (40320.0 * h_var * g_var**7 * c**8)
        )
        o = o - a**2 * b + a**4 * i_var - a**6 * j_var + a**8 * h_var

        # 경도 계산
        b = 1.0 / (g_var * z * c)
        h_var = (1.0 + 2.0 * e_var**2 + u) / (6.0 * g_var**3 * z**3 * c**3)
        u = (
            5.0
            + 6.0 * u
            + 28.0 * e_var**2
            - 3.0 * u**2
            + 8.0 * e_var**2 * u
            + 24.0 * e_var**4
            - 4.0 * u**3
            + 4.0 * e_var**2 * u**2
            + 24.0 * e_var**2 * u**3
        ) / (120.0 * g_var**5 * z**5 * c**5)
        z = (61.0 + 662.0 * e_var**2 + 1320.0 * e_var**4 + 720.0 * e_var**6) / (
            5040.0 * g_var**7 * z**7 * c**7
        )
        a = a * b - a**3 * h_var + a**5 * u - a**7 * z
        d_lon += a

        # 라디안을 각도로 변환
        latitude = o / w
        longitude = d_lon / w

        return longitude, latitude


def wgs84_to_wcongnamul(latitude: float, longitude: float) -> tuple[float, float]:
    """
    WGS84 좌표를 WCONGNAMUL 좌표로 변환하는 헬퍼 함수.

    Args:
        latitude: 위도 (WGS84, decimal degrees)
        longitude: 경도 (WGS84, decimal degrees)

    Returns:
        Tuple[float, float]: (x, y) WCONGNAMUL 좌표
    """
    return CoordinateConverter.wgs84_to_wcongnamul(latitude, longitude)


def wcongnamul_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """
    WCONGNAMUL 좌표를 WGS84 좌표로 변환하는 헬퍼 함수.

    Args:
        x: WCONGNAMUL X 좌표
        y: WCONGNAMUL Y 좌표

    Returns:
        Tuple[float, float]: (longitude, latitude) WGS84 좌표
    """
    return CoordinateConverter.wcongnamul_to_wgs84(x, y)
