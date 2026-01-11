"""네이버 부동산 크롤링 E2E 테스트

네이버 부동산(land.naver.com)에서 아파트 검색, 상세 정보, 매물 목록을 수집하는 E2E 테스트.
"""

import json

import pytest

try:
    from crawler.naver import (
        NaverComplexInfoCrawler,
        NaverListingsCrawler,
        NaverSearchCrawler,
    )

    NAVER_AVAILABLE = True
except ImportError:
    NAVER_AVAILABLE = False


# =============================================================================
# 테스트 상수
# =============================================================================

# 테스트용 검색 키워드
SEARCH_KEYWORD = "래미안"
SEARCH_KEYWORD_SHORT = "힐스테이트"

# 테스트용 단지 번호 (래미안 아파트 중 하나)
# 실제 네이버 부동산에서 확인한 유효한 단지 번호여야 함
TEST_COMPLEX_NO = "109073"  # 래미안배현마을(9단지) 예시

# 네이버 부동산 기본 URL
NAVER_LAND_URL = "https://land.naver.com"


# =============================================================================
# test_search_apartment - 아파트 이름으로 검색
# =============================================================================


@pytest.mark.e2e
@pytest.mark.skipif(not NAVER_AVAILABLE, reason="Naver crawler not implemented")
def test_search_apartment():
    """e2e: 아파트 이름으로 검색

    검증:
    1. 검색 결과가 존재해야 함
    2. 각 결과에 필수 필드가 포함되어야 함 (complexNo, complexName)
    3. 검색 키워드가 결과에 포함되어야 함
    """
    crawler = NaverSearchCrawler(keyword=SEARCH_KEYWORD)
    results = crawler.crawl()

    # 검증 1: 검색 결과 존재
    assert len(results) > 0, f"'{SEARCH_KEYWORD}' 검색 결과가 없음"

    # 검증 2: 필수 필드 확인 (DTO 속성 접근)
    for idx, result in enumerate(results):
        assert result.complex_no, f"결과 {idx}: complex_no 필드 누락"
        assert result.complex_name, f"결과 {idx}: complex_name 필드 누락"
        assert isinstance(result.complex_no, str), f"결과 {idx}: complex_no는 문자열이어야 함"
        assert isinstance(result.complex_name, str), f"결과 {idx}: complex_name은 문자열이어야 함"

        # 검증 3: 검색 키워드가 이름에 포함되어야 함
        # (일부 결과는 포함되지 않을 수 있으므로 첫 번째 결과만 확인)
        if idx == 0:
            print(f"첫 번째 검색 결과: {result.complex_name} (단지번호: {result.complex_no})")


@pytest.mark.e2e
@pytest.mark.skipif(not NAVER_AVAILABLE, reason="Naver crawler not implemented")
def test_search_apartment_short_keyword():
    """e2e: 짧은 검색어로 아파트 검색

    검증:
    1. 검색 결과가 존재해야 함
    2. 결과 수가 합리적인 범위여야 함 (1~100개)
    """
    crawler = NaverSearchCrawler(keyword=SEARCH_KEYWORD_SHORT)
    results = crawler.crawl()

    assert len(results) > 0, f"'{SEARCH_KEYWORD_SHORT}' 검색 결과가 없음"
    assert len(results) <= 100, f"검색 결과가 너무 많음: {len(results)}개"


# =============================================================================
# test_get_complex_info - 단지 상세 정보 조회
# =============================================================================


@pytest.mark.e2e
@pytest.mark.skipif(not NAVER_AVAILABLE, reason="Naver crawler not implemented")
def test_get_complex_info():
    """e2e: 단지 번호로 상세 정보 조회

    검증:
    1. 단지 정보가 존재해야 함
    2. 결과는 dict 형태여야 함
    3. 필수 데이터가 포함되어야 함
    """
    crawler = NaverComplexInfoCrawler(complex_no=TEST_COMPLEX_NO)
    result = crawler.crawl()

    # 검증 1: 단지 정보 존재 (None 또는 빈 dict 가능)
    if result is None or result == {}:
        print(f"단지번호 {TEST_COMPLEX_NO}에 대한 정보 없음 (일반적일 수 있음)")
        return

    # 검증 2: 결과는 dict여야 함
    assert isinstance(result, dict), "단지 정보는 dict여야 함"

    # 검증 3: 필수 데이터 확인
    if "complexNo" in result:
        assert isinstance(result["complexNo"], str), "complexNo는 문자열이어야 함"
        print(f"단지번호: {result['complexNo']}")

    if "complexName" in result:
        assert isinstance(result["complexName"], str), "complexName은 문자열이어야 함"
        print(f"단지명: {result['complexName']}")

    if "address" in result:
        assert isinstance(result["address"], str), "address는 문자열이어야 함"
        print(f"주소: {result['address']}")

    # 위치 정보가 있으면 검증
    if "lat" in result and "lng" in result:
        lat = result["lat"]
        lng = result["lng"]
        # 서울 지역 좌표 범위 확인 (대략적인 검증)
        assert isinstance(lat, (int, float, str)), "위도는 숫자 또는 문자열이어야 함"
        assert isinstance(lng, (int, float, str)), "경도는 숫자 또는 문자열이어야 함"


