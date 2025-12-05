# 서울시 전체 아파트 단지 크롤링 설계

**작성일**: 2025-12-06
**목표**: 서울시 전체 아파트 단지의 상세 정보 및 거래내역을 한 번의 실행으로 크롤링하여 CSV로 저장

---

## 1. 크롤링 범위 및 데이터 종류

### 크롤링 범위
- **지역**: 서울시 전체 (25개 구, 약 400+개 동)
- **대상**: 모든 아파트 단지

### 수집 데이터 종류
1. **기본 단지 정보** (이미 구현됨)
   - complex_id, complex_name, real_estate_type
   - completion_year_month, total_dong_count, total_household_count
   - min_area, max_area, deal_count, lease_count, rent_count

2. **단지 상세 정보** (`fetch_complex_detail` 활용)
   - 평형별 정보 (pyeongList)
   - 보유세 정보 (holdingTax)
   - 공시가격 (declaredValue)
   - 매물 가격 분포 (askingPrice)
   - 최근 시세 (marketPrice)

3. **거래내역 (신규 구현 필요)**
   - 매매 거래내역 (tradeType=A1)
   - 전세 거래내역 (tradeType=B1)
   - 월세 거래내역 (tradeType=B2)
   - **기간**: 가능한 모든 기간 (5년 이상)

---

## 2. 전체 아키텍처 및 데이터 플로우

### 크롤링 플로우

```
1. 동(洞) 순회 (서울시 400+개 동)
   ↓
2. 각 동의 단지 목록 수집
   - 기존 crawl() 메서드 사용
   - 모바일 API: /cluster/ajax/complexList
   ↓
3. 각 단지별로 상세 정보 수집
   3-1. 단지 상세 정보 조회 (fetch_complex_detail)
   3-2. 평형 타입 목록 추출 (pyeongList에서)
   3-3. 각 평형별 거래내역 조회 (신규):
        - 매매 거래내역 (tradeType=A1)
        - 전세 거래내역 (tradeType=B1)
        - 월세 거래내역 (tradeType=B2)
   ↓
4. 데이터 병합 및 CSV 저장
   - complexes.csv (단지 정보 + 통계)
   - transactions.csv (거래내역 상세)
   ↓
5. 체크포인트 저장
   - 동 단위로 진행 상황 저장
   - 중단 시 재개 가능
```

### 예상 소요 시간

**단지당 평균 API 호출 수:**
- 기본 정보: 1회
- 상세 정보: 5회
- 거래내역: 평형 수 × 3 (매매/전세/월세) × 페이지 수

**예상 단지 수:** 약 10,000~15,000개
**예상 소요 시간:** 10~15시간 (적응적 Rate Limiting 적용 시)

---

## 3. 거래내역 API 엔드포인트

### API URL

**페이지네이션 방식 (권장):**
```
GET https://fin.land.naver.com/front-api/v1/complex/pyeong/realPrice
```

### 필수 파라미터

| 파라미터 | 설명 | 예시 | 필수 |
|---------|------|------|------|
| `complexNumber` | 단지 ID | `111515` | ✅ |
| `pyeongTypeNumber` | 평형 타입 번호 | `1` | ✅ |
| `tradeType` | 거래 유형 | `A1`, `B1`, `B2` | ✅ |
| `page` | 페이지 번호 | `1` | ✅ |
| `size` | 페이지당 개수 | `20` | ✅ |

### 거래 유형 코드

| 코드 | 설명 |
|-----|------|
| `A1` | 매매 |
| `B1` | 전세 |
| `B2` | 월세 |

### 응답 JSON 구조

```json
{
  "isSuccess": true,
  "result": {
    "list": [
      {
        "tradeDate": "2025-11-14",
        "tradeYear": "2025",
        "floor": 21,
        "dealPrice": 1700000000,
        "deposit": 0,
        "monthlyRent": 0,
        "isDelete": false,
        "tradeCategory": "중개거래",
        "propertyType": "NORMAL",
        "isRenew": false
      }
    ],
    "hasNextPage": true
  }
}
```

