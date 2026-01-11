"""CLI 공통 유틸리티"""

import argparse

from crawler.constants.legal_dong_codes import SEOUL_LEGAL_DONG_CODES


def create_dong_code_parser(description: str) -> argparse.ArgumentParser:
    """동 코드 인자를 포함한 CLI 파서 생성

    Args:
        description: CLI 설명

    Returns:
        ArgumentParser 인스턴스
    """
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--dong-code",
        action="append",
        dest="dong_code",
        help="법정동 코드 (예: 1150010100). 여러 번 사용 가능.",
    )

    return parser


def add_all_argument(parser: argparse.ArgumentParser) -> None:
    """--all 인자 추가

    Args:
        parser: ArgumentParser 인스턴스
    """
    parser.add_argument(
        "--all",
        action="store_true",
        help="서울 전체 법정동 크롤링",
    )


def add_output_argument(
    parser: argparse.ArgumentParser,
    default: str,
    help: str,
) -> None:
    """--output 인자 추가

    Args:
        parser: ArgumentParser 인스턴스
        default: 기본값
        help: 도움말
    """
    parser.add_argument(
        "--output",
        type=str,
        default=default,
        help=help,
    )


def resolve_dong_codes(args: argparse.Namespace, has_all_flag: bool = True) -> list[str]:
    """인자로부터 동 코드 리스트 결정

    Args:
        args: 파싱된 인자
        has_all_flag: --all 플래그 지원 여부

    Returns:
        동 코드 리스트
    """
    if has_all_flag and getattr(args, "all", False):
        return list(SEOUL_LEGAL_DONG_CODES.keys())
    elif args.dong_code:
        return args.dong_code
    else:
        # 기본값: 5개 샘플 동
        return list(SEOUL_LEGAL_DONG_CODES.keys())[:5]
