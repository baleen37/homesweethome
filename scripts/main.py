import argparse
from pathlib import Path

from crawler.config import CrawlerConfig
from crawler.crawlers.hogangnono import HogangnonoCrawler


def main() -> None:
    parser = argparse.ArgumentParser(description="HomeSweetHome Crawler - 호갱노노 부동산")
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
    parser.add_argument(
        "--regions",
        type=str,
        default=None,
        help="크롤링할 시/도 코드 (예: 11,26). 쉼표로 구분하여 여러 시/도 지정 가능",
    )
    parser.add_argument(
        "--districts",
        type=str,
        default=None,
        help="크롤링할 구/군 코드 (예: 11680,11650). 쉼표로 구분하여 여러 구/군 지정 가능. --district 인자보다 우선순위가 높음",
    )
    parser.add_argument(
        "--full-period",
        action="store_true",
        help="전체 기간 데이터 수집 (기본값: 최근 3년)",
    )

    args = parser.parse_args()

    # district_filter 처리 (--district 인자는 호환성을 위해 유지)
    district_filter = None
    if args.district:
        # 쉼표로 구분된 문자열을 리스트로 변환
        district_filter = [d.strip() for d in args.district.split(",") if d.strip()]

    # regions 처리
    regions_filter = None
    if args.regions:
        # 쉼표로 구분된 문자열을 리스트로 변환
        regions_filter = [r.strip() for r in args.regions.split(",") if r.strip()]

    # districts 처리 (--districts 인자가 --district 인자보다 우선순위 높음)
    districts_filter = None
    if args.districts:
        # 쉼표로 구분된 문자열을 리스트로 변환
        districts_filter = [d.strip() for d in args.districts.split(",") if d.strip()]
    elif district_filter:
        # --district 인자가 사용된 경우 (호환성을 위해)
        # TODO: 구 이름을 구/군 코드로 변환하는 기능 추가 필요
        print(
            "경고: --district 인자는 호환성을 위해 유지됩니다. --districts 인자 사용을 권장합니다."
        )
        print(f"요청하신 구: {', '.join(district_filter)}")
        print("--districts 인자로 구/군 코드를 직접 지정해주세요.")
        exit(1)

    # 출력 파일명 생성
    output_file = None
    if args.output is not None:
        output_file = str(args.output)

    try:
        config = CrawlerConfig.from_env(output_file=output_file)
    except ValueError as e:
        print(f"설정 오류: {e}")
        exit(1)

    print("호갱노노 부동산 크롤링 시작...")
    if args.resume:
        print("체크포인트에서 재개합니다.")
    if regions_filter:
        print(f"대상 시/도 코드: {', '.join(regions_filter)}")
    if districts_filter:
        print(f"대상 구/군 코드: {', '.join(districts_filter)}")
    if args.full_period:
        print("전체 기간 데이터 수집 모드")

    crawler = HogangnonoCrawler(config)

    try:
        stats = crawler.crawl(
            regions=regions_filter,
            districts=districts_filter,
            full_period=args.full_period,
        )
    except ValueError as e:
        print(f"\n오류: {e}")
        print("\n사용 가능한 시/도 및 구/군 코드 목록을 확인하려면 다음 명령을 실행하세요:")
        print(
            "python -c \"from crawler.crawlers.hogangnono import HogangnonoCrawler; from crawler.config import CrawlerConfig; c = HogangnonoCrawler(CrawlerConfig.from_env()); r = c.hogangnono_client.get_regions(); print('시/도 목록:'); [print(f'  {reg[\\\"regionCode\\\"]}: {reg[\\\"name\\\"]}') for reg in r.data['regionList']]; print('\\n구/군 목록:'); [print(f'  {child[\\\"regionCode\\\"]}: {child[\\\"name\\\"]}') for reg in r.data['regionList'] for child in reg['children']]\""
        )
        exit(1)
    except RuntimeError as e:
        print(f"\n크롤링 실패: {e}")
        exit(1)

    # 결과 출력
    print("\n크롤링 완료!")
    print(f"  - 처리된 구/군: {stats.get('dongs_processed', 0)}/{stats.get('total_dongs', 0)}")
    print(f"  - 소요 시간: {stats.get('duration_seconds', 0):.1f}초")
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
