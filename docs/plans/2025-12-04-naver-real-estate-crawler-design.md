# 네이버 부동산 크롤러 설계

## 실행 요약

서울시 전체의 아파트 매매 매물 정보를 크롤링하는 시스템을 설계합니다. Python Playwright를 사용하여 브라우저 컨텍스트를 유지하고, `page.evaluate()`로 네이버 부동산 API를 직접 호출하여 데이터를 수집합니다. 진행 상황을 저장하여 중단/재개가 가능하며, CSV 파일에 점진적으로 데이터를 저장합니다.

## 요구사항

- **크롤링 범위**: 서울시 전체 (25개 구, 약 400~500개 동)
- **매물 유형**: 아파트 매매만
- **필터링**: 없음 (모든 아파트 단지)
- **실행 방식**: 체크포인트 기반 중단/재개 가능
- **데이터 저장**: CSV 파일 누적 저장 + JSON 체크포인트

## 전체 아키텍처

### 핵심 구조

`NaverRealEstateCrawler` 클래스를 `DynamicCrawler`를 상속하여 구현합니다.

**주요 컴포넌트**:

1. **지역 데이터 파일** (`src/crawler/data/seoul_districts.json`): 서울시 25개 구와 각 구의 동 목록, 지역 코드(cortarNo), 좌표 범위를 사전 정의
2. **체크포인트 매니저** (`CheckpointManager`): 진행 상황을 `output/checkpoint.json`에 저장/로드하여 중단/재개 지원
3. **크롤러 본체** (`NaverRealEstateCrawler`): Playwright로 브라우저 세션 유지, `page.evaluate()`로 fetch API 호출
4. **CSV Writer**: 기존 `CSVWriter` 활용, append 모드로 점진적 저장

### 실행 흐름

```
1. 체크포인트 로드 (있으면 이어서, 없으면 처음부터)
   ↓
2. Playwright 브라우저 실행 → 네이버 부동산 페이지 접속 (세션/쿠키 획득)
   ↓
3. 서울시 구/동 목록 순회:
   - 각 동의 cortarNo, 좌표로 API URL 생성
   - page.evaluate()로 fetch 호출 → JSON 응답 획득
   - CSV 파일에 append
   - 체크포인트 업데이트
   ↓
4. 완료 또는 에러 시 브라우저 종료
```

## 데이터 구조

### 1. 서울시 지역 데이터 (`src/crawler/data/seoul_districts.json`)

```json
{
  "districts": [
    {
      "district_name": "강남구",
      "district_code": "1168000000",
      "dongs": [
        {
          "dong_name": "삼성동",
          "cortarNo": "1168010100",
          "bounds": {
            "leftLon": 127.05,
            "rightLon": 127.07,
            "topLat": 37.52,
            "bottomLat": 37.50
          }
        }
      ]
    }
  ]
}
```

각 동(dong)마다 API 호출에 필요한 `cortarNo`와 지도 경계 좌표를 포함합니다.

**데이터 획득 방법**: 네이버 부동산 사이트를 수동으로 탐색하거나, 브라우저 개발자 도구로 네트워크 요청을 분석하여 서울시 전체의 구/동 목록과 cortarNo를 수집합니다.

### 2. 체크포인트 파일 (`output/checkpoint.json`)

```json
{
  "last_completed": {
    "district": "강남구",
    "dong": "삼성동"
  },
  "completed_dongs": ["1168010100", "1168010200"],
  "failed_dongs": [
    {
      "cortarNo": "1168010300",
      "error": "API timeout",
      "timestamp": "2025-12-04T10:30:00"
    }
  ],
  "total_complexes_crawled": 1523,
  "last_updated": "2025-12-04T10:35:00"
}
```

중단된 위치와 실패한 지역을 추적하여 재시도 또는 건너뛰기 가능합니다.

## 크롤러 클래스 구조

### NaverRealEstateCrawler 클래스

`DynamicCrawler`를 상속하여 다음 메서드들을 구현합니다:

