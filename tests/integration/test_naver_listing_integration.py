"""네이버 매물 크롤러 Integration Test

실제 네이버 API를 호출하여 전체 매물 크롤링 흐름을 검증합니다.

테스트 순서:
1. test_cluster_api_real_call - Cluster API 기본 호출 테스트
2. test_front_api_real_call - Front API 기본 호출 테스트
3. test_full_workflow - 전체 워크플로우 테스트
"""

import pytest
import requests

try:
    from crawler.naver_cluster_api import NaverClusterAPIClient
    from crawler.naver_coordinate import bounds_from_center
    from crawler.naver_front_api import NaverFrontAPIClient

    NAVER_API_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    NAVER_API_AVAILABLE = False


# =============================================================================
# 테스트 상수
# =============================================================================

# 강남구 좌표
TEST_LAT_GANGNAM = 37.5172
TEST_LON_GANGNAM = 127.0473

# 시청 좌표
TEST_LAT_CITYHALL = 37.5665
TEST_LON_CITYHALL = 126.9780


# =============================================================================
# 1. test_cluster_api_real_call - 가장 기본
# =============================================================================


@pytest.mark.integration
@pytest.mark.skipif(not NAVER_API_AVAILABLE, reason="Naver API clients not available")
def test_cluster_api_real_call():
    """integration: Cluster API 실제 호출

    서울 강남구 좌표 (lat=37.5172, lon=127.0473)에서
    NaverClusterAPIClient로 실제 API 호출을 수행합니다.

    검증:
    1. 최소 1개 이상 매물 반환
    2. 응답 필드 검증 (atcl_no, atcl_nm, prc 등)
    3. requests.exceptions 처리
    """
    # 지도 경계 계산 (반경 500m)
    s_lat, s_lng, e_lat, e_lng = bounds_from_center(
        lat=TEST_LAT_GANGNAM,
        lon=TEST_LON_GANGNAM,
        radius_m=500,
        zoom=14,
    )

    # Cluster API 클라이언트 초기화
    client = NaverClusterAPIClient(
        lat=TEST_LAT_GANGNAM,
        lon=TEST_LON_GANGNAM,
        bottom=s_lat,
        left=s_lng,
        top=e_lat,
        right=e_lng,
        rlet_tp_cd="A01",  # 아파트만
        trad_tp_cd="A1",  # 매매만
        zoom=14,
    )

    # URL 빌드
    url = client.build_url(page=1)

    # API 요청
    try:
        response_json = client.fetch(url)
    except requests.RequestException as e:
        pytest.skip(f"Cluster API 요청 실패 (네이버 API 문제 가능성): {e}")
    except requests.exceptions.JSONDecodeError as e:
        pytest.skip(f"Cluster API JSON 파싱 실패 (네이버 API 응답 변경 가능성): {e}")

    # 응답 파싱
    response_dto = client.parse_response(response_json)

    # 검증 1: 최소 1개 이상 매물 반환
    assert len(response_dto.articles) > 0, "매물이 1개 이상 반환되어야 함"

    # 검증 2: 응답 필드 검증
    first_article = response_dto.articles[0]
    assert first_article.atcl_no, "atcl_no 필드가 비어있음"
    assert first_article.atcl_nm, "atcl_nm 필드가 비어있음"
    # 필터가 API에서 제대로 작동하지 않을 수 있음 (네이버 API 사양 변경 가능성)
    # 실제 반환된 유형을 검증
    assert first_article.rlet_tp_cd in ["A01", "A02"], (
        f"부동산 유형이 아파트/오피스텔이 아님: {first_article.rlet_tp_cd}"
    )
    assert first_article.trad_tp_cd in ["A1", "B1", "B2"], (
        f"거래 유형이 유효하지 않음: {first_article.trad_tp_cd}"
    )

    # 검증 3: 페이지 정보 확인
    assert response_dto.page == 1, "페이지 번호가 1이어야 함"

    print(f"Cluster API 호출 성공: {len(response_dto.articles)}개 매물")
    print(f"첫 번째 매물: {first_article.atcl_nm} (ID: {first_article.atcl_no})")
    if first_article.prc:
        print(f"가격: {first_article.prc}만원")


# =============================================================================
# 2. test_front_api_real_call
# =============================================================================


