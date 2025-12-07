"""
End-to-End 크롤링 통합 테스트

이 테스트는 실제 네이버 부동산 API를 호출하여 전체 크롤링 워크플로우를 검증합니다.
TDD의 RED 단계로, 현재 코드의 문제점을 드러내기 위해 작성되었습니다.

대상: 동작구 노량진동 (cortarNo: 1111010300)
- 단지 목록 조회
- 단지 상세 정보 조회
- 거래내역 조회 (1페이지만)
"""

import pytest
import time

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler


@pytest.fixture(scope="module")
def config():
    """테스트용 CrawlerConfig 설정"""
    # 환경 변수에서 직접 설정 (실제 API 호출 필요)
    config = CrawlerConfig(
        base_url="https://m.land.naver.com",
        timeout=30,
        rate_limit=5.0,  # 5초 간격 (느리게 설정)
        max_retries=3,
        output_dir="output_test",
    )
    return config


@pytest.fixture(scope="module")
def crawler(config):
    """NaverRealEstateCrawler 인스턴스 생성"""
    return NaverRealEstateCrawler(config)


class TestEndToEndCrawling:
    """End-to-End 크롤링 테스트"""

    # 테스트 대상: 동작구 노량진동
    NORYANGJIN_DONG_CODE = "1111010300"
    NORYANGJIN_BOUNDS = {
        "min_lat": 37.5114,
        "max_lat": 37.5270,
        "min_lng": 126.9347,
        "max_lng": 126.9541,
    }

    def test_complex_list_retrieval(self, crawler):
        """
        단지 목록 조회 테스트

        GIVEN: 노량진동 코드와 경계 좌표
        WHEN: 단지 목록을 조회하면
        THEN: 적어도 1개 이상의 단지 정보가 반환되어야 함
        """
        # 시작 시간 기록 (성능 측정)
        start_time = time.time()

        # 단지 목록 조회
        complexes = crawler.fetch_complex_list(
            cortar_no=self.NORYANGJIN_DONG_CODE, bounds=self.NORYANGJIN_BOUNDS
        )

        # 소요 시간 계산
        elapsed_time = time.time() - start_time

        # 기본 응답 검증
        assert complexes is not None, "단지 목록 응답이 None입니다"
        assert isinstance(complexes, list), "단지 목록이 리스트가 아닙니다"
        assert len(complexes) > 0, "노량진동에 단지가 없습니다"

        # 첫 번째 단지 정보 상세 검증
        first_complex = complexes[0]
        assert "complexNo" in first_complex, "단지번호(complexNo) 필드가 누락되었습니다"
        assert "complexName" in first_complex, "단지명(complexName) 필드가 누락되었습니다"
        assert "address" in first_complex, "주소(address) 필드가 누락되었습니다"

        # 성능 검증: 10초 이내에 응답해야 함
        assert elapsed_time < 10.0, f"단지 목록 조회가 너무 느립니다: {elapsed_time:.2f}초"

        # 로그 출력
        print("\n✓ 단지 목록 조회 성공:")
        print(f"  - 소요 시간: {elapsed_time:.2f}초")
        print(f"  - 단지 수: {len(complexes)}개")
        print(f"  - 첫 번째 단지: {first_complex.get('complexName', 'N/A')}")

    def test_complex_detail_retrieval(self, crawler):
        """
        단지 상세 정보 조회 테스트

        GIVEN: 유효한 단지번호
        WHEN: 단지 상세 정보를 조회하면
        THEN: 상세 정보의 모든 필드가 포함되어야 함
        """
        # 먼저 단지 목록에서 첫 번째 단지 ID 가져오기
        complexes = crawler.fetch_complex_list(
            cortar_no=self.NORYANGJIN_DONG_CODE, bounds=self.NORYANGJIN_BOUNDS
        )

        assert len(complexes) > 0, "상세 정보 조회할 단지가 없습니다"
        complex_id = complexes[0]["complexNo"]

        # 시작 시간 기록
        start_time = time.time()

        # 단지 상세 정보 조회
        detail = crawler.fetch_complex_detail(complex_id)

        # 소요 시간 계산
        elapsed_time = time.time() - start_time

        # 기본 응답 검증
        assert detail is not None, "단지 상세 정보 응답이 None입니다"
        assert isinstance(detail, dict), "단지 상세 정보가 딕셔너리가 아닙니다"

        # 필수 필드 검증
        required_fields = [
            "complexNo",
            "complexName",
            "address",
            "buildYear",
            "households",
            "allsizes",
            "floors",
        ]
        for field in required_fields:
            assert field in detail, f"필수 필드 '{field}'가 누락되었습니다"

        # 데이터 타입 검증
        assert isinstance(detail["households"], (int, str)), "세대수가 숫자가 아닙니다"
        assert detail["buildYear"] is not None, "건축년도가 없습니다"

        # 성능 검증: 5초 이내에 응답해야 함
        assert elapsed_time < 5.0, f"단지 상세 정보 조회가 너무 느립니다: {elapsed_time:.2f}초"

        # 로그 출력
        print("\n✓ 단지 상세 정보 조회 성공:")
        print(f"  - 소요 시간: {elapsed_time:.2f}초")
        print(f"  - 단지명: {detail.get('complexName', 'N/A')}")
        print(f"  - 주소: {detail.get('address', 'N/A')}")
        print(f"  - 세대수: {detail.get('households', 'N/A')}")

    def test_transaction_list_retrieval(self, crawler):
        """
        거래내역 조회 테스트

        GIVEN: 유효한 단지번호
        WHEN: 매매 거래내역 1페이지를 조회하면
        THEN: 거래내역 정보와 페이지네이션 정보가 반환되어야 함
        """
        # 먼저 단지 목록에서 첫 번째 단지 ID 가져오기
        complexes = crawler.fetch_complex_list(
            cortar_no=self.NORYANGJIN_DONG_CODE, bounds=self.NORYANGJIN_BOUNDS
        )

        assert len(complexes) > 0, "거래내역을 조회할 단지가 없습니다"
        complex_id = complexes[0]["complexNo"]

        # 시작 시간 기록
        start_time = time.time()

        # 거래내역 조회 (매매, 1페이지)
        result = crawler.fetch_complex_listings(
            complex_id=complex_id,
            trade_type="A1",  # 매매
            page=1,
        )

        # 소요 시간 계산
        elapsed_time = time.time() - start_time

        # 기본 응답 검증
        assert result is not None, "거래내역 응답이 None입니다"
        assert isinstance(result, dict), "거래내역 응답이 딕셔너리가 아닙니다"

        # 거래내역 목록 검증
        assert "list" in result, "거래내역 목록(list) 필드가 누락되었습니다"
        listings = result["list"]
        assert isinstance(listings, list), "거래내역 목록이 리스트가 아닙니다"

        # 최소한의 거래내역이 있어야 함 (있을 경우만 검증)
        if len(listings) > 0:
            first_listing = listings[0]

            # 필수 필드 검증
            required_fields = ["articleNo", "cortarNo", "tradTpNm", "dealingGbn", "objAmt", "spc1"]
            for field in required_fields:
                assert field in first_listing, f"거래내역 필수 필드 '{field}'가 누락되었습니다"

            # 가격 정보 검증
            assert first_listing.get("objAmt"), "거래가격 정보가 없습니다"
            assert first_listing.get("spc1"), "전용면적 정보가 없습니다"

        # 페이지네이션 정보 검증
        assert "pagination" in result, "페이지네이션 정보가 누락되었습니다"
        pagination = result["pagination"]
        assert "page" in pagination, "현재 페이지 정보가 없습니다"
        assert "total" in pagination, "전체 개수 정보가 없습니다"

        # 성능 검증: 5초 이내에 응답해야 함
        assert elapsed_time < 5.0, f"거래내역 조회가 너무 느립니다: {elapsed_time:.2f}초"

        # 로그 출력
        print("\n✓ 거래내역 조회 성공:")
        print(f"  - 소요 시간: {elapsed_time:.2f}초")
        print(f"  - 거래내역 수: {len(listings)}개")
        print(f"  - 현재 페이지: {pagination.get('page', 'N/A')}")
        print(f"  - 전체 개수: {pagination.get('total', 'N/A')}")

    def test_full_workflow_integration(self, crawler):
        """
        전체 워크플로우 통합 테스트

        GIVEN: 노량진동
        WHEN: 단지 목록 → 상세 정보 → 거래내역 순서로 조회하면
        THEN: 모든 단계에서 유효한 데이터가 반환되어야 함
        """
        # 전체 워크플로우 시작 시간
        workflow_start = time.time()

        # 1. 단지 목록 조회
        print("\n=== 단계 1: 단지 목록 조회 ===")
        complexes = crawler.fetch_complex_list(
            cortar_no=self.NORYANGJIN_DONG_CODE, bounds=self.NORYANGJIN_BOUNDS
        )
        assert len(complexes) > 0, "워크플로우 실패: 단지 목록 조회 실패"

        # 첫 번째 단지 선택
        target_complex = complexes[0]
        complex_id = target_complex["complexNo"]
        print(f"선택된 단지: {target_complex.get('complexName', 'N/A')}")

        # 2. 단지 상세 정보 조회
        print("\n=== 단계 2: 단지 상세 정보 조회 ===")
        detail = crawler.fetch_complex_detail(complex_id)
        assert detail is not None, "워크플로우 실패: 단지 상세 정보 조회 실패"
        assert "complexName" in detail, "워크플로우 실패: 상세 정보에 단지명 없음"
        print(f"단지명: {detail.get('complexName', 'N/A')}")

        # 3. 거래내역 조회
        print("\n=== 단계 3: 거래내역 조회 ===")
        transaction_result = crawler.fetch_complex_listings(
            complex_id=complex_id, trade_type="A1", page=1
        )
        assert transaction_result is not None, "워크플로우 실패: 거래내역 조회 실패"

        # 전체 워크플로우 소요 시간
        total_time = time.time() - workflow_start

        # 워크플로우 성공 검증
        assert total_time < 30.0, f"전체 워크플로우가 너무 느립니다: {total_time:.2f}초"

        # 데이터 일관성 검증
        assert detail["complexNo"] == complex_id, "단지 ID 불일치"
        assert detail["complexName"] == target_complex["complexName"], "단지명 불일치"

        # 최종 로그
        print("\n✓ 전체 워크플로우 성공:")
        print(f"  - 총 소요 시간: {total_time:.2f}초")
        print(f"  - 단지명: {detail.get('complexName', 'N/A')}")
        print(f"  - 주소: {detail.get('address', 'N/A')}")
        print(f"  - 세대수: {detail.get('households', 'N/A')}")
        print(f"  - 거래내역 수: {len(transaction_result.get('list', []))}개")

    @pytest.mark.parametrize("trade_type", ["A1", "B1", "B2"])
    def test_different_trade_types(self, crawler, trade_type):
        """
        다양한 거래유형 조회 테스트

        GIVEN: 유효한 단지번호
        WHEN: 매매(A1), 전세(B1), 월세(B2) 거래내역을 각각 조회하면
        THEN: 모든 거래유형에 대한 응답이 반환되어야 함
        """
        # 단지 목록에서 첫 번째 단지 ID 가져오기
        complexes = crawler.fetch_complex_list(
            cortar_no=self.NORYANGJIN_DONG_CODE, bounds=self.NORYANGJIN_BOUNDS
        )

        if len(complexes) == 0:
            pytest.skip("테스트할 단지가 없습니다")

        complex_id = complexes[0]["complexNo"]

        # 거래내역 조회
        result = crawler.fetch_complex_listings(
            complex_id=complex_id, trade_type=trade_type, page=1
        )

        # 기본 검증
        assert result is not None, f"{trade_type} 거래내역 응답이 None입니다"
        assert isinstance(result, dict), f"{trade_type} 거래내역 응답이 딕셔너리가 아닙니다"
        assert "list" in result, f"{trade_type} 거래내역 목록이 없습니다"
        assert "pagination" in result, f"{trade_type} 페이지네이션 정보가 없습니다"

        # 거래유형 이름 확인
        trade_type_names = {"A1": "매매", "B1": "전세", "B2": "월세"}
        print(f"\n✓ {trade_type_names[trade_type]} 거래내역 조회 성공")
        print(f"  - 거래내역 수: {len(result['list'])}개")
