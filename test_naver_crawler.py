#!/usr/bin/env python3
"""
네이버 부동산 크롤러 테스트 스크립트
"""

import sys
from pathlib import Path

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler


def test_fetch_dong_data():
    """법정동 데이터 수집 테스트"""
    print("🧪 법정동 데이터 수집 테스트 시작...")

    # 테스트용 동 데이터
    test_dong = {
        "cortarNo": "1168010500",  # 강남구 청담동
        "dong_name": "청담동",
    }

    # 크롤러 생성
    config = CrawlerConfig()
    crawler = NaverRealEstateCrawler(config)

    try:
        # 데이터 수집
        result = crawler._fetch_dong_data(test_dong)

        print(f"✅ 결과: {len(result)}개 단지")
        for i, complex in enumerate(result[:5], 1):
            print(f"  {i}. {complex.get('complex_name', 'N/A')} (ID: {complex.get('complex_id', 'N/A')})")

        return result

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        return []

    finally:
        # 브라우저 리소스 정리
        if hasattr(crawler, 'browser_manager'):
            crawler.browser_manager.close_all()


def test_fetch_complex_listings():
    """단지별 매물 목록 수집 테스트"""
    print("\n🧪 단지별 매물 목록 수집 테스트 시작...")

    # 테스트용 단지 ID
    test_complex_id = "112581"  # 힐스테이트 서울숲 (예시)

    # 크롤러 생성
    config = CrawlerConfig()
    crawler = NaverRealEstateCrawler(config)

    try:
        # 매물 목록 수집
        result = crawler.fetch_complex_listings(test_complex_id, trade_type="A1")

        print(f"✅ 결과: {len(result)}개 매물")
        for i, listing in enumerate(result[:5], 1):
            print(f"  {i}. 가격: {listing.get('price', 'N/A')}")
            print(f"     면적: {listing.get('area', 'N/A')}㎡")
            print(f"     층: {listing.get('floor', 'N/A')}")

        return result

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        return []

    finally:
        # 브라우저 리소스 정리
        if hasattr(crawler, 'browser_manager'):
            crawler.browser_manager.close_all()


def main():
    """메인 테스트 함수"""
    print("🚀 네이버 부동산 크롤러 테스트 시작\n")

    # 법정동 데이터 테스트
    complexes = test_fetch_dong_data()

    if complexes:
        print(f"\n📊 발견된 단지 중 첫 번째 단지로 매물 테스트...")
        first_complex_id = complexes[0].get('complex_id')
        if first_complex_id:
            listings = test_fetch_complex_listings()

    print("\n✅ 테스트 완료")


if __name__ == "__main__":
    main()