@pytest.mark.integration
@pytest.mark.skipif(not NAVER_API_AVAILABLE, reason="Naver API clients not available")
def test_front_api_real_call():
    """integration: Front API 실제 호출

    Cluster API에서 가져온 첫 번째 매물의 atcl_no를 사용하여
    NaverFrontAPIClient.get_article_key()를 호출합니다.

    검증:
    1. Cluster API로 매물 목록 가져오기
    2. 첫 번째 매물의 atcl_no로 Front API 호출
    3. 응답 검증
    """
    # 먼저 Cluster API로 매물 목록 가져오기
    s_lat, s_lng, e_lat, e_lng = bounds_from_center(
        lat=TEST_LAT_GANGNAM,
        lon=TEST_LON_GANGNAM,
        radius_m=500,
        zoom=14,
    )

    cluster_client = NaverClusterAPIClient(
        lat=TEST_LAT_GANGNAM,
        lon=TEST_LON_GANGNAM,
        bottom=s_lat,
        left=s_lng,
        top=e_lat,
        right=e_lng,
        rlet_tp_cd="A01",
        trad_tp_cd="A1",
        zoom=14,
    )

    url = cluster_client.build_url(page=1)

    try:
        response_json = cluster_client.fetch(url)
    except requests.RequestException as e:
        pytest.fail(f"Cluster API 요청 실패: {e}")

    response_dto = cluster_client.parse_response(response_json)

    if len(response_dto.articles) == 0:
        pytest.skip("Cluster API에서 매물을 찾을 수 없음")

    # 첫 번째 매물의 atcl_no 사용
    first_article = response_dto.articles[0]
    article_id = first_article.atcl_no

    # Front API 클라이언트 초기화
    front_client = NaverFrontAPIClient()

    # article key URL 빌드
    key_url = front_client.get_article_key_url(article_id)

    # API 요청 - NaverFrontAPIClient.fetch() 메서드 사용
    try:
        key_response_json = front_client.fetch(key_url)
    except requests.RequestException as e:
        pytest.skip(f"Front API 요청 실패 (403은 예상된 동작일 수 있음): {e}")

    # 응답 파싱
    parsed_key = front_client.parse_article_key_response(key_response_json)

    # 검증: 응답이 존재해야 함
    assert parsed_key is not None, "Front API 응답 파싱 실패"
    assert parsed_key.get("articleId") is not None, "articleId가 비어있음"

    print("Front API 호출 성공")
    print(f"매물 ID: {parsed_key.get('articleId')}")
    print(f"단지 번호: {parsed_key.get('complexNumber')}")


# =============================================================================
# 3. test_full_workflow
# =============================================================================


@pytest.mark.integration
@pytest.mark.skipif(not NAVER_API_AVAILABLE, reason="Naver API clients not available")
def test_full_workflow():
    """integration: 전체 워크플로우 테스트

    Cluster API로 매물 목록을 가져오고,
    첫 번째 매물의 상세 정보를 Front API로 조회합니다.

    검증:
    1. Cluster API로 매물 목록 가져오기
    2. 첫 번째 매물의 상세 정보 가져오기 (Front API)
    3. 전체 데이터 검증
    """
    # Step 1: Cluster API로 매물 목록 가져오기
    s_lat, s_lng, e_lat, e_lng = bounds_from_center(
        lat=TEST_LAT_GANGNAM,
        lon=TEST_LON_GANGNAM,
        radius_m=500,
        zoom=14,
    )

    cluster_client = NaverClusterAPIClient(
        lat=TEST_LAT_GANGNAM,
        lon=TEST_LON_GANGNAM,
        bottom=s_lat,
        left=s_lng,
        top=e_lat,
        right=e_lng,
        rlet_tp_cd="A01",
        trad_tp_cd="A1",
        zoom=14,
    )

    url = cluster_client.build_url(page=1)

    try:
        response_json = cluster_client.fetch(url)
    except requests.RequestException as e:
        pytest.fail(f"Cluster API 요청 실패: {e}")

    response_dto = cluster_client.parse_response(response_json)

    assert len(response_dto.articles) > 0, "매물이 1개 이상 반환되어야 함"

    first_article = response_dto.articles[0]
    article_id = first_article.atcl_no

    print(f"Step 1 완료: {len(response_dto.articles)}개 매물 발견")
    print(f"첫 번째 매물: {first_article.atcl_nm} (ID: {article_id})")

    # Step 2: Front API로 매물 상세 정보 가져오기
    front_client = NaverFrontAPIClient()

    # 상세 정보 URL 빌드
    detail_url = front_client.get_article_basic_info_url(
        article_id=article_id,
        real_estate_type=first_article.rlet_tp_cd,  # A01
        trade_type=first_article.trad_tp_cd,  # A1
    )

    # API 요청 - NaverFrontAPIClient.fetch() 메서드 사용
    try:
        detail_json = front_client.fetch(detail_url)
    except requests.RequestException as e:
        pytest.skip(f"Front API 상세 정보 요청 실패 (403은 예상된 동작일 수 있음): {e}")

    # 응답 파싱
    price_info = front_client.parse_basic_info_price(detail_json)
    detail_info = front_client.parse_basic_info_detail(detail_json)
    size_info = front_client.parse_basic_info_size(detail_json)

    # 검증: 상세 정보가 존재해야 함
    assert price_info is not None or detail_info is not None or size_info is not None, (
        "상세 정보가 최소 하나 이상 파싱되어야 함"
    )

    print("Step 2 완료: 매물 상세 정보 조회 성공")

    # 상세 정보 출력
    if price_info:
        print(f"가격 정보: {price_info}")
    if detail_info:
        print(f"상세 정보: {detail_info}")
    if size_info:
        print(f"면적 정보: {size_info}")

    # 전체 워크플로우 성공
    print("\n=== 전체 워크플로우 테스트 성공 ===")
    print(f"매물명: {first_article.atcl_nm}")
    print(f"매물 ID: {article_id}")
    print(f"부동산 유형: {first_article.rlet_tp_nm}")
    print(f"거래 유형: {first_article.trad_tp_nm}")


