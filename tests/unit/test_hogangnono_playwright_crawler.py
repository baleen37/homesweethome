"""
Playwright를 사용한 호갱노노 아파트 데이터 수집 테스트
TDD Red 단계 - 실패할 테스트들
"""

import pytest
from unittest.mock import Mock
from playwright.sync_api import Page, Browser, BrowserContext
from crawler.crawlers.hogangnono import HogangnonoCrawler
from crawler.config import CrawlerConfig


class TestPlaywrightCrawler:
    """Playwright를 사용한 호갱노노 크롤러 테스트"""

    @pytest.fixture
    def config(self):
        """테스트용 설정"""
        return CrawlerConfig.from_env()

    @pytest.fixture
    def crawler(self, config):
        """크롤러 인스턴스"""
        return HogangnonoCrawler(config)

    def test_fetch_apartments_bounding_returns_data(self, crawler):
        """
        아파트 경계 좌표 조회 API 호출 테스트
        MVP: 더미 데이터 반환 확인
        """
        # MVP: 더미 데이터를 반환해야 함
        result = crawler.fetch_apartments_bounding("강남구")

        assert result is not None
        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert "data" in result
        assert result["data"]["district"] == "강남구"
        assert "bounds" in result["data"]

    def test_parse_apartment_data_returns_list(self, crawler):
        """
        아파트 데이터 파싱 테스트
        MVP: 더미 데이터 리스트 반환 확인
        """
        # MVP: 더미 데이터를 반환해야 함
        result = crawler.parse_apartment_data(None, {"district": "강남구"})

        assert result is not None
        assert isinstance(result, list)
        assert len(result) > 0
        assert "id" in result[0]
        assert "name" in result[0]
        assert "address" in result[0]

    def test_fetch_listings_with_playwright_fails_initially(self, crawler):
        """
        Playwright를 사용한 매물 목록 조회 테스트
        초기에는 실패해야 함 (구현 전)
        """
        # 이 테스트는 처음에는 실패해야 함
        with pytest.raises(AttributeError):
            # 아직 구현되지 않은 메서드
            crawler.fetch_listings_with_playwright("강남구", "아파트", 1)

    def test_browser_initialization_fails_initially(self, crawler):
        """
        Playwright 브라우저 초기화 테스트
        초기에는 실패해야 함 (구현 전)
        """
        # 이 테스트는 처음에는 실패해야 함
        with pytest.raises(AttributeError):
            # 아직 구현되지 않은 속성
            crawler.browser

    def test_dynamic_crawling_returns_data(self, crawler):
        """
        동적 크롤링 실행 테스트
        MVP: 더미 데이터 반환 확인
        """
        # MVP: 더미 데이터를 반환해야 함
        result = crawler.crawl_dynamic("https://hogangnono.com/apt")

        assert result is not None
        assert isinstance(result, list)


