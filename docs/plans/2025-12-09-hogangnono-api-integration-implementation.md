# 호갱노노 API 연동 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 호갱노노 API를 통해 전국 아파트 단지 정보 + 실거래 내역을 계층적으로 수집하는 완전한 파이프라인 구축

**Architecture:** HogangnonoAPIClient에 3개의 신규 API 메서드 추가 (regions, detail, transactions), HogangnonoCrawler에 계층적 크롤링 로직 구현, 구/군 단위 점진적 저장 및 checkpoint 관리

**Tech Stack:** Python 3.11+, requests, structlog, AdaptiveRateLimiter, Retryable, CSV

---

## Task 1: get_regions API 메서드 구현

**Files:**
- Modify: `src/crawler/api/hogangnono_client.py:363-808`
- Test: `tests/unit/test_hogangnono_api_client.py` (신규)

**Step 1: regions API 테스트 작성**

```python
# tests/unit/test_hogangnono_api_client.py
import pytest
from unittest.mock import Mock, patch
from crawler.api.hogangnono_client import HogangnonoAPIClient, APIResponse
from crawler.config import CrawlerConfig


@pytest.fixture
def config():
    return CrawlerConfig.from_env()


@pytest.fixture
def client(config):
    return HogangnonoAPIClient(config)


def test_get_regions_success(client):
    """전체 지역 목록 조회 성공"""
    with patch.object(client, '_make_request') as mock_request:
        mock_request.return_value = APIResponse(
            success=True,
            data={
                "regionList": [
                    {
                        "regionCode": "11",
                        "name": "서울",
                        "fullName": "서울특별시",
                        "children": [
                            {
                                "regionCode": "11680",
                                "name": "강남구",
                                "fullName": "서울특별시 강남구"
                            }
                        ]
                    }
                ]
            },
            status_code=200
        )

        response = client.get_regions()

        assert response.success
        assert response.data is not None
        assert "regionList" in response.data
        assert len(response.data["regionList"]) > 0

        mock_request.assert_called_once_with(
            method="GET",
            endpoint="/api/v2/regions",
            params={}
        )


def test_get_regions_with_filter(client):
    """특정 시/도 필터링"""
    with patch.object(client, '_make_request') as mock_request:
        mock_request.return_value = APIResponse(
            success=True,
            data={"regionList": [{"regionCode": "11", "name": "서울"}]},
            status_code=200
        )

        response = client.get_regions(region_code="11")

        assert response.success
        mock_request.assert_called_once_with(
            method="GET",
            endpoint="/api/v2/regions",
            params={"regionCode": "11"}
        )
```

**Step 2: 테스트 실행하여 실패 확인**

Run: `pytest tests/unit/test_hogangnono_api_client.py::test_get_regions_success -v`
Expected: FAIL with "AttributeError: 'HogangnonoAPIClient' object has no attribute 'get_regions'"

**Step 3: get_regions 메서드 구현**

```python
# src/crawler/api/hogangnono_client.py
# 808행 이후에 추가

    def get_regions(
        self,
        region_code: Optional[str] = None
    ) -> APIResponse:
        """시/도, 구/군 목록 조회

        Args:
            region_code: 특정 시/도 필터링 (예: "11" = 서울)

        Returns:
            APIResponse with regionList data

        Example Response:
            {
                "data": {
                    "regionList": [
                        {
                            "regionCode": "11",
                            "name": "서울",
                            "fullName": "서울특별시",
                            "children": [
                                {
                                    "regionCode": "11680",
                                    "name": "강남구",
                                    "fullName": "서울특별시 강남구"
                                }
                            ]
                        }
                    ]
                },
                "status": "success"
            }
        """
        params = {}
        if region_code:
            params["regionCode"] = region_code

        return self._make_request(
            method="GET",
            endpoint="/api/v2/regions",
            params=params
        )
```

**Step 4: 테스트 실행하여 통과 확인**

Run: `pytest tests/unit/test_hogangnono_api_client.py::test_get_regions_success -v`
Expected: PASS

**Step 5: 커밋**

```bash
git add tests/unit/test_hogangnono_api_client.py src/crawler/api/hogangnono_client.py
git commit -m "feat: get_regions API 메서드 구현

- 전국 시/도, 구/군 목록 조회 기능 추가
- region_code 파라미터로 특정 시/도 필터링 지원
- 테스트 추가"
```

---

## Task 2: get_apartment_detail API 메서드 구현

**Files:**
- Modify: `src/crawler/api/hogangnono_client.py:808-`
- Modify: `tests/unit/test_hogangnono_api_client.py`

**Step 1: apartment_detail API 테스트 작성**

```python
# tests/unit/test_hogangnono_api_client.py에 추가

def test_get_apartment_detail_success(client):
    """단지 상세 정보 조회 성공"""
    with patch.object(client, '_make_request') as mock_request:
        mock_request.return_value = APIResponse(
            success=True,
            data={
                "aptHash": "1Hq6f",
                "aptName": "래미안",
                "buildYear": 2005,
                "household": 1012,
                "parkingCount": 850,
                "floorAreaRatio": 250.5,
                "buildingCoverageRatio": 15.3
            },
            status_code=200
        )

        response = client.get_apartment_detail("1Hq6f")

        assert response.success
        assert response.data is not None
        assert response.data["aptHash"] == "1Hq6f"

        mock_request.assert_called_once_with(
            method="GET",
            endpoint="/api/v2/apts/1Hq6f",
            params={}
        )


def test_get_apartment_detail_not_found(client):
    """존재하지 않는 단지 조회"""
    with patch.object(client, '_make_request') as mock_request:
        mock_request.return_value = APIResponse(
            success=False,
            error="Apartment not found",
            status_code=404
        )

        response = client.get_apartment_detail("invalid")

        assert not response.success
        assert response.status_code == 404
```

**Step 2: 테스트 실행하여 실패 확인**

Run: `pytest tests/unit/test_hogangnono_api_client.py::test_get_apartment_detail_success -v`
Expected: FAIL with "AttributeError: 'HogangnonoAPIClient' object has no attribute 'get_apartment_detail'"