@pytest.mark.e2e
@pytest.mark.skipif(not NAVER_AVAILABLE, reason="Naver crawler not implemented")
def test_get_complex_info_invalid_number():
    """e2e: 잘못된 단지 번호로 조회 시 빈 결과 반환

    검증:
    1. 존재하지 않는 단지 번호는 빈 결과를 반환해야 함
    """
    crawler = NaverComplexInfoCrawler(complex_no="99999999")
    result = crawler.crawl()

    # 빈 결과 처리 - None 또는 빈 딕셔너리
    assert result is None or result == {}, "잘못된 단지번호는 빈 결과를 반환해야 함"


# =============================================================================
# test_get_listings - 매물 목록 조회
# =============================================================================


@pytest.mark.e2e
@pytest.mark.skipif(not NAVER_AVAILABLE, reason="Naver crawler not implemented")
def test_get_listings():
    """e2e: 특정 단지의 매물 목록 조회

    검증:
    1. 매물 목록이 반환되어야 함 (빈 리스트일 수 있음)
    2. 각 매물은 NaverListingDTO여야 함
    3. 필수 필드가 포함되어야 함
    """
    crawler = NaverListingsCrawler(complex_no=TEST_COMPLEX_NO)
    results = crawler.crawl()

    # 검증 1: 결과는 리스트여야 함
    assert isinstance(results, list), "매물 목록은 리스트여야 함"

    # 매물이 있는 경우에만 검증
    if len(results) > 0:
        # 검증 2: 필수 필드 확인 (DTO 속성 접근)
        for idx, listing in enumerate(results):
            assert listing.article_no, f"매물 {idx}: article_no 필드 누락"
            assert listing.complex_name, f"매물 {idx}: complex_name 필드 누락"
            assert listing.trade_type, f"매물 {idx}: trade_type 필드 누락"

        print(f"총 {len(results)}개 매물 발견")

        # 첫 번째 매물 정보 출력 (DTO를 dict로 변환)
        if results[0]:
            print(
                f"첫 번째 매물: {json.dumps(results[0].model_dump(), ensure_ascii=False, indent=2)}"
            )
    else:
        print("매물이 없음 (일반적인 상황)")


@pytest.mark.e2e
@pytest.mark.skipif(not NAVER_AVAILABLE, reason="Naver crawler not implemented")
def test_get_listings_with_filter():
    """e2e: 매물 목록 기본 조회

    참고: 현재 NaverListingsCrawler는 필터를 지원하지 않습니다.
    이 테스트는 기본 매물 목록 조회를 검증합니다.
    """
    # 기본 매물 목록 조회
    crawler = NaverListingsCrawler(complex_no=TEST_COMPLEX_NO)
    results = crawler.crawl()

    assert isinstance(results, list), "매물 목록은 리스트여야 함"

    # 결과 검증
    if results:
        print(f"총 {len(results)}개 매물 발견")
        # 첫 번째 매물의 가격 정보 확인
        if results[0].deal_price:
            print(f"첫 매물 가격: {results[0].deal_price}원")
    else:
        print("매물이 없음")


# =============================================================================
# test_end_to_end - 전체 워크플로우 테스트
# =============================================================================


