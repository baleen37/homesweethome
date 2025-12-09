# 호갱노노 아파트 단지 정보 조회 API 최종 분석 보고서

## 개요

호갱노노(https://hogangnono.com)의 아파트 단지 정보 조회 API를 상세 분석한 결과입니다. 실제 API를 호출하여 데이터 구조와 파라미터를 확인했습니다.

**분석 일자**: 2025-12-09
**분석 방법**: 직접 API 호출 및 응답 데이터 분석

---

## 1. API 엔드포인트

### 기본 엔드포인트
- **URL**: `https://hogangnono.com/api/v2/pois-bounding`
- **HTTP Method**: GET
- **인증**: 세션 쿠키 필요 (connect.sid, client.cid, bat)

### 검색 엔드포인트
- **URL**: `https://hogangnono.com/api/v2/searches/new`
- **용도**: 아파트 이름으로 ID 검색
- **Method**: GET

---

## 2. 아파트 단지 정보 조회 API 상세

### 2.1 요청 파라미터

| 파라미터 | 타입 | 필수 여부 | 설명 | 예시 |
|----------|------|-----------|------|------|
| map | string | O | 지도 종료 | "google" |
| level | int | O | 줌 레벨 (14-18) | 17 |
| startX | float | O | 최소 경도 | 127.040 |
| endX | float | O | 최대 경도 | 127.050 |
| startY | float | O | 최소 위도 | 37.510 |
| endY | float | O | 최대 위도 | 37.520 |
| tradeType | int | X | 거래 유형 (0:매매, 1:전세, 2:월세) | 0 |
| priceType | int | X | 가격 타입 (0:전체) | 0 |
| rentType | int | X | 임대 타입 (0:전체) | 0 |
| apt | string | X | 특정 아파트 ID | "5SA38" |
| screenWidth | int | X | 화면 너비 | 1200 |
| screenHeight | int | X | 화면 높이 | 924 |

### 2.2 요청 예시

```bash
# 특정 영역의 아파트 조회
GET /api/v2/pois-bounding?map=google&level=17&startX=127.040&endX=127.050&startY=37.510&endY=37.520&tradeType=0

# 특정 아파트 ID로 조회
GET /api/v2/pois-bounding?map=google&level=17&apt=5SA38
```

---

## 3. 응답 데이터 구조

### 3.1 전체 응답 형식

```json
{
  "data": [
    {
      "id": "아이디",
      "category": 카테고리번호,
      "name": "이름",
      "description": "설명",
      "lat": 위도,
      "lng": 경도,
      ...
    }
  ],
  "status": "success"
}
```

### 3.2 카테고리 분류

| Category | 설명 | 예시 |
|----------|------|------|
| 0 | 아파트 | 래미안, 힐스테이트 |
| 1 | 지하철역 | 강남구청, 선정릉 |
| 10 | 상점/마트 | 하나로마트 |
| 기타 | 기타 POI | 학교, 병원 등 |

### 3.3 아파트 데이터 필드 (Category=0)

```json
{
  "id": "5SA38",                    // 아파트 고유 ID (5자리 영숫자)
  "category": 0,                    // 0: 아파트
  "name": "래미안슈르",             // 아파트 이름
  "address": "경기도 과천시 원문동 4", // 주소
  "road_address": "경기도 과천시 별양로 12", // 도로명 주소
  "lat": 37.4206735,               // 위도
  "lng": 126.9922954,              // 경도
  "household": 2899,               // 세대수
  "trade_count": 3706,             // 거래 건수
  "build_date": "2008-08-11",      // 건축일
  "tag": "과천 과천역 남동향...",   // 태그 정보
  // ... 기타 필드
}
```

---

## 4. 아파트 ID 체계

### ID 형식
- **길이**: 5자리
- **구성**: 영문(대소문자) + 숫자 조합
- **예시**: `5SA38`, `20B1c`, `bnWd0`

### ID 얻는 방법
1. **검색 API 사용**: `/api/v2/searches/new?query=아파트이름`
2. **응답에서 추출**: `data.matched.apt.list[].id`

---

## 5. 데이터 수집 전략

### 5.1 권장 흐름

```
1. 검색 API로 아파트 ID 수집
   ↓
2. 아파트 ID로 bounding API 호출
   ↓
3. category=0인 데이터만 필터링
```

### 5.2 파라미터 최적화 팁

1. **줌 레벨**
   - 14-16: 구 단위 넓은 영역
   - 17-18: 동 단위 좁은 영역
   - 높을수록 상세한 아파트 정보

2. **좌표 범위**
   - 너무 넓으면 POI가 너무 많음
   - 0.01도 차이가 약 1km

3. **apt 파라미터**
   - 특정 아파트 주변 POI 조회 시 유용
   - 넓은 영역에서 아파트 찾을 때 사용

---

## 6. 필터링 옵션

### 6.1 거래 유형 필터링
- `tradeType=0`: 매매
- `tradeType=1`: 전세
- `tradeType=2`: 월세

### 6.2 카테고리 필터링
- 응답받은 데이터에서 `category=0`인 것만 선택
- 아파트만 필터링 가능

---

## 7. 데이터 제한

- **최대 데이터**: 약 600개 POI (API 기본 제한)
- **아파트 수**: 영역에 따라 0~수십 개
- **Rate Limiting**: 1-2초 간격 권장

---

## 8. 실제 사용 예시

### Python 코드

```python
import requests
import json

def get_apartments(session, search_query):
    # 1. 검색으로 아파트 ID 얻기
    search_url = "https://hogangnono.com/api/v2/searches/new"
    params = {
        "query": search_query,
        "x": "127.046953",
        "y": "37.517236"
    }

    response = session.get(search_url, params=params)
    data = response.json()

    apartments = []
    if 'data' in data and 'matched' in data['data']:
        apt_list = data['data']['matched'].get('apt', {}).get('list', [])
        apartments = apt_list

    return apartments

def get_apartments_in_area(session, apt_id, lat, lng):
    # 2. bounding API로 아파트 정보 얻기
    bbox_url = "https://hogangnono.com/api/v2/pois-bounding"
    params = {
        "map": "google",
        "level": "17",
        "startX": lng - 0.01,
        "endX": lng + 0.01,
        "startY": lat - 0.01,
        "endY": lat + 0.01,
        "tradeType": "0",
        "apt": apt_id
    }

    response = session.get(bbox_url, params=params)
    data = response.json()

    # 아파트만 필터링
    apartments = [item for item in data.get('data', []) if item.get('category') == 0]

    return apartments

# 사용 예시
session = requests.Session()
session.get("https://hogangnono.com")  # 세션 초기화

# 강남구 아파트 검색
apts = get_apartments(session, "강남구 아파트")
if apts:
    apt = apts[0]
    print(f"아파트: {apt['name']} (ID: {apt['id']})")

    # 주변 아파트 조회
    nearby_apts = get_apartments_in_area(
        session,
        apt['id'],
        apt['lat'],
        apt['lng']
    )
    print(f"주변 아파트 수: {len(nearby_apts)}")
```

---

## 9. 주의사항

1. **인증 필수**: 세션 쿠키 필요
2. **ID 기반**: 아파트 ID를 먼저 얻어야 함
3. **카테고리 필터링**: 응답에는 다양한 POI 포함
4. **Rate Limiting**: 과도한 요금은 429 에러 유발
5. **좌표 정확도**: 정확한 좌표 범위 설정 필요

---

## 10. 결론

호갱노노 아파트 단지 정보 API는 다음과 같은 특징을 가집니다:

1. **검색 기반**: 아파트 이름으로 ID를 먼저 검색해야 함
2. **Bounding Box**: 지역 기반 조회는 좌표 범위로 수행
3. **카테고리 분류**: POI 타입별 category로 구분
4. **ID 체계**: 5자리 영숫자 조합의 고유 ID 사용
5. **세션 필요**: 쿠키 기반 인증 필수

효과적인 데이터 수집을 위해서는 검색 API와 bounding API를 조합하여 사용하는 것이 권장됩니다.
