# Fixture 기반 테스트 설계

**작성일**: 2025-12-09
**목적**: 호갱노노 크롤러의 데이터 누락 문제를 integration test로 파악하고 개선

## 문제 정의

현재 `main.py` 실행 시 `hogangnono_complexes.csv`와 `hogangnono_transactions.csv`에 예상보다 훨씬 적은 데이터만 수집됨 (약 600개). 실제 호갱노노에는 더 많은 데이터가 있으나 크롤러가 일부만 수집하고 있으며, 어디서 데이터를 놓치는지 파악이 필요함.

## 해결 방안

두 가지 레벨의 테스트를 구현하여 문제를 단계적으로 파악:

1. **Fixture 기반 파싱 테스트**: 파싱 로직의 정확성 검증
2. **실제 API Integration 테스트**: 데이터 완성도 및 누락 지점 파악

---

## 1. Fixture 기반 파싱 테스트

### 목적
- 실제 API 응답을 JSON으로 저장하여 네트워크 호출 없이 빠르게 파싱 로직 검증
- 파싱 함수가 API 응답을 올바르게 처리하는지 확인

### Fixtures 구조

```
tests/fixtures/
├── hogangnono_complexes_sample.json      # 단지 목록 API 응답
├── hogangnono_listings_sample.json       # 매물 목록 API 응답 (page 1)
└── hogangnono_listings_page2_sample.json # 매물 목록 API 응답 (page 2)
```

간단하게 필요한 것만: API 원본 응답을 JSON으로 저장.

### 테스트 예시

```python
# tests/unit/test_hogangnono_parsing.py

def test_parse_complexes_from_fixture():
    """Fixture 데이터로 단지 목록 파싱 검증"""
    with open("tests/fixtures/hogangnono_complexes_sample.json") as f:
        response = json.load(f)

    crawler = HogangnonoCrawler(config)
    result = crawler.parse_complexes(response)

    assert len(result) > 0
    assert "complex_id" in result[0]
    assert "name" in result[0]
    assert "address" in result[0]

def test_parse_listings_from_fixture():
    """Fixture 데이터로 매물 목록 파싱 검증"""
    with open("tests/fixtures/hogangnono_listings_sample.json") as f:
        response = json.load(f)

    crawler = HogangnonoCrawler(config)
    result = crawler.parse_listings(response)

    assert len(result) > 0
    assert "listing_id" in result[0]
    assert "price" in result[0]
```

### 특징
- **빠름**: 네트워크 호출 없음, 몇 초 안에 완료
- **안정적**: 외부 API 상태와 무관
- **매번 실행**: pre-commit hook, CI에서 항상 실행

---

## 2. Fixture Recorder

### 목적
실제 API를 호출하여 응답을 JSON 파일로 저장하는 간단한 스크립트.

### 구현

```python
# tests/helpers/record_fixtures.py

from pathlib import Path
import json
from crawler.config import CrawlerConfig
from crawler.crawlers.hogangnono import HogangnonoCrawler

def record_fixtures():
    """실제 API 호출해서 fixtures 저장"""
    config = CrawlerConfig.from_env()
    crawler = HogangnonoCrawler(config)

    fixtures_dir = Path("tests/fixtures")
    fixtures_dir.mkdir(exist_ok=True)

    # 1. 단지 목록 샘플
    print("단지 목록 수집 중...")
    complexes_response = crawler._fetch_raw_complexes("강남구")
    save_json(fixtures_dir / "hogangnono_complexes_sample.json", complexes_response)

    # 2. 매물 목록 샘플 (page 1)
    print("매물 목록 (page 1) 수집 중...")
    listings_response = crawler._fetch_raw_listings("강남구", page=1)
    save_json(fixtures_dir / "hogangnono_listings_sample.json", listings_response)

    # 3. 매물 목록 샘플 (page 2)
    print("매물 목록 (page 2) 수집 중...")
    listings_page2 = crawler._fetch_raw_listings("강남구", page=2)
    save_json(fixtures_dir / "hogangnono_listings_page2_sample.json", listings_page2)

    print("✓ Fixtures 저장 완료")

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    record_fixtures()
```