**Note:** 기존에 `get_apartment_detail` 메서드가 있지만 엔드포인트가 다릅니다 (`/api/apt/detail` vs `/api/v2/apts/{aptId}`). 새로운 엔드포인트로 교체합니다.

**Step 3: get_apartment_detail 메서드 수정**

```python
# src/crawler/api/hogangnono_client.py
# 기존 get_apartment_detail 메서드 (762-779행) 수정

    def get_apartment_detail(self, apt_id: str) -> APIResponse:
        """아파트 상세 정보 조회

        Args:
            apt_id: 아파트 ID (aptHash)

        Returns:
            APIResponse 객체

        Example Response:
            {
                "data": {
                    "aptHash": "1Hq6f",
                    "aptName": "래미안",
                    "buildYear": 2005,
                    "household": 1012,
                    "parkingCount": 850,
                    "floorAreaRatio": 250.5,
                    "buildingCoverageRatio": 15.3
                },
                "status": "success"
            }
        """
        return self._make_request(
            method="GET",
            endpoint=f"/api/v2/apts/{apt_id}",
            params={}
        )
```

**Step 4: 테스트 실행하여 통과 확인**

Run: `pytest tests/unit/test_hogangnono_api_client.py::test_get_apartment_detail_success -v`
Expected: PASS

**Step 5: 커밋**

```bash
git add tests/unit/test_hogangnono_api_client.py src/crawler/api/hogangnono_client.py
git commit -m "feat: get_apartment_detail API 엔드포인트 업데이트

- /api/v2/apts/{aptId} 엔드포인트로 변경
- 단지 상세 정보 조회 기능 개선
- 404 에러 처리 테스트 추가"
```

---

## Task 3: get_apartment_transactions API 메서드 구현

**Files:**
- Modify: `src/crawler/api/hogangnono_client.py:808-`
- Modify: `tests/unit/test_hogangnono_api_client.py`

**Step 1: transactions API 테스트 작성**

```python
# tests/unit/test_hogangnono_api_client.py에 추가

def test_get_apartment_transactions_recent(client):
    """최근 3년 실거래 내역 조회"""
    with patch.object(client, '_make_request') as mock_request:
        mock_request.return_value = APIResponse(
            success=True,
            data={
                "shortTermReport": [
                    {
                        "date": "2025-01-31T15:00:00.000Z",
                        "minPrice": 333000,
                        "maxPrice": 346000,
                        "averagePrice": 343000,
                        "volume": 3,
                        "trades": [
                            {
                                "id": 36780389,
                                "price": 340000,
                                "floor": 9,
                                "day": 18
                            }
                        ]
                    }
                ]
            },
            status_code=200
        )

        response = client.get_apartment_transactions("1Hq6f", trade_type=0)

        assert response.success
        assert response.data is not None
        assert "shortTermReport" in response.data

        mock_request.assert_called_once_with(
            method="GET",
            endpoint="/api/v2/apts/1Hq6f/monthly-reports",
            params={"tradeType": 0, "areaNo": 0}
        )


def test_get_apartment_transactions_full_period(client):
    """전체 기간 실거래 내역 조회"""
    with patch.object(client, '_make_request') as mock_request:
        mock_request.return_value = APIResponse(
            success=True,
            data={"longTermReport": []},
            status_code=200
        )

        response = client.get_apartment_transactions(
            "1Hq6f",
            trade_type=0,
            full_period=True
        )

        assert response.success

        mock_request.assert_called_once_with(
            method="GET",
            endpoint="/api/v2/apts/1Hq6f/monthly-reports/more",
            params={"tradeType": 0, "areaNo": 0}
        )
```

**Step 2: 테스트 실행하여 실패 확인**

Run: `pytest tests/unit/test_hogangnono_api_client.py::test_get_apartment_transactions_recent -v`
Expected: FAIL with "AttributeError"

**Step 3: get_apartment_transactions 메서드 구현**

```python
# src/crawler/api/hogangnono_client.py
# get_apartment_detail 메서드 다음에 추가

    def get_apartment_transactions(
        self,
        apt_id: str,
        trade_type: int = 0,
        area_no: int = 0,
        full_period: bool = False
    ) -> APIResponse:
        """실거래 내역 조회

        Args:
            apt_id: 단지 ID (aptHash)
            trade_type: 0=매매, 1=전세, 2=월세
            area_no: 면적 필터 (0=전체)
            full_period: True면 전체 기간, False면 최근 3년

        Returns:
            APIResponse 객체

        Example Response:
            {
                "data": {
                    "shortTermReport": [
                        {
                            "date": "2025-01-31T15:00:00.000Z",
                            "minPrice": 333000,
                            "maxPrice": 346000,
                            "averagePrice": 343000,
                            "volume": 3,
                            "trades": [...]
                        }
                    ]
                },
                "status": "success"
            }
        """
        # 엔드포인트 결정
        if full_period:
            endpoint = f"/api/v2/apts/{apt_id}/monthly-reports/more"
        else:
            endpoint = f"/api/v2/apts/{apt_id}/monthly-reports"

        params = {
            "tradeType": trade_type,
            "areaNo": area_no
        }

        return self._make_request(
            method="GET",
            endpoint=endpoint,
            params=params
        )
```

**Step 4: 테스트 실행하여 통과 확인**

Run: `pytest tests/unit/test_hogangnono_api_client.py::test_get_apartment_transactions_recent -v`
Run: `pytest tests/unit/test_hogangnono_api_client.py::test_get_apartment_transactions_full_period -v`
Expected: PASS (모두)

**Step 5: 커밋**

```bash
git add tests/unit/test_hogangnono_api_client.py src/crawler/api/hogangnono_client.py
git commit -m "feat: get_apartment_transactions API 메서드 구현

- 최근 3년/전체 기간 실거래 내역 조회 기능 추가
- trade_type, area_no 파라미터 지원
- full_period 플래그로 엔드포인트 자동 선택
- 테스트 추가"
```

