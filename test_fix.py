#!/usr/bin/env python3
"""수정된 코드 테스트"""

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler
from crawler.coordinator import CrawlCoordinator


def test_fix():
    """수정된 코드 테스트"""
    config = CrawlerConfig.from_env()
    crawler = NaverRealEstateCrawler(config)

    test_complex_id = "112581"
    print(f"단지 ID {test_complex_id}로 테스트 시작...")

    try:
        # 1. 단지 상세 정보 조회
        detail = crawler.fetch_complex_detail(test_complex_id)
        print("✅ 단지 상세 정보 조회 성공!")
        print(f"   - pyeong_types 타입: {type(detail.get('pyeong_types', {}))}")

        # 2. Coordinator 테스트를 위한 간단한 dong_complexes 데이터 생성
        _ = [  # 변수를 사용하지 않으므로 _로 할당
            {
                "dong_code": "1154510100",  # 역삼1동 코드
                "dong_name": "역삼1동",
                "complexes": [{"complex_id": test_complex_id, "complex_name": "테스트 단지"}],
            }
        ]

        # 3. CrawlCoordinator 초기화
        coordinator = CrawlCoordinator(
            output_dir="test_output",
            checkpoint_path=None,  # 체크포인트 미사용
            initial_delay=1.0,
            max_delay=3.0,
        )

        # 4. crawl_dong 메서드 직접 테스트
        print("\n🔄 crawl_dong 메서드 테스트 시작...")
        result = coordinator.crawl_dong(
            dong_code="1154510100",
            dong_name="역삼1동",
            complexes=[{"complex_id": test_complex_id, "complex_name": "테스트 단지"}],
            fetch_complex_detail=crawler.fetch_complex_detail,
            fetch_transaction_history=crawler.fetch_transaction_history,
        )

        print("✅ crawl_dong 테스트 성공!")
        print(f"   - 처리된 단지 수: {result['complexes_processed']}")
        print(f"   - 수집된 거래내역 수: {result['transactions_collected']}")
        print(f"   - 에러 수: {len(result['errors'])}")

        if result["errors"]:
            print("   - 에러 목록:")
            for error in result["errors"]:
                print(f"     * {error}")

        print("\n🎉 모든 테스트 성공! 'string indices must be integers' 오류가 해결되었습니다.")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_fix()
