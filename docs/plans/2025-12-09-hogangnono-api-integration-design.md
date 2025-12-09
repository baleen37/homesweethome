# 호갱노노 API 연동 재설계

**작성일**: 2025-12-09
**목적**: 호갱노노 API 분석 보고서 기반 완전한 데이터 수집 파이프라인 구축
**참고**: `hogangnono_api_analysis_report.md`

---

## 1. 개요

### 목표
- 호갱노노 API를 통해 **전국 아파트 단지 정보 + 실거래 내역** 완전 수집
- 계층적 데이터 수집: 시/도 → 구/군 → 단지 → 실거래 내역
- 안정적이고 재시작 가능한 크롤링 시스템

### 핵심 원칙
- **YAGNI**: 필요한 기능만 구현
- **단순성**: 복잡한 추상화 지양
- **안정성**: 점진적 저장 및 checkpoint 관리
- **데이터 무결성**: 실패 시 재시도, 중단 시 재시작

---

## 2. 데이터 수집 흐름

```
1. GET /api/v2/regions
   → 전국 시/도, 구/군 목록 수집 (1회만)

2. 각 구/군마다:
   GET /api/apt/bounding
   → 단지 목록 수집 (ID, 이름, 주소, 좌표, 기본 정보)

3. 각 단지마다:
   a) GET /api/v2/apts/{aptId} (또는 detail)
      → 단지 상세 정보 (용적률, 건폐율, 주차대수 등)

   b) GET /api/v2/apts/{aptId}/monthly-reports[/more]
      → 실거래 내역 (최근 3년 or 전체 기간)

4. 구/군 완료 시마다 CSV 저장
   → hogangnono_complexes.csv
   → hogangnono_transactions.csv
   → checkpoint.json
```

---

## 3. API 클라이언트 설계

### 3.1. HogangnonoAPIClient 확장

```python
class HogangnonoAPIClient:
    """호갱노노 API 클라이언트 - 모든 API 엔드포인트 담당"""

    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.session = requests.Session()

        # 단일 AdaptiveRateLimiter (모든 API 공통)
        self.rate_limiter = AdaptiveRateLimiter(
            initial_delay=2.0,  # 기본 2초
            min_delay=1.0,      # 최소 1초
            max_delay=10.0      # 최대 10초
        )

    def get_regions(
        self,
        region_code: Optional[str] = None
    ) -> APIResponse:
        """시/도, 구/군 목록 조회

        Args:
            region_code: 특정 시/도 필터링 (예: "11" = 서울)

        Returns:
            APIResponse with regionList data

        Example Response:
            {
                "data": {
                    "regionList": [
                        {
                            "regionCode": "11",
                            "name": "서울",
                            "fullName": "서울특별시",
                            "children": [...]
                        }
                    ]
                },
                "status": "success"
            }
        """

    def get_apartments_bounding(
        self,
        params: SearchParams
    ) -> APIResponse:
        """단지 목록 조회 (좌표 기반) - 기존 메서드"""

    def get_apartment_detail(
        self,
        apt_id: str
    ) -> APIResponse:
        """단지 상세 정보 조회

        Args:
            apt_id: 단지 ID (aptHash)

        Returns:
            APIResponse with apartment detail data
        """

    def get_apartment_transactions(
        self,
        apt_id: str,
        trade_type: int = 0,
        area_no: int = 0,
        full_period: bool = False
    ) -> APIResponse:
        """실거래 내역 조회

        Args:
            apt_id: 단지 ID
            trade_type: 0=매매, 1=전세, 2=월세
            area_no: 면적 필터 (0=전체)
            full_period: True면 전체 기간, False면 최근 3년

        Returns:
            APIResponse with transaction data

        Endpoints:
            - False: /api/v2/apts/{aptId}/monthly-reports
            - True:  /api/v2/apts/{aptId}/monthly-reports/more
        """
```

### 3.2. Rate Limiting 전략

- **단일 AdaptiveRateLimiter**: 모든 API에 동일하게 적용
- **기본 지연**: 2초
- **429 에러 시**: 자동으로 지연 시간 2배 증가 (최대 10초)
- **연속 성공 시**: 점진적으로 지연 시간 감소 (최소 1초)

**장점**:
- 단순하고 이해하기 쉬움
- API별 복잡한 설정 불필요
- 자동으로 최적 속도 찾아감

---

## 4. Crawler 로직 설계

### 4.1. HogangnonoCrawler 주요 메서드

