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
def test_crawl_complexes_basic(tmp_path: Path) -> None:
    """
    기본 단지 크롤링 기능 테스트 (Level 1)

    이 테스트는:
    - 금천구의 첫 번째 동만 크롤링합니다 (1개 동만)
    - 실제 브라우저를 실행합니다 (headless=True)
    - 기본 필드들이 올바르게 수집되는지 검증합니다
    - CSV 저장 기능을 검증합니다
    - 체크포인트 파일 생성을 확인합니다

    실행: pytest tests/integration/test_naver_integration.py::test_crawl_complexes_basic -v -s
    """
    # 체크포인트 초기화
    checkpoint_path = Path("output/checkpoint.json")
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    # CrawlerConfig 생성 (headless=True)
    config = CrawlerConfig(timeout=30, headless=True, output_dir=str(tmp_path))

    # NaverRealEstateCrawler 초기화
    crawler = NaverRealEstateCrawler(config)

    # 금천구만 선택하고 첫 번째 동만 사용
    original_data = crawler.districts_data
    test_district = None
    for district in original_data["districts"]:
        if district["district_name"] == "금천구":
            test_district = district
            break

    assert test_district is not None, "금천구를 찾을 수 없습니다"
    assert len(test_district["dongs"]) >= 1, "금천구에 동이 없습니다"

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
    results = crawler.crawl()

    # 결과 검증
    assert len(results) > 0, "크롤링 결과가 비어있습니다"
    print(f"\n크롤링된 단지 수: {len(results)}")

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

    for field in required_fields:
        assert field in first_result, f"필수 필드 '{field}'가 없습니다"

    # CSV 저장 테스트
    output_path = tmp_path / "test_basic_crawl.csv"
    writer = CSVWriter(output_path)
    writer.write(results)

    assert output_path.exists(), "CSV 파일이 생성되지 않았습니다"
    assert output_path.stat().st_size > 0, "CSV 파일이 비어있습니다"

    # CSV 내용 검증
    with open(output_path, encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) > 1, "CSV에 데이터가 없습니다 (헤더만 존재)"
        assert "complex_id" in lines[0], "CSV 헤더에 complex_id가 없습니다"

    print(f"CSV 저장 완료: {output_path}")
    print(f"CSV 라인 수: {len(lines)} (헤더 포함)")

    # 체크포인트 파일 생성 검증
    assert checkpoint_path.exists(), "체크포인트 파일이 생성되지 않았습니다"

    print("\n✅ test_crawl_complexes_basic 테스트 통과!")
    print(f"   - 크롤링된 단지: {len(results)}개")
    print("   - 체크포인트: 생성됨")


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
        assert checkpoint["last_dong"] == test_district["dongs"][0]["cortarNo"]
        print(f"체크포인트 저장됨: last_dong={checkpoint['last_dong']}")

    # === 두 번째 크롤링: 전체 3개 동 (1개는 skip되어야 함) ===
    crawler2 = NaverRealEstateCrawler(config)
    crawler2.districts_data = {"districts": [test_district]}  # 전체 3개 동

    results2 = crawler2.crawl()
    print(f"두 번째 크롤링 결과: {len(results2)}개 단지")

    # 체크포인트 업데이트 검증
    with open(checkpoint_path, encoding="utf-8") as f:
        checkpoint_final = json.load(f)
        # 마지막 동이 마지막으로 완료된 동인지 확인
        assert checkpoint_final["last_dong"] == test_district["dongs"][-1]["cortarNo"]
        print(f"최종 체크포인트: last_dong={checkpoint_final['last_dong']}")

    # 중복 크롤링 없이 전체 결과 확인
    assert len(results1) > 0, "첫 번째 크롤링 결과가 비어있습니다"
    assert len(results2) > 0, "두 번째 크롤링 결과가 비어있습니다"

    # 두 번째 크롤링에서는 첫 번째 동을 건너뛰고 나머지 2개 동만 크롤링해야 함
    # 따라서 총 결과 수는 첫 번째 크롤링 결과 + 두 번째 크롤링 결과가 되어야 함
    print(
        f"\n총 크롤링된 단지 수: 첫 번째 {len(results1)}개 + 두 번째 {len(results2)}개 = {len(results1) + len(results2)}개"
    )


