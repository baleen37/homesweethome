# 네이버 부동산 API 네트워크 분석 결과

## 개요

실제 브라우저(Playwright)를 통한 네트워크 요청 캡처 및 분석 결과를 정리한 문서입니다.
이 분석은 `https://m.land.naver.com/` 및 `https://fin.land.naver.com/` 모바일/PC 페이지를 기반으로 수행되었습니다.

**수행일**: 2025-12-07
**분석 방법**: Playwright 브라우저 자동화를 통한 실제 API 호출 캡처

## 주요 발견 사항

### 1. 이중 API 구조 확인

실제 분석 결과, 네이버 부동산은 이중 API 구조를 운영하고 있습니다:

- **기존 API (여전히 사용 가능)**: `https://m.land.naver.com/cluster/ajax/*`
  - 단지 목록, 상세 정보, 매물 목록 등 기본 기능 제공
  - 인증 없이 기본 데이터 접근 가능

- **신규 API (Next.js 기반)**: `https://fin.land.naver.com/front-api/v1/*`
  - 개인화 기능, 최신 기능 제공
  - 일부 기능은 로그인 필요
  - Next.js SSR/CSR 아키텍처 기반

### 2. API 상세 분석

#### 활성화된 엔드포인트 목록

**기존 API (m.land.naver.com)**
- ✅ `/cluster/ajax/complexList` - 단지 목록 조회
- ✅ `/cluster/ajax/articleList` - 매물 목록 조회
- ❌ `/cluster/ajax/complexDetail` - 단지 상세 (404 에러)

**신규 API (fin.land.naver.com)**
- ✅ `/front-api/v1/favorite/recentComplex` - 최근 본 단지
- ✅ `/front-api/v1/legalDivision/infoListByLevel` - 법정동 정보
- ❌ `/front-api/v1/user/recommendArticleVR` - 추천 매물 (401 에러)
- ❌ `/front-api/v1/user/recentView` - 최근 조회 (401 에러)

### 3. 인증 정책

- **기본 데이터**: 인증 없이 접근 가능
- **개인화 기능**: 로그인 필요 (401 에러 반환)
- **Rate Limiting**: 적용됨 (약 5초 간격 권장)
- **User-Agent**: 모바일 User-Agent 사용 시 더 안정적

## API 상세 목록

### 기존 API (m.land.naver.com)

#### 1. 단지 목록 조회

```http
GET /cluster/ajax/complexList
```

**필수 파라미터:**
- `cortarNo`: 법정동 코드 (예: 1168010500 - 강남구 대치동)
- `rletTypeCd`: 매물 유형 (APT: 아파트)
- `hscpTypeCd`: 주상복합 유형 (3: 주상복합)
- `order`: 정렬 순서 (prc: 가격순)

**응답 구조:**
```json
{
  "result": [
    {
      "complexNo": "단지번호",
      "complexName": "단지명",
      "sidoNm": "시도명",
      "gugunNm": "구군명",
      "dongNm": "동명",
      "priceInfo": {
        "pAvg": "평균가격",
        "pMax": "최고가격",
        "pMin": "최저가격"
      }
    }
  ],
  "hasPaidPreSale": false,
  "more": false,
  "isPreSale": false
}
```

#### 2. 매물 목록 조회

```http
GET /cluster/ajax/articleList
```

**필수 파라미터:**
- `complexNo`: 단지 번호
- `tradTpCd`: 거래 유형 (A1: 매매, B1: 전세, B2: 월세)
- `page`: 페이지 번호

**응답 구조:**
```json
{
  "code": "success",
  "hasPaidPreSale": false,
  "more": false,
  "TIME": false,
  "z": 0,
  "page": 1,
  "body": [
    {
      "articleNo": "매물번호",
      "floorInfo": "층 정보",
      "dealOrWarrantPrc": "가격",
      "tradeTypeName": "거래유형명",
      "direction": "방향",
      "area1": "전용면적",
      "representativeFloor": "대표층"
    }
  ]
}
```

#### 3. 단지 상세 정보

```http
GET /cluster/ajax/complexDetail
```

**참고:** 현재 404 에러 반환 - 기능 이전 또는 폐기 가능성

### 신규 API (fin.land.naver.com)

#### 1. 최근 본 단지

```http
GET /front-api/v1/favorite/recentComplex
```

**파라미터:**
- `legalDivisionNumber`: 법정동 코드

#### 2. 법정동 정보

```http
GET /front-api/v1/legalDivision/infoListByLevel
```

**파라미터:**
- `regionLevelType`: 지역 레벨 (SI: 시/도)

#### 3. 추천 매물

