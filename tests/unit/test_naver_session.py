"""네이버 크롤러 세션 확보 로직 테스트"""

import pytest
from unittest.mock import Mock, patch
import time

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler


class TestNaverSessionManagement:
    """네이버 크롤러 세션 관리 기능 테스트"""

    @pytest.fixture
    def config(self):
        """테스트용 설정 객체"""
        return CrawlerConfig(
            timeout=30,  # 30초로 수정 (300 이하)
            max_retries=3,
            delay=5.0,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        )

    @pytest.fixture
    def crawler(self, config):
        """테스트용 크롤러 객체"""
        # output_dir를 임시 디렉토리로 설정
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            yield NaverRealEstateCrawler(config, output_dir=tmpdir)

    def test_ensure_session_method_should_exist(self, crawler):
        """_ensure_session 메서드가 존재해야 함"""
        assert hasattr(crawler, "_ensure_session")
        assert callable(getattr(crawler, "_ensure_session"))

    @patch("crawler.crawlers.naver.BrowserManager")
    def test_ensure_session_waits_for_networkidle(self, mock_browser_manager, crawler):
        """세션 확보 시 networkidle 상태를 대기해야 함"""
        # Mock 설정
        mock_response = Mock()
        mock_response.status = 200
        mock_page = Mock()
        mock_page.goto = Mock(return_value=mock_response)
        mock_page.wait_for_load_state = Mock()
        mock_page.wait_for_function = Mock()
        mock_page.context = Mock()
        mock_page.context.cookies = Mock(return_value=[])

        mock_browser_manager.return_value.managed_browser.return_value.__enter__.return_value = (
            mock_page
        )

        # _refresh_session 모의
        with patch.object(crawler, "_refresh_session"):
            # _ensure_session 메서드 호출
            crawler._ensure_session(mock_page)

        # networkidle 대기 확인
        mock_page.wait_for_load_state.assert_any_call("networkidle", timeout=10000)

    @patch("crawler.crawlers.naver.BrowserManager")
    def test_ensure_session_waits_sufficient_time(self, mock_browser_manager, crawler):
        """세션 확보 후 충분한 대기 시간을 가져야 함 (10초)"""
        # Mock 설정
        mock_response = Mock()
        mock_response.status = 200
        mock_page = Mock()
        mock_page.goto = Mock(return_value=mock_response)
        mock_page.wait_for_load_state = Mock()
        mock_page.wait_for_function = Mock()
        mock_page.context = Mock()
        mock_page.context.cookies = Mock(return_value=[])

        mock_browser_manager.return_value.managed_browser.return_value.__enter__.return_value = (
            mock_page
        )

        # _refresh_session 모의
        with patch.object(crawler, "_refresh_session"):
            # 시작 시간 기록
            start_time = time.time()

            # _ensure_session 메서드 호출
            crawler._ensure_session(mock_page)

            # 경과 시간 확인 (최소 10초 대기)
            elapsed_time = time.time() - start_time
            assert elapsed_time >= 10.0, f"대기 시간이 10초보다 짧음: {elapsed_time:.2f}초"

    @patch("crawler.crawlers.naver.BrowserManager")
    def test_ensure_session_sets_proper_user_agent(self, mock_browser_manager, crawler):
        """적절한 User-Agent를 설정해야 함"""
        # Mock 설정
        mock_page = Mock()
        mock_page.goto = Mock()
        mock_page.wait_for_load_state = Mock()
        mock_page.set_extra_http_headers = Mock()
        mock_page.wait_for_function = Mock()

        mock_browser_manager.return_value.managed_browser.return_value.__enter__.return_value = (
            mock_page
        )

        # _ensure_session 메서드 호출
        crawler._ensure_session(mock_page)

        # User-Agent 설정 확인
        mock_page.set_extra_http_headers.assert_called_once()
        headers = mock_page.set_extra_http_headers.call_args[0][0]
        assert "User-Agent" in headers
        assert "iPhone" in headers["User-Agent"]
        assert "Mobile" in headers["User-Agent"]

    @patch("crawler.crawlers.naver.BrowserManager")
    def test_ensure_session_checks_document_ready_state(self, mock_browser_manager, crawler):
        """문서의 readyState를 확인해야 함"""
        # Mock 설정
        mock_page = Mock()
        mock_page.goto = Mock()
        mock_page.wait_for_load_state = Mock()
        mock_page.wait_for_function = Mock()

        mock_browser_manager.return_value.managed_browser.return_value.__enter__.return_value = (
            mock_page
        )

        # _ensure_session 메서드 호출
        crawler._ensure_session(mock_page)

        # document readyState 확인
        mock_page.wait_for_function.assert_called_once_with(
            """() => document.readyState === 'complete'""", timeout=30000
        )

    @patch("crawler.crawlers.naver.BrowserManager")
    def test_ensure_session_fails_on_timeout(self, mock_browser_manager, crawler):
        """타임아웃 시 예외가 발생해야 함"""
        # Mock 설정
        mock_page = Mock()
        mock_page.goto = Mock()
        mock_page.wait_for_load_state = Mock(side_effect=Exception("Timeout"))

        mock_browser_manager.return_value.managed_browser.return_value.__enter__.return_value = (
            mock_page
        )

        # 예외 발생 확인
        with pytest.raises(Exception, match="Timeout"):
            crawler._ensure_session(mock_page)

    @patch("crawler.crawlers.naver.BrowserManager")
    def test_ensure_session_navigates_to_correct_url(self, mock_browser_manager, crawler):
        """올바른 URL로 이동해야 함"""
        # Mock 설정
        mock_page = Mock()
        mock_page.goto = Mock()
        mock_page.wait_for_load_state = Mock()
        mock_page.wait_for_function = Mock()

        mock_browser_manager.return_value.managed_browser.return_value.__enter__.return_value = (
            mock_page
        )

        # _ensure_session 메서드 호출
        crawler._ensure_session(mock_page)

        # URL 확인
        mock_page.goto.assert_called_once_with(
            "https://m.land.naver.com/complexes", wait_until="domcontentloaded", timeout=30000
        )

    @patch("crawler.crawlers.naver.BrowserManager")
    @patch("time.sleep")
    def test_ensure_session_handles_ready_state_incomplete(
        self, mock_sleep, mock_browser_manager, crawler
    ):
        """readyState가 complete가 아닐 경우 처리해야 함"""
        # Mock 설정
        mock_page = Mock()
        mock_page.goto = Mock()
        mock_page.wait_for_load_state = Mock()
        mock_page.wait_for_function = Mock()
        # wait_for_function은 성공한다고 가정 (timeout 없음)

        mock_browser_manager.return_value.managed_browser.return_value.__enter__.return_value = (
            mock_page
        )

        # _ensure_session 메서드 호출
        crawler._ensure_session(mock_page)

        # wait_for_function이 호출되었는지 확인
        mock_page.wait_for_function.assert_called_once_with(
            """() => document.readyState === 'complete'""", timeout=30000
        )


