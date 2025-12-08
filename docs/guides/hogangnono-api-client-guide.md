# 호갱노노 API 클라이언트 가이드

호갱노노 API 전용 클라이언트 사용법을 안내합니다.

## 개요

`HogangnonoAPIClient`는 호갱노노 API와의 통신을 쉽게 하기 위한 전용 클라이언트입니다. 다양한 API 엔드포인트에 접근할 수 있는 메서드와 편리한 응답 처리 기능을 제공합니다.

## 기본 사용법

### 1. 클라이언트 초기화

```python
from crawler.api import HogangnonoAPIClient
from crawler.config import CrawlerConfig

# 설정 로드
config = CrawlerConfig.from_env()

# 클라이언트 생성 (Context Manager 사용)
with HogangnonoAPIClient(config) as client:
    # API 호출
    pass
```

### 2. 기본 API 호출

```python
# 랭킹 조회
response = client.get_ranking(rank_type="daily", limit=20)

# 응답 확인
if response.success:
    print(f"성공: {response.data}")
else:
    print(f"실패: {response.error}")
```

## API 메서드 상세

### 랭킹 조회

```python
response = client.get_ranking(
    rank_type="daily",  # "daily", "weekly", "monthly"
    region=None,        # 지역 코드 (선택)
    limit=20           # 결과 제한 개수
)
```

### 최근 조회 목록

```python
response = client.get_recent_visits(
    apt_type="apart",   # "apart", "officetel", "house" (선택)
    region=None,        # 지역 코드 (선택)
    limit=50           # 결과 제한 개수
)
```

### 지역 정보 조회

```python
response = client.get_region_info(
    lat=37.5172,       # 위도
    lng=127.0473,      # 경도
    zoom=14            # 지도 확대 레벨
)
```

### POI 정보 조회 (Bounding box)

```python
from crawler.api import SearchParams

# 검색 파라미터 설정
search_params = SearchParams(
    bbox=(37.5, 126.9, 37.6, 127.0),  # (lat_min, lng_min, lat_max, lng_max)
    zoom=14,                          # 지도 확대 레벨
    filters={"category": "subway"},   # 필터링 조건 (선택)
    limit=20                          # 결과 제한 개수
)

response = client.get_pois_bounding(search_params)
```

### 아파트 목록 조회 (Bounding box)

```python
# 검색 파라미터 설정
search_params = SearchParams(
    bbox=(37.5, 126.9, 37.6, 127.0),
    zoom=14,
    filters={
        "min_price": 50000,  # 최소 가격
        "max_price": 100000, # 최대 가격
        "min_area": 84,      # 최소 전용면적
    },
    limit=20
)

response = client.get_apartments_bounding(
    search_params,
    apt_type="apart",    # "apart", "officetel", "house" (선택)
    trade_type="sale",   # "sale", "jeonse", "monthly" (선택)
)
```

### 아파트 검색

```python
response = client.search_apartments(
    keyword="강남구 삼성동 아파트",
    region=None,          # 지역 코드 (선택)
    page=1,              # 페이지 번호
    limit=20             # 페이지당 결과 수
)
```

### 아파트 상세 정보

```python
response = client.get_apartment_detail(apt_id="apt_12345")
```

## 데이터 모델

### SearchParams

API 검색 파라미터를 위한 데이터 클래스입니다.

```python
@dataclass
class SearchParams:
    bbox: Optional[tuple[float, float, float, float]] = None  # Bounding box
    zoom: Optional[int] = None                                # 지도 확대 레벨
    filters: Optional[dict[str, Any]] = None                  # 필터링 조건
    limit: Optional[int] = None                               # 결과 제한 개수
```

### APIResponse

API 응답을 감싸는 클래스입니다.

```python
@dataclass
class APIResponse:
    success: bool                           # API 호출 성공 여부
    data: Optional[dict[str, Any]] = None   # 응답 데이터
    error: Optional[str] = None            # 에러 메시지
    status_code: Optional[int] = None      # HTTP 상태 코드
```

## 예제 스크립트

전체 예제는 `scripts/example_hogangnono_client.py`를 참고하세요.

```bash
# 예제 스크립트 실행
python scripts/example_hogangnono_client.py
```

## 에러 처리

클라이언트는 자동으로 에러 처리 및 재시도 로직을 적용합니다.

- 최대 3회 재시도
- 지수 백오프 적용
- API 응답 구조 자동 분석
- 상세한 로깅 제공

## 주의사항

1. **Rate Limiting**: API 호출 간 최소 1초 간격 유지
2. **Session 관리**: Context Manager 사용 권장
3. **에러 처리**: 항상 `response.success` 확인
4. **데이터 검증**: 실제 응답 구조에 따라 데이터 검증 필요

## 테스트

```bash
# 단위 테스트 실행
uv run pytest tests/unit/test_hogangnono_client.py -v
```

## 확장

새로운 API 엔드포인트가 필요한 경우 `HogangnonoAPIClient` 클래스에 메서드를 추가할 수 있습니다.

```python
def get_new_endpoint(self, param1, param2):
    """새로운 API 엔드포인트"""
    params = {
        "param1": param1,
        "param2": param2,
    }
    return self._make_request(
        method="GET",
        endpoint="/api/v2/new-endpoint",
        params=params,
    )
```