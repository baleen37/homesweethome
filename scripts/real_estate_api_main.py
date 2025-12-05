#!/usr/bin/env python3
"""
공공데이터 API 기반 부동산 정보 크롤링 스크립트
"""

import argparse
import sys
from pathlib import Path
from typing import NoReturn

import structlog

# src 디렉토리를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crawler.config import CrawlerConfig
from crawler.crawlers.real_estate_api import RealEstateAPICrawler
from crawler.writers.complexes_csv_writer import ComplexesCSVWriter


def parse_args() -> argparse.Namespace:
    """커맨드 라인 인자 파싱"""
    parser = argparse.ArgumentParser(description="공공데이터 API 기반 부동산 정보 크롤러")

    parser.add_argument(
        "--output",
        type=str,
        default="output/public_real_estate_data.csv",
        help="출력 CSV 파일 경로 (기본값: output/public_real_estate_data.csv)",
    )

    parser.add_argument(
        "--api-key",
        type=str,
        help="공공데이터 포털 API 인증키 (환경변수 PUBLIC_DATA_API_KEY 우선)",
    )

    parser.add_argument(
        "--region-code",
        type=str,
        help="법정동코드 (예: 11680: 서울 강남구, 11650: 서울 서초구)",
    )

    parser.add_argument(
        "--start-date",
        type=str,
        help="조회 시작일 (YYYY-MM 형식, 예: 2025-01)",
    )

    parser.add_argument(
        "--end-date",
        type=str,
        help="조회 종료일 (YYYY-MM 형식, 지정하지 않으면 시작일만 조회)",
    )

    parser.add_argument(
        "--page-size",
        type=int,
        default=1000,
        help="한 페이지당 조회 건수 (기본값: 1000, 최대: 1000)",
    )

    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    """인자 유효성 검사"""
    if args.start_date and len(args.start_date) != 7:
        raise ValueError("시작일은 YYYY-MM 형식이어야 합니다 (예: 2025-01)")

    if args.end_date and len(args.end_date) != 7:
        raise ValueError("종료일은 YYYY-MM 형식이어야 합니다 (예: 2025-01)")

    if args.page_size < 1 or args.page_size > 1000:
        raise ValueError("페이지 크기는 1에서 1000 사이여야 합니다")


def setup_config(args: argparse.Namespace) -> CrawlerConfig:
    """CrawlerConfig 설정"""
    import os

    # API 키 우선순위: CLI > 환경변수
    api_key = args.api_key or os.getenv("PUBLIC_DATA_API_KEY")

    if not api_key:
        print("경고: API 키가 설정되지 않았습니다. 실제 API 호출은 실패할 수 있습니다.")
        print("CLI --api-key 옵션을 사용하거나 PUBLIC_DATA_API_KEY 환경변수를 설정하세요.")

    return CrawlerConfig(
        api_key=api_key,
        region_code=args.region_code,
        start_date=args.start_date,
        end_date=args.end_date,
        page_size=args.page_size,
    )


def crawl_real_estate_data(config: CrawlerConfig) -> list[dict]:
    """부동산 데이터 크롤링"""
    logger = structlog.get_logger()

    logger.info(
        "starting_real_estate_crawl",
        region_code=config.region_code,
        start_date=config.start_date,
        end_date=config.end_date,
        page_size=config.page_size,
    )

    crawler = RealEstateAPICrawler(config)
    all_data = []

    try:
        # 기본적으로 한 번의 API 호출로 데이터 수집
        data = crawler.crawl()
        all_data.extend(data)

        logger.info(
            "crawl_completed",
            total_items=len(all_data),
            first_item=data[0] if data else None,
        )

    except Exception as e:
        logger.error(
            "crawl_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise

    return all_data


def save_to_csv(data: list[dict], output_path: str) -> None:
    """데이터를 CSV 파일로 저장"""
    logger = structlog.get_logger()

    if not data:
        logger.warning("no_data_to_save")
        return

    # 출력 디렉토리 생성
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # CSV 저장
    writer = ComplexesCSVWriter()
    writer.write(data, output_path)

    logger.info(
        "data_saved",
        output_path=output_path,
        item_count=len(data),
    )


def print_summary(data: list[dict], region_code: str | None) -> None:
    """크롤링 결과 요약 출력"""
    if not data:
        print("\n❌ 수집된 데이터가 없습니다.")
        return

    print(f"\n✅ 총 {len(data):,}개의 부동산 거래 데이터를 수집했습니다.")

    # 지역별 통계
    if region_code:
        region_name = get_region_name(region_code)
        print(f"\n📍 조회 지역: {region_name} (법정동코드: {region_code})")

    # 거래 유형별 통계
    trade_types = {}
    for item in data:
        trade_type = item.get("trade_type", "기타")
        trade_types[trade_type] = trade_types.get(trade_type, 0) + 1

    print("\n📊 거래 유형별 현황:")
    for trade_type, count in trade_types.items():
        print(f"  - {trade_type}: {count:,}건")

    # 평균 가격 정보
    sale_prices = [item["sale_price"] for item in data if item.get("sale_price")]
    jeonse_prices = [item["jeonse_price"] for item in data if item.get("jeonse_price")]

    if sale_prices:
        avg_sale = sum(sale_prices) / len(sale_prices)
        print(f"\n💰 매매 평균 가격: {avg_sale:,.0f}원 ({len(sale_prices)}건)")

    if jeonse_prices:
        avg_jeonse = sum(jeonse_prices) / len(jeonse_prices)
        print(f"💰 전세 평균 가격: {avg_jeonse:,.0f}원 ({len(jeonse_prices)}건)")


def get_region_name(region_code: str) -> str:
    """법정동코드를 지역명으로 변환 (일부만 지원)"""
    region_map = {
        "11680": "강남구",
        "11650": "서초구",
        "11530": "송파구",
        "11545": "강동구",
        "11560": "강북구",
        "11350": "노원구",
        "11320": "도봉구",
        "11590": "동작구",
        "11440": "마포구",
        "11410": "서대문구",
        "11140": "성동구",
        "11000": "종로구",
        "11710": "양천구",
        "11470": "영등포구",
        "11500": "용산구",
        "11620": "은평구",
        "10680": "강남구(새주소)",
        # 더 많은 지역 추가 가능
    }

    return region_map.get(region_code, f"법정동코드 {region_code}")


def main() -> NoReturn:
    """메인 함수"""
    try:
        # 인자 파싱 및 유효성 검사
        args = parse_args()
        validate_args(args)

        # 설정 구성
        config = setup_config(args)

        # 데이터 크롤링
        data = crawl_real_estate_data(config)

        # CSV 저장
        save_to_csv(data, args.output)

        # 결과 요약 출력
        print_summary(data, config.region_code)

        print(f"\n📁 데이터가 '{args.output}' 파일에 저장되었습니다.")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()