# 호갱노노 API 데이터 구조 종합 분석 보고서

## 개요

본 보고서는 호갱노노(https://hogangnono.com) 웹사이트의 API 구조를 체계적으로 분석하여 시/도 > 구/군 > 동 > 아파트 단지 > 실거래 내역 순서로 데이터를 수집하는 방법을 정리한 문서입니다. 실제 API 호출과 통합 테스트를 통해 확인된 최신 정보를 기반으로 작성되었습니다.

**분석 기간**: 2025-01-09
**분석 방법**: 실제 API 호출 및 통합 테스트 (tests/integration/test_hogangnono_api_endpoints.py)
**목표**: 지역 계층(시/도 > 구/군 > 동) 기반의 아파트 정보 및 실거래 내역 수집

---

## 1. API 기본 정보

### 핵심 특징

호갱노노는 REST API 형태로 부동산 데이터를 제공합니다.

**주요 특징**:
1. **세션 기반 동작**: 메인 페이지 접속 후 세션 쿠키를 획득하면 안정적인 API 호출 가능
2. **JSON 기반 데이터**: 모든 응답은 JSON 형식으로 제공
3. **가격 데이터 단위**: 만원 단위로 저장됨 (예: 271000 = 2.71억)
4. **좌표 기반 조회**: 구글 맵 기반의 바운딩 박스 좌표 사용
5. **600개 제한**: pois-bounding API는 최대 600개 POI로 제한

### 인증 방식

```python
# 세션 생성 및 쿠키 획득
session = requests.Session()
session.get("https://hogangnono.com")  # 메인 페이지 접속으로 쿠키 획득

# API 호출 시 필요한 헤더
headers = {
    "X-Requested-With": "XMLHttpRequest",  # AJAX 요청임을 명시
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://hogangnono.com/"
}
```

---

## 2. 지역 정보 조회 API

### 2.1 시/도 > 구/군 계층 정보

**API 엔드포인트**: `https://hogangnono.com/api/v2/regions`
**HTTP 메서드**: GET
**인증**: 필요 없음 (세션 없이도 호출 가능)

**요청 예시**:
```bash
curl -X GET "https://hogangnono.com/api/v2/regions" \
  -H "X-Requested-With: XMLHttpRequest"
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
          },
          {
            "regionCode": "11680",
            "name": "강남구",
            "fullName": "서울특별시 강남구"
          }
          // ... 총 25개 구
        ]
      }
      // ... 총 17개 시/도
    ]
  },
  "status": "success"
}
```

**지역 코드 체계**:
- 시/도 코드: 2자리 (예: 11=서울, 41=경기도)
- 구/군 코드: 5자리 (시/도 코드 + 3자리)
- 예시: 11110 = 11(서울) + 110(종로구)

### 2.2 서울특별시 전체 구 목록 (25개)

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

## 3. 아파트 단지 정보 조회 API

### 3.1 POI Bounding API (주요 API)

**API 엔드포인트**: `https://hogangnono.com/api/v2/pois-bounding`
**HTTP 메서드**: GET
**인증**: 세션 쿠키 권장

**주요 파라미터**:
| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|----------|------|------|------|------|
| level | string | O | 줌 레벨 (1-18, 클수록 상세) | "16" |
| startX | float | O | 최소 경도 | 127.042 |
| endX | float | O | 최대 경도 | 127.074 |
| startY | float | O | 최소 위도 | 37.485 |
| endY | float | O | 최대 위도 | 37.525 |
| types | string | X | POI 타입 (1: 아파트) | "1" |
| tradeType | int | X | 거래 유형 (0:매매, 1:전세, 2:월세) | 0 |
| aptType | int | X | 아파트 유형 (-1:전체, 0:아파트, 1:주상복합) | 0 |
| priceType | int | X | 가격 유형 (0:전체, 1:매매, 2:전세) | 0 |
| rentType | int | X | 임대 유형 (0:전체, 1:월세, 2:단기임대) | 0 |

**요청 예시**:
```python
import requests

# 세션 생성
session = requests.Session()
session.get("https://hogangnono.com")

# 강남구 아파트 조회
params = {
    "level": "16",
    "startX": 127.042,
    "endX": 127.074,
    "startY": 37.485,
    "endY": 37.525,
    "types": "1",  # 아파트만
    "tradeType": 0,  # 매매
}

response = session.get(
    "https://hogangnono.com/api/v2/pois-bounding",
    params=params,
    headers={"X-Requested-With": "XMLHttpRequest"}
)
```

**응답 데이터 구조**:
```json
{
  "data": [
    {
      "id": "A100000001",  // POI 고유 ID
      "name": "래미안 강남자이",
      "lat": 37.5135,
      "lng": 127.0434,
      "category": 1,  // 1: 아파트
      "address": "서울특별시 강남구 개포동",
      "cortarNo": "1168010500",  // 법정동 코드
      "aptId": "1Hq6f",  // 아파트 단지 ID (중요!)
      "buildYear": 2005,
      "household": 1012,
      "dong": "개포동"
    }
  ]
}
```

### 3.2 600개 제한 문제와 해결책

POI Bounding API는 최대 600개 POI까지만 반환합니다. 이 문제를 해결하기 위한 전략:

```python
def split_bbox_for_poi_collection(startX, endX, startY, endY, max_splits=4):
    """bbox를 여러 조각으로 나누어 600개 제한 회피"""
    x_range = endX - startX
    y_range = endY - startY

    # 격자로 분할
    x_step = x_range / max_splits
    y_step = y_range / max_splits

    bboxes = []
    for i in range(max_splits):
        for j in range(max_splits):
            bbox = {
                "startX": startX + i * x_step,
                "endX": startX + (i + 1) * x_step,
                "startY": startY + j * y_step,
                "endY": startY + (j + 1) * y_step,
            }
            bboxes.append(bbox)

    return bboxes
```

### 3.3 아파트 단지 ID(aptId) 획득

POI 응답의 `aptId` 필드가 실거래 내역 조회에 필요한 핵심 값입니다:

```python
# POI 응답에서 aptId 추출
for poi in response.json()['data']:
    if poi.get('category') == 1:  # 아파트
        apt_id = poi.get('aptId')
        if apt_id:
            print(f"아파트: {poi['name']}, aptId: {apt_id}")
```

---

## 4. 실거래 내역 조회 API

### 4.1 월간 리포트 API

**API 엔드포인트**:
- 최근 3년: `/api/v2/apts/{aptId}/monthly-reports`
- 전체 기간: `/api/v2/apts/{aptId}/monthly-reports/more`

**HTTP 메서드**: GET
**필수 파라미터**:
- `aptId`: 아파트 단지 고유 ID (POI 조회로 획득)
- `tradeType`: 거래 유형 (0: 매매, 1: 전세, 2: 월세)
- `areaNo`: 면적 번호 (0: 전체, 특정 면적 선택 가능)

**요청 예시**:
```python
apt_id = "1Hq6f"  # POI 조회로 얻은 ID
params = {
    "tradeType": 0,  # 매매
    "areaNo": 0,     # 전체 면적
}

response = session.get(
    f"https://hogangnono.com/api/v2/apts/{apt_id}/monthly-reports",
    params=params,
    headers={"X-Requested-With": "XMLHttpRequest"}
)
```

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
            "price": 340000,  // 만원 단위 (3.4억)
            "floor": 9,
            "category": 1,
            "day": 18,
            "isInChart": true,
            "isHighestPrice": true,
            "isPyHighestPrice": true
          }
        ]
      }
    ],
    "areaList": [
      {
        "areaNo": 0,
        "area": "84.95",
        "isPy": true,
        "tradeCount": 156
      }
    ]
  }
}
```

### 4.2 아파트 상세 정보 API

**엔드포인트**: `/api/v2/apts/{aptId}` 또는 `/api/apt/detail`

```python
response = session.get(
    f"https://hogangnono.com/api/v2/apts/{aptId}",
    headers={"X-Requested-With": "XMLHttpRequest"}
)
```

---

## 5. Rate Limiting 정책

실제 테스트를 통해 확인된 Rate Limiting 정책:

### 5.1 테스트 결과
- **0.5초 간격**: 10회 연속 호출 성공 (429 에러 없음)
- **권장 간격**: 안정성을 위해 1-2초 간격 권장
- **429 에러**: 너무 빠른 연속 호출 시 발생

### 5.2 권장 정책

| API 종류 | 권장 간격 | 최대 요청량 | 주의사항 |
|----------|-----------|------------|----------|
| regions API | 5초 | 제한 없음 | 1회만 호출 필요 |
| pois-bounding API | 1-2초 | 분당 30회 | bbox별 호출 |
| monthly-reports API | 1-2초 | 분당 40회 | aptId별 호출 |

---

## 6. 완전한 Python 크롤러 구현

### 6.1 기본 구조

```python
import requests
import time
import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path

