# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

HomeSweetHome Crawler Boilerplate는 Python 기반 웹 크롤링 보일러플레이트입니다. 정적/동적 사이트 크롤링을 지원하며, 크롤링한 데이터를 CSV 파일로 저장합니다.

**현재 목표**: 호갱노노 부동산 매물 데이터 크롤링

**중요**: 이 프로젝트는 **호갱노노 부동산 크롤링만** 수행합니다. 국토교통부 공공데이터 API는 사용하지 않습니다.

## 기술 스택

- **Python**: 3.11+
- **패키지 매니저**: uv (Astral의 Rust 기반 고속 패키지 매니저)
- **정적 크롤링**: requests + BeautifulSoup + lxml
- **동적 크롤링**: Playwright (sync API)
- **데이터 저장**: Python 표준 csv 모듈
- **로깅**: structlog (구조화된 로깅)
- **코드 품질**: ruff (linting/formatting), mypy (type checking, strict mode)
- **테스트**: pytest

## 프로젝트 구조

```
homesweethome/
├── src/crawler/                   # 메인 소스 코드 (src layout)
│   ├── __init__.py
│   ├── config.py                 # CrawlerConfig (dataclass 기반)
│   ├── coordinator.py            # CrawlCoordinator (크롤링 조정 및 점진적 저장)
│   ├── progress_tracker.py       # ProgressTracker (진행 상황 추적)
│   ├── rate_limiter.py           # AdaptiveRateLimiter (적응형 Rate Limiting)
│   ├── crawlers/                 # 크롤러 모듈
│   │   ├── __init__.py
│   │   ├── base.py              # BaseCrawler (추상 베이스 클래스)
│   │   ├── static.py            # StaticCrawler (requests 기반)
│   │   ├── dynamic.py           # DynamicCrawler (Playwright 기반)
│   │   ├── api.py               # APICrawler (API 기반)
│   │   └── hogangnono.py        # HogangnonoCrawler (호갱노노 부동산 크롤러)
│   ├── parsers/                  # HTML 파싱 유틸
│   │   └── __init__.py
│   ├── utils/                    # 유틸리티 모듈
│   │   ├── __init__.py
│   │   ├── browser_manager.py   # BrowserManager (브라우저 자원 관리)
│   │   ├── checkpoint.py        # CheckpointManager (체크포인트 관리)
│   │   ├── retry.py             # 재시도 로직
│   │   └── statistics.py        # 통계 정보 수집
│   └── writers/                  # 데이터 출력
│       ├── __init__.py
│       ├── csv_writer.py        # CSVWriter (기본)
│       ├── complexes_csv_writer.py  # ComplexesCSVWriter (단지 정보)
│       └── transaction_csv_writer.py # TransactionCSVWriter (거래내역)
├── tests/                        # 테스트 코드
│   ├── conftest.py              # pytest 공통 설정
│   ├── helpers/                 # 테스트 헬퍼
│   │   ├── __init__.py
│   │   └── error_injection.py   # 오류 주입 유틸
│   ├── unit/                    # 단위 테스트
│   │   ├── test_*.py
│   └── integration/             # 통합 테스트
│       └── test_*.py
├── scripts/                      # 실행 스크립트
│   ├── main.py                  # 메인 엔트리포인트
│   ├── calculate_total_stats.py # 통계 계산
│   ├── collect_dongs_step4.py   # 동 데이터 수집 (스텝 4)
│   ├── collect_dongs_step5.py   # 동 데이터 수집 (스텝 5)
│   ├── collect_seoul_data.py    # 서울 데이터 수집
│   └── integrate_seoul_data.py  # 서울 데이터 통합
├── docs/                         # 문서
│   ├── guides/                  # 사용 가이드
│   │   └── naver-real-estate-api-guide.md
│   └── plans/                   # 설계 및 구현 계획
└── output/                       # CSV 출력 디렉토리 (gitignored)
    ├── complexes.csv            # 단지 정보
    ├── transactions.csv         # 거래내역
    └── checkpoint.json          # 체크포인트 파일
```

