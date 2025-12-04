# 네이버 부동산 서울시 구/동 정보 추출 가이드

**조사 일자**: 2025-12-04
**작성자**: Claude Code
**목적**: 네이버 부동산에서 서울시 구/동 정보 및 법정동 코드, 좌표 범위 추출 방법 조사

---

## 1. 사이트 개요

### 1.1 URL 및 구조
- **메인 URL**: https://new.land.naver.com
- **지역 선택 방식**: 시 → 구 → 동 3단계 계층 구조
- **UI 특징**:
  - "지역선택" 버튼 클릭 시 모달 팝업 표시
  - 구 선택 시 해당 구의 동 목록 자동 로드
  - DOM에서 직접 데이터를 가져오는 것보다 **API 호출이 훨씬 효율적**

### 1.2 법정동 코드(cortarNo) 체계
- **10자리 숫자 코드**
- 구조: `시도(2) + 시군구(3) + 읍면동(5)`
- 예시:
  - 서울시: `1100000000`
  - 강남구: `1168000000`
  - 대치동: `1168010600`

---

## 2. API 엔드포인트

### 2.1 지역 목록 조회 API

#### 서울시 전체 구 목록
```
GET https://new.land.naver.com/api/regions/list?cortarNo=1100000000
```

**응답 구조**:
```json
{
  "regionList": [
    {
      "cortarNo": "1168000000",
      "centerLat": 37.517408,
      "centerLon": 127.047313,
      "cortarName": "강남구",
      "cortarType": "dvsn"
    },
    ...
  ]
}
```

**필드 설명**:
- `cortarNo`: 법정동 코드 (10자리)
- `centerLat`, `centerLon`: 중심 좌표
- `cortarName`: 지역명
- `cortarType`: 지역 유형
  - `dvsn`: 구(division)
  - `sec`: 동(sector)

#### 특정 구의 동 목록
```
GET https://new.land.naver.com/api/regions/list?cortarNo={구의cortarNo}
```

예시: 강남구 동 목록
```
GET https://new.land.naver.com/api/regions/list?cortarNo=1168000000
```

**응답 구조**:
```json
{
  "regionList": [
    {
      "cortarNo": "1168010300",
      "centerLat": 37.482968,
      "centerLon": 127.0634,
      "cortarName": "개포동",
      "cortarType": "sec"
    },
    {
      "cortarNo": "1168010800",
      "centerLat": 37.513583,
      "centerLon": 127.031375,
      "cortarName": "논현동",
      "cortarType": "sec"
    },
    ...
  ]
}
```

### 2.2 법정동 경계 좌표(Bounds) 조회 API

```
GET https://new.land.naver.com/api/cortars?zoom={줌레벨}&centerLat={위도}&centerLon={경도}
```

**중요**: `cortarNo` 파라미터만으로는 경계 좌표를 가져올 수 없음. 반드시 `zoom`, `centerLat`, `centerLon`이 필요함.

**파라미터**:
- `zoom`: 지도 줌 레벨 (권장: 15-17)
- `centerLat`: 중심 위도 (regions API에서 가져온 값 사용)
- `centerLon`: 중심 경도 (regions API에서 가져온 값 사용)

**응답 구조** (강남구 대치동 예시):
```json
{
  "cortarVertexLists": [
    [
      [37.5061619, 127.0693789],
      [37.5027424, 127.069802],
      [37.502074, 127.076995],
      ...
      [37.5061619, 127.0693789]
    ]
  ],
  "cortarNo": "1168010600",
  "cortarName": "대치동",
  "cityName": "서울시",
  "divisionName": "강남구",
  "sectorName": "대치동",
  "cityNo": "1100000000",
  "divisionNo": "1168000000",
  "sectorNo": "1168010600",
  "cortarType": "sec",
  "centerLat": 37.49911,
  "centerLon": 127.065463,
  "cortarZoom": 15
}
```

**필드 설명**:
- `cortarVertexLists`: 경계 좌표 배열 (폴리곤 형태)
  - 각 요소는 `[위도, 경도]` 쌍
  - 첫 점과 마지막 점이 동일 (폴리곤 닫힘)
- `cityNo`, `divisionNo`, `sectorNo`: 시/구/동 각각의 cortarNo
- `cortarZoom`: 적용된 줌 레벨

---

## 3. 데이터 추출 전략

### 3.1 권장 크롤링 순서