class TestSessionValidation:
    """세션 유효성 검증 테스트"""

    @pytest.fixture
    def config(self):
        """테스트용 설정 객체"""
        return CrawlerConfig(
            timeout=30,
            max_retries=3,
            delay=5.0,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        )

    @pytest.fixture
    def crawler(self, config):
        """테스트용 크롤러 객체"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            yield NaverRealEstateCrawler(config, output_dir=tmpdir)

    def test_validate_session_with_valid_cookies(self, crawler):
        """유효한 쿠키가 있는 경우 세션 유효성 확인"""
        # 유효한 쿠키 목록
        valid_cookies = [
            {"name": "NNB", "value": "valid_token", "domain": ".naver.com"},
            {"name": "NID", "value": "valid_nid", "domain": ".naver.com"},
        ]

        # _validate_session 메서드 호출
        result = crawler._validate_session(valid_cookies)

        # 유효한 세션이면 True 반환
        assert result is True

    def test_validate_session_without_nnb_cookie(self, crawler):
        """NNB 쿠키가 없는 경우 세션 유효성 실패"""
        # NNB가 없는 쿠키 목록
        cookies_without_nnb = [
            {"name": "NID", "value": "valid_nid", "domain": ".naver.com"},
            {"name": "Other", "value": "value", "domain": ".naver.com"},
        ]

        # _validate_session 메서드 호출
        result = crawler._validate_session(cookies_without_nnb)

        # NNB가 없으면 False 반환
        assert result is False

    def test_validate_session_with_expired_cookies(self, crawler):
        """만료된 쿠키가 있는 경우 세션 유효성 실패"""
        # 만료된 쿠키 목록
        expired_cookies = [
            {
                "name": "NNB",
                "value": "expired_token",
                "domain": ".naver.com",
                "expires": int(time.time()) - 3600,  # 1시간 전 만료
            },
        ]

        # _validate_session 메서드 호출
        result = crawler._validate_session(expired_cookies)

        # 만료된 쿠키가 있으면 False 반환
        assert result is False

    def test_validate_session_with_empty_cookies(self, crawler):
        """빈 쿠키 목록인 경우 세션 유효성 실패"""
        # 빈 쿠키 목록
        empty_cookies = []

        # _validate_session 메서드 호출
        result = crawler._validate_session(empty_cookies)

        # 빈 쿠키 목록이면 False 반환
        assert result is False


class TestCookieAcquisition:
    """쿠키 확보 로직 테스트"""

    @pytest.fixture
    def config(self):
        """테스트용 설정 객체"""
        return CrawlerConfig(
            timeout=30,
            max_retries=3,
            delay=5.0,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        )

    @pytest.fixture
    def crawler(self, config):
        """테스트용 크롤러 객체"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            yield NaverRealEstateCrawler(config, output_dir=tmpdir)

    @patch("crawler.crawlers.naver.time.sleep")
    def test_ensure_session_acquires_required_cookies(self, mock_sleep, crawler):
        """필수 쿠키(NNB, NID 등) 확보 확인"""
        # 모의 Playwright Page 객체
        mock_page = Mock()
        mock_page.set_extra_http_headers = Mock()
        mock_page.goto = Mock(return_value=Mock(status=200))
        mock_page.wait_for_load_state = Mock()
        mock_page.wait_for_function = Mock()
        mock_page.context = Mock()
        mock_page.context.cookies = Mock()

        # 모의 쿠키 응답 설정
        mock_page.context.cookies.return_value = [
            {"name": "NNB", "value": "test_nnb_token", "domain": ".naver.com"},
            {"name": "NID", "value": "test_nid_token", "domain": ".naver.com"},
            {"name": "SESSION", "value": "test_session", "domain": ".naver.com"},
        ]

        # _ensure_session 메서드 호출
        crawler._ensure_session(mock_page)

        # 페이지 접속 확인
        mock_page.goto.assert_called_once_with(
            "https://m.land.naver.com/complexes", wait_until="domcontentloaded", timeout=30000
        )

        # 모바일 User-Agent 설정 확인
        expected_headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/16.0 Mobile/15E148 Safari/604.1 NaverLandApp",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        mock_page.set_extra_http_headers.assert_called_once_with(expected_headers)

        # 쿠키 확인 로그 호출 확인
        mock_page.context.cookies.assert_called_once()

    def test_get_required_cookies_returns_necessary_cookies(self, crawler):
        """필수 쿠키 목록 반환 확인"""
        # 모의 쿠키 데이터
        all_cookies = [
            {"name": "NNB", "value": "nnb_value", "domain": ".naver.com"},
            {"name": "NID", "value": "nid_value", "domain": ".naver.com"},
            {"name": "Other", "value": "other_value", "domain": ".naver.com"},
            {"name": "NNB", "value": "nnb_value2", "domain": "other.com"},  # 다른 도메인
        ]

        # _get_required_cookies 메서드 호출 (아직 구현되지 않음)
        required_cookies = crawler._get_required_cookies(all_cookies)

        # 네이버 도메인의 필수 쿠키만 필터링되는지 확인
        expected_cookies = [
            {"name": "NNB", "value": "nnb_value", "domain": ".naver.com"},
            {"name": "NID", "value": "nid_value", "domain": ".naver.com"},
        ]
        assert required_cookies == expected_cookies


