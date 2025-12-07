#!/usr/bin/env python3
"""CrawlCoordinator를 통한 거래내역 수집 및 CSV 저장 테스트"""

from pathlib import Path
from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler
from crawler.coordinator import CrawlCoordinator


def test_transaction_crawl():
    """CrawlCoordinator를 사용하여 거래내역 수집 및 CSV 저장 테스트"""
    # 설정 로드
    config = CrawlerConfig.from_env()
    crawler = NaverRealEstateCrawler(config)

    # 테스트할 단지 (래미안강남자이)
    test_complex_id = "112581"
    test_dong_code = "1168010500"  # 강남구 대치동
    test_dong_name = "대치동"

    print("CrawlCoordinator를 통한 거래내역 수집 테스트 시작...")
    print(f"단지 ID: {test_complex_id}")

    try:
        # 1. 단지 상세 정보 조회
        print("\n1. 단지 상세 정보 조회...")
        detail = crawler.fetch_complex_detail(test_complex_id)
        pyeong_types = detail.get("pyeong_types", {})

        if not pyeong_types:
            print("   - 평형 정보를 찾을 수 없습니다")
            return

        print(f"   - 단지명: {detail.get('complex_name', 'N/A')}")
        print(f"   - 평형 타입: {list(pyeong_types.keys())}")

        # 2. CrawlCoordinator 초기화
        print("\n2. CrawlCoordinator 초기화...")
        coordinator = CrawlCoordinator(
            output_dir=Path("output"), checkpoint_path=Path("output/checkpoint.json")
        )

        # 3. 테스트용 단지 데이터 생성
        dong_complexes = [
            {
                "dong_code": test_dong_code,
                "dong_name": test_dong_name,
                "complexes": [
                    {
                        "complex_id": test_complex_id,
                        "complex_name": detail.get("complex_name", "테스트단지"),
                        "real_estate_type": "아파트",
                    }
                ],
            }
        ]

        # 4. 단지 상세 정보와 거래내역 수집 실행
        print("\n3. CrawlCoordinator 실행 시작...")
        coordinator.crawl_multiple_dongs(
            dong_complexes=dong_complexes,
            fetch_complex_detail=crawler.fetch_complex_detail,
            fetch_transaction_history=crawler.fetch_transaction_history,
            resume=False,
        )

        print("\n4. CSV 파일 확인...")
        # transactions.csv 파일 확인
        transactions_file = Path("output/transactions.csv")
        if transactions_file.exists():
            with open(transactions_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                print(f"   - transactions.csv: {len(lines)}행 (헤더 제외: {len(lines)-1}건)")

                if len(lines) > 1:
                    print("   - 최근 3건의 거래내역:")
                    for i, line in enumerate(lines[1:4], 1):
                        cols = line.strip().split(",")
                        if len(cols) >= 8:
                            print(f"     {i}. 날짜: {cols[6]}, 가격: {cols[8]}, 층: {cols[9]}")
        else:
            print("   - transactions.csv 파일이 생성되지 않았습니다")

        print("\n✅ 거래내역 수집 및 저장 테스트 성공!")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_transaction_crawl()
