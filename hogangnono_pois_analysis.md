# 호갱노노 아파트 단지 정보 API 상세 분석 보고서

## 5단계: 아파트 단지 정보 API 분석

### API 엔드포인트
- 기본 URL: `https://hogangnono.com`
- 단지 목록 조회: `/api/v2/pois-bounding`
- 인기 순위 조회: `/api/v2/ranks/rolling`

### 요청 파라미터 상세

| 파라미터명 | 타입 | 필수 여부 | 설명 | 예시 |
|-----------|------|-----------|------|------|
| startX | float | 필수 | 최소 경도 (lng_min) | 126.734086 |
| endX | float | 필수 | 최대 경도 (lng_max) | 127.183394 |
| startY | float | 필수 | 최소 위도 (lat_min) | 37.413294 |
| endY | float | 필수 | 최대 위도 (lat_max) | 37.715133 |
| level | int | 선택 | 줌 레벨 (1-18) | 14 |
| tradeType | int | 선택 | 거래 유형 (0:매매, 1:전세, 2:월세) | 0 |
| aptType | int | 선택 | 아파트 유형 (-1:전체, 0:아파트, 1:주상복합, 2:오피스텔) | 0 |
| priceType | int | 선택 | 가격 유형 (0:전체, 1:매매, 2:전세) | 0 |
| rentType | int | 선택 | 임대 유형 (0:전체, 1:월세, 2:단기임대) | 0 |
| map | string | 선택 | 지도 종류 | "google" |
| screenWidth | int | 고정 | 화면 너비 | 1200 |
| screenHeight | int | 고정 | 화면 높이 | 924 |
| apt | string | 고정 | 아파트 필터 | "" |

### 요청 예시

```bash
# 강남구 아파트 단지 조회
curl -X GET "https://hogangnono.com/api/v2/pois-bounding?startX=126.998&endX=127.087&startY=37.483&endY=37.545&level=14&tradeType=0&aptType=0"

# 특정 동 조회 (역삼1동)
curl -X GET "https://hogangnono.com/api/v2/pois-bounding?startX=127.035&endX=127.055&startY=37.5&endY=37.52&level=17&tradeType=0&aptType=0"
```

### 응답 데이터 구조

```json
{
  "status": "success",
  "data": [
    {
      "id": "ho13",
      "category": 1,
      "name": "봉은사",
      "description": "9호선",
      "content": null,
      "lat": 37.5142554489848,
      "lng": 127.060233935114,
      "address": null,
      "likes": 0,
      "isExpired": 0,
      "dong": null,
      "dist": 86
    }
  ]
}
```

### 주요 필드 설명

| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| id | string | 단지/POI 고유 ID | "ho13" |
| category | number | 카테고리 (1: POI) | 1 |
| name | string | 명칭 | "봉은사" |
| description | string | 설명 (주로 교통정보) | "9호선" |
| content | object | 상세 콘텐츠 (null인 경우多) | null |
| lat | float | 위도 (WGS84) | 37.514255 |
| lng | float | 경도 (WGS84) | 127.060233 |
| address | string | 주소 (대부분 null) | null |
| likes | number | 좋아요 수 | 0 |
| isExpired | number | 만료 여부 | 0 |
| dong | string | 동 정보 (대부분 null) | null |
| dist | number | 중심점으로부터의 거리(미터) | 86 |

### bbox 계산 방법

- **좌표계**: WGS84 (EPSG:4326)
- **단위**: 도 (decimal degrees)
- **형식**: (lng_min, lat_min, lng_max, lat_max)
- **경도 범위**: 126.734086 ~ 127.183394 (서울시)
- **위도 범위**: 37.413294 ~ 37.715133 (서울시)

### bbox 계산 예시

```python
# 서울시 전체
seoul_bbox = (126.734086, 37.413294, 127.183394, 37.715133)

# 강남구
gangnam_bbox = (126.998, 37.483, 127.087, 37.545)

# 특정 동 (역삼1동)
yesan_bbox = (127.035, 37.5, 127.055, 37.52)
```

### 줌 레벨별 데이터 차이

| 줌 레벨 | 설명 | 데이터 수 | 특징 |
|---------|------|-----------|------|
| 12 | 시/도 단위 | 0개 | 너무 넓어 데이터 없음 |
| 14 | 구/군 단위 | 87개 | 적절한 단위로 데이터 조회 |
| 16 | 동 단위 | 87개 | 상세한 단지 정보 |
| 17 | 소동 단위 | 10개 | 더 좁은 영역의 단지만 |
| 18 | 최상세 | 10개 | 가장 상세한 뷰 |

### aptType 파라미터 영향

- **aptType=-1**: 전체 유형 (10개)
- **aptType=0**: 아파트 (10개)
- **aptType=1**: 주상복합 (10개)
- **aptType=2**: 오피스텔 (10개)

⚠️ **주의**: 테스트 결과 모든 aptType 값에서 동일한 데이터가 반환됨. 실제 아파트 단지 필터링은 다른 방식으로 이루어질 수 있음.

### 데이터 제한 및 페이지네이션

- **최대 데이터 수**: 600개 (서울시 전체 조회 시)
- **페이지네이션**: 지원하지 않음
- **제한**: bbox 당 최대 600개 POI 반환
- **해결책**: bbox를 더 작은 단위로 분할하여 요청 필요

### 분석 결과 및 제약사항

1. **API 특징**
   - bbox 기반의 공간查询 API
   - POI(Point of Interest) 데이터 반환
   - 아파트 단지 정보 뿐만 아니라 지역 내 모든 POI 포함

2. **주요 제약사항**
   - **데이터 제한**: bbox 당 최대 600개
   - **페이지네이션 없음**: 한 번에 모든 데이터 반환
   - **아파트 필터링**: aptType 파라미터가 실제로는 필터링되지 않음
   - **상세 정보 부족**: address, dong 등 주요 필드가 null로 반환

3. **좌표 정확도**
   - 고정밀도 좌표 제공 (소수점 15자리)
   - WGS84 좌표계 사용
   - GPS 기반 위치 정확도 높음

4. **실제 아파트 단지와 POI의 구분**
   - category 필드로 구분 가능 (1 = POI)
   - name 필드로 아파트 단지명 판별 필요
   - description 필드에 교통정보 포함

### 활용 방안

1. **데이터 수집 전략**
   - bbox를 0.01도 간격으로 분할
   - 각 bbox 별로 최대 600개 제한 고려
   - 수집 후 name 필드로 아파트 단지 필터링

2. **개선 제안**
   - aptType 필터링 기능 확인 필요
   - 아파트 단지 전용 API 엔드포인트 탐색
   - 상세 정보 조회 API 추가 조사 (단지 ID 기반)

### 다음 단계 (6단계)
실거래 내역 API를 분석하여 단지별 매물 정보를 조회하는 방법을 파악해야 함. 특히:
- 단지 ID를 이용한 매물 목록 조회 API
- 실거래 데이터 필드 및 구조
- 시계열 데이터 수집 방법
- 거래 유형별(매매/전세/월세) 조회 방법