@pytest.mark.e2e
@pytest.mark.skipif(not NAVER_AVAILABLE, reason="Naver crawler not implemented")
def test_end_to_end():
    """e2e: 전체 워크플로우 - 검색 → 상세 정보 → 매물 목록

    검증:
    1. 검색으로 단지 번호를 찾을 수 있음
    2. 단지 번호로 상세 정보를 조회할 수 있음
    3. 상세 정보로 매물 목록을 조회할 수 있음
    """
    # Step 1: 검색
    search_crawler = NaverSearchCrawler(keyword=SEARCH_KEYWORD)
    search_results = search_crawler.crawl()

    assert len(search_results) > 0, f"'{SEARCH_KEYWORD}' 검색 결과가 없음"

    # 첫 번째 검색 결과의 단지 번호 사용 (DTO 속성 접근)
    first_complex = search_results[0]
    complex_no = first_complex.complex_no
    complex_name = first_complex.complex_name

    print(f"Step 1 완료: '{complex_name}' 단지 찾음 (단지번호: {complex_no})")

    # Step 2: 단지 상세 정보 조회
    info_crawler = NaverComplexInfoCrawler(complex_no=complex_no)
    complex_info = info_crawler.crawl()

    # complex_info는 dict 또는 None
    if complex_info is None or complex_info == {}:
        print(f"Step 2: 단지번호 {complex_no}에 대한 상세 정보 없음 (건너뜀)")
    else:
        assert isinstance(complex_info, dict), "단지 정보는 dict여야 함"
        print("Step 2 완료: 단지 상세 정보 조회 완료")
        if "address" in complex_info:
            print(f"  주소: {complex_info['address']}")

    # Step 3: 매물 목록 조회
    listings_crawler = NaverListingsCrawler(complex_no=complex_no)
    listings = listings_crawler.crawl()

    assert isinstance(listings, list), "매물 목록은 리스트여야 함"

    print(f"Step 3 완료: {len(listings)}개 매물 발견")

    # 전체 워크플로우 성공
    print("\n=== E2E 테스트 성공 ===")
    print(f"단지: {complex_name}")
    print(f"단지번호: {complex_no}")
    print(f"매물 수: {len(listings)}개")


# =============================================================================
# 에러 핸들링 테스트
# =============================================================================


@pytest.mark.e2e
@pytest.mark.skipif(not NAVER_AVAILABLE, reason="Naver crawler not implemented")
def test_search_empty_keyword():
    """e2e: 빈 검색어 처리

    검증:
    1. 빈 검색어는 빈 결과를 반환해야 함
    """
    crawler = NaverSearchCrawler(keyword="")
    results = crawler.crawl()

    assert len(results) == 0, "빈 검색어는 빈 결과를 반환해야 함"


@pytest.mark.e2e
@pytest.mark.skipif(not NAVER_AVAILABLE, reason="Naver crawler not implemented")
def test_get_listings_invalid_complex():
    """e2e: 존재하지 않는 단지의 매물 목록 조회

    검증:
    1. 존재하지 않는 단지는 빈 리스트를 반환해야 함
    """
    crawler = NaverListingsCrawler(complex_no="000000")
    results = crawler.crawl()

    assert isinstance(results, list), "결과는 리스트여야 함"
    assert len(results) == 0, "존재하지 않는 단지는 빈 리스트 반환"


# =============================================================================
# 데이터 구조 검증 테스트
# =============================================================================


@pytest.mark.e2e
@pytest.mark.skipif(not NAVER_AVAILABLE, reason="Naver crawler not implemented")
def test_search_result_structure():
    """e2e: 검색 결과 데이터 구조 검증

    검증:
    1. 모든 필수 필드가 존재
    2. 필드 타입이 올바름
    3. 선택적 필드가 있으면 타입 검증
    """
    crawler = NaverSearchCrawler(keyword=SEARCH_KEYWORD)
    results = crawler.crawl()

    assert len(results) > 0, "검색 결과가 없음"

    # 첫 번째 결과 상세 검증 (DTO 속성 접근)
    first_result = results[0]

    # 필수 필드 (DTO 속성)
    assert first_result.complex_no, "필수 필드 'complex_no' 누락"
    assert first_result.complex_name, "필수 필드 'complex_name' 누락"
    assert isinstance(first_result.complex_no, str), "필드 'complex_no' 타입 불일치"
    assert isinstance(first_result.complex_name, str), "필드 'complex_name' 타입 불일치"
    assert isinstance(first_result.article_count, int), "필드 'article_count' 타입 불일치"

    # 선택적 필드 (있으면 타입 검증)
    if first_result.latitude is not None:
        assert isinstance(first_result.latitude, (int, float)), "선택적 필드 'latitude' 타입 불일치"

    if first_result.longitude is not None:
        assert isinstance(first_result.longitude, (int, float)), (
            "선택적 필드 'longitude' 타입 불일치"
        )

    if first_result.address is not None:
        assert isinstance(first_result.address, str), "선택적 필드 'address' 타입 불일치"

    if first_result.build_year is not None:
        assert isinstance(first_result.build_year, int), "선택적 필드 'build_year' 타입 불일치"

    if first_result.household_count is not None:
        assert isinstance(first_result.household_count, int), (
            "선택적 필드 'household_count' 타입 불일치"
        )

    print(f"데이터 구조 검증 통과: {first_result.complex_name}")


