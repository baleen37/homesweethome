# 네이버 부동산 매물지도 크롤링 구조 분석

## 문서 목적

이 문서는 네이버 부동산 매물지도(`https://fin.land.naver.com/regions`)를 **크롤링하기 위해 필요한 구조를 이해하고 참고**하기 위한 목적으로 작성되었습니다.

- 사이트의 계층적 구조 (시/도 → 구 → 동 → 단지)
- URL 패턴 및 파라미터
- 페이지별 데이터 구조 및 DOM 파싱 방법
- 크롤링 구현을 위한 기술적 접근 방법

## 개요

네이버 부동산 매물지도는 지역별 아파트 시세 및 매물 정보를 제공하는 서비스입니다. 직접 API 접근이 차단되어 있어 **브라우저 기반 크롤링**이 필요합니다.

**주요 발견사항:**
- 브라우저 내에서 호출되는 내부 API 다수 발견
- Playwright를 통해 API 직접 호출 가능
- DOM 파싱과 API 호출 하이브리드 접근 권장

---

## 1. 사이트 구조

### 1.1 계층적 지역 선택 구조

네이버 부동산은 3단계 계층 구조로 지역을 선택합니다:

```
시/도 선택 → 시/군/구 선택 → 읍/면/동 선택 → 단지 목록
```

#### 단계별 URL 패턴

| 단계 | URL 패턴 | 예시 |
|------|----------|------|
| 1. 시/도 선택 | `/regions` | `https://fin.land.naver.com/regions` |
| 2. 시/군/구 선택 | `/regions?si={시도코드}` | `/regions?si=1100000000` (서울) |
| 3. 읍/면/동 선택 | `/regions?si={시도코드}&gun={구코드}` | `/regions?si=1100000000&gun=1168000000` (강남구) |
| 4. 단지 목록 | `/regions?si={시도코드}&gun={구코드}&eup={동코드}` | `/regions?si=1100000000&gun=1168000000&eup=1168010100` (역삼동) |

#### 지역 코드 체계

- **시/도 코드**: 10자리 숫자 (예: `1100000000` = 서울시)
- **구 코드**: 10자리 숫자 (예: `1168000000` = 강남구)
- **동 코드**: 10자리 숫자 (예: `1168010100` = 역삼동)

**실제 확인된 코드:**
```
서울특별시: 1100000000
├── 강남구: 1168000000
│   └── 역삼동: 1168010100
```

### 1.2 단지 정보 구조

각 동(읍/면/동) 페이지에는 해당 지역의 아파트/오피스텔 단지 목록이 표시됩니다.

#### 단지 목록 정보

```yaml
- 단지명: 역삼래미안
- 단지 타입: 아파트 / 오피스텔 (코드: A01/A02)
- 세대수: 1,050세대
- 준공년월: 2005. 10. (21년차)
- 매물 수:
  - 매매: 26건
  - 전세: 28건
  - 월세: 51건
  - 단기: 5건
- 단지 ID: 13814
- 단지 상세 URL: `/complexes/{단지ID}`
- VR 투어 여부: true/false
```

#### DOM 구조 및 CSS 클래스

**실제 확인된 CSS 선택자:**
```javascript
// 단지 목록 컨테이너
const complexList = document.querySelector('.RegionList_list__9GSMS');

// 각 단지 항목
const items = document.querySelectorAll('.ComplexItem_article__gnmoK');

// 단지별 정보 추출
items.forEach(item => {
  const name = item.querySelector('.ComplexItem_name__OusaI')?.textContent;
  const type = item.querySelector('.TitleBadge_article__dh89O')?.textContent;
  const infoItems = item.querySelectorAll('.ComplexItem_item-info__CvUkT');
  const households = infoItems[0]?.textContent; // "1,050세대"
  const completionDate = infoItems[1]?.textContent; // "2005. 10. (21년차)"
});
```

#### 정렬 옵션

- **세대수순** (HOUSEHOLD, 기본값)
- **가나다순** (NAME)
- **최근입주순** (COMPLETION)
- **매물많은순** (ARTICLE)

---

## 2. 단지 상세 페이지 구조

### 2.1 URL 패턴

```
https://fin.land.naver.com/complexes/{단지ID}?tab={탭}&articleTradeTypes={거래타입}&transactionPyeongTypeNumber={평형타입}
```

#### URL 파라미터

| 파라미터 | 값 | 설명 |
|----------|-----|------|
| `tab` | `transaction` | 시세/실거래 탭 |
|  | `article` | 매물 탭 |
|  | (기본값) | 단지정보 탭 |
| `articleTradeTypes` | `A1` | 매매 (복수 선택 시 쉼표로 구분: `A1,B1`) |
|  | `B1` | 전세 |
|  | `B2` | 월세 |
|  | `B3` | 단기임대 |
| `transactionPyeongTypeNumber` | `1`, `2`, ... | 시세/실거래 탭의 평형 타입 번호 |
| `articlePyeongTypeNumbers` | `1`, `2`, ... | 매물 탭의 평형 타입 번호 |

**주의사항:**
- 평형 선택 시 UI 버튼 클릭하면 URL 파라미터가 자동 변경됨
- 거래유형 변경 시 `transactionTradeType` 파라미터 추가됨 (예: `?tab=transaction&transactionTradeType=B1`)

### 2.2 시세/실거래 탭 (`tab=transaction`)

#### 수집 가능한 데이터

**1. 시세 정보**
- 시세 기준 제공처: 한국부동산원 / KB부동산
- 평형별 시세 호가 (상한가, 하한가)
- 최근 실거래가
- 3개월 평균 실거래가
- 시세 그래프 (1년/3년/5년/7년)

**2. 실거래가 정보**
- 계약일
- 등기일
- 층
- 가격
- 3년 내 최고가/최저가

**3. 대출 정보**
- 대출 한도 (LTV)
- 금리 정보 (은행별)

**4. 호별시세**
- 동/호수별 시세

**5. 매물 분포**
- 가격대별 매물 수

**6. 매매/전세 흐름**
- 갭 투자 정보
- 시간별 가격 추이

**7. 평당가 비교**
- 해당 아파트 vs 동 vs 구 vs 시 평균

**8. 보유세 정보**
- 공시가격
- 재산세
- 종합부동산세

### 2.3 매물 탭 (`tab=article`)

#### 필터 옵션

