# 네이버 부동산 단지 상세 정보 API 탐색 결과

## 개요

네이버 부동산 모바일 사이트에서 단지 상세 정보를 가져오는 API 엔드포인트들을 탐색하고 분석한 결과입니다.

## 기본 정보

- **기본 URL**: `https://fin.land.naver.com`
- **API Prefix**: `/front-api/v1/complex/`
- **단지 ID 파라미터**: `complexNumber` (예: 111515 - 헬리오시티)
- **평형 타입 파라미터**: `pyeongTypeNumber` (예: 19 - 110D㎡)

## 주요 API 엔드포인트

### 1. 건물 평형 정보 API

```http
GET /front-api/v1/complex/building/pyeongList?complexNumber={complexNumber}
```

**파라미터**:
- `complexNumber`: 단지 번호 (필수)

**응답 구조**:
```json
{
  "isSuccess": true,
  "result": {
    "1": [
      {
        "buildingNumber": 3,
        "buildingName": "103"
      }
      // ... 더 많은 건물 정보
    ],
    "2": [...],
    // ... 평형별 건물 목록 (1-30까지의 평형 타입)
  }
}
```

### 2. 보유세 정보 API

```http
GET /front-api/v1/complex/holdingTax?complexNumber={complexNumber}&pyeongTypeNumber={pyeongType}
```

**파라미터**:
- `complexNumber`: 단지 번호 (필수)
- `pyeongTypeNumber`: 평형 타입 번호 (필수)

**응답 구조**:
```json
{
  "isSuccess": true,
  "result": {
    "min": {
      "propertyTax": {
        "propertyTax": 1974600,
        "localEducationTax": 394920,
        "urbanAreaSegmentTax": 911610,
        "complexAppraisedValueOfLandBaseDate": "2025-01-01"
      },
      "totalRealEstateTax": {
        "totalRealEstateTax": 474240,
        "ruralSpecialTax": 94848,
        "complexAppraisedValueOfLandBaseDate": "2025-01-01"
      }
    },
    "max": { /* 최대 세금 정보 */ }
  }
}
```

### 3. 공시가격 정보 API

```http
GET /front-api/v1/complex/declaredValue/pyeongType?complexNumber={complexNumber}&pyeongTypeNumber={pyeongType}
```

**응답 구조**:
```json
{
  "isSuccess": true,
  "result": {
    "baseDate": "2025-01-01",
    "priceList": [
      1447000000,
      1469000000,
      // ... 호별 공시가격 목록
    ],
    "minPrice": 1447000000,
    "maxPrice": 1663000000
  }
}
```

### 4. 매물 가격 분포 API

```http
GET /front-api/v1/complex/askingPrice?complexNumber={complexNumber}&pyeongTypeNumber={pyeongType}&realEstateType=A01&tradeType=A1
```

**파라미터**:
- `complexNumber`: 단지 번호
- `pyeongTypeNumber`: 평형 타입 번호
- `realEstateType`: 부동산 유형 (A01: 아파트)
- `tradeType`: 거래 유형 (A1: 매매)

**응답 구조**:
```json
{
  "isSuccess": true,
  "result": {
    "priceAxisSectionCount": 10,
    "priceAxis": [
      [2850000000, 2894000000],
      // ... 가격 구간별 데이터
    ],
    "priceCountsBySection": [15, 10, 16, 27, 13, 8, 2, 6, null, 2],
    "maxCount": 27,
    "minPrice": 2850000000,
    "maxPrice": 3300000000,
    "totalCount": 99
  }
}
```

### 5. 실거래가 요약 정보 API

```http
GET /front-api/v1/complex/pyeong/realPrice/summary?complexNumber={complexNumber}&pyeongTypeNumber={pyeongType}&realEstateType=A01&tradeType=A1
```

**응답 구조**:
```json
{
  "isSuccess": true,
  "result": {
    "minPrice": {
      "tradeDate": "2023-01-04",
      "tradeYear": "2023",
      "floor": 1,
      "dealPrice": 1530000000,
      "tradeCategory": "중개거래"
    },
    "maxPrice": {
      "tradeDate": "2025-11-01",
      "tradeYear": "2025",
      "floor": 18,
      "dealPrice": 3040000000,
      "tradeCategory": "중개거래"
    },
    "avgPrice": 2180670000,
    "startDate": "2022-12-06"
  }
}
```

### 6. 시세 정보 API (부동산 기관별)

```http
GET /front-api/v1/complex/marketPrice/recent?complexNumber={complexNumber}&pyeongTypeNumber={pyeongType}&realEstateType=A01&cpList[]=kab&cpList[]=kbstar
```

**응답 구조**:
```json
{
  "isSuccess": true,
  "result": [
    {
      "cp": "kab",
      "realtors": [
        {
          "name": "삼천공인중개사사무소",
          "telephoneNumber": "02-407-3000"
        }
      ],
      "baseDate": "2025-12-01",
      "dealPriceRange": {
        "ceiling": 3000000000,
        "floor": 2600000000
      },
      "dealAveragePrice": 2800000000,
      "depositPriceRange": {
        "ceiling": 1250000000,
        "floor": 1080000000
      }
    }
  ]
}
```

### 7. VR 정보 API

```http
GET /front-api/v1/complex/vr/representativeSameType?pyeongTypeNumber={pyeongType}&complexNumber={complexNumber}
```

**응답 구조**:
```json
{
  "isSuccess": true,
  "result": [
    {
      "complexNumber": 111515,
      "complexName": "헬리오시티",
      "sizeInfo": {
        "supplySpace": 110.1,
        "exclusiveSpace": 84.99,
        "pyeongTypeNumber": 19,
        "pyeongTypeName": "110D",
        "nameType": "D"
      },
      "representativeVRThumbnail": "https://landthumb-phinf.pstatic.net/...",
      "representativeArticleNumber": "1024062410",
      "representativeVRUrl": "https://fin.land.naver.com/articles/1024062410/tour"
    }
  ]
}
```

## 주요 파라미터 설명

### complexNumber
- 단지 고유 번호
- 예시: 111515 (헬리오시티)

### pyeongTypeNumber
- 평형 타입 고유 번호
- 예시:
  - 19: 110D㎡ (84.99평)
  - 1-30까지 다양한 평형 타입 존재

### realEstateType
- A01: 아파트
- 기타 유형 추가 가능

### tradeType
- A1: 매매
- B1: 전세
- B2: 월세

### cpList
- 시세 정보 제공 기관
- kab: 한국감정원
- kbstar: KB부동산

## 특이사항

1. **인증 필요**: 모든 API는 브라우저 컨텍스트 내에서 호출해야 함
2. **도메인**: `fin.land.naver.com` 도메인에서만 API 호출 가능
3. **JSON 응답**: 모든 API는 JSON 형식으로 응답
4. **파라미터 인코딩**: cpList와 같은 배열 파라미터는 URL 인코딩 필요 (cpList%5B%5D=kab)

## 활용 방안

이 API들을 활용하여 다음과 같은 정보를 크롤링할 수 있습니다:
- 단지별 평형 정보 및 건물 목록
- 호별 공시가격 정보
- 보유세 계산 정보
- 실거래가 통계 (최저/최고/평균)
- 현재 매물 가격 분포
- 부동산 기관별 시세 정보
- VR 투어 정보

## 제약 사항

- 직접적인 API 호출은 차단될 수 있으며, Playwright와 같은 브라우저 자동화 도구 필요
- Rate limiting 적용 가능성 있음
- 네이버 부동산의 정책에 따라 API 엔드포인트 변경 가능성