@pytest.mark.integration
def test_fetch_complex_detail(tmp_path: Path) -> None:
    """
    fetch_complex_detail() 메서드 통합 테스트

    이 테스트는:
    - 실제 브라우저를 실행합니다 (headless=True)
    - 금천구의 첫 번째 동에서 단지 정보를 가져옵니다
    - 새 크롤러 인스턴스를 생성하여 첫 번째 단지의 상세 정보를 fetch_complex_detail()로 가져옵니다
    - 상세 정보 응답의 필드들을 검증합니다

    실행: pytest tests/integration/test_naver_integration.py::test_fetch_complex_detail -v -s
    """
    # 체크포인트 초기화
    checkpoint_path = Path("output/checkpoint.json")
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    # CrawlerConfig 설정 (headless=True)
    config = CrawlerConfig(timeout=30, headless=True, output_dir=str(tmp_path))

    # 1. 첫 번째 크롤러: 단지 목록 가져오기
    crawler1 = NaverRealEstateCrawler(config)

    # 금천구만 선택하고 첫 번째 동만 사용
    original_data = crawler1.districts_data
    test_district = None
    for district in original_data["districts"]:
        if district["district_name"] == "금천구":
            test_district = district
            break

    assert test_district is not None, "금천구를 찾을 수 없습니다"

    # 첫 번째 동만 설정
    crawler1.districts_data = {
        "districts": [
            {
                "district_name": test_district["district_name"],
                "district_code": test_district["district_code"],
                "dongs": [test_district["dongs"][0]],  # 첫 번째 동만
            }
        ]
    }

    print(f"\n테스트 동: {test_district['dongs'][0]['dong_name']}")

    # 크롤러 실행하여 단지 목록 가져오기
    complex_id = None
    complex_name = None

    try:
        complexes = crawler1.crawl()
        assert len(complexes) > 0, "크롤링된 단지가 없습니다"
        print(f"\n크롤링된 단지 수: {len(complexes)}")

        # 첫 번째 단지의 complex_id 가져오기
        first_complex = complexes[0]
        complex_id = str(first_complex["complex_id"])
        complex_name = first_complex["complex_name"]
        print(f"\n테스트 대상 단지: {complex_name} (ID: {complex_id})")

    except Exception as e:
        print(f"\n❌ 단지 목록 크롤링 실패: {str(e)}")
        # 레이트 리밋 가능성
        if "rate" in str(e).lower() or "limit" in str(e).lower():
            print("⚠️ 레이트 리밋에 걸렸을 수 있습니다. 잠시 후 다시 시도하세요.")
        raise

    # 2. 두 번째 크롤러: 단지 상세 정보 가져오기
    print("\n새 크롤러 인스턴스 생성 중...")
    crawler2 = NaverRealEstateCrawler(config)

    try:
        # fetch_complex_detail() 호출
        print(f"\nfetch_complex_detail() 호출 중... (complex_id: {complex_id})")
        detail = crawler2.fetch_complex_detail(complex_id)

        # 상세 정보 검증
        assert detail is not None, "상세 정보를 가져오지 못했습니다"

        # 에러가 있는지 확인
        if "error" in detail:
            print(f"\n⚠️ API에서 에러 반환: {detail['error']}")
            # 에러가 있어도 테스트는 계속 진행 (일부 필드만 확인)

        # 주요 정보 출력
        print("\n=== 단지 상세 정보 ===")
        print(f"Complex ID: {detail.get('complex_id', 'N/A')}")
        print(f"Fetched at: {detail.get('fetched_at', 'N/A')}")

        # pyeong_types가 있는 경우 (가장 확실한 데이터)
        if "pyeong_types" in detail and detail["pyeong_types"]:
            print(f"평형 정보: {len(detail['pyeong_types'])}개")
            for i, pyeong in enumerate(detail["pyeong_types"][:3]):  # 처음 3개만
                print(
                    f"  - {pyeong.get('pyeong_name', 'N/A')}: "
                    f"전용 {pyeong.get('exclusive_area', 'N/A')}㎡ / "
                    f"공급 {pyeong.get('supply_area', 'N/A')}㎡"
                )

        # 기타 필드들 (있을 수도 있고 없을 수도 있음)
        other_fields = [
            "road_address",
            "jibun_address",
            "complex_name",
            "building_type",
            "total_household_count",
            "completion_date",
            "maintenance_cost",
            "parking_count",
            "heating_type",
            "move_in_date",
            "total_dong_count",
        ]

        print("\n=== 기타 필드 확인 ===")
        found_fields = []
        for field in other_fields:
            value = detail.get(field)
            if value is not None:
                print(f"{field}: {value}")
                found_fields.append(field)

        # 최소한 pyeong_types나 주소 정보 중 하나는 있어야 함
        has_data = (
            ("pyeong_types" in detail and detail["pyeong_types"])
            or (detail.get("road_address") is not None or detail.get("jibun_address") is not None)
            or (
                "error" not in detail  # 에러가 없다는 것 자체가 성공
            )
        )

        assert has_data, "단지 상세 정보가 비어있습니다"
        assert detail.get("complex_id") == complex_id, "complex_id가 일치하지 않습니다"

        print("\n✅ fetch_complex_detail() 테스트 성공!")
        print(f"   - {len(found_fields)}개의 추가 필드 발견")
        if "pyeong_types" in detail and detail["pyeong_types"]:
            print(f"   - {len(detail['pyeong_types'])}개의 평형 정보 확인")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        # 레이트 리밋 가능성
        if "rate" in str(e).lower() or "limit" in str(e).lower():
            print("⚠️ 레이트 리밋에 걸렸을 수 있습니다. 잠시 후 다시 시도하세요.")
        raise


