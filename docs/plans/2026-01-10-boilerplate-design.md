# 보일러플레이트 기본 구조 설계

**날짜**: 2026-01-10
**목적**: TDD 기반 웹 크롤링 보일러플레이트 최소 구조 구축

## 개요

서울시 아파트 데이터 수집을 위한 크롤러 보일러플레이트를 TDD로 처음부터 작성한다.

## 디렉토리 구조

```
homesweethome/
├── src/
│   └── crawler/
│       ├── __init__.py
│       └── base.py             # BaseCrawler (추상 베이스)
├── tests/
│   ├── conftest.py             # pytest 공통 설정
│   ├── unit/                   # 단위 테스트
│   │   ├── __init__.py
│   │   └── test_base_crawler.py
│   ├── integration/            # 통합 테스트
│   │   ├── __init__.py
│   │   └── test_crawler_integration.py
│   └── e2e/                    # E2E 테스트
│       ├── __init__.py
│       └── test_crawler_e2e.py
├── scripts/
│   └── main.py                 # 예시 실행
├── output/                     # CSV 출력 (gitignored)
├── pyproject.toml
└── .gitignore
```

## 핵심 구성 요소

### BaseCrawler

```python
from abc import ABC, abstractmethod
from typing import Any

class BaseCrawler(ABC):
    @abstractmethod
    def get_url(self) -> str:
        """크롤링할 URL 반환"""
        pass

    @abstractmethod
    def fetch(self, url: str) -> str:
        """HTML/JSON 가져오기"""
        pass

    @abstractmethod
    def parse(self, content: str) -> list[dict[str, Any]]:
        """컨텐츠 파싱하여 데이터 추출"""
        pass

    def crawl(self) -> list[dict[str, Any]]:
        """템플릿 메서드: fetch + parse 실행"""
        url = self.get_url()
        content = self.fetch(url)
        return self.parse(content)
```

### 테스트 구조

1. **Unit Test**: Mock 사용, 인터페이스 검증
2. **Integration Test**: 여러 컴포넌트 연결, Playwright 사용
3. **E2E Test**: 실제 사이트 대상, `--e2e` 플래그 필요

### 프로젝트 설정

- **Python**: 3.11+
- **의존성**: playwright (최소)
- **Dev**: pytest, pytest-cov
- **패키지 매니저**: uv
- **빌드 백엔드**: hatchling

## 실행 방법

```bash
# 설치
uv sync
uv run playwright install chromium

# 테스트
uv run pytest -v              # 단위 + 통합
uv run pytest -v -m e2e      # E2E 포함

# 실행
uv run python scripts/main.py
```

## 다음 단계

1. 보일러플레이트 구현
2. 호갱노노 크롤러 TDD로 작성 (기본 정보)
3. 점진적으로 매물 정보, 상세 정보 필드 추가
