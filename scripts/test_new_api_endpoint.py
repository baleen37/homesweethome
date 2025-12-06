#!/usr/bin/env python3
"""
신버전 API 엔드포인트 테스트 스크립트
서울 종로구 데이터를 조회하여 신버전 API가 정상 작동하는지 확인
"""

import os
import sys
from pathlib import Path

import structlog

# src 디렉토리를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crawler.config import CrawlerConfig
from crawler.crawlers.real_estate_api import RealEstateAPICrawler


def main() -> None:
    """메인 함수"""
    logger = structlog.get_logger()

    # API 키 확인
    api_key = os.getenv("PUBLIC_DATA_API_KEY")

    if not api_key:
        print("=" * 80)
        print("⚠️  API 키가 설정되지 않았습니다.")
        print("=" * 80)
        print()
        print("실제 API 호출을 위해서는 다음 중 하나를 수행해야 합니다:")
        print()
        print("1. .env 파일에 PUBLIC_DATA_API_KEY 추가:")
        print("   PUBLIC_DATA_API_KEY=your_api_key_here")
        print()
        print("2. 환경 변수로 설정:")
        print("   export PUBLIC_DATA_API_KEY=your_api_key_here")
        print()
        print("공공데이터 포털(https://www.data.go.kr)에서 API 키를 발급받을 수 있습니다.")
        print("API 서비스: '국토교통부 아파트매매 신고 조회 서비스'")
        print("=" * 80)
        sys.exit(1)

    # 설정 생성 (서울 종로구, 현재 월)
    config = CrawlerConfig(
        api_key=api_key,
        region_code="11110",  # 서울 종로구
        start_date="2025-01",
    )

    # 크롤러 생성
    crawler = RealEstateAPICrawler(config)

    print("=" * 80)
    print("🔍 신버전 API 엔드포인트 테스트")
    print("=" * 80)
    print(f"엔드포인트: {crawler.base_url}")
    print(f"조회 지역: 서울 종로구 (11110)")
    print(f"조회 기간: 2025-01")
    print("=" * 80)
    print()

    try:
        # URL 생성
        url = crawler.get_url()
        logger.info("generated_url", url=url)
        print(f"✅ URL 생성 성공")
        print(f"   URL: {url}")
        print()

        # API 호출
        print("🌐 API 호출 중...")
        response = crawler.fetch(url)
        logger.info("fetch_success", response_length=len(response))
        print(f"✅ API 호출 성공")
        print(f"   응답 크기: {len(response):,} bytes")
        print()

        # 응답 파싱
        print("📊 응답 파싱 중...")
        items = crawler.parse(response)
        logger.info("parse_success", items_count=len(items))
        print(f"✅ 파싱 성공")
        print(f"   조회된 항목 수: {len(items):,}개")
        print()

        # 결과 샘플 출력
        if items:
            print("=" * 80)
            print("📋 첫 번째 항목 샘플:")
            print("=" * 80)
            first_item = items[0]
            print(f"  - 아파트명: {first_item.get('apartment_name', 'N/A')}")
            print(f"  - 거래유형: {first_item.get('trade_type', 'N/A')}")
            print(f"  - 거래금액: {first_item.get('sale_price', 'N/A'):,}원" if first_item.get('sale_price') else "  - 거래금액: N/A")
            print(f"  - 전용면적: {first_item.get('exclusive_area', 'N/A')}㎡")
            print(f"  - 층: {first_item.get('floor', 'N/A')}")
            print(f"  - 건축년도: {first_item.get('construct_year', 'N/A')}")
            print(f"  - 주소: {first_item.get('address', 'N/A')}")
            print("=" * 80)
            print()

            # 거래 유형별 통계
            trade_types = {}
            for item in items:
                trade_type = item.get("trade_type", "기타")
                trade_types[trade_type] = trade_types.get(trade_type, 0) + 1

            print("📊 거래 유형별 통계:")
            for trade_type, count in trade_types.items():
                print(f"  - {trade_type}: {count:,}건")
            print()
        else:
            print("⚠️  조회된 데이터가 없습니다. (해당 기간에 거래가 없었을 수 있습니다)")
            print()

        print("=" * 80)
        print("✅ 신버전 API 엔드포인트 테스트 성공!")
        print("=" * 80)

    except Exception as e:
        logger.error("test_failed", error=str(e), error_type=type(e).__name__)
        print()
        print("=" * 80)
        print("❌ 테스트 실패")
        print("=" * 80)
        print(f"오류 유형: {type(e).__name__}")
        print(f"오류 메시지: {e}")
        print()
        print("가능한 원인:")
        print("  1. API 키가 잘못되었거나 만료됨")
        print("  2. API 키 활성화가 필요함 (공공데이터 포털에서 신청 및 승인 필요)")
        print("  3. API 서비스 일시 중단")
        print("  4. 네트워크 연결 문제")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
