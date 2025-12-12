#!/usr/bin/env python
"""API 탐색 통합 실행기

호갱노노 API에서 아파트 데이터를 가져올 수 있는 방법을 탐색합니다.
"""

import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

# 프로젝트 루트에 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.crawler.api.hogangnono_client import HogangnonoAPIClient
from src.crawler.config import CrawlerConfig


def print_header(title):
    """헤더 출력"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def run_script(script_path, description):
    """스크립트 실행"""
    print_header(description)

    try:
        # 스크립트 실행
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=300,  # 5분 타임아웃
        )

        # 출력
        if result.stdout:
            print(result.stdout)

        if result.stderr:
            print("\n[오류 출력]")
            print(result.stderr)

        if result.returncode != 0:
            print(f"\n⚠️  스크립트 실행 실패 (종료 코드: {result.returncode})")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("\n⏰ 타임아웃: 스크립트 실행이 5분을 초과했습니다")
        return False
    except Exception as e:
        print(f"\n❌ 실행 오류: {str(e)}")
        return False


def quick_test_api():
    """빠른 API 테스트"""
    print_header("빠른 API 테스트")

    try:
        config = CrawlerConfig()
        client = HogangnonoAPIClient(config)

        # 기본 bounding API 테스트
        print("1. 기본 pois-bounding API 테스트...")
        from src.crawler.api.hogangnono_client import SearchParams

        params = SearchParams(
            bbox=(126.924, 37.514, 127.087, 37.632),  # 강남구
            aptType=1,
            level=14,
        )

        response = client.get_apartments_bounding(params, use_cache=False)

        if response.success and response.data:
            items = (
                response.data if isinstance(response.data, list) else response.data.get("data", [])
            )
            print(f"✓ 성공: {len(items)}개 항목 수신")

            # 처음 5개 샘플 출력
            for i, item in enumerate(items[:5]):
                print(f"\n  항목 {i + 1}:")
                print(f"    ID: {item.get('id', 'N/A')}")
                print(f"    이름: {item.get('name', 'N/A')}")
                print(f"    유형: {item.get('category', 'N/A')}")
                print(f"    설명: {item.get('description', 'N/A')[:50]}...")
        else:
            print(f"✗ 실패: {response.error}")

        # 다른 파라미터로 테스트
        print("\n2. 다른 파라미터 테스트...")

        test_params = [
            {"aptType": 0, "level": 14},  # 전체 타입
            {"aptType": 2, "level": 14},  # 오피스텔
            {"aptType": 1, "level": 15},  # 더 상세
        ]

        for i, params in enumerate(test_params):
            print(f"\n  테스트 {i + 1}: {params}")
            test_search_params = SearchParams(bbox=(126.924, 37.514, 127.087, 37.632), **params)

            response = client.get_apartments_bounding(test_search_params, use_cache=False)
            if response.success and response.data:
                items = (
                    response.data
                    if isinstance(response.data, list)
                    else response.data.get("data", [])
                )
                print(f"    ✓ 성공: {len(items)}개 항목")
            else:
                print(f"    ✗ 실패: {response.error}")

            time.sleep(1)

        return True

    except Exception as e:
        print(f"❌ 테스트 오류: {str(e)}")
        return False


def main():
    """메인 실행"""
    print("호갱노노 API 아파트 데이터 탐색")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"작업 디렉토리: {Path.cwd()}")

    results = {
        "start_time": datetime.now().isoformat(),
        "tests": {},
        "summary": {},
    }

    # 1. 빠른 API 테스트
    success = quick_test_api()
    results["tests"]["quick_test"] = success

    if not success:
        print("\n⚠️  빠른 테스트 실패 - 다른 테스트는 건너뜁니다")
        return

    # 2. 파라미터 조합 탐색
    print("\n계속하려면 Enter를 누르세요 (Ctrl+C로 종료)...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n\n사용자가 종료했습니다")
        return

    script_path = Path("test_apartment_api_explorer.py")
    if script_path.exists():
        success = run_script(script_path, "파라미터 조합 탐색")
        results["tests"]["parameter_exploration"] = success
    else:
        print(f"\n⚠️  스크립트를 찾을 수 없습니다: {script_path}")
        results["tests"]["parameter_exploration"] = False

    # 3. 엔드포인트 분석
    print("\n계속하려면 Enter를 누르세요...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n\n사용자가 종료했습니다")
        return

    script_path = Path("test_api_endpoints_analysis.py")
    if script_path.exists():
        success = run_script(script_path, "API 엔드포인트 분석")
        results["tests"]["endpoint_analysis"] = success
    else:
        print(f"\n⚠️  스크립트를 찾을 수 없습니다: {script_path}")
        results["tests"]["endpoint_analysis"] = False

    # 4. 웹 API 패턴 분석
    print("\n계속하려면 Enter를 누르세요...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n\n사용자가 종료했습니다")
        return

    script_path = Path("analyze_web_api_patterns.py")
    if script_path.exists():
        success = run_script(script_path, "웹 API 패턴 분석")
        results["tests"]["web_pattern_analysis"] = success
    else:
        print(f"\n⚠️  스크립트를 찾을 수 없습니다: {script_path}")
        results["tests"]["web_pattern_analysis"] = False

    # 결과 요약
    print_header("탐색 결과 요약")

    results["end_time"] = datetime.now().isoformat()

    success_count = sum(1 for success in results["tests"].values() if success)
    total_count = len(results["tests"])

    print(f"\n수행된 테스트: {total_count}개")
    print(f"성공한 테스트: {success_count}개")
    print(f"실패한 테스트: {total_count - success_count}개")

    print("\n테스트 결과:")
    for test_name, success in results["tests"].items():
        status = "✓ 성공" if success else "✗ 실패"
        print(f"  - {test_name}: {status}")

    # 결과 저장
    import json

    results_file = Path("output/api_exploration_summary.json")
    results_file.parent.mkdir(parents=True, exist_ok=True)

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n상세 결과: {results_file}")

    # 최종 권장사항
    print_header("권장사항")

    recommendations = [
        "1. 모든 테스트 결과를 확인하고 아파트 데이터가 있는지 검토하세요",
        "2. output/ 디렉토리에 생성된 파일들을 상세히 분석하세요",
        "3. 아파트 데이터가 없다면 웹스크래핑을 고려해보세요",
        "4. API 문서나 개발자 도구를 통해 추가 정보를 수집하세요",
    ]

    for rec in recommendations:
        print(f"  {rec}")

    print("\n탐색 완료!")


if __name__ == "__main__":
    main()