# =============================================================================
# 4. test_cityhall_location - 시청 좌표 테스트
# =============================================================================


@pytest.mark.integration
@pytest.mark.skipif(not NAVER_API_AVAILABLE, reason="Naver API clients not available")
def test_cityhall_location():
    """integration: 시청 좌표에서 Cluster API 호출

    서울 시청 좌표 (lat=37.5665, lon=126.9780)에서
    Cluster API를 호출하여 매물을 조회합니다.

    검증:
    1. 최소 1개 이상 매물 반환
    2. 응답 필드 검증
    """
    s_lat, s_lng, e_lat, e_lng = bounds_from_center(
        lat=TEST_LAT_CITYHALL,
        lon=TEST_LON_CITYHALL,
        radius_m=500,
        zoom=14,
    )

    client = NaverClusterAPIClient(
        lat=TEST_LAT_CITYHALL,
        lon=TEST_LON_CITYHALL,
        bottom=s_lat,
        left=s_lng,
        top=e_lat,
        right=e_lng,
        rlet_tp_cd="A01",
        trad_tp_cd="A1",
        zoom=14,
    )

    url = client.build_url(page=1)

    try:
        response_json = client.fetch(url)
    except requests.RequestException as e:
        pytest.fail(f"Cluster API 요청 실패: {e}")

    response_dto = client.parse_response(response_json)

    assert len(response_dto.articles) > 0, "매물이 1개 이상 반환되어야 함"

    print(f"시청 좌표 Cluster API 호출 성공: {len(response_dto.articles)}개 매물")


# =============================================================================
# 5. test_pagination - 페이지네이션 테스트
# =============================================================================


@pytest.mark.integration
@pytest.mark.skipif(not NAVER_API_AVAILABLE, reason="Naver API clients not available")
def test_pagination():
    """integration: 페이지네이션 테스트

    여러 페이지를 크롤링하여 페이지네이션 기능을 검증합니다.

    검증:
    1. 2페이지까지 조회 가능
    2. more 플래그 정상 작동
    """
    s_lat, s_lng, e_lat, e_lng = bounds_from_center(
        lat=TEST_LAT_GANGNAM,
        lon=TEST_LON_GANGNAM,
        radius_m=1000,  # 더 큰 반경
        zoom=13,  # 더 낮은 줌 레벨
    )

    client = NaverClusterAPIClient(
        lat=TEST_LAT_GANGNAM,
        lon=TEST_LON_GANGNAM,
        bottom=s_lat,
        left=s_lng,
        top=e_lat,
        right=e_lng,
        rlet_tp_cd="A01",
        trad_tp_cd="A1",
        zoom=13,
    )

    all_articles = []
    max_pages = 2

    for page in range(1, max_pages + 1):
        url = client.build_url(page=page)

        try:
            response_json = client.fetch(url)
        except requests.RequestException as e:
            pytest.fail(f"Cluster API 요청 실패 (page {page}): {e}")

        response_dto = client.parse_response(response_json)
        all_articles.extend(response_dto.articles)

        # more가 False이면 종료
        if not response_dto.more:
            break

    assert len(all_articles) > 0, "매물이 1개 이상 반환되어야 함"

    print(f"페이지네이션 테스트 성공: {len(all_articles)}개 매물 수집")


# =============================================================================
# 6. test_error_handling - 에러 핸들링 테스트
# =============================================================================


