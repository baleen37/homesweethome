# 호갱노노 API 가이드

## 목차

1. [개요](#개요)
2. [핵심 API 엔드포인트](#핵심-api-엔드포인트)
3. [데이터 흐름](#데이터-흐름)
4. [API 상세 명세](#api-상세-명세)
5. [지역 코드 체계](#지역-코드-체계)
6. [크롤링 전략](#크롤링-전략)
7. [주의사항](#주의사항)

## 개요

호갱노노(https://hogangnono.com) 부동산 정보 플랫폼 API 명세입니다.

- **기본 URL**: `https://hogangnono.com`
- **API 버전**: v2
- **인증**: 세션 및 쿠키 기반
- **Rate Limiting**: 1-2초 간격 권장

## 데이터 흐름

호갱노노의 데이터는 **시 > 구 > 동 > 아파트 단지 > 실거래 내역**의 5단계 계층 구조로 되어 있습니다.

```
1. 시/도 목록 조회 (/api/v2/regions)
   ↓
2. 구/군 정보 획득 (서울 25개 구)
   ↓
3. Bounding Box 분할 (600개 제한 회피)
   ↓
4. 아파트 단지 목록 수집 (/api/v2/pois-bounding)
   ↓
5. 실거래 내역 조회 (/api/v2/apts/{aptId}/monthly-reports)
```

## 핵심 API 엔드포인트

### 1. 지역 정보 API

```http
GET /api/v2/regions
Headers: {"X-Requested-With": "XMLHttpRequest"}
```

### 2. 아파트 단지 조회 API

```http
GET /api/v2/pois-bounding
Parameters:
- level: 16 (줌 레벨, 1-18)
- startX/endX: 경도 범위 (필수)
- startY/endY: 위도 범위 (필수)
- aptType: -1 (전체), 0(아파트), 1(주상복합), 2(오피스텔)
- tradeType: 0 (0=매매, 1=전세, 2=월세)
- priceType: 0 (0=전체, 1=매매, 2=전세)
- rentType: 0 (0=전체, 1=월세, 2=단기임대)
- screenWidth: 1200 (화면 너비)
- screenHeight: 924 (화면 높이)
- map: "google" (지도 종류)
```

### 3. 실거래 내역 API

```http
GET /api/v2/apts/{aptId}/monthly-reports
Parameters:
- tradeType: 0 (0=매매, 1=전세, 2=월세)
- areaNo: 0 (0=전체)
```

```http
GET /api/v2/apts/{aptId}/monthly-reports/more
Parameters: 위와 동일
```

## 지역 코드 체계

- **시/도 코드**: 2자리 (예: 11=서울, 41=경기도)
- **구/군 코드**: 5자리 = 시/도 코드 + 3자리 (예: 11680=서울+강남구)
- **법정동 코드**: cortarNo (예: 1168010500=서울+강남구+개포동)

### 서울시 구 코드 목록

| 코드 | 구명 | 코드 | 구명 |
|------|------|------|------|
| 11110 | 종로구 | 11500 | 강서구 |
| 11140 | 중구 | 11530 | 구로구 |
| 11170 | 용산구 | 11545 | 금천구 |
| 11200 | 성동구 | 11560 | 영등포구 |
| 11215 | 광진구 | 11590 | 동작구 |
| 11230 | 동대문구 | 11620 | 관악구 |
| 11260 | 중랑구 | 11650 | 서초구 |
| 11290 | 성북구 | 11680 | 강남구 |
| 11305 | 강북구 | 11710 | 송파구 |
| 11320 | 도봉구 | 11740 | 강동구 |
| 11350 | 노원구 | | |
| 11380 | 은평구 | | |
| 11410 | 서대문구 | | |
| 11440 | 마포구 | | |
| 11470 | 양천구 | | |

## 크롤링 전략

### 1. 600개 제한 해결책

호갱노노 API는 한 번의 요청으로 최대 600개의 POI를 반환합니다. 이 제한을 피하기 위해 구 영역을 여러 개의 작은 bbox로 분할해야 합니다.

#### Bbox 분할 알고리즘

```python
def split_bbox(bbox, max_items=600, estimated_density=0.001):
    """
    bbox를 동적으로 분할하여 600개 제한 회피

    Args:
        bbox: (min_lng, min_lat, max_lng, max_lat)
        max_items: API당 최대 항목 수 (600)
        estimated_density: km²당 아파트 밀도 (서울: 약 0.001)

    Returns:
        List of bbox tuples
    """
    import math

    # bbox 면적 계산 (대략적)
    lat_diff = bbox[3] - bbox[1]
    lng_diff = bbox[2] - bbox[0]
    area_km2 = lat_diff * lng_diff * 111 * 111  # 1도 ≈ 111km

    # 예상 아파트 수
    estimated_apts = area_km2 / estimated_density

    # 필요한 분할 수 계산
    splits_needed = math.ceil(estimated_apts / max_items)
    grid_size = math.ceil(math.sqrt(splits_needed))

    # 격자로 분할
    lat_step = lat_diff / grid_size
    lng_step = lng_diff / grid_size

    bboxes = []
    for i in range(grid_size):
        for j in range(grid_size):
            sub_bbox = (
                bbox[0] + j * lng_step,
                bbox[1] + i * lat_step,
                bbox[0] + (j + 1) * lng_step,
                bbox[1] + (i + 1) * lat_step
            )
            bboxes.append(sub_bbox)

    return bboxes

# 사용 예시
seoul_bbox = (126.734086, 37.413294, 127.183394, 37.715133)
bboxes = split_bbox(seoul_bbox, max_items=600)
print(f"서울시를 {len(bboxes)}개 bbox로 분할")
```

### 2. Rate Limiting 정책

- **권장 간격**: 1-2초
- **테스트 결과**: 0.5초 간격으로 10회 연속 호출 성공
- **429 에러**: 너무 빠른 연속 호출 시 발생
- **AdaptiveRateLimiter**: 성공 시 감소, 429 에러 시 2배 증가

### 3. 세션 관리

```python
# 메인 페이지 접속으로 쿠키 획득
session = requests.Session()
session.get("https://hogangnono.com")

# 이후 API 호출 시 자동으로 쿠키 포함
headers = {
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://hogangnono.com/"
}
```

## 실제 사용 시나리오

### 1. 전체 서울시 데이터 수집

```python
from crawler.crawlers.hogangnono import HogangnonoCrawler
from crawler.config import CrawlerConfig
import json

# 설정 초기화
config = CrawlerConfig()

# 크롤러 생성 (출력 디렉토리 지정)
crawler = HogangnonoCrawler(
    config=config,
    output_dir="./output/seoul_data"
)

# 전체 크롤링 실행
stats = crawler.crawl(
    regions=["11"],  # 서울시 코드
    full_period=False  # 최근 3년만 수집
)

print(f"크롤링 완료: {stats['dongs_processed']}/{stats['total_dongs']}개 동 처리")
print(f"소요 시간: {stats['duration_seconds']:.2f}초")
```

### 2. 특정 구만 수집 (배치 처리)

```python
# 수집할 구 목록
target_districts = ["11680", "11650", "11710"]  # 강남구, 서초구, 송파구

# 병렬 처리를 위한 Threading 사용
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

def crawl_district(district_code):
    """단일 구 크롤링 함수"""
    config = CrawlerConfig()
    crawler = HogangnonoCrawler(
        config=config,
        output_dir=f"./output/district_{district_code}"
    )

    return crawler.crawl(districts=[district_code])

# ThreadPoolExecutor를 사용한 병렬 처리
with ThreadPoolExecutor(max_workers=3) as executor:
    # 각 구에 대한 작업 제출
    future_to_district = {
        executor.submit(crawl_district, code): code
        for code in target_districts
    }

    # 완료된 작업 결과 수집
    for future in as_completed(future_to_district):
        district_code = future_to_district[future]
        try:
            stats = future.result()
            print(f"구 {district_code} 크롤링 완료: {stats}")
        except Exception as e:
            print(f"구 {district_code} 크롤링 실패: {e}")
```

### 3. 특정 아파트 단지의 상세 정보 수집

```python
from crawler.api.hogangnono_client import HogangnonoAPIClient
from crawler.data_mappers import HogangnonoDataMapper

config = CrawlerConfig()
data_mapper = HogangnonoDataMapper()

with HogangnonoAPIClient(config) as client:
    # 1. 먼저 POI 바운딩 API로 aptHash 획득
    search_params = SearchParams(
        bbox=(127.043, 37.513, 127.044, 37.514),  # 아파트 위치 근처
        level=16,
        tradeType=0,
        aptType=0
    )

    pois_response = client.get_apartments_bounding(search_params)
    apt_hash = None

    if pois_response.success and pois_response.data:
        # 목록에서 원하는 아파트 찾기
        for poi in pois_response.data:
            if "래미안 강남자이" in poi.get('name', ''):
                apt_hash = poi.get('aptHash')
                break

    if apt_hash:
        # 2. 실거래 내역 조회
        transactions_response = client.get_apartment_transactions(
            apt_hash=apt_hash,
            trade_type=0,  # 매매
            full_period=True  # 전체 기간
        )

        if transactions_response.success:
            # 응답 데이터 구조 처리
            transactions = []
            if isinstance(transactions_response.data, dict):
                transactions = transactions_response.data.get("shortTermReport", [])
            else:
                transactions = transactions_response.data if transactions_response.data else []

            print(f"총 {len(transactions)}개 거래내역 존재")

            # 최근 거래 내역 출력
            for transaction in transactions[-5:]:  # 최근 5개
                if isinstance(transaction, dict):
                    trade_date = transaction.get('date', '')[:10]
                    volume = transaction.get('volume', 0)
                    print(f"{trade_date}: {volume}건")
```

### 4. 동적 검색 (사용자 입력 기반)

```python
def search_apartments_by_name(apartment_name: str, limit: int = 10):
    """아파트 이름으로 검색"""
    config = CrawlerConfig()

    with HogangnonoAPIClient(config) as client:
        # 아파트 이름으로 검색
        search_response = client.search_apartments(
            query=apartment_name,
            limit=limit
        )

        if search_response.success and search_response.data:
            results = search_response.data.get("results", [])

            print(f"'{apartment_name}' 검색 결과 ({len(results)}건):")
            for apt in results:
                print(f"- {apt.get('name')} ({apt.get('address')})")

                # aptHash 정보 확인 (실거래 조회에 필요)
                apt_hash = apt.get("aptHash")
                if apt_hash:
                    print(f"  aptHash: {apt_hash} (실거래 조회용 ID)")
        else:
            print(f"'{apartment_name}' 검색 결과가 없습니다")

# 사용 예시
search_apartments_by_name("래미안 강남자이")
```

### 5. 실시간 인기 순위 데이터 수집

```python
import schedule
import time
from datetime import datetime

def collect_ranking_data():
    """인기 순위 데이터 수집 및 저장"""
    config = CrawlerConfig()

    with HogangnonoAPIClient(config) as client:
        # 인기 순위 조회
        ranks_response = client.get_ranking(rank_type="daily", limit=50)

        if ranks_response.success:
            ranks_data = ranks_response.data

            # CSV로 저장
            crawler = HogangnonoCrawler(config, output_dir="./rankings")
            crawler.save_ranks_to_csv()

            print(f"[{datetime.now()}] 인기 순위 데이터 저장 완료")

# 매일 오전 9시에 데이터 수집
schedule.every().day.at("09:00").do(collect_ranking_data)

# 테스트를 위해 즉시 실행
collect_ranking_data()

# 스케줄러 실행 (실제 운영 환경용)
# while True:
#     schedule.run_pending()
#     time.sleep(60)
```

## 에러 핸들링

### 1. 기본 에러 처리

```python
from crawler.api.hogangnono_client import APIResponse

def safe_api_call(func, *args, **kwargs):
    """안전한 API 호출 래퍼"""
    try:
        response = func(*args, **kwargs)

        if not response.success:
            # API 레벨 에러 처리
            if response.status_code == 429:
                print("Rate limit 초과. 잠시 후 다시 시도하세요.")
                return None
            elif response.status_code == 404:
                print("요청한 데이터를 찾을 수 없습니다.")
                return None
            elif response.status_code >= 500:
                print("서버 에러가 발생했습니다. 잠시 후 다시 시도하세요.")
                return None
            else:
                print(f"API 에러: {response.error}")
                return None

        return response.data

    except Exception as e:
        print(f"예상치 못한 에러 발생: {e}")
        return None

# 사용 예시
config = CrawlerConfig()
with HogangnonoAPIClient(config) as client:
    # 안전한 API 호출
    regions = safe_api_call(client.get_regions)
    if regions:
        print(f"{len(regions)}개 지역 조회 성공")
```

### 2. API 응답 데이터 유효성 검사

```python
def validate_poi_response(response_data):
    """POI 응답 데이터 유효성 검사"""
    if not response_data:
        print("응답 데이터가 없습니다")
        return False

    if not isinstance(response_data, list):
        print("응답이 배열 형태가 아닙니다")
        return False

    required_fields = ['aptHash', 'name', 'lat', 'lng']
    for poi in response_data:
        for field in required_fields:
            if field not in poi:
                print(f"필수 필드 '{field}'가 없습니다: {poi}")
                return False

    return True

def validate_transaction_response(response_data):
    """실거래 응답 데이터 유효성 검사"""
    if not response_data:
        return True  # 빈 응답은 유효

    # 응답이 객체인 경우 (shortTermReport 필드)
    if isinstance(response_data, dict):
        transactions = response_data.get("shortTermReport", [])
    # 응답이 배열인 경우
    elif isinstance(response_data, list):
        transactions = response_data
    else:
        print("실거래 응답 형식이 올바르지 않습니다")
        return False

    # 각 거래 데이터 필드 확인
    for transaction in transactions:
        if not isinstance(transaction, dict):
            continue
        if 'date' not in transaction or 'volume' not in transaction:
            print(f"거래 데이터에 필수 필드가 없습니다: {transaction}")
            return False

    return True
```

### 2. 재시도 로직 구현

```python
import time
from typing import Callable, Any

def retry_with_backoff(
    func: Callable,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    *args,
    **kwargs
) -> Any:
    """지수 백오프를 사용한 재시도"""
    for attempt in range(max_attempts):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == max_attempts - 1:
                # 최종 실패
                raise e

            # 대기 시간 계산
            delay = initial_delay * (backoff_factor ** attempt)
            print(f"시도 {attempt + 1} 실패: {e}")
            print(f"{delay:.1f}초 후 재시도...")
            time.sleep(delay)

# 사용 예시
config = CrawlerConfig()
with HogangnonoAPIClient(config) as client:
    try:
        # 재시도 로직과 함께 API 호출
        regions_response = retry_with_backoff(
            client.get_regions,
            max_attempts=5,
            initial_delay=2.0
        )
        print("지역 정보 조회 성공")
    except Exception as e:
        print(f"최종 실패: {e}")
```

### 3. 체크포인트를 이용한 중단점 관리

```python
import json
from pathlib import Path

class CheckpointManager:
    """체크포인트 관리자"""

    def __init__(self, checkpoint_file: Path):
        self.checkpoint_file = checkpoint_file
        self.data = self._load()

    def _load(self) -> dict:
        """체크포인트 파일 로드"""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return {"completed": [], "last_position": None}

    def save(self, completed_items: list, last_position: str = None):
        """체크포인트 저장"""
        self.data["completed"] = completed_items
        self.data["last_position"] = last_position

        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.data, f, indent=2)

    def is_completed(self, item_id: str) -> bool:
        """완료된 항목인지 확인"""
        return item_id in self.data["completed"]

# 사용 예시
def crawl_with_checkpoint():
    checkpoint = CheckpointManager(Path("./checkpoint.json"))

    # 크롤링할 아파트 ID 목록
    apartment_ids = ["1Hq6f", "2Bx7k", "3Cz9l", "4Da2m", "5En5p"]
    completed = []

    config = CrawlerConfig()
    with HogangnonoAPIClient(config) as client:
        for apt_id in apartment_ids:
            if checkpoint.is_completed(apt_id):
                print(f"{apt_id}는 이미 처리됨")
                continue

            try:
                # 아파트 정보 처리
                response = client.get_apartment_detail(apt_id)
                if response.success:
                    print(f"{apt_id} 처리 완료")
                    completed.append(apt_id)

                    # 체크포인트 저장
                    checkpoint.save(completed, apt_id)
                else:
                    print(f"{apt_id} 처리 실패: {response.error}")

            except Exception as e:
                print(f"{apt_id} 처리 중 에러: {e}")
                # 실패해도 체크포인트 저장 (다음 시도에 건너뛰기 위해)
                checkpoint.save(completed, apt_id)
```

## 데이터 저장 형식

### 단지 정보 (complexes.csv)
```csv
aptId,name,address,buildYear,household,lat,lng,cortarNo
1Hq6f,래미안 강남자이,서울특별시 강남구 개포동,2005,1012,37.5135,127.0434,1168010500
```

### 거래내역 (transactions.csv)
```csv
aptId,tradeDate,price,floor,area,tradeType
1Hq6f,2025-01-18,340000,9,84.95,매매
```

## 에러 처리 및 안정성 확보

1. **재시도 로직**: 최대 3회, 지수 백오프
2. **체크포인트**: 중단된 지점부터 재개 지원
3. **로그 기록**: 상세한 실행 로그와 에러 추적
4. **데이터 검증**: 중복 제거 및 필수 필드 확인

## 추가 API 엔드포인트

### 아파트 상세 정보
- `/api/v2/apts/{aptId}` - 아파트 상세 정보 (실제 사용)
- `/api/v2/apts/{aptId}/simple` - 아파트 기본 정보 (문서상 존재)
- `/api/v2/apts/{aptId}/room-types` - 아파트 타입 정보 (문서상 존재)
- `/api/v2/apts/{aptId}/reviews/summary` - 리뷰 요약 (문서상 존재)

### 통계 정보
- `/api/v2/ranks/rolling` - 인기 순위 롤링 데이터 (실제 사용)
- `/api/v2/regions/{regionCode}/details` - 지역 상세 정보 (문서상 존재)
- `/api/v2/regions/{regionCode}/charts` - 지역 차트 데이터 (문서상 존재)
- `/api/v2/realtime/visitor/apt/{aptId}` - 실시간 방문자 수 (문서상 존재)

### 매물 관련
- `/cluster/ajax/complexList` - 단지 목록 조회 (실제 사용)
- `/cluster/ajax/complexDetail` - 단지 상세 정보 (실제 사용)
- `/api/v2/item-catalogs/summaries` - 매물 요약 정보 (문서상 존재)
- `/api/v2/item-catalogs/{itemId}` - 매물 상세 정보 (문서상 존재)

### 검색 관련
- `/api/v2/searches/new` - 동 코드 검색 API (실제 사용)
- `/api/search/apartments` - 아파트 검색 API (일부 구현)

## API 상세 명세

### 1. POI 바운딩 API (/api/v2/pois-bounding)

#### 요청 파라미터
| 파라미터 | 타입 | 필수 | 설명 | 기본값 |
|---------|------|------|------|--------|
| level | int | 아니오 | 줌 레벨 (1-18) | 14 |
| startX | float | 예 | 최소 경도 | - |
| endX | float | 예 | 최대 경도 | - |
| startY | float | 예 | 최소 위도 | - |
| endY | float | 예 | 최대 위도 | - |
| aptType | int | 아니오 | 아파트 유형 | -1 |
| tradeType | int | 아니오 | 거래 유형 | 0 |
| priceType | int | 아니오 | 가격 유형 | 0 |
| rentType | int | 아니오 | 임대 유형 | 0 |
| screenWidth | int | 아니오 | 화면 너비 | 1200 |
| screenHeight | int | 아니오 | 화면 높이 | 924 |
| map | string | 아니오 | 지도 종류 | "google" |

#### aptType 상세
- `-1`: 전체 유형
- `0`: 아파트 (APARTMENT)
- `1`: 주상복합 (MIXED_USE)
- `2`: 오피스텔 (OFFICETEL)

#### tradeType 상세
- `0`: 매매 (A1)
- `1`: 전세 (A2)
- `2`: 월세 (A3)

#### 응답 필드
| 필드 | 타입 | 설명 |
|------|------|------|
| aptHash | string | 아파트 고유 해시 (실거래 조회에 사용) |
| name | string | 아파트 단지명 |
| address | string | 도로명 주소 |
| addressJibun | string | 지번 주소 |
| lat | float | 위도 |
| lng | float | 경도 |
| buildYear | int | 건축년도 |
| householdCnt | int | 세대수 |
| minArea | float | 최소 전용면적 (㎡) |
| maxArea | float | 최대 전용면적 (㎡) |
| minPrice | int | 최소 가격 (만원) |
| maxPrice | int | 최대 가격 (만원) |
| cortarNo | string | 법정동 코드 (9자리) |
| category | string | 부동산 카테고리 |
| tradeType | string | 거래 유형 코드 |

### 2. 실거래 내역 API (/api/v2/apts/{aptHash}/monthly-reports)

#### 요청 파라미터
| 파라미터 | 타입 | 필수 | 설명 | 기본값 |
|---------|------|------|------|--------|
| aptHash | string | 예 | 아파트 해시 (POI 조회에서 획득) | - |
| tradeType | int | 아니오 | 거래 유형 (0=매매, 1=전세, 2=월세) | 0 |
| areaNo | int | 아니오 | 전용면적 번호 (0=전체) | 0 |

#### 응답 필드
| 필드 | 타입 | 설명 |
|------|------|------|
| date | string | 거래일 (ISO 8601 형식) |
| minPrice | int | 최소 거래가 (만원) |
| maxPrice | int | 최대 거래가 (만원) |
| averagePrice | int | 평균 거래가 (만원) |
| volume | int | 거래 건수 |
| trades | array | 상세 거래 정보 |
| trades[].id | int | 거래 고유 ID |
| trades[].price | int | 거래가 (만원) |
| trades[].floor | int | 층수 |
| trades[].day | int | 거래일 |

### 3. 지역 정보 API (/api/v2/regions)

#### 응답 필드
| 필드 | 타입 | 설명 |
|------|------|------|
| regionCode | string | 지역 코드 |
| name | string | 지역명 (짧음) |
| fullName | string | 지역명 (전체) |
| children | array | 하위 지역 목록 |

## POI 카테고리 필터링

### 특정 유형만 조회 예시

```python
# 주상복합만 조회
search_params = SearchParams(
    bbox=(126.7, 37.4, 127.2, 37.7),
    level=14,
    aptType=1,  # 주상복합
    tradeType=0  # 매매
)

# 오피스텔 전세만 조회
search_params = SearchParams(
    bbox=(126.7, 37.4, 127.2, 37.7),
    level=14,
    aptType=2,  # 오피스텔
    tradeType=1  # 전세
)

# 전체 유형 조회
search_params = SearchParams(
    bbox=(126.7, 37.4, 127.2, 37.7),
    level=14,
    aptType=-1,  # 전체
    tradeType=0  # 매매
)
```

## 아파트 ID(aptHash) 획득 방법

### 1. Bounding Box 조회로 획득
가장 일반적인 방법으로, 특정 지역의 모든 아파트 목록을 조회하며 자동으로 aptHash를 포함합니다.

### 2. 검색어로 조회
```python
# 아파트 이름으로 검색하여 aptHash 획득
def get_apt_hash_by_name(name: str):
    search_params = SearchParams(
        bbox=(127.0, 37.5, 127.1, 37.6),  # 대략적인 서울 위치
        level=14,
        aptType=0
    )

    response = client.get_apartments_bounding(search_params)
    if response.success:
        for apt in response.data:
            if name in apt.get('name', ''):
                return apt.get('aptHash')
    return None
```

### 3. 좌표 기반 조회
특정 좌표 근처의 아파트를 조회하여 aptHash를 찾을 수 있습니다.

## 구현 팁

1. **aptHash 관리**: POI 조회에서 얻은 aptHash를 반드시 저장해야 실거래 데이터를 조회할 수 있습니다
2. **좌표 변환**: 지도 좌표계와 행정구역 코드 간의 변환이 필요할 수 있습니다
3. **데이터 정규화**: 가격은 만원 단위, 날짜는 ISO 형식 등으로 정규화 필요
4. **병렬 처리**: 각 구나 bbox 단위로 병렬 처리 가능하나 rate limiting에 주의
5. **응답 구조 유연성**: API 응답 구조가 변경될 수 있으므로 항상 데이터 타입 확인 필요

## 코드 예제

### 기본 API 클라이언트 사용법
```python
from crawler.config import CrawlerConfig
from crawler.api.hogangnono_client import HogangnonoAPIClient, SearchParams

# 설정 초기화
config = CrawlerConfig()

# API 클라이언트 생성
with HogangnonoAPIClient(config) as client:
    # 지역 정보 조회
    regions_response = client.get_regions()
    if regions_response.success:
        regions = regions_response.data

    # 아파트 검색
    search_params = SearchParams(
        bbox=(126.7, 37.4, 127.2, 37.7),  # 서울시 좌표
        level=14,
        tradeType=0,  # 매매
        aptType=0,    # 아파트
    )

    apartments_response = client.get_apartments_bounding(search_params)
    if apartments_response.success:
        apartments = apartments_response.data
```

### 데이터 매핑 사용법
```python
from crawler.data_mappers import HogangnonoDataMapper

# 데이터 매퍼 초기화
mapper = HogangnonoDataMapper()

# API 응답 데이터를 네이버 형식으로 변환
mapped_data = mapper.map_to_naver_format(
    item=api_response_item,
    fetch_dong_code_func=client.fetch_dong_codes
)

if mapped_data:
    # 단지 정보 추출
    complex_info = mapper.extract_complex_info(mapped_data)

    # 거래 정보 추출
    transaction_info = mapper.extract_transaction_info(mapped_data)
```

### Rate Limiting 처리
```python
from crawler.rate_limiter import AdaptiveRateLimiter

# AdaptiveRateLimiter는 HogangnonoAPIClient 내부에서 자동으로 사용됨
# - 성공 시: 대기 시간 감소 (최소 1초)
# - 429 에러 시: 대기 시간 2배 증가 (최대 10초)
# - 기본 대기 시간: 2초
```

## 주의사항

- API 호출 시 반드시 `X-Requested-With: XMLHttpRequest` 헤더 포함
- 600개 POI 제한을 피하기 위해 bbox 분할 필수
- 과도한 요청은 IP 차단 가능성이 있으므로 rate limiting 준수
- 일부 API는 로그인이 필요할 수 있음
- **aptHash vs aptId**: POI 조회 응답에는 `aptId` 필드가 없으며, `aptHash` 필드를 사용해야 함
- **응답 구조**: 실거래 API 응답은 `shortTermReport` 객체 또는 직접 배열로 올 수 있음
- **주요**: 최신 코드베이스는 HogangnonoAPIClient를 사용하므로 직접적인 API 호출 대신 클라이언트 메서드 사용 권장

## 추가 팁

### 1. 효율적인 데이터 수집 전략
- 구 단위로 병렬 처리 시 각 구를 독립적인 bbox로 분할
- POI 밀도가 높은 지역은 더 작은 격자로 분할
- Rate limiting을 준수하며 요청 간격 조절

### 2. 데이터 무결성 유지
- `aptHash`를 DB 인덱스로 사용하여 중복 방지
- 법정동 코드(`cortarNo`)를 활용한 지역별 데이터 집계
- 정기적으로 데이터 검증 및 오류 수정

### 3. 성능 최적화
- 불필요한 필드 요청 제거
- 배치 처리를 통한 API 호출 최소화
- 캐싱 전략을 활용한 중복 요청 방지