---

## Task 4: AdaptiveRateLimiter 통합

**Files:**
- Modify: `src/crawler/api/hogangnono_client.py:363-380`
- Modify: `tests/unit/test_hogangnono_api_client.py`

**Step 1: RateLimiter 통합 테스트 작성**

```python
# tests/unit/test_hogangnono_api_client.py에 추가

def test_rate_limiter_integration(client):
    """RateLimiter가 API 호출에 통합되었는지 확인"""
    # RateLimiter가 초기화되었는지 확인
    assert hasattr(client, 'rate_limiter')
    assert client.rate_limiter is not None

    # 초기 설정 확인
    assert client.rate_limiter.current_delay == 2.0
    assert client.rate_limiter.min_delay == 1.0
    assert client.rate_limiter.max_delay == 10.0


def test_rate_limiter_called_before_request(client):
    """API 호출 전 rate limiter wait() 호출 확인"""
    with patch.object(client.rate_limiter, 'wait') as mock_wait:
        with patch.object(client, '_initialize_session', return_value=True):
            with patch.object(client.session, 'request') as mock_request:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"status": "success", "data": {}}
                mock_response.headers = {"content-type": "application/json"}
                mock_request.return_value = mock_response

                client.get_regions()

                # wait()가 호출되었는지 확인
                mock_wait.assert_called_once()
```

**Step 2: 테스트 실행하여 실패 확인**

Run: `pytest tests/unit/test_hogangnono_api_client.py::test_rate_limiter_integration -v`
Expected: FAIL with "AssertionError: False is not true" (rate_limiter 속성 없음)

**Step 3: RateLimiter 통합 구현**

```python
# src/crawler/api/hogangnono_client.py
# __init__ 메서드 수정 (369-385행)

    def __init__(self, config: CrawlerConfig):
        """클라이언트 초기화

        Args:
            config: 크롤러 설정 객체
        """
        self.config = config
        self.base_url = "https://hogangnono.com"
        self.session = Session()

        # 초기화 상태 추적
        self._session_initialized = False

        self.logger = get_logger()

        # Rate limiting - 단일 AdaptiveRateLimiter
        from ..rate_limiter import AdaptiveRateLimiter
        self.rate_limiter = AdaptiveRateLimiter()
        # 초기값 설정 (2초, 최소 1초, 최대 10초)
        self.rate_limiter.current_delay = 2.0
        self.rate_limiter.min_delay = 1.0
        self.rate_limiter.max_delay = 10.0


# _make_request 메서드 수정 (494-567행)
# wait() 호출 추가

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> APIResponse:
        """HTTP 요청 실행"""
        # Rate limiting 적용
        self.rate_limiter.wait()

        # 세션이 초기화되지 않았다면 초기화
        if not self._session_initialized:
            if not self._initialize_session():
                return APIResponse(
                    success=False,
                    error="Failed to initialize session",
                    status_code=None,
                )

        url = self._build_url(endpoint)
        request_headers = self._add_auth_headers(headers)

        self.logger.info(
            "API request",
            method=method,
            url=url,
            params=params,
        )

        # ... (기존 코드 유지)

        response = self.session.request(
            method=method,
            url=url,
            params=params,
            json=data,
            headers=request_headers,
            timeout=self.config.timeout,
        )

        api_response = APIResponse.from_response(response)

        # Rate limiter 피드백
        if api_response.success:
            self.rate_limiter.on_success()
            self.logger.info(
                "API request successful",
                status=response.status_code,
            )
        elif api_response.status_code == 429:
            self.rate_limiter.on_rate_limit_error()
            self.logger.error(
                "API request rate limited",
                status=response.status_code,
                error=api_response.error,
            )
        else:
            self.rate_limiter.on_error()
            self.logger.error(
                "API request failed",
                status=response.status_code,
                error=api_response.error,
            )

        return api_response
```

**Step 4: 테스트 실행하여 통과 확인**

Run: `pytest tests/unit/test_hogangnono_api_client.py::test_rate_limiter_integration -v`
Run: `pytest tests/unit/test_hogangnono_api_client.py::test_rate_limiter_called_before_request -v`
Expected: PASS (모두)

**Step 5: 커밋**

```bash
git add src/crawler/api/hogangnono_client.py tests/unit/test_hogangnono_api_client.py
git commit -m "feat: AdaptiveRateLimiter 통합

- 단일 AdaptiveRateLimiter로 모든 API 요청 제어
- 초기 2초, 최소 1초, 최대 10초 설정
- 429 에러 시 자동 지연 증가
- 성공 시 점진적 속도 향상
- 테스트 추가"
```

---

## Task 5: retry 데코레이터 적용

**Files:**
- Modify: `src/crawler/api/hogangnono_client.py:494-567`
- Modify: `tests/unit/test_hogangnono_api_client.py`

**Step 1: retry 테스트 작성**

```python
# tests/unit/test_hogangnono_api_client.py에 추가

def test_retry_on_transient_error(client):
    """일시적 오류 시 재시도 확인"""
    with patch.object(client, '_initialize_session', return_value=True):
        with patch.object(client.rate_limiter, 'wait'):
            with patch.object(client.session, 'request') as mock_request:
                # 첫 2번은 실패, 3번째는 성공
                mock_response_fail = Mock()
                mock_response_fail.status_code = 503
                mock_response_fail.headers = {"content-type": "application/json"}
                mock_response_fail.json.return_value = {
                    "success": False,
                    "error": "Service temporarily unavailable"
                }

                mock_response_success = Mock()
                mock_response_success.status_code = 200
                mock_response_success.headers = {"content-type": "application/json"}
                mock_response_success.json.return_value = {
                    "status": "success",
                    "data": {"regionList": []}
                }

                mock_request.side_effect = [
                    mock_response_fail,
                    mock_response_fail,
                    mock_response_success
                ]

                response = client.get_regions()

                # 3번 호출되었는지 확인
                assert mock_request.call_count == 3
                # 최종적으로 성공
                assert response.success
```