### 페이지네이션 방식

```javascript
// 1페이지
await fetch('...?page=1&size=20&tradeType=A1');

// 2페이지
await fetch('...?page=2&size=20&tradeType=A1');

// hasNextPage가 false가 될 때까지 반복
```

---

## 4. 적응적 Rate Limiting 전략

### AdaptiveRateLimiter 클래스

```python
class AdaptiveRateLimiter:
    def __init__(self):
        self.current_delay = 2.5  # 초기 대기 시간 (초)
        self.min_delay = 1.5      # 최소 대기 시간
        self.max_delay = 10.0     # 최대 대기 시간
        self.error_count = 0      # 연속 429 에러 카운트
        self.success_count = 0    # 연속 성공 카운트
```

### 적응 로직

#### 1. 성공 시
```python
success_count += 1
if success_count >= 10:
    current_delay = max(min_delay, current_delay * 0.9)  # 10% 감소
    success_count = 0
error_count = 0
```

#### 2. HTTP 429 에러 시
```python
error_count += 1
current_delay = min(max_delay, current_delay * 2)  # 2배 증가
success_count = 0

# 지수 백오프 재시도
wait_time = 2 ** attempt  # 2초 → 4초 → 8초
```

#### 3. 기타 에러 시
```python
# delay 유지
# 재시도 로직 (최대 3회)
```

### API 호출 순서별 대기 시간

```
단지 목록 조회 (동별) → 0.5초 대기
  ↓
단지 상세 조회 → current_delay (2.5초 시작)
  ↓
평형 목록 파싱 → 0초
  ↓
거래내역 조회 (평형별):
  - 매매 API (페이지 1) → current_delay
  - 매매 API (페이지 2) → current_delay
  - ...
  - 전세 API (페이지 1) → current_delay
  - ...
  - 월세 API (페이지 1) → current_delay
  - ...
```

---

## 5. 새 메서드: fetch_transaction_history()

### 메서드 시그니처

```python
def fetch_transaction_history(
    self,
    complex_id: str,
    pyeong_type_number: int,
    trade_type: str  # "A1", "B1", "B2"
) -> list[dict[str, Any]]:
    """
    특정 단지의 특정 평형에 대한 전체 거래내역 조회

    페이지네이션 방식 사용:
    - page=1부터 시작
    - hasNextPage=false가 될 때까지 반복
    - Rate limiter 적용하여 API 호출

    Args:
        complex_id: 단지 ID
        pyeong_type_number: 평형 타입 번호
        trade_type: 거래 유형 ("A1", "B1", "B2")

    Returns:
        거래내역 리스트 (전체 페이지 합친 결과)
    """
```

### 구현 로직

```python
all_transactions = []
page = 1
max_pages = 100  # 안전장치

while page <= max_pages:
    # Rate limiter 적용
    self.rate_limiter.wait()

    # API 호출
    api_url = (
        f"https://fin.land.naver.com/front-api/v1/complex/pyeong/realPrice?"
        f"complexNumber={complex_id}&"
        f"pyeongTypeNumber={pyeong_type_number}&"
        f"tradeType={trade_type}&"
        f"page={page}&"
        f"size=20"
    )

    try:
        response = self.page.evaluate(
            """
            async (url) => {
                const response = await fetch(url);
                return await response.json();
            }
            """,
            api_url,
        )

        # 성공 시 rate limiter 업데이트
        self.rate_limiter.on_success()

        # 데이터 추출
        if response.get("isSuccess"):
            result = response.get("result", {})
            transactions = result.get("list", [])
            all_transactions.extend(transactions)

            # 다음 페이지 확인
            if not result.get("hasNextPage", False):
                break

            page += 1
        else:
            break

    except Exception as e:
        if "429" in str(e):
            self.rate_limiter.on_rate_limit_error()
            # 재시도 로직
        else:
            self.rate_limiter.on_error()
            break

return all_transactions
```

### 거래내역 데이터 정규화