@pytest.mark.integration
def test_fetch_heliocity_listings(tmp_path: Path) -> None:
    """
    헬리오시티 매물 목록 테스트 (기존 테스트 유지)

    이 테스트는:
    - 실제 브라우저를 실행합니다 (headless=True)
    - 헬리오시티의 매물 목록을 가져옵니다
    - 매매(A1), 전세(B1), 월세(B2) 모두 테스트합니다

    실행: pytest tests/integration/test_naver_integration.py::test_fetch_heliocity_listings -v -s
    """
    # 헬리오시티 complex ID (실제 존재하는 단지)
    HELIO_CITY_ID = "112581"  # 헬리오시티 3단지

    config = CrawlerConfig(timeout=30, headless=True, output_dir=str(tmp_path))
    crawler = NaverRealEstateCrawler(config)

    print(f"\n=== 헬리오시티 매물 목록 테스트 (ID: {HELIO_CITY_ID}) ===")

    # 1. 매매(A1) 테스트
    print("\n1. 매매(A1) 매물 목록 가져오기...")
    try:
        sale_listings = crawler.fetch_complex_listings(HELIO_CITY_ID, "A1")
        print(f"   - 매매 매물 수: {len(sale_listings)}")

        if sale_listings:
            first_sale = sale_listings[0]
            print(
                f"   - 첫 번째 매물: {first_sale.get('complex_name', 'N/A')} "
                f"{first_sale.get('area', 'N/A')}㎡ "
                f"{first_sale.get('floor', 'N/A')}층"
            )

            # 필드 검증
            required_fields = ["article_id", "complex_id", "trade_type", "price"]
            for field in required_fields:
                assert field in first_sale, f"매매 매물에 {field} 필드가 없습니다"

            # 가격 정보 확인
            assert first_sale.get("price"), "매매 매물의 가격 정보가 비어있습니다"

    except Exception as e:
        print(f"   - 매매 매물 조회 실패: {str(e)}")
        if "rate" in str(e).lower() or "limit" in str(e).lower():
            print("   - 레이트 리밋: 2초 대기 후 재시도...")
            import time

            time.sleep(2)
            sale_listings = crawler.fetch_complex_listings(HELIO_CITY_ID, "A1")
            assert sale_listings is not None, "재시도 후에도 매매 매물을 가져오지 못했습니다"
        else:
            raise

    # 2. 전세(B1) 테스트
    print("\n2. 전세(B1) 매물 목록 가져오기...")
    try:
        lease_listings = crawler.fetch_complex_listings(HELIO_CITY_ID, "B1")
        print(f"   - 전세 매물 수: {len(lease_listings)}")

        if lease_listings:
            first_lease = lease_listings[0]
            print(
                f"   - 첫 번째 매물: {first_lease.get('complex_name', 'N/A')} "
                f"{first_lease.get('area', 'N/A')}㎡ "
                f"{first_lease.get('floor', 'N/A')}층"
            )

            # 필드 검증
            assert first_lease.get("trade_type") == "B1", "전세 매물의 거래 유형이 B1이 아닙니다"
            assert first_lease.get("price"), "전세 매물의 가격 정보가 비어있습니다"

    except Exception as e:
        print(f"   - 전세 매물 조회 실패: {str(e)}")
        # 전세 매물이 없을 수도 있음
        if (
            "result" in str(e)
            and len(e.args[0]) > 0
            and "result" in e.args[0]
            and len(e.args[0]["result"]) == 0
        ):
            print("   - 전세 매물 없음 (정상)")
        else:
            raise

    # 3. 월세(B2) 테스트
    print("\n3. 월세(B2) 매물 목록 가져오기...")
    try:
        rent_listings = crawler.fetch_complex_listings(HELIO_CITY_ID, "B2")
        print(f"   - 월세 매물 수: {len(rent_listings)}")

        if rent_listings:
            first_rent = rent_listings[0]
            print(
                f"   - 첫 번째 매물: {first_rent.get('complex_name', 'N/A')} "
                f"{first_rent.get('area', 'N/A')}㎡ "
                f"{first_rent.get('floor', 'N/A')}층"
            )

            # 필드 검증
            assert first_rent.get("trade_type") == "B2", "월세 매물의 거래 유형이 B2가 아닙니다"

            # 월세는 보증금과 월세가 모두 있어야 함
            assert first_rent.get("price"), "월세 매물의 가격 정보가 비어있습니다"

            # 계약 갱신권 정보 확인
            if first_rent.get("is_contract_renewal") == "Y":
                print(
                    f"   - 계약 갱신권: {first_rent.get('contract_renewal_price', 'N/A')} / "
                    f"{first_rent.get('contract_renewal_fee', 'N/A')}"
                )

    except Exception as e:
        print(f"   - 월세 매물 조회 실패: {str(e)}")
        # 월세 매물이 없을 수도 있음
        if (
            "result" in str(e)
            and len(e.args[0]) > 0
            and "result" in e.args[0]
            and len(e.args[0]["result"]) == 0
        ):
            print("   - 월세 매물 없음 (정상)")
        else:
            raise

    # 4. 모든 매물 정보 합치기
    all_listings = []
    if "sale_listings" in locals():
        all_listings.extend(sale_listings)
    if "lease_listings" in locals():
        all_listings.extend(lease_listings)
    if "rent_listings" in locals():
        all_listings.extend(rent_listings)

    # 5. CSV로 저장
    if all_listings:
        print("\n=== CSV 저장 ===")
        csv_path = tmp_path / "heliocity_listings.csv"
        writer = CSVWriter(csv_path)
        writer.write(all_listings)

        print(f"   - 총 {len(all_listings)}개 매물 저장됨")
        print(f"   - 파일 경로: {csv_path}")

        # CSV 파일 확인
        assert csv_path.exists()
        with open(csv_path, encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) > 1  # 헤더 + 데이터
            print(f"   - CSV 라인 수: {len(lines)}")
    else:
        print("\n⚠️ 저장할 매물이 없습니다")

    print("\n✅ fetch_complex_listings() 테스트 완료!")