```python
class NaverRealEstateCrawler(DynamicCrawler):
    def __init__(self, config: CrawlerConfig):
        super().__init__(config)
        self.checkpoint_manager = CheckpointManager("output/checkpoint.json")
        self.districts_data = self._load_districts_data()

    def get_url(self) -> str:
        # 네이버 부동산 메인 페이지 (세션 획득용)
        return "https://new.land.naver.com/complexes"

    def crawl(self) -> list[dict[str, Any]]:
        # BaseCrawler의 crawl() 오버라이드
        # 1. 브라우저 시작 및 페이지 로드
        # 2. 체크포인트 로드
        # 3. 구/동 순회하며 크롤링
        # 4. 진행 상황 저장
        pass

    def _fetch_dong_data(self, dong: dict) -> list[dict[str, Any]]:
        # page.evaluate()로 fetch API 호출
        # cortarNo와 bounds로 API URL 생성
        # JSON 응답 파싱하여 단지 리스트 반환
        pass

    def _load_districts_data(self) -> dict:
        # seoul_districts.json 로드
        pass
```

### CheckpointManager 클래스

```python
class CheckpointManager:
    def __init__(self, filepath: str):
        self.filepath = filepath

    def load(self) -> dict | None:
        # checkpoint.json 로드
        pass

    def save(self, checkpoint: dict) -> None:
        # checkpoint.json 저장
        pass

    def should_skip_dong(self, cortarNo: str) -> bool:
        # 이미 완료되었거나 실패한 동인지 확인
        pass

    def add_failed_dong(self, dong: dict, error: str) -> None:
        # 실패한 동 기록
        pass
```

## API 호출 및 데이터 추출

### Playwright page.evaluate()를 통한 fetch 호출

```python
def _fetch_dong_data(self, dong: dict) -> list[dict[str, Any]]:
    cortarNo = dong["cortarNo"]
    bounds = dong["bounds"]

    api_url = (
        f"https://new.land.naver.com/api/complexes/single-markers/2.0?"
        f"cortarNo={cortarNo}&"
        f"zoom=17&"
        f"priceType=RETAIL&"
        f"realEstateType=APT&"
        f"tradeType=A1&"
        f"leftLon={bounds['leftLon']}&"
        f"rightLon={bounds['rightLon']}&"
        f"topLat={bounds['topLat']}&"
        f"bottomLat={bounds['bottomLat']}"
    )

    # 브라우저 컨텍스트 내에서 fetch 실행
    result = self.page.evaluate("""
        async (url) => {
            const response = await fetch(url);
            return await response.json();
        }
    """, api_url)

    return result.get("list", [])
```

### 데이터 필드 매핑

분석 문서(`docs/analysis/naver-real-estate-final-approach.md`)에 따르면 24개 필드가 제공됩니다. CSV에는 주요 필드만 저장:

**단지 정보**:
- `complexName`: 단지명
- `markerId`: 단지 ID
- `latitude`: 위도
- `longitude`: 경도

**부동산 정보**:
- `realEstateTypeName`: 부동산 유형명 (아파트, 오피스텔 등)
- `completionYearMonth`: 완공일 (YYYYMM 형식)
- `totalDongCount`: 총 동 수
- `totalHouseholdCount`: 총 세대 수

**면적/가격**:
- `minArea`: 최소 면적 (㎡)
- `maxArea`: 최대 면적 (㎡)
- `floorAreaRatio`: 용적률

**매물 현황**:
- `dealCount`: 매매 매물 수
- `leaseCount`: 전월세 매물 수
- `totalArticleCount`: 총 매물 수

## 에러 처리 및 재시도 로직

### 에러 유형 및 대응

1. **네트워크 타임아웃**: 3회 재시도 (지수 백오프: 1초, 2초, 4초)
2. **API 오류 응답 (4xx, 5xx)**: 실패 목록에 기록 후 다음 동으로 진행
3. **빈 결과 (totalCount=0)**: 정상으로 간주하고 다음으로 진행
4. **Playwright 오류**: 브라우저 재시작 후 현재 동부터 재시도

### 재시도 로직

