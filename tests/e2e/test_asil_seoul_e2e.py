"""ASIL 서울 아파트 E2E 테스트

실제 API를 호출하여 크롤링이 동작하는지 검증합니다.
"""

import pytest

from crawler.asil import AsilAptListCrawler


@pytest.mark.e2e
def test_crawl_seoul_apartments_e2e():
    """integration: 서울 아파트 목록 크롤링

    검증:
    1. ASIL API에서 성공적으로 데이터 가져옴
    2. 각 레코드가 필수 필드를 가짐
    3. 데이터 타입이 올바름
    """
    # 데이터 수집 (역삼동, 청담동, 삼성동)
    dong_codes = ["1168010100", "1168010200", "1168010300"]
    all_apartments = []
    crawled_dongs = set()

    for dong_code in dong_codes:
        crawler = AsilAptListCrawler(dong_code=dong_code)
        results = crawler.crawl()

        if results:
            crawled_dongs.add(dong_code)
            all_apartments.extend(results)

    # 검증 1: 최소 데이터 및 레코드 검증
    assert len(crawled_dongs) > 0, "적어도 하나의 동에서 데이터를 가져와야 함"
    assert len(all_apartments) > 0, "아파트 데이터가 없음"

    # 검증 2: 필수 필드 검증
    for apt in all_apartments:
        assert apt.seq, f"seq 필드가 비어있음 (name: {apt.name})"
        assert apt.name, f"name 필드가 비어있음 (seq: {apt.seq})"
        assert apt.dong, f"dong 필드가 비어있음 (name: {apt.name})"
        assert apt.dongname, f"dongname 필드가 비어있음 (name: {apt.name})"

    # 검증 3: 데이터 타입 검증
    for apt in all_apartments:
        assert isinstance(apt.seq, str), f"seq는 str이어야 함 (실제: {type(apt.seq)})"
        assert isinstance(apt.name, str), f"name은 str이어야 함 (실제: {type(apt.name)})"
        assert isinstance(apt.dong, str), f"dong은 str이어야 함 (실제: {type(apt.dong)})"
        assert isinstance(apt.dongname, str), (
            f"dongname은 str이어야 함 (실제: {type(apt.dongname)})"
        )

    # 검증 4: 중복 seq 확인 (경고만, API 데이터에 중복이 있을 수 있음)
    seq_list = [apt.seq for apt in all_apartments]
    unique_seq_count = len(set(seq_list))
    duplicate_count = len(seq_list) - unique_seq_count
    if duplicate_count > 0:
        import warnings

        warnings.warn(f"중복된 seq 존재: {duplicate_count}개 (API 데이터 중복 가능성)")