**Step 2: 테스트 실행하여 실패 확인**

Run: `pytest tests/unit/test_hogangnono_api_client.py::test_retry_on_transient_error -v`
Expected: FAIL (재시도 없이 첫 번째 실패에서 종료)

**Step 3: retry 데코레이터 적용**

```python
# src/crawler/api/hogangnono_client.py
# _make_request 메서드에 데코레이터 추가

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> APIResponse:
        """HTTP 요청 실행 (재시도 포함)"""
        # retry 로직을 내부 함수로 이동
        from ..utils.retry import Retryable, BackoffStrategy

        retryable = Retryable(
            max_attempts=3,
            base_delay=1.0,
            max_delay=10.0,
            strategy=BackoffStrategy.EXPONENTIAL,
            jitter=True,
            retry_on=Exception
        )

        return retryable.execute(self._make_request_internal, method, endpoint, params, data, headers)

    def _make_request_internal(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> APIResponse:
        """실제 HTTP 요청 실행 (내부 메서드)"""
        # Rate limiting 적용
        self.rate_limiter.wait()

        # ... (기존 _make_request 로직)

        api_response = APIResponse.from_response(response)

        # 에러 시 예외 발생 (retry 트리거)
        if not api_response.success:
            # 429는 rate limiter가 처리
            if api_response.status_code == 429:
                self.rate_limiter.on_rate_limit_error()
            else:
                self.rate_limiter.on_error()

            # 재시도 가능한 에러인 경우 예외 발생
            if api_response.status_code in (500, 502, 503, 504):
                raise Exception(f"API error: {api_response.error}")
        else:
            self.rate_limiter.on_success()

        return api_response
```

**Note:** 위 구조는 복잡할 수 있습니다. 더 간단한 방법은 각 public 메서드에 `@retry_transient_errors` 데코레이터를 직접 적용하는 것입니다. 하지만 DRY 원칙을 위해 `_make_request`에 통합합니다.

**Alternative (더 간단한 방법):**

```python
# src/crawler/api/hogangnono_client.py
# _make_request 메서드는 그대로 두고, 각 public 메서드에 데코레이터 적용

from ..utils.retry import retry_transient_errors

@retry_transient_errors(max_attempts=3, base_delay=1.0, max_delay=10.0)
def get_regions(self, region_code: Optional[str] = None) -> APIResponse:
    # ... 기존 코드

@retry_transient_errors(max_attempts=3, base_delay=1.0, max_delay=10.0)
def get_apartment_detail(self, apt_id: str) -> APIResponse:
    # ... 기존 코드

@retry_transient_errors(max_attempts=3, base_delay=1.0, max_delay=10.0)
def get_apartment_transactions(...) -> APIResponse:
    # ... 기존 코드
```

**Decision:** 각 메서드에 데코레이터 적용하는 방식 채택 (더 명확하고 테스트 용이)

**Step 4: 테스트 실행하여 통과 확인**

Run: `pytest tests/unit/test_hogangnono_api_client.py::test_retry_on_transient_error -v`
Expected: PASS

**Step 5: 커밋**

```bash
git add src/crawler/api/hogangnono_client.py tests/unit/test_hogangnono_api_client.py
git commit -m "feat: API 메서드에 재시도 로직 추가

- retry_transient_errors 데코레이터 적용
- 500/502/503/504 에러 시 자동 재시도 (최대 3회)
- 지수 백오프 및 jitter 적용
- 테스트 추가"
```

---

## Task 6: HogangnonoCrawler 계층적 크롤링 로직 (1/3): _filter_districts

**Files:**
- Modify: `src/crawler/crawlers/hogangnono.py:588-637`
- Test: `tests/unit/test_hogangnono_crawler.py` (기존)

**Step 1: _filter_districts 테스트 작성**

```python
# tests/unit/test_hogangnono_crawler.py에 추가

def test_filter_districts_all_seoul(hogangnono_crawler):
    """서울 전체 구 필터링"""
    all_regions = {
        "regionList": [
            {
                "regionCode": "11",
                "name": "서울",
                "children": [
                    {"regionCode": "11680", "name": "강남구"},
                    {"regionCode": "11650", "name": "서초구"}
                ]
            }
        ]
    }

    result = hogangnono_crawler._filter_districts(
        all_regions,
        regions=["11"],
        districts=None
    )

    assert len(result) == 2
    assert result[0]["regionCode"] == "11680"
    assert result[1]["regionCode"] == "11650"


def test_filter_districts_specific(hogangnono_crawler):
    """특정 구만 필터링"""
    all_regions = {
        "regionList": [
            {
                "regionCode": "11",
                "name": "서울",
                "children": [
                    {"regionCode": "11680", "name": "강남구"},
                    {"regionCode": "11650", "name": "서초구"},
                    {"regionCode": "11710", "name": "송파구"}
                ]
            }
        ]
    }

    result = hogangnono_crawler._filter_districts(
        all_regions,
        regions=None,
        districts=["11680", "11710"]
    )

    assert len(result) == 2
    assert result[0]["regionCode"] == "11680"
    assert result[1]["regionCode"] == "11710"
```

**Step 2: 테스트 실행하여 실패 확인**

Run: `pytest tests/unit/test_hogangnono_crawler.py::test_filter_districts_all_seoul -v`
Expected: FAIL with "AttributeError"

**Step 3: _filter_districts 메서드 구현**

```python
# src/crawler/crawlers/hogangnono.py
# crawl 메서드 이전에 추가

    def _filter_districts(
        self,
        all_regions: Dict[str, Any],
        regions: Optional[List[str]],
        districts: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """지역 필터링

        Args:
            all_regions: get_regions() 응답 데이터
            regions: 시/도 코드 리스트
            districts: 구/군 코드 리스트 (우선순위 높음)

        Returns:
            필터링된 구/군 목록
        """
        # districts가 명시되면 해당 구/군만 반환
        if districts:
            result = []
            for region in all_regions.get("regionList", []):
                for child in region.get("children", []):
                    if child["regionCode"] in districts:
                        result.append(child)
            return result

        # regions가 명시되면 해당 시/도의 모든 구/군 반환
        if regions:
            result = []
            for region in all_regions.get("regionList", []):
                if region["regionCode"] in regions:
                    result.extend(region.get("children", []))
            return result

        # 기본값: 서울만
        default_regions = ["11"]
        result = []
        for region in all_regions.get("regionList", []):
            if region["regionCode"] in default_regions:
                result.extend(region.get("children", []))
        return result
```

