"""
개선된 호갱노노 크롤러 실행 스크립트

의존성 주입과 환경별 설정을 지원하는 개선된 버전의 크롤러를 실행합니다.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

# 프로젝트 루트를 시스템 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crawler.factories import create_crawler


def setup_logging(log_level: str = "INFO"):
    """로깅 설정"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("output/crawler.log", encoding="utf-8"),
        ],
    )


def parse_arguments():
    """커맨드 라인 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="개선된 호갱노노 부동산 크롤러",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 기본 실행
  python scripts/main_improved.py

  # 특정 구만 크롤링
  python scripts/main_improved.py --district 강남구,서초구

  # 전체 기간 데이터 수집
  python scripts/main_improved.py --full-period

  # 출력 디렉토리 지정
  python scripts/main_improved.py --output results/20251212

  # 체크포인트에서 재개
  python scripts/main_improved.py --resume

  # 디버그 모드
  python scripts/main_improved.py --log-level DEBUG
        """,
    )

    # 환경별 설정이 제거되었으므로 --env 옵션 제거

    parser.add_argument(
        "--district", type=str, help="크롤링할 구 목록 (쉼표로 구분, 예: 강남구,서초구)"
    )

    parser.add_argument("--region", type=str, help="크롤링할 시/도 목록 (쉼표로 구분, 예: 11,41)")

    parser.add_argument(
        "--output", type=str, default="output", help="출력 디렉토리 (기본값: output)"
    )

    parser.add_argument("--config", type=str, help="설정 파일 경로 (YAML 또는 JSON)")

    parser.add_argument(
        "--full-period", action="store_true", help="전체 기간 데이터 수집 (시간 소요 많음)"
    )

    parser.add_argument("--resume", action="store_true", help="체크포인트에서 재개")

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="로그 레벨 (기본값: INFO)",
    )

    parser.add_argument("--workers", type=int, help="병렬 처리 worker 수 (설정 파일 오버라이드)")

    parser.add_argument("--rate-limit", type=float, help="API 호출 간격 (초, 설정 파일 오버라이드)")

    parser.add_argument("--batch-size", type=int, help="배치 처리 크기 (설정 파일 오버라이드)")

    parser.add_argument(
        "--bounds", type=str, help="크롤링 영역 좌표 (lat_min,lng_min,lat_max,lng_max)"
    )

    parser.add_argument("--dry-run", action="store_true", help="실제 크롤링 없이 설정만 확인")

    parser.add_argument("--show-stats", action="store_true", help="완료 후 통계 정보 표시")

    return parser.parse_args()


def parse_bounds(bounds_str: Optional[str]) -> Optional[tuple]:
    """영역 좌표 파싱"""
    if not bounds_str:
        return None

    try:
        parts = [float(x.strip()) for x in bounds_str.split(",")]
        if len(parts) != 4:
            raise ValueError("4개의 좌표가 필요합니다")
        return tuple(parts)
    except ValueError as e:
        raise ValueError(f"잘못된 좌표 형식: {e}")


