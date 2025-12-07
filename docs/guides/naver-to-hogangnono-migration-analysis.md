# 네이버 부동산 크롤러 → 호갱노노 전환 분석 보고서

## 1. 현재 아키텍처의 핵심 패턴과 설계 원칙

### 1.1. 구조화된 계층 설계
- **Coordinator 패턴**: `CrawlCoordinator`가 전체 크롤링 프로세스를 조정
- **전문화된 Writer**: `ComplexesCSVWriter`, `TransactionCSVWriter`로 데이터 저장 분리
- **유틸리티 모듈화**: Rate limiting, 재시도, 체크포인트 등 기능 분리

### 1.2. 적응형 처리 메커니즘
- **AdaptiveRateLimiter**: 성공/실패에 따라 동적으로 요청 간격 조절
- **CheckpointManager**: 중단된 크롤링 재개 지원
- **ProgressTracker**: 실시간 진행 상황 모니터링

### 1.3. 에러 핸들링과 안정성
- **재시도 로직**: `@retry_with_backoff` 데코레이터
- **세션 관리**: `NaverSessionManager`로 인증 상태 유지
- **BrowserManager**: 브라우저 자원 효율적 관리

## 2. BaseCrawler 추상화 구조의 재사용성

### 2.1. 현재 BaseCrawler 분석
```python
class BaseCrawler(ABC):
    @abstractmethod
    def fetch(self, url: str) -> str
    @abstractmethod
    def parse(self, html: str) -> list[dict[str, Any]]
    @abstractmethod
    def get_url(self) -> str
```

### 2.2. 재사용성 평가
**재사용 가능**:
- 템플릿 메서드 패턴은 다른 사이트에도 적용 가능
- 간단한 인터페이스로 새 크롤러 구현 용이

**확장 필요**:
- 호갱노노는 API 기반이므로 `fetch()` 메서드 시그니처 변경 필요
- 페이지네이션 처리를 위한 추가 메서드 필요
- 인증 처리를 위한 추상 메서드 추가 제안

### 2.3. 개선 제안
```python
class BaseCrawler(ABC):
    @abstractmethod
    def fetch_data(self, params: dict[str, Any]) -> dict[str, Any] | list[dict[str, Any]]

    @abstractmethod
    def parse_response(self, response: dict[str, Any] | list) -> list[dict[str, Any]]

    @abstractmethod
    def get_auth_headers(self) -> dict[str, str]

    def handle_pagination(self, response: dict[str, Any]) -> bool:
        """페이지네이션 처리 - 기본 구현 제공"""
        return response.get("has_next", False)
```

## 3. Rate Limiting 및 유틸리티 활용 방안

### 3.1. AdaptiveRateLimiter
**그대로 재사용 가능**:
- 호갱노노도 API 레이트 리밋이 있을 가능성이 높음
- 현재 구조는 사이트에 종속적이지 않음

**설정 조정 필요**:
```python
# 호갱노노에 맞게 초기값 조정
rate_limiter = AdaptiveRateLimiter(
    initial_delay=1.0,  # 더 짧은 간격으로 시작
    min_delay=0.5,
    max_delay=5.0,
    success_threshold=5  # 5회 성공 후 간격 감소
)
```

### 3.2. 재시도 로직
**재사용 가능**:
- `Retryable` 클래스는 일반적이어서 그대로 사용 가능
- 재시도 전략만 호갱노노 API에 맞게 조정

### 3.3. CheckpointManager
**그대로 사용 가능**:
- 중단/재개 기능은 호갱노노에도 필요
- 현재 구조는 특정 API에 종속되지 않음

## 4. CSV 출력 포맷과 호환성 고려사항

### 4.1. 현재 CSV 스키마 분석
**Complexes CSV 필드**:
- 기본 정보: complex_id, complex_name, address
- 상세 정보: build_year, household_count, dong_count
- 통계 정보: min/max_deal_price, deal_count 등

**Transaction CSV 필드**:
- 거래 기본: complex_id, trade_type, trade_date
- 가격 정보: deal_price, deposit, monthly_rent
- 상세 정보: floor, area, direction

