# 네이버 부동산 API 구조 분석 보고서

**분석일자**: 2025-12-06
**분석 목적**: 구별 필터링 기능 구현을 위한 네이버 부동산 API 구조 파악
**분석 방법**: Playwright MCP를 통한 브라우저 자동화 및 API 직접 호출 테스트

## 1. 개요

본 문서는 네이버 부동산 플랫폼의 API 구조를 체계적으로 분석하여, 구별 필터링 기능을 포함한 크롤러 구현에 필요한 기술 정보를 제공합니다.

### 1.1 분석 범위

- 네이버 부동산 메인 페이지 구조
- 지역 검색 및 자동완성 API
- 단지 목록 및 상세 정보 API
- 매물 목록 조회 API
- API 인증 방식 및 호출 패턴

### 1.2 핵심 발견

- **인증 기반**: 브라우저 세션 기반의 인증 시스템 사용
- **API 분리**: 공개 API(단지 정보)와 인증 필수 API(매물 정보)로 명확히 분리
- **Rate Limiting**: 매우 엄격한 요청 제한 정책 적용

## 2. API 분류 및 접근성

### 2.1 접근 가능한 API (인증 불필요)

| API 엔드포인트 | 설명 | 파라미터 | 용도 |
|---|---|---|---|
| `/api/complexes/overview/{complexNo}` | 단지 상세 정보 | complexNo | 단지 기본 정보, 평형, 동 정보 조회 |
| `/api/cortars` | 지역 정보 | zoom, centerLat, centerLon | 지역 경계, 시/구/동 정보 |
| `/api/complexes/single-markers/2.0` | 단지 마커 정보 | bbox, zoom | 지도 위 단지 위치 정보 |
| `/api/developmentplan/road/list` | 도로 개발계획 | bbox, cortarNo | 도로 개발 정보 |
| `/api/developmentplan/rail/list` | 철도 개발계획 | bbox, cortarNo | 철도 개발 정보 |
| `/api/developmentplan/station/list` | 역사 개발계획 | bbox, cortarNo | 역사 개발 정보 |
| `/api/developmentplan/jigu/list` | 지구 개발계획 | bbox, cortarNo | 지구 개발 정보 |

### 2.2 접근 불가한 API (인증 필수)

| API 엔드포인트 | 설명 | 오류 메시지 |
|---|---|---|
| `/api/articles` | 지역별 매물 목록 | "unauthorized user" |
| `/api/articles/complex/{complexNo}` | 단지별 매물 목록 | "unauthorized user" |
| `/api/interests/articles` | 관심 매물 | "unauthorized user" |

## 3. 주요 API 상세 분석

### 3.1 단지 상세 정보 API

**엔드포인트**: `GET /api/complexes/overview/{complexNo}`

**요청 예시**:
```
https://new.land.naver.com/api/complexes/overview/101517?complexNo=101517
```

**주요 응답 필드**:
```json
{
  "complexTypeName": "아파트",
  "complexType": "A01",
  "complexName": "래미안레이크팰리스",
  "complexNo": "101517",
  "totalHouseHoldCount": 2580,
  "useApproveYmd": "20031231",
  "minArea": 84.86,
  "maxArea": 259.79,
  "minPrice": 280000,
  "maxPrice": 850000,
  "latitude": 37.517295,
  "longitude": 127.047376,
  "pyeongs": [...],
  "dongs": [...],
  "realPrice": {...}
}
```

### 3.2 지역 정보 API

**엔드포인트**: `GET /api/cortars`

**요청 파라미터**:
- `zoom`: 줌 레벨 (정수)
- `centerLat`: 중심 위도
- `centerLon`: 중심 경도

**응답 데이터 구조**:
```json
{
  "cortars": [
    {
      "cortarNo": "1168000000",
      "cortarName": "서울특별시 강남구",
      "cortarLevel": 3,
      "coords": [...]
    }
  ]
}
```

### 3.3 지역 코드 구조

- **형식**: 10자리 숫자
- **구조**: 시(2자리) + 구(4자리) + 동(4자리)
- **예시**:
  - 서울시: `1100000000`
  - 강남구: `1168000000`
  - 강남구 청담동: `1168010400`

## 4. 매물 정보 접근 방안

### 4.1 페이지 접근 기반 수집

API 직접 호출이 제한되므로, 다음 페이지에서 직접 데이터 추출 필요:

1. **지역별 매물 페이지**:
   - URL: `https://new.land.naver.com/houses?cortarNo={cortarNo}`
   - 예: `https://new.land.naver.com/houses?cortarNo=1168000000` (강남구)

2. **단지별 매물 페이지**:
   - URL: `https://new.land.naver.com/complex/{complexNo}`
   - 예: `https://new.land.naver.com/complex/101517`

### 4.2 DOM 기반 데이터 추출

