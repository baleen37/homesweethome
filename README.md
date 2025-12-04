# HomeSweetHome Crawler Boilerplate

Python 크롤링 + CSV 저장 보일러플레이트

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

```bash
# 기본 사용
python scripts/main.py

# 출력 파일 지정
python scripts/main.py --output results/data.csv
```

## 새 크롤러 추가

1. `src/crawler/crawlers/` 아래에 파일 생성
2. `BaseCrawler` 상속
3. `get_url()`, `parse()` 메서드 구현