```python
class HogangnonoCrawler(APICrawler):

    def crawl(
        self,
        regions: Optional[List[str]] = None,      # ["11", "26"]
        districts: Optional[List[str]] = None,    # ["11680"]
        full_period: bool = False
    ) -> Dict[str, Any]:
        """전체 크롤링 실행

        Args:
            regions: 시/도 코드 리스트 (기본값: ["11"] 서울)
            districts: 구/군 코드 리스트 (우선순위 높음)
            full_period: 전체 기간 실거래 내역 수집 여부

        Returns:
            크롤링 통계 정보
        """

        # 1. 지역 정보 수집
        logger.info("지역 정보 수집 시작")
        all_regions = self.client.get_regions()
        target_districts = self._filter_districts(
            all_regions,
            regions,
            districts
        )
        logger.info(f"대상 구/군: {len(target_districts)}개")

        # 2. Checkpoint 로드
        checkpoint = self._load_checkpoint()
        completed_districts = checkpoint.get('completed_districts', [])

        # 3. 구/군별 크롤링
        for district in target_districts:
            if district['code'] in completed_districts:
                logger.info(f"{district['name']} 건너뛰기 (완료됨)")
                continue

            self._crawl_district(district, full_period)
            self._save_checkpoint(district)

        return self._get_stats()

    def _crawl_district(
        self,
        district: Dict[str, Any],
        full_period: bool
    ) -> None:
        """단일 구/군 크롤링

        Args:
            district: 구/군 정보 딕셔너리
            full_period: 전체 기간 수집 여부
        """

        logger.info(f"구/군 크롤링 시작", district=district['name'])

        # 2-1. 단지 목록 수집
        apartments = self._fetch_apartments_in_district(district)
        logger.info(f"단지 수집 완료", count=len(apartments))

        # 2-2. 각 단지 상세 정보 및 실거래 내역 수집
        for apt in apartments:
            try:
                # 단지 상세 정보
                apt_detail = self.client.get_apartment_detail(apt['aptHash'])

                # 실거래 내역
                transactions = self.client.get_apartment_transactions(
                    apt['aptHash'],
                    full_period=full_period
                )

                # 데이터 병합 및 저장
                self._save_apartment_data(apt, apt_detail, transactions)

            except Exception as e:
                logger.error(
                    "단지 처리 실패",
                    apt_id=apt['aptHash'],
                    error=str(e)
                )
                raise  # 실패 시 즉시 중단

        logger.info(f"구/군 크롤링 완료", district=district['name'])

    def _fetch_apartments_in_district(
        self,
        district: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """구/군 내 모든 단지 수집

        좌표 기반 bounding API 사용
        필요 시 구/군을 여러 그리드로 분할하여 수집
        """

    def _save_apartment_data(
        self,
        apt: Dict[str, Any],
        apt_detail: Dict[str, Any],
        transactions: Dict[str, Any]
    ) -> None:
        """단지 정보 및 실거래 내역 CSV 저장

        - hogangnono_complexes.csv에 append
        - hogangnono_transactions.csv에 append
        """
```

### 4.2. 에러 처리 및 재시도

```python
# 모든 API 호출에 적용
@retry_with_backoff(max_retries=3, initial_delay=1.0)
def _call_api(self, method, *args, **kwargs):
    """API 호출 with 재시도

    - 최대 3회 재시도
    - 지수 백오프 (1초 → 2초 → 4초)
    - 실패 시 예외 발생하여 전체 중단
    """
```

**에러 처리 전략**:
- **429 (Rate Limit)**: AdaptiveRateLimiter가 자동 조절
- **404**: 단지 삭제된 경우, 로그 후 건너뛰기 고려 (구현 시 결정)
- **500/Timeout/Network**: 재시도 3회 후 실패 시 예외 발생
- **예외 발생 시**: 전체 크롤링 중단, checkpoint에서 재시작 가능

---

## 5. 데이터 저장 구조

### 5.1. CSV 파일 구조

**hogangnono_complexes.csv** - 단지 정보
```csv
aptHash,aptName,address,lat,lng,buildYear,household,dong,regionCode,...
1Hq6f,래미안,서울특별시 강남구 개포동,37.5135,127.0434,2005,1012,개포동,11680,...
```

**호갱노노 API 응답 구조 그대로 저장**:
- bounding API 응답 필드
- detail API 응답 필드 (병합)
- 원본 데이터 최대한 보존
- 필드명은 호갱노노 API와 동일하게 유지

**hogangnono_transactions.csv** - 실거래 내역
```csv
aptHash,date,price,floor,area,category,volume,...
1Hq6f,2025-01-18,340000,9,84.95,1,3,...
```

