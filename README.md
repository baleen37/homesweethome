# HomeSweetHome Crawler Boilerplate

Python 웹 크롤링 + CSV 저장 보일러플레이트

## 현재 상태 (2025-12-07)

✅ **네이버 부동산 크롤링 작동 중**
- 모바일 API(m.land.naver.com) 기반으로 안정적인 데이터 수집
- Rate Limiting: 5초 간격으로 429 에러 방지
- 단지 목록, 상세 정보, 매물 목록, 거래내역 수집 가능
- ⚠️ 알려진 이슈: 일부 "Event loop is closed" 경고 발생 (크롤링은 정상 동작)

## 현재 목표

네이버 부동산 매물 데이터 점진적 크롤링 구현 완료 ✅

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

### 네이버 부동산 크롤링

```python
from crawler.crawlers.naver import NaverRealEstateCrawler
from crawler.config import CrawlerConfig

# 크롤러 초기화
config = CrawlerConfig(timeout=30, headless=True)
crawler = NaverRealEstateCrawler(config)

# 기본 단지 목록 크롤링
complexes = crawler.crawl()

# 단지 상세 정보 조회
detail = crawler.fetch_complex_detail("138225")

# 단지 매물 목록 조회
listings = crawler.fetch_complex_listings("138225", "매매")
```

### 실행 방법

```bash
# 1. 전체 서울시 크롤링 (체크포인트 지원)
uv run python scripts/main.py

# 2. 특정 구만 크롤링
uv run python scripts/main.py --districts 강남구 서초구 송파구

# 3. 특정 구의 법정동만 크롤링
uv run python scripts/main.py --districts 강남구 --dongs 청담동 삼성동

# 4. 출력 파일 지정
uv run python scripts/main.py --output results/naver_data_20251207.csv

# 5. 상세 모드 (단지 상세 정보, 매물 정보 포함)
uv run python scripts/main.py --detail

# 6. 이어서 크롤링 (중단된 경우)
uv run python scripts/main.py --resume
```

### 출력 데이터

크롤링 결과는 CSV 파일로 저장되며 다음 필드를 포함합니다:
- **기본 정보**: 단지명, 주소, 건축일, 세대수, 면적
- **가격 정보**: 매매/전세/월세 가격대
- **상세 정보**: 평형별 정보, 보유세, 공시가격 (상세 모드)
- **매물 정보**: 실제 매물 데이터 (매물 수 제한)

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

# 네이버 통합 테스트
uv run pytest tests/integration/test_naver_integration.py -v -s
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