## 개발 환경 설정

```bash
# 의존성 설치
uv sync

# Playwright 브라우저 설치
uv run playwright install chromium

# pre-commit 훅 설치
uv run pre-commit install

# 환경 변수 설정
cp .env.example .env
```

## 실행 방법

### 기본 실행
```bash
# 전체 서울시 크롤링 (output 디렉토리에 저장)
python scripts/main.py

# 출력 파일 지정
python scripts/main.py --output results/my_data.csv

# 특정 구만 크롤링
python scripts/main.py --district 강남구
python scripts/main.py --district "강남구,서초구,송파구"

# 중단된 지점부터 재개
python scripts/main.py --resume
```

### 기타 스크립트
```bash
# 통계 계산
python scripts/calculate_total_stats.py

# 동 데이터 수집
python scripts/collect_dongs_step4.py
python scripts/collect_dongs_step5.py

# 서울 데이터 수집 및 통합
python scripts/collect_seoul_data.py
python scripts/integrate_seoul_data.py
```

## 테스트

### 전체 테스트 실행
```bash
# 전체 테스트 실행
uv run pytest -v

# 커버리지 포함
uv run pytest --cov=src --cov-report=html

# 특정 마커 테스트만 실행
uv run pytest -m "integration" -v
uv run pytest -m "not integration" -v  # 단위 테스트만
```

### 특정 테스트 실행
```bash
# 단위 테스트만 실행
uv run pytest tests/unit/ -v

# 통합 테스트만 실행
uv run pytest tests/integration/ -v

# 특정 테스트 파일 실행
uv run pytest tests/unit/test_hogangnono_crawler.py -v

# 특정 테스트 함수 실행
uv run pytest tests/unit/test_hogangnono_crawler.py::test_fetch_complexes -v
```

### 디버깅 테스트
```bash
# 테스트 실패 시 디버거 실행
uv run pytest -pdb

# 테스트 출력 상세 보기
uv run pytest -v -s
```

## 코드 품질 검사

### Ruff (Linting & Formatting)
```bash
# Ruff 린팅
uv run ruff check .

# Ruff 자동 수정
uv run ruff check . --fix

# Ruff 포맷팅
uv run ruff format .

# Ruff 포맷 체크 (CI용)
uv run ruff format --check .

# 특정 파일만 검사
uv run ruff check src/crawler/hogangnono.py
uv run ruff format src/crawler/hogangnono.py
```

### MyPy (Type Checking)
```bash
# MyPy 타입 체크 (strict mode)
uv run mypy src/

# 특정 모듈만 체크
uv run mypy src/crawler/hogangnono.py

# 상세한 오류 정보 표시
uv run mypy src/ --show-error-codes
```

### Pre-commit 훅
```bash
# 전체 파일에 대해 실행
uv run pre-commit run --all-files

# Staged 파일만 실행
uv run pre-commit run
```

## 아키텍처

### 핵심 패턴

1. **Abstract Base Class 패턴**: `BaseCrawler`가 템플릿 메서드 패턴 구현
   - `crawl()` 메서드가 `get_url() → fetch() → parse()` 흐름 정의
   - 새 크롤러는 3개 추상 메서드만 구현

2. **Strategy 패턴**: 정적/동적 크롤링을 별도 클래스로 분리
   - StaticCrawler: requests 사용
   - DynamicCrawler: Playwright 사용

3. **Coordinator 패턴**: `CrawlCoordinator`가 전체 크롤링 프로세스 조정
   - 동 단위 점진적 저장
   - 체크포인트 관리를 통한 재시작 지원
   - 진행 상황 추적

4. **Adaptive Rate Limiting**: `AdaptiveRateLimiter`가 동적으로 요청 간격 조정
   - 성공 시: 10회 연속 성공 후 지연 시간 감소
   - 429 에러 시: 즉시 지연 시간 2배 증가
   - 기본 간격: 5초 (최소 1.5초, 최대 10초)

