#!/usr/bin/env python
"""단지 상세 정보 조회 테스트"""

import json
import sys
from pathlib import Path

# src 디렉토리를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crawler.crawlers.naver import NaverRealEstateCrawler
from crawler.config import CrawlerConfig


def test_fetch_complex_detail():
    """fetch_complex_detail() 메서드 테스트"""
    # 테스트용 헬리오시티 단지 ID (111515)
    test_complex_id = "111515"

    print(f"테스트 단지 ID: {test_complex_id} (헬리오시티)")
    print("-" * 50)

    # 크롤러 초기화
    config = CrawlerConfig()
    crawler = NaverRealEstateCrawler(config)

    try:
        # 단지 상세 정보 조회
        detail = crawler.fetch_complex_detail(test_complex_id)

        # 결과 출력
        print("\n=== 단지 상세 정보 ===")
        print(f"단지 ID: {detail.get('complex_id', 'N/A')}")
        print(f"조회 시각: {detail.get('fetched_at', 'N/A')}")

        # 평형 정보
        if 'pyeong_types' in detail:
            print(f"\n평형 정보 ({len(detail['pyeong_types'])}개):")
            for i, pyeong in enumerate(detail['pyeong_types'][:3], 1):  # 앞 3개만 출력
                print(f"  {i}. {pyeong.get('pyeong_name', 'N/A')} - "
                      f"전용 {pyeong.get('exclusive_area', 'N/A')}㎡ "
                      f"({pyeong.get('room_count', 'N/A')}개방)")
            if len(detail['pyeong_types']) > 3:
                print(f"  ... 외 {len(detail['pyeong_types']) - 3}개 평형")

        # 보유세 정보
        if 'holding_tax' in detail:
            tax = detail['holding_tax']
            print("\n보유세 정보:")
            print(f"  재산세: {tax.get('property_tax', 'N/A'):,}원")
            print(f"  종부세: {tax.get('comprehensive_real_estate_tax', 'N/A'):,}원")
            print(f"  총 보유세: {tax.get('total_tax', 'N/A'):,}원")
            print(f"  과세 기준년도: {tax.get('tax_base_year', 'N/A')}")

        # 공시가격 정보
        if 'declared_value' in detail:
            declared = detail['declared_value']
            print("\n공시가격 정보:")
            print(f"  공시가격: {declared.get('declared_price', 'N/A'):,}원")
            print(f"  평당 공시가격: {declared.get('declared_price_per_pyeong', 'N/A'):,}원")
            print(f"  기준년도: {declared.get('declared_year', 'N/A')}")

        # 최근 시세 정보
        if 'recent_market_price' in detail:
            market = detail['recent_market_price']
            print("\n최근 시세:")
            print(f"  최근 시세: {market.get('recent_price', 'N/A'):,}원")
            print(f"  변동률: {market.get('price_change_rate', 'N/A'):.2f}%")
            print(f"  제공처: {market.get('source', 'N/A')}")
            print(f"  업데이트: {market.get('updated_date', 'N/A')}")

        # 에러 확인
        if 'error' in detail:
            print(f"\n에러 발생: {detail['error']}")

        # 전체 결과 저장
        output_path = Path(__file__).parent / "test_complex_detail_output.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(detail, f, ensure_ascii=False, indent=2)
        print(f"\n전체 결과가 {output_path}에 저장되었습니다.")

        return True

    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 브라우저 정리
        if hasattr(crawler, 'page') and crawler.page:
            try:
                crawler.page.close()
            except Exception:
                pass


if __name__ == "__main__":
    success = test_fetch_complex_detail()
    if success:
        print("\n✅ 테스트 성공!")
    else:
        print("\n❌ 테스트 실패!")
        sys.exit(1)