```python
def _parse_transaction(
    self,
    raw_transaction: dict[str, Any],
    complex_id: str,
    complex_name: str,
    pyeong_type_number: int,
    pyeong_name: str,
    trade_type: str
) -> dict[str, Any]:
    """거래내역 원본 데이터를 CSV 저장용으로 정규화"""

    # 거래 유형명 매핑
    trade_type_names = {
        "A1": "매매",
        "B1": "전세",
        "B2": "월세"
    }

    return {
        "complex_id": complex_id,
        "complex_name": complex_name,
        "pyeong_type_number": pyeong_type_number,
        "pyeong_name": pyeong_name,
        "trade_type": trade_type,
        "trade_type_name": trade_type_names.get(trade_type, ""),
        "trade_date": raw_transaction.get("tradeDate", ""),
        "trade_year": raw_transaction.get("tradeYear", ""),
        "floor": raw_transaction.get("floor", 0),
        "deal_price": raw_transaction.get("dealPrice", 0),
        "deposit": raw_transaction.get("deposit", 0),
        "monthly_rent": raw_transaction.get("monthlyRent", 0),
        "trade_category": raw_transaction.get("tradeCategory", ""),
        "is_delete": raw_transaction.get("isDelete", False),
        "is_renew": raw_transaction.get("isRenew", False),
    }
```

---

## 6. CSV 스키마 및 저장 전략

### 1. complexes.csv (단지 정보 + 통계)

#### 기본 필드 (현재 구현)
- `complex_id`: 단지 ID
- `complex_name`: 단지명
- `real_estate_type`: 매물 유형
- `completion_year_month`: 준공년월
- `total_dong_count`: 총 동 수
- `total_household_count`: 총 세대수
- `min_area`: 최소 면적
- `max_area`: 최대 면적
- `deal_count`: 매매 매물 수
- `lease_count`: 전세 매물 수
- `rent_count`: 월세 매물 수

#### 추가 필드 (상세 정보)
- `pyeong_types`: 평형 정보 (JSON 문자열)
- `fetched_at`: 상세 정보 조회 시각

#### 추가 필드 (거래내역 통계)
- `total_transaction_count`: 전체 거래 건수
- `latest_deal_price`: 최근 매매가
- `latest_deal_date`: 최근 매매일
- `avg_deal_price_1year`: 최근 1년 평균 매매가
- `deal_count_1year`: 최근 1년 매매 건수
- `lease_count_1year`: 최근 1년 전세 건수
- `rent_count_1year`: 최근 1년 월세 건수

### 2. transactions.csv (거래내역 상세)

#### 모든 필드
```
complex_id, complex_name,
pyeong_type_number, pyeong_name,
trade_type, trade_type_name,
trade_date, trade_year, floor,
deal_price, deposit, monthly_rent,
trade_category, is_delete, is_renew
```

#### 샘플 데이터
```csv
complex_id,complex_name,pyeong_type_number,pyeong_name,trade_type,trade_type_name,trade_date,trade_year,floor,deal_price,deposit,monthly_rent,trade_category,is_delete,is_renew
111515,헬리오시티,1,84A,A1,매매,2025-11-14,2025,21,1700000000,0,0,중개거래,false,false
111515,헬리오시티,1,84A,B1,전세,2025-10-20,2025,15,0,800000000,0,중개거래,false,false
111515,헬리오시티,1,84A,B2,월세,2025-09-10,2025,8,0,100000000,2000000,중개거래,false,false
```

### 저장 전략

#### 점진적 저장 (Incremental Write)

**동 단위로 저장:**
```python
# 동별 크롤링 완료 시마다
for dong in dongs:
    complexes = crawl_dong(dong)

    for complex in complexes:
        # 상세 정보 조회
        detail = fetch_complex_detail(complex_id)

        # 거래내역 조회 (평형별)
        for pyeong in detail["pyeong_types"]:
            for trade_type in ["A1", "B1", "B2"]:
                transactions = fetch_transaction_history(
                    complex_id,
                    pyeong["pyeong_type_number"],
                    trade_type
                )

                # transactions.csv에 즉시 append
                append_to_csv("output/transactions.csv", transactions)

        # 통계 계산
        complex_with_stats = calculate_statistics(complex, transactions)

        # complexes.csv에 append
        append_to_csv("output/complexes.csv", [complex_with_stats])

    # 동 단위 체크포인트 저장
    save_checkpoint(dong_id)
```