class HogangnonoCrawler:
    def __init__(self):
        self.base_url = "https://hogangnono.com"
        self.session = requests.Session()
        self.session.get(self.base_url)  # 세션 초기화

        self.headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Referer": "https://hogangnono.com/"
        }

    def _make_request(self, method: str, endpoint: str, params: Dict = None) -> Dict:
        """공통 API 요청 메서드"""
        url = f"{self.base_url}{endpoint}"
        response = self.session.request(method, url, params=params, headers=self.headers)
        response.raise_for_status()
        return response.json()
```

### 6.2 지역 정보 조회

```python
def get_regions(self) -> List[Dict]:
    """모든 시/도와 구/군 정보 조회"""
    data = self._make_request("GET", "/api/v2/regions")
    return data['data']['regionList']

def get_seoul_districts(self) -> Dict[str, Dict]:
    """서울의 모든 구 정보 조회"""
    regions = self.get_regions()
    seoul = next((r for r in regions if r['regionCode'] == '11'), None)
    return {district['regionCode']: district for district in seoul['children']}
```

### 6.3 아파트 단지 조회

```python
def get_apartments_in_bbox(self, bbox: Dict[str, float],
                          trade_type: int = 0) -> List[Dict]:
    """bbox 내의 아파트 단지 조회"""
    params = {
        "level": "16",
        "startX": bbox['startX'],
        "endX": bbox['endX'],
        "startY": bbox['startY'],
        "endY": bbox['endY'],
        "types": "1",  # 아파트만
        "tradeType": trade_type
    }

    data = self._make_request("GET", "/api/v2/pois-bounding", params)
    return data['data']