**Step 4: 테스트 실행하여 통과 확인**

Run: `pytest tests/unit/test_hogangnono_crawler.py::test_filter_districts_all_seoul -v`
Run: `pytest tests/unit/test_hogangnono_crawler.py::test_filter_districts_specific -v`
Expected: PASS (모두)

**Step 5: 커밋**

```bash
git add src/crawler/crawlers/hogangnono.py tests/unit/test_hogangnono_crawler.py
git commit -m "feat: _filter_districts 메서드 구현

- 시/도, 구/군 필터링 로직 추가
- districts 우선순위 > regions > 기본값(서울)
- 테스트 추가"
```

---

## Task 7: HogangnonoCrawler 계층적 크롤링 로직 (2/3): _crawl_district

**Files:**
- Modify: `src/crawler/crawlers/hogangnono.py`
- Modify: `tests/unit/test_hogangnono_crawler.py`

**Step 1: _crawl_district 테스트 작성**

```python
# tests/unit/test_hogangnono_crawler.py에 추가

def test_crawl_district(hogangnono_crawler):
    """단일 구/군 크롤링"""
    district = {
        "regionCode": "11680",
        "name": "강남구",
        "fullName": "서울특별시 강남구"
    }

    # Mock API 응답
    with patch.object(hogangnono_crawler, '_fetch_apartments_in_district') as mock_fetch:
        with patch.object(hogangnono_crawler.hogangnono_client, 'get_apartment_detail') as mock_detail:
            with patch.object(hogangnono_crawler.hogangnono_client, 'get_apartment_transactions') as mock_trans:
                with patch.object(hogangnono_crawler, '_save_apartment_data') as mock_save:
                    # 2개 단지 반환
                    mock_fetch.return_value = [
                        {"aptHash": "apt1", "aptName": "단지1"},
                        {"aptHash": "apt2", "aptName": "단지2"}
                    ]

                    # 상세 정보 Mock
                    mock_detail.return_value = APIResponse(
                        success=True,
                        data={"parkingCount": 100}
                    )

                    # 실거래 내역 Mock
                    mock_trans.return_value = APIResponse(
                        success=True,
                        data={"shortTermReport": []}
                    )

                    # 실행
                    hogangnono_crawler._crawl_district(district, full_period=False)

                    # 검증
                    assert mock_fetch.call_count == 1
                    assert mock_detail.call_count == 2
                    assert mock_trans.call_count == 2
                    assert mock_save.call_count == 2
```

**Step 2: 테스트 실행하여 실패 확인**

Run: `pytest tests/unit/test_hogangnono_crawler.py::test_crawl_district -v`
Expected: FAIL

**Step 3: _crawl_district 메서드 구현**

```python
# src/crawler/crawlers/hogangnono.py
# _filter_districts 메서드 다음에 추가

    def _crawl_district(
        self,
        district: Dict[str, Any],
        full_period: bool
    ) -> None:
        """단일 구/군 크롤링

        Args:
            district: 구/군 정보 딕셔너리
            full_period: 전체 기간 수집 여부
        """
        district_code = district["regionCode"]
        district_name = district["name"]

        self.logger.info(
            "crawling_district",
            district_code=district_code,
            district_name=district_name
        )

        # 2-1. 단지 목록 수집
        apartments = self._fetch_apartments_in_district(district)
        self.logger.info(
            "apartments_fetched",
            district=district_name,
            count=len(apartments)
        )

        # 2-2. 각 단지 상세 정보 및 실거래 내역 수집
        for apt in apartments:
            apt_id = apt.get("aptHash")
            if not apt_id:
                self.logger.warning(
                    "missing_apt_id",
                    apartment=apt
                )
                continue

            try:
                # 단지 상세 정보
                apt_detail_response = self.hogangnono_client.get_apartment_detail(apt_id)
                if not apt_detail_response.success:
                    self.logger.error(
                        "failed_to_get_detail",
                        apt_id=apt_id,
                        error=apt_detail_response.error
                    )
                    # 404는 건너뛰기, 나머지는 예외 발생
                    if apt_detail_response.status_code != 404:
                        raise Exception(f"Failed to get detail for {apt_id}: {apt_detail_response.error}")
                    continue

                # 실거래 내역
                transactions_response = self.hogangnono_client.get_apartment_transactions(
                    apt_id,
                    trade_type=0,  # 매매
                    full_period=full_period
                )
                if not transactions_response.success:
                    self.logger.error(
                        "failed_to_get_transactions",
                        apt_id=apt_id,
                        error=transactions_response.error
                    )
                    raise Exception(f"Failed to get transactions for {apt_id}: {transactions_response.error}")

                # 데이터 병합 및 저장
                self._save_apartment_data(
                    apt,
                    apt_detail_response.data,
                    transactions_response.data
                )

            except Exception as e:
                self.logger.error(
                    "apartment_processing_failed",
                    apt_id=apt_id,
                    error=str(e)
                )
                raise  # 실패 시 즉시 중단

        self.logger.info(
            "district_crawling_completed",
            district=district_name
        )
```

**Step 4: 테스트 실행하여 통과 확인**

Run: `pytest tests/unit/test_hogangnono_crawler.py::test_crawl_district -v`
Expected: PASS

**Step 5: 커밋**

```bash
git add src/crawler/crawlers/hogangnono.py tests/unit/test_hogangnono_crawler.py
git commit -m "feat: _crawl_district 메서드 구현

- 구/군 단위 크롤링 로직
- 단지 목록 → 상세 정보 → 실거래 내역 순차 수집
- 404 에러는 건너뛰기, 나머지 에러는 즉시 중단
- 테스트 추가"
```