### 4.2. 호갱노노 데이터 매핑 전략
**공통 필드 (그대로 사용)**:
- complex_id → 호갱노노 단지 ID
- complex_name → 단지명
- trade_type → 매매/전세/월세 구분
- deal_price → 거래 가격

**매핑 필요 필드**:
- 네이버의 pyeong_type → 호갱노노의 전용면적/공급면적
- 네이버의 cortarNo → 호갱노노의 지역 코드

### 4.3. CSV Writer 재사용 계획
**ComplexesCSVWriter**:
- `_normalize_complex_data()` 메서드만 호갱노노 데이터 구조에 맞게 수정
- 통계 필드 계산 로직은 그대로 활용

**TransactionCSVWriter**:
- `_normalize_transaction()` 메서드만 필드 매핑 수정
- 기본적인 CSV write/append 로직은 그대로 사용

## 5. 의존성 주입 및 설정 관리 개선점

### 5.1. 현재 CrawlerConfig 한계
- 네이버 특화 설정 (cortar_no 등)이 포함됨
- API 인증 정보 관리가 미흡함
- 환경별 설정 분리가 명확하지 않음

### 5.2. 개선 제안
```python
from abc import ABC, abstractmethod
from typing import Protocol

class SiteConfig(Protocol):
    """사이트별 설정 프로토콜"""
    api_base_url: str
    auth_headers: dict[str, str]
    rate_limits: dict[str, int]
    field_mappings: dict[str, str]

class HogangNonoConfig(SiteConfig):
    api_base_url: str = "https://hogangnono.com/api"
    auth_headers: dict[str, str] = {"Authorization": "Bearer {token}"}
    rate_limits: dict[str, int] = {"requests_per_second": 10}
    field_mappings: dict[str, str] = {
        "complex_id": "complexNo",
        "deal_price": "price",
        # ...
    }

class CrawlerConfig(BaseModel):
    """공통 설정만 유지"""
    timeout: int = 30
    retry_attempts: int = 3
    output_dir: Path = Path("output")

    # 사이트별 설정은 의존성 주입
    site_config: SiteConfig

    @classmethod
    def create_for_site(cls, site: str, **overrides) -> "CrawlerConfig":
        if site == "naver":
            site_config = NaverConfig()
        elif site == "hogangnono":
            site_config = HogangNonoConfig()
        else:
            raise ValueError(f"Unsupported site: {site}")

        return cls(site_config=site_config, **overrides)
```

## 6. 마이그레이션 전략

### 6.1. 단계적 접근
**Phase 1: 기반 구조 마이그레이션**
1. BaseCrawler 확장하여 API 기반 크롤러 지원
2. Config 재설계 및 사이트별 분리
3. 공통 유틸리티 그대로 이전

**Phase 2: 데이터 파이프라인 조정**
1. CSV Writer 필드 매핑 로직 수정
2. Coordinator의 사이트 의존성 제거
3. 데이터 파싱 로직 새로 구현

**Phase 3: 최적화**
1. 호갱노노 API 특화 최적화
2. 병렬 처리 도입 (API 제한 허용 시)
3. 캐싱 전략 구현

### 6.2. 우선순위 작업
1. **높음**: BaseCrawler 확장, Config 재설계
2. **중간**: CSV Writer 매핑, Coordinator 수정
3. **낮음**: 성능 최적화, 추가 기능 구현

### 6.3. 리스크 관리
- 네이버 크롤러는 유지하며 병행 개발
- 호갱노노 API 제한 사항 사전 조사
- 데이터 형식 차이로 인한 파싱 오류 주의

## 7. 결론

네이버 부동산 크롤러의 아키텍처는 잘 설계되어 있어 **60-70% 재사용 가능**합니다. 특히 Coordinator 패턴, Rate limiting, 체크포인트 관리 등 핵심 인프라는 그대로 활용할 수 있습니다. 주요 변경 사항은 API 클라이언트 계층과 데이터 파싱 부분에 집중될 것입니다.

성공적인 전환을 위해서는:
1. 명확한 인터페이스 정의
2. 점진적 마이그레이션 전략
3. 충분한 테스트 커버리지 확보
가 필요합니다.