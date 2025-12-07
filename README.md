# HomeSweetHome Crawler Boilerplate

Python 웹 크롤링 + CSV 저장 보일러플레이트

## 현재 상태 (2025-12-07)

✅ **호갱노노 부동산 크롤링 작동 중**
- 호갱노노 API 기반으로 안정적인 데이터 수집
- Rate Limiting: 5초 간격으로 429 에러 방지
- 단지 목록, 매물 목록 수집 가능
- 다양한 필터링 옵션 제공 (지역, 매물 유형 등)

## 현재 목표

호갱노노 부동산 매물 데이터 크롤링 구현 완료 ✅

## 설치

```bash
# 의존성 설치
uv sync

# Playwright 브라우저 설치
uv run playwright install chromium

# pre-commit 설치
uv run pre-commit install
```

## 사용

### 기본 사용

```bash
# 기본 사용 (전체 크롤링)
uv run python scripts/main.py

# 출력 파일 지정
uv run python scripts/main.py --output results/data.csv
```

### 호갱노노 부동산 크롤링

```python
from crawler.crawlers.hogangnono import HogangnonoCrawler
from crawler.config import CrawlerConfig

# 환경 변수에서 설정 로드 (기본: 호갱노노)
config = CrawlerConfig.from_env()
crawler = HogangnonoCrawler(config)

# 단지 목록 크롤링
complexes = crawler.fetch_complexes()

# 매물 목록 조회
listings = crawler.fetch_listings("강남구", property_type="apartment")
```

### 실행 방법

```bash
# 1. 전체 서울시 크롤링 (체크포인트 지원)
uv run python scripts/main.py

# 2. 특정 구만 크롤링
uv run python scripts/main.py --district 강남구,서초구,송파구

# 3. 이어서 크롤링 (중단된 경우)
uv run python scripts/main.py --resume

# 4. 출력 파일 지정
uv run python scripts/main.py --output results/hogangnono_data_20251207.csv
```

### 출력 데이터

크롤링 결과는 CSV 파일로 저장되며 다음 필드를 포함합니다:
- **거래내역**: `output/transactions.csv`
  - 단지ID, 건물명, 전용면적, 층, 거래가, 계약일 등
- **단지 정보**: `output/complexes.csv`
  - 단지ID, 단지명, 주소, 건축년도, 세대수, 동 수 등

### 주의사항
- API 호출 간 5초 간격으로 Rate Limiting 준수
-长时间 크롤링 시 체크포인트 기능으로 안정성 확보
- 출력 디렉토리: `output/` (gitignored)

## 새 크롤러 추가

1. `src/crawler/crawlers/` 아래에 파일 생성
2. `BaseCrawler` 상속
3. `get_url()`, `parse()` 메서드 구현

## 개발

### 테스트 실행

```bash
# 전체 테스트
uv run pytest -v

# 단위 테스트만
uv run pytest tests/unit/ -v

# 통합 테스트만
uv run pytest tests/integration/ -v
```

### 코드 품질 검사

```bash
# Linting
uv run ruff check .

# Formatting
uv run ruff format .

# Type checking
uv run mypy src/
```

### 새 크롤러 추가 예시

```python
# src/crawler/crawlers/my_site.py
from crawler.crawlers.base import BaseCrawler
from bs4 import BeautifulSoup
import requests

class MySiteCrawler(BaseCrawler):
    def get_url(self) -> str:
        return "https://mysite.com"

    def fetch(self, url: str) -> str:
        response = requests.get(url, timeout=self.config.timeout)
        response.raise_for_status()
        return response.text

    def parse(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        # 파싱 로직 구현
        return []
```
