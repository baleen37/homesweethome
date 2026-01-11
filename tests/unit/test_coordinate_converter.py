"""
좌표 변환기 유닛 테스트

WGS84 <-> WCONGNAMUL 변환의 정확성을 검증합니다.
"""

from src.crawler.coordinate_converter import (
    CoordinateConverter,
    wcongnamul_to_wgs84,
    wgs84_to_wcongnamul,
)


class TestCoordinateConverter:
    """좌표 변환기 테스트"""

    def test_wgs84_to_wcongnamul_known_values(self):
        """
        알려진 값으로 WGS84 -> WCONGNAMUL 변환 테스트

        테스트 데이터 출처: https://choiseokwon.tistory.com/407
        """
        test_cases = [
            # (위도, 경도, 예상 X, 예상 Y)
            (37.248098895147216, 126.99116337285824, 498040.0, 1041367.0),
            (36.762436923118536, 127.28434974725708, 563473.0, 906718.0),
            (35.73294563400083, 127.37264182214031, 584279.0, 621193.0),
        ]

        for lat, lon, expected_x, expected_y in test_cases:
            x, y = wgs84_to_wcongnamul(lat, lon)

            # 허용 오차: 1 (블로그의 테스트 기준)
            assert abs(x - expected_x) <= 1.0, (
                f"X 좌표 불일치: lat={lat}, lon={lon}, expected={expected_x}, got={x}"
            )
            assert abs(y - expected_y) <= 1.0, (
                f"Y 좌표 불일치: lat={lat}, lon={lon}, expected={expected_y}, got={y}"
            )

    def test_wcongnamul_to_wgs84_known_values(self):
        """
        알려진 값으로 WCONGNAMUL -> WGS84 변환 테스트

        테스트 데이터 출처: https://choiseokwon.tistory.com/407
        """
        test_cases = [
            # (X, Y, 예상 위도, 예상 경도)
            (498040.0, 1041367.0, 37.248098895147216, 126.99116337285824),
            (563473.0, 906718.0, 36.762436923118536, 127.28434974725708),
            (584279.0, 621193.0, 35.73294563400083, 127.37264182214031),
        ]

        for x, y, expected_lat, expected_lon in test_cases:
            lon, lat = wcongnamul_to_wgs84(x, y)

            # 허용 오차: 0.0001도 (약 11미터)
            # 블로그에서 언급한 margin error ~= 0.0001 기준
            assert abs(lat - expected_lat) <= 0.0001, (
                f"위도 불일치: x={x}, y={y}, expected={expected_lat}, got={lat}"
            )
            assert abs(lon - expected_lon) <= 0.0001, (
                f"경도 불일치: x={x}, y={y}, expected={expected_lon}, got={lon}"
            )

    def test_roundtrip_conversion(self):
        """
        왕복 변환 테스트: WGS84 -> WCONGNAMUL -> WGS84

        원래 좌표와 복원된 좌표가 일치해야 합니다.

        참고: 중부원점 TM 투영(EPSG:5181)은 서울/경기 지역에 최적화되어 있습니다.
        부산, 제주 등 원점에서 먼 지역은 오차가 커질 수 있습니다.
        """
        test_cases = [
            # 서울/경기 지역 주요 좌표 (중부원점 기준 최적 범위)
            (37.5665, 126.9780),  # 서울시청
            (37.5512, 126.9882),  # 남산타워
            (37.5796, 126.9770),  # 경복궁
            (37.5172, 127.0473),  # 강남역
            (37.4602, 126.9045),  # 여의도
        ]

        for original_lat, original_lon in test_cases:
            # WGS84 -> WCONGNAMUL
            x, y = wgs84_to_wcongnamul(original_lat, original_lon)

            # WCONGNAMUL -> WGS84
            restored_lon, restored_lat = wcongnamul_to_wgs84(x, y)

            # 허용 오차: 0.000002도 (약 0.22미터)
            # round() 함수 사용으로 인한 반올림 오차 고려
            assert abs(restored_lat - original_lat) <= 0.000002, (
                f"왕복 변환 후 위도 불일치: "
                f"original=({original_lat}, {original_lon}), "
                f"restored=({restored_lat}, {restored_lon})"
            )
            assert abs(restored_lon - original_lon) <= 0.000002, (
                f"왕복 변환 후 경도 불일치: "
                f"original=({original_lat}, {original_lon}), "
                f"restored=({restored_lat}, {restored_lon})"
            )

    def test_wgs84_to_wcongnamul_class_method(self):
        """클래스 메서드를 직접 호출하는 테스트"""
        lat, lon = 35.73294563400083, 127.37264182214031
        expected_x, expected_y = 584279.0, 621193.0

        x, y = CoordinateConverter.wgs84_to_wcongnamul(lat, lon)

        assert abs(x - expected_x) <= 1.0
        assert abs(y - expected_y) <= 1.0

    def test_wcongnamul_to_wgs84_class_method(self):
        """클래스 메서드를 직접 호출하는 테스트"""
        x, y = 584279.0, 621193.0
        expected_lat, expected_lon = 35.73294563400083, 127.37264182214031

        lon, lat = CoordinateConverter.wcongnamul_to_wgs84(x, y)

        assert abs(lat - expected_lat) <= 0.0001
        assert abs(lon - expected_lon) <= 0.0001

    def test_coordinate_scale(self):
        """
        좌표값의 스케일 테스트

        WCONGNAMUL 좌표는 보통 수십만 단위의 값을 가집니다.
        """
        lat, lon = 37.5665, 126.9780  # 서울시청
        x, y = wgs84_to_wcongnamul(lat, lon)

        # WCONGNAMUL 좌표는 보통 100,000 ~ 1,000,000 범위
        assert 100000 < x < 1000000, f"X 좌표가 예상 범위를 벗어남: {x}"
        assert 100000 < y < 2000000, f"Y 좌표가 예상 범위를 벗어남: {y}"

    def test_invalid_coordinates(self):
        """
        잘못된 좌표 입력에 대한 테스트

        한국 범위를 벗어난 좌표도 변환은 가능하지만,
        결과값이 Korea TM 기준이므로 한국 지역에서만 정확합니다.
        """
        # 적도 (한국 범위 밖)
        lat, lon = 0.0, 127.0
        x, y = wgs84_to_wcongnamul(lat, lon)

        # 변환 자체는 성공해야 함
        assert isinstance(x, (int, float))
        assert isinstance(y, (int, float))

    def test_coordinate_order(self):
        """
        좌표 순서 테스트

        함수 파라미터 순서가 올바른지 확인:
        - wgs84_to_wcongnamul(latitude, longitude)
        - wcongnamul_to_wgs84(x, y) -> (longitude, latitude)
        """
        # 강남역
        lat, lon = 37.5172, 127.0473

        x, y = wgs84_to_wcongnamul(lat, lon)
        restored_lon, restored_lat = wcongnamul_to_wgs84(x, y)

        # 위도/경도가 올바르게 복원되어야 함
        # 허용 오차: 0.000002도 (약 0.22미터)
        # round() 함수 사용으로 인한 반올림 오차 고려
        assert abs(restored_lat - lat) <= 0.000002
        assert abs(restored_lon - lon) <= 0.000002