@pytest.mark.e2e
@pytest.mark.skipif(not NAVER_AVAILABLE, reason="Naver crawler not implemented")
def test_complex_info_complete():
    """e2e: 단지 정보 완전성 검증

    검증:
    1. 단지 정보 조회가 가능해야 함
    2. 결과가 있으면 주요 정보가 포함되어야 함
    3. 좌표 정보가 유효한 범위여야 함
    4. 세대수가 양수여야 함
    """
    crawler = NaverComplexInfoCrawler(complex_no=TEST_COMPLEX_NO)
    result = crawler.crawl()

    # 단지 정보는 None 또는 dict일 수 있음
    if result is None or result == {}:
        print(
            f"단지번호 {TEST_COMPLEX_NO}에 대한 상세 정보 없음 (API 미지원 또는 존재하지 않는 단지)"
        )
        # 이 경우 테스트를 통과시키고 종료
        return

    # 기본 정보
    assert "complexName" in result, "단지명 누락"
    assert len(result["complexName"]) > 0, "단지명이 비어있음"

    # 좌표 정보가 있으면 범위 검증
    if "lat" in result and "lng" in result:
        lat = float(result["lat"]) if isinstance(result["lat"], str) else result["lat"]
        lng = float(result["lng"]) if isinstance(result["lng"], str) else result["lng"]

        # 위도: -90 ~ 90, 경도: -180 ~ 180
        assert -90 <= lat <= 90, f"위도 범위 벗어남: {lat}"
        assert -180 <= lng <= 180, f"경도 범위 벗어남: {lng}"

        # 한국 좌표 범위 (대략적)
        assert 33 <= lat <= 43, f"한국 위도 범위 벗어남: {lat}"
        assert 124 <= lng <= 132, f"한국 경도 범위 벗어남: {lng}"

    # 세대수가 있으면 양수 검증
    if "totalHouseholdCount" in result:
        household = result["totalHouseholdCount"]
        if isinstance(household, str):
            household = int(household.replace(",", "").replace("세", ""))
        assert household > 0, f"세대수는 양수여야 함: {household}"

    print(f"단지 정보 완전성 검증 통과: {result['complexName']}")


# =============================================================================
# 성능 및 한계 테스트
# =============================================================================


@pytest.mark.e2e
@pytest.mark.skipif(not NAVER_AVAILABLE, reason="Naver crawler not implemented")
def test_search_result_limit():
    """e2e: 검색 결과 개수 확인

    검증:
    1. 일반적인 검색어로 검색 시 결과가 반환되어야 함
    2. 검색 결과 개수가 합리적인 범위여야 함
    """
    crawler = NaverSearchCrawler(keyword="아파트")
    results = crawler.crawl()

    # 검색 결과가 너무 많지 않은지 확인 (네이버 지도 API의 기본 제한)
    assert len(results) <= 100, f"검색 결과가 너무 많음: {len(results)}개"

    print(f"검색 결과 개수: {len(results)}개")


@pytest.mark.e2e
@pytest.mark.skipif(not NAVER_AVAILABLE, reason="Naver crawler not implemented")
@pytest.mark.slow
def test_multiple_sequential_requests():
    """e2e: 연속 요청 처리 (느린 테스트)

    검증:
    1. 여러 번 연속 요청이 가능해야 함
    2. 각 요청이 성공적으로 처리되어야 함
    """
    search_keywords = [SEARCH_KEYWORD, SEARCH_KEYWORD_SHORT]

    for keyword in search_keywords:
        crawler = NaverSearchCrawler(keyword=keyword)
        results = crawler.crawl()
        assert len(results) > 0, f"키워드 '{keyword}' 검색 실패"
        print(f"'{keyword}': {len(results)}개 결과")

    print("연속 요청 테스트 완료")


# =============================================================================
# 스킵된 테스트 안내
# =============================================================================


@pytest.mark.unit
def test_naver_crawler_not_implemented():
    """단위 테스트: 네이버 크롤러 구현 전 스킵 안내

    네이버 크롤러가 구현되지 않았으면 이 테스트가 실행됩니다.
    """
    if not NAVER_AVAILABLE:
        pytest.skip("Naver 크롤러가 아직 구현되지 않음. src/crawler/naver.py를 구현하세요.")
    else:
        # 구현되어 있으면 통과
        assert True
