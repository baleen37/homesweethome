# 네이버 부동산 크롤링 최종 분석 및 권장 방법

## 실행 요약

네이버 부동산 페이지에서 단지 정보를 추출하는 세 가지 방법을 테스트한 결과, **Playwright MCP의 `browser_evaluate`를 통한 API 직접 호출 방식**이 가장 효과적인 것으로 확인되었습니다.

## 테스트 결과

### 1. Playwright MCP 설정 및 기본 동작 확인 ✅

- Playwright MCP가 정상적으로 작동함을 확인
- 브라우저를 통한 페이지 로드 및 DOM 접근 가능

### 2. browser_network_requests를 통한 API 캡처 ⚠️

**결과**: API URL은 캡처되지만 응답 본문(response body)은 제공되지 않음

```
[GET] https://new.land.naver.com/api/complexes/single-markers/2.0?cortarNo=1154510200&zoom=17&... => [200]
```

**제한 사항**:
- URL과 상태 코드만 제공
- 실제 데이터를 읽을 수 없음
- 네트워크 트래픽 모니터링 용도로만 유용

### 3. browser_evaluate + fetch()를 통한 API 직접 호출 ✅

**결과**: API를 직접 호출하여 완전한 JSON 데이터 획득 성공

**테스트 결과**:
```javascript
{
  "totalCount": 26,
  "firstItem": {
    "markerId": "149239",
    "markerType": "COMPLEX",
    "latitude": 37.458919,
    "longitude": 126.898166,
    "complexName": "W컨템포287(도시형)",
    "realEstateTypeCode": "APT",
    "realEstateTypeName": "아파트",
    "completionYearMonth": "202403",
    "totalDongCount": 1,
    "totalHouseholdCount": 151,
    "floorAreaRatio": 499,
    "minArea": "70.79",
    "maxArea": "78.25",
    "priceCount": 0,
    "representativeArea": 0,
    "isPresales": false,
    "photoCount": 0,
    "dealCount": 0,
    "leaseCount": 0,
    "rentCount": 0,
    "shortTermRentCount": 0,
    "totalArticleCount": 0,
    "existPriceTab": false,
    "isComplexTourExist": false
  }
}
```

**획득 가능한 필드** (24개):
- `markerId`, `markerType`, `latitude`, `longitude`
- `complexName`, `realEstateTypeCode`, `realEstateTypeName`
- `completionYearMonth`, `totalDongCount`, `totalHouseholdCount`
- `floorAreaRatio`, `minArea`, `maxArea`
- `priceCount`, `representativeArea`, `isPresales`
- `photoCount`, `dealCount`, `leaseCount`, `rentCount`
- `shortTermRentCount`, `totalArticleCount`, `existPriceTab`
- `isComplexTourExist`

## 접근 방식 비교

| 구분 | Selector 방식 (DOM) | browser_network_requests | browser_evaluate + fetch() |
|------|---------------------|--------------------------|----------------------------|
| **구현 난이도** | 높음 | 낮음 | 중간 |
| **데이터 완전성** | 제한적 | 없음 (URL만) | 완전 |
| **유지보수성** | 낮음 (DOM 변경에 취약) | 높음 | 높음 |
| **성능** | 느림 (렌더링 필요) | 빠름 | 빠름 |
| **오류 가능성** | 높음 (셀렉터 변경) | 낮음 | 낮음 |
| **데이터 구조화** | 필요 (파싱 후 변환) | 불가능 | 불필요 (JSON 직접 획득) |
| **실제 사용 가능성** | ⚠️ 제한적 | ❌ 불가능 | ✅ 가능 |

### 1. Selector 방식 (DOM 파싱)

**장점**:
- 페이지에 표시되는 모든 시각적 정보 접근 가능
- 추가 API 분석 불필요

**단점**:
- DOM 구조 변경 시 셀렉터 수정 필요
- 복잡한 CSS 셀렉터 또는 XPath 필요
- 데이터가 시각적으로 표현된 형태로 제공 (예: "2,236만", "4.6억")
- 파싱 및 정규화 로직 필요
- 성능 저하 (렌더링 대기 필요)
- 네이버 부동산은 지도에 마커로 표시되므로 접근성 스냅샷으로는 단지명 추출이 어려움

**적용 상황**:
- API가 제공하지 않는 추가 시각적 정보 필요 시
- API 접근이 완전히 차단된 경우

### 2. browser_network_requests 방식

**장점**:
- API URL 및 엔드포인트 발견에 유용
- 네트워크 트래픽 모니터링 가능

**단점**:
- **응답 본문(response body)을 제공하지 않음**
- URL과 상태 코드만 제공
- 실제 데이터 추출 불가능