5. **Checkpoint System**: `CheckpointManager`가 중단 지점 저장/복원
   - `output/checkpoint.json`에 상태 저장
   - `--resume` 옵션으로 중단된 지점부터 재개

### BaseCrawler 구조

```python
class BaseCrawler(ABC):
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.logger = structlog.get_logger()

    @abstractmethod
    def get_url(self) -> str:
        """크롤링할 URL 반환"""
        pass

    @abstractmethod
    def fetch(self, url: str) -> str:
        """HTML 가져오기"""
        pass

    @abstractmethod
    def parse(self, html: str) -> list[dict[str, Any]]:
        """HTML 파싱하여 데이터 추출"""
        pass

    def crawl(self) -> list[dict[str, Any]]:
        """fetch + parse 실행"""
        url = self.get_url()
        html = self.fetch(url)
        return self.parse(html)
```

## 호갱노노 부동산 크롤러 상세

### 주요 기능

1. **지역별 단지 목록 조회**
   - `fetch_complexes(district)`
   - 지역(구) 기반 단지 목록 조회

2. **매물 목록 조회**
   - `fetch_listings(district, property_type, page)`
   - 페이지네이션 지원
   - 다양한 필터링 옵션 (매물 유형, 가격대 등)

3. **점진적 크롤링**
   - 각 동 완료 시마다 CSV 저장
   - 중단 시 재시작 지원
   - 실패한 동 기록 및 후속 재시도

### API 엔드포인트

- **기본 URL**: `https://hogangnono.com`

### 데이터 저장

- **거래내역**: `output/transactions.csv`
  - 단지ID, 건물명, 전용면적, 층, 거래가, 계약일, 등
- **단지 정보**: `output/complexes.csv`
  - 단지ID, 단지명, 주소, 건축년도, 세대수, 동 수, 등
- **체크포인트**: `output/checkpoint.json`
  - 진행 상황, 실패 목록, 재시도 횟수 등

## 새 크롤러 추가 방법

1. `src/crawler/crawlers/` 아래에 파일 생성 (예: `samsung.py`)
2. `BaseCrawler` 또는 `StaticCrawler`/`DynamicCrawler` 상속
3. 필수 메서드 구현:
   - `get_url()`: 크롤링할 URL 반환
   - `parse(html)`: HTML/JSON 파싱 로직
   - (선택) `fetch(url)`: 특수한 fetch 로직이 필요한 경우만
4. TDD: 테스트 먼저 작성 후 구현

## 테스트 규칙

- **모든 새 크롤러**에 대해 단위 테스트 작성
- `unittest.mock`을 사용하여 HTTP 요청 및 브라우저 동작 Mock
- 실제 HTML/JSON 응답 샘플을 테스트 데이터로 사용
- `parse()` 메서드는 실제 HTML로 테스트 (Mock 불필요)
- pytest fixtures로 공통 설정 관리 (`tests/conftest.py`)

### 테스트 작성 예시

```python
# tests/unit/test_my_crawler.py
import pytest
from unittest.mock import Mock, patch
from crawler.crawlers.my_crawler import MyCrawler
from crawler.config import CrawlerConfig

@pytest.fixture
def config():
    return CrawlerConfig.from_env()

@pytest.fixture
def crawler(config):
    return MyCrawler(config)

def test_parse_html(crawler):
    # 실제 HTML 샘플로 테스트
    html = "<html>...</html>"
    result = crawler.parse(html)
    assert len(result) > 0
    assert "title" in result[0]

@patch('requests.get')
def test_fetch_data(mock_get, crawler):
    # Mock으로 HTTP 응답 테스트
    mock_response = Mock()
    mock_response.text = '{"data": "test"}'
    mock_get.return_value = mock_response

    result = crawler.fetch("http://example.com")
    assert result == '{"data": "test"}'
```

## 에러 처리 및 모범 사례

### 1. Rate Limiting
- **기본 간격**: 5초 (AdaptiveRateLimiter 기본값)
- **최소 간격**: 1.5초
- **최대 간격**: 10초
- **429 에러**: 자동으로 지연 시간 2배 증가