```yaml
거래유형:
  - 전체거래유형
  - 매매 (A1)
  - 전세 (B1)
  - 월세 (B2)
  - 단기임대 (B3)

면적:
  - 전체면적
  - 80.66㎡ (59평형)
  - 109㎡ (80평형)
  - ...

동:
  - 전체동
  - 101동
  - 102동
  - ...
```

#### 정렬 옵션

- 랭킹순 (기본값)
- 가격순
- 최신순
- 면적순

#### 매물 정보 구조

**기본 정보**
```yaml
매물 항목:
  - 단지명: 역삼래미안
  - 동: 104동
  - 거래타입: 매매 / 전세 / 월세 / 단기임대
  - 가격:
    - 단일 가격: 29억 2,000만원
    - 가격 범위: 29억 ~ 29억 8,000만원 (여러 중개사 등록 시)
    - 월세: 보증금/월세 (예: 6억/150만원)
    - 단기임대: 보증금/월세 (예: 500만원/480만원)
  - 매물타입: 아파트 / 오피스텔
  - 전용면적: 80㎡ (전용59평형)
  - 층: 4/22층 (현재층/전체층)
  - 층 구분: 저층/중층/고층 표시
  - 방향: 남향, 남동향, 남서향, 동향, 서향, 북서향 등
```

**소유 및 중개 정보**
```yaml
소유주 정보:
  - 소유주 타입: 집주인 / 중개사
  - 확인매물 날짜: 2025.12.04
  - 중개사 정보:
    - 단일 중개사: "래미안(단지내)공인중개사사무소"
    - 다중 등록: "중개사 33곳에서 등록했어요" (매물목록 펼치기 가능)
  - 매물 포털: "매경부동산", "한경부동산", "부동산뱅크", "선방", "부동산써브" 등
```

**추가 정보**
```yaml
특수 정보:
  - 매물 설명: "주인매물.보증금 5억 6억 가능합니다"
  - 이미지: "이미지 20개" (있는 경우만)
  - VR 투어: VR 가능 여부
  - 가격 변동:
    - "변동 하락내역 보기" 버튼
    - "변동 상승내역 보기" 버튼
  - 관심매물: 관심매물 등록 버튼
  - 매물 상세 URL:
    - 일반: /articles/{매물ID}
    - 외부 링크: /articles/{매물ID}/out-link-bridge?cpId={포털ID}
```

**매물 그룹화**
```yaml
그룹 매물 (여러 중개사가 동일 매물 등록):
  - 표시: "역삼래미안 104동 매매 29억 ~ 29억 8,000"
  - 중개사 수: "중개사 33곳에서 등록했어요"
  - 펼치기: "매물목록 펼치기" 버튼으로 개별 매물 확인 가능
  - 대표 정보만 표시: 아파트, 면적, 층, 방향, 확인매물 날짜
```

---

## 3. API 분석

### 3.1 API 접근 제한

직접 API 호출 시도 결과:

```
❌ https://fin.land.naver.com/api/regions/complexes?si=...&gun=...&eup=...
→ "Claude Code is unable to fetch from fin.land.naver.com"
```

**결론**: 네이버는 직접 API 접근을 차단하고 있으며, 브라우저를 통한 접근만 허용합니다.

### 3.2 발견된 API 엔드포인트 ⭐

브라우저에서 페이지를 로드할 때 다음 내부 API들이 호출됩니다. Playwright를 통해 브라우저 컨텍스트 내에서 직접 호출 가능합니다.

#### A. 단지 목록 API

**1. 단지 목록 조회 API**
```
GET /front-api/v1/complex/region
  ?eupLegalDivisionNumber=1168010100
  &size=30
  &sortType=HOUSEHOLD
  &page=0
```

**응답 구조:**
```json
{
  "isSuccess": true,
  "result": {
    "hasNextPage": true,
    "totalCount": 250,
    "list": [
      {
        "complexInfo": {
          "complexNumber": 13814,
          "name": "역삼래미안",
          "type": "A01",
          "totalHouseholdNumber": 1050,
          "useApprovalDate": "20051026",
          "approvalElapsedYear": 21
        },
        "articleCountInfo": {
          "dealCount": 26,
          "leaseDepositCount": 28,
          "leaseMonthlyCount": 51,
          "leaseShortTerm": 5
        },
        "isComplexTourExist": true
      }
    ]
  }
}
```

#### B. 시세/실거래 API

**2. 실거래가 조회 API**
```
GET /front-api/v1/complex/pyeong/realPrice
  ?complexNumber=13814
  &tradeType=A1
  &pyeongTypeNumber=1
  &page=1
  &size=3
```

**3. 실거래가 요약 API**
```
GET /front-api/v1/complex/pyeong/realPrice/summary
  ?complexNumber=13814
  &pyeongTypeNumber=1
  &realEstateType=A01
  &tradeType=A1
```

**4. 시세 정보 API**
```
GET /front-api/v1/complex/marketPrice/list
  ?complexNumber=13814
  &pyeongTypeNumber=1
  &startDate=2024-12-04
  &endDate=2025-12-04
  &cpList[]=kab
  &cpList[]=kbstar
```

**5. 최근 시세 API**
```
GET /front-api/v1/complex/marketPrice/recent
  ?complexNumber=13814
  &pyeongTypeNumber=1
  &realEstateType=A01
  &cpList[]=kab
  &cpList[]=kbstar
```

**6. 호가 정보 API**
```
GET /front-api/v1/complex/askingPrice
  ?complexNumber=13814
  &pyeongTypeNumber=1
  &realEstateType=A01
  &tradeType=A1
```

**7. 대출 정보 API**
```
GET /front-api/v1/loan/mortgage/ltvInfo
  ?legalDivisionNumber=1168010100
  &realEstateType=A01

GET /front-api/v1/loan/mortgage/kbPrice
  ?complexNumber=13814
  &pyeongTypeNumber=1

GET /front-api/v1/loan/mortgage/partnerProduct
  ?productTypes[]=LOAN-MORTGAGE
```

**8. 보유세 정보 API**
```
GET /front-api/v1/complex/holdingTax
  ?complexNumber=13814
  &pyeongTypeNumber=1

GET /front-api/v1/complex/declaredValue/pyeongType
  ?complexNumber=13814
  &pyeongTypeNumber=1
```

**9. 평형 정보 API**
```
GET /front-api/v1/complex/building/pyeongList
  ?complexNumber=13814
```

#### C. 매물 목록 API

**10. 매물 목록 조회 API (추정)**
```
POST /front-api/v1/complex/article/list

요청 Body (추정):
{
  "complexNumber": "13814",
  "tradeTypes": ["A1"],
  "sortType": "RANKING",
  "page": 0,
  "size": 30
}
```

