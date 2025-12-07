#!/usr/bin/env python3
"""호갱노노 부동산 데이터 크롤링 스크립트

HogangnonoCrawler를 사용하여 부동산 데이터를 수집합니다.
"""

import argparse
from typing import Optional, Tuple

import structlog

from crawler.config import CrawlerConfig
from crawler.crawlers.hogangnono import HogangnonoCrawler


def parse_bounds(bounds_str: str) -> Tuple[float, float, float, float]:
    """경계 좌표 문자열을 파싱

    Args:
        bounds_str: "lat_min,lng_min,lat_max,lng_max" 형태의 문자열

    Returns:
        튜플 형태의 경계 좌표
    """
    try:
        parts = bounds_str.split(",")
        if len(parts) != 4:
            raise ValueError("경계 좌표는 4개 값이 필요합니다")

        return tuple(float(p.strip()) for p in parts)
    except Exception:
        raise ValueError(f"잘못된 경계 좌표 형식: {bounds_str}")


def main() -> None:
    """메인 함수"""
    parser = argparse.ArgumentParser(description="호갱노노 부동산 데이터 크롤러")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="output",
        help="출력 디렉토리 (기본값: output)",
    )
    parser.add_argument(
        "--bounds",
        "-b",
        type=str,
        help="경계 좌표 (lat_min,lng_min,lat_max,lng_max)",
    )
    parser.add_argument(
        "--apt-type",
        type=str,
        default="apart",
        choices=["apart", "officetel", "house"],
        help="매물 타입 (기본값: apart)",
    )
    parser.add_argument(
        "--trade-type",
        type=str,
        choices=["sale", "jeonse", "monthly"],
        help="거래 타입",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=10,
        help="최대 페이지 수 (기본값: 10)",
    )
    parser.add_argument(
        "--district",
        type=str,
        help="크롤링할 구 이름 (콤마로 여러 개 지정 가능)",
    )

    args = parser.parse_args()

    # 로깅 설정
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logger = structlog.get_logger()

    try:
        # 설정 로드
        config = CrawlerConfig.from_env()
        logger.info("config_loaded", config=config)

        # 경계 좌표 처리
        region_bounds: Optional[Tuple[float, float, float, float]] = None
        if args.bounds:
            region_bounds = parse_bounds(args.bounds)
        elif args.district:
            # TODO: 구 이름을 좌표로 변환하는 로직 추가
            logger.warning("district_to_bounds_conversion_not_implemented")
            region_bounds = None

        # 크롤러 생성
        crawler = HogangnonoCrawler(
            config=config,
            output_dir=args.output,
            region_bounds=region_bounds,
        )

        # 크롤링 실행
        logger.info(
            "starting_crawl",
            output_dir=args.output,
            apt_type=args.apt_type,
            trade_type=args.trade_type,
            max_pages=args.max_pages,
        )

        crawler.crawl_and_save(
            region_bounds=region_bounds,
            apt_type=args.apt_type,
            trade_type=args.trade_type,
            max_pages=args.max_pages,
        )

        logger.info("crawl_completed_successfully")

    except Exception as e:
        logger.error(
            "crawl_failed",
            error=str(e),
            exc_info=True,
        )
        raise


if __name__ == "__main__":
    main()
