# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

HomeSweetHome Crawler Boilerplate는 Python 기반 웹 크롤링 보일러플레이트입니다. 정적/동적 사이트 크롤링을 지원하며, 크롤링한 데이터를 CSV 파일로 저장합니다.

**현재 목표**: 네이버 부동산 매물 데이터 크롤링

**중요**: 이 프로젝트는 **네이버 부동산 크롤링만** 수행합니다. 국토교통부 공공데이터 API는 사용하지 않습니다.

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
│   ├── config.py                 # CrawlerConfig (dataclass 기반)
│   ├── crawlers/                 # 크롤러 모듈
│   │   ├── base.py              # BaseCrawler (추상 베이스 클래스)
│   │   ├── static.py            # StaticCrawler (requests 기반)
│   │   └── dynamic.py           # DynamicCrawler (Playwright 기반)
│   ├── parsers/                  # HTML 파싱 유틸
│   └── writers/                  # 데이터 출력
│       └── csv_writer.py        # CSVWriter
├── tests/                        # 테스트 코드
│   ├── unit/                    # 단위 테스트
│   └── integration/             # 통합 테스트
├── scripts/                      # 실행 스크립트
│   └── main.py                  # 메인 엔트리포인트
├── docs/                         # 문서
│   ├── plans/                   # 설계 및 구현 계획
│   └── analysis/                # 분석 문서 (네이버 부동산 분석 포함)
└── output/                       # CSV 출력 디렉토리 (gitignored)
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

## 명령어

### 실행
```bash
# 기본 실행 (output/data.csv에 저장)
python scripts/main.py

# 출력 파일 지정
python scripts/main.py --output results/my_data.csv
```

### 테스트
```bash
# 전체 테스트 실행
uv run pytest -v

# 특정 테스트 파일 실행
uv run pytest tests/unit/test_config.py -v

# 단위 테스트만 실행
uv run pytest tests/unit/ -v

# 통합 테스트만 실행
uv run pytest tests/integration/ -v
```

### 코드 품질 검사
```bash
# Ruff 린팅
uv run ruff check .

# Ruff 자동 수정
uv run ruff check . --fix

# Ruff 포맷팅
uv run ruff format .

# Ruff 포맷 체크 (CI용)
uv run ruff format --check .

# MyPy 타입 체크 (strict mode)
uv run mypy src/

# Pre-commit 훅 전체 실행
uv run pre-commit run --all-files
```

## 아키텍처

### 핵심 패턴

1. **Abstract Base Class 패턴**: `BaseCrawler`가 템플릿 메서드 패턴 구현
   - `crawl()` 메서드가 `get_url() → fetch() → parse()` 흐름 정의
   - 새 크롤러는 3개 추상 메서드만 구현

2. **Strategy 패턴**: 정적/동적 크롤링을 별도 클래스로 분리
   - StaticCrawler: requests 사용
   - DynamicCrawler: Playwright 사용

3. **의존성 주입**: `CrawlerConfig`를 생성자에서 주입

4. **타입 안정성**
   - 모든 함수에 타입 힌트 적용
   - `mypy --strict` 통과
   - Python 3.11+ 문법 사용 (예: `list[dict[str, Any]]`)

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

## 새 크롤러 추가 방법

1. `src/crawler/crawlers/` 아래에 파일 생성 (예: `naver.py`)
2. `BaseCrawler` 또는 `StaticCrawler`/`DynamicCrawler` 상속
3. 필수 메서드 구현:
   - `get_url()`: 크롤링할 URL 반환
   - `parse(html)`: HTML/JSON 파싱 로직
   - (선택) `fetch(url)`: 특수한 fetch 로직이 필요한 경우만
4. TDD: 테스트 먼저 작성 후 구현

## 테스트 규칙

- YOU MUST 모든 새 크롤러에 대해 단위 테스트 작성
- `unittest.mock`을 사용하여 HTTP 요청 및 브라우저 동작 Mock
- 실제 HTML/JSON 응답 샘플을 테스트 데이터로 사용
- `parse()` 메서드는 실제 HTML로 테스트 (Mock 불필요)
- pytest fixtures로 공통 설정 관리 (`tests/conftest.py`)

## 네이버 부동산 크롤링 특이사항

네이버 부동산 매물 크롤링 시 다음 사항을 참고하세요:

- **권장 방법**: Playwright MCP의 `browser_evaluate` + `fetch()` 조합
- 직접 API 호출이 차단되어 있으므로 브라우저 컨텍스트 내에서만 API 접근 가능
- 상세 분석 문서: `docs/analysis/naver-real-estate-final-approach.md`
- API 엔드포인트 및 DOM 구조: `naver-real-estate-crawling.md`

### 점진적 크롤링 기능

- **fetch_complex_detail(complex_id)**: 단지 상세 정보 조회 (평형, 보유세, 공시가격, 시세)
- **fetch_complex_listings(complex_id, trade_type)**: 단지별 매물 목록 조회 (페이지네이션 지원)
- **체크포인트 시스템**: 중단된 크롤링을 이어서 진행할 수 있음 (`output/checkpoint.json`)
- **CSV 확장 필드**: 단지 상세 정보와 매물 정보가 기본 CSV에 추가됨

## 크롤링 주의사항

- **Rate limiting**: 요청 간 2~4초 대기 필수 (네이버 429 에러 방지)
- **User-Agent**: 필요 시 설정 (네이버 부동산의 경우)
- **에러 처리**: 재시도 로직 구현 권장
- **세션 관리**: 네이버 부동산 API는 브라우저 세션 내에서만 동작 (쿠키 필요)
- **HTTP 429**: 네이버 서버의 Rate Limiting이 매우 엄격하여 API 호출이 제한될 수 있음

## 코드 스타일

- **Line length**: 100자
- **Target**: Python 3.11+
- **MyPy**: strict 모드 활성화
- **Ruff**: 빠른 린팅 및 포맷팅
- **structlog**: 키-값 쌍으로 로그 기록 (예: `logger.info("fetching_url", url=url)`)
- **src layout**: `src/crawler/` 구조로 패키지 네임스페이스 명확화

## 커밋 컨벤션

Conventional Commits 규칙 준수:
- `feat: 네이버 부동산 크롤러 구현`
- `fix: StaticCrawler 타입 힌트 수정`
- `test: CSV writer 테스트 추가`
- `docs: README 업데이트`

## 설계 원칙

- **YAGNI**: 최소한의 기능으로 시작, 필요 시 확장
- **Single Responsibility**: 각 컴포넌트는 하나의 책임만
- **동기 방식**: 간단하고 명확한 구조 (비동기는 필요 시 추가)