```
1. 서울시 구 목록 조회
   GET /api/regions/list?cortarNo=1100000000

2. 각 구별로 동 목록 조회 (25회)
   GET /api/regions/list?cortarNo={각 구의 cortarNo}

3. (선택) 각 동의 경계 좌표 조회 (필요시)
   GET /api/cortars?zoom=15&centerLat={동의 centerLat}&centerLon={동의 centerLon}
```

### 3.2 추출 가능한 정보

**기본 정보** (regions API에서):
- ✅ 법정동 코드 (cortarNo)
- ✅ 지역명 (cortarName)
- ✅ 중심 좌표 (centerLat, centerLon)
- ✅ 지역 유형 (cortarType)

**상세 정보** (cortars API에서):
- ✅ 경계 좌표 폴리곤 (cortarVertexLists)
- ✅ 계층 구조 (cityNo, divisionNo, sectorNo)
- ✅ 전체 주소 (cityName, divisionName, sectorName)

### 3.3 Rate Limiting 고려사항

- **요청 간 대기 시간**: 500ms~1000ms 권장
- **총 API 호출 수**:
  - 구 목록: 1회
  - 동 목록: 25회 (서울시 25개 구)
  - 경계 좌표: ~424회 (서울시 전체 동 개수, 선택적)
- **총 소요 시간**: 약 5~10분 (경계 좌표 포함 시)

---

## 4. 실제 데이터 샘플

### 4.1 서울시 전체 구 목록 (25개)

```json
{
  "regionList": [
    {"cortarNo": "1168000000", "centerLat": 37.517408, "centerLon": 127.047313, "cortarName": "강남구", "cortarType": "dvsn"},
    {"cortarNo": "1174000000", "centerLat": 37.530126, "centerLon": 127.123771, "cortarName": "강동구", "cortarType": "dvsn"},
    {"cortarNo": "1130500000", "centerLat": 37.63974, "centerLon": 127.025488, "cortarName": "강북구", "cortarType": "dvsn"},
    {"cortarNo": "1150000000", "centerLat": 37.550985, "centerLon": 126.849534, "cortarName": "강서구", "cortarType": "dvsn"},
    {"cortarNo": "1162000000", "centerLat": 37.481021, "centerLon": 126.951601, "cortarName": "관악구", "cortarType": "dvsn"},
    {"cortarNo": "1121500000", "centerLat": 37.538617, "centerLon": 127.082375, "cortarName": "광진구", "cortarType": "dvsn"},
    {"cortarNo": "1153000000", "centerLat": 37.49551, "centerLon": 126.887532, "cortarName": "구로구", "cortarType": "dvsn"},
    {"cortarNo": "1154500000", "centerLat": 37.45196, "centerLon": 126.902075, "cortarName": "금천구", "cortarType": "dvsn"},
    {"cortarNo": "1135000000", "centerLat": 37.654286, "centerLon": 127.056411, "cortarName": "노원구", "cortarType": "dvsn"},
    {"cortarNo": "1132000000", "centerLat": 37.668768, "centerLon": 127.047163, "cortarName": "도봉구", "cortarType": "dvsn"},
    {"cortarNo": "1123000000", "centerLat": 37.574493, "centerLon": 127.039765, "cortarName": "동대문구", "cortarType": "dvsn"},
    {"cortarNo": "1159000000", "centerLat": 37.51245, "centerLon": 126.9395, "cortarName": "동작구", "cortarType": "dvsn"},
    {"cortarNo": "1144000000", "centerLat": 37.563517, "centerLon": 126.9084, "cortarName": "마포구", "cortarType": "dvsn"},
    {"cortarNo": "1141000000", "centerLat": 37.579225, "centerLon": 126.9368, "cortarName": "서대문구", "cortarType": "dvsn"},
    {"cortarNo": "1165000000", "centerLat": 37.483564, "centerLon": 127.032594, "cortarName": "서초구", "cortarType": "dvsn"},
    {"cortarNo": "1120000000", "centerLat": 37.563475, "centerLon": 127.036838, "cortarName": "성동구", "cortarType": "dvsn"},
    {"cortarNo": "1129000000", "centerLat": 37.5874, "centerLon": 127.020729, "cortarName": "성북구", "cortarType": "dvsn"},
    {"cortarNo": "1171000000", "centerLat": 37.514592, "centerLon": 127.105863, "cortarName": "송파구", "cortarType": "dvsn"},
    {"cortarNo": "1147000000", "centerLat": 37.517007, "centerLon": 126.866546, "cortarName": "양천구", "cortarType": "dvsn"},
    {"cortarNo": "1156000000", "centerLat": 37.526367, "centerLon": 126.896213, "cortarName": "영등포구", "cortarType": "dvsn"},
    {"cortarNo": "1117000000", "centerLat": 37.538825, "centerLon": 126.96535, "cortarName": "용산구", "cortarType": "dvsn"},
    {"cortarNo": "1138000000", "centerLat": 37.60278, "centerLon": 126.929163, "cortarName": "은평구", "cortarType": "dvsn"},
    {"cortarNo": "1111000000", "centerLat": 37.573025, "centerLon": 126.979638, "cortarName": "종로구", "cortarType": "dvsn"},
    {"cortarNo": "1114000000", "centerLat": 37.563842, "centerLon": 126.9976, "cortarName": "중구", "cortarType": "dvsn"},
    {"cortarNo": "1126000000", "centerLat": 37.606324, "centerLon": 127.092584, "cortarName": "중랑구", "cortarType": "dvsn"}
  ]
}
```