---

## Task 8: HogangnonoCrawler 계층적 크롤링 로직 (3/3): crawl 메서드

**Files:**
- Modify: `src/crawler/crawlers/hogangnono.py:588-637`
- Modify: `tests/unit/test_hogangnono_crawler.py`

**Step 1: crawl 메서드 테스트 작성**

```python
# tests/unit/test_hogangnono_crawler.py에 추가

def test_crawl_seoul_default(hogangnono_crawler):
    """기본값 서울 크롤링"""
    with patch.object(hogangnono_crawler.hogangnono_client, 'get_regions') as mock_regions:
        with patch.object(hogangnono_crawler, '_filter_districts') as mock_filter:
            with patch.object(hogangnono_crawler, '_crawl_district') as mock_crawl:
                with patch.object(hogangnono_crawler, '_save_checkpoint') as mock_checkpoint:
                    # Mock 응답
                    mock_regions.return_value = APIResponse(
                        success=True,
                        data={"regionList": []}
                    )
                    mock_filter.return_value = [
                        {"regionCode": "11680", "name": "강남구"}
                    ]

                    # 실행
                    stats = hogangnono_crawler.crawl()

                    # 검증
                    mock_regions.assert_called_once()
                    mock_filter.assert_called_once()
                    mock_crawl.assert_called_once()
                    assert stats["dongs_processed"] == 1
```

**Step 2: 테스트 실행하여 실패 확인**

Run: `pytest tests/unit/test_hogangnono_crawler.py::test_crawl_seoul_default -v`
Expected: FAIL (기존 crawl 메서드와 충돌)

**Step 3: crawl 메서드 재구현**

```python
# src/crawler/crawlers/hogangnono.py
# 기존 crawl 메서드 (588-637행) 완전 교체

    def crawl(
        self,
        regions: Optional[List[str]] = None,
        districts: Optional[List[str]] = None,
        full_period: bool = False
    ) -> Dict[str, Any]:
        """전체 크롤링 실행

        Args:
            regions: 시/도 코드 리스트 (기본값: ["11"] 서울)
            districts: 구/군 코드 리스트 (우선순위 높음)
            full_period: 전체 기간 실거래 내역 수집 여부

        Returns:
            크롤링 통계 정보
        """
        start_time = time.time()

        # 1. 지역 정보 수집
        self.logger.info("fetching_regions")
        regions_response = self.hogangnono_client.get_regions()
        if not regions_response.success:
            raise Exception(f"Failed to get regions: {regions_response.error}")

        all_regions = regions_response.data
        target_districts = self._filter_districts(all_regions, regions, districts)
        self.logger.info(
            "target_districts_filtered",
            count=len(target_districts)
        )

        # 2. Checkpoint 로드
        checkpoint_path = self.output_dir / "checkpoint.json"
        completed_districts = []
        if checkpoint_path.exists():
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)
                completed_districts = checkpoint.get("completed_districts", [])
            self.logger.info(
                "checkpoint_loaded",
                completed_count=len(completed_districts)
            )

        # 3. 구/군별 크롤링
        processed_count = 0
        for district in target_districts:
            district_code = district["regionCode"]

            if district_code in completed_districts:
                self.logger.info(
                    "district_skipped",
                    district=district["name"],
                    reason="already_completed"
                )
                continue

            self._crawl_district(district, full_period)
            self._save_checkpoint(district, checkpoint_path)
            processed_count += 1

        # 4. 통계 반환
        duration = time.time() - start_time
        stats = {
            "dongs_processed": processed_count,
            "total_dongs": len(target_districts),
            "duration_seconds": duration
        }

        self.logger.info(
            "crawling_completed",
            **stats
        )

        return stats

    def _save_checkpoint(
        self,
        district: Dict[str, Any],
        checkpoint_path: Path
    ) -> None:
        """Checkpoint 저장"""
        # 기존 checkpoint 로드
        checkpoint = {}
        if checkpoint_path.exists():
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)

        # 완료된 구/군 추가
        completed = checkpoint.get("completed_districts", [])
        district_code = district["regionCode"]
        if district_code not in completed:
            completed.append(district_code)

        checkpoint["completed_districts"] = completed
        checkpoint["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        # 저장
        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)

        self.logger.info(
            "checkpoint_saved",
            district=district["name"]
        )
```

**Step 4: 테스트 실행하여 통과 확인**

Run: `pytest tests/unit/test_hogangnono_crawler.py::test_crawl_seoul_default -v`
Expected: PASS

**Step 5: 커밋**

```bash
git add src/crawler/crawlers/hogangnono.py tests/unit/test_hogangnono_crawler.py
git commit -m "feat: crawl 메서드 계층적 크롤링으로 재구현

- regions → districts → apartments 순차 수집
- checkpoint 기반 재시작 지원
- 구/군 단위 점진적 처리
- 통계 정보 반환
- 테스트 추가"
```

---

## Task 9: _fetch_apartments_in_district 및 _save_apartment_data 구현

**Files:**
- Modify: `src/crawler/crawlers/hogangnono.py`
- Modify: `tests/unit/test_hogangnono_crawler.py`

**Step 1: 헬퍼 메서드 테스트 작성**