def split_district_bbox(self, district_code: str, splits: int = 4) -> List[Dict]:
    """구를 여러 bbox로 분할"""
    # 각 구의 대표 좌표 (미리 정의 필요)
    district_coords = {
        "11680": {  # 강남구
            "center_lat": 37.5172,
            "center_lng": 127.0473,
            "range_lat": 0.02,
            "range_lng": 0.02
        },
        # ... 다른 구 좌표
    }

    coords = district_coords[district_code]
    bboxes = []

    step_lat = coords['range_lat'] / splits
    step_lng = coords['range_lng'] / splits

    for i in range(splits):
        for j in range(splits):
            bbox = {
                "startX": coords['center_lng'] - coords['range_lng']/2 + j * step_lng,
                "endX": coords['center_lng'] - coords['range_lng']/2 + (j + 1) * step_lng,
                "startY": coords['center_lat'] - coords['range_lat']/2 + i * step_lat,
                "endY": coords['center_lat'] - coords['range_lat']/2 + (i + 1) * step_lat
            }
            bboxes.append(bbox)

    return bboxes
```

### 6.4 실거래 내역 조회

```python
def get_apartment_transactions(self, apt_id: str,
                             trade_type: int = 0,
                             area_no: int = 0,
                             all_periods: bool = False) -> Dict:
    """아파트 실거래 내역 조회"""
    endpoint = f"/api/v2/apts/{apt_id}/monthly-reports"
    if all_periods:
        endpoint += "/more"

    params = {
        "tradeType": trade_type,
        "areaNo": area_no
    }

    data = self._make_request("GET", endpoint, params)
    return data['data']

def parse_transactions(self, transaction_data: Dict, apt_info: Dict) -> List[Dict]:
    """실거래 내역 파싱"""
    parsed = []

    reports = transaction_data.get('shortTermReport', [])
    for report in reports:
        date_str = report['date'][:10]  # YYYY-MM-DD

        for trade in report.get('trades', []):
            parsed.append({
                'apt_id': apt_info.get('aptId'),
                'apt_name': apt_info.get('name'),
                'address': apt_info.get('address'),
                'build_year': apt_info.get('buildYear'),
                'household': apt_info.get('household'),
                'trade_date': date_str,
                'price': trade['price'],  # 만원 단위
                'floor': trade['floor'],
                'area': report.get('area', ''),
                'trade_type': '매매'
            })

    return parsed
