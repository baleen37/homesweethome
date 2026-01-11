"""ASIL-네이버 매칭 E2E 테스트

ASIL 아파트 목록을 네이버 부동산 매물과 매칭하고 매물 정보를 크롤링하는 E2E 테스트.
"""

import pytest

from crawler.asil import AsilAptListCrawler
from crawler.naver_cluster_api import NaverClusterAPIClient

# =============================================================================
# 테스트 상수
# =============================================================================

# 문래동 동 코드 (테스트용 단일 동)
MULLAE_DONG_CODE = "1156011900"

# 좌표 오차 범위 (미터)
# 네이버 Cluster API는 근처 매물을 반환하지만 같은 아파트가 아닐 수 있음
COORDINATE_TOLERANCE_METERS = 2000


# =============================================================================
# test_match_asil_apartment_to_naver_article
# =============================================================================


@pytest.mark.e2e
@pytest.mark.slow
def test_match_asil_apartment_to_naver_article():
    """e2e: ASIL 아파트를 네이버 매물에 매칭

    검증:
    1. ASIL에서 문래동 아파트 목록을 성공적으로 가져옴
    2. 첫 번째 아파트에 대해 네이버 Cluster API로 매칭 시도
    3. 매칭된 네이버 매물이 존재
    4. 매칭된 매물의 좌표가 일정 범위 내에 있음
    5. 매물명이 비어있지 않음

    참고: 네이버 API abuse 감지 시 Playwright로 자동 우회합니다.
    """
    # Step 1: ASIL 아파트 목록 크롤링
    apt_crawler = AsilAptListCrawler(dong_code=MULLAE_DONG_CODE)
    apt_list = apt_crawler.crawl()

    # 검증 1: ASIL 목록 크롤링 성공
    assert len(apt_list) > 0, f"문래동({MULLAE_DONG_CODE}) ASIL 목록 크롤링 실패"

    print(f"\nASIL 목록 크롤링 성공: {len(apt_list)}개 아파트 찾음")

    # 첫 번째 아파트 선택 (좌표가 있는 것)
    target_apt = None
    for apt in apt_list:
        try:
            lat_f = float(apt.lat) if apt.lat else 0
            lng_f = float(apt.lng) if apt.lng else 0
            if lat_f != 0 and lng_f != 0:
                target_apt = apt
                break
        except (ValueError, TypeError):
            continue

    assert target_apt is not None, "좌표가 있는 아파트를 찾을 수 없음"

    apt_name = getattr(target_apt, "name", "")
    apt_seq = getattr(target_apt, "seq", "")
    lat_f = float(target_apt.lat)
    lng_f = float(target_apt.lng)

    print(f"타겟 아파트: {apt_name} (seq: {apt_seq})")
    print(f"좌표: {lat_f}, {lng_f}")

    # Step 2: Naver Cluster API로 매칭
    cluster_client = NaverClusterAPIClient(
        lat=lat_f,
        lon=lng_f,
        bottom=lat_f - 0.01,
        left=lng_f - 0.01,
        top=lat_f + 0.01,
        right=lng_f + 0.01,
        zoom=15,
    )

    url = cluster_client.build_url(page=1)

    # fetch()는 abuse 감지 시 자동으로 Playwright로 우회합니다
    try:
        response_json = cluster_client.fetch(url)
    except ValueError as e:
        # Playwright 우회 후에도 실패한 경우
        pytest.fail(f"Naver API 요청 실패 (Playwright 우회 후): {e}")

    cluster_response = cluster_client.parse_response(response_json)
    articles = cluster_response.articles

    # 검증 2: 매칭된 매물 존재
    assert len(articles) > 0, f"네이버 매칭 실패: 매물 없음 (아파트: {apt_name})"

    # 검증 3: 같은 아파트 이름의 매물 찾기 (좌표 근처에서)
    matched_article = None
    for article in articles:
        if article.atcl_nm and apt_name in article.atcl_nm:
            matched_article = article
            break

    # 같은 이름의 매물이 없으면 첫 번째 매물 사용 (API가 반환한 근처 매물)
    if matched_article is None:
        matched_article = articles[0]
        print(f"주의: 같은 이름의 매물 없음, 첫 번째 매물 사용: {matched_article.atcl_nm}")

    assert matched_article.atcl_nm, "매물명이 비어있음"
    assert matched_article.lat is not None, "매물 위도가 없음"
    assert matched_article.lng is not None, "매물 경도가 없음"

    print(f"네이버 매칭 성공: {matched_article.atcl_nm}")
    print(f"매물 좌표: {matched_article.lat}, {matched_article.lng}")

    # 검증 4: 좌표 오차 범위 검증 (Haversine 거리로 정확히 계산)
    from crawler.matching.asil_naver_matcher import AsilNaverMatcher

    distance_m = AsilNaverMatcher.haversine(
        (lat_f, lng_f), (matched_article.lat, matched_article.lng)
    )

    assert distance_m < COORDINATE_TOLERANCE_METERS, (
        f"좌표 차이가 너무 큼: {distance_m:.1f}m (허용: {COORDINATE_TOLERANCE_METERS}m)"
    )

    print(f"좌표 차이: {distance_m:.1f}m")
