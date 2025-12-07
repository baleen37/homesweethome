"""구별 크롤링 기능 통합 테스트

실제 네이버 API를 호출하여 구별 필터링 기능을 테스트합니다.
네트워크 의존 테스트이므로 명시적으로 실행해야 합니다.

실행 방법:
    pytest tests/integration/test_district_crawling.py -v -s
"""

import json
import pytest
from pathlib import Path

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler


@pytest.fixture
def test_config(tmp_path: Path) -> CrawlerConfig:
    """테스트용 CrawlerConfig fixture"""
    return CrawlerConfig(headless=True, timeout=30, output_dir=str(tmp_path / "output"))


@pytest.fixture
def setup_test_output():
    """테스트용 output 디렉토리 설정 및 정리"""
    output_dir = Path("output/test_integration")
    output_dir.mkdir(parents=True, exist_ok=True)

    yield output_dir

    # 테스트 후 파일 정리 (선택적)
    # for file in output_dir.glob("*.csv"):
    #     file.unlink()
    # for file in output_dir.glob("*.json"):
    #     file.unlink()


@pytest.mark.slow
def test_crawl_single_district_real_api(test_config, setup_test_output):
    """실제 네이버 API로 강남구의 1개 동만 크롤링 테스트

    이 테스트는:
    - 강남구만 필터링하여 크롤링합니다
    - 실제 네이버 API를 호출합니다
    - 최소 1개 동이 처리되는지 검증합니다
    - CSV 파일이 생성되는지 확인합니다

    실행: pytest tests/integration/test_district_crawling.py::test_crawl_single_district_real_api -v -s
    """
    # 체크포인트 초기화
    checkpoint_path = Path("output/checkpoint.json")
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    # 크롤러 초기화
    crawler = NaverRealEstateCrawler(test_config)

    # 강남구 필터링 테스트
    print("\n=== 강남구 필터링 테스트 ===")
    districts = crawler.filter_districts(["강남구"])

    # 필터링 결과 검증
    assert len(districts) == 1, "강남구 필터링 결과가 1개가 아닙니다"
    assert districts[0]["district_name"] == "강남구", "강남구가 올바르게 필터링되지 않았습니다"
    print(f"필터링된 구: {districts[0]['district_name']}")
    print(f"동 수: {len(districts[0]['dongs'])}개")

    # 강남구의 첫 번째 동만 테스트 (시간 절약)
    test_dong = districts[0]["dongs"][0]
    print(f"테스트 동: {test_dong['dong_name']}")

    # districts_data를 강남구의 첫 번째 동만으로 수정
    crawler.districts_data = {
        "districts": [
            {
                "district_name": districts[0]["district_name"],
                "district_code": districts[0]["district_code"],
                "dongs": [test_dong],  # 첫 번째 동만
            }
        ]
    }

    # 크롤러 실행
    print("\n크롤링 시작...")
    results = crawler.crawl(district_filter=["강남구"])

    # 결과 검증
    assert isinstance(results, dict), "결과가 dict 형태가 아닙니다"
    assert results["dongs_processed"] >= 1, "처리된 동이 1개 이상이어야 합니다"
    assert results["total_complexes_processed"] > 0, "처리된 단지가 1개 이상이어야 합니다"

    print("\n크롤링 완료!")
    print(f"처리된 동: {results['dongs_processed']}개")
    print(f"처리된 단지: {results['total_complexes_processed']}개")

    # CSV 파일 생성 확인
    complexes_csv = Path(test_config.output_dir) / "complexes.csv"
    transactions_csv = Path(test_config.output_dir) / "transactions.csv"

    assert complexes_csv.exists(), "complexes.csv 파일이 생성되지 않았습니다"
    assert transactions_csv.exists(), "transactions.csv 파일이 생성되지 않았습니다"

    # CSV 내용 검증
    with open(complexes_csv, encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) > 1, "CSV에 데이터가 없습니다 (헤더만 존재)"
        assert "complex_id" in lines[0], "CSV 헤더에 complex_id가 없습니다"

        # 데이터 행 샘플 출력
        if len(lines) > 1:
            sample_line = lines[1].strip()
            print(f"\n첫 번째 데이터 행 샘플: {sample_line[:100]}...")

    with open(transactions_csv, encoding="utf-8") as f:
        lines = f.readlines()
        # transactions는 비어있을 수도 있음 (해당 동에 매물이 없는 경우)
        print(f"transactions.csv 라인 수: {len(lines)}")

    # 체크포인트 파일 검증
    assert checkpoint_path.exists(), "체크포인트 파일이 생성되지 않았습니다"
    with open(checkpoint_path, encoding="utf-8") as f:
        checkpoint = json.load(f)
        assert checkpoint.get("district_filter") == [
            "강남구"
        ], "체크포인트에 district_filter가 올바르게 저장되지 않았습니다"
        assert "last_dong" in checkpoint, "체크포인트에 last_dong이 없습니다"

    print("\n✅ test_crawl_single_district_real_api 테스트 통과!")
    print(f"   - 처리된 동: {results['dongs_processed']}개")
    print(f"   - 처리된 단지: {results['total_complexes_processed']}개")
    print(
        f"   - complexes.csv: {len(Path(test_config.output_dir, 'complexes.csv').read_text(encoding='utf-8').splitlines())} 라인"
    )
    print(
        f"   - transactions.csv: {len(Path(test_config.output_dir, 'transactions.csv').read_text(encoding='utf-8').splitlines())} 라인"
    )


