"""네이버 부동산 크롤러 E2E 통합 테스트

실제 Playwright를 띄워서 실제 네이버 부동산 모바일 API를 호출하는 통합 테스트입니다.
네트워크 의존 테스트이므로 명시적으로 실행해야 합니다.

실행 방법:
    pytest tests/integration/test_naver_integration.py -v -s
"""

import json
import pytest
from pathlib import Path

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler
from crawler.writers.csv_writer import CSVWriter


@pytest.mark.integration
def test_real_crawl_small_area(tmp_path: Path) -> None:
    """
    실제 Playwright를 띄워서 금천구 3개 동만 크롤링하는 E2E 테스트

    이 테스트는:
    - 실제 브라우저를 실행합니다 (headless=True)
    - 실제 네이버 부동산 모바일 API를 호출합니다
    - 실제 데이터를 수집하고 CSV로 저장합니다

    실행: pytest tests/integration/test_naver_integration.py::test_real_crawl_small_area -v -s
    """
    # 체크포인트 초기화
    checkpoint_path = Path("output/checkpoint.json")
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    config = CrawlerConfig(timeout=30, headless=True, output_dir=str(tmp_path))
    crawler = NaverRealEstateCrawler(config)

    # 금천구만 선택 (3개 동)
    original_data = crawler.districts_data
    test_district = None
    for district in original_data["districts"]:
        if district["district_name"] == "금천구":
            test_district = district
            break

    assert test_district is not None, "금천구를 찾을 수 없습니다"

    crawler.districts_data = {"districts": [test_district]}

    # 실제 크롤링 실행
    results = crawler.crawl()

    # 결과 검증
    assert len(results) > 0, "크롤링 결과가 비어있습니다"
    print(f"\n크롤링된 단지 수: {len(results)}")

    # 첫 번째 결과 필드 검증 (모바일 API 응답 형식)
    first_result = results[0]
    assert "complex_id" in first_result
    assert "complex_name" in first_result
    assert "real_estate_type" in first_result
    assert "completion_year_month" in first_result
    assert "total_dong_count" in first_result
    assert "total_household_count" in first_result
    assert "min_area" in first_result
    assert "max_area" in first_result

    # CSV 저장 검증
    output_path = tmp_path / "test_output.csv"
    writer = CSVWriter(output_path)
    writer.write(results)

    assert output_path.exists()
    assert output_path.stat().st_size > 0

    # CSV 내용 검증
    with open(output_path, encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) > 1  # 헤더 + 데이터
        assert "complex_id" in lines[0]  # 헤더 확인

    print(f"CSV 저장 완료: {output_path}")
    print(f"CSV 라인 수: {len(lines)}")

    # 체크포인트 검증
    assert checkpoint_path.exists(), "체크포인트 파일이 생성되지 않았습니다"


@pytest.mark.integration
def test_real_crawl_with_checkpoint(tmp_path: Path) -> None:
    """
    체크포인트 저장 및 재개 기능 E2E 테스트

    이 테스트는:
    - 첫 번째 크롤링에서 1개 동만 크롤링하고 체크포인트 저장
    - 두 번째 크롤링에서 체크포인트를 로드하고 나머지 동 크롤링
    - 중복 크롤링이 발생하지 않는지 검증

    실행: pytest tests/integration/test_naver_integration.py::test_real_crawl_with_checkpoint -v -s
    """
    # 체크포인트 초기화
    checkpoint_path = Path("output/checkpoint.json")
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    config = CrawlerConfig(timeout=30, headless=True, output_dir=str(tmp_path))

    # 금천구 데이터 준비 (3개 동)
    crawler_temp = NaverRealEstateCrawler(config)
    test_district = None
    for district in crawler_temp.districts_data["districts"]:
        if district["district_name"] == "금천구":
            test_district = district
            break

    assert test_district is not None
    assert len(test_district["dongs"]) == 3

    # === 첫 번째 크롤링: 1개 동만 ===
    crawler1 = NaverRealEstateCrawler(config)
    crawler1.districts_data = {
        "districts": [
            {
                "district_name": test_district["district_name"],
                "district_code": test_district["district_code"],
                "dongs": [test_district["dongs"][0]],  # 첫 번째 동만
            }
        ]
    }

    results1 = crawler1.crawl()
    print(f"\n첫 번째 크롤링 결과: {len(results1)}개 단지")

    # 체크포인트 검증
    assert checkpoint_path.exists(), "체크포인트 파일이 생성되지 않았습니다"
    with open(checkpoint_path, encoding="utf-8") as f:
        checkpoint = json.load(f)
        assert len(checkpoint["completed_dongs"]) == 1
        print(f"체크포인트 저장됨: {checkpoint['completed_dongs']}")

    # === 두 번째 크롤링: 전체 3개 동 (1개는 skip되어야 함) ===
    crawler2 = NaverRealEstateCrawler(config)
    crawler2.districts_data = {"districts": [test_district]}  # 전체 3개 동

    results2 = crawler2.crawl()
    print(f"두 번째 크롤링 결과: {len(results2)}개 단지")

    # 체크포인트 업데이트 검증
    with open(checkpoint_path, encoding="utf-8") as f:
        checkpoint_final = json.load(f)
        assert len(checkpoint_final["completed_dongs"]) == 3
        print(f"최종 체크포인트: {checkpoint_final['completed_dongs']}")

    # 중복 크롤링 없이 전체 결과 확인
    assert len(results1) > 0, "첫 번째 크롤링 결과가 비어있습니다"
    assert len(results2) > 0, "두 번째 크롤링 결과가 비어있습니다"

    print(f"\n총 크롤링된 단지 수: {len(results1) + len(results2)}")