### 3.3 API 활용 전략

**방법 1: Playwright 브라우저 컨텍스트에서 직접 호출 (권장)**
```typescript
import { chromium } from 'playwright';

async function fetchComplexData(complexNumber: string) {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  // 1. 페이지 먼저 방문 (세션/쿠키 획득)
  await page.goto(`https://fin.land.naver.com/complexes/${complexNumber}`);

  // 2. 브라우저 컨텍스트 내에서 API 호출
  const data = await page.evaluate(async (complexNum) => {
    const response = await fetch(
      `/front-api/v1/complex/pyeong/realPrice?complexNumber=${complexNum}&tradeType=A1&pyeongTypeNumber=1&page=1&size=100`
    );
    return await response.json();
  }, complexNumber);

  await browser.close();
  return data;
}
```

**방법 2: Response 인터셉트 (가장 안정적)**
```typescript
async function interceptAPIResponses(page: Page) {
  const apiData = [];

  page.on('response', async (response) => {
    const url = response.url();

    if (url.includes('/front-api/')) {
      const data = await response.json();
      apiData.push({ url, data });
      console.log(`API 호출 감지: ${url}`);
    }
  });

  // 페이지 탐색하면서 자동으로 API 호출 수집
  await page.goto('https://fin.land.naver.com/complexes/13814?tab=transaction');

  return apiData;
}
```

**방법 3: API 직접 호출 (쿠키 필요)**
```typescript
// 브라우저에서 쿠키 추출
const context = await browser.newContext();
const page = await context.newPage();
await page.goto('https://fin.land.naver.com/regions');

const cookies = await context.cookies();

// axios 등으로 직접 호출
const response = await axios.get(
  'https://fin.land.naver.com/front-api/v1/complex/region',
  {
    params: {
      eupLegalDivisionNumber: '1168010100',
      size: 30,
      sortType: 'HOUSEHOLD',
      page: 0
    },
    headers: {
      'Cookie': cookies.map(c => `${c.name}=${c.value}`).join('; '),
      'User-Agent': 'Mozilla/5.0...',
      'Referer': 'https://fin.land.naver.com/regions'
    }
  }
);
```

**주의사항:**
- API는 브라우저 세션 내에서만 동작 (직접 호출 시 쿠키 필요)
- Rate limiting 고려: 요청 간 500ms~1000ms 대기 권장
- 일부 API는 Referer 헤더 필수

### 3.4 데이터 로딩 방식

브라우저 렌더링 방식을 분석한 결과:

1. **Server-Side Rendering (SSR)**: 페이지 초기 로드 시 HTML에 데이터가 포함되어 있음
2. **Client-Side Rendering**: 추가 데이터는 JavaScript를 통해 동적으로 로드됨
3. **페이지별 로딩 방식**:

   **a) 단지 목록 페이지:**
   - "더보기" 버튼 방식
   - 버튼 클릭 시 다음 30개 로드
   - API: `GET /front-api/v1/complex/region?page=0,1,2...`

   **b) 매물 목록 페이지 (중요!):**
   - **무한 스크롤 방식**
   - 페이지 하단까지 스크롤 시 자동으로 추가 매물 로드
   - "더보기" 버튼 없음
   - 초기 30개 로드, 스크롤 시 30개씩 증가
   - **테스트 결과**: 110개 매물 전체 로드 확인 완료 ✅
   - API: `POST /front-api/v1/complex/article/list`

   **c) 시세/실거래 페이지:**
   - 초기 3~5개 표시
   - "실거래가 더보기" 버튼으로 전체 로드
   - API: `GET /front-api/v1/complex/pyeong/realPrice`

---

## 4. 크롤링 전략

### 4.1 기술 스택 선택

#### Playwright (권장)

**장점:**
- 실제 브라우저 환경에서 동작
- JavaScript 렌더링 지원
- 네이버의 봇 탐지 회피 용이
- API 인터셉트 및 직접 호출 가능
- TypeScript 지원 우수

**3가지 구현 방법:**

**1) API 직접 호출 (가장 빠름)**
```typescript
import { chromium } from 'playwright';

async function crawlViaAPI() {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  // 세션 획득
  await page.goto('https://fin.land.naver.com/regions');

  // API 직접 호출
  const data = await page.evaluate(async () => {
    const response = await fetch('/front-api/v1/complex/region?eupLegalDivisionNumber=1168010100&size=30&page=0');
    return await response.json();
  });

  await browser.close();
  return data;
}
```

**2) Response 인터셉트 (가장 안정적)**
```typescript
async function crawlViaIntercept() {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  const apiData = [];
  page.on('response', async (response) => {
    if (response.url().includes('/front-api/')) {
      apiData.push(await response.json());
    }
  });

  await page.goto('https://fin.land.naver.com/complexes/13814?tab=article');

  return apiData;
}
```

**3) DOM 파싱 (API 차단 시 대비)**
```typescript
async function crawlViaDOM() {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  await page.goto('https://fin.land.naver.com/regions?si=1100000000&gun=1168000000&eup=1168010100');

  const complexes = await page.evaluate(() => {
    const items = document.querySelectorAll('.ComplexItem_article__gnmoK');
    return Array.from(items).map(item => ({
      name: item.querySelector('.ComplexItem_name__OusaI')?.textContent,
      // ... 추가 정보
    }));
  });

  await browser.close();
  return complexes;
}
```

#### 하이브리드 접근 (권장 전략)

```typescript
async function crawlWithFallback() {
  try {
    // 1순위: API 직접 호출
    return await crawlViaAPI();
  } catch (error) {
    console.warn('API 호출 실패, DOM 파싱으로 전환:', error);
    // 2순위: DOM 파싱
    return await crawlViaDOM();
  }
}
```

### 4.2 크롤링 흐름도

```
[시작]
  ↓
[1. 시/도 목록 수집]
  - 방법 A: API 호출 (URL 직접 탐색하여 코드 추출)
  - 방법 B: DOM 파싱
  - 수집: 시/도명, 시/도 코드
  ↓
[2. 시/군/구 목록 수집 (각 시/도마다)]
  - URL: /regions?si={시도코드}
  - 수집: 구명, 구 코드
  ↓
[3. 읍/면/동 목록 수집 (각 구마다)]
  - URL: /regions?si={시도코드}&gun={구코드}
  - 수집: 동명, 동 코드
  ↓