class TestStorageAcquisition:
    """localStorage/sessionStorage 확보 테스트"""

    @pytest.fixture
    def config(self):
        """테스트용 설정 객체"""
        return CrawlerConfig(
            timeout=30,
            max_retries=3,
            delay=5.0,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        )

    @pytest.fixture
    def crawler(self, config):
        """테스트용 크롤러 객체"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            yield NaverRealEstateCrawler(config, output_dir=tmpdir)

    def test_extract_storage_data_returns_necessary_storage(self, crawler):
        """필요한 localStorage/sessionStorage 데이터 추출 확인"""
        # 모의 Playwright Page 객체
        mock_page = Mock()

        # 모의 스토리지 데이터
        mock_storage_data = {
            "localStorage": {
                "naver.adult": "false",
                "naver.main": "main_data",
                "NID_AUT": "nid_aut_value",
                "NID_SES": "nid_ses_value",
            },
            "sessionStorage": {
                "naver.session": "session_data",
                "tmp.session": "temp_data",
            },
        }

        # page.evaluate 모의 응답 설정
        mock_page.evaluate.return_value = mock_storage_data

        # _extract_storage_data 메서드 호출 (아직 구현되지 않음)
        storage_data = crawler._extract_storage_data(mock_page)

        # storage 데이터가 올바르게 추출되는지 확인
        assert storage_data == mock_storage_data

        # evaluate가 올바른 JavaScript 코드로 호출되었는지 확인
        mock_page.evaluate.assert_called_once()


class TestSessionRefresh:
    """세션 재확보 테스트"""

    @pytest.fixture
    def config(self):
        """테스트용 설정 객체"""
        return CrawlerConfig(
            timeout=30,
            max_retries=3,
            delay=5.0,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        )

    @pytest.fixture
    def crawler(self, config):
        """테스트용 크롤러 객체"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            yield NaverRealEstateCrawler(config, output_dir=tmpdir)

    @patch("crawler.crawlers.naver.time.sleep")
    def test_refresh_session_clears_and_reestablishes(self, mock_sleep, crawler):
        """세션 새로고침 시 기존 세션 클리어 및 재확보 확인"""
        # 모의 Playwright Page 객체
        mock_page = Mock()
        mock_page.set_extra_http_headers = Mock()
        mock_page.goto = Mock(return_value=Mock(status=200))
        mock_page.wait_for_load_state = Mock()
        mock_page.wait_for_function = Mock()
        mock_page.context = Mock()
        mock_page.context.cookies = Mock()
        mock_page.context.clear_cookies = Mock()

        # 기존 쿠키 설정
        old_cookies = [
            {"name": "NNB", "value": "old_token", "domain": ".naver.com"},
        ]
        mock_page.context.cookies.return_value = old_cookies

        # _refresh_session 메서드를 모의하여 _ensure_session 재귀 호출 방지
        with patch.object(crawler, "_ensure_session") as mock_ensure_session:
            # _refresh_session 메서드 호출
            crawler._refresh_session(mock_page)

            # 쿠키 클리어 확인
            mock_page.context.clear_cookies.assert_called_once()

            # 세션 재확보를 위해 페이지 재접속 확인
            assert mock_page.goto.call_count == 1  # 재접속만 호출 (reload는 실패했다고 가정)

            # _ensure_session이 호출되었는지 확인
            mock_ensure_session.assert_called_once_with(mock_page)


