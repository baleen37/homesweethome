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

### 2. Rate Limiting 정책

- **권장 간격**: 1-2초
- **429 에러**: 너무 빠른 연속 호출 시 발생

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

## 주의사항

- API 호출 시 반드시 `X-Requested-With: XMLHttpRequest` 헤더 포함
- 600개 POI 제한을 피하기 위해 bbox 분할 필수
- 과도한 요청은 IP 차단 가능성이 있으므로 rate limiting 준수
- 일부 API는 로그인이 필요할 수 있음
- **aptHash vs aptId**: POI 조회 응답에는 `aptId` 필드가 없으며, `aptHash` 필드를 사용해야 함
- **응답 구조**: 실거래 API 응답은 `shortTermReport` 객체 또는 직접 배열로 올 수 있음
