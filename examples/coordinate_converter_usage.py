"""
카카오맵 좌표계 변환 예제

WGS84(위경도)와 WCONGNAMUL 간의 변환 방법을 보여줍니다.
"""

from crawler.coordinate_converter import (
    wcongnamul_to_wgs84,
    wgs84_to_wcongnamul,
)


def main():
    """좌표 변환 예제 실행"""

    print("=" * 80)
    print("카카오맵 좌표계 변환 예제")
    print("=" * 80)

    # 예제 1: WGS84 -> WCONGNAMUL 변환
    print("\n[예제 1] WGS84(위경도) -> WCONGNAMUL 변환")
    print("-" * 80)

    # 서울시청
    lat, lon = 37.5665, 126.9780
    x, y = wgs84_to_wcongnamul(lat, lon)

    print("입력 (WGS84):")
    print(f"  위도: {lat}")
    print(f"  경도: {lon}")
    print("\n출력 (WCONGNAMUL):")
    print(f"  X: {x}")
    print(f"  Y: {y}")

    # 예제 2: WCONGNAMUL -> WGS84 변환
    print("\n[예제 2] WCONGNAMUL -> WGS84(위경도) 변환")
    print("-" * 80)

    # 강남역 (WCONGNAMUL 좌표)
    x, y = 1247180, 544695
    lon, lat = wcongnamul_to_wgs84(x, y)

    print("입력 (WCONGNAMUL):")
    print(f"  X: {x}")
    print(f"  Y: {y}")
    print("\n출력 (WGS84):")
    print(f"  위도: {lat}")
    print(f"  경도: {lon}")

    # 예제 3: 주요 지역 좌표 변환
    print("\n[예제 3] 주요 지역 좌표 변환")
    print("-" * 80)

    locations = [
        ("서울시청", 37.5665, 126.9780),
        ("강남역", 37.5172, 127.0473),
        ("경복궁", 37.5796, 126.9770),
        ("여의도", 37.4602, 126.9045),
    ]

    print(f"{'지역':<12} {'위도':<12} {'경도':<12} {'WCONGNAMUL X':<15} {'WCONGNAMUL Y':<15}")
    print("-" * 80)

    for name, lat, lon in locations:
        x, y = wgs84_to_wcongnamul(lat, lon)
        print(f"{name:<12} {lat:<12.6f} {lon:<12.6f} {x:<15.0f} {y:<15.0f}")

    # 예제 4: 왕복 변환 정확성 검증
    print("\n[예제 4] 왕복 변환 정확성 검증")
    print("-" * 80)

    original_lat, original_lon = 37.5665, 126.9780

    # WGS84 -> WCONGNAMUL
    x, y = wgs84_to_wcongnamul(original_lat, original_lon)

    # WCONGNAMUL -> WGS84
    restored_lon, restored_lat = wcongnamul_to_wgs84(x, y)

    print("원래 좌표 (WGS84):")
    print(f"  위도: {original_lat}")
    print(f"  경도: {original_lon}")
    print("\n복원된 좌표 (WGS84):")
    print(f"  위도: {restored_lat}")
    print(f"  경도: {restored_lon}")
    print("\n오차:")
    print(f"  위도 오차: {abs(restored_lat - original_lat):.10f} 도")
    print(f"  경도 오차: {abs(restored_lon - original_lon):.10f} 도")
    print("\n참고: 0.000001도는 약 0.11미터입니다.")

    # 예제 5: 카카오맵 대중교통 API 사용 예시
    print("\n[예제 5] 카카오맵 대중교통 API 좌표 변환")
    print("-" * 80)

    # 출발지: 서울역, 도착지: 강남역
    start_lat, start_lon = 37.5547, 126.9707
    end_lat, end_lon = 37.5172, 127.0473

    start_x, start_y = wgs84_to_wcongnamul(start_lat, start_lon)
    end_x, end_y = wgs84_to_wcongnamul(end_lat, end_lon)

    print("출발지 (서울역):")
    print(f"  WGS84: ({start_lat}, {start_lon})")
    print(f"  WCONGNAMUL: (sX={start_x}, sY={start_y})")

    print("\n도착지 (강남역):")
    print(f"  WGS84: ({end_lat}, {end_lon})")
    print(f"  WCONGNAMUL: (eX={end_x}, eY={end_y})")

    print("\n카카오맵 대중교통 API 요청 파라미터 예시:")
    print(f"  ?sX={start_x}&sY={start_y}&eX={end_x}&eY={end_y}")

    # 주의사항
    print("\n" + "=" * 80)
    print("주의사항")
    print("=" * 80)
    print("""
1. 중부원점 TM 투영(EPSG:5181) 기반:
   - 서울/경기 지역에서 가장 정확합니다.
   - 부산, 제주 등 원점에서 먼 지역은 오차가 커질 수 있습니다.

2. 좌표계 파라미터 순서:
   - wgs84_to_wcongnamul(latitude, longitude) -> (x, y)
   - wcongnamul_to_wgs84(x, y) -> (longitude, latitude)

3. API 요청 파라미터:
   - sX, sY: 출발지 좌표 (WCONGNAMUL)
   - eX, eY: 도착지 좌표 (WCONGNAMUL)

4. 변환 공식 출처:
   - https://choiseokwon.tistory.com/407
   - Go 언어로 구현된 Transverse Mercator 투영 공식을 Python으로 변환
    """)


if __name__ == "__main__":
    main()
