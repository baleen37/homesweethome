# 네이버 부동산 매물 목록 API 탐색 결과

## 개요

네이버 부동산의 단지별 매물 목록 API를 탐색한 결과입니다.

## API Endpoint

### 1. 데스크톱 버전 API (인증 필요)

```
GET https://new.land.naver.com/api/articles/complex/{complexId}
```

**파라미터:**
- `complexNo`: 단지 ID (필수)
- `realEstateType`: 부동산 타입 (예: APT:ABYG:JGC:PRE)
- `tradeType`: 거래 유형 (비워있으면 전체, A1=매매, B1=전세, B2=월세)
- `priceType`: RETAIL (소매가 기준)
- `page`: 페이지 번호 (기본값: 1)
- `type`: list (목록 타입)
- `order`: rank (랭킹순)

**응답:**
- 인증된 사용자만 접근 가능
- 401 Unauthorized 에러 반환

### 2. 모바일 버전 API (성공)

```
GET https://m.land.naver.com/cluster/ajax/articleList
```

**파라미터:**
- `complexNo`: 단지 ID (필수)
- `tradTpCd`: 거래 유형 코드
  - A1: 매매
  - B1: 전세
  - B2: 월세
- `showR0`: N (R0 타입 매물 표시 여부)
- `page`: 페이지 번호 (기본값: 1)

**응답 구조:**
```json
{
  "code": "success",
  "hasPaidPreSale": false,
  "more": false,
  "TIME": false,
  "z": 0,
  "page": 1,
  "body": []  // 매물 목록 배열
}
```

## 거래 유형 코드

| 코드 | 설명 | 예시 |
|------|------|------|
| A1 | 매매 | 완전 소유권 거래 |
| B1 | 전세 | 보증금 기반 임대 |
| B2 | 월세 | 보증금 + 월세 임대 |

## 사용 예시

### 1. 특정 단지의 매매 매물 조회
```javascript
const complexId = 111515;  // 헬리오시티
const url = `https://m.land.naver.com/cluster/ajax/articleList?complexNo=${complexId}&tradTpCd=A1&showR0=N&page=1`;

fetch(url)
  .then(response => response.json())
  .then(data => console.log(data));
```

### 2. 특정 단지의 전세 매물 조회
```javascript
const complexId = 111515;
const url = `https://m.land.naver.com/cluster/ajax/articleList?complexNo=${complexId}&tradTpCd=B1&showR0=N&page=1`;

fetch(url)
  .then(response => response.json())
  .then(data => console.log(data));
```

### 3. 특정 단지의 월세 매물 조회
```javascript
const complexId = 111515;
const url = `https://m.land.naver.com/cluster/ajax/articleList?complexNo=${complexId}&tradTpCd=B2&showR0=N&page=1`;

fetch(url)
  .then(response => response.json())
  .then(data => console.log(data));
```

## 주의사항

1. **브라우저 컨텍스트 필요**: API는 브라우저 내에서만 호출 가능하며, 서버 사이드에서 직접 호출하면 차단됩니다
2. **CORS 제한**: cross-origin 요청이 차단되므로 같은 도메인 내에서만 호출 가능
3. **인증**: 데스크톱 버전 API는 로그인이 필요하며, 모바일 버전은 비로그인도 접근 가능
4. **Rate Limiting**: 과도한 요청은 IP 차단의 원인이 될 수 있으니 적절한 간격(500ms 이상)을 두고 호출해야 함

## 구현 가이드

Playwright를 사용하여 API를 호출하는 예시:

```python
from playwright.sync_api import sync_playwright

def get_complex_listings(complex_id, trade_type='A1'):
    """단지별 매물 목록 조회"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 네이버 부동산 페이지로 이동하여 쿠키 획득
        page.goto("https://new.land.naver.com/complexes")

        # API 호출
        api_url = f"https://m.land.naver.com/cluster/ajax/articleList?complexNo={complex_id}&tradTpCd={trade_type}&showR0=N&page=1"

        result = page.evaluate("""
            async (url) => {
                const response = await fetch(url);
                return await response.json();
            }
        """, api_url)

        browser.close()
        return result
```

## 테스트 결과

- **복합 단지 ID**: 111515 (헬리오시티) - 9510세대, 84동
- **피더하우스(실버주택)**: 114261 - 161세대, 1동 (현재 매물 없음)
- **매물 수**: 헬리오시티의 경우 매매 972개, 전세 856개, 월세 954개 (UI 표시 기준)