```python
# tests/unit/test_hogangnono_crawler.py에 추가

def test_fetch_apartments_in_district(hogangnono_crawler):
    """구/군 내 단지 목록 수집"""
    district = {"regionCode": "11680", "name": "강남구"}

    with patch.object(hogangnono_crawler.hogangnono_client, 'get_apartments_bounding') as mock_bounding:
        mock_bounding.return_value = APIResponse(
            success=True,
            data=[
                {"aptHash": "apt1", "aptName": "단지1"},
                {"aptHash": "apt2", "aptName": "단지2"}
            ]
        )

        result = hogangnono_crawler._fetch_apartments_in_district(district)

        assert len(result) == 2
        assert result[0]["aptHash"] == "apt1"


def test_save_apartment_data(hogangnono_crawler):
    """단지 데이터 저장"""
    apt = {"aptHash": "apt1", "aptName": "단지1"}
    apt_detail = {"parkingCount": 100, "floorAreaRatio": 250.5}
    transactions = {"shortTermReport": [{"date": "2025-01", "price": 100000}]}

    with patch.object(hogangnono_crawler.hogangnono_writer, 'save_complexes') as mock_complexes:
        with patch.object(hogangnono_crawler.hogangnono_writer, 'save_transactions') as mock_trans:
            hogangnono_crawler._save_apartment_data(apt, apt_detail, transactions)

            mock_complexes.assert_called_once()
            mock_trans.assert_called_once()
```

**Step 2: 테스트 실행하여 실패 확인**

Run: `pytest tests/unit/test_hogangnono_crawler.py::test_fetch_apartments_in_district -v`
Expected: FAIL

**Step 3: 헬퍼 메서드 구현**

```python
# src/crawler/crawlers/hogangnono.py
# _crawl_district 메서드 다음에 추가

    def _fetch_apartments_in_district(
        self,
        district: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """구/군 내 모든 단지 수집

        좌표 기반 bounding API 사용
        TODO: 구/군을 여러 그리드로 분할하여 수집 (현재는 단순 구현)

        Args:
            district: 구/군 정보

        Returns:
            단지 목록
        """
        # 구/군 코드로 좌표 범위 계산 (간단한 예시)
        # 실제로는 구/군별 좌표 매핑 테이블 필요
        district_code = district["regionCode"]

        # 기본 서울 좌표 (임시)
        # TODO: 구/군별 정확한 좌표 매핑
        bbox = (126.7, 37.4, 127.2, 37.7)

        search_params = SearchParams(
            bbox=bbox,
            level=14,
            tradeType=0,  # 매매
            aptType=1  # 아파트
        )

        response = self.hogangnono_client.get_apartments_bounding(search_params)
        if not response.success:
            raise Exception(f"Failed to fetch apartments: {response.error}")

        # 응답 데이터 파싱
        apartments = response.data or []
        return apartments

    def _save_apartment_data(
        self,
        apt: Dict[str, Any],
        apt_detail: Optional[Dict[str, Any]],
        transactions: Optional[Dict[str, Any]]
    ) -> None:
        """단지 정보 및 실거래 내역 CSV 저장

        Args:
            apt: 단지 기본 정보 (bounding API)
            apt_detail: 단지 상세 정보 (detail API)
            transactions: 실거래 내역 (transactions API)
        """
        # 단지 정보 병합
        complex_data = {**apt}
        if apt_detail:
            complex_data.update(apt_detail)

        # 단지 정보 저장
        self.hogangnono_writer.save_complexes([complex_data])

        # 실거래 내역 저장
        if transactions and "shortTermReport" in transactions:
            transaction_list = []
            for report in transactions["shortTermReport"]:
                for trade in report.get("trades", []):
                    trade_data = {
                        "aptHash": apt["aptHash"],
                        "date": report["date"],
                        **trade
                    }
                    transaction_list.append(trade_data)

            if transaction_list:
                self.hogangnono_writer.save_transactions(transaction_list)
```

**Step 4: 테스트 실행하여 통과 확인**

Run: `pytest tests/unit/test_hogangnono_crawler.py::test_fetch_apartments_in_district -v`
Run: `pytest tests/unit/test_hogangnono_crawler.py::test_save_apartment_data -v`
Expected: PASS (모두)

**Step 5: 커밋**

```bash
git add src/crawler/crawlers/hogangnono.py tests/unit/test_hogangnono_crawler.py
git commit -m "feat: 단지 수집 및 저장 헬퍼 메서드 구현

- _fetch_apartments_in_district: 좌표 기반 단지 목록 수집
- _save_apartment_data: 단지 및 실거래 내역 CSV 저장
- 데이터 병합 로직 추가
- 테스트 추가"
```

---

## Task 10: scripts/main.py 인자 추가

**Files:**
- Modify: `scripts/main.py`

**Step 1: CLI 인자 테스트 (수동)**

Run: `python scripts/main.py --help`
Expected: 기존 옵션만 표시

**Step 2: argparse에 신규 인자 추가**

```python
# scripts/main.py
# argparse 섹션 수정

parser.add_argument(
    "--regions",
    type=str,
    help="크롤링할 시/도 코드 (쉼표 구분, 예: 11,26)",
    default=None
)

parser.add_argument(
    "--districts",
    type=str,
    help="크롤링할 구/군 코드 (쉼표 구분, 예: 11680,11650)",
    default=None
)

parser.add_argument(
    "--full-period",
    action="store_true",
    help="전체 기간 실거래 내역 수집 (기본값: 최근 3년)",
    default=False
)

# 기존 --district 옵션과 충돌 확인 후 제거 또는 이름 변경
```

**Step 3: 인자 파싱 및 crawler.crawl() 호출**

```python
# scripts/main.py
# main() 함수 수정

def main():
    args = parser.parse_args()

    # regions/districts 파싱
    regions = None
    if args.regions:
        regions = [r.strip() for r in args.regions.split(",")]

    districts = None
    if args.districts:
        districts = [d.strip() for d in args.districts.split(",")]

    # Crawler 초기화
    config = CrawlerConfig.from_env()
    crawler = HogangnonoCrawler(config, output_dir=args.output)

    # 크롤링 실행
    stats = crawler.crawl(
        regions=regions,
        districts=districts,
        full_period=args.full_period
    )

    # 결과 출력
    print(f"크롤링 완료: {stats}")
```

**Step 4: 테스트 실행**

Run: `python scripts/main.py --help`
Expected: 새 옵션 표시 (--regions, --districts, --full-period)

Run: `python scripts/main.py --regions 11 --districts 11680` (실제 실행하지 말고 dry-run 확인)

**Step 5: 커밋**

