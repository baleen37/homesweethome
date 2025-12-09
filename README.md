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

### Nix를 사용하는 경우 (권장)

```bash
# 1. Nix 설치 (https://nixos.org/download.html)
# 2. direnv 설치 및 설정
# macOS: brew install direnv
# Ubuntu: sudo apt install direnv

# 3. direnv 설정 (shell config에 추가)
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc
# 또는 zsh의 경우
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc

# 4. 프로젝트 진입 (자동으로 Nix 환경 활성화)
cd homesweethome
direnv allow  # 최초 1회만 실행

# 5. Playwright 브라우저 설치
uv run playwright install chromium
```

### 기존 방식 (uv 직접 사용)

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

## 계층적 크롤링

호갱노노는 구 → 동 → 단지 → 매물 순서의 계층적 구조를 가지고 있습니다. 계층적 크롤링은 이 구조를 따라 체계적으로 데이터를 수집합니다.

### 데이터 흐름

1. **구(District) 조회**: 서울시 25개 구 목록 조회
2. **동(Dong) 조회**: 각 구에 속한 동 목록 조회 (예: 강남구 → 개포동, 역삼동, etc.)
3. **단지(Complex) 조회**: 각 동에 속한 아파트 단지 목록 조회
4. **매물(Transaction) 조회**: 각 단지의 실거래 내역 조회

### 실행 예제

```bash
# 단일 구 계층적 크롤링 (예: 강남구)
uv run python scripts/main.py --district 강남구

# 여러 구 동시 크롤링
uv run python scripts/main.py --district 강남구,서초구,송파구

# 중단된 크롤링 재개 (체크포인트 활용)
uv run python scripts/main.py --resume
```

### 예상 소요 시간

- **단일 구**: 약 30분 ~ 1시간 (동 수에 따라 차이)
- **전체 서울시**: 약 8시간 ~ 12시간

*참고: API Rate Limiting (5초 간격)으로 인한 예상 시간입니다*

### 체크포인트 시스템

- 각 동 완료 시마다 진행 상황 저장 (`output/checkpoint.json`)
- 중단 시 `--resume` 옵션으로 마지막 완료 지점부터 재개
- 실패한 동은 별도로 기록하여 후속 재시도

### 출력 파일

계층적 크롤링 결과는 별도 CSV 파일에 저장됩니다:

- **`output/complexes.csv`**: 단지 정보
  - 단지ID, 단지명, 주소, 건축년도, 세대수 등
  - 통계 정보: 총 거래 수, 최신 거래가, 1년 평균 거래가 등

- **`output/transactions.csv`**: 거래내역
  - 단지ID, 거래일, 가격, 면적, 층, 거래 유형 등
  - 구/동 코드 포함 (지역별 분석 용이)

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