**파일 위치:**
```
output/
  ├── complexes.csv         # 단지 정보 + 통계
  ├── transactions.csv      # 전체 거래내역
  └── checkpoint.json       # 진행 상황
```

#### 체크포인트 확장

```json
{
  "last_dong": "1154510200",
  "last_complex": "111515",
  "total_complexes_processed": 1523,
  "total_transactions_collected": 245678,
  "started_at": "2025-12-06T10:00:00",
  "last_updated_at": "2025-12-06T15:30:00",
  "rate_limiter_state": {
    "current_delay": 2.8,
    "success_count": 45,
    "error_count": 0
  }
}
```

---

## 7. 에러 처리 및 복원력

### 1. Rate Limit (HTTP 429) 처리

```python
try:
    response = fetch_api(url)
except RateLimitError:
    # 1. delay 증가
    rate_limiter.on_rate_limit_error()

    # 2. 지수 백오프 재시도
    for attempt in range(3):
        wait_time = 2 ** attempt
        time.sleep(wait_time)
        try:
            response = fetch_api(url)
            break
        except RateLimitError:
            continue
    else:
        # 3회 실패 시 해당 항목 건너뛰고 로그 기록
        log_failed_item(complex_id, "Rate limit exceeded")
```

### 2. 네트워크 에러 처리

```python
try:
    response = fetch_api(url)
except NetworkError:
    # 재시도 (최대 3회)
    for attempt in range(3):
        time.sleep(5)
        try:
            response = fetch_api(url)
            break
        except NetworkError:
            continue
    else:
        log_failed_item(complex_id, "Network error")
```

### 3. 데이터 검증

```python
def validate_transaction(transaction: dict) -> bool:
    """거래내역 데이터 유효성 검증"""
    # 삭제된 거래는 제외
    if transaction.get("isDelete", False):
        return False

    # 필수 필드 확인
    required_fields = ["tradeDate", "floor"]
    for field in required_fields:
        if field not in transaction:
            return False

    # 가격 필드 확인 (거래 유형별)
    # 매매: dealPrice > 0
    # 전세: deposit > 0
    # 월세: deposit >= 0 and monthlyRent > 0

    return True
```

### 4. 중단 시 재개

```python
# 체크포인트에서 재개
checkpoint = load_checkpoint()
if checkpoint:
    last_dong = checkpoint["last_dong"]
    logger.info(f"Resuming from checkpoint: {last_dong}")

    # last_dong 이후부터 크롤링 시작
    start_crawling_from(last_dong)
```

---

## 8. 테스트 전략

### 통합 테스트 단계

#### Level 1: 단일 평형 거래내역 테스트
```python
def test_fetch_transaction_history_single_pyeong():
    """단일 평형의 매매 거래내역 조회 테스트"""
    crawler = NaverRealEstateCrawler(config)
    transactions = crawler.fetch_transaction_history(
        complex_id="111515",
        pyeong_type_number=1,
        trade_type="A1"
    )

    assert len(transactions) > 0
    assert "tradeDate" in transactions[0]
    assert "dealPrice" in transactions[0]
```

#### Level 2: 전체 거래 유형 테스트
```python
def test_fetch_all_trade_types():
    """매매/전세/월세 모두 조회 테스트"""
    crawler = NaverRealEstateCrawler(config)

    for trade_type in ["A1", "B1", "B2"]:
        transactions = crawler.fetch_transaction_history(
            complex_id="111515",
            pyeong_type_number=1,
            trade_type=trade_type
        )
        assert isinstance(transactions, list)
```

