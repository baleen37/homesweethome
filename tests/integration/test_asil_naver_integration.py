"""ASIL-Naver 연동 통합 테스트

ASIL 아파트 데이터를 Naver 부동산 데이터와 연동하는 통합 테스트입니다.
Mock fixture를 사용하여 실제 API 호출 없이 테스트합니다.
"""

import pytest


# =============================================================================
# test_match_single_apartment - 단일 아파트 매칭 테스트 (Mock 사용)
# =============================================================================


@pytest.mark.integration
def test_match_single_apartment(mock_asil_apts, mock_naver_search_results):
    """integration: 단일 Asil 아파트를 Naver에 매칭 (Mock fixture 사용)

    검증:
    1. Mock ASIL 데이터가 존재함
    2. Mock Naver 검색 결과가 존재함
    3. 매칭 결과에 필수 필드가 포함되어야 함
    """
    # 검증 1: Mock 데이터 존재
    assert len(mock_asil_apts) > 0, "ASIL Mock 데이터가 없음"

    # 테스트용 아파트 (래미안)
    target = mock_asil_apts[0]
    assert "래미안" in target.name, "테스트용 아파트 이름 확인"

    # 검증 2: Mock Naver 검색 결과 존재
    assert len(mock_naver_search_results) > 0, "Naver Mock 검색 결과가 없음"

    # 검증 3: 첫 번째 결과 필수 필드 확인
    first_result = mock_naver_search_results[0]
    assert first_result.complex_no, "Naver 결과: complex_no 필드 누락"
    assert first_result.complex_name, "Naver 결과: complex_name 필드 누락"


# =============================================================================
# test_integration_workflow - 전체 통합 워크플로우 테스트 (Mock 사용)
# =============================================================================


@pytest.mark.integration
def test_integration_workflow(mock_asil_apts, mock_naver_search_results, mock_naver_listings):
    """integration: 전체 워크플로우 - Asil 크롤링 → Naver 매칭 → Naver 매물 (Mock 사용)

    검증:
    1. Mock ASIL 데이터가 존재함
    2. Mock Naver 검색 결과와 매칭 가능함
    3. Mock Naver 매물 목록 구조 확인
    """
    # 검증 1: Mock 데이터 존재
    assert len(mock_asil_apts) > 0, "ASIL Mock 데이터가 없음"

    # 최대 2개 아파트로 제한
    sample_apts = mock_asil_apts[:2]

    # Step 2: Mock Naver 검색 결과와 매칭
    matched_results = []

    for apt in sample_apts:
        # Mock Naver 검색 결과에서 매칭 (이름 포함 여부로 간단 매칭)
        for naver_apt in mock_naver_search_results:
            if apt.name in naver_apt.complex_name or naver_apt.complex_name in apt.name:
                matched_results.append({"asil_apt": apt, "naver_apt": naver_apt})
                break

    # 검증 2: 최소 1개 매칭 성공
    assert len(matched_results) > 0, "Naver 매칭 결과가 없음"

    # 검증 3: Mock Naver 매물 목록 구조 확인
    assert isinstance(mock_naver_listings, list), "매물 목록은 리스트여야 함"
    assert len(mock_naver_listings) > 0, "매물 목록이 비어있음"

    # 매물 필수 필드 확인
    first_listing = mock_naver_listings[0]
    assert "article_no" in first_listing, "매물: article_no 필드 누락"
    assert "complex_no" in first_listing, "매물: complex_no 필드 누락"
    assert "price" in first_listing, "매물: price 필드 누락"