**monthly-reports API 응답 구조 그대로 저장**:
- 거래일, 가격, 층, 면적 등
- 중첩된 JSON은 flatten하여 저장
- 가격은 만원 단위 (API 원본 그대로)

### 5.2. 저장 방식

```python
# 구/군 단위 점진적 저장
def _save_checkpoint(self, district: Dict[str, Any]):
    """Checkpoint 저장

    checkpoint.json 구조:
    {
        "completed_districts": ["11680", "11650"],
        "current_district": "11710",
        "total_complexes": 1234,
        "total_transactions": 56789,
        "last_updated": "2025-12-09T10:30:00"
    }
    """
```

**특징**:
- 구/군 완료 시마다 CSV에 append
- Checkpoint 업데이트
- 중복 제거: aptHash 기준
- 원자적 저장: 임시 파일 사용

---

## 6. 설정 및 실행

### 6.1. 설정 옵션

```python
# scripts/main.py 인자
--regions 11,26           # 서울, 부산
--districts 11680,11650   # 강남구, 서초구
--full-period             # 전체 기간 실거래 내역
--resume                  # 중단된 지점부터 재개
--output output/          # 출력 디렉토리
```

### 6.2. 실행 예시

```bash
# 서울 전체 크롤링 (기본값, 최근 3년)
python scripts/main.py

# 서울 + 부산 크롤링
python scripts/main.py --regions 11,26

# 강남구만 크롤링
python scripts/main.py --districts 11680

# 전체 기간 데이터 수집
python scripts/main.py --full-period

# 중단된 지점부터 재개
python scripts/main.py --resume
```

### 6.3. 예상 소요 시간

**서울 기준** (25개 구, 약 2,500개 단지):

| 단계 | API 호출 횟수 | 평균 지연 | 예상 시간 |
|------|--------------|----------|----------|
| 지역 정보 | 1회 | 2초 | 2초 |
| 단지 목록 | 25회 | 2초 | 50초 |
| 단지 상세 | 2,500회 | 2초 | 83분 |
| 실거래 내역 | 2,500회 | 2초 | 83분 |
| **합계** | **5,026회** | - | **약 2.8시간** |

**전국 크롤링** (250개 구/군, 약 50,000개 단지):
- 예상 시간: **약 56시간** (2일 이상)
- Checkpoint로 중단/재개 필수

---

## 7. 구현 순서

### Phase 1: API Client 확장
1. `get_regions()` 구현 및 테스트
2. `get_apartment_detail()` 구현 및 테스트
3. `get_apartment_transactions()` 구현 및 테스트

### Phase 2: Crawler 로직 구현
4. `_filter_districts()` - 지역 필터링
5. `_crawl_district()` - 구/군 크롤링
6. `_fetch_apartments_in_district()` - 단지 목록 수집
7. `_save_apartment_data()` - 데이터 저장

### Phase 3: 통합 및 테스트
8. Checkpoint 관리 로직
9. 에러 처리 및 재시도
10. 엔드투엔드 테스트 (서울 1개 구)

### Phase 4: 최적화
11. 성능 튜닝
12. 로깅 개선
13. 문서화

---

## 8. 제약사항 및 고려사항

### 제약사항
- **Rate Limiting**: 기본 2초 간격, 429 에러 시 자동 증가
- **API 변경**: 호갱노노 API는 변경될 수 있음
- **데이터 완전성**: detail API 엔드포인트가 존재하지 않을 수 있음 (구현 시 확인 필요)

### 향후 개선 가능 항목
- 병렬 처리 (asyncio/aiohttp)
- 데이터베이스 저장 (PostgreSQL)
- 증분 업데이트 (신규 데이터만 수집)
- 모니터링 대시보드

---

## 9. 성공 기준

✅ 서울 25개 구 완전 수집 가능
✅ 단지 정보 + 상세 정보 + 실거래 내역 모두 수집
✅ 중단 시 checkpoint에서 재시작 가능
✅ Rate limiting으로 안정적 수집
✅ CSV 형식으로 데이터 저장
✅ 테스트 커버리지 80% 이상

---

## 부록: API 엔드포인트 정리

| API | Method | Endpoint | 설명 |
|-----|--------|----------|------|
| 지역 목록 | GET | /api/v2/regions | 시/도, 구/군 목록 |
| 단지 목록 | GET | /api/apt/bounding | 좌표 기반 단지 조회 |
| 단지 상세 | GET | /api/v2/apts/{aptId} | 단지 상세 정보 (추정) |
| 실거래 3년 | GET | /api/v2/apts/{aptId}/monthly-reports | 최근 3년 |
| 실거래 전체 | GET | /api/v2/apts/{aptId}/monthly-reports/more | 전체 기간 |