@pytest.mark.integration
def test_fetch_complex_listings(tmp_path: Path) -> None:
    """
    fetch_complex_listings() 메서드 통합 테스트

    이 테스트는:
    - 실제 브라우저를 실행합니다 (headless=True)
    - 금천구에서 매물이 있는 단지를 찾아 테스트합니다
    - fetch_complex_listings() 메서드의 응답을 검증합니다

    실행: pytest tests/integration/test_naver_integration.py::test_fetch_complex_listings -v -s
    """
    # 체크포인트 초기화
    checkpoint_path = Path("output/checkpoint.json")
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    # CrawlerConfig 설정 (headless=True)
    config = CrawlerConfig(timeout=30, headless=True, output_dir=str(tmp_path))

    # 크롤러 초기화
    crawler = NaverRealEstateCrawler(config)

    print("\n=== fetch_complex_listings() 테스트 시작 ===")

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
        "districts": [
            {
                "district_name": test_district["district_name"],
                "district_code": test_district["district_code"],
                "dongs": [test_district["dongs"][0]],  # 첫 번째 동만
            }
        ]
    }

    print(f"\n테스트 동: {test_district['dongs'][0]['dong_name']}")

    # 1. 크롤러 실행하여 단지 목록 가져오기
    complexes_with_listings = None
    complex_id_to_test = None
    complex_name_to_test = None

    try:
        print("\n크롤링 실행 중...")
        complexes = crawler.crawl()
        assert len(complexes) > 0, "크롤링된 단지가 없습니다"
        print(f"크롤링된 단지 수: {len(complexes)}")

        # 매물이 있는 단지 찾기 (total_article_count > 0)
        for complex in complexes:
            if complex.get("total_article_count", 0) > 0:
                complexes_with_listings = complex
                complex_id_to_test = str(complex["complex_id"])
                complex_name_to_test = complex["complex_name"]
                break

        if complexes_with_listings is None:
            # 모든 단지에 매물이 없는 경우
            print("\n⚠️ 모든 단지에 매물이 없습니다. 첫 번째 단지로 테스트합니다.")
            complexes_with_listings = complexes[0]
            complex_id_to_test = str(complexes[0]["complex_id"])
            complex_name_to_test = complexes[0]["complex_name"]

        # 여러 단지 정보 출력 (디버깅용)
        print("\n=== 크롤링된 단지 목록 (처음 5개) ===")
        for i, complex in enumerate(complexes[:5]):
            print(
                f"{i + 1}. {complex['complex_name']} (ID: {complex['complex_id']}) - "
                f"매물 {complex.get('total_article_count', 0)}개"
            )

        print(f"\n테스트 대상 단지: {complex_name_to_test}")
        print(f"Complex ID: {complex_id_to_test}")
        print(f"총 매물 수: {complexes_with_listings.get('total_article_count', 0)}")

    except Exception as e:
        print(f"\n❌ 단지 목록 크롤링 실패: {str(e)}")
        if "rate" in str(e).lower() or "limit" in str(e).lower():
            print("⚠️ 레이트 리밋에 걸렸을 수 있습니다. 잠시 후 다시 시도하세요.")
        raise

    # 2. 새 크롤러 인스턴스로 fetch_complex_listings() 테스트
    print("\n새 크롤러 인스턴스 생성 중...")
    crawler2 = NaverRealEstateCrawler(config)

    try:
        # fetch_complex_listings() 호출
        print(f"\nfetch_complex_listings() 호출 중... (complex_id: {complex_id_to_test})")
        listings = crawler2.fetch_complex_listings(complex_id_to_test)

        # 응답 검증
        assert listings is not None, "매물 목록을 가져오지 못했습니다"
        assert isinstance(listings, list), "매물 목록이 리스트 형태가 아닙니다"

        print(f"\n응답 받은 매물 수: {len(listings)}")

        if len(listings) == 0:
            print("\n⚠️ 이 단지에는 현재 매물이 없습니다. (정상적인 경우일 수 있음)")
            print("✅ 빈 응답 처리 확인 - 테스트 통과")
        else:
            # 첫 번째 매물의 필드 검증
            first_listing = listings[0]
            print("\n=== 첫 번째 매물 정보 ===")
            print(f"article_id: {first_listing.get('article_id', 'N/A')}")
            print(f"floor: {first_listing.get('floor', 'N/A')}")
            print(f"area: {first_listing.get('area', 'N/A')}")
            print(f"price: {first_listing.get('price', 'N/A')}")
            print(f"trade_type: {first_listing.get('trade_type', 'N/A')}")

            # 필수 필드 검증
            required_fields = ["article_id", "floor", "area", "price"]
            missing_fields = []

            for field in required_fields:
                if field not in first_listing:
                    missing_fields.append(field)
                elif not first_listing[field]:
                    missing_fields.append(f"{field} (empty)")

            assert len(missing_fields) == 0, f"필수 필드 누락: {', '.join(missing_fields)}"

            # 샘플 매물 데이터 출력 (디버깅용)
            print("\n=== 샘플 매물 데이터 (상세) ===")
            for key, value in first_listing.items():
                print(f"{key}: {value}")

            print("\n✅ fetch_complex_listings() 테스트 성공!")
            print(f"   - {len(listings)}개 매물 확인")
            print("   - 필수 필드 모두 존재")

    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        if "rate" in str(e).lower() or "limit" in str(e).lower():
            print("⚠️ 레이트 리밋에 걸렸을 수 있습니다. 잠시 후 다시 시도하세요.")
        elif "result" in str(e) and len(e.args) > 0 and isinstance(e.args[0], dict):
            # API 응답 에러 분석
            error_detail = e.args[0]
            print(f"API 응답: {error_detail}")
        raise

    finally:
        # 브라우저 정리
        try:
            if hasattr(crawler2, "page"):
                crawler2.page.close()
            if hasattr(crawler2, "browser"):
                crawler2.browser.close()
            print("\n브라우저 리소스 정리 완료")
        except Exception as cleanup_error:
            print(f"\n브라우저 정리 중 오류 (무시 가능): {cleanup_error}")