**적용 상황**:
- API 엔드포인트 분석 및 디버깅
- 네트워크 요청 모니터링
- **실제 데이터 추출 용도로는 부적합**

### 3. browser_evaluate + fetch() 방식 (권장) ✅

**장점**:
- 완전한 구조화된 JSON 데이터 직접 획득
- API가 제공하는 모든 필드 접근 가능 (24개 필드)
- 파싱 로직 불필요
- 높은 성능 (직접 API 호출)
- DOM 구조 변경에 영향 받지 않음
- 데이터 타입이 명확 (문자열, 숫자, 불리언)
- 유지보수 용이

**단점**:
- 브라우저 컨텍스트에서 실행되어야 함 (쿠키/세션 필요)
- API URL 파라미터 분석 필요
- API가 변경될 가능성 (하지만 DOM보다는 안정적)

**적용 상황**:
- **대부분의 크롤링 작업에 권장**
- 구조화된 데이터가 필요한 경우
- 성능과 안정성이 중요한 경우

## 최종 권장 방법

### 권장: browser_evaluate + fetch() 방식

**이유**:
1. **완전한 데이터 획득**: 24개의 구조화된 필드 접근
2. **높은 안정성**: DOM 변경에 영향 받지 않음
3. **우수한 성능**: 직접 API 호출로 빠른 응답
4. **유지보수 용이**: JSON 구조 변경이 DOM 변경보다 드묾
5. **데이터 품질**: 정확한 타입과 값 (파싱 오류 없음)

## 구현 예시

### browser_evaluate를 통한 API 호출

```javascript
async () => {
  const apiUrl = 'https://new.land.naver.com/api/complexes/single-markers/2.0?' +
    'cortarNo=1154510200&' +
    'zoom=17&' +
    'priceType=RETAIL&' +
    'realEstateType=APT%3APRE&' +
    'tradeType=A1&' +
    'leftLon=126.8828998&' +
    'rightLon=126.9031774&' +
    'topLat=37.4626995&' +
    'bottomLat=37.4558608&' +
    'isPresale=true';

  const response = await fetch(apiUrl);
  const data = await response.json();

  return data;
}
```

## 구현 시 고려사항

### 1. API URL 파라미터

**필수 파라미터**:
- `cortarNo`: 지역 코드 (예: 1154510200 = 서울시 금천구 독산동)
- `zoom`: 지도 줌 레벨
- `leftLon`, `rightLon`, `topLat`, `bottomLat`: 지도 경계 좌표
- `realEstateType`: 매물 유형 (APT, APT:PRE 등)
- `tradeType`: 거래 유형 (A1 = 매매)

**선택 파라미터**:
- `priceType`: 가격 표시 유형
- `priceMin`, `priceMax`: 가격 범위
- `areaMin`, `areaMax`: 면적 범위
- `isPresale`: 분양 여부

### 2. 페이지 로드 및 쿠키

- 페이지를 먼저 로드하여 필요한 쿠키 및 세션 획득
- `browser_navigate`로 페이지 로드 후 `browser_evaluate` 실행

### 3. 지역 코드 획득

두 가지 방법:
1. URL의 `ms` 파라미터에서 좌표 추출 후 cortarNo API 호출
2. 브라우저에서 지역 선택 후 네트워크 요청에서 cortarNo 추출

### 4. 에러 처리

- API 응답 상태 코드 확인
- 빈 결과 처리
- 네트워크 오류 처리

### 5. 데이터 저장

- JSON 데이터를 CSV로 변환 시 필드 매핑 필요
- 숫자 필드는 그대로 사용 가능 (파싱 불필요)
- 날짜 필드는 "YYYYMM" 형식으로 제공

## 구현 아키텍처 제안

```
1. 페이지 로드 (browser_navigate)
   ↓
2. 지역 코드 획득 (cortarNo API 또는 URL 파라미터)
   ↓
3. API 호출 (browser_evaluate + fetch)
   ↓
4. JSON 데이터 추출
   ↓
5. CSV 변환 및 저장
```

## 결론

네이버 부동산 크롤링을 위해 **Playwright MCP의 `browser_evaluate`를 통한 API 직접 호출 방식**을 권장합니다. 이 방식은 완전한 데이터 획득, 높은 안정성, 우수한 성능을 제공하며, DOM 파싱 방식보다 유지보수가 훨씬 용이합니다.

`browser_network_requests`는 API 엔드포인트 발견에는 유용하지만, 응답 본문을 제공하지 않으므로 실제 데이터 추출에는 사용할 수 없습니다.