[4. 단지 목록 수집 (각 동마다)] ⭐
  - 방법 A (권장): API 호출
    GET /front-api/v1/complex/region?eupLegalDivisionNumber={동코드}&page=0&size=30
  - 방법 B: DOM 파싱 + "더보기" 버튼 클릭
  - 수집: 단지명, 단지ID, 타입, 세대수, 준공연도, 매물 수, VR 여부
  ↓
[5. 단지 시세 정보 수집 (각 단지마다)] ⭐
  - 방법 A (권장): Response 인터셉트
    - 페이지 로드 시 자동으로 여러 API 호출됨
    - GET /front-api/v1/complex/pyeong/realPrice
    - GET /front-api/v1/complex/marketPrice/recent
    - GET /front-api/v1/complex/askingPrice 등
  - 방법 B: DOM 파싱 + "실거래가 더보기" 버튼 클릭
  - 수집: 시세, 실거래가, 대출정보, 보유세
  ↓
[6. 단지 매물 정보 수집 (각 단지마다)] ⭐
  - 방법 A (권장): API 직접 호출
    POST /front-api/v1/complex/article/list
  - 방법 B: DOM 파싱 + 무한 스크롤 (End 키 반복)
  - 수집: 매물 목록 (동, 층, 가격, 면적, 방향, 중개사 등)
  - 주의: 무한 스크롤 완료 확인 (3번 연속 변화 없음)
  ↓
[데이터 저장]
  - DB 또는 JSON 파일로 저장
  - 중복 제거 및 검증
  ↓
[종료]
```

### 4.3 DOM 파싱 전략

#### 단지 목록 페이지

**실제 확인된 CSS 선택자 사용:**

```typescript
// Playwright를 사용한 단지 목록 추출
async function parseComplexList(page: Page) {
  const complexes = await page.evaluate(() => {
    const items = document.querySelectorAll('.ComplexItem_article__gnmoK');

    return Array.from(items).map(item => {
      // 단지명
      const name = item.querySelector('.ComplexItem_name__OusaI')?.textContent?.trim();

      // 타입 (아파트/오피스텔)
      const type = item.querySelector('.TitleBadge_article__dh89O')?.textContent?.trim();

      // 세대수와 준공년월
      const infoItems = item.querySelectorAll('.ComplexItem_item-info__CvUkT');
      const households = infoItems[0]?.textContent?.trim(); // "1,050세대"
      const completionDate = infoItems[1]?.textContent?.trim(); // "2005. 10. (21년차)"

      // 매물 수 추출
      const tradeLinks = item.querySelectorAll('a[href*="article"]');
      const articleCounts = {
        A1: 0, // 매매
        B1: 0, // 전세
        B2: 0, // 월세
        B3: 0  // 단기
      };

      tradeLinks.forEach(link => {
        const text = link.textContent?.trim() || '';
        const match = text.match(/^(.*?)\s+(\d+)$/);
        if (match) {
          const [, type, count] = match;
          if (type === '매매') articleCounts.A1 = parseInt(count);
          else if (type === '전세') articleCounts.B1 = parseInt(count);
          else if (type === '월세') articleCounts.B2 = parseInt(count);
          else if (type === '단기') articleCounts.B3 = parseInt(count);
        }
      });

      // 단지 ID 추출
      const detailLink = item.querySelector('a[href*="/complexes/"]:not([href*="article"])');
      const complexId = detailLink?.getAttribute('href')?.match(/\/complexes\/(\d+)/)?.[1];

      // VR 투어 여부
      const hasVR = item.textContent?.includes('VR') || false;

      return {
        complexId: parseInt(complexId || '0'),
        name,
        type,
        households,
        completionDate,
        articleCounts,
        hasVR
      };
    });
  });

  return complexes;
}

// "더보기" 버튼 클릭하여 모든 단지 로드
async function loadAllComplexes(page: Page) {
  let hasMore = true;

  while (hasMore) {
    const moreButton = await page.locator('button:has-text("더보기")').first();

    if (await moreButton.isVisible()) {
      await moreButton.click();
      await page.waitForTimeout(1000); // 로딩 대기
    } else {
      hasMore = false;
    }
  }

  return parseComplexList(page);
}
```

#### 시세/실거래 페이지

**Playwright MCP 기반 DOM 파싱 방법**

```javascript
// 1. 페이지 접근
await browser_navigate(`https://fin.land.naver.com/complexes/${complexId}?tab=transaction&transactionPyeongTypeNumber=${pyeongType}&transactionTradeType=${tradeType}`);
const snapshot = await browser_snapshot();

// 2. 시세 요약 정보 추출
const priceListItems = snapshot
  .filter(el => el.role === 'listitem')
  .filter(el => el.textContent?.includes('최근 실거래') || el.textContent?.includes('3개월 평균'));

const recentPrice = priceListItems
  .find(el => el.textContent?.includes('최근 실거래'))
  .children.find(el => el.role === 'strong').textContent;

const avgPrice = priceListItems
  .find(el => el.textContent?.includes('3개월 평균'))
  .children.find(el => el.role === 'strong').textContent;

// 3. 시세호가 정보 (상한가/하한가)
const priceSection = snapshot.find(el =>
  el.textContent?.includes('시세호가')
);
const priceLists = priceSection.children
  .filter(el => el.role === 'list')
  .flatMap(list => list.children);

const maxPriceItem = priceLists.find(el => el.textContent?.includes('상한가'));
const minPriceItem = priceLists.find(el => el.textContent?.includes('하한가'));

// 4. 실거래가 테이블
const table = snapshot.find(el =>
  el.role === 'table' &&
  el.caption?.includes('실거래가')
);

// 헤더 파싱
const headerRow = table.children
  .find(el => el.role === 'rowgroup' && el.children[0].children.every(c => c.role === 'columnheader'));
const headers = headerRow.children[0].children
  .map(header => header.textContent);

// 데이터 행 파싱
const tbody = table.children
  .find(el => el.role === 'rowgroup' && el !== headerRow);