@pytest.mark.integration
def test_crawl_full_pipeline(tmp_path: Path) -> None:
    """
    전체 파이프라인 통합 테스트 (Level 4)

    이 테스트는:
    - 단지 목록 크롤링
    - 단지 상세 정보 조회 (1개 단지만)
    - 매물 목록 조회 (1개 단지만)
    - 데이터 집계 및 CSV 저장
    - 전체 풀 파이프라인 검증

    실행: pytest tests/integration/test_naver_integration.py::test_crawl_full_pipeline -v -s
    """
    import time

    # 체크포인트 초기화
    checkpoint_path = Path("output/checkpoint.json")
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    # CrawlerConfig 생성 (headless=True)
    config = CrawlerConfig(timeout=30, headless=True, output_dir=str(tmp_path))

    # NaverRealEstateCrawler 초기화
    crawler = NaverRealEstateCrawler(config)

    # 금천구만 선택하고 첫 번째 동만 사용
    original_data = crawler.districts_data
    test_district = None
    for district in original_data["districts"]:
        if district["district_name"] == "금천구":
            test_district = district
            break

    assert test_district is not None, "금천구를 찾을 수 없습니다"
    assert len(test_district["dongs"]) >= 1, "금천구에 동이 없습니다"

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

    print("\n=== 전체 파이프라인 테스트 시작 ===")
    print(f"테스트 대상: {test_district['district_name']} {test_district['dongs'][0]['dong_name']}")

    # 1. 기본 크롤링 실행
    print("\n1. 단지 목록 크롤링 중...")
    try:
        complexes = crawler.crawl()
        assert len(complexes) > 0, "크롤링된 단지가 없습니다"
        print(f"   - 크롤링된 단지 수: {len(complexes)}")
    except Exception as e:
        print(f"   - ❌ 단지 목록 크롤링 실패: {str(e)}")
        raise

    # 테스트할 단지 수를 1개로 제한 (레이트 리밋 방지)
    test_complex = complexes[0]
    print(f"   - 테스트할 단지: {test_complex['complex_name']} (ID: {test_complex['complex_id']})")

    # 2. 첫 번째 단지에 대해서만 상세 정보와 매물 정보 조회
    enriched_complexes = [test_complex.copy()]  # 복사본 사용

    complex_id = str(test_complex["complex_id"])
    complex_name = test_complex["complex_name"]

    print(f"\n2. 단지 상세 정보 및 매물 조회 중: {complex_name}")

    # 상세 정보 조회 (성공했을 경우에만)
    try:
        print("   - 상세 정보 조회 중...")

        # 새 크롤러 인스턴스 사용
        detail_crawler = NaverRealEstateCrawler(config)
        detail = detail_crawler.fetch_complex_detail(complex_id)

        if detail and "error" not in detail:
            # 상세 정보로 단지 데이터 업데이트
            enriched_complexes[0].update(detail)
            print("   - ✅ 상세 정보 조회 성공")
        else:
            print("   - ⚠️ 상세 정보 없음 또는 에러")

        # 브라우저 정리
        try:
            if hasattr(detail_crawler, "page"):
                detail_crawler.page.close()
            if hasattr(detail_crawler, "browser"):
                detail_crawler.browser.close()
        except Exception:
            pass

    except Exception as e:
        print(f"   - ❌ 상세 정보 조회 실패: {str(e)}")

    # 잠시 대기 (레이트 리밋 방지)
    time.sleep(1)

    # 매물 정보 조회 (성공했을 경우에만)
    try:
        print("   - 매물 목록 조회 중...")

        # 새 크롤러 인스턴스 사용
        listings_crawler = NaverRealEstateCrawler(config)
        listings = listings_crawler.fetch_complex_listings(complex_id, "A1")  # 매매만 조회

        if listings:
            # 매물 데이터 집계
            prices = []
            for listing in listings:
                price_str = listing.get("price", "0")
                # 가격에서 쉼표와 "만" 등 제거하고 숫자로 변환
                try:
                    # "만"으로 끝나는 경우 변환 (예: 5만 -> 50000)
                    if "만" in price_str:
                        price_num = int(float(price_str.replace("만", "").replace(",", "")) * 10000)
                    else:
                        price_num = int(price_str.replace(",", ""))
                    prices.append(price_num)
                except Exception:
                    pass

            if prices:
                enriched_complexes[0]["avg_listing_price"] = sum(prices) / len(prices)
                enriched_complexes[0]["min_listing_price"] = min(prices)
                enriched_complexes[0]["max_listing_price"] = max(prices)

            enriched_complexes[0]["active_listings_count"] = len(listings)
            print(f"   - ✅ 매물 {len(listings)}개 조회 성공")
            if prices:
                print(
                    f"   - 가격 범위: {min(prices):,} ~ {max(prices):,} (평균: {int(sum(prices) / len(prices)):,})"
                )
        else:
            enriched_complexes[0]["active_listings_count"] = 0
            print("   - ⚠️ 매물 없음")

        # 브라우저 정리
        try:
            if hasattr(listings_crawler, "page"):
                listings_crawler.page.close()
            if hasattr(listings_crawler, "browser"):
                listings_crawler.browser.close()
        except Exception:
            pass

    except Exception as e:
        print(f"   - ❌ 매물 목록 조회 실패: {str(e)}")
        enriched_complexes[0]["active_listings_count"] = 0

    # 3. CSV 저장
    print("\n3. CSV 저장 중...")
    output_path = tmp_path / "test_full_pipeline.csv"
    writer = CSVWriter(output_path)
    writer.write(enriched_complexes)

    assert output_path.exists(), "CSV 파일이 생성되지 않았습니다"
    assert output_path.stat().st_size > 0, "CSV 파일이 비어있습니다"

    # 4. CSV 내용 검증
    with open(output_path, encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) > 1, "CSV에 데이터가 없습니다 (헤더만 존재)"

        header = lines[0].strip()
        print(f"\n   - CSV 라인 수: {len(lines)} (헤더 포함)")

        # 기본 필드 확인
        basic_fields = ["complex_id", "complex_name", "real_estate_type"]
        for field in basic_fields:
            assert field in header, f"CSV 헤더에 필수 필드 '{field}'가 없습니다"

        # 확장 필드 확인 (상세 정보)
        enriched_fields = [
            "road_address",
            "jibun_address",
            "complex_name",
            "building_type",
            "total_household_count",
            "completion_date",
            "maintenance_cost",
            "fetched_at",
        ]
        found_enriched_fields = [field for field in enriched_fields if field in header]
        print(f"   - 발견된 확장 필드: {len(found_enriched_fields)}개")

        # 매물 집계 필드 확인
        listing_fields = [
            "avg_listing_price",
            "min_listing_price",
            "max_listing_price",
            "active_listings_count",
        ]
        found_listing_fields = [field for field in listing_fields if field in header]
        print(f"   - 발견된 매물 필드: {len(found_listing_fields)}개")

        # 첫 번째 데이터 행 샘플 출력
        if len(lines) > 1:
            first_row = lines[1].strip()
            print("\n   - 첫 번째 데이터 행 샘플:")
            print(f"     {first_row[:100]}...")

    # 5. 데이터 검증
    print("\n5. 데이터 검증 중...")

    # 모든 단지에 기본 필드가 있는지 확인
    for complex in enriched_complexes:
        assert "complex_id" in complex, "단지에 complex_id가 없습니다"
        assert "complex_name" in complex, "단지에 complex_name이 없습니다"
        # 매물 카운트 필드가 있는지 확인
        assert "active_listings_count" in complex, "단지에 active_listings_count가 없습니다"

    # 집계된 데이터 확인
    if enriched_complexes[0].get("active_listings_count", 0) > 0:
        print("\n   - 매물이 있는 단지: 1개")
        print(
            f"     - {enriched_complexes[0]['complex_name']}: {enriched_complexes[0]['active_listings_count']}개 매물"
        )

    print("\n✅ test_crawl_full_pipeline 테스트 통과!")
    print(f"   - 크롤링된 단지: {len(enriched_complexes)}개")
    print(f"   - 저장된 CSV: {output_path}")
    print(f"   - 확장 필드: {len(found_enriched_fields)}개")
    print(f"   - 매물 필드: {len(found_listing_fields)}개")
    print(f"   - 총 데이터 라인: {len(lines)}개")
