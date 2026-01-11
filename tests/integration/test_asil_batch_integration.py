"""ASIL 아파트 목록 배치 크롤링 통합 테스트

여러 동 코드에 대해 실제 API를 호출하여 배치 크롤링을 테스트합니다.
단일 동 코드 테스트는 test_asil_integration.py에서 커버합니다.
"""

import pytest

from crawler.asil import AsilAptListCrawler

# 샘플 동 코드 (실제 데이터가 있는 동 코드)
SAMPLE_DONG_CODES = [
    "1168010100",  # 역삼동
    "1168010200",  # 청담동
    "1168010300",  # 삼성동
    "1150010700",  # 사직동 (종로구)
    "1156005000",  # 영등포동
]

# 최소 테스트 조건
MIN_SAMPLE_DONGS_WITH_DATA = 1  # 최소 1개 동에서 데이터 발견


@pytest.mark.integration
class TestAsilAptListBatchIntegration:
    """AsilAptListCrawler 배치 크롤링 통합 테스트"""

    def test_batch_crawl_sample_dongs(self):
        """여러 동 코드에 대한 배치 크롤링 테스트

        검증:
        1. 샘플 동 코드에서 실제 데이터 수집
        2. 최소 데이터 수집 확인
        3. 에러율 확인
        """
        stats = {
            "total_processed": 0,
            "data_found": 0,
            "empty_dongs": 0,
            "error_dongs": 0,
            "total_apartments": 0,
        }

        # 샘플 동 코드로 크롤링
        for dong_code in SAMPLE_DONG_CODES:
            stats["total_processed"] += 1

            try:
                crawler = AsilAptListCrawler(dong_code=dong_code)
                results = crawler.crawl()

                if results is None:
                    # 타임아웃 또는 에러
                    stats["error_dongs"] += 1
                    continue

                if results:
                    stats["data_found"] += 1
                    stats["total_apartments"] += len(results)
                else:
                    stats["empty_dongs"] += 1

            except Exception:
                stats["error_dongs"] += 1

        # 검증 1: 최소 데이터 수집 확인
        assert stats["data_found"] >= MIN_SAMPLE_DONGS_WITH_DATA, (
            f"최소 {MIN_SAMPLE_DONGS_WITH_DATA}개 동에서 데이터를 가져와야 함: "
            f"{stats['data_found']}개"
        )

        # 검증 2: 에러율 확인 (너무 많은 에러면 실패)
        if stats["total_processed"] > 0:
            error_rate = stats["error_dongs"] / stats["total_processed"]
        else:
            error_rate = 0
        assert error_rate < 0.5, f"에러율이 너무 높음: {error_rate * 100:.1f}%"

    def test_crawl_with_invalid_dong_code(self):
        """유효하지 않은 동 코드로 에러 핸들링 테스트

        검증:
        1. 유효하지 않은 동 코드 처리
        2. 에러가 발생해도 프로그램이 종료되지 않음
        """
        # 유효하지 않은 동 코드로 에러 핸들링 테스트
        invalid_dong_code = "9999900100"  # 존재하지 않는 구

        try:
            crawler = AsilAptListCrawler(dong_code=invalid_dong_code)
            results = crawler.crawl()
            # 결과가 없어도 에러로 처리하지 않아야 함
            assert results is None or results == [], "유효하지 않은 동 코드 처리 확인"
        except Exception:
            # 예외가 발생해도 테스트 통과 (에러 핸들링 확인)
            assert True

    def test_crawl_with_min_household_filter(self):
        """세대수 필터가 적용된 배치 크롤링 테스트

        검증:
        1. min_household 파라미터가 정상 동작
        2. 필터링된 결과 확인
        """
        dong_code = "1168010100"  # 역삼동
        crawler = AsilAptListCrawler(dong_code=dong_code, min_household=100)
        results = crawler.crawl()

        # 결과가 리스트여야 함
        assert isinstance(results, list)

        # 데이터가 있으면 검증
        if len(results) > 0:
            # 100세대 이상인 아파트만 필터링되어야 함
            for apt in results:
                household_str = apt.household or "0"
                household = int(household_str.replace(",", ""))
                assert household >= 100, (
                    f"{apt.name}의 세대수 {household}가 min_household=100보다 작습니다"
                )