const transactions = tbody.children.map(row => {
  const cells = row.children.filter(el => el.role === 'cell');

  // 매매: [계약일, 등기일, 층, 가격]
  // 전세/월세: [계약일, 층, 가격] (등기일 없음)
  if (headers.length === 4) {
    return {
      contractDate: cells[0].textContent.trim(),
      registrationDate: cells[1].textContent.trim(),
      floor: cells[2].textContent.trim(),
      price: cells[3].textContent.trim().replace(/최고|최저/g, ''),
      isHighest: cells[3].textContent.includes('최고'),
      isLowest: cells[3].textContent.includes('최저'),
    };
  } else {
    return {
      contractDate: cells[0].textContent.trim(),
      registrationDate: null,
      floor: cells[1].textContent.trim(),
      price: cells[2].textContent.trim().replace(/최고|최저/g, ''),
      isHighest: cells[2].textContent.includes('최고'),
      isLowest: cells[2].textContent.includes('최저'),
    };
  }
});

// 5. "실거래가 더보기" 버튼 클릭하여 전체 데이터 로드
const moreButton = snapshot.find(el =>
  el.role === 'button' &&
  el.textContent?.includes('실거래가 더보기')
);
if (moreButton) {
  await browser_click(moreButton.element, moreButton.ref);
  // 추가 데이터 로드 후 다시 파싱
}

// 6. 평형타입 변경
const pyeongButton = snapshot.find(el =>
  el.role === 'button' &&
  el.textContent?.includes('㎡')
);
await browser_click(pyeongButton.element, pyeongButton.ref);

// 모달에서 평형 선택
const pyeongModal = snapshot.find(el =>
  el.heading?.includes('면적 선택')
);
const targetPyeong = pyeongModal.children
  .find(el => el.textContent?.includes('109.4㎡'));
await browser_click(targetPyeong.element, targetPyeong.ref);

// 7. 거래유형 변경
const tradeTypeButton = snapshot.find(el =>
  el.role === 'button' &&
  (el.textContent === '매매' || el.textContent === '전세' || el.textContent === '월세')
);
await browser_click(tradeTypeButton.element, tradeTypeButton.ref);

const tradeModal = snapshot.find(el =>
  el.heading?.includes('유형 선택')
);
const jeonseOption = tradeModal.children
  .find(el => el.textContent === '전세');
