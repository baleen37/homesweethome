"""NaverSessionManager 테스트"""

import pytest
from unittest.mock import Mock, patch

from crawler.utils.naver_session import NaverSessionManager, SessionState


class TestNaverSessionManager:
    """NaverSessionManager 단위 테스트"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """싱글톤 인스턴스 리셋"""
        # 클래스 속성 초기화
        NaverSessionManager._instance = None
        NaverSessionManager._initialized = False
        yield

    @pytest.fixture
    def mock_page(self):
        """Mock Playwright page 객체"""
        page = Mock()
        page.context = Mock()
        page.context.cookies = Mock(return_value=[])
        page.context.clear_cookies = Mock()
        page.goto = Mock()
        page.wait_for_load_state = Mock()
        page.evaluate = Mock(return_value={})
        return page

    @pytest.fixture
    def session_manager(self):
        """NaverSessionManager 인스턴스"""
        return NaverSessionManager()

    def test_singleton_pattern(self, session_manager):
        """싱글톤 패턴 확인"""
        another_manager = NaverSessionManager()
        assert session_manager is another_manager

    def test_initial_state(self, session_manager):
        """초기 상태 확인"""
        assert session_manager.state == SessionState.UNINITIALIZED
        assert session_manager.last_check_time == 0
        assert session_manager.retry_count == 0

    @patch("crawler.utils.naver_session.time.time")
    def test_ensure_session_with_valid_existing_session(
        self, mock_time, session_manager, mock_page
    ):
        """유효한 기존 세션이 있는 경우"""
        # Mock 시간 설정
        mock_time.return_value = 1000.0

        # Mock 쿠키 설정
        valid_cookies = [
            {"name": "NaverSession", "value": "valid_session", "domain": ".naver.com"},
            {"name": "nid_inf", "value": "some_value", "domain": ".naver.com"},
        ]
        mock_page.context.cookies.return_value = valid_cookies

        # validate_session을 True로 mock
        with patch.object(session_manager, "validate_session", return_value=True):
            session_manager.ensure_session(mock_page)

        # 상태 확인
        assert session_manager.state == SessionState.VALID
        assert session_manager.last_check_time == 1000.0

        # 새로운 세션 확보 시도가 없어야 함
        mock_page.goto.assert_not_called()

    @patch("crawler.utils.naver_session.time.time")
    def test_ensure_session_with_invalid_existing_session(
        self, mock_time, session_manager, mock_page
    ):
        """유효하지 않은 기존 세션이 있는 경우"""
        # Mock 시간 설정
        mock_time.return_value = 1000.0

        # Mock 쿠키 설정
        invalid_cookies = []
        mock_page.context.cookies.return_value = invalid_cookies

        # 세션 확成功率 성공으로 mock
        with patch.object(
            session_manager, "_acquire_new_session", return_value=True
        ) as mock_acquire:
            session_manager.ensure_session(mock_page)

        # 새로운 세션 확보 시도가 있어야 함
        mock_acquire.assert_called_once_with(mock_page)

    def test_validate_session_with_empty_cookies(self, session_manager):
        """빈 쿠키 리스트로 세션 유효성 검증"""
        assert not session_manager.validate_session([])

    def test_validate_session_without_required_cookies(self, session_manager):
        """필수 쿠키가 없는 경우"""
        cookies = [{"name": "irwg", "value": "some_value", "domain": ".naver.com"}]
        assert not session_manager.validate_session(cookies)

    def test_validate_session_with_all_required_cookies(self, session_manager):
        """모든 필수 쿠키가 있는 경우"""
        cookies = [
            {"name": "NaverSession", "value": "valid_session", "domain": ".naver.com"},
            {"name": "nid_inf", "value": "some_value", "domain": ".naver.com"},
            {"name": "irwg", "value": "some_value", "domain": ".naver.com"},
        ]
        assert session_manager.validate_session(cookies)

    def test_get_required_cookies_filters_naver_domains(self, session_manager):
        """네이버 도메인 쿠키만 필터링"""
        all_cookies = [
            {"name": "NaverSession", "value": "session1", "domain": ".naver.com"},
            {"name": "google_cookie", "value": "g_cookie", "domain": ".google.com"},
            {"name": "nid_inf", "value": "info1", "domain": "naver.com"},
            {"name": "facebook", "value": "fb_cookie", "domain": ".facebook.com"},
        ]

        required = session_manager.get_required_cookies(all_cookies)

        assert len(required) == 2
        assert all(cookie["domain"] in [".naver.com", "naver.com"] for cookie in required)
        assert any(cookie["name"] == "NaverSession" for cookie in required)
        assert any(cookie["name"] == "nid_inf" for cookie in required)

    def test_extract_storage_data(self, session_manager, mock_page):
        """스토리지 데이터 추출"""
        mock_storage_data = {
            "localStorage": {"key1": "value1"},
            "sessionStorage": {"key2": "value2"},
        }
        mock_page.evaluate.return_value = mock_storage_data

        storage = session_manager.extract_storage_data(mock_page)

        assert storage == mock_storage_data
        # localStorage 및 sessionStorage 모두 추출해야 함
        mock_page.evaluate.assert_called_once()

    def test_check_cookie_expiration_with_session_cookie(self, session_manager):
        """세션 쿠키(만료시간 없음) 만료 확인"""
        session_cookie = {"name": "session", "value": "data"}
        assert not session_manager.check_cookie_expiration(session_cookie)

    @patch("crawler.utils.naver_session.time.time")
    def test_check_cookie_expiration_with_expired_cookie(self, mock_time, session_manager):
        """만료된 쿠키 확인"""
        mock_time.return_value = 1000.0
        expired_cookie = {
            "name": "expired",
            "value": "data",
            "expires": 500,  # 500초 (만료됨)
        }
        assert session_manager.check_cookie_expiration(expired_cookie)

    @patch("crawler.utils.naver_session.time.time")
    def test_check_cookie_expiration_with_valid_cookie(self, mock_time, session_manager):
        """유효한 쿠키 확인"""
        mock_time.return_value = 1000.0
        valid_cookie = {
            "name": "valid",
            "value": "data",
            "expires": 2000,  # 2000초 (유효)
        }
        assert not session_manager.check_cookie_expiration(valid_cookie)

    def test_refresh_session_clears_cookies_and_acquires_new(self, session_manager, mock_page):
        """세션 새로고침 테스트"""
        with patch.object(
            session_manager, "_acquire_new_session", return_value=True
        ) as mock_acquire:
            session_manager.refresh_session(mock_page)

        # 쿠키 클리어 확인
        mock_page.context.clear_cookies.assert_called_once()
        # 새 세션 확보 확인
        mock_acquire.assert_called_once_with(mock_page)
        # 상태 초기화 확인
        assert session_manager.state == SessionState.UNINITIALIZED

    def test_is_session_valid_check_time_interval(self, session_manager):
        """세션 유효성 검사 시간 간격 테스트"""
        # 초기 상태에서는 유효하지 않음
        assert not session_manager.is_session_valid()

        # 세션을 유효하게 설정
        session_manager.state = SessionState.VALID
        session_manager.last_check_time = 1000.0

        # 시간 간격이 충분하지 않으면 유효함
        with patch("crawler.utils.naver_session.time.time", return_value=1005.0):
            assert session_manager.is_session_valid()

        # 시간 간격이 너무 길면 유효하지 않음
        with patch("crawler.utils.naver_session.time.time", return_value=2000.0):
            assert not session_manager.is_session_valid()

    def test_acquire_new_session_success(self, session_manager, mock_page):
        """새 세션 확보 성공 테스트"""
        # Mock 응답 설정
        mock_page.goto.return_value = Mock(status=200)
        mock_page.context.cookies.return_value = [
            {"name": "NaverSession", "value": "new_session", "domain": ".naver.com"},
            {"name": "nid_inf", "value": "info", "domain": ".naver.com"},
        ]
        mock_page.evaluate.return_value = {"localStorage": {"key": "value"}}

        with patch("crawler.utils.naver_session.time.sleep"):  # sleep 실제 실행 방지
            result = session_manager._acquire_new_session(mock_page)

        assert result
        assert session_manager.state == SessionState.VALID
        assert session_manager.retry_count == 0

    def test_acquire_new_session_failure_with_retry(self, session_manager, mock_page):
        """새 세션 확보 실패 후 재시도 테스트"""
        # 첫 번째 시도는 실패, 두 번째 시도는 성공
        mock_page.goto.side_effect = [Exception("Network error"), Mock(status=200)]
        mock_page.context.cookies.return_value = [
            {"name": "NaverSession", "value": "retry_session", "domain": ".naver.com"}
        ]

        with patch("crawler.utils.naver_session.time.sleep"):
            result = session_manager._acquire_new_session(mock_page)

        assert result
        # 성공 후 retry_count는 0으로 리셋됨
        assert session_manager.retry_count == 0
        assert session_manager.state == SessionState.VALID

    def test_acquire_new_session_max_retries_exceeded(self, session_manager, mock_page):
        """최대 재시도 횟수 초과 테스트"""
        # 항상 실패
        mock_page.goto.side_effect = Exception("Always fails")

        with patch("crawler.utils.naver_session.time.sleep"):
            result = session_manager._acquire_new_session(mock_page)

        assert not result
        assert session_manager.state == SessionState.INVALID
        assert session_manager.retry_count >= session_manager.max_retries