class TestCookieExpiration:
    """쿠키 만료 확인 및 재갱신 테스트"""

    @pytest.fixture
    def config(self):
        """테스트용 설정 객체"""
        return CrawlerConfig(
            timeout=30,
            max_retries=3,
            delay=5.0,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        )

    @pytest.fixture
    def crawler(self, config):
        """테스트용 크롤러 객체"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            yield NaverRealEstateCrawler(config, output_dir=tmpdir)

    def test_check_cookie_expiration_detects_expired(self, crawler):
        """만료된 쿠키 감지 확인"""
        # 만료된 쿠키
        expired_cookie = {
            "name": "NNB",
            "value": "expired_value",
            "expires": int(time.time()) - 3600,  # 1시간 전 만료
            "domain": ".naver.com",
        }

        # _check_cookie_expiration 메서드 호출 (아직 구현되지 않음)
        is_expired = crawler._check_cookie_expiration(expired_cookie)

        # 만료 확인
        assert is_expired is True

    def test_check_cookie_expiration_valid_cookie(self, crawler):
        """유효한 쿠키 확인"""
        # 유효한 쿠키 (1시간 후 만료)
        valid_cookie = {
            "name": "NNB",
            "value": "valid_value",
            "expires": int(time.time()) + 3600,  # 1시간 후 만료
            "domain": ".naver.com",
        }

        # _check_cookie_expiration 메서드 호출
        is_expired = crawler._check_cookie_expiration(valid_cookie)

        # 유효함 확인
        assert is_expired is False

    def test_check_cookie_expiration_no_expiry(self, crawler):
        """만료 시간이 없는 쿠키(세션 쿠키) 확인"""
        # 세션 쿠키 (만료 시간 없음)
        session_cookie = {
            "name": "NNB",
            "value": "session_value",
            "domain": ".naver.com",
        }

        # _check_cookie_expiration 메서드 호출
        is_expired = crawler._check_cookie_expiration(session_cookie)

        # 세션 쿠키는 만료되지 않음
        assert is_expired is False


class TestSessionManagementIntegration:
    """세션 관리 통합 테스트"""

    @pytest.fixture
    def config(self):
        """테스트용 설정 객체"""
        return CrawlerConfig(
            timeout=30,
            max_retries=3,
            delay=5.0,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        )

    @pytest.fixture
    def crawler(self, config):
        """테스트용 크롤러 객체"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            yield NaverRealEstateCrawler(config, output_dir=tmpdir)

    @patch("crawler.crawlers.naver.time.sleep")
    def test_full_session_workflow(self, mock_sleep, crawler):
        """전체 세션 워크플로우 테스트"""
        # 모의 Playwright Page 객체
        mock_page = Mock()
        mock_page.set_extra_http_headers = Mock()
        mock_page.goto = Mock(return_value=Mock(status=200))
        mock_page.wait_for_load_state = Mock()
        mock_page.wait_for_function = Mock()
        mock_page.context = Mock()
        mock_page.context.cookies = Mock()

        # 초기 상태: 유효한 쿠키 없음
        mock_page.context.cookies.return_value = []

        # 세션 확보 시도
        crawler._ensure_session(mock_page)

        # 페이지 접속 확인
        mock_page.goto.assert_called_once_with(
            "https://m.land.naver.com/complexes", wait_until="domcontentloaded", timeout=30000
        )

        # 대기 상태 확인
        mock_page.wait_for_load_state.assert_any_call("networkidle", timeout=10000)
        mock_page.wait_for_function.assert_called_once_with(
            """() => document.readyState === 'complete'""", timeout=30000
        )

        # 쿠키 확인
        mock_page.context.cookies.assert_called()

    def test_session_validation_failure_triggers_refresh(self, crawler):
        """세션 유효성 검증 실패 시 새로고침 트리거 확인"""
        # 모의 Playwright Page 객체
        mock_page = Mock()
        mock_page.set_extra_http_headers = Mock()
        mock_page.goto = Mock(return_value=Mock(status=200))
        mock_page.wait_for_load_state = Mock()
        mock_page.wait_for_function = Mock()
        mock_page.context = Mock()
        mock_page.context.cookies = Mock()

        # 유효하지 않은 쿠키
        invalid_cookies = [
            {"name": "Other", "value": "value", "domain": ".naver.com"},
        ]
        mock_page.context.cookies.return_value = invalid_cookies

        # _ensure_session이 실패를 감지하고 재시도하는지 확인
        with (
            patch.object(crawler, "_validate_session", return_value=False),
            patch.object(crawler, "_refresh_session") as mock_refresh,
        ):
            try:
                crawler._ensure_session(mock_page)
            except Exception:
                pass  # 예외는 무시

            # 세션 새로고침 호출 확인
            mock_refresh.assert_called_once_with(mock_page)