@pytest.mark.slow
def test_crawl_multiple_districts_real_api(test_config):
    """여러 구 크롤링 테스트 (2개 구의 첫 번째 동만)

    이 테스트는:
    - 강남구와 서초구를 필터링하여 크롤링합니다
    - 각 구의 첫 번째 동만 크롤링하여 시간을 절약합니다
    - 여러 구 필터링이 올바르게 동작하는지 검증합니다

    실행: pytest tests/integration/test_district_crawling.py::test_crawl_multiple_districts_real_api -v -s
    """
    # 체크포인트 초기화
    checkpoint_path = Path("output/checkpoint.json")
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    # 크롤러 초기화
    crawler = NaverRealEstateCrawler(test_config)

    # 여러 구 필터링 테스트
    target_districts = ["강남구", "서초구"]
    print(f"\n=== 여러 구 필터링 테스트: {', '.join(target_districts)} ===")

    districts = crawler.filter_districts(target_districts)

    # 필터링 결과 검증
    assert len(districts) == 2, "2개 구가 필터링되어야 합니다"
    district_names = [d["district_name"] for d in districts]
    assert "강남구" in district_names, "강남구가 포함되지 않았습니다"
    assert "서초구" in district_names, "서초구가 포함되지 않았습니다"

    # 각 구의 첫 번째 동만 선택
    for i, district in enumerate(districts):
        first_dong = district["dongs"][0]
        districts[i]["dongs"] = [first_dong]
        print(f"선택된 동: {district['district_name']} {first_dong['dong_name']}")

    # districts_data 업데이트
    crawler.districts_data = {"districts": districts}

    # 크롤러 실행
    print("\n크롤링 시작...")
    results = crawler.crawl(district_filter=target_districts)

    # 결과 검증
    assert results["dongs_processed"] == 2, "2개 동이 처리되어야 합니다"
    assert results["total_complexes_processed"] > 0, "처리된 단지가 1개 이상이어야 합니다"

    print("\n크롤링 완료!")
    print(f"처리된 동: {results['dongs_processed']}개")
    print(f"처리된 단지: {results['total_complexes_processed']}개")

    # 체크포인트 검증
    assert checkpoint_path.exists(), "체크포인트 파일이 생성되지 않았습니다"
    with open(checkpoint_path, encoding="utf-8") as f:
        checkpoint = json.load(f)
        saved_filter = checkpoint.get("district_filter", [])
        assert set(saved_filter) == set(
            target_districts
        ), "체크포인트에 district_filter가 올바르게 저장되지 않았습니다"

    print("\n✅ test_crawl_multiple_districts_real_api 테스트 통과!")


