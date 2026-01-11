#!/usr/bin/env python3
"""카카오맵 대중교통 경로 검색 예제 스크립트

아파트 위치에서 주요 장소까지 대중교통 경로를 검색합니다.
"""

from crawler.kakao_transit import MAJOR_LOCATIONS, KakaoTransitCrawler


def print_route_summary(
    crawler: KakaoTransitCrawler,
    lat: float,
    lon: float,
    location: str,
) -> None:
    """경로 요약을 출력합니다."""
    print(f"\n{'=' * 60}")
    print(f"🚇 {location}까지 대중교통 경로")
    print(f"{'=' * 60}")

    result = crawler.search_transit_route(lat, lon, location)

    if not result.routes:
        print("❌ 경로를 찾을 수 없습니다.")
        return

    # 추천 경로 출력
    for i, route in enumerate(result.routes[:3], 1):  # 최대 3개 경로
        print(f"\n📍 경로 {i} ({'⭐ 추천' if route.recommended else ''})")
        print(f"   소요시간: {route.time_text}")
        print(f"   거리: {route.distance_text}")
        print(f"   환승: {route.transfers}회")
        print(f"   도보: {route.walking_distance_text} ({route.walking_time_text})")

        # 주요 이동 수단 출력
        for step in route.steps:
            if step.action == "GETON":
                lane_info = step.lane.get("name", "") if step.lane else ""
                print(f"   🚌 {lane_info} 승차")
            elif step.action == "TRANSFER":
                print(f"   🔄 {step.end_location.get('name', '')}에서 환승")


def main():
    """메인 함수"""
    # 예시: 문래동 위치 (서울 영등포구)
    mullae_lat = 37.5138
    mullae_lon = 126.8826

    print("\n" + "=" * 60)
    print("🗺️  카카오맵 대중교통 경로 검색")
    print("=" * 60)
    print(f"📍 출발지: 문래동 ({mullae_lat}, {mullae_lon})")

    crawler = KakaoTransitCrawler()

    # 모든 주요 장소에 대해 경로 검색
    for location in MAJOR_LOCATIONS.keys():
        try:
            print_route_summary(crawler, mullae_lat, mullae_lon, location)
        except Exception as e:
            print(f"❌ {location} 경로 검색 실패: {e}")

    # 여러 도착지 한번에 검색
    print(f"\n{'=' * 60}")
    print("📊 전체 경로 비교")
    print(f"{'=' * 60}")

    results = crawler.search_multiple_destinations(
        mullae_lat, mullae_lon, list(MAJOR_LOCATIONS.keys())
    )

    print(f"\n{'장소':<10} {'소요시간':<10} {'거리':<10} {'환승':<5}")
    print("-" * 40)
    for location, result in results.items():
        if result.routes:
            route = result.routes[0]
            transfers_text = f"{route.transfers}회"
            print(
                f"{location:<10} {route.time_text:<10} "
                f"{route.distance_text:<10} {transfers_text:<5}"
            )


if __name__ == "__main__":
    main()