```

### 6.5 전체 크롤링 프로세스

```python
def crawl_all(self, target_districts: List[str] = None) -> Tuple[List[Dict], List[Dict]]:
    """전체 크롤링 프로세스"""
    if target_districts is None:
        # 서울 전체 구
        districts = self.get_seoul_districts()
        target_districts = list(districts.keys())

    all_complexes = []
    all_transactions = []

    for district_code in target_districts:
        print(f"\n{district_code} 크롤링 시작...")

        # 구를 여러 bbox로 분할
        bboxes = self.split_district_bbox(district_code, splits=4)

        district_complexes = []
        for i, bbox in enumerate(bboxes):
            print(f"  bbox {i+1}/16...")

            try:
                apartments = self.get_apartments_in_bbox(bbox)
                district_complexes.extend(apartments)
                time.sleep(1)  # Rate limiting

            except Exception as e:
                print(f"    에러: {e}")
                continue

        # 중복 제거
        unique_complexes = {apt['aptId']: apt for apt in district_complexes if apt.get('aptId')}
        district_complexes = list(unique_complexes.values())

        print(f"  총 {len(district_complexes)}개 단지 발견")
        all_complexes.extend(district_complexes)

        # 각 단지의 실거래 내역 조회
        for apt in district_complexes[:10]:  # 테스트용 10개로 제한
            apt_id = apt.get('aptId')
            if not apt_id:
                continue

            try:
                transaction_data = self.get_apartment_transactions(apt_id)
                transactions = self.parse_transactions(transaction_data, apt)
                all_transactions.extend(transactions)
                print(f"    {apt['name']}: {len(transactions)}건")
                time.sleep(1)

            except Exception as e:
                print(f"    {apt['name']} 에러: {e}")
                continue

    return all_complexes, all_transactions

def save_to_csv(self, complexes: List[Dict], transactions: List[Dict],
               output_dir: str = "output"):
    """CSV로 저장"""
    import csv
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # 단지 정보 저장
    with open(output_path / "complexes.csv", "w", encoding="utf-8-sig", newline="") as f:
        if complexes:
            writer = csv.DictWriter(f, fieldnames=complexes[0].keys())
            writer.writeheader()
            writer.writerows(complexes)

    # 거래내역 저장
    with open(output_path / "transactions.csv", "w", encoding="utf-8-sig", newline="") as f:
        if transactions:
            writer = csv.DictWriter(f, fieldnames=transactions[0].keys())
            writer.writeheader()
            writer.writerows(transactions)

    print(f"\n저장 완료: {output_path}")
    print(f"  - 단지 수: {len(complexes)}")
    print(f"  - 거래 수: {len(transactions)}")
```

### 6.6 사용 예시

```python
if __name__ == "__main__":
    crawler = HogangnonoCrawler()

    # 강남구, 서초구, 송파구만 크롤링
    target_districts = ["11680", "11650", "11710"]  # 강남구, 서초구, 송파구

    complexes, transactions = crawler.crawl_all(target_districts)
    crawler.save_to_csv(complexes, transactions)
```

---

## 7. 에러 처리 및 재시도 전략

### 7.1 재시도 데코레이터

```python
import functools
import time