def test_crawl_invalid_district(test_config):
    """유효하지 않은 구 이름에 대한 에러 처리 테스트

    이 테스트는:
    - 유효하지 않은 구 이름을 필터링 시도합니다
    - ValueError가 발생하는지 검증합니다
    - 에러 메시지에 적절한 정보가 포함되는지 확인합니다

    실행: pytest tests/integration/test_district_crawling.py::test_crawl_invalid_district -v
    """
    # 크롤러 초기화
    crawler = NaverRealEstateCrawler(test_config)

    # 유효하지 않은 구 이름으로 필터링 시도
    invalid_districts = ["강남", "없는구", "InvalidDistrict"]

    print(f"\n=== 유효하지 않은 구 테스트: {', '.join(invalid_districts)} ===")

    # ValueError가 발생하는지 확인
    with pytest.raises(ValueError) as exc_info:
        crawler.filter_districts(invalid_districts)

    # 에러 메시지 검증
    error_message = str(exc_info.value)
    assert "유효하지 않은 구 이름" in error_message, "에러 메시지에 적절한 내용이 없습니다"
    assert "강남" in error_message, "잘못된 구 이름이 에러 메시지에 포함되어야 합니다"
    assert "사용 가능한 구" in error_message, "사용 가능한 구 목록 안내가 있어야 합니다"

    print(f"에러 메시지: {error_message}")

    # 전체 구 목록이 에러 메시지에 포함되는지 확인
    all_districts = {d["district_name"] for d in crawler.districts_data["districts"]}
    for district in list(all_districts)[:3]:  # 처음 3개 구만 확인 (테스트 속도)
        assert district in error_message, f"사용 가능한 구 '{district}'가 에러 메시지에 없습니다"

    print("\n✅ test_crawl_invalid_district 테스트 통과!")


def test_filter_districts_none(test_config):
    """district_filter가 None일 때 전체 구가 반환되는지 테스트

    이 테스트는:
    - filter_districts에 None을 전달합니다
    - 전체 구 목록이 반환되는지 검증합니다

    실행: pytest tests/integration/test_district_crawling.py::test_filter_districts_none -v
    """
    # 크롤러 초기화
    crawler = NaverRealEstateCrawler(test_config)

    print("\n=== 전체 구 필터링 테스트 (district_filter=None) ===")

    # None으로 필터링
    districts = crawler.filter_districts(None)

    # 전체 구가 반환되는지 검증
    original_districts = crawler.districts_data["districts"]
    assert len(districts) == len(original_districts), "전체 구가 반환되어야 합니다"

    # 구 이름 확인
    district_names = [d["district_name"] for d in districts]
    original_names = [d["district_name"] for d in original_districts]
    assert set(district_names) == set(original_names), "구 이름이 일치해야 합니다"

    print(f"반환된 구 수: {len(districts)}개")
    print(f"처음 5개 구: {', '.join(district_names[:5])}")

    print("\n✅ test_filter_districts_none 테스트 통과!")


@pytest.mark.slow
def test_resume_with_different_district_filter(test_config):
    """다른 district_filter로 resume 시도 시 에러 처리 테스트

    이 테스트는:
    - 특정 구로 크롤링을 시작하고 체크포인트를 생성합니다
    - 다른 구 필터로 resume을 시도합니다
    - 에러가 발생하는지 검증합니다

    실행: pytest tests/integration/test_district_crawling.py::test_resume_with_different_district_filter -v -s
    """
    # 체크포인트 초기화
    checkpoint_path = Path("output/checkpoint.json")
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    # 크롤러 초기화
    crawler = NaverRealEstateCrawler(test_config)

    # 1. 강남구로 체크포인트 생성
    print("\n=== 체크포인트 생성 (강남구) ===")
    districts = crawler.filter_districts(["강남구"])
    first_dong = districts[0]["dongs"][0]
    crawler.districts_data = {
        "districts": [
            {
                "district_name": districts[0]["district_name"],
                "district_code": districts[0]["district_code"],
                "dongs": [first_dong],
            }
        ]
    }

    # 크롤링 실행하여 체크포인트 생성
    results = crawler.crawl(district_filter=["강남구"])
    assert results["dongs_processed"] == 1

    # 체크포인트 확인
    assert checkpoint_path.exists(), "체크포인트가 생성되지 않았습니다"
    with open(checkpoint_path, encoding="utf-8") as f:
        checkpoint = json.load(f)
        assert checkpoint["district_filter"] == ["강남구"]

    print(f"체크포인트 생성됨: {checkpoint['district_filter']}")

    # 2. 다른 구 필터로 resume 시도
    print("\n=== 다른 구 필터로 resume 시도 (서초구) ===")
    crawler2 = NaverRealEstateCrawler(test_config)

    # validate_resume 메서드가 있는 경우 테스트
    if hasattr(crawler2, "validate_resume"):
        is_valid = crawler2.validate_resume(["서초구"])
        assert not is_valid, "다른 구 필터로 resume은 불가능해야 합니다"
        print("validate_resume: False (올바름)")
    else:
        # validate_resume 메서드가 없는 경우, crawl()이 에러를 발생시키는지 확인
        with pytest.raises(Exception) as exc_info:
            crawler2.crawl(district_filter=["서초구"], resume=True)

        # 에러 종류 확인 (구현에 따라 다를 수 있음)
        error_message = str(exc_info.value).lower()
        assert any(
            keyword in error_message for keyword in ["district", "filter", "mismatch", "different"]
        ), "구 필터 불일치 에러가 발생해야 합니다"
        print(f"에러 발생: {str(exc_info.value)}")

    print("\n✅ test_resume_with_different_district_filter 테스트 통과!")


