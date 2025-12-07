# APICrawler 사용 가이드

APICrawler는 BaseCrawler를 확장하여 API 기반의 데이터 수집을 위한 추상 클래스입니다. 세션 관리, 헤더 설정, 인증 처리, 페이지네이션, 에러 핸들링, Rate Limiting 등 API 크롤링에 필요한 공통 기능을 제공합니다.

## 주요 기능

### 1. 세션 관리
- requests.Session을 사용한 커넥션 풀링
- 기본 인증 (Basic Auth) 및 API 키 인증 지원
- 컨텍스트 매니저를 통한 자원 정리

### 2. 동적 헤더 설정
- 기본 헤더 자동 설정 (User-Agent, Accept 등)
- `get_dynamic_headers()` 메서드 오버라이드를 통한 동적 헤더 추가
- 인증 헤더 자동 관리

### 3. Rate Limiting
- AdaptiveRateLimiter를 통한 지능적 호출 간격 조절
- 성공/실패에 따른 동적 지연 시간 조정
- 429 에러 발생 시 자동 백오프

### 4. 재시도 로직
- 지수 백오프와 지터를 적용한 재시도 전략
- 재시도 가능한 예외 자동 판별
- 상세한 재시도 로깅

### 5. 페이지네이션 처리
- `handle_pagination()` 메서드를 통한 자동 페이지네이션
- 다양한 페이지네이션 형식 지원
- 페이지별 데이터 자동 병합

### 6. 에러 핸들링
- APIError 커스텀 예외를 통한 상세한 에러 정보 제공
- HTTP 상태 코드별 에러 처리
- JSON 파싱 에러 처리

## 기본 사용법

### 1. APICrawler 상속 구현

```python
from crawler.crawlers.api import APICrawler
from crawler.config import CrawlerConfig
from typing import Any, Dict, List

class MyAPICrawler(APICrawler):
    def __init__(self, config: CrawlerConfig):
        super().__init__(
            config=config,
            base_url="https://api.example.com",
            api_key="your-api-key",
            rate_limit_delay=2.0,  # 2초 간격
        )

    def get_endpoint(self) -> str:
        """API 엔드포인트 반환"""
        return "/v1/search"

    def get_params(self) -> Dict[str, Any]:
        """요청 파라미터 반환"""
        return {
            "query": "search term",
            "limit": 100,
        }

    def parse_response(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """API 응답 파싱"""
        return response_data.get("items", [])

    def get_dynamic_headers(self) -> Dict[str, str]:
        """동적 헤더 추가"""
        return {
            "X-Custom-Header": "custom-value",
        }
```

### 2. 사용 예시

```python
# 설정 생성
config = CrawlerConfig.from_env()

# 크롤러 인스턴스 생성
crawler = MyAPICrawler(config)

# 데이터 크롤링
try:
    # crawl() 메서드는 BaseCrawler에서 상속
    results = crawler.crawl()
    print(f"총 {len(results)}개의 데이터를 수집했습니다.")
except APIError as e:
    print(f"API 에러 발생: {e}")
    print(f"상태 코드: {e.status_code}")
    print(f"요청 URL: {e.request_url}")
```

### 3. 컨텍스트 매니저 사용

```python
# 자동 리소스 정리를 위해 with 구문 사용
with MyAPICrawler(config) as crawler:
    results = crawler.crawl()
# 자동으로 cleanup()이 호출됨
```

## 고급 기능

### 1. POST 요청 처리

```python
class PostAPICrawler(APICrawler):
    def get_request_method(self) -> str:
        """POST 메서드 사용"""
        return "POST"

    def get_request_body(self) -> Dict[str, Any]:
        """POST 요청 바디"""
        return {
            "action": "search",
            "filters": {
                "category": "news",
                "date_range": "7d",
            }
        }
```

### 2. 페이지네이션 처리

```python
class PaginatedAPICrawler(APICrawler):
    def get_params(self) -> Dict[str, Any]:
        return {
            "page": 1,
            "size": 50,
        }

    def crawl_all_pages(self) -> List[Dict[str, Any]]:
        """모든 페이지 데이터 가져오기"""
        # 첫 페이지 요청
        first_response = self._make_request(
            url=self.get_url(),
            params=self.get_params(),
        )

        # 페이지네이션 처리
        def fetch_next_page(page: int):
            params = self.get_params()
            params["page"] = page
            return self._make_request(
                url=self.get_url(),
                params=params,
            )

        return self.handle_pagination(
            initial_response=first_response,
            fetch_next_page=fetch_next_page,
        )

    def parse_page(self, response: Dict[str, Any], page: int) -> Tuple[List[Dict[str, Any]], bool]:
        """페이지별 데이터 파싱"""
        items = response.get("items", [])
        has_more = response.get("has_next", False)
        return items, has_more
```