```python
def _fetch_with_retry(self, dong: dict, max_retries: int = 3) -> list[dict[str, Any]]:
    for attempt in range(max_retries):
        try:
            data = self._fetch_dong_data(dong)
            time.sleep(0.5)  # Rate limiting
            return data
        except TimeoutError:
            if attempt == max_retries - 1:
                self.checkpoint_manager.add_failed_dong(dong, "Timeout after retries")
                return []
            time.sleep(2 ** attempt)  # 지수 백오프
        except Exception as e:
            self.logger.error("fetch_error", dong=dong["dong_name"], error=str(e))
            self.checkpoint_manager.add_failed_dong(dong, str(e))
            return []
    return []
```

### Rate Limiting

각 API 호출 후 500ms 대기하여 서버 부하 방지 및 차단 위험 감소.

## 테스트 전략

### 단위 테스트

1. **CheckpointManager 테스트** (`tests/unit/test_checkpoint_manager.py`)
   - 체크포인트 저장/로드
   - 완료/실패 동 추적
   - 건너뛰기 로직

2. **데이터 파싱 테스트** (`tests/unit/test_naver_crawler.py`)
   - Mock API 응답으로 필드 매핑 검증
   - 빈 결과 처리
   - 잘못된 JSON 형식 처리

3. **재시도 로직 테스트**
   - 타임아웃 시 재시도 횟수 확인
   - 지수 백오프 검증

### 통합 테스트

1. **실제 API 호출 테스트** (`tests/integration/test_naver_integration.py`) (선택적)
   - 한 개 동만 크롤링하여 전체 파이프라인 검증
   - CI에서는 skip 처리 가능 (네트워크 의존)

2. **체크포인트 복구 테스트**
   - 중간에 중단 시뮬레이션 후 재시작하여 이어지는지 확인

### Mock 전략

- Playwright의 `page.evaluate()` 호출은 Mock 처리
- 실제 네이버 부동산 API 응답 샘플을 `tests/fixtures/naver_api_response.json`에 저장하여 사용

## 실행 및 모니터링

### 실행 방법

```bash
# 처음부터 실행
python scripts/main.py

# 중단된 지점부터 재개 (checkpoint.json 자동 감지)
python scripts/main.py --resume

# 실패한 동만 재시도
python scripts/main.py --retry-failed
```

### 진행 상황 모니터링

structlog를 활용한 실시간 로그:

```python
logger.info(
    "crawling_dong",
    district="강남구",
    dong="삼성동",
    progress=f"{completed}/{total}",
    complexes_found=26
)
```

### 출력 형식

- **CSV 파일**: `output/seoul_apartments_{timestamp}.csv`
- **체크포인트**: `output/checkpoint.json` (자동 업데이트)
- **실패 리포트**: 크롤링 완료 후 실패한 동 목록을 로그 또는 별도 파일로 출력

### 예상 실행 시간

- 서울시 약 400~500개 동
- 각 동당 평균 1~2초 (API 호출 + rate limiting)
- 총 예상 시간: 10~15분 (에러 없이 순조롭게 진행 시)

## 구현 우선순위

1. **Phase 1**: CheckpointManager 구현 및 테스트
2. **Phase 2**: 서울시 지역 데이터 수집 및 JSON 파일 작성
3. **Phase 3**: NaverRealEstateCrawler 기본 구조 구현
4. **Phase 4**: API 호출 및 데이터 파싱 로직 구현
5. **Phase 5**: 에러 처리 및 재시도 로직 추가
6. **Phase 6**: CSV 저장 및 체크포인트 통합
7. **Phase 7**: 통합 테스트 및 실제 크롤링 검증

## 고려사항 및 제약

- **법적/윤리적 준수**: 네이버 부동산 이용약관 및 robots.txt 확인 필요
- **API 변경 가능성**: API URL이나 응답 구조 변경 시 수정 필요
- **차단 위험**: Rate limiting과 User-Agent 설정으로 최소화하지만, 장시간 크롤링 시 IP 차단 가능성 존재
- **데이터 정확성**: API 응답이 실시간이 아닐 수 있으며, 일부 필드가 누락될 수 있음