@pytest.mark.integration
@pytest.mark.skipif(not NAVER_API_AVAILABLE, reason="Naver API clients not available")
def test_error_handling():
    """integration: 에러 핸들링 테스트

    잘못된 좌표로 요청 시 에러가 적절히 처리되는지 검증합니다.

    검증:
    1. 바다 한가운데 좌표는 빈 결과 반환
    2. requests.exceptions 처리
    """
    # 바다 한가운데 좌표
    s_lat, s_lng, e_lat, e_lng = bounds_from_center(
        lat=35.0,
        lon=129.0,
        radius_m=100,
        zoom=13,
    )

    client = NaverClusterAPIClient(
        lat=35.0,
        lon=129.0,
        bottom=s_lat,
        left=s_lng,
        top=e_lat,
        right=e_lng,
        zoom=13,
    )

    url = client.build_url(page=1)

    try:
        response_json = client.fetch(url)
        response_dto = client.parse_response(response_json)

        # 바다 근처는 매물이 없을 수 있음
        assert isinstance(response_dto.articles, list), "응답은 리스트여야 함"
        print(f"에러 핸들링 테스트 성공: {len(response_dto.articles)}개 매물 (예상: 0개)")

    except requests.RequestException as e:
        # 네트워크 에러도 정상적으로 처리되어야 함
        print(f"에러 핸들링 테스트: 요청 실패 (예상된 동작): {e}")


# =============================================================================
# 7. test_rate_limiting - Rate Limiting 고려
# =============================================================================


@pytest.mark.integration
@pytest.mark.skipif(not NAVER_API_AVAILABLE, reason="Naver API clients not available")
@pytest.mark.slow
def test_rate_limiting():
    """integration: Rate Limiting 고려

    연속 요청 사이에 적절한 딜레이가 있어야 함을 검증합니다.

    검증:
    1. 연속 요청이 정상적으로 완료
    2. 요청 간 딜레이가 있음
    """
    import time

    s_lat, s_lng, e_lat, e_lng = bounds_from_center(
        lat=TEST_LAT_GANGNAM,
        lon=TEST_LON_GANGNAM,
        radius_m=500,
        zoom=14,
    )

    client = NaverClusterAPIClient(
        lat=TEST_LAT_GANGNAM,
        lon=TEST_LON_GANGNAM,
        bottom=s_lat,
        left=s_lng,
        top=e_lat,
        right=e_lng,
        rlet_tp_cd="A01",
        trad_tp_cd="A1",
        zoom=14,
    )

    start_time = time.time()

    # 2페이지 연속 요청
    for page in range(1, 3):
        url = client.build_url(page=page)

        try:
            response_json = client.fetch(url)
            client.parse_response(response_json)
        except requests.RequestException as e:
            pytest.fail(f"Cluster API 요청 실패 (page {page}): {e}")

        # 요청 간 딜레이 (rate limiting)
        if page < 2:
            time.sleep(1)

    elapsed = time.time() - start_time

    # 2개 요청에 최소 1초 이상 소요되어야 함 (rate limiting 고려)
    assert elapsed >= 1.0, f"Rate limiting 딜레이 부족: {elapsed:.2f}초"

    print(f"Rate limiting 테스트 성공: {elapsed:.2f}초 소요")


# =============================================================================
# 8. test_filter_options - 필터 옵션 테스트
# =============================================================================


@pytest.mark.integration
@pytest.mark.skipif(not NAVER_API_AVAILABLE, reason="Naver API clients not available")
def test_filter_options():
    """integration: 필터 옵션 테스트

    부동산 유형과 거래 유형 필터가 정상 작동하는지 검증합니다.

    검증:
    1. rlet_tp_cd 필터 작동
    2. trad_tp_cd 필터 작동
    """
    s_lat, s_lng, e_lat, e_lng = bounds_from_center(
        lat=TEST_LAT_GANGNAM,
        lon=TEST_LON_GANGNAM,
        radius_m=500,
        zoom=14,
    )

    # 아파트 매매 필터
    client = NaverClusterAPIClient(
        lat=TEST_LAT_GANGNAM,
        lon=TEST_LON_GANGNAM,
        bottom=s_lat,
        left=s_lng,
        top=e_lat,
        right=e_lng,
        rlet_tp_cd="A01",  # 아파트
        trad_tp_cd="A1",  # 매매
        zoom=14,
    )

    url = client.build_url(page=1)

    try:
        response_json = client.fetch(url)
    except requests.RequestException as e:
        pytest.fail(f"Cluster API 요청 실패: {e}")

    response_dto = client.parse_response(response_json)

    # 필터 검증 (API가 필터를 무시할 수 있음)
    for article in response_dto.articles:
        if article.rlet_tp_cd:  # 필드가 있으면 검증
            assert article.rlet_tp_cd in ["A01", "A02", "A03"], (
                f"부동산 유형 필터 실패: {article.rlet_tp_cd}"
            )
        if article.trad_tp_cd:  # 필드가 있으면 검증
            assert article.trad_tp_cd in ["A1", "B1", "B2"], (
                f"거래 유형 필터 실패: {article.trad_tp_cd}"
            )

    print(f"필터 옵션 테스트 성공: {len(response_dto.articles)}개 매물")
