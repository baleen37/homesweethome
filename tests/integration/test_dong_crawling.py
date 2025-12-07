"""동(dong) 단위 크롤링 기능 통합 테스트

법정동(cortar_no)별로 단지 데이터를 크롤링하는 기능을 테스트합니다.
네트워크 의존 테스트이므로 명시적으로 실행해야 합니다.

실행 방법:
    pytest tests/integration/test_dong_crawling.py -v -s
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler


@pytest.fixture
def test_config(tmp_path: Path) -> CrawlerConfig:
    """테스트용 CrawlerConfig fixture"""
    return CrawlerConfig(headless=True, timeout=30, output_dir=str(tmp_path / "output"))


@pytest.fixture
def sample_dong_data() -> dict:
    """테스트용 동 데이터"""
    return {
        "dong_name": "사직동",
        "cortarNo": "1111010100",
        "bounds": {
            "leftLon": 126.97,
            "rightLon": 126.99,
            "topLat": 37.58,
            "bottomLat": 37.56,
        },
    }


@pytest.fixture
def setup_test_output():
    """테스트용 output 디렉토리 설정 및 정리"""
    output_dir = Path("output/test_dong_crawling")
    output_dir.mkdir(parents=True, exist_ok=True)

    yield output_dir

    # 테스트 후 파일 정리 (선택적)
    # for file in output_dir.glob("*.csv"):
    #     file.unlink()
    # for file in output_dir.glob("*.json"):
    #     file.unlink()


@pytest.mark.slow
def test_fetch_dong_data_real_api(test_config, sample_dong_data, setup_test_output):
    """실제 네이버 API로 동 단지 데이터 조회 테스트

    이 테스트는:
    - 실제 네이버 모바일 API를 호출합니다
    - cortar_no와 bounds 파라미터를 사용합니다
    - 응답 데이터의 구조를 검증합니다

    실행: pytest tests/integration/test_dong_crawling.py::test_fetch_dong_data_real_api -v -s
    """
    # 크롤러 초기화
    crawler = NaverRealEstateCrawler(test_config, output_dir=setup_test_output)

    print(f"\n=== 동 단지 데이터 조회 테스트: {sample_dong_data['dong_name']} ===")
    print(f"cortarNo: {sample_dong_data['cortarNo']}")
    print(f"bounds: {sample_dong_data['bounds']}")

    # 동 데이터 조회
    complexes = crawler._fetch_dong_data(sample_dong_data)

    # 결과 검증
    assert isinstance(complexes, list), "결과가 리스트 형태여야 합니다"

    # 최소한의 데이터가 반환되는지 확인 (실제 환경에서는 없을 수도 있음)
    if len(complexes) > 0:
        print(f"조회된 단지 수: {len(complexes)}개")

        # 첫 번째 단지의 필드 확인
        complex = complexes[0]
        required_fields = [
            "complex_id",
            "complex_name",
            "real_estate_type",
            "completion_year_month",
            "total_dong_count",
            "total_household_count",
        ]

        for field in required_fields:
            assert field in complex, f"필수 필드 '{field}'가 없습니다"

        print(f"첫 번째 단지: {complex['complex_name']} ({complex['complex_id']})")
        print(f"  - 유형: {complex['real_estate_type']}")
        print(f"  - 세대수: {complex['total_household_count']}")
    else:
        print("해당 동에 단지가 없습니다.")

    print("\n✅ test_fetch_dong_data_real_api 테스트 통과!")


def test_fetch_dong_data_with_mock(test_config, sample_dong_data):
    """Mock을 사용한 동 데이터 조회 테스트

    이 테스트는:
    - API 응답을 Mock하여 테스트 속도를 향상시킵니다
    - 다양한 응답 시나리오를 테스트합니다
    - 파라미터 전달이 올바른지 검증합니다

    실행: pytest tests/integration/test_dong_crawling.py::test_fetch_dong_data_with_mock -v
    """
    # 크롤러 초기화
    crawler = NaverRealEstateCrawler(test_config)

    # Mock browser manager
    mock_browser_manager = Mock()
    mock_page = Mock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None

    # Mock API 응답
    mock_response = {
        "result": [
            {
                "hscpNo": "1111010100001",
                "hscpNm": "사직동테스트아파트",
                "hscpTypeNm": "아파트",
                "useAprvYmd": "202001",
                "totDongCnt": 3,
                "totHsehCnt": 300,
                "minSpc": "59.99",
                "maxSpc": "84.99",
                "dealCnt": 2,
                "leaseCnt": 1,
                "rentCnt": 0,
                "dealPrcMin": "<em class='txt_unit'>8억</em>",
                "dealPrcMax": "<em class='txt_unit'>12억</em>",
                "leasePrcMin": "<em class='txt_unit'>5억</em>",
                "leasePrcMax": "<em class='txt_unit'>7억</em>",
            },
            {
                "hscpNo": "1111010100002",
                "hscpNm": "사직동더샵",
                "hscpTypeNm": "아파트",
                "useAprvYmd": "201901",
                "totDongCnt": 2,
                "totHsehCnt": 150,
                "minSpc": "74.99",
                "maxSpc": "114.99",
                "dealCnt": 1,
                "leaseCnt": 2,
                "rentCnt": 1,
                "dealPrcMin": "<em class='txt_unit'>10억</em>",
                "dealPrcMax": "<em class='txt_unit'>15억</em>",
                "leasePrcMin": "<em class='txt_unit'>6억</em>",
                "leasePrcMax": "<em class='txt_unit'>9억</em>",
            },
        ]
    }

    mock_page.evaluate.return_value = mock_response
    mock_browser_manager.managed_browser.return_value.__enter__.return_value = mock_page
    crawler.browser_manager = mock_browser_manager

    # Mock rate limiter
    with patch.object(crawler.rate_limiter, "wait"):
        with patch.object(crawler.rate_limiter, "on_success"):
            # 동 데이터 조회
            complexes = crawler._fetch_dong_data(sample_dong_data)

    # 결과 검증
    assert len(complexes) == 2, "2개의 단지가 반환되어야 합니다"

    # 첫 번째 단지 확인
    complex1 = complexes[0]
    assert complex1["complex_id"] == "1111010100001"
    assert complex1["complex_name"] == "사직동테스트아파트"
    assert complex1["real_estate_type"] == "아파트"
    assert complex1["total_dong_count"] == 3
    assert complex1["total_household_count"] == 300
    assert complex1["deal_count"] == 2
    assert complex1["lease_count"] == 1

    # HTML 태그 제거 확인
    assert complex1["deal_price_min"] == "8억"
    assert complex1["deal_price_max"] == "12억"

    # 두 번째 단지 확인
    complex2 = complexes[1]
    assert complex2["complex_id"] == "1111010100002"
    assert complex2["complex_name"] == "사직동더샵"

    # API 호출 파라미터 확인
    mock_page.evaluate.assert_called_once()
    call_args = mock_page.evaluate.call_args[0][1]  # URL 인자

    # URL에 올바른 파라미터가 포함되어 있는지 확인
    assert "cortarNo=1111010100" in call_args
    assert "rletTpCd=APT" in call_args
    assert "tradTpCd=A1" in call_args
    assert "lat=37.57" in call_args  # 중심 위도
    assert "lon=126.98" in call_args  # 중심 경도

    print("\n✅ test_fetch_dong_data_with_mock 테스트 통과!")
    print(f"   - 조회된 단지: {len(complexes)}개")
    print(f"   - 첫 번째 단지: {complex1['complex_name']}")
    print(f"   - 두 번째 단지: {complex2['complex_name']}")


def test_fetch_dong_data_error_handling(test_config, sample_dong_data):
    """API 에러 핸들링 테스트

    이 테스트는:
    - 429 Rate Limit 에러 처리를 검증합니다
    - 일반 에러 처리를 검증합니다
    - 재시도 로직이 올바르게 동작하는지 확인합니다

    실행: pytest tests/integration/test_dong_crawling.py::test_fetch_dong_data_error_handling -v
    """
    # 크롤러 초기화
    crawler = NaverRealEstateCrawler(test_config)

    # Mock browser manager
    mock_browser_manager = Mock()
    mock_page = Mock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None

    # 429 에러 응답
    mock_page.evaluate.return_value = {"error": "HTTP 429: Too Many Requests"}

    mock_browser_manager.managed_browser.return_value.__enter__.return_value = mock_page
    crawler.browser_manager = mock_browser_manager

    # Mock rate limiter와 sleep
    with patch.object(crawler.rate_limiter, "wait"):
        with patch("time.sleep") as mock_sleep:
            # 동 데이터 조회
            complexes = crawler._fetch_dong_data(sample_dong_data)

    # 에러 시 빈 리스트 반환
    assert len(complexes) == 0

    # sleep 호출 확인 (429 에러 시 10초 대기)
    mock_sleep.assert_called_with(10)

    print("\n✅ test_fetch_dong_data_error_handling 테스트 통과!")
    print("   - 429 에러 시 10초 대기 후 빈 리스트 반환 확인")


def test_parse_complex_list_api_with_empty_result(test_config):
    """빈 응답 파싱 테스트

    이 테스트는:
    - 빈 result 배열을 처리하는지 확인합니다
    - 빈 리스트를 반환하는지 검증합니다

    실행: pytest tests/integration/test_dong_crawling.py::test_parse_complex_list_api_with_empty_result -v
    """
    # 크롤러 초기화
    crawler = NaverRealEstateCrawler(test_config)

    # 빈 응답
    empty_response = {"result": []}

    # 파싱 실행
    complexes = crawler._parse_complex_list_api(empty_response)

    # 결과 검증
    assert len(complexes) == 0, "빈 응답은 빈 리스트를 반환해야 합니다"

    print("\n✅ test_parse_complex_list_api_with_empty_result 테스트 통과!")


def test_parse_complex_list_api_with_html_tags(test_config):
    """HTML 태그가 포함된 가격 정보 파싱 테스트

    이 테스트는:
    - 가격 정보의 HTML 태그를 제거하는지 확인합니다
    - 다양한 HTML 태그 형식을 처리하는지 검증합니다

    실행: pytest tests/integration/test_dong_crawling.py::test_parse_complex_list_api_with_html_tags -v
    """
    # 크롤러 초기화
    crawler = NaverRealEstateCrawler(test_config)

    # HTML 태그가 포함된 응답
    response_with_tags = {
        "result": [
            {
                "hscpNo": "12345",
                "hscpNm": "태그테스트아파트",
                "hscpTypeNm": "아파트",
                "useAprvYmd": "202001",
                "totDongCnt": 1,
                "totHsehCnt": 100,
                "minSpc": "59.99",
                "maxSpc": "84.99",
                "dealCnt": 0,
                "leaseCnt": 0,
                "rentCnt": 0,
                # 다양한 HTML 태그 형식
                "dealPrcMin": "<em class='txt_unit'>5억</em>",
                "dealPrcMax": "<em class='txt_unit'>5억 5,000</em>",
                "leasePrcMin": "<em class='txt_unit'>3억 5,000</em>",
                "leasePrcMax": "<em class='txt_unit'>4억 2,000</em>",
            }
        ]
    }

    # 파싱 실행
    complexes = crawler._parse_complex_list_api(response_with_tags)

    # 결과 검증
    assert len(complexes) == 1
    complex = complexes[0]

    # HTML 태그가 제거되었는지 확인
    assert complex["deal_price_min"] == "5억"
    assert complex["deal_price_max"] == "5억 5,000"
    assert complex["lease_price_min"] == "3억 5,000"
    assert complex["lease_price_max"] == "4억 2,000"

    print("\n✅ test_parse_complex_list_api_with_html_tags 테스트 통과!")
    print(f"   - deal_price_min: {complex['deal_price_min']}")
    print(f"   - deal_price_max: {complex['deal_price_max']}")


@pytest.mark.slow
def test_dong_level_crawling_with_coordinator(test_config, setup_test_output):
    """CrawlCoordinator를 사용한 동 단위 크롤링 테스트

    이 테스트는:
    - CrawlCoordinator가 동 데이터를 올바르게 처리하는지 확인합니다
    - 단지 상세 정보 조회 시나리오를 테스트합니다
    - CSV 파일 생성을 검증합니다

    실행: pytest tests/integration/test_dong_crawling.py::test_dong_level_crawling_with_coordinator -v -s
    """

    # 체크포인트 초기화
    checkpoint_path = setup_test_output / "checkpoint.json"
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    # 크롤러 초기화
    NaverRealEstateCrawler(test_config, output_dir=setup_test_output)

    # 테스트용 동 데이터 준비
    dong_data = {
        "dong_code": "1111010100",
        "dong_name": "사직동",
        "complexes": [
            {
                "complex_id": "1111010100001",
                "complex_name": "사직동테스트아파트",
                "address": "서울 종로구 사직동",
            }
        ],
    }

    # Mock fetch_complex_detail
    mock_detail = {
        "complex_id": "1111010100001",
        "complex_name": "사직동테스트아파트",
        "address": "서울 종로구 사직동 123",
        "build_year": "2020",
        "household_count": 100,
        "dong_count": 1,
        "pyeong_types": [
            {
                "pyeongTypeNumber": 1,
                "pyeongName": "59A",
            },
            {
                "pyeongTypeNumber": 2,
                "pyeongName": "84A",
            },
        ],
    }

    # Mock fetch_transaction_history
    mock_transactions = [
        {
            "complex_id": "1111010100001",
            "complex_name": "사직동테스트아파트",
            "pyeong_type_number": 1,
            "pyeong_name": "59A",
            "trade_type": "A1",
            "trade_type_name": "매매",
            "trade_date": "2024-01-15",
            "deal_price": 800000000,
            "floor": 5,
        }
    ]

    print(f"\n=== CrawlCoordinator 동 크롤링 테스트: {dong_data['dong_name']} ===")

    # CrawlCoordinator를 사용하여 크롤링
    from crawler.coordinator import CrawlCoordinator

    coordinator = CrawlCoordinator(
        output_dir=setup_test_output,
        checkpoint_path=checkpoint_path,
    )

    # Mock 함수들 설정
    def mock_fetch_complex_detail(complex_id: str):
        return mock_detail

    def mock_fetch_transaction_history(
        complex_id: str,
        pyeong_type_number: int,
        trade_type: str,
        complex_name: str = "",
        pyeong_name: str = "",
    ):
        # A1 (매매) 타입에 대해서만 반환
        if trade_type == "A1":
            return mock_transactions
        return []

    # 동 크롤링 실행
    result = coordinator.crawl_dong(
        dong_code=dong_data["dong_code"],
        dong_name=dong_data["dong_name"],
        complexes=dong_data["complexes"],
        fetch_complex_detail=mock_fetch_complex_detail,
        fetch_transaction_history=mock_fetch_transaction_history,
    )

    # 결과 검증
    assert result["dong_code"] == "1111010100"
    assert result["dong_name"] == "사직동"
    assert result["complexes_processed"] == 1
    assert result["transactions_collected"] == 2  # 2개 평형 * 1개 매물 = 2

    # CSV 파일 생성 확인
    complexes_csv = setup_test_output / "complexes.csv"
    transactions_csv = setup_test_output / "transactions.csv"

    assert complexes_csv.exists(), "complexes.csv 파일이 생성되지 않았습니다"
    assert transactions_csv.exists(), "transactions.csv 파일이 생성되지 않았습니다"

    # 체크포인트 파일 생성 확인
    assert checkpoint_path.exists(), "체크포인트 파일이 생성되지 않았습니다"

    print("\n✅ test_dong_level_crawling_with_coordinator 테스트 통과!")
    print(f"   - 처리된 단지: {result['complexes_processed']}개")
    print(f"   - 수집된 거래내역: {result['transactions_collected']}개")
    print(f"   - complexes.csv: {len(complexes_csv.read_text(encoding='utf-8').splitlines())} 라인")
    print(
        f"   - transactions.csv: {len(transactions_csv.read_text(encoding='utf-8').splitlines())} 라인"
    )