### 2. 재시도 로직
- `utils/retry.py`에 제공된 `@retry_with_backoff` 데코레이터 사용
- 최대 3회 재시도 (기본값)
- 지수 백오프 적용

### 3. 로깅
- structlog 사용: `logger.info("action", key=value)`
- 로그 레벨: DEBUG, INFO, WARNING, ERROR
- 구조화된 로그로 디버깅 용이

### 4. 리소스 관리
- BrowserManager를 통한 브라우저 자원 관리
- Context Manager 사용 (`with` 구문)
- 반드시 `page.close()`와 `browser.close()` 호출

### 5. 체크포인트 활용
- 긴 작업 시 반드시 체크포인트 사용
- 각 동 완료 시마다 상태 저장
- 실패한 항목 별도 관리

## 성능 최적화

### 1. 동시성
- 현재는 순차 처리 (안정성 우선)
- 필요시 비동기 처리 고려 (단, Playwright 주의)

### 2. 메모리 관리
- 대용량 데이터는 스트리밍 처리
- 페이지 처리 후 즉시 메모리 해제

### 3. 캐싱
- 반복 조회되는 데이터는 캐싱 고려
- 단지 기본 정보 등 정적 데이터

## 디버깅 가이드

### 1. 로깅 레벨 조정
```python
import logging
logging.getLogger("crawler").setLevel(logging.DEBUG)
```

### 2. Playwright 디버깅
```python
# headless 모드 비활성화
browser = playwright.chromium.launch(headless=False)

# 스텝 모드 (실행 시마다 중지)
browser = playwright.chromium.launch(slow_mo=1000)
```

### 3. 네트워크 요청 모니터링
```python
# 페이지 로드 시 모든 요청 로깅
page.on("request", lambda request: print(f"Request: {request.url}"))
page.on("response", lambda response: print(f"Response: {response.url}"))
```

## 프로덕션 배포 시 고려사항

### 1. 모니터링
- 진행 상황 실시간 모니터링 (ProgressTracker)
- 에러률 추적 및 알림
- 처리량 모니터링

### 2. 안정성
- Circuit Breaker 패턴 구현
- 장애 복구 전략
- 데이터 백업 및 복원

### 3. 확장성
- 분산 처리 아키텍처 고려
- 스케줄링 시스템 연동
- 데이터 파이프라인 구축

## 커밋 컨벤션

Conventional Commits 규칙 준수:
- `feat: 네이버 부동산 크롤러 구현`
- `fix: RateLimiter 타입 힌트 수정`
- `test: CSV writer 테스트 추가`
- `docs: README 업데이트`
- `refactor: 코드 중복 제거`
- `perf: 성능 최적화`
- `chore: 의존성 업데이트`

## 문서

- **API 가이드**: `docs/guides/naver-real-estate-api-guide.md`
- **설계 문서**: `docs/plans/`
- **README**: `README.md`

## 문제 해결

### 자주 발생하는 문제

1. **Playwright 브라우저 설치 오류**
   ```bash
   uv run playwright install chromium
   ```

2. **권한 오류**
   - `.env` 파일 확인
   - 출력 디렉토리 권한 확인

3. **메모리 부족**
   - `--max-workers=1` 옵션 사용
   - 페이지 처리 후 즉시 해제

4. **네트워크 타임아웃**
   - `TIMEOUT` 환경변수 증가
   - 재시도 로직 확인

## 설계 원칙

- **YAGNI**: 최소한의 기능으로 시작, 필요 시 확장
- **Single Responsibility**: 각 컴포넌트는 하나의 책임만
- **Fail Fast**: 에러는 즉시 발생시키고 명확한 메시지 제공
- **Defensive Programming**: 입력값 검증, 에러 처리 강화
- **동기 방식**: 간단하고 명확한 구조 (비동기는 필요 시 추가)

## 추가 리소스

- [Playwright 문서](https://playwright.dev/python/)
- [structlog 가이드](https://www.structlog.org/en/stable/)
- [pytest 문서](https://docs.pytest.org/)
