"""부동산 크롤링 통합 CLI

모든 크롤링 기능을 하나의 CLI 명령으로 통합합니다.
"""

import argparse
from pathlib import Path

from crawler.commands.apt_and_trade_crawl import crawl_apt_and_trade
from crawler.commands.apt_list_crawl import crawl_apt_list_to_csv
from crawler.commands.asil_naver_listing_crawl import crawl_asil_to_naver_listings
from crawler.commands.cli_common import (
    add_all_argument,
    add_output_argument,
    resolve_dong_codes,
)


def create_apt_list_subparser(subparsers) -> argparse.ArgumentParser:
    """apt-list 서브커맨드 파서 생성

    Args:
        subparsers: 서브파서 객체

    Returns:
        생성된 파서
    """
    parser = subparsers.add_parser(
        "apt-list",
        help="ASIL 아파트 목록 크롤링",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="ASIL에서 법정동별 아파트 목록을 크롤링합니다.",
    )
    add_all_argument(parser)
    add_output_argument(
        parser,
        default="output/apt_list.csv",
        help="출력 CSV 경로 (기본값: output/apt_list.csv)",
    )
    return parser


def create_apt_trade_subparser(subparsers) -> argparse.ArgumentParser:
    """apt-trade 서브커맨드 파서 생성

    Args:
        subparsers: 서브파서 객체

    Returns:
        생성된 파서
    """
    parser = subparsers.add_parser(
        "apt-trade",
        help="아파트 기본정보 + 실거래가 크롤링",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="아파트 기본정보와 실거래가를 각각 별도 CSV로 크롤링합니다.",
    )
    add_output_argument(
        parser,
        default="output",
        help="출력 디렉토리 (기본값: output)",
    )
    return parser


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


def cmd_apt_list(args: argparse.Namespace) -> None:
    """apt-list 서브커맨드 실행

    Args:
        args: 파싱된 인자
    """
    dong_codes = resolve_dong_codes(args, has_all_flag=True)
    output_path = Path(args.output)

    crawl_apt_list_to_csv(
        dong_codes=dong_codes,
        output_path=output_path,
    )


def cmd_apt_trade(args: argparse.Namespace) -> None:
    """apt-trade 서브커맨드 실행

    Args:
        args: 파싱된 인자
    """
    dong_codes = resolve_dong_codes(args, has_all_flag=False)

    output_dir = Path(args.output)
    apt_output_path = output_dir / "apt_list.csv"
    trade_output_path = output_dir / "trade_price.csv"

    crawl_apt_and_trade(
        dong_codes=dong_codes,
        apt_output_path=apt_output_path,
        trade_output_path=trade_output_path,
    )


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
            "  %(prog)s apt-list --dong-code 1150010100\n"
            "  %(prog)s apt-list --all\n"
            "  %(prog)s apt-trade --dong-code 1150010100 --output output/data\n"
            "  %(prog)s asil-naver --dong-code 1150010100 --radius 300\n"
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        help="크롤링 명령",
        metavar="<command>",
    )

    # 서브커맨드 등록
    create_apt_list_subparser(subparsers)
    create_apt_trade_subparser(subparsers)
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
    if args.command == "apt-list":
        cmd_apt_list(args)
    elif args.command == "apt-trade":
        cmd_apt_trade(args)
    elif args.command == "asil-naver":
        cmd_asil_naver(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