await browser_click(jeonseOption.element, jeonseOption.ref);
```

**실거래가 테이블 구조 차이**

| 거래유형 | 테이블 헤더 | 예시 데이터 | 특이사항 |
|---------|------------|-----------|---------|
| 매매 (A1) | 계약일, 등기일, 층, 가격 | "11.08.", "-", "8층", "29억" | 등기일 컬럼 존재 |
| 전세 (B1) | 계약일, 층, 가격 | "11.08.", "17층", "12억 1,800" | 등기일 컬럼 없음 |
| 월세 (B2) | 계약일, 층, 가격 | "11.08.", "17층", "6억/150" | 등기일 컬럼 없음 |

**URL 파라미터 자동 변경**

```
평형 변경: ?transactionPyeongTypeNumber=1 → ?transactionPyeongTypeNumber=5
거래유형 변경: ?transactionTradeType=A1 → ?transactionTradeType=B1
```

#### 매물 목록 페이지

**실제 확인된 CSS 선택자 사용:**

```typescript
// 매물 목록 추출
async function parseArticles(page: Page) {
  const articles = await page.evaluate(() => {
    const items = document.querySelectorAll('.ComplexArticleList_article__66N3p > li');

    return Array.from(items).map(item => {
      // 기본 정보
      const dongName = item.querySelector('.ArticleCard_name__3Nh_2')?.textContent?.trim();
      const price = item.querySelector('.ArticleCard_price__KBHz7')?.textContent?.trim();

      // 매물 상세 정보
      const summaryItems = item.querySelectorAll('.ArticleCard_list-summary__jgk_M li');
      const propertyType = summaryItems[0]?.textContent?.trim(); // "아파트"
      const area = summaryItems[1]?.textContent?.trim(); // "80㎡ (전용59)"
      const floor = summaryItems[2]?.textContent?.trim(); // "4/22층"
      const direction = summaryItems[3]?.textContent?.trim(); // "남동향"

      // 뱃지 정보 (집주인, 확인매물 날짜 등)
      const badges = Array.from(
        item.querySelectorAll('.PropertyBadgeList_article__7ScTD li')
      ).map(li => li.textContent?.trim());

      // 매물 설명
      const description = item.querySelector('p')?.textContent?.replace(/"/g, '').trim();

      // 중개사 정보 (그룹 매물인 경우)
      const agentInfo = item.querySelector('.text-more')?.textContent?.trim();
      const agentCount = agentInfo?.match(/\d+/)?.[0];

      // 매물 링크 및 ID
      const articleLink = item.querySelector('a[href*="/articles/"]');
      const articleUrl = articleLink?.getAttribute('href');
      const articleId = articleUrl?.match(/articles\/(\d+)/)?.[1];

      // 그룹 매물 여부
      const isGrouped = item.classList.contains('ArticleCard_folded__xReim');

      return {
        articleId,
        dongName,
        price,
        propertyType,
        area,
        floor,
        direction,
        badges,
        description,
        agentCount: agentCount ? parseInt(agentCount) : null,
        articleUrl,
        isGrouped
      };
    });
  });

  return articles;
}

// 무한 스크롤로 모든 매물 로드
async function loadAllArticles(page: Page) {
  let prevCount = 0;
  let unchangedCount = 0;

  while (unchangedCount < 3) {
    // 현재 매물 개수 확인
    const currentCount = await page.evaluate(() => {
      return document.querySelectorAll('.ComplexArticleList_article__66N3p > li').length;
    });

    if (currentCount === prevCount) {
      unchangedCount++;
    } else {
      unchangedCount = 0;
      console.log(`매물 ${currentCount}개 로드됨`);
    }

    prevCount = currentCount;

    // 페이지 끝까지 스크롤
    await page.evaluate(() => {
      window.scrollTo(0, document.documentElement.scrollHeight);
    });

    // 또는 End 키 사용
    await page.keyboard.press('End');

    await page.waitForTimeout(2000); // 로딩 대기
  }

  return parseArticles(page);
}

// 그룹 매물 펼치기
async function expandGroupedArticles(page: Page) {
  const expandButtons = await page.$$('.ArticleCard_button-expand__Tpi_1');
  console.log(`${expandButtons.length}개 그룹 매물 펼치기`);

  for (const button of expandButtons) {
    await button.click();
    await page.waitForTimeout(500); // 애니메이션 대기
  }
}
```

### 4.4 크롤링 주의사항

#### Rate Limiting (요청 제한)

```javascript
// 각 요청 사이 지연 추가
await sleep(randomInt(2000, 5000)); // 2~5초 랜덤 대기

// 동시 요청 수 제한
const concurrencyLimit = 3;
```

#### 세션 관리

```javascript
// 쿠키 및 User-Agent 설정
const context = await browser.newContext({
  userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
  locale: 'ko-KR',
  timezoneId: 'Asia/Seoul',
});
```

#### 에러 핸들링

```javascript
try {
  await page.goto(url, { timeout: 30000 });
} catch (error) {
  console.error(`Failed to load ${url}:`, error);
  // 재시도 로직
  await retryWithBackoff(async () => {
    await page.goto(url);
  }, maxRetries = 3);
}
```

#### 데이터 검증

```javascript
// 필수 필드 검증
function validateComplex(complex) {
  const requiredFields = ['name', 'complexId', 'type'];
  return requiredFields.every(field => complex[field]);
}

// 중복 제거
const uniqueComplexes = [...new Set(complexes.map(c => c.complexId))]
  .map(id => complexes.find(c => c.complexId === id));
```

---

## 5. 데이터 스키마 설계

### 5.1 지역 테이블

```sql
CREATE TABLE regions (
  id SERIAL PRIMARY KEY,
  level VARCHAR(10) NOT NULL, -- 'si', 'gun', 'eup'
  code VARCHAR(10) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL,
  parent_code VARCHAR(10),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (parent_code) REFERENCES regions(code)
);
```

### 5.2 단지 테이블

```sql
CREATE TABLE complexes (
  id SERIAL PRIMARY KEY,
  complex_id VARCHAR(20) NOT NULL UNIQUE,
  name VARCHAR(200) NOT NULL,
  type VARCHAR(20) NOT NULL, -- 'APT', 'OFFICETEL'
  region_code VARCHAR(10) NOT NULL,
  households INT,
  build_year INT,
  build_month INT,
  age INT,
  floor_area_ratio DECIMAL(5,2), -- 용적률
  building_coverage_ratio DECIMAL(5,2), -- 건폐율
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (region_code) REFERENCES regions(code)
);
```

### 5.3 시세 테이블

```sql
CREATE TABLE market_prices (
  id SERIAL PRIMARY KEY,
  complex_id VARCHAR(20) NOT NULL,
  pyeong_type INT NOT NULL,
  area_sqm DECIMAL(10,2),
  price_date DATE NOT NULL,
  recent_price BIGINT,
  avg_price_3months BIGINT,
  max_price BIGINT,
  min_price BIGINT,
  source VARCHAR(50), -- '한국부동산원', 'KB부동산'
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (complex_id) REFERENCES complexes(complex_id),
  UNIQUE(complex_id, pyeong_type, price_date, source)
);
```

### 5.4 실거래 테이블

```sql
CREATE TABLE transactions (
  id SERIAL PRIMARY KEY,
  complex_id VARCHAR(20) NOT NULL,
  pyeong_type INT,
  area_sqm DECIMAL(10,2),
  contract_date DATE NOT NULL,
  registration_date DATE,
  floor INT,
  price BIGINT NOT NULL,
  trade_type VARCHAR(10) NOT NULL, -- 'A1', 'B1', 'B2', 'B3'
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (complex_id) REFERENCES complexes(complex_id),
  UNIQUE(complex_id, contract_date, floor, price, trade_type)
);
```

### 5.5 매물 테이블

```sql
CREATE TABLE articles (
  id SERIAL PRIMARY KEY,
  article_id VARCHAR(20) NOT NULL UNIQUE,
  complex_id VARCHAR(20) NOT NULL,
  dong VARCHAR(50),
  pyeong_type INT,
  area_sqm DECIMAL(10,2),
  floor INT,
  total_floors INT,
  direction VARCHAR(20),
  trade_type VARCHAR(10) NOT NULL, -- 'A1', 'B1', 'B2', 'B3'
  price_deposit BIGINT,
  price_monthly BIGINT,
  owner_type VARCHAR(20), -- '집주인', '중개사'
  verified_date DATE,
  broker_name VARCHAR(200),
  description TEXT,
  image_count INT DEFAULT 0,
  has_vr BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (complex_id) REFERENCES complexes(complex_id)
);
```

---

## 6. 구현 예시 (Playwright 사용)

### 6.1 전체 크롤링 스크립트 구조

#### 방법 1: API 중심 구현 (권장)

```typescript
import { chromium, Page, Browser } from 'playwright';

class NaverRealEstateCrawler {
  private browser: Browser;
  private page: Page;
  private baseUrl = 'https://fin.land.naver.com';

  async init() {
    this.browser = await chromium.launch({ headless: false });
    this.page = await this.browser.newPage();

    // 초기 세션 획득
    await this.page.goto(this.baseUrl);
    await this.sleep(2000);
  }

  async close() {
    await this.browser.close();
  }

  async crawlAll() {
    await this.init();

    try {
      // 1단계: 시/도 목록 수집 (URL 패턴 기반)
      const siList = this.getKnownSiList(); // 고정된 시/도 코드 사용

      for (const si of siList) {
        console.log(`크롤링 시작: ${si.name}`);

        // 2~3단계: 구/동 목록은 DOM 파싱 필요
        const eupList = await this.getEupListForSi(si.code);

        for (const eup of eupList) {
          console.log(`  - ${eup.name} 크롤링 중...`);

          // 4단계: 단지 목록 수집 (API 사용)
          const complexes = await this.getComplexListAPI(eup.code);
          console.log(`    단지 ${complexes.length}개 발견`);

          for (const complex of complexes) {
            // 5단계: 단지 상세 정보 수집
            await this.crawlComplexDetail(complex.complexNumber);

            // Rate limiting
            await this.sleep(1000);
          }
        }
      }
    } finally {
      await this.close();
    }
  }

  // API를 통한 단지 목록 수집
  async getComplexListAPI(eupCode: string) {
    const allComplexes = [];
    let page = 0;
    let hasMore = true;

    while (hasMore) {
      const data = await this.page.evaluate(async (eupCode, page) => {
        const response = await fetch(
          `/front-api/v1/complex/region?eupLegalDivisionNumber=${eupCode}&size=30&sortType=HOUSEHOLD&page=${page}`
        );
        return await response.json();
      }, eupCode, page);

      if (data.isSuccess && data.result.list.length > 0) {
        allComplexes.push(...data.result.list.map(item => item.complexInfo));
        hasMore = data.result.hasNextPage;
        page++;
        await this.sleep(500); // Rate limiting
      } else {
        hasMore = false;
      }
    }

    return allComplexes;
  }

  // Response 인터셉트를 통한 시세 데이터 수집
  async getTransactionData(complexId: string) {
    const apiResponses = [];

    // Response 이벤트 리스너 등록
    this.page.on('response', async (response) => {
      const url = response.url();
      if (url.includes('/front-api/v1/complex')) {
        try {
          const data = await response.json();
          apiResponses.push({ url, data });
        } catch (e) {
          // JSON 파싱 실패 무시
        }
      }
    });

    // 페이지 로드 (자동으로 여러 API 호출됨)
    await this.page.goto(`${this.baseUrl}/complexes/${complexId}?tab=transaction`);
    await this.sleep(3000); // 모든 API 호출 대기

    return apiResponses;
  }

  // API를 통한 매물 목록 수집
  async getArticleData(complexId: string, tradeTypes: string[] = ['A1', 'B1', 'B2', 'B3']) {
    const allArticles = [];
    let page = 0;
    let hasMore = true;

    // 먼저 페이지 방문 (세션 유지)
    await this.page.goto(`${this.baseUrl}/complexes/${complexId}?tab=article`);
    await this.sleep(2000);

    // API 직접 호출
    while (hasMore && page < 100) {
      try {
        const data = await this.page.evaluate(async (complexId, tradeTypes, page) => {
          const response = await fetch('/front-api/v1/complex/article/list', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              complexNumber: complexId,
              tradeTypes: tradeTypes,
              page: page,
              size: 30,
              sortType: 'RANKING'
            })
          });
          return await response.json();
        }, complexId, tradeTypes, page);

        if (data.articles && data.articles.length > 0) {
          allArticles.push(...data.articles);
          console.log(`  페이지 ${page}: ${data.articles.length}개 로드, 누적 ${allArticles.length}개`);
          page++;
          await this.sleep(500);
        } else {
          hasMore = false;
        }
      } catch (error) {
        console.error(`API 호출 실패 (페이지 ${page}):`, error);
        hasMore = false;
      }
    }

    return allArticles;
  }

  async crawlComplexDetail(complexId: string) {
    console.log(`      단지 ${complexId} 상세 정보 수집 중...`);

    // 시세/실거래 정보
    const transactionData = await this.getTransactionData(complexId);
    console.log(`        - API 응답 ${transactionData.length}개 수집`);

    // 매물 정보
    const articles = await this.getArticleData(complexId);
    console.log(`        - 매물 ${articles.length}개 수집`);

    // 데이터 저장
    await this.saveData({ complexId, transactionData, articles });
  }

  async saveData(data: any) {
    // DB 저장 로직
    // TODO: 구현
  }

  getKnownSiList() {
    return [
      { code: '1100000000', name: '서울특별시' },
      // 다른 시/도 추가
    ];
  }

  async getEupListForSi(siCode: string) {
    // DOM 파싱으로 구/동 목록 수집
    // TODO: 구현
    return [];
  }

  private sleep(ms: number) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// 사용 예시