매물 정보는 주로 다음 DOM 구조에서 추출 가능:
```html
<button class="item" data-...>
  <div class="item_title">...</div>  <!-- 단지명 -->
  <div class="price">...</div>        <!-- 가격 -->
  <div class="spec">...</div>         <!-- 면적, 층, 방향 -->
</button>
```

## 5. 인증 및 보안

### 5.1 인증 방식

- **브라우저 세션 기반**: 브라우저 쿠키를 통한 세션 인증
- **Credentials**: `same-origin` 필수
- **Referer**: `https://new.land.naver.com` 도메인 필수

### 5.2 공통 헤더 정보

```javascript
{
  "Accept": "application/json",
  "Content-Type": "application/json",
  "Sec-Fetch-Dest": "empty",
  "Sec-Fetch-Mode": "cors",
  "Sec-Fetch-Site": "same-origin",
  "credentials": "same-origin"
}
```

### 5.3 Rate Limiting

- **요청 간격**: 최소 2-4초 대기 권장
- **연속 호출**: 429 에러 발생 가능성 높음
- **지수 백오프**: 에러 시 대기 시간 점진적 증가 필요

## 6. 구별 크롤링 구현 전략

### 6.1 추천 접근 방식

1. **1단계**: API로 구 코드(cortarNo) 조회
   ```python
   # 자동완성 API를 통한 구 코드 조회
   cortar_no = get_district_code("강남구")  # 1168000000
   ```

2. **2단계**: Playwright로 지역 페이지 접속
   ```python
   page.goto(f"https://new.land.naver.com/houses?cortarNo={cortar_no}")
   ```

3. **3단계**: 페이지 스크롤 및 데이터 추출
   ```python
   while has_more:
       scroll_page()
       listings = extract_listings_from_dom()
       save_to_csv(listings)
   ```

4. **4단계**: 단지별 상세 정보 조회 (API 활용)
   ```python
   for complex_no in extracted_complexes:
       detail = fetch_complex_overview(complex_no)
       merge_data(listing, detail)
   ```

### 6.2 효율화 전략

1. **병렬 처리**: 각 구를 별도 세션에서 병렬 처리
2. **체크포인트**: 처리된 데이터는 즉시 저장
3. **에러 핸들링**: 일시적 오류 시 재시도 로직 구현
4. **캐싱**: 단지 상세 정보는 중복 조회 방지

## 7. 코드 예시

### 7.1 Playwright를 통한 데이터 추출

```python
from playwright.sync_api import sync_playwright

def extract_district_listings(cortar_no: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 페이지 접속
        page.goto(f"https://new.land.naver.com/houses?cortarNo={cortar_no}")

        listings = []

        # 스크롤하며 데이터 추출
        while True:
            # 페이지 로딩 대기
            page.wait_for_selector(".item", timeout=10000)

            # 현재 페이지의 매물 추출
            current_listings = page.evaluate("""
                () => {
                    const items = document.querySelectorAll('.item');
                    return Array.from(items).map(item => ({
                        title: item.querySelector('.item_title')?.textContent?.trim(),
                        price: item.querySelector('.price')?.textContent?.trim(),
                        spec: item.querySelector('.spec')?.textContent?.trim(),
                        href: item.getAttribute('href')
                    }));
                }
            """)

            if not current_listings:
                break

            listings.extend(current_listings)

            # 페이지 스크롤
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)

            # 더 이상 새로운 데이터가 없는지 확인
            page.wait_for_timeout(1000)

        browser.close()
        return listings
```

## 8. 결론 및 제언

### 8.1 핵심 결론

1. **API 직접 호출은 제한적**: 매물 정보는 페이지 접근 필수
2. **브라우저 자동화 필수**: Playwright 또는 유사 도구 사용 필요
3. **속도보다 안정성**: Rate Limiting에 따른 충분한 대기 시간 확보

### 8.2 구현 우선순위

1. **1순위**: 구별 필터링을 통한 페이지 접근 기능
2. **2순위**: DOM 기반 매물 정보 추출
3. **3순위**: API를 통한 단지 상세 정보 병합
4. **4순위**: 체크포인트 및 재개 기능

### 8.3 기술 권장사항

- **Python**: Playwright sync API 사용
- **데이터 저장**: CSV로 즉시 저장
- **오류 처리**: 429 에러별 특별 핸들링
- **로깅**: 상세한 진행 상황 기록

---

## 부록

### A. 관련 문서

- [네이버 부동산 최종 접근 방식 분석](./naver-real-estate-final-approach.md)
- [구별 크롤링 설계 문서](../plans/2025-12-06-district-based-crawling-design.md)

### B. 테스트 환경

- **브라우저**: Chromium (Playwright)
- **테스트 지역**: 서울특별시 강남구
- **분석 일자**: 2025-12-06

### C. 제한 사항

본 분석은 2025-12-06 기준의 네이버 부동산 플랫폼을 기반으로 하며, API 구조는 언제든 변경될 수 있습니다.