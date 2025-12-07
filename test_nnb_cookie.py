#!/usr/bin/env python3
"""NNB 쿠키 획득 테스트 스크립트"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, "src")

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler
from crawler.writers.csv_writer import CSVWriter


def test_nnb_cookie():
    """NNB 쿠키 획득 및 크롤링 테스트"""

    # 체크포인트 초기화
    checkpoint_path = Path("output/checkpoint.json")
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    # 출력 디렉토리 생성
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # CrawlerConfig 생성 (headless=True)
    config = CrawlerConfig(timeout=30, headless=True, output_dir=str(output_dir))

    # NaverRealEstateCrawler 초기화
    print("\n=== NaverRealEstateCrawler 초기화 ===")
    crawler = NaverRealEstateCrawler(config)

    # 금천구만 선택하고 첫 번째 동만 사용
    original_data = crawler.districts_data
    test_district = None
    for district in original_data["districts"]:
        if district["district_name"] == "금천구":
            test_district = district
            break

    if test_district is None:
        print("❌ 금천구를 찾을 수 없습니다")
        return False

    if len(test_district["dongs"]) < 1:
        print("❌ 금천구에 동이 없습니다")
        return False

    # districts_data를 금천구의 첫 번째 동만으로 수정
    crawler.districts_data = {
        "districts": [
            {
                "district_name": test_district["district_name"],
                "district_code": test_district["district_code"],
                "dongs": [test_district["dongs"][0]],  # 첫 번째 동만
            }
        ]
    }

    print(
        f"\n테스트 대상: {test_district['district_name']} {test_district['dongs'][0]['dong_name']}"
    )

    # 크롤러 실행
    print("\n=== 크롤링 시작 ===")
    try:
        results = crawler.crawl()
        print(f"\n✅ 크롤링 성공! 단지 수: {len(results)}")

        # 결과 검증
        if len(results) == 0:
            print("❌ 크롤링 결과가 비어있습니다")
            return False

        # 기본 필드 검증
        first_result = results[0]
        required_fields = [
            "complex_id",
            "complex_name",
            "real_estate_type",
            "completion_year_month",
            "total_dong_count",
            "total_household_count",
            "min_area",
            "max_area",
        ]

        missing_fields = []
        for field in required_fields:
            if field not in first_result:
                missing_fields.append(field)

        if missing_fields:
            print(f"❌ 필수 필드 누락: {missing_fields}")
            return False

        print("✅ 모든 필수 필드 존재")

        # CSV 저장 테스트
        output_path = output_dir / "test_nnb_crawl.csv"
        writer = CSVWriter(output_path)
        writer.write(results)

        if not output_path.exists():
            print("❌ CSV 파일이 생성되지 않았습니다")
            return False

        if output_path.stat().st_size == 0:
            print("❌ CSV 파일이 비어있습니다")
            return False

        print(f"✅ CSV 저장 성공: {output_path}")

        # CSV 내용 검증
        with open(output_path, encoding="utf-8") as f:
            lines = f.readlines()
            if len(lines) <= 1:
                print("❌ CSV에 데이터가 없습니다 (헤더만 존재)")
                return False

            if "complex_id" not in lines[0]:
                print("❌ CSV 헤더에 complex_id가 없습니다")
                return False

        print(f"✅ CSV 데이터 정상 (라인 수: {len(lines)})")

        # 체크포인트 파일 생성 검증
        if not checkpoint_path.exists():
            print("❌ 체크포인트 파일이 생성되지 않았습니다")
            return False

        print("✅ 체크포인트 파일 생성됨")

        # 체크포인트 내용 확인
        with open(checkpoint_path, encoding="utf-8") as f:
            checkpoint = json.load(f)
            last_dong = checkpoint.get("last_dong")
            if last_dong:
                print(f"✅ 체크포인트 저장: last_dong={last_dong}")

        print("\n🎉 NNB 쿠키 테스트 통과!")
        print(f"   - 크롤링된 단지: {len(results)}개")
        print("   - NNB 쿠키 획득: 성공")
        print("   - 세션 인증: 성공")
        return True

    except Exception as e:
        print(f"\n❌ 크롤링 실패: {str(e)}")

        # 에러 메시지 분석
        error_str = str(e).lower()
        if "failed to acquire naver session" in error_str:
            print("   - 원인: Naver 세션 획득 실패 (NNB 쿠키 문제)")
        elif "rate" in error_str or "limit" in error_str:
            print("   - 원인: 레이트 리밋")
        elif "timeout" in error_str:
            print("   - 원인: 타임아웃")
        else:
            print("   - 원인: 기타 오류")

        return False


if __name__ == "__main__":
    success = test_nnb_cookie()
    sys.exit(0 if success else 1)