### 4.2 강남구 동 목록 (14개)

```json
{
  "regionList": [
    {"cortarNo": "1168010300", "centerLat": 37.482968, "centerLon": 127.0634, "cortarName": "개포동", "cortarType": "sec"},
    {"cortarNo": "1168010800", "centerLat": 37.513583, "centerLon": 127.031375, "cortarName": "논현동", "cortarType": "sec"},
    {"cortarNo": "1168010600", "centerLat": 37.49911, "centerLon": 127.065463, "cortarName": "대치동", "cortarType": "sec"},
    {"cortarNo": "1168011800", "centerLat": 37.488143, "centerLon": 127.04505, "cortarName": "도곡동", "cortarType": "sec"},
    {"cortarNo": "1168010500", "centerLat": 37.514792, "centerLon": 127.055387, "cortarName": "삼성동", "cortarType": "sec"},
    {"cortarNo": "1168011100", "centerLat": 37.46436, "centerLon": 127.1046, "cortarName": "세곡동", "cortarType": "sec"},
    {"cortarNo": "1168011500", "centerLat": 37.488856, "centerLon": 127.104886, "cortarName": "수서동", "cortarType": "sec"},
    {"cortarNo": "1168010700", "centerLat": 37.524142, "centerLon": 127.0229, "cortarName": "신사동", "cortarType": "sec"},
    {"cortarNo": "1168011000", "centerLat": 37.5291, "centerLon": 127.0236, "cortarName": "압구정동", "cortarType": "sec"},
    {"cortarNo": "1168010100", "centerLat": 37.499776, "centerLon": 127.03895, "cortarName": "역삼동", "cortarType": "sec"},
    {"cortarNo": "1168011300", "centerLat": 37.4717, "centerLon": 127.1114, "cortarName": "율현동", "cortarType": "sec"},
    {"cortarNo": "1168011400", "centerLat": 37.487485, "centerLon": 127.081638, "cortarName": "일원동", "cortarType": "sec"},
    {"cortarNo": "1168011200", "centerLat": 37.4766, "centerLon": 127.101, "cortarName": "자곡동", "cortarType": "sec"},
    {"cortarNo": "1168010400", "centerLat": 37.525492, "centerLon": 127.05235, "cortarName": "청담동", "cortarType": "sec"}
  ]
}
```

### 4.3 송파구 동 목록 (13개)

```json
{
  "regionList": [
    {"cortarNo": "1171010700", "centerLat": 37.495301, "centerLon": 127.1186, "cortarName": "가락동", "cortarType": "sec"},
    {"cortarNo": "1171011300", "centerLat": 37.489351, "centerLon": 127.147175, "cortarName": "거여동", "cortarType": "sec"},
    {"cortarNo": "1171011400", "centerLat": 37.49746, "centerLon": 127.153625, "cortarName": "마천동", "cortarType": "sec"},
    {"cortarNo": "1171010800", "centerLat": 37.4854, "centerLon": 127.1221, "cortarName": "문정동", "cortarType": "sec"},
    {"cortarNo": "1171011100", "centerLat": 37.51506, "centerLon": 127.122999, "cortarName": "방이동", "cortarType": "sec"},
    {"cortarNo": "1171010600", "centerLat": 37.502717, "centerLon": 127.092513, "cortarName": "삼전동", "cortarType": "sec"},
    {"cortarNo": "1171010500", "centerLat": 37.503592, "centerLon": 127.1037, "cortarName": "석촌동", "cortarType": "sec"},
    {"cortarNo": "1171010400", "centerLat": 37.504983, "centerLon": 127.11465, "cortarName": "송파동", "cortarType": "sec"},
    {"cortarNo": "1171010200", "centerLat": 37.517425, "centerLon": 127.101844, "cortarName": "신천동", "cortarType": "sec"},
    {"cortarNo": "1171011200", "centerLat": 37.504774, "centerLon": 127.134595, "cortarName": "오금동", "cortarType": "sec"},
    {"cortarNo": "1171010100", "centerLat": 37.5111, "centerLon": 127.0851, "cortarName": "잠실동", "cortarType": "sec"},
    {"cortarNo": "1171010900", "centerLat": 37.478842, "centerLon": 127.135859, "cortarName": "장지동", "cortarType": "sec"},
    {"cortarNo": "1171010300", "centerLat": 37.533267, "centerLon": 127.11485, "cortarName": "풍납동", "cortarType": "sec"}
  ]
}
```

