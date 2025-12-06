# 네이버 부동산 서울시 구별 크롤링 기능 설계

**작성일**: 2025-12-06

## 개요

네이버 부동산 크롤러에 구(district) 단위 필터링 기능을 추가하여, 사용자가 원하는 특정 구만 선택적으로 크롤링할 수 있도록 개선합니다.

## 요구사항

1. **구 선택 크롤링**: 명령줄 인자로 특정 구를 지정하여 크롤링 (`--district 강남구`)
2. **데이터 저장**: 현재 구조 유지 (`complexes.csv` + `transactions.csv`)
3. **Integration test**: 실제 네이버 API 호출 테스트 (1개 동만)
4. **기존 기능 유지**: 체크포인트, resume, rate limiting 모두 정상 동작

## 아키텍처

### 1. CLI 인터페이스 (`scripts/main.py`)

#### 새로운 명령줄 옵션

```bash
# 서울시 전체 크롤링 (기본)
python scripts/main.py

# 특정 구만 크롤링
python scripts/main.py --district 강남구

# 여러 구 크롤링 (선택적 기능)
python scripts/main.py --district 강남구,서초구

# 체크포인트에서 재개
python scripts/main.py --district 강남구 --resume
```

#### 옵션 추가

```python
parser.add_argument(
    "--district",
    type=str,
    default=None,
    help="크롤링할 구 이름 (예: 강남구). 쉼표로 구분하여 여러 구 지정 가능",
)
```

### 2. 크롤러 수정 (`src/crawler/crawlers/naver.py`)

#### A. 구 필터링 메서드 추가

```python
def filter_districts(self, district_names: list[str] | None) -> list[dict[str, Any]]:
    """지정된 구만 필터링하여 반환

    Args:
        district_names: 구 이름 리스트 (None이면 전체)

    Returns:
        필터링된 구 리스트

    Raises:
        ValueError: 유효하지 않은 구 이름이 있을 경우
    """
    if district_names is None:
        return self.districts_data["districts"]

    # 유효성 검사
    all_districts = {d["district_name"] for d in self.districts_data["districts"]}
    invalid = [name for name in district_names if name not in all_districts]

    if invalid:
        raise ValueError(
            f"유효하지 않은 구 이름: {', '.join(invalid)}\n"
            f"사용 가능한 구: {', '.join(sorted(all_districts))}"
        )

    # 필터링
    return [d for d in self.districts_data["districts"]
            if d["district_name"] in district_names]
```

#### B. `crawl()` 메서드 시그니처 변경

```python
def crawl(self, district_filter: list[str] | None = None) -> dict[str, Any]:
    """서울시 구/동을 순회하며 크롤링 (거래내역 포함)

    Args:
        district_filter: 크롤링할 구 이름 리스트 (None이면 전체)

    Returns:
        크롤링 결과 통계
    """
    self.logger.info("crawling_start_with_transactions", districts=district_filter)

    # 구 필터링
    districts = self.filter_districts(district_filter)

    # CrawlCoordinator 초기화
    # ... (기존 코드)

    # 필터링된 구의 동들만 수집
    for district in districts:
        self.logger.info("processing_district", district_name=district["district_name"])
        for dong in district["dongs"]:
            # 기존 로직 유지
```

### 3. 체크포인트 호환성

#### 체크포인트 포맷 확장

```json
{
  "last_dong": "1168010300",
  "district_filter": ["강남구"],
  "timestamp": "2025-12-06T12:00:00",
  "rate_limiter_state": { ... }
}
```

#### Resume 시 검증

```python
def validate_resume(self, current_filter: list[str] | None) -> bool:
    """체크포인트의 district_filter와 현재 필터가 일치하는지 확인"""
    checkpoint = self.checkpoint_manager.checkpoint
    saved_filter = checkpoint.get("district_filter")

    if saved_filter != current_filter:
        self.logger.warning(
            "district_filter_mismatch",
            saved=saved_filter,
            current=current_filter
        )
        # 사용자에게 확인 요청 또는 새로 시작
        return False

    return True
```

### 4. Integration Test

#### 실제 API 호출 테스트

```python
# tests/integration/test_district_crawling.py

import pytest
from pathlib import Path
from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler


@pytest.mark.slow
def test_crawl_single_district_real_api():
    """실제 네이버 API로 강남구의 1개 동만 크롤링 테스트"""

    config = CrawlerConfig(
        headless=True,
        timeout=30,
        output_dir="output/test_integration"
    )

    crawler = NaverRealEstateCrawler(config)

    # 강남구만 크롤링 (1개 동만 테스트)
    results = crawler.crawl(district_filter=["강남구"])

    # 검증: 최소 1개 동 처리
    assert results["dongs_processed"] >= 1
    assert results["total_complexes_processed"] > 0

    # CSV 파일 생성 확인
    assert Path("output/test_integration/complexes.csv").exists()
    assert Path("output/test_integration/transactions.csv").exists()

    # CSV 내용 검증
    with open("output/test_integration/complexes.csv") as f:
        lines = f.readlines()
        assert len(lines) > 1  # 헤더 + 최소 1개 데이터
        assert "complex_id" in lines[0]  # 헤더 확인
```

#### 테스트 전략

1. **@pytest.mark.slow**: CI에서 선택적으로 실행
2. **1개 동만 테스트**: 시간 절약 (전체 크롤링은 수 시간 소요)
3. **실제 데이터 검증**: 파일 생성 및 포맷 확인

### 5. 에러 처리 및 사용자 경험

#### A. 유효하지 않은 구 이름 처리

```bash
$ python scripts/main.py --district 강남

Error: 유효하지 않은 구 이름: 강남
사용 가능한 구: 강남구, 강동구, 강북구, ... (25개)
```

#### B. 진행 상황 출력

```
네이버 부동산 크롤링 시작...
대상 구: 강남구
대상 동: 22개

[강남구] 개포동 크롤링 중... (단지 15개)
[강남구] 논현동 크롤링 중... (단지 23개)
...

크롤링 완료!
- 처리한 동: 22개
- 수집한 단지: 450개
- 수집한 거래내역: 12,500건
```

## 구현 순서

1. ✅ 설계 문서 작성
2. `NaverRealEstateCrawler.filter_districts()` 메서드 추가
3. `NaverRealEstateCrawler.crawl()` 메서드 수정
4. `scripts/main.py`에 `--district` 옵션 추가
5. Integration test 작성
6. 기존 테스트 수정 (필요 시)
7. 수동 테스트 (강남구 1개 동)

## 고려사항

### A. 체크포인트 호환성
- 기존 체크포인트 파일과 호환성 유지
- `district_filter` 필드가 없으면 전체 크롤링으로 간주

### B. 성능
- 구 필터링은 메모리 내에서 처리 (빠름)
- 실제 API 호출은 변경 없음 (기존 rate limiting 유지)

### C. 테스트
- Integration test는 실제 API를 호출하므로:
  - 느림 (1개 동도 수 분 소요)
  - Rate limit 주의
  - CI에서는 기본적으로 스킵

## 기대 효과

1. **개발 효율성 향상**: 테스트 시 특정 구만 크롤링하여 시간 절약
2. **점진적 크롤링**: 구별로 나누어 실행 가능 (서버 부하 분산)
3. **디버깅 용이**: 특정 구에서 문제 발생 시 해당 구만 재실행
4. **유연성**: 전체 크롤링도 여전히 가능 (기본 동작)