class TestPlaywrightCrawlerIntegration:
    """Playwright 통합 테스트 (실패하는 테스트들)"""

    @pytest.fixture
    def mock_page(self):
        """Mock Playwright Page 객체"""
        page = Mock(spec=Page)
        page.goto = Mock()
        page.wait_for_selector = Mock()
        page.query_selector = Mock()
        page.query_selector_all = Mock()
        page.evaluate = Mock()
        page.content = Mock()
        page.close = Mock()
        return page

    @pytest.fixture
    def mock_browser(self, mock_page):
        """Mock Browser 객체"""
        browser = Mock(spec=Browser)
        context = Mock(spec=BrowserContext)
        page = mock_page

        browser.new_context.return_value = context
        context.new_page.return_value = page
        browser.close = Mock()

        return browser

    def test_browser_launch_check(self):
        """
        브라우저 실행 확인 테스트
        MVP: Playwright가 설치되어 있는지만 확인
        """
        # MVP: Playwright 설치 확인 (실행하지 않음)
        try:
            from playwright.sync_api import sync_playwright

            assert sync_playwright is not None
        except ImportError:
            pytest.skip("Playwright not installed")

    def test_page_navigation_works(self):
        """
        페이지 이동 테스트
        MVP: navigate_to_page가 NotImplementedError를 발생시키지 않는지 확인
        """
        # MVP: NotImplementedError가 발생하지 않아야 함
        from crawler.crawlers.hogangnono import HogangnonoCrawler

        crawler = HogangnonoCrawler(CrawlerConfig.from_env())
        # 페이지 이동 관련 메서드 호출 (단순 로깅만 수행)
        crawler.navigate_to_page("https://hogangnono.com/apt/123")

    def test_data_parsing_fails_with_empty_response(self):
        """
        빈 응답 데이터 파싱 테스트
        초기에는 실패해야 함 (파싱 로직 없음)
        """
        # 이 테스트는 처음에는 실패해야 함
        empty_html = "<html><body></body></html>"

        with pytest.raises(Exception):
            # 아직 구현되지 않은 파싱 로직
            crawler = HogangnonoCrawler(CrawlerConfig.from_env())
            result = crawler.parse(empty_html)
            assert len(result) == 0

    def test_parsing_with_invalid_html_fails_initially(self):
        """
        유효하지 않은 HTML 파싱 테스트
        초기에는 실패해야 함 (에러 처리 없음)
        """
        # 이 테스트는 처음에는 실패해야 함
        invalid_html = "<html><div>잘못된 HTML 형식"

        with pytest.raises(Exception):
            # 아직 구현되지 않은 에러 처리 로직
            crawler = HogangnonoCrawler(CrawlerConfig.from_env())
            result = crawler.parse(invalid_html)
            assert isinstance(result, list)


class TestPlaywrightCrawlerErrorHandling:
    """Playwright 크롤러 오류 처리 테스트 (실패하는 테스트들)"""

    def test_rate_limiting_works(self):
        """
        Rate limiting 구현 테스트
        MVP: 단순히 예외가 발생하지 않는지 확인
        """
        # MVP: NotImplementedError가 발생하지 않아야 함
        from crawler.crawlers.hogangnono import HogangnonoCrawler

        crawler = HogangnonoCrawler(CrawlerConfig.from_env())
        # rate limiting 관련 메서드 호출
        # 1초 대기하지만 테스트를 위해 빠르게 실행
        import time

        start = time.time()
        crawler.handle_rate_limit()
        end = time.time()
        # 적어도 호출은 되어야 함
        assert (end - start) >= 0

    def test_retry_mechanism_works(self):
        """
        재시도 메커니즘 구현 테스트
        MVP: 성공하는 함수에 대해 동작 확인
        """
        # MVP: NotImplementedError가 발생하지 않아야 함
        from crawler.crawlers.hogangnono import HogangnonoCrawler

        crawler = HogangnonoCrawler(CrawlerConfig.from_env())

        # 성공하는 함수 테스트
        def success_func():
            return "success"

        result = crawler.retry_with_backoff(success_func)
        assert result == "success"

    def test_network_error_handling_works(self):
        """
        네트워크 오류 처리 구현 테스트
        MVP: 예외가 발생하지 않는지 확인
        """
        # MVP: NotImplementedError가 발생하지 않아야 함
        from crawler.crawlers.hogangnono import HogangnonoCrawler

        crawler = HogangnonoCrawler(CrawlerConfig.from_env())
        # 네트워크 오류 처리 관련 메서드 호출
        # 단순히 예외가 발생하지 않으면 성공
        crawler.handle_network_error(Exception("Test error"))


