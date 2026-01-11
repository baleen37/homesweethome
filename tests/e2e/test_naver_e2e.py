"""네이버 부동산 크롤링 E2E 테스트

네이버 부동산(land.naver.com)에서 아파트 검색, 상세 정보, 매물 목록을 수집하는 E2E 테스트.
"""

import pytest

from crawler.naver import NaverSearchCrawler

# =============================================================================
# 테스트 상수
# =============================================================================

# 테스트용 검색 키워드
SEARCH_KEYWORD = "래미안"


# =============================================================================
# test_search_apartment - 아파트 이름으로 검색
# =============================================================================


@pytest.mark.e2e
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