const crawler = new NaverRealEstateCrawler();
await crawler.crawlAll();
```

#### 방법 2: DOM 파싱 기반 (API 차단 시 대비)

```typescript
class NaverRealEstateCrawlerDOM {
  private browser: Browser;
  private page: Page;
  private baseUrl = 'https://fin.land.naver.com';

  async init() {
    this.browser = await chromium.launch({ headless: false });
    this.page = await this.browser.newPage();
  }

  async close() {
    await this.browser.close();
  }

  // DOM 파싱으로 단지 목록 수집
  async getComplexListDOM(eupCode: string) {
    await this.page.goto(`${this.baseUrl}/regions?si=1100000000&gun=1168000000&eup=${eupCode}`);

    // "더보기" 버튼 모두 클릭
    let hasMore = true;
    while (hasMore) {
      const moreButton = this.page.locator('button:has-text("더보기")').first();
      if (await moreButton.isVisible()) {
        await moreButton.click();
        await this.sleep(1000);
      } else {
        hasMore = false;
      }
    }

    // 단지 목록 파싱
    const complexes = await this.page.evaluate(() => {
      const items = document.querySelectorAll('.ComplexItem_article__gnmoK');
      return Array.from(items).map(item => {
        const name = item.querySelector('.ComplexItem_name__OusaI')?.textContent?.trim();
        const detailLink = item.querySelector('a[href*="/complexes/"]:not([href*="article"])');
        const complexId = detailLink?.getAttribute('href')?.match(/\/complexes\/(\d+)/)?.[1];

        return { complexId: parseInt(complexId || '0'), name };
      });
    });

    return complexes;
  }

  // DOM 파싱으로 매물 목록 수집
  async getArticleDataDOM(complexId: string) {
    await this.page.goto(`${this.baseUrl}/complexes/${complexId}?tab=article`);

    // 무한 스크롤
    let prevCount = 0;
    let unchangedCount = 0;

    while (unchangedCount < 3) {
      const currentCount = await this.page.evaluate(() => {
        return document.querySelectorAll('.ComplexArticleList_article__66N3p > li').length;
      });

      if (currentCount === prevCount) {
        unchangedCount++;
      } else {
        unchangedCount = 0;
      }

      prevCount = currentCount;

      await this.page.keyboard.press('End');
      await this.sleep(2000);
    }

    // 매물 파싱
    const articles = await this.page.evaluate(() => {
      const items = document.querySelectorAll('.ComplexArticleList_article__66N3p > li');
      return Array.from(items).map(item => {
        const dongName = item.querySelector('.ArticleCard_name__3Nh_2')?.textContent?.trim();
        const price = item.querySelector('.ArticleCard_price__KBHz7')?.textContent?.trim();
        const summaryItems = item.querySelectorAll('.ArticleCard_list-summary__jgk_M li');

        return {
          dongName,
          price,
          area: summaryItems[1]?.textContent?.trim(),
          floor: summaryItems[2]?.textContent?.trim(),
          direction: summaryItems[3]?.textContent?.trim()
        };
      });
    });

    return articles;
  }

  private sleep(ms: number) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
```

### 6.2 하이브리드 접근 구현

```typescript
class HybridCrawler {
  private async crawlWithFallback(complexId: string) {
    try {
      // 1순위: API 호출
      console.log('API 호출 시도...');
      return await this.getArticleDataAPI(complexId);
    } catch (error) {
      console.warn('API 호출 실패, DOM 파싱으로 전환:', error);

      try {
        // 2순위: DOM 파싱
        return await this.getArticleDataDOM(complexId);
      } catch (domError) {
        console.error('DOM 파싱도 실패:', domError);
        throw new Error('모든 크롤링 방법 실패');
      }
    }
  }

