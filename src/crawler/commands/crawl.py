"""부동산 크롤링 통합 CLI

모든 크롤링 기능을 하나의 CLI 명령으로 통합합니다.
"""

import argparse
from pathlib import Path

from crawler.commands.asil_naver_listing_crawl import crawl_asil_to_naver_listings
from crawler.commands.cli_common import (
    add_all_argument,
    add_output_argument,
    resolve_dong_codes,
)


def create_asil_naver_subparser(subparsers) -> argparse.ArgumentParser:
    """asil-naver 서브커맨드 파서 생성

    Args:
        subparsers: 서브파서 객체

    Returns:
        생성된 파서
    """
    parser = subparsers.add_parser(
        "asil-naver",
        help="ASIL→Naver 매물 크롤링",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "ASIL에서 법정동별 아파트 목록을 추출하고, 각 아파트를 "
            "Naver Cluster API로 매칭한 후, 매칭된 아파트 주변의 네이버 매물을 크롤링합니다."
        ),
    )
    add_all_argument(parser)
    add_output_argument(
        parser,
        default="output/asil_naver_listings.csv",
        help="출력 CSV 경로 (기본값: output/asil_naver_listings.csv)",
    )
    parser.add_argument(
        "--radius",
        type=int,
        default=500,
        help="매물 검색 반경 (미터, 기본값: 500)",
    )
    return parser


def cmd_asil_naver(args: argparse.Namespace) -> None:
    """asil-naver 서브커맨드 실행

    Args:
        args: 파싱된 인자
    """
    dong_codes = resolve_dong_codes(args, has_all_flag=True)
    output_path = Path(args.output)

    crawl_asil_to_naver_listings(
        dong_codes=dong_codes,
        output_path=output_path,
        radius_m=args.radius,
    )


def main() -> None:
    """메인 진입점"""
    parser = argparse.ArgumentParser(
        description="부동산 크롤링 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "사용 예시:\n"
            "  %(prog)s asil-naver --dong-code 1150010100 --radius 300\n"
            "  %(prog)s asil-naver --all\n"
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        help="크롤링 명령",
        metavar="<command>",
    )

    # 서브커맨드 등록
    create_asil_naver_subparser(subparsers)

    # 공통 인자 추가 (모든 서브커맨드에 적용)
    for subparser in subparsers.choices.values():
        subparser.add_argument(
            "--dong-code",
            action="append",
            dest="dong_code",
            help="법정동 코드 (예: 1150010100). 여러 번 사용 가능.",
        )

    args = parser.parse_args()

    # 서브커맨드별 실행
    if args.command == "asil-naver":
        cmd_asil_naver(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
