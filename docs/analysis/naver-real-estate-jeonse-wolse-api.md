# 네이버 부동산 전세/월세 거래내역 API 분석

## 개요

네이버 부동산 단지 페이지의 전세/월세 거래내역 API 엔드포인트를 조사한 결과를 정리합니다.

**조사 일시**: 2025-12-06
**테스트 단지**: 헬리오시티 (complex ID: 111515, 서울시 송파구 가락동)
**조사 방법**: Playwright MCP를 사용한 브라우저 네트워크 모니터링

## 핵심 발견사항

### 1. 거래 유형 코드 (tradeType)

네이버 부동산은 거래 유형을 다음과 같이 구분합니다:

- **A1**: 매매 (기존 확인됨)
- **B1**: 전세
- **B2**: 월세
- **B3**: 단기임대 (추정)

### 2. 전세와 월세는 **동일한 API**를 사용

전세(B1)와 월세(B2)는 별도의 API가 아니라, **동일한 API 엔드포인트에서 `tradeType` 파라미터만 변경**하여 사용합니다.

## API 엔드포인트 목록

### 1. 실거래가 목록 조회

**기본 정보**
- **URL**: `https://fin.land.naver.com/front-api/v1/complex/pyeong/realPrice`
- **Method**: GET
- **용도**: 특정 단지의 실거래가 목록을 페이지네이션으로 조회

**필수 파라미터**
| 파라미터 | 타입 | 설명 | 예시 |
|---------|------|------|------|
| `complexNumber` | number | 단지 ID | `111515` |
| `pyeongTypeNumber` | number | 평형 타입 번호 | `1` |
| `tradeType` | string | 거래 유형 (B1: 전세, B2: 월세) | `B1` |
| `page` | number | 페이지 번호 (1부터 시작) | `1` |
| `size` | number | 페이지당 결과 개수 | `10` |

**요청 예시**
```
# 전세
GET https://fin.land.naver.com/front-api/v1/complex/pyeong/realPrice?complexNumber=111515&pyeongTypeNumber=1&page=1&size=10&tradeType=B1

# 월세
GET https://fin.land.naver.com/front-api/v1/complex/pyeong/realPrice?complexNumber=111515&pyeongTypeNumber=1&page=1&size=10&tradeType=B2
```

**응답 구조 (추정)**
```json
{
  "list": [
    {
      "contractDate": "2025-12-02",
      "floor": 8,
      "price": 643860000,      // 전세가 (전세의 경우)
      "deposit": 116280000,    // 보증금 (월세의 경우)
      "monthlyRent": 410000,   // 월세 (월세의 경우)
      // ... 기타 필드
    }
  ],
  "totalCount": 45,
  "page": 1,
  "size": 10
}
```

### 2. 실거래가 요약 정보

**기본 정보**
- **URL**: `https://fin.land.naver.com/front-api/v1/complex/pyeong/realPrice/summary`
- **Method**: GET
- **용도**: 특정 기간 동안의 실거래가 요약 정보 (최고/최저/평균 등)

**필수 파라미터**
| 파라미터 | 타입 | 설명 | 예시 |
|---------|------|------|------|
| `complexNumber` | number | 단지 ID | `111515` |
| `pyeongTypeNumber` | number | 평형 타입 번호 | `1` |
| `realEstateType` | string | 부동산 유형 (A01: 아파트) | `A01` |
| `tradeType` | string | 거래 유형 (B1: 전세, B2: 월세) | `B1` |
| `startDate` | string | 시작일 (YYYY-MM-DD) | `2025-09-06` |

**요청 예시**
```
# 전세 요약 (최근 3개월)
GET https://fin.land.naver.com/front-api/v1/complex/pyeong/realPrice/summary?complexNumber=111515&pyeongTypeNumber=1&realEstateType=A01&tradeType=B1&startDate=2025-09-06

# 월세 요약 (최근 3개월)
GET https://fin.land.naver.com/front-api/v1/complex/pyeong/realPrice/summary?complexNumber=111515&pyeongTypeNumber=1&realEstateType=A01&tradeType=B2&startDate=2025-09-06
```

