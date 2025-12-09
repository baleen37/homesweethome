# 호갱노노 API 데이터 구조 종합 분석 보고서

## 개요

본 보고서는 호갱노노(https://hogangnono.com) 웹사이트의 API 구조를 체계적으로 분석하여 시/도 > 구/군 > 동 > 아파트 단지 > 실거래 내역 순서로 데이터를 수집하는 방법을 정리한 문서입니다. MCP Playwright를 사용한 6단계 서브에이전트 분석 과정을 통해 실제 API 호출 및 네트워크 분석을 수행했습니다.

**분석 기간**: 2025-01-09
**분석 방법**: Playwright MCP를 통한 실제 API 호출 및 네트워크 분석 (6개 서브에이전트 순차 분석)
**목표**: 지역 계층(시/도 > 구/군 > 동) 기반의 아파트 정보 및 실거래 내역 수집

---

## 1단계: 웹사이트 기본 구조 분석 (서브에이전트 1)

### 핵심 특징

호갱노노는 대부분의 기능에 인증이 필요한 API를 제공합니다.

**주요 특징**:
1. **인증 필요**: 대부분의 API는 세션 쿠키 기반 인증이 필요
2. **JSON 기반 데이터**: 모든 응답은 JSON 형식으로 제공
3. **가격 데이터 단위**: 만원 단위로 저장됨 (예: 271000 = 2.71억)
4. **CORS 제한**: 외부 도메인에서의 직접 API 호출이 제한됨
5. **좌표 기반 조회**: 구글 맵 기반의 바운딩 박스 좌표 사용

### 발견된 주요 API 패턴

**지역 검색 API**:
- 검색 제안: `/api/v2/searches/suggestions/new?query=서초구&x=좌표&y=좌표`
- 검색 결과: `/api/v2/searches/new?query=서초구&x=좌표&y=좌표`

**아파트 목록 조회**:
```
GET /api/apt/bounding?
- map=google
- level=17 (줌 레벨: 13=구단위, 17=동단위)
- startX/endX, startY/endY (좌표 범위)
- tradeType=0 (0: 매매, 1: 전세, 2: 월세)
- areaFrom/areaTo (면적 범위)
- priceFrom/priceTo (가격 범위)
```

### 크롤링 시 고려사항

- **기본 좌표**: 서울 (37.5029854, 126.999697)
- **Rate Limiting**: 기본 5초 간격 권장, 429 에러 시 자동 지연 증가
- **파라미터 최적화**: `r` 파라미터(랜덤 값), `screenWidth/screenHeight` 필수

---

## 2단계: 시/도 목록 조회 API (서브에이전트 2)

### 지역 정보 API

호갱노노는 모든 시/도와 구/군 정보를 한 번에 제공하는 API를 운영합니다.

**API 엔드포인트**: `https://hogangnono.com/api/v2/regions`
**HTTP 메서드**: GET
**파라미터**:
- `regionCode` (선택): 특정 시/도 필터링

**요청 예시**:
```bash
# 전체 시/도 조회
curl -X GET "https://hogangnono.com/api/v2/regions"

# 특정 시/도만 조회
curl -X GET "https://hogangnono.com/api/v2/regions?regionCode=11"
```

**응답 구조**:
```json
{
  "data": {
    "regionList": [
      {
        "regionCode": "11",
        "name": "서울",
        "fullName": "서울특별시",
        "children": [
          {
            "regionCode": "11110",
            "name": "종로구",
            "fullName": "서울특별시 종로구"
          }
        ]
      }
    ]
  },
  "status": "success"
}
```

**전체 시/도 목록 (총 17개)**:
| 코드 | 시/도명 | 특이사항 |
|------|---------|----------|
| 11 | 서울 | 25개 구 |
| 26 | 부산 | 16개 구/군 |
| 28 | 인천 | 10개 구/군 |
| 27 | 대구 | 8개 구/군 |
| 30 | 대전 | 5개 구 |
| 29 | 광주 | 5개 구 |
| 31 | 울산 | 5개 구/군 |
| 36 | 세종특별자치시 | 하위 구/군 없음 |
| 41 | 경기도 | 44개 시/구/군 |
| 51 | 강원특별자치도 | 18개 시/군 |
| 43 | 충청북도 | 11개 시/군 |
| 44 | 충청남도 | 15개 시/군 |
| 52 | 전북특별자치도 | 15개 시/군 |
| 46 | 전라남도 | 22개 시/군 |
| 47 | 경상북도 | 24개 시/군 |
| 48 | 경상남도 | 18개 시/군 |
| 50 | 제주특별자치도 | 2개 시 |

---

## 3단계: 구/군 목록 조회 API (서브에이전트 3)

### 계층적 지역 정보

`/api/v2/regions` API는 시/도와 모든 하위 구/군 정보를 계층 구조로 제공합니다.

**지역 코드 체계**:
- 시/도 코드: 2자리 (예: 11=서울, 41=경기도)
- 구/군 코드: 5자리 (시/도 코드 + 3자리)
- 예시: 11110 = 11(서울) + 110(종로구)

**서울특별시 구 목록 (25개)**:
| regionCode | 구명 | fullName |
|------------|------|---------|
| 11110 | 종로구 | 서울특별시 종로구 |
| 11140 | 중구 | 서울특별시 중구 |
| 11170 | 용산구 | 서울특별시 용산구 |
| 11200 | 성동구 | 서울특별시 성동구 |
| 11215 | 광진구 | 서울특별시 광진구 |
| 11230 | 동대문구 | 서울특별시 동대문구 |
| 11260 | 중랑구 | 서울특별시 중랑구 |
| 11290 | 성북구 | 서울특별시 성북구 |
| 11305 | 강북구 | 서울특별시 강북구 |
| 11320 | 도봉구 | 서울특별시 도봉구 |
| 11350 | 노원구 | 서울특별시 노원구 |
| 11380 | 은평구 | 서울특별시 은평구 |
| 11410 | 서대문구 | 서울특별시 서대문구 |
| 11440 | 마포구 | 서울특별시 마포구 |
| 11470 | 양천구 | 서울특별시 양천구 |
| 11500 | 강서구 | 서울특별시 강서구 |
| 11530 | 구로구 | 서울특별시 구로구 |
| 11545 | 금천구 | 서울특별시 금천구 |
| 11560 | 영등포구 | 서울특별시 영등포구 |
| 11590 | 동작구 | 서울특별시 동작구 |
| 11620 | 관악구 | 서울특별시 관악구 |
| 11650 | 서초구 | 서울특별시 서초구 |
| 11680 | 강남구 | 서울특별시 강남구 |
| 11710 | 송파구 | 서울특별시 송파구 |
| 11740 | 강동구 | 서울특별시 강동구 |

---

## 4단계: 동 목록 조회 API

### 검색 기반 동 정보 조회

호갱노노는 별도의 동 목록 조회 API를 제공하지 않습니다. 대신 검색 API를 통해 각 동의 정보를 개별적으로 조회할 수 있습니다.

**API 엔드포인트**: `/api/v2/searches/new`
**사용 방법**: 특정 지역명 검색을 통해 동 정보 파악

**예시**: 강남구(11680)의 동 정보
- 총 18개의 행정동
- 동 코드 형식: 5자리 (11680xxx)
- 검색 API를 통해 동별 정보 획득 가능

---

## 5단계: 아파트 단지 정보 조회 API

### 좌표 기반 아파트 목록 조회

호갱노노는 구글 맵 기반의 바운딩 박스(Bounding Box) 좌표로 아파트 단지 목록을 조회합니다.

**API 엔드포인트**: `https://hogangnono.com/api/apt/bounding`
**HTTP 메서드**: GET

**주요 파라미터**:
| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|----------|------|------|------|------|
| map | string | O | 맵 종류 | "google" |
| level | int | O | 줌 레벨 (13: 구단위, 17: 동단위) | 13 |
| startX | float | O | 최소 경도 | 127.042 |
| endX | float | O | 최대 경도 | 127.074 |
| startY | float | O | 최소 위도 | 37.485 |
| endY | float | O | 최대 위도 | 37.525 |
| tradeType | int | X | 거래 유형 (0: 매매) | 0 |
| areaFrom | int | X | 최소 면적 | 0 |
| areaTo | int | X | 최대 면적 | 80 |
| priceFrom | int | X | 최소 가격(만원) | 0 |
| priceTo | int | X | 최대 가격(만원) | 401000 |

**요청 예시**:
```python
import requests

params = {
    "map": "google",
    "level": 13,
    "screenWidth": "1200",
    "screenHeight": "924",
    "startX": "127.042",
    "endX": "127.074",
    "startY": "37.485",
    "endY": "37.525",
    "tradeType": "0",
    "areaFrom": "0",
    "areaTo": "80",
    "priceFrom": "0",
    "priceTo": "401000"
}

response = requests.get("https://hogangnono.com/api/apt/bounding", params=params)
```

**응답 데이터 구조**:
```json
{
  "data": [
    {
      "aptHash": "1Hq6f",
      "aptName": "래미안 레미안",
      "address": "서울특별시 강남구 개포동",
      "lat": 37.5135,
      "lng": 127.0434,
      "buildYear": 2005,
      "household": 1012,
      "dong": "개포동"
    }
  ]
}
```

### 상세 필터링 파라미터
- `floorAreaRatioFrom/To`: 용적률 범위
- `buildingCoverageRatioFrom/To`: 건폐율 범위
- `householdFrom/To`: 세대수 범위
- `parking`: 주차장 필터
- `reconstructionStep`: 재건축 단계

---

## 6단계: 실거래 내역 조회 API

### 실거래 월간 리포트 API

호갱노노는 특정 아파트 단지의 실거래 내역을 월간 리포트 형태로 제공합니다.

**API 엔드포인트**:
- 최근 3년: `/api/v2/apts/{aptId}/monthly-reports?tradeType=0&areaNo=0`
- 전체 기간: `/api/v2/apts/{aptId}/monthly-reports/more?tradeType=0&areaNo=0`

**핵심 파라미터**:
- `aptId`: 아파트 단지 고유 ID (예: `1Hq6f`)
- `tradeType`: 거래 유형 (0: 매매, 1: 전세, 2: 월세)
- `areaNo`: 면적 번호 (0: 전체, 특정 면적 선택 가능)

**응답 구조**:
```json
{
  "data": {
    "shortTermReport": [
      {
        "date": "2025-01-31T15:00:00.000Z",
        "minPrice": 333000,
        "maxPrice": 346000,
        "averagePrice": 343000,
        "volume": 3,
        "rentVolume": 0,
        "offerVolume": 0,
        "trades": [
          {
            "id": 36780389,
            "price": 340000,
            "floor": 9,
            "category": 1,
            "day": 18,
            "isInChart": true,
            "isHighestPrice": true,
            "isPyHighestPrice": true
          }
        ]
      }
    ]
  }
}
```

### 실거래 데이터 필드 상세

| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| date | string | 거래일 (YYYY-MM-DD) | "2025-01-18" |
| minPrice | int | 최저 거래가 (만원) | 333000 |
| maxPrice | int | 최고 거래가 (만원) | 346000 |
| averagePrice | int | 평균 거래가 (만원) | 343000 |
| volume | int | 거래 건수 | 3 |
| floor | int | 층수 | 9 |
| area | float | 면적 (㎡) | 84.95 |
| isAuction | bool | 경매 여부 | false |
| isHighestPrice | bool | 최고가 여부 | true |

### 상세 실거래 정보 API

**엔드포인트**: `/api/v2/apts/{aptId}/item-report?tradeTypes=0&areaNo=0`

개별 거래 내역의 상세 정보를 제공하며, 동, 호수, 정확한 면적 등 추가 정보 포함.

---

## 7단계: 종합 크롤러 구현 가이드

### 전체 데이터 흐름

```
1. /api/v2/regions → 시/도, 구/군 목록 수집
   ↓
2. 구/군별 좌표 범위 계산
   ↓
3. /api/apt/bounding → 아파트 단지 정보 수집
   ↓
4. /api/v2/apts/{aptId}/monthly-reports → 실거래 내역 수집
```

### 파이썬 크롤러 구현 예시

```python
import requests
import time
import json
from typing import List, Dict, Optional

class HogangnonoCrawler:
    def __init__(self):
        self.base_url = "https://hogangnono.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ko-KR,ko;q=0.9'
        }

    def get_regions(self) -> List[Dict]:
        """모든 시/도와 구/군 정보 조회"""
        response = requests.get(
            f"{self.base_url}/api/v2/regions",
            headers=self.headers
        )
        return response.json()['data']['regionList']

    def get_apartments_in_district(self, region_code: str, level: int = 13) -> List[Dict]:
        """특정 구/군의 아파트 단지 정보 조회"""
        # 구/군별 대표 좌표 (미리 정의 필요)
        district_coords = {
            '11680': {  # 강남구
                'startX': 127.042,
                'endX': 127.074,
                'startY': 37.485,
                'endY': 37.525
            },
            # ... 다른 구/군 좌표
        }

        if region_code not in district_coords:
            raise ValueError(f"Unknown district code: {region_code}")

        coords = district_coords[region_code]
        params = {
            "map": "google",
            "level": level,
            "screenWidth": "1200",
            "screenHeight": "924",
            "startX": coords['startX'],
            "endX": coords['endX'],
            "startY": coords['startY'],
            "endY": coords['endY'],
            "tradeType": "0",
            "areaFrom": "0",
            "areaTo": "80",
            "priceFrom": "0",
            "priceTo": "401000"
        }

        response = requests.get(
            f"{self.base_url}/api/apt/bounding",
            params=params,
            headers=self.headers
        )

        return response.json()['data']

    def get_real_transactions(self, apt_id: str, trade_type: int = 0, area_no: int = 0) -> Dict:
        """특정 아파트의 실거래 내역 조회"""
        url = f"{self.base_url}/api/v2/apts/{apt_id}/monthly-reports"
        params = {
            "tradeType": trade_type,
            "areaNo": area_no
        }

        response = requests.get(
            url,
            params=params,
            headers=self.headers
        )

        return response.json()['data']

    def get_all_transactions(self, apt_id: str, trade_type: int = 0, area_no: int = 0) -> Dict:
        """특정 아파트의 전체 기간 실거래 내역 조회"""
        url = f"{self.base_url}/api/v2/apts/{apt_id}/monthly-reports/more"
        params = {
            "tradeType": trade_type,
            "areaNo": area_no
        }

        response = requests.get(
            url,
            params=params,
            headers=self.headers
        )

        return response.json()['data']

    def collect_all_data(self, target_districts: List[str]):
        """전체 데이터 수집 프로세스"""
        # 1. 지역 정보 수집
        regions = self.get_regions()

        # 2. 목표 구/군의 아파트 단지 수집
        all_apartments = []
        for district_code in target_districts:
            apartments = self.get_apartments_in_district(district_code)
            all_apartments.extend(apartments)
            time.sleep(2)  # Rate limiting

            print(f"{district_code}: {len(apartments)}개 단지 수집 완료")

        # 3. 각 아파트의 실거래 내역 수집
        results = []
        for apt in all_apartments:
            apt_id = apt.get('aptHash')
            if not apt_id:
                continue

            try:
                transactions = self.get_all_transactions(apt_id)
                result = {
                    'apt_info': apt,
                    'transactions': transactions
                }
                results.append(result)
                time.sleep(1)  # Rate limiting

            except Exception as e:
                print(f"Error fetching transactions for {apt_id}: {e}")
                continue

        return results

# 사용 예시
crawler = HogangnonoCrawler()

# 서울 주요 구의 아파트 데이터 수집
target_districts = ['11680', '11650', '11710']  # 강남구, 서초구, 송파구
data = crawler.collect_all_data(target_districts)

# 결과 저장
with open('hogangnono_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

### Rate Limiting 정책

| 구분 | 권장 간격 | 최대 요청량 | 주의사항 |
|------|-----------|------------|----------|
| regions API | 5초 | 제한 없음 | 1회 호출만 필요 |
| bounding API | 2-3초 | 분당 20회 | 좌표별 호출 |
| transactions API | 1-2초 | 분당 30회 | aptId별 호출 |
| 전체 프로세스 | - | 시간당 500건 | 안정적 수집 |

### 에러 처리 및 재시도 전략

```python
import time
from functools import wraps

def retry_with_backoff(max_retries=3, initial_delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    last_exception = e
                    if attempt == max_retries - 1:
                        raise e

                    print(f"Attempt {attempt + 1} failed. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff

            raise last_exception
        return wrapper
    return decorator

# 적용 예시
@retry_with_backoff(max_retries=3)
def get_api_with_retry(self, url, params):
    response = requests.get(url, params=params, headers=self.headers)
    response.raise_for_status()
    return response.json()
```

---

## 8단계: 활용 방안 및 확장 전략

### 데이터 활용 예시

1. **지역별 평균 가격 분석**
   ```python
   def analyze_price_by_district(data):
       district_prices = {}

       for item in data:
           district = item['apt_info'].get('district')
           transactions = item['transactions'].get('shortTermReport', [])

           for month_data in transactions:
               avg_price = month_data.get('averagePrice', 0)
               if district not in district_prices:
                   district_prices[district] = []
               district_prices[district].append(avg_price)

       # 지역별 평균 계산
       for district in district_prices:
           prices = [p for p in district_prices[district] if p > 0]
           district_prices[district] = sum(prices) / len(prices) if prices else 0

       return district_prices
   ```

2. **시계열 가격 추이 분석**
   - 월별/분기별 가격 변화 추적
   - 특정 지역의 가격 상승률 계산
   - 계절별 가격 패턴 분석

3. **아파트 규모별 가격 비교**
   - 전용면적별 평균 가격
   - 세대수별 가격 차이
   - 건축년도별 가격 분석

### 확장 전략

1. **병렬 처리**
   - asyncio/aiohttp를 사용한 비동기 처리
   - 멀티프로세싱을 통한 대용량 데이터 수집

2. **캐싱 전략**
   - 이미 수집된 데이터는 로컬에 저장
   - 증분 데이터만 업데이트

3. **모니터링 및 알림**
   - 가격 변동 알림 시스템
   - 신규 매물 알림

---

## 결론 및 제언

### 주요 발견사항

1. **완전한 API 지원**: 호갱노노는 지역 정보부터 실거래 내역까지 완벽한 API를 제공
2. **체계적인 데이터 구조**: 시/도 > 구/군 > 동 > 단지 > 실거래 내역의 계층 구조
3. **유연한 필터링**: 가격, 면적, 기간 등 다양한 필터링 옵션 제공
4. **실시간 데이터**: 최신 거래 내역을 신속하게 제공

### 크롤링 권장 전략

1. **순차적 접근**: 지역 → 단지 → 실거래 내역 순서로 접근
2. **적절한 Rate Limiting**: 1-2초 간격의 요청으로 서버 부하 최소화
3. **체크포인트 관리**: 중단 지점부터 재시작할 수 있는 상태 관리
4. **데이터 검증**: 수집된 데이터의 정확성 검증 프로세스 포함

### 기대 효과

본 보고서의 API 분석과 크롤러 가이드를 통해 다음과 같은 효과를 기대할 수 있습니다:

- 정확하고 최신의 부동산 데이터 수집
- 효율적인 데이터 파이프라인 구축
- 지역별 시장 동향 분석
- 투자 결정을 위한 데이터 기반 인사이트 확보

---

*본 보고서는 2025-01-09 기준의 분석 결과이며, API는 언제든 변경될 수 있으니 지속적인 모니터링이 필요합니다.*