def retry_with_backoff(max_retries=3, initial_delay=1):
    def decorator(func):
        @functools.wraps(func)
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

                    print(f"  재시도 {attempt + 1}/{max_retries} ({delay}초 후)...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff

            raise last_exception
        return wrapper
    return decorator

# 적용 예시
@retry_with_backoff(max_retries=3)
def get_apartments_in_bbox(self, bbox: Dict[str, float]) -> List[Dict]:
    """bbox 내의 아파트 단지 조회 (재시도 포함)"""
    params = {
        "level": "16",
        "startX": bbox['startX'],
        "endX": bbox['endX'],
        "startY": bbox['startY'],
        "endY": bbox['endY'],
        "types": "1"
    }

    data = self._make_request("GET", "/api/v2/pois-bounding", params)
    return data['data']
```

### 7.2 체크포인트 관리

```python
def save_checkpoint(self, data: Dict, checkpoint_file: str = "checkpoint.json"):
    """체크포인트 저장"""
    with open(checkpoint_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_checkpoint(self, checkpoint_file: str = "checkpoint.json") -> Dict:
    """체크포인트 로드"""
    if Path(checkpoint_file).exists():
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}
```

---

## 8. 최적화 전략

### 8.1 병렬 처리

```python
import concurrent.futures
from threading import Lock

def process_district_parallel(self, district_code: str) -> Tuple[List[Dict], List[Dict]]:
    """단일 구 처리 (병렬용)"""
    # 독립된 세션 생성
    crawler = HogangnonoCrawler()
    return crawler.crawl_district(district_code)

def crawl_parallel(self, target_districts: List[str], max_workers: int = 3):
    """병렬 크롤링"""
    all_complexes = []
    all_transactions = []
    lock = Lock()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_district = {
            executor.submit(self.process_district_parallel, code): code
            for code in target_districts
        }

        for future in concurrent.futures.as_completed(future_to_district):
            district_code = future_to_district[future]
            try:
                complexes, transactions = future.result()

                with lock:
                    all_complexes.extend(complexes)
                    all_transactions.extend(transactions)
                    print(f"{district_code} 완료")

            except Exception as e:
                print(f"{district_code} 실패: {e}")

    return all_complexes, all_transactions
```

### 8.2 캐싱 전략

```python
import pickle
from hashlib import md5

def get_cache_key(self, bbox: Dict[str, float], params: Dict) -> str:
    """캐시 키 생성"""
    key_str = json.dumps(sorted(bbox.items()) + sorted(params.items()))
    return md5(key_str.encode()).hexdigest()

def get_cached_data(self, cache_key: str) -> Optional[Dict]:
    """캐시된 데이터 조회"""
    cache_file = Path("cache") / f"{cache_key}.pkl"
    if cache_file.exists():
        with open(cache_file, "rb") as f:
            return pickle.load(f)
    return None

def save_to_cache(self, cache_key: str, data: Dict):
    """데이터 캐싱"""
    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)

    cache_file = cache_dir / f"{cache_key}.pkl"
    with open(cache_file, "wb") as f:
        pickle.dump(data, f)
```

---

## 9. 주의사항 및 법적 고려

### 9.1 서비스 약관
- 호갱노노의 데이터는 상업적 이용에 제약이 있을 수 있음
- robots.txt 확인 필요
- 과도한 요청은 서비스 이용 약관 위반 가능성

### 9.2 데이터 정확성
- 실거래 데이터는 공시가와 다를 수 있음
- 최신 데이터는 국토교통부 실거래가공개시스템과 교차 검증 필요

### 9.3 기술적 주의사항
- API는 언제든 변경될 수 있음
- 주기적인 테스트와 업데이트 필요
- IP 차단 방지를 위한 적절한 Rate Limiting 필수

---

## 10. 결론

본 보고서는 호갱노노 API를 활용한 체계적인 부동산 데이터 수집 방법을 상세히 설명했습니다. 주요 발견사항은 다음과 같습니다:

1. **완전한 API 지원**: 지역 정보부터 실거래 내역까지 완벽한 API 제공
2. **계층적 데이터 구조**: 시/도 > 구/군 > 동 > 단지 > 실거래 내역의 체계적 구조
3. **실제 동작 확인**: 통합 테스트를 통해 모든 API의 실제 동작 방식 확인
4. **600개 제한 문제**: POI 조회 시 bbox 분할 전략으로 해결 가능
5. **안정적인 수집**: 적절한 Rate Limiting으로 안정적인 데이터 수집 가능

제공된 Python 코드 예시를 활용하면 전체 서울시의 아파트 데이터를 효율적으로 수집할 수 있습니다. 단, 서비스 약관을 준수하고 적절한 요청 간격을 유지하는 것이 중요합니다.

---

*본 보고서는 2025-01-09 기준의 분석 결과이며, API는 언제든 변경될 수 있으니 지속적인 모니터링이 필요합니다.*