**응답 구조 (추정)**
```json
{
  "recentPrice": 643860000,      // 최근 거래가
  "recentContractDate": "2025-12-02",
  "averagePrice3Month": 660550000,  // 3개월 평균
  "maxPrice2Year": 800000000,    // 2년 내 최고가
  "minPrice2Year": 300000000,    // 2년 내 최저가
  // ... 기타 통계
}
```

### 3. 실거래가 상세 목록 (기간별)

**기본 정보**
- **URL**: `https://fin.land.naver.com/front-api/v1/complex/pyeong/realPrice/list`
- **Method**: GET
- **용도**: 특정 기간의 실거래가 전체 목록 조회 (페이지네이션 없음)

**필수 파라미터**
| 파라미터 | 타입 | 설명 | 예시 |
|---------|------|------|------|
| `complexNumber` | number | 단지 ID | `111515` |
| `pyeongTypeNumber` | number | 평형 타입 번호 | `1` |
| `realEstateType` | string | 부동산 유형 | `A01` |
| `tradeType` | string | 거래 유형 | `B1` |
| `startDate` | string | 시작일 | `2024-12-06` |
| `endDate` | string | 종료일 | `2025-12-06` |

**요청 예시**
```
# 전세 (최근 1년)
GET https://fin.land.naver.com/front-api/v1/complex/pyeong/realPrice/list?complexNumber=111515&endDate=2025-12-06&pyeongTypeNumber=1&realEstateType=A01&startDate=2024-12-06&tradeType=B1

# 월세 (최근 1년)
GET https://fin.land.naver.com/front-api/v1/complex/pyeong/realPrice/list?complexNumber=111515&endDate=2025-12-06&pyeongTypeNumber=1&realEstateType=A01&startDate=2024-12-06&tradeType=B2
```

### 4. 시세 정보 조회

**기본 정보**
- **URL**: `https://fin.land.naver.com/front-api/v1/complex/askingPrice`
- **Method**: GET
- **용도**: KB/한국부동산원 시세 정보 조회

**필수 파라미터**
| 파라미터 | 타입 | 설명 | 예시 |
|---------|------|------|------|
| `complexNumber` | number | 단지 ID | `111515` |
| `pyeongTypeNumber` | number | 평형 타입 번호 | `1` |
| `realEstateType` | string | 부동산 유형 | `A01` |
| `tradeType` | string | 거래 유형 | `B1` 또는 `B2` |

**요청 예시**
```
# 전세 시세
GET https://fin.land.naver.com/front-api/v1/complex/askingPrice?complexNumber=111515&pyeongTypeNumber=1&realEstateType=A01&tradeType=B1

# 월세 시세
GET https://fin.land.naver.com/front-api/v1/complex/askingPrice?complexNumber=111515&pyeongTypeNumber=1&realEstateType=A01&tradeType=B2
```

**응답 구조 (추정)**
```json
{
  "provider": "KB부동산",
  "date": "2025-12-05",
  "maxPrice": 700000000,    // 상한가
  "minPrice": 620000000,    // 하한가
  // 월세의 경우
  "deposit": 100000000,     // 보증금
  "monthlyRentMin": 2200000, // 월세 하한
  "monthlyRentMax": 2500000  // 월세 상한
}
```

### 5. 평형별 가격 정보

**기본 정보**
- **URL**: `https://fin.land.naver.com/front-api/v1/complex/pyeongPrice/pyeongType`
- **Method**: GET
- **용도**: 특정 평형의 현재 가격 정보

**필수 파라미터**
| 파라미터 | 타입 | 설명 | 예시 |
|---------|------|------|------|
| `complexNumber` | number | 단지 ID | `111515` |
| `pyeongTypeNumber` | number | 평형 타입 번호 | `1` |
| `tradeType` | string | 거래 유형 | `B1` 또는 `B2` |

**요청 예시**
```
GET https://fin.land.naver.com/front-api/v1/complex/pyeongPrice/pyeongType?complexNumber=111515&pyeongTypeNumber=1&tradeType=B2
```