```bash
git add scripts/main.py
git commit -m "feat: main.py에 계층적 크롤링 옵션 추가

- --regions: 시/도 필터링
- --districts: 구/군 필터링
- --full-period: 전체 기간 실거래 내역
- 기존 인터페이스와 통합"
```

---

## Task 11: 통합 테스트

**Files:**
- Create: `tests/integration/test_hogangnono_hierarchical_crawling.py`

**Step 1: 통합 테스트 작성**

```python
# tests/integration/test_hogangnono_hierarchical_crawling.py
import pytest
from pathlib import Path
from crawler.config import CrawlerConfig
from crawler.crawlers.hogangnono import HogangnonoCrawler


@pytest.mark.integration
def test_hierarchical_crawling_single_district(tmp_path):
    """단일 구/군 계층적 크롤링 (실제 API 호출)"""
    config = CrawlerConfig.from_env()
    output_dir = tmp_path / "output"

    crawler = HogangnonoCrawler(config, output_dir=output_dir)

    # 강남구만 크롤링 (테스트용)
    stats = crawler.crawl(
        regions=None,
        districts=["11680"],
        full_period=False
    )

    # 검증
    assert stats["dongs_processed"] == 1
    assert stats["total_dongs"] == 1

    # CSV 파일 생성 확인
    complexes_csv = output_dir / "hogangnono_complexes.csv"
    transactions_csv = output_dir / "hogangnono_transactions.csv"

    assert complexes_csv.exists()
    assert transactions_csv.exists()

    # 데이터 존재 확인
    with open(complexes_csv, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) > 1  # 헤더 + 최소 1개 데이터
```

**Step 2: 통합 테스트 실행**

Run: `pytest tests/integration/test_hogangnono_hierarchical_crawling.py -m integration -v`
Expected: PASS (실제 API 호출하여 데이터 수집)

**Note:** 이 테스트는 실제 API를 호출하므로 느립니다. CI에서는 선택적으로 실행합니다.

**Step 3: 커밋**

```bash
git add tests/integration/test_hogangnono_hierarchical_crawling.py
git commit -m "test: 계층적 크롤링 통합 테스트 추가

- 단일 구/군 크롤링 시나리오
- 실제 API 호출 테스트
- CSV 파일 생성 검증"
```

---

## Task 12: README 및 문서 업데이트

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

**Step 1: README 업데이트**

```markdown
# README.md에 추가

## 계층적 크롤링

호갱노노 API를 통해 전국 아파트 데이터를 계층적으로 수집합니다.

### 실행 예시

```bash
# 서울 전체 크롤링 (기본값, 최근 3년)
python scripts/main.py

# 서울 + 부산 크롤링
python scripts/main.py --regions 11,26

# 강남구만 크롤링
python scripts/main.py --districts 11680

# 전체 기간 데이터 수집
python scripts/main.py --full-period

# 중단된 지점부터 재개
python scripts/main.py --resume
```

### 데이터 흐름

1. `/api/v2/regions` - 시/도, 구/군 목록 수집
2. `/api/v2/pois-bounding` - 단지 목록 수집
3. `/api/v2/apts/{aptId}` - 단지 상세 정보
4. `/api/v2/apts/{aptId}/monthly-reports` - 실거래 내역

### 예상 소요 시간

- 서울 (25개 구): 약 2.8시간
- 전국 (250개 구/군): 약 56시간
```

**Step 2: CLAUDE.md 업데이트**

```markdown
# CLAUDE.md에 추가

## 호갱노노 크롤러 사용법

### API 메서드

- `get_regions()`: 시/도, 구/군 목록 조회
- `get_apartment_detail(apt_id)`: 단지 상세 정보
- `get_apartment_transactions(apt_id, full_period)`: 실거래 내역

### 크롤링 실행

```python
from crawler.crawlers.hogangnono import HogangnonoCrawler

crawler = HogangnonoCrawler(config)
stats = crawler.crawl(
    regions=["11"],  # 서울
    districts=None,
    full_period=False
)
```
```

**Step 3: 커밋**

```bash
git add README.md CLAUDE.md
git commit -m "docs: 계층적 크롤링 문서 업데이트

- README에 실행 예시 추가
- CLAUDE.md에 API 사용법 추가
- 데이터 흐름 및 소요 시간 설명"
```

---

## 완료 체크리스트

- [ ] Task 1: get_regions API 메서드 구현
- [ ] Task 2: get_apartment_detail API 메서드 구현
- [ ] Task 3: get_apartment_transactions API 메서드 구현
- [ ] Task 4: AdaptiveRateLimiter 통합
- [ ] Task 5: retry 데코레이터 적용
- [ ] Task 6: _filter_districts 구현
- [ ] Task 7: _crawl_district 구현
- [ ] Task 8: crawl 메서드 재구현
- [ ] Task 9: 헬퍼 메서드 구현
- [ ] Task 10: main.py 인자 추가
- [ ] Task 11: 통합 테스트
- [ ] Task 12: 문서 업데이트

---

## 추가 개선 사항 (선택)

다음 항목들은 기본 구현 완료 후 선택적으로 진행:

1. **구/군별 정확한 좌표 매핑**: `_fetch_apartments_in_district`에서 하드코딩된 좌표를 구/군별 정확한 좌표로 교체
2. **그리드 분할 로직**: 큰 구/군을 여러 그리드로 분할하여 600개 제한 우회
3. **병렬 처리**: asyncio/aiohttp로 성능 개선
4. **데이터베이스 저장**: PostgreSQL 연동
5. **모니터링 대시보드**: 진행 상황 실시간 모니터링

---

## 참고 사항

- **TDD 준수**: 모든 Task는 테스트 → 실패 → 구현 → 통과 → 커밋 순서
- **Small Commits**: 각 Task마다 커밋
- **Error Handling**: 404는 건너뛰기, 나머지는 즉시 중단
- **Rate Limiting**: AdaptiveRateLimiter가 자동 조절
- **Checkpoint**: 구/군 단위 저장, 재시작 지원

---

**구현 시작 준비 완료!** 🚀