  private async getArticleDataAPI(complexId: string) {
    // API 구현 (섹션 6.1 참조)
    throw new Error('Not implemented');
  }

  private async getArticleDataDOM(complexId: string) {
    // DOM 파싱 구현 (섹션 6.1 방법 2 참조)
    throw new Error('Not implemented');
  }
}
```

---

## 7. CSS 선택자 참조표

실제 확인된 CSS 클래스명입니다. CSS Modules를 사용하므로 변경될 수 있습니다.

### 7.1 단지 목록 페이지

| 요소 | CSS 선택자 | 설명 |
|------|------------|------|
| 단지 목록 컨테이너 | `.RegionList_list__9GSMS` | 전체 목록을 감싸는 ul |
| 단지 항목 | `.ComplexItem_article__gnmoK` | 각 단지를 나타내는 li |
| 단지명 | `.ComplexItem_name__OusaI` | 단지 이름 |
| 타입 뱃지 | `.TitleBadge_article__dh89O` | 아파트/오피스텔 |
| 정보 항목 | `.ComplexItem_item-info__CvUkT` | 세대수, 준공년월 |
| 매물 수 링크 | `a[href*="article"]` | 매매/전세/월세/단기 링크 |
| 단지 상세 링크 | `a[href*="/complexes/"]:not([href*="article"])` | 단지 상세 페이지 링크 |

### 7.2 매물 목록 페이지

| 요소 | CSS 선택자 | 설명 |
|------|------------|------|
| 매물 목록 컨테이너 | `.ComplexArticleList_article__66N3p` | ul 태그 |
| 매물 항목 | `.ComplexArticleList_article__66N3p > li` | 각 매물 카드 |
| 그룹 매물 | `.ArticleCard_folded__xReim` | 여러 중개사 등록 |
| 단일 매물 | `.ArticleCard_type-single__dRAIG` | 단일 중개사 |
| 동 정보 | `.ArticleCard_name__3Nh_2` | "역삼래미안 104동" |
| 가격 | `.ArticleCard_price__KBHz7` | "매매 29억" 등 |
| 상세 정보 리스트 | `.ArticleCard_list-summary__jgk_M li` | 타입, 면적, 층, 방향 |
| 뱃지 | `.PropertyBadgeList_article__7ScTD li` | 집주인, 확인매물 등 |
| 중개사 수 | `.text-more` | "중개사 N곳에서 등록" |
| 펼치기 버튼 | `.ArticleCard_button-expand__Tpi_1` | 그룹 매물 펼치기 |
| 매물 링크 | `a[href*="/articles/"]` | 매물 상세 페이지 링크 |

### 7.3 시세/실거래 페이지

| 요소 | CSS 선택자 | 설명 |
|------|------------|------|
| 실거래가 테이블 | `table[caption*="실거래가"]` | 실거래가 목록 테이블 |
| 테이블 헤더 | `thead th` | 계약일, 등기일, 층, 가격 |
| 데이터 행 | `tbody tr` | 각 실거래 기록 |
| 더보기 버튼 | `button:has-text("실거래가 더보기")` | 전체 데이터 로드 |
| 평형 선택 버튼 | `button:has-text("㎡")` | 평형 변경 |
| 거래유형 버튼 | `button:has-text("매매")` 등 | 매매/전세/월세 전환 |

---

## 8. 요약

### 핵심 포인트

1. ✅ **Playwright 기반 크롤링 필수**: 직접 API 접근 차단, 브라우저 컨텍스트 내에서만 동작
2. ✅ **3가지 구현 방법**:
   - API 직접 호출 (가장 빠름, 권장)
   - Response 인터셉트 (가장 안정적)
   - DOM 파싱 (API 차단 시 대비)
3. ✅ **계층적 구조**: 시/도 → 구 → 동 → 단지 → 매물 순서로 수집
4. ✅ **URL 패턴 명확**: `/regions`, `/complexes/{id}` 등 일관된 구조
5. ✅ **페이지별 로딩 방식 차이**:
   - 단지 목록: "더보기" 버튼 방식
   - 매물 목록: 무한 스크롤 방식 (3번 연속 변화 없을 때까지)
   - 시세/실거래: "실거래가 더보기" 버튼
6. ✅ **풍부한 내부 API**: 10개 이상의 API 엔드포인트 발견
7. ✅ **실제 CSS 클래스 확인**: CSS Modules 기반, 변경 가능성 고려 필요

### 권장 크롤링 전략

**우선순위:**
1. API 직접 호출 (page.evaluate + fetch)
2. Response 인터셉트 (page.on('response'))
3. DOM 파싱 (CSS 선택자)

**주의사항:**
- Rate Limiting: 요청 간 500ms~1000ms 대기
- 세션 유지: 페이지 먼저 방문 후 API 호출
- CSS 클래스 변경 가능성: API 우선 사용
- 무한 스크롤: 3번 연속 변화 없을 때 종료

### 발견된 주요 API

| API | 용도 | 메서드 |
|-----|------|--------|
| `/front-api/v1/complex/region` | 단지 목록 조회 | GET |
| `/front-api/v1/complex/article/list` | 매물 목록 조회 | POST |
| `/front-api/v1/complex/pyeong/realPrice` | 실거래가 조회 | GET |
| `/front-api/v1/complex/marketPrice/recent` | 최근 시세 | GET |
| `/front-api/v1/complex/askingPrice` | 호가 정보 | GET |
| `/front-api/v1/loan/mortgage/ltvInfo` | 대출 정보 | GET |
| `/front-api/v1/complex/holdingTax` | 보유세 정보 | GET |

### 실제 확인된 데이터

- **단지 목록**: 역삼동 250개 단지 확인
- **매물 목록**: 역삼래미안 110개 매물 전체 로드 성공
- **부동산 타입 코드**: A01(아파트), A02(오피스텔)
- **거래 타입 코드**: A1(매매), B1(전세), B2(월세), B3(단기)
- **정렬 옵션**: HOUSEHOLD, NAME, COMPLETION, ARTICLE

---

**문서 작성일**: 2025-12-04
**최종 수정일**: 2025-12-04
**분석 도구**: Playwright MCP
**분석 대상**: https://fin.land.naver.com/regions
**테스트 단지**: 역삼래미안 (ID: 13814)
**테스트 지역**: 서울시 강남구 역삼동 (1168010100)