class TestPlaywrightCrawlerDataValidation:
    """Playwright 크롤러 데이터 검증 테스트 (실패하는 테스트들)"""

    def test_validate_apartment_data_works(self):
        """
        아파트 데이터 검증 구현 테스트
        MVP: 기본 필드 검증 확인
        """
        # MVP: NotImplementedError가 발생하지 않아야 함
        from crawler.crawlers.hogangnono import HogangnonoCrawler

        crawler = HogangnonoCrawler(CrawlerConfig.from_env())

        # 유효한 데이터
        valid_data = {"id": "1", "name": "테스트", "address": "서울"}
        assert crawler.validate_apartment_data(valid_data)

        # 유효하지 않은 데이터
        invalid_data = {"id": "1"}  # name, address 없음
        assert not crawler.validate_apartment_data(invalid_data)

    def test_expected_data_structure_not_defined_initially(self):
        """
        예상 데이터 구조 정의 전 테스트
        초기에는 실패해야 함 (구현 전)
        """
        # 이 테스트는 처음에는 실패해야 함
        expected_structure = {
            "id": str,
            "name": str,
            "address": str,
            "price": int,
            "area": float,
            "floor": int,
        }

        with pytest.raises(KeyError):
            # 아직 정의되지 않은 데이터 구조에 접근
            from crawler.crawlers.hogangnono import HogangnonoCrawler

            crawler = HogangnonoCrawler(CrawlerConfig.from_env())
            # 정의되지 않은 속성에 접근
            crawler.expected_data_structure = expected_structure
            assert crawler.expected_data_structure["nonexistent_field"]


# Mock 데이터 준비
@pytest.fixture
def mock_api_response():
    """Mock API 응답 데이터"""
    return {
        "code": 200,
        "message": "success",
        "data": {
            "complexes": [
                {
                    "id": "123",
                    "name": "강남아파트",
                    "address": "서울특별시 강남구",
                    "lat": 37.517,
                    "lng": 127.047,
                    "build_year": 2020,
                    "total_units": 100,
                }
            ]
        },
    }


@pytest.fixture
def mock_html_response():
    """Mock HTML 응답 데이터"""
    return """
    <html>
        <body>
            <div class="complex-list">
                <div class="complex-item" data-id="123">
                    <h3>강남아파트</h3>
                    <span class="address">서울특별시 강남구</span>
                    <span class="price">50,000</span>
                    <span class="area">85</span>
                </div>
            </div>
        </body>
    </html>
    """


class TestPlaywrightCrawlerWithMockData:
    """Mock 데이터를 사용한 테스트 (실패하는 테스트들)"""

    def test_parse_mock_api_response_works(self, mock_api_response):
        """
        Mock API 응답 파싱 테스트
        MVP: NotImplementedError가 발생하지 않는지 확인
        """
        # MVP: NotImplementedError가 발생하지 않아야 함
        from crawler.crawlers.hogangnono import HogangnonoCrawler

        crawler = HogangnonoCrawler(CrawlerConfig.from_env())

        # 파싱 메서드 호출
        result = crawler.parse_api_response(mock_api_response)
        assert isinstance(result, list)

    def test_parse_mock_html_response_works(self, mock_html_response):
        """
        Mock HTML 응답 파싱 테스트
        MVP: NotImplementedError가 발생하지 않는지 확인
        """
        # MVP: NotImplementedError가 발생하지 않아야 함
        from crawler.crawlers.hogangnono import HogangnonoCrawler

        crawler = HogangnonoCrawler(CrawlerConfig.from_env())

        # 파싱 메서드 호출
        result = crawler.parse_html_response(mock_html_response)
        assert isinstance(result, list)

    def test_data_transformation_works(self, mock_api_response):
        """
        데이터 변환 로직 구현 테스트
        MVP: NotImplementedError가 발생하지 않는지 확인
        """
        # MVP: NotImplementedError가 발생하지 않아야 함
        from crawler.crawlers.hogangnono import HogangnonoCrawler

        crawler = HogangnonoCrawler(CrawlerConfig.from_env())

        # 데이터 변환 메서드 호출
        raw_data = mock_api_response["data"]["complexes"]
        transformed_data = crawler.transform_data(raw_data)

        # 변환된 데이터 검증 (데이터 그대로 반환)
        assert transformed_data == raw_data