### 4.4 종로구 동 목록 (87개) - 일부만 표시

종로구는 87개의 동이 있어 서울시에서 가장 많습니다. 주요 동 샘플:

```json
{
  "regionList": [
    {"cortarNo": "1111014600", "centerLat": 37.582583, "centerLon": 126.984525, "cortarName": "가회동", "cortarType": "sec"},
    {"cortarNo": "1111018200", "centerLat": 37.6179, "centerLon": 126.9574, "cortarName": "구기동", "cortarType": "sec"},
    {"cortarNo": "1111016800", "centerLat": 37.5813, "centerLon": 127.005, "cortarName": "동숭동", "cortarType": "sec"},
    {"cortarNo": "1111018400", "centerLat": 37.59244, "centerLon": 126.964047, "cortarName": "부암동", "cortarType": "sec"},
    {"cortarNo": "1111014000", "centerLat": 37.59, "centerLon": 126.9817, "cortarName": "삼청동", "cortarType": "sec"},
    {"cortarNo": "1111011900", "centerLat": 37.5795, "centerLon": 126.9768, "cortarName": "세종로", "cortarType": "sec"},
    {"cortarNo": "1111013600", "centerLat": 37.5717, "centerLon": 126.986, "cortarName": "인사동", "cortarType": "sec"},
    {"cortarNo": "1111016900", "centerLat": 37.583383, "centerLon": 127.001369, "cortarName": "혜화동", "cortarType": "sec"}
  ]
}
```

### 4.5 경계 좌표(Bounds) 샘플 - 대치동

```json
{
  "cortarVertexLists": [
    [
      [37.5061619, 127.0693789],
      [37.5027424, 127.069802],
      [37.502074, 127.076995],
      [37.5010926, 127.0799371],
      [37.4995921, 127.0802967],
      [37.4982535, 127.0794894],
      [37.4974321, 127.078782],
      [37.4976172, 127.078491],
      [37.4974434, 127.078431],
      [37.4962565, 127.0747511],
      [37.4952414, 127.0743974],
      [37.4942367, 127.0737293],
      [37.4942362, 127.0721618],
      [37.4918778, 127.0697383],
      [37.4909139, 127.0681335],
      [37.4904326, 127.0668897],
      [37.4893765, 127.0611214],
      [37.4889255, 127.0592419],
      [37.4875859, 127.0564319],
      [37.4907562, 127.0554966],
      [37.5045202, 127.0490088],
      [37.5098949, 127.0665209],
      [37.5103033, 127.068888],
      [37.5061619, 127.0693789]
    ]
  ],
  "cortarNo": "1168010600",
  "cortarName": "대치동",
  "cityName": "서울시",
  "divisionName": "강남구",
  "sectorName": "대치동",
  "cityNo": "1100000000",
  "divisionNo": "1168000000",
  "sectorNo": "1168010600",
  "cortarType": "sec",
  "centerLat": 37.49911,
  "centerLon": 127.065463,
  "cortarZoom": 15
}
```

---

## 5. 크롤러 구현 권장 사항

### 5.1 크롤러 타입
- **권장**: `StaticCrawler` (requests 기반)
- **이유**:
  - API가 JSON 형태로 제공
  - 동적 렌더링 불필요
  - Playwright보다 빠르고 가볍고 안정적

### 5.2 구현 단계

**Phase 1: 구/동 목록 수집**
```python
1. GET /api/regions/list?cortarNo=1100000000
   → 서울시 25개 구 목록 저장

2. For each 구:
   GET /api/regions/list?cortarNo={구의cortarNo}
   → 해당 구의 동 목록 저장

3. CSV 저장:
   - 컬럼: cortarNo, cortarName, centerLat, centerLon, cortarType,
           divisionName(구명), cityName(시명)
```