### 크롤러 수정 필요
`HogangnonoCrawler`에 원본 응답 반환 메서드 추가:
- `_fetch_raw_complexes(district)`: 파싱 전 원본 응답
- `_fetch_raw_listings(district, page)`: 파싱 전 원본 응답

### 실행 방법
```bash
python tests/helpers/record_fixtures.py
```

---

## 3. 실제 API Integration 테스트

### 목적
실제 호갱노노 API를 호출하여 데이터 누락 지점 파악.

### 테스트 케이스

```python
# tests/integration/test_hogangnono_data_completeness.py

def test_all_districts_have_data():
    """서울 25개 구 모두에서 데이터를 수집하는지 확인"""
    crawler = HogangnonoCrawler(config)

    expected_districts = ["강남구", "강동구", "강북구", ...]  # 서울 25개 구

    for district in expected_districts:
        complexes = crawler.fetch_complexes(district)
        assert len(complexes) > 0, f"{district}에서 단지를 찾지 못했습니다"

def test_pagination_works():
    """페이지네이션이 제대로 동작하는지 확인"""
    crawler = HogangnonoCrawler(config)

    page1 = crawler.fetch_listings(district="강남구", page=1)
    page2 = crawler.fetch_listings(district="강남구", page=2)

    # 페이지가 다르면 데이터도 달라야 함
    assert page1 != page2
    assert len(page1) > 0
    assert len(page2) > 0

def test_sample_complex_completeness():
    """특정 샘플 단지의 모든 매물을 수집하는지 확인"""
    crawler = HogangnonoCrawler(config)

    # 알려진 단지 ID (실제로 매물이 많은 단지)
    sample_complex_id = "12345"

    all_listings = crawler.fetch_all_listings_for_complex(sample_complex_id)

    # 최소 N개 이상의 매물이 있어야 함 (수동으로 확인한 기준값)
    assert len(all_listings) >= 10
```

### 특징
- **느림**: 실제 API 호출, 몇 분 소요
- **선택적 실행**: `pytest -m integration`
- **CI**: nightly 또는 수동 트리거

---

## 4. 테스트 실행 전략

### 빠른 테스트 (Fixture 기반)
```bash
pytest tests/unit/test_hogangnono_parsing.py
```
- 네트워크 호출 없음
- 매번 실행 (pre-commit, CI)
- 파싱 로직 검증

### 느린 테스트 (실제 API)
```bash
pytest tests/integration/test_hogangnono_data_completeness.py -m integration
```
- 실제 API 호출
- 선택적 실행
- 데이터 누락 지점 파악

---

## 5. 문제 발견 프로세스

### Fixture 테스트 실패
→ **파싱 로직 버그**
- 파싱 함수 수정
- 필드 매핑 확인

### Integration 테스트 실패
→ **데이터 누락 문제**
- 어느 구에서 실패? → 해당 구 API 호출 문제
- 페이지네이션 실패? → 페이지 처리 로직 버그
- 특정 단지 실패? → 단지별 예외 처리 필요

---

## 6. 기대 효과

1. **파싱 로직 정확성 보장**: Fixture 기반 테스트로 빠르게 검증
2. **데이터 누락 지점 파악**: Integration 테스트로 명확히 식별
3. **회귀 방지**: API 변경 감지
4. **디버깅 시간 단축**: 문제 지점이 명확해짐

---

## 7. 구현 순서

1. Fixture recorder 스크립트 작성
2. 크롤러에 `_fetch_raw_*` 메서드 추가
3. Fixture 수집 실행
4. Fixture 기반 파싱 테스트 작성
5. 실제 API integration 테스트 작성
6. 테스트 실행 후 데이터 누락 원인 분석