### 3. 커스텀 에러 핸들링

```python
class RobustAPICrawler(APICrawler):
    def _validate_response(self, response) -> None:
        """커스텀 응답 검증"""
        # 기본 검증 실행
        super()._validate_response(response)

        # 추가 검증 로직
        try:
            data = response.json()
            if data.get("status") == "error":
                raise APIError(
                    f"API returned error: {data.get('message')}",
                    status_code=response.status_code,
                    response_data=data,
                    request_url=response.url,
                )
        except json.JSONDecodeError:
            pass  # 이미 기본 검증에서 처리됨
```

### 4. 동적 Rate Limiting

```python
class AdaptiveAPICrawler(APICrawler):
    def __init__(self, config: CrawlerConfig):
        super().__init__(
            config=config,
            rate_limit_delay=1.0,  # 초기 지연 시간
        )

        # Rate Limiter 커스터마이징
        self.rate_limiter = AdaptiveRateLimiter(
            initial_delay=1.0,
            min_delay=0.5,      # 최소 0.5초
            max_delay=10.0,     # 최대 10초
        )

    def handle_rate_limit_error(self, response: Dict[str, Any]):
        """Rate Limit 에러 핸들링"""
        retry_after = response.get("retry_after", 60)
        self.logger.warning(
            "rate_limit_hit",
            retry_after=retry_after,
        )
        time.sleep(retry_after)
```

## 베스트 프랙티스

### 1. 설정 관리
```python
# 환경 변수를 통한 설정 관리
config = CrawlerConfig.from_env()

# 또는 직접 설정
config = CrawlerConfig(
    timeout=30.0,
    user_agent="MyAPICrawler/1.0",
)
```

### 2. 로깅 활용
```python
import structlog

# 구조화된 로깅
logger = structlog.get_logger()

class LoggedAPICrawler(APICrawler):
    def parse_response(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        items = response_data.get("items", [])

        # 상세 로깅
        self.logger.info(
            "response_parsed",
            item_count=len(items),
            response_keys=list(response_data.keys()),
        )

        return items
```

### 3. 캐싱 구현
```python
from functools import lru_cache
import hashlib

class CachedAPICrawler(APICrawler):
    @lru_cache(maxsize=1000)
    def _cached_request(self, cache_key: str):
        """캐시된 요청"""
        return super()._make_request(...)

    def _make_request(self, url: str, **kwargs):
        # 캐시 키 생성
        key_data = f"{url}_{kwargs}"
        cache_key = hashlib.md5(key_data.encode()).hexdigest()

        return self._cached_request(cache_key)
```

## 테스트 팁

### 1. Mock을 사용한 테스트
```python
import pytest
from unittest.mock import Mock, patch

def test_api_crawler():
    config = CrawlerConfig.from_env()

    with patch('requests.Session.request') as mock_request:
        # Mock 응답 설정
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": [{"id": 1}]}
        mock_request.return_value = mock_response

        # 테스트
        crawler = MyAPICrawler(config)
        results = crawler.crawl()

        assert len(results) == 1
        assert results[0]["id"] == 1
```

### 2. 통합 테스트
```python
@pytest.mark.integration
def test_api_integration():
    """실제 API를 사용한 통합 테스트"""
    config = CrawlerConfig.from_env()

    crawler = MyAPICrawler(config)
    results = crawler.crawl()

    assert isinstance(results, list)
    assert len(results) > 0
```

## 주의사항

1. **Rate Limiting**: API의 Rate Limit 정책을 확인하고 적절한 지연 시간을 설정하세요
2. **에러 처리**: 각 API의 에러 응답 형식을 확인하고 적절히 처리하세요
3. **인증**: API 키나 다른 인증 정보를 안전하게 관리하세요 (환경 변수 사용 권장)
4. **모니터링**: API 호출 성공률, 응답 시간 등을 모니터링하세요
5. **캐싱**: 반복적인 요청은 캐싱하여 API 사용량을 최적화하세요