**Phase 2: 경계 좌표 수집 (선택적)**
```python
1. Phase 1에서 수집한 동 목록 로드

2. For each 동:
   GET /api/cortars?zoom=15&centerLat={동의centerLat}&centerLon={동의centerLon}
   → cortarVertexLists 저장

3. JSON 또는 GeoJSON 형태로 저장
   - 폴리곤 데이터는 CSV보다 JSON이 적합
```

### 5.3 에러 처리

```python
- 네트워크 에러: 3회 재시도 (exponential backoff)
- Rate limit: 429 응답 시 1분 대기 후 재시도
- 빈 응답: 로그 기록 후 스킵 (일부 동은 경계 데이터 없을 수 있음)
```

### 5.4 데이터 검증

```python
- cortarNo: 10자리 숫자 확인
- centerLat: 37.4 ~ 37.7 범위 (서울시)
- centerLon: 126.8 ~ 127.2 범위 (서울시)
- cortarType: "dvsn" 또는 "sec"만 허용
- cortarVertexLists: 최소 3개 이상의 좌표 쌍
```

### 5.5 출력 형식

**regions_seoul.csv**:
```csv
cortarNo,cortarName,centerLat,centerLon,cortarType,divisionName,cityName
1168000000,강남구,37.517408,127.047313,dvsn,,서울시
1168010300,개포동,37.482968,127.0634,sec,강남구,서울시
1168010800,논현동,37.513583,127.031375,sec,강남구,서울시
...
```

**regions_bounds_seoul.json** (선택적):
```json
{
  "1168010600": {
    "cortarNo": "1168010600",
    "cortarName": "대치동",
    "divisionName": "강남구",
    "cityName": "서울시",
    "centerLat": 37.49911,
    "centerLon": 127.065463,
    "bounds": [
      [37.5061619, 127.0693789],
      [37.5027424, 127.069802],
      ...
    ]
  },
  ...
}
```

---

## 6. 핵심 요약

### 6.1 데이터 추출 방법
1. **구 목록**: `GET /api/regions/list?cortarNo=1100000000`
2. **동 목록**: `GET /api/regions/list?cortarNo={구의cortarNo}` (25번 반복)
3. **경계 좌표**: `GET /api/cortars?zoom=15&centerLat={lat}&centerLon={lon}` (선택적)

### 6.2 주요 발견 사항
- ✅ **API 기반 접근 가능**: Playwright 없이 requests만으로 충분
- ✅ **구조화된 JSON 응답**: 파싱 간단
- ✅ **법정동 코드 제공**: cortarNo로 고유 식별 가능
- ✅ **중심 좌표 제공**: 지도 표시 및 bounds 조회에 활용
- ✅ **경계 좌표 제공**: 폴리곤 형태로 지역 범위 시각화 가능
- ⚠️ **Rate limiting 존재**: 요청 간 0.5~1초 대기 권장

### 6.3 권장 크롤링 전략
- **크롤러**: StaticCrawler (requests)
- **Rate limiting**: 500ms~1000ms 대기
- **재시도**: 3회 (exponential backoff)
- **출력**: CSV (목록) + JSON (경계 좌표)
- **검증**: cortarNo 형식, 좌표 범위 체크

---

## 7. 참고 사항

### 7.1 서울시 통계
- **총 구 개수**: 25개
- **총 동 개수**: 약 424개 (구별 차이 큼)
- **동 개수 분포**:
  - 최소: 세종시 (행정동 기준, 서울 아님)
  - 최대: 종로구 (87개 법정동)
  - 평균: 약 17개/구

### 7.2 cortarNo 패턴
```
서울시:    1100000000
├─ 강남구: 1168000000
│  ├─ 개포동: 1168010300
│  ├─ 논현동: 1168010800
│  └─ ...
├─ 송파구: 1171000000
│  ├─ 잠실동: 1171010100
│  └─ ...
└─ ...
```

### 7.3 좌표계
- **좌표계**: WGS84 (위도/경도)
- **위도 범위** (서울시): 37.4 ~ 37.7
- **경도 범위** (서울시): 126.8 ~ 127.2

---

## 8. 다음 단계

1. ✅ **지역 정보 크롤러 구현** (이 문서 기반)
2. 매물 정보 크롤러 구현 (별도 문서 참조)
3. 데이터 통합 및 검증
4. 스케줄러 구현 (정기 업데이트)

---

**문서 버전**: 1.0
**최종 업데이트**: 2025-12-04
