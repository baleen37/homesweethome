"""
크롤링 데이터 검증 실행 스크립트

다양한 시나리오로 Playwright를 사용한 데이터 검증을 실행합니다.
"""

import asyncio
import sys
from pathlib import Path

# src 디렉토리를 Python path에 추가
sys.path.append(str(Path(__file__).parent / "src"))

from test_playwright_verification import PlaywrightDataVerifier
import structlog

logger = structlog.get_logger().bind(component="VerificationRunner")


async def run_region_verification(csv_path: str, region: str, sample_size: int = 10):
    """특정 지역 데이터 검증"""
    print(f"\n{'=' * 60}")
    print(f"{region} 지역 데이터 검증 시작")
    print(f"{'=' * 60}")

    verifier = PlaywrightDataVerifier(csv_path, f"verification_reports/{region}")
    report = await verifier.verify_sample_data(sample_size, region)
    verifier.save_report(report)

    print(f"\n{region} 지역 검증 결과:")
    print(f"- 총 비교 수: {report.total_comparisons}")
    print(f"- 일치 데이터: {report.matched_count}")
    print(f"- 전체 정확도: {report.overall_accuracy:.1f}%")
    print(f"- 보고서: verification_reports/{region}/")

    return report


async def run_random_sampling(csv_path: str, sample_sizes: list = [5, 10, 20]):
    """랜덤 샘플링 검증"""
    print(f"\n{'=' * 60}")
    print("랜덤 샘플링 검증 시작")
    print(f"{'=' * 60}")

    results = []

    for size in sample_sizes:
        print(f"\n샘플링 크기: {size}")
        verifier = PlaywrightDataVerifier(csv_path, f"verification_reports/random_sampling_{size}")
        report = await verifier.verify_sample_data(size, None)  # 지역 필터링 없음
        verifier.save_report(report)
        results.append((size, report))

        print(f"- 정확도: {report.overall_accuracy:.1f}%")

    # 샘플링 크기별 정확도 요약
    print(f"\n{'=' * 60}")
    print("샘플링 크기별 정확도 요약")
    print(f"{'=' * 60}")
    print("샘플링 크기 | 정확도")
    print("-" * 30)
    for size, report in results:
        print(f"{size:10d} | {report.overall_accuracy:6.1f}%")

    return results


async def run_comprehensive_verification(csv_path: str):
    """종합 검증 - 여러 시나리오 실행"""
    print("\n" + "=" * 60)
    print("크롤링 데이터 종합 검증 시작")
    print("=" * 60)

    # 1. 주요 지역 검증
    regions = [("종로구", 10), ("강남구", 10), ("서초구", 8), ("마포구", 8)]

    region_results = []
    for region, sample_size in regions:
        try:
            report = await run_region_verification(csv_path, region, sample_size)
            region_results.append((region, report))
        except Exception as e:
            logger.error(f"{region} 지역 검증 실패", error=str(e))
            region_results.append((region, None))

    # 2. 랜덤 샘플링 검증
    print(f"\n{'=' * 60}")
    random_results = await run_random_sampling(csv_path, [10, 15])

    # 3. 종합 보고서 생성
    await generate_comprehensive_report(region_results, random_results)


async def generate_comprehensive_report(region_results, random_results):
    """종합 보고서 생성"""
    from datetime import datetime
    import json

    report_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "region_verification": {},
        "random_sampling": {},
        "summary": {
            "total_regions_tested": len([r for r in region_results if r[1] is not None]),
            "avg_region_accuracy": 0,
            "best_region": "",
            "worst_region": "",
            "avg_random_accuracy": 0,
        },
    }

    # 지역별 결과 정리
    accuracies = []
    for region, report in region_results:
        if report:
            report_data["region_verification"][region] = {
                "accuracy": report.overall_accuracy,
                "total_comparisons": report.total_comparisons,
                "matched_count": report.matched_count,
            }
            accuracies.append(report.overall_accuracy)

    if accuracies:
        report_data["summary"]["avg_region_accuracy"] = sum(accuracies) / len(accuracies)
        best_region = max(region_results, key=lambda x: x[1].overall_accuracy if x[1] else 0)
        worst_region = min(region_results, key=lambda x: x[1].overall_accuracy if x[1] else 0)
        report_data["summary"]["best_region"] = best_region[0]
        report_data["summary"]["worst_region"] = worst_region[0]

    # 랜덤 샘플링 결과 정리
    for size, report in random_results:
        report_data["random_sampling"][f"sample_{size}"] = {
            "accuracy": report.overall_accuracy,
            "total_comparisons": report.total_comparisons,
        }

    random_accuracies = [report.overall_accuracy for _, report in random_results]
    if random_accuracies:
        report_data["summary"]["avg_random_accuracy"] = sum(random_accuracies) / len(
            random_accuracies
        )

    # 종합 보고서 저장
    output_dir = Path("verification_reports")
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(
        output_dir / f"comprehensive_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    # 종합 결과 출력
    print(f"\n{'=' * 60}")
    print("종합 검증 결과 요약")
    print("=" * 60)
    print(f"1. 지역별 평균 정확도: {report_data['summary']['avg_region_accuracy']:.1f}%")
    print(f"2. 가장 정확한 지역: {report_data['summary']['best_region']}")
    print(f"3. 가장 부정확한 지역: {report_data['summary']['worst_region']}")
    print(f"4. 랜덤 샘플링 평균 정확도: {report_data['summary']['avg_random_accuracy']:.1f}%")


async def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="크롤링 데이터 검증 실행")
    parser.add_argument("--csv-path", required=True, help="검증할 CSV 파일 경로")
    parser.add_argument(
        "--mode",
        choices=["region", "random", "comprehensive"],
        default="comprehensive",
        help="검증 모드",
    )
    parser.add_argument("--region", help="검증할 지역 (region 모드일 때)")
    parser.add_argument("--sample-size", type=int, default=10, help="샘플 크기")

    args = parser.parse_args()

    # CSV 파일 존재 확인
    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        print(f"오류: CSV 파일을 찾을 수 없습니다 - {csv_path}")
        sys.exit(1)

    try:
        if args.mode == "region":
            if not args.region:
                print("오류: region 모드에는 --region 인자가 필요합니다.")
                sys.exit(1)
            await run_region_verification(args.csv_path, args.region, args.sample_size)

        elif args.mode == "random":
            await run_random_sampling(args.csv_path, [args.sample_size])

        else:  # comprehensive
            await run_comprehensive_verification(args.csv_path)

        print("\n검증 완료!")

    except Exception as e:
        logger.error("검증 실행 중 오류 발생", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
