#!/usr/bin/env python3
"""거래내역 수집 테스트 스크립트"""

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler


def test_transaction_fetching():
    """거래내역 수집 기능 테스트"""
    # 설정 로드
    config = CrawlerConfig.from_env()
    crawler = NaverRealEstateCrawler(config)

    # 테스트할 단지 ID (강남구의 유명 단지)
    test_complex_id = "112581"  # 래미안강남자이

    print(f"단지 ID {test_complex_id}의 거래내역 수집 테스트 시작...")

    try:
        # 1. 단지 상세 정보 조회
        print("\n1. 단지 상세 정보 조회...")
        detail = crawler.fetch_complex_detail(test_complex_id)
        print(f"   - 단지명: {detail.get('complex_name', 'N/A')}")
        print(f"   - 평형: {list(detail.get('pyeong_types', {}).keys())}")

        # 2. 매매 목록 조회
        print("\n2. 매매 목록 조회 (A1)...")
        listings = crawler.fetch_complex_listings(test_complex_id, "A1")
        print(f"   - 매물 수: {len(listings)}")

        if listings:
            print("   - 최신 매물 3건:")
            for i, listing in enumerate(listings[:3], 1):
                print(
                    f"     {i}. 평형: {listing.get('pyeong_name', 'N/A')}, "
                    f"가격: {listing.get('deal_price', 'N/A')}, "
                    f"층: {listing.get('floor', 'N/A')}층"
                )

        # 3. 특정 평형의 거래내역 조회
        if detail.get("pyeong_types"):
            first_pyeong = list(detail["pyeong_types"].keys())[0]
            print(f"\n3. {first_pyeong} 평형의 거래내역 조회...")
            transactions = crawler.fetch_transaction_history(test_complex_id, first_pyeong, "A1")
            print(f"   - 거래내역 수: {len(transactions)}")

            if transactions:
                print("   - 최신 거래 3건:")
                for i, trans in enumerate(transactions[:3], 1):
                    print(
                        f"     {i}. 날짜: {trans.get('trade_date', 'N/A')}, "
                        f"가격: {trans.get('deal_price', 'N/A')}, "
                        f"층: {trans.get('floor', 'N/A')}층"
                    )

        print("\n✅ 거래내역 수집 테스트 성공!")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_transaction_fetching()
