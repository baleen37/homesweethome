import argparse
from pathlib import Path

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler


def main() -> None:
    parser = argparse.ArgumentParser(description="HomeSweetHome Crawler - 네이버 부동산")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="출력 파일 경로 (기본: output/seoul_apartments_{timestamp}.csv)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="중단된 지점부터 재개",
    )
    parser.add_argument(
        "--district",
        type=str,
        default=None,
        help="크롤링할 구 이름 (예: 강남구). 쉼표로 구분하여 여러 구 지정 가능",
    )

    args = parser.parse_args()

    # district_filter 처리
    district_filter = None
    if args.district:
        # 쉼표로 구분된 문자열을 리스트로 변환
        district_filter = [d.strip() for d in args.district.split(",") if d.strip()]

    # 출력 파일명 생성
    output_file = None
    if args.output is not None:
        output_file = str(args.output)

    try:
        config = CrawlerConfig.from_env(output_file=output_file)
    except ValueError as e:
        print(f"설정 오류: {e}")
        exit(1)

    print("네이버 부동산 크롤링 시작...")
    if args.resume:
        print("체크포인트에서 재개합니다.")
    if district_filter:
        print(f"대상 구: {', '.join(district_filter)}")

    crawler = NaverRealEstateCrawler(config)

    try:
        stats = crawler.crawl(district_filter=district_filter)
    except ValueError as e:
        print(f"\n오류: {e}")
        print("\n사용 가능한 구 목록을 확인하려면 다음 명령을 실행하세요:")
        print(
            "python -c \"from crawler.crawlers.naver import NaverRealEstateCrawler; from crawler.config import CrawlerConfig; c = NaverRealEstateCrawler(CrawlerConfig.from_env()); districts = [d['district_name'] for d in c.districts_data['districts']]; print(', '.join(sorted(districts)))\""
        )
        exit(1)
    except RuntimeError as e:
        print(f"\n크롤링 실패: {e}")
        exit(1)

    # 결과 출력 (CSV는 CrawlCoordinator에서 이미 저장됨)
    print("\n크롤링 완료!")
    print(f"  - 처리된 동: {stats['dongs_processed']}/{stats['total_dongs']}")
    print(f"  - 처리된 단지: {stats['total_complexes_processed']}/{stats['total_complexes']}")
    print(f"  - 수집된 거래내역: {stats['total_transactions_collected']}건")
    print(f"  - 소요 시간: {stats['duration_seconds']:.1f}초")
    print("\n결과 파일:")
    print("  - 거래내역: output/transactions.csv")
    print("  - 단지 정보: output/complexes.csv")

    # 실패 리포트
    failed = crawler.checkpoint_manager.checkpoint.get("failed_dongs", [])
    if failed:
        print(f"\n실패한 동: {len(failed)}개")
        for fail in failed[:5]:  # 최대 5개만 출력
            # 다양한 데이터 형식을 지원하도록 안전한 처리
            dong_name = fail.get("dong_name", fail.get("name", "알 수 없음"))
            dong_code = fail.get("dong_code", fail.get("cortarNo", fail.get("code", "알 수 없음")))
            error = fail.get("error", "알 수 없는 오류")
            print(f"  - {dong_name} ({dong_code}): {error}")


if __name__ == "__main__":
    main()
