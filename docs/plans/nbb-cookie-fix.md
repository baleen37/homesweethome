# NNB 쿠키 인증 문제 해결 계획

## 문제 요약
- 첫 API 호출(`/cluster/ajax/complexList`)은 성공
- 이후 API 호출(`/complex/detail`)은 NNB 쿠키 누락으로 실패
- 쿠키가 갱신되면서 NNB가 사라짐

## 원인 분석
1. 도메인 불일치: `new.land.naver.com` vs `m.land.naver.com`
2. 쿠키 관리 로직 문제: NNB 쿠키가 덮어쓰기됨
3. 세션 확보 로직: 모바일 페이지에서 세션 확보 후 데스크탑 API 사용

## 해결 방안

### 1. 도메인 통일
- 모든 API 호출을 `https://new.land.naver.com`으로 통일
- NaverSessionManager도 `new.land.naver.com`에서 세션 확보

### 2. NaverAuthManager 수정
```python
def update_cookies(self, new_cookies: Dict[str, str]) -> None:
    """쿠키 업데이트 시 NNB와 같은 중요 쿠키 보호"""
    if not new_cookies:
        return

    # 기존 NNB 쿠키 보호
    existing_nnb = self.cookies.get("NNB")

    # 쿠키 업데이트
    self.cookies.update(new_cookies)

    # NNB가 새 응답에 없고 기존에 있었다면 복원
    if "NNB" not in new_cookies and existing_nnb:
        self.cookies["NNB"] = existing_nnb
        self.logger.info("NNB cookie preserved")
```

### 3. NaverAPIClient 수정
```python
def _make_request(self, method: str, endpoint: str, **kwargs):
    """API 요청 시 쿠키 보호 로직 강화"""
    session = self._get_session()

    # 요청 전 NNB 쿠키 확인
    has_nnb_before = "NNB" in self.auth_manager.cookies

    # 자동 새로고침 체크
    self.auth_manager.auto_refresh_if_needed()

    # 세션 헤더 업데이트
    session.headers.update(self._get_api_headers())

    # 요청 실행
    response = session.request(method, endpoint, timeout=self.timeout, **kwargs)

    # 응답 쿠키 업데이트
    if response.cookies:
        new_cookies = dict(response.cookies)

        # NNB 쿠키 보호
        if has_nnb_before and "NNB" not in new_cookies:
            self.logger.warning("NNB cookie missing in response, preserving existing")

        self.auth_manager.update_cookies(new_cookies)

    # 상태 코드 처리
    if response.status_code in self.retry_manager.config.retryable_status_codes:
        error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
        raise RetryableError(error_msg, status_code=response.status_code)
    elif not response.ok:
        error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
        raise NonRetryableError(error_msg, status_code=response.status_code)

    return response
```

### 4. NaverSessionManager 수정
```python
def _acquire_new_session(self, page: Any) -> bool:
    """new.land.naver.com에서 세션 확보"""
    self.logger.info("acquiring_new_session", retry_count=self.retry_count)

    try:
        # 네이버 부동산 메인 페이지 접속 (모바일 아님)
        self.logger.info("accessing_naver_main")
        response = page.goto(
            "https://new.land.naver.com/", wait_until="domcontentloaded", timeout=30000
        )

        # ... 기존 로직 유지 ...

        # NNB 쿠키 특별 확인
        cookies = page.context.cookies()
        nnb_cookie = next((c for c in cookies if c.get("name") == "NNB"), None)

        if not nnb_cookie:
            self.logger.error("NNB cookie not found after page load")
            return self._handle_acquisition_failure(page)

        self.logger.info("NNB cookie acquired", value=nnb_cookie.get("value", "")[:10] + "...")

        # ... 나머지 로직 ...
```

### 5. 쿠키 영속성 추가
```python
# NaverAuthManager에 추가
def save_cookies_to_file(self, filepath: str) -> None:
    """쿠키를 파일에 저장"""
    import json
    with open(filepath, 'w') as f:
        json.dump(self.cookies, f)

def load_cookies_from_file(self, filepath: str) -> bool:
    """파일에서 쿠키 로드"""
    import json
    try:
        with open(filepath, 'r') as f:
            self.cookies = json.load(f)
        return True
    except:
        return False
```

## 구현 순서
1. NaverAuthManager.update_cookies() 수정
2. NaverAPIClient._make_request() 수정
3. NaverSessionManager._acquire_new_session() 수정
4. 테스트 및 검증

## 예상 결과
- NNB 쿠키가 API 호출 간에 유지됨
- 일관된 인증 상태 유지
- 401 에러 발생 감소