## 매매 API와의 차이점

### 공통점
1. **동일한 API 구조**: 엔드포인트 URL, 파라미터 형식이 매매(A1)와 동일
2. **브라우저 세션 필수**: 직접 API 호출 시 429 Too Many Requests 에러 발생
3. **페이지네이션 지원**: `page`와 `size` 파라미터로 페이지네이션 구현
4. **기간별 조회 가능**: `startDate`와 `endDate`로 기간 필터링

### 차이점
1. **tradeType 파라미터만 다름**
   - 매매: `tradeType=A1`
   - 전세: `tradeType=B1`
   - 월세: `tradeType=B2`

2. **응답 데이터 구조**
   - 매매: `price` 필드만 존재
   - 전세: `price` 필드 (전세금)
   - 월세: `deposit` (보증금) + `monthlyRent` (월세) 필드

3. **시세 정보 차이**
   - 매매: 단일 가격 범위
   - 전세: 단일 가격 범위
   - 월세: 보증금 + 월세 범위 (두 값의 조합)

## 크롤링 구현 시 고려사항

### 1. API 호출 제약사항
- **브라우저 컨텍스트 필수**: Playwright MCP의 `browser_evaluate` + `fetch()` 조합 사용 필요
- **Rate Limiting**: 요청 간 2~4초 대기 권장
- **세션 관리**: 브라우저 세션 내에서만 API 접근 가능

### 2. 데이터 필드 처리
- 월세는 보증금과 월세를 **분리된 필드**로 저장
- 표시 형식: `보증금/월세` (예: "1억 1,628/41" → deposit: 116,280,000, monthlyRent: 410,000)
- 전세는 단일 `price` 필드만 사용

### 3. 크롤링 순서 권장사항
```python
# 1. 매매 거래내역 크롤링 (tradeType=A1)
# 2. 전세 거래내역 크롤링 (tradeType=B1)
# 3. 월세 거래내역 크롤링 (tradeType=B2)
# 각 거래 유형별로 동일한 크롤링 로직 재사용 가능
```

### 4. CSV 저장 시 필드 설계
```csv
complex_id,trade_type,contract_date,floor,price,deposit,monthly_rent
111515,B1,2025-12-02,8,643860000,,
111515,B2,2025-12-04,7,,116280000,410000
```

## 실제 사용 예시

### Python + Playwright (권장)
```python
from playwright.sync_api import sync_playwright

def fetch_jeonse_data(complex_id: int, pyeong_type: int, page: int = 1, size: int = 20):
    """전세 거래내역 조회"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # 먼저 단지 페이지 방문 (세션 생성)
        page.goto(f"https://fin.land.naver.com/complexes/{complex_id}")

        # browser_evaluate로 API 호출
        result = page.evaluate(f"""
            async () => {{
                const response = await fetch(
                    '/front-api/v1/complex/pyeong/realPrice?complexNumber={complex_id}&pyeongTypeNumber={pyeong_type}&page={page}&size={size}&tradeType=B1'
                );
                return await response.json();
            }}
        """)

        browser.close()
        return result

def fetch_wolse_data(complex_id: int, pyeong_type: int, page: int = 1, size: int = 20):
    """월세 거래내역 조회 - 전세와 동일한 로직, tradeType만 B2로 변경"""
    # ... 위와 동일하되 tradeType=B2
```

## 결론

1. **전세와 월세는 동일 API 사용**: `tradeType` 파라미터로 구분 (B1: 전세, B2: 월세)
2. **매매 API와 구조 동일**: 기존 매매 크롤러를 `tradeType` 파라미터만 변경하여 재사용 가능
3. **월세는 2개 필드 필요**: `deposit` (보증금) + `monthlyRent` (월세)
4. **브라우저 컨텍스트 필수**: Playwright를 통한 API 호출만 가능
5. **Rate Limiting 주의**: 요청 간 대기 시간 필수

## 참고 문서
- 매매 API 분석: `docs/analysis/naver-real-estate-final-approach.md`
- 네이버 부동산 크롤링 가이드: `docs/analysis/naver-real-estate-crawling.md`