@pytest.mark.integration
def test_fetch_complex_detail(tmp_path: Path) -> None:
    """
    fetch_complex_detail() 메서드 통합 테스트

    이 테스트는:
    - 실제 브라우저를 실행합니다 (headless=True)
    - 금천구의 첫 번째 동에서 단지 정보를 가져옵니다
    - 첫 번째 단지의 상세 정보를 fetch_complex_detail()로 가져옵니다
    - 상세 정보 응답의 필드들을 검증합니다

    실행: pytest tests/integration/test_naver_integration.py::test_fetch_complex_detail -v -s
    """
    # 체크포인트 초기화
    checkpoint_path = Path("output/checkpoint.json")
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    # CrawlerConfig 설정 (headless=True)
    config = CrawlerConfig(timeout=30, headless=True, output_dir=str(tmp_path))
    crawler = NaverRealEstateCrawler(config)

    # 금천구만 선택하고 첫 번째 동만 사용
    original_data = crawler.districts_data
    test_district = None
    for district in original_data["districts"]:
        if district["district_name"] == "금천구":
            test_district = district
            break

    assert test_district is not None, "금천구를 찾을 수 없습니다"

    # 첫 번째 동만 설정
    crawler.districts_data = {
        "districts": [{
            "district_name": test_district["district_name"],
            "district_code": test_district["district_code"],
            "dongs": [test_district["dongs"][0]]  # 첫 번째 동만
        }]
    }

    print(f"\n테스트 동: {test_district['dongs'][0]['dong_name']}")

    # 크롤러 실행하여 단지 목록 가져오기
    try:
        complexes = crawler.crawl()
        assert len(complexes) > 0, "크롤링된 단지가 없습니다"
        print(f"\n크롤링된 단지 수: {len(complexes)}")

        # 첫 번째 단지의 complex_id 가져오기
        first_complex = complexes[0]
        complex_id = first_complex["complex_id"]
        complex_name = first_complex["complex_name"]
        print(f"\n테스트 대상 단지: {complex_name} (ID: {complex_id})")

        # fetch_complex_detail() 호출
        print("\nfetch_complex_detail() 호출 중...")
        detail = crawler.fetch_complex_detail(complex_id)

        # 상세 정보 검증
        assert detail is not None, "상세 정보를 가져오지 못했습니다"

        # 필수 필드 검증 (address 계열 필드 중 하나는 있어야 함)
        has_address = (
            detail.get("road_address") is not None or
            detail.get("jibun_address") is not None
        )
        assert has_address, "주소 정보(road_address 또는 jibun_address)가 없습니다"

        # 주요 정보 출력
        print(f"\n=== 단지 상세 정보 ===")
        print(f"단지명: {detail.get('complex_name', 'N/A')}")
        print(f"도로명 주소: {detail.get('road_address', 'N/A')}")
        print(f"지번 주소: {detail.get('jibun_address', 'N/A')}")
        print(f"건물 종류: {detail.get('building_type', 'N/A')}")
        print(f"총 세대수: {detail.get('total_household_count', 'N/A')}")
        print(f"준공일: {detail.get('completion_date', 'N/A')}")
        print(f"관리비: {detail.get('maintenance_cost', 'N/A')}")

        # 세부 정보 필드 확인 (있을 수도 있고 없을 수도 있음)
        optional_fields = [
            "building_type", "total_household_count", "completion_date",
            "maintenance_cost", "parking_count", "heating_type",
            "floor_plan", "move_in_date", "total_dong_count"
        ]

        print(f"\n=== 추가 필드 확인 ===")
        for field in optional_fields:
            value = detail.get(field)
            if value is not None:
                print(f"{field}: {value}")

        # 응답에 기본 정보가 있는지 최소한으로 확인
        assert detail.get("complex_id") == complex_id, "complex_id가 일치하지 않습니다"

        print(f"\n✅ fetch_complex_detail() 테스트 성공!")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        # 레이트 리밋 가능성
        if "rate" in str(e).lower() or "limit" in str(e).lower():
            print("⚠️ 레이트 리밋에 걸렸을 수 있습니다. 잠시 후 다시 시도하세요.")
        raise