#### Level 3: 단지 전체 파이프라인 테스트
```python
def test_crawl_complex_full_pipeline():
    """단일 단지의 전체 파이프라인 테스트"""
    crawler = NaverRealEstateCrawler(config)

    # 1. 단지 상세 조회
    detail = crawler.fetch_complex_detail("111515")
    assert "pyeong_types" in detail

    # 2. 평형별 거래내역 조회
    all_transactions = []
    for pyeong in detail["pyeong_types"]:
        for trade_type in ["A1", "B1", "B2"]:
            transactions = crawler.fetch_transaction_history(
                "111515",
                pyeong["pyeong_type_number"],
                trade_type
            )
            all_transactions.extend(transactions)

    # 3. CSV 저장
    save_transactions_csv(all_transactions)
    assert os.path.exists("output/transactions.csv")
```

#### Level 4: 동 단위 크롤링 테스트
```python
def test_crawl_dong_with_transactions():
    """단일 동의 전체 크롤링 + 거래내역 테스트"""
    # 금천구 첫 번째 동만 크롤링
    # 거래내역까지 모두 수집
    # CSV 저장 확인
```

---

## 9. 구현 우선순위

### Phase 1: 거래내역 API 통합 (필수)
1. `AdaptiveRateLimiter` 클래스 구현
2. `fetch_transaction_history()` 메서드 구현
3. 거래내역 파싱 로직 구현
4. 단위 테스트 작성

### Phase 2: CSV 스키마 확장
1. `TransactionCSVWriter` 클래스 구현
2. `complexes.csv` 통계 필드 추가
3. 점진적 저장 로직 구현
4. 체크포인트 확장

### Phase 3: 전체 파이프라인 통합
1. `crawl()` 메서드 확장 (거래내역 포함)
2. 에러 처리 강화
3. 통합 테스트 작성
4. 문서 업데이트

### Phase 4: 최적화 및 모니터링
1. 진행 상황 로깅 개선
2. 통계 출력 (완료/남은 단지 수 등)
3. 성능 최적화
4. 에러 리포트 생성

---

## 10. 예상 문제 및 해결 방안

### 문제 1: Rate Limiting으로 인한 실행 시간 증가
**해결**: 적응적 Rate Limiter로 최적 속도 자동 조정

### 문제 2: 중단 시 데이터 유실
**해결**: 동 단위 체크포인트 + 점진적 CSV 저장

### 문제 3: 메모리 부족 (거래내역 데이터 양)
**해결**: 평형별/거래 유형별로 즉시 CSV에 append (메모리에 전체 데이터 보관 안 함)

### 문제 4: API 응답 구조 변경
**해결**: 응답 검증 로직 + 에러 로깅으로 빠른 대응

### 문제 5: 평형 정보 없는 단지
**해결**: pyeong_types가 비어있으면 거래내역 수집 건너뛰기

---

## 11. 성공 기준

### 기능 요구사항
- [x] 서울시 전체 단지 크롤링 가능
- [x] 단지 상세 정보 수집
- [x] 거래내역 (매매/전세/월세) 전체 기간 수집
- [x] CSV 2개 파일로 저장 (complexes.csv, transactions.csv)
- [x] 체크포인트로 중단 시 재개 가능

### 품질 요구사항
- [x] Rate limit 에러 최소화 (적응적 조절)
- [x] 데이터 유실 방지 (점진적 저장)
- [x] 테스트 커버리지 80% 이상
- [x] 에러 발생 시 로그 기록 및 계속 진행

### 성능 요구사항
- [x] 예상 완료 시간 15시간 이내
- [x] 메모리 사용량 1GB 이내
- [x] 중단 시 재시작 오버헤드 5분 이내

---

## 12. 다음 단계

1. **설계 검토 및 승인**
2. **구현 계획 수립** (상세 구현 계획 문서 작성)
3. **TDD로 구현** (테스트 먼저 작성)
4. **통합 테스트** (금천구 1개 동으로 전체 파이프라인 검증)
5. **서울시 전체 실행**