def main():
    """메인 실행 함수"""
    args = parse_arguments()

    # 로깅 설정
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    # 출력 디렉토리 생성
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 설정 로드
        config_overrides = {}

        # 인자로부터 설정 오버라이드
        if args.workers:
            config_overrides["max_workers"] = args.workers
        if args.rate_limit:
            config_overrides["rate_limit_delay"] = args.rate_limit
        if args.batch_size:
            config_overrides["batch_size"] = args.batch_size

        # 영역 좌표 파싱
        region_bounds = parse_bounds(args.bounds)

        # 크롤러 생성
        crawler = create_crawler(
            output_dir=output_dir,
            region_bounds=region_bounds,
            **config_overrides,
        )

        # Dry run 모드
        if args.dry_run:
            logger.info("Dry run 모드 - 설정 확인만 수행합니다")
            config = crawler.deps.config
            logger.info("환경: 고정된 설정 사용")
            logger.info(f"출력 디렉토리: {output_dir}")
            logger.info(f"Rate Limit: {config.RATE_LIMIT_DELAY}초")
            logger.info(f"Max Workers: {config.MAX_WORKERS}")
            logger.info(f"Batch Size: {getattr(config, 'batch_size', 'N/A')}")
            logger.info(f"Region Bounds: {region_bounds or '기본값'}")
            return

        # 크롤링 파라미터 준비
        crawl_params = {"full_period": args.full_period}

        # 구 목록 파싱
        if args.district:
            crawl_params["districts"] = [d.strip() for d in args.district.split(",")]
            logger.info(f"대상 구: {crawl_params['districts']}")

        # 시/도 목록 파싱
        if args.region:
            crawl_params["regions"] = [r.strip() for r in args.region.split(",")]
            logger.info(f"대상 시/도: {crawl_params['regions']}")

        # 체크포인트 확인
        if args.resume:
            logger.info("체크포인트에서 재개합니다")
            completed = crawler.deps.checkpoint_manager.get_completed_districts()
            logger.info(f"이미 완료된 구/군: {len(completed)}개")

        # 크롤링 시작
        logger.info("크롤링을 시작합니다...")
        logger.info("환경: 고정된 설정 사용")
        logger.info(f"출력 디렉토리: {output_dir}")

        # 크롤링 실행
        stats = crawler.crawl_and_save(**crawl_params)

        # 결과 출력
        logger.info("크롤링이 완료되었습니다!")
        logger.info(f"처리된 구/군: {stats['districts_completed']}/{stats['districts_total']}")
        logger.info(f"발견된 아파트: {stats['apartments_found']}")
        logger.info(f"처리된 아파트: {stats['apartments_processed']}")
        logger.info(f"발견된 거래내역: {stats['transactions_found']}")
        logger.info(f"에러 수: {stats['errors']}")
        logger.info(f"소요 시간: {stats.get('duration_seconds', 0):.2f}초")

        # 상세 통계
        if args.show_stats:
            print("\n" + "=" * 50)
            print("상세 통계")
            print("=" * 50)

            # 성능 통계
            perf_stats = stats.get("requests_stats", {})
            if perf_stats:
                print("\n[성능]")
                print(f"총 요청: {perf_stats.get('total_requests', 0)}")
                print(f"성공 요청: {perf_stats.get('successful_requests', 0)}")
                print(f"실패 요청: {perf_stats.get('failed_requests', 0)}")
                print(f"스킵된 아파트: {perf_stats.get('skipped_apartments', 0)}")
                print(f"캐시된 요청: {perf_stats.get('cached_requests', 0)}")

            # 에러 통계
            error_stats = stats.get("error_handler_stats", {})
            if error_stats and "error_statistics" in error_stats:
                print("\n[에러]")
                err_stat = error_stats["error_statistics"]
                print(f"에러율: {err_stat.get('error_rate', 0):.2%}")
                common_errors = err_stat.get("common_errors", [])
                if common_errors:
                    print("주요 에러:")
                    for error_type, count in common_errors[:5]:
                        print(f"  - {error_type}: {count}")

            # 캐시 통계
            cache_stats = stats.get("cache_stats", {})
            if cache_stats:
                print("\n[캐시]")
                print(f"아파트 캐시: {cache_stats.get('apartment_cache_size', 0)}개")
                print(f"동 코드 캐시: {cache_stats.get('dong_code_cache_size', 0)}개")

        # 에러 추천사항
        error_stats = stats.get("error_handler_stats", {})
        if error_stats and "recommendations" in error_stats:
            recommendations = error_stats["recommendations"]
            if recommendations:
                print("\n[추천사항]")
                for rec in recommendations:
                    print(f"- {rec}")

    except KeyboardInterrupt:
        logger.info("\n사용자가 중단했습니다")
        sys.exit(1)
    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