```http
GET /front-api/v1/user/recommendArticleVR
```

**참고:** 401 에러 - 로그인 필요

## 요청 헤더

### 기본 헤더

```http
Accept: application/json, text/plain, */*
Accept-Language: ko-KR,ko;q=0.9
User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.15
X-Requested-With: XMLHttpRequest
```

### 선택적 헤더

```http
Referer: https://m.land.naver.com/  # 기존 API
Referer: https://fin.land.naver.com/  # 신규 API
```

## 캡처된 실제 요청 예시

### 성공적인 API 호출 예시

```http
GET /cluster/ajax/complexList?cortarNo=1168010500&rletTypeCd=APT&hscpTypeCd=3&order=prc&sp=0&hsp=0&a=&b=&c=&k=false&l=&e=false&t=&demo=false&an=&at=&ac=&ad=&ae=&_=1765080301234
Host: m.land.naver.com
User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.15
Accept: application/json, text/plain, */*
Accept-Language: ko-KR,ko;q=0.9
Referer: https://m.land.naver.com/
X-Requested-With: XMLHttpRequest
```

### 실패하는 API 호출 예시 (401 에러)

```http
GET /front-api/v1/user/recommendArticleVR
Host: fin.land.naver.com
User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.15
Accept: application/json, text/plain, */*
Referer: https://fin.land.naver.com/?content=recent
```

## 데이터 로딩 패턴

### 1. 페이지 초기 로딩 시

1. SSR(Server-Side Rendering) 데이터 포함
2. 클라이언트 사이드에서 추가 API 호출
3. 병렬로 여러 API 동시 호출

### 2. 사용자 상호작용 시

1. 탭 전환 시 관련 API 호출
2. 필터 변경 시 파라미터 업데이트 후 재호출
3. 무한 스크롤 방식으로 추가 데이터 로드

## Rate Limiting

- 최소 요청 간격: 5초
- 429 응답 시 2배로 지연 시간 증가
- 최대 지연 시간: 60초

## 에러 처리

### 일반적인 에러 형식

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "에러 메시지"
  }
}
```

### 주요 에러 코드

- `RATE_LIMIT_EXCEEDED`: 요청 초과
- `COMPLEX_NOT_FOUND`: 단지 없음
- `AUTHENTICATION_REQUIRED`: 로그인 필요
- `INTERNAL_SERVER_ERROR`: 서버 오류

## 캐싱 전략

### 클라이언트 사이드 캐싱

- 단지 기본 정보: 30분
- 실거래가 데이터: 1시간
- 시세 정보: 10분

### HTTP 캐싱 헤더

```http
Cache-Control: max-age=600
ETag: "..."
Last-Modified: "..."
```

## 구현 가이드

### 1. API 클라이언트 구현 시 고려사항

1. **세션 관리**: 쿠키 유지 필요
2. **User-Agent**: 모바일 User-Agent 사용 권장
3. **Referer**: `https://fin.land.naver.com/` 설정
4. **Rate Limiting**: 자동 지연 기능 구현

### 2. 데이터 파싱 팁

1. **날짜 형식**: `YYYY.MM.DD` 또는 `YYYYMMDD`
2. **금액 형식**: 만 단위 숫자 (예: `25000` = 2억 5천)
3. **면적 형식**: 전용면적은 소수점 2자리

### 3. 안정성 확보 방법

1. **재시도 로직**: 최대 3회 재시도
2. **지수 백오프**: 실패 시 지연 시간 증가
3. **서킷 브레이커**: 연속 실패 시 일시 중단
4. **체크포인트**: 중단 지점부터 재시작

## 테스트 전략

### 1. 단위 테스트

- API 응답 구조 검증
- 데이터 파싱 로직 테스트
- 에러 처리 테스트

### 2. 통합 테스트

- 실제 API 호출 테스트
- Rate Limiting 테스트
- 인증 플로우 테스트

### 3. E2E 테스트

- 전체 크롤링 시나리오 테스트
- 대용량 데이터 처리 테스트
- 장시간 실행 안정성 테스트

## 주의사항

1. **서비스 약관**: 네이버 부동산의 약관을 준수해야 함
2. **상업적 이용**: 상업적 이용 시 사전 허가 필요
3. **데이터 저작권**: 데이터의 저작권은 네이버파이낸셜에 있음
4. **API 변경**: 사전 통보 없이 API가 변경될 수 있음

## 참고 자료

- [네이버 부동산 개발자 포털](https://developers.naver.com/products/land)
- [네이버 부동산 이용약관](https://fin.land.naver.com/terms)
- [테스트 코드 예시](../tests/unit/test_naver_api_client.py)