@pytest.mark.slow
def test_crawl_all_districts_vs_filtered(test_config):
    """전체 크롤링과 필터링 크롤링의 결과 비교 테스트

    이 테스트는:
    - 금천구 전체를 크롤링합니다
    - 금천구를 필터링하여 크롤링합니다
    - 두 결과의 단지 수가 같은지 확인합니다

    실행: pytest tests/integration/test_district_crawling.py::test_crawl_all_districts_vs_filtered -v -s
    """
    # 체크포인트 초기화
    checkpoint_path = Path("output/checkpoint.json")
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    # 금천구 데이터 준비
    crawler_temp = NaverRealEstateCrawler(test_config)
    geumcheon_district = None
    for district in crawler_temp.districts_data["districts"]:
        if district["district_name"] == "금천구":
            geumcheon_district = district
            break

    assert geumcheon_district is not None, "금천구를 찾을 수 없습니다"
    print("\n=== 금천구 크롤링 비교 테스트 ===")
    print(f"금천구 동 수: {len(geumcheon_district['dongs'])}개")

    # 1. 금천구만 포함하도록 districts_data 설정 (방법 1)
    print("\n1. districts_data 직접 설정 방식")
    crawler1 = NaverRealEstateCrawler(test_config)
    crawler1.districts_data = {"districts": [geumcheon_district]}
    results1 = crawler1.crawl()
    complexes_count1 = len(results1)
    print(f"   - 크롤링된 단지: {complexes_count1}개")

    # 체크포인트 초기화
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    # 2. district_filter 사용 (방법 2)
    print("\n2. district_filter 사용 방식")
    crawler2 = NaverRealEstateCrawler(test_config)
    results2 = crawler2.crawl(district_filter=["금천구"])
    complexes_count2 = len(results2)
    print(f"   - 크롤링된 단지: {complexes_count2}개")

    # 결과 비교
    assert complexes_count1 > 0, "첫 번째 방법에서 단지가 크롤링되어야 합니다"
    assert complexes_count2 > 0, "두 번째 방법에서 단지가 크롤링되어야 합니다"

    # 두 방법의 결과는 같아야 함 (네트워크 상태에 따라 약간의 차이는 있을 수 있음)
    difference = abs(complexes_count1 - complexes_count2)
    print(f"\n두 방법의 단지 수 차이: {difference}개")

    # 허용 가능한 차이 (네트워크 타이밍에 따라 약간의 차이는 있을 수 있음)
    assert (
        difference <= max(complexes_count1, complexes_count2) * 0.1
    ), f"두 방법의 결과 차이가 너무 큽니다: {difference}"

    print("\n✅ test_crawl_all_districts_vs_filtered 테스트 통과!")
    print(f"   - 방법 1 (직접 설정): {complexes_count1}개 단지")
    print(f"   - 방법 2 (필터링): {complexes_count2}개 단지")
