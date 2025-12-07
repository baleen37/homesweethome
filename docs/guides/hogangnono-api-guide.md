# 호갱노노 API 가이드

## ⚠️ 중요 경고

**호갱노노는 robots.txt를 통해 모든 자동화된 접근(크롤링)을 명시적으로 금지하고 있습니다:**

```text
User-agent: *
Disallow: /
```

이는 다음을 의미합니다:

- 모든 자동화된 데이터 수집은 서비스 약관 위반
- IP 차단 및 법적 조치 가능성 있음
- 수집한 데이터의 상업적 이용은 법적 제한 있음

**권장 대안**: 이 가이드는 참고용이며, 실제 데이터 수집 시에는 국토교통부 공공데이터나 다른 플랫폼을 활용하시기 바랍니다.

## 1. 기본 URL과 API 버전 정보

### 기본 URL

- **PC 버전**: `https://hogangnono.com`
- **모바일 버전**: `https://m.hogangnono.com`
- **API 기본 URL**: `https://hogangnono.com/api` (※ api.hogangnono.com이 아님)

### API 버전

- 현재 API 버전: v2 (※ v1이 아님)
- 버전 정보는 URL 경로에 포함: `/api/v2/...`

## 2. 인증 방식과 필수 헤더

### 인증 방식

호갱노노는 **대부분의 엔드포인트에서 인증을 요구하지 않습니다**:

- **대부분 공개**: 기본적인 부동산 정보 조회는 인증 불필요
- **선택적 인증**: 일부 고급 기능에서만 쿠키 기반 인증 사용
- **소셜 로그인 지원**: 카카오, 페이스북, 애플, 휴대전화 번호

### 필수 헤더

```json
{
  "Accept": "application/json, text/plain, */*",
  "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
  "Accept-Encoding": "gzip, deflate, br",
  "Cache-Control": "no-cache",
  "Connection": "keep-alive",
  "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
  "Content-Type": "application/json"
}
```

## 3. Rate Limiting 정책

### Rate Limiting 현황

- **사실상 없음**: 테스트 결과 명시적인 제한 없음
- **사용자 제어**: 합리적인 수준에서 자율적인 제어 필요
- **권장 간격**: 0.5-1초 이상 간격 유지 (서버 부하 방지)
- **버스트 제한**: 테스트에서 초당 80+ 요청도 정상 처리

## 4. 실제 발견된 API 엔드포인트

### 4.1 검색 관련

- **검색 제안**: `GET /api/v2/searches/suggestions/new`
  - 파라미터: `query`, `x`, `y`

- **아파트 검색**: `GET /api/apt/bounding`
  - 파라미터: `startX`, `endX`, `startY`, `endY`, `tradeType`, `areaFrom`, `areaTo`, `priceFrom`, `priceTo` 등

### 4.2 지역 정보

- **지역 목록**: `GET /api/v2/maps/region`
  - 파라미터: `lat`, `lng`, `zoom`

- **지역 상세**: `GET /api/v2/regions/{regionCode}`

### 4.3 기타 엔드포인트

- **최신 뉴스**: `GET /api/v2/news/latest`
- **공지사항**: `GET /api/v2/notices`
- **FAQ**: `GET /api/v2/faqs`
- **설정 정보**: `GET /get/config`

## 5. 실제 요청/응답 예시

### 5.1 아파트 검색

**요청 예시**:

```http
GET /api/apt/bounding?map=google&level=17&startX=127.0357119&endX=127.0445632&startY=37.5126209&endY=37.520484&tradeType=0&areaFrom=0&areaTo=80&priceFrom=0&priceTo=401000&r=46318
```

**응답 예시**:

```json
{
  "status": "success",
  "data": [
    {
      "id": "1TUbc",
      "type": 0,
      "name": "강남파라곤",
      "address": "서울특별시 강남구 논현동 241-1",
      "road_address": "서울특별시 강남구 학동로 338",
      "trade_count": 66,
      "total_household": 58,
      "lat": 37.51655253697078,
      "lng": 127.0401375821117,
      "area": {
        "private_area": 117.84,
        "public_area": 140.85,
        "real_trade_price": 175200,
        "real_rent_price": 0,
        "type_official_price": 115700
      },
      "realtime": {
        "visitor": 3,
        "rank": 10
      }
    }
  ]
}
```

### 5.2 검색 제안

**요청 예시**:

```http
GET /api/v2/searches/suggestions/new?query=강남&x=127.040137&y=37.516552
```

**응답 예시**:

```json
{
  "status": "success",
  "data": {
    "query": "강남",
    "matched": {
      "apt": {
        "list": [
          {
            "id": "1TUbc",
            "type": 0,
            "name": "강남파라곤",
            "address": "서울특별시 강남구 논현동 241-1",
            "location": {
              "lat": 37.516552,
              "lon": 127.040137
            },
            "rank_point": 1.0045404105922082
          }
        ],
        "isEnd": false
      }
    }
  }
}
```

## 6. robots.txt 및 법적 고지

### 6.1 Robots.txt 정보

호갱노노는 웹 크롤링을 전면 금지하고 있습니다:

```text
# Notice: Crawling Hogangnono is prohibited unless you have express written permission.
User-agent: *
Disallow: /
```

### 6.2 법적 주의사항

- **크롤링 금지**: 호갱노노는 명시적으로 모든 자동화된 접근을 금지
- **법적 책임**: 무단 크롤링 시 서비스 약관 위반 및 불법행위에 해당할 수 있음
- **민/형사상 책임**: 데이터 무단 수집으로 인한 손해배상 책임 발생 가능성

### 6.3 관련 법령

- **전기통신사업법 제92조**: 정당한 사유 없는 타인 정보통신망 접근 금지
- **저작권법**: 웹사이트 콘텐츠의 무단 복제/배포 제한
- **불법행위법**: 영업방해로 간주될 수 있는 대규모 데이터 수집

## 7. 권장 대안

### 7.1 공식 데이터 소스 활용

1. **국토교통부 실거래가 공개시스템**
   - URL: [https://rt.molit.go.kr](https://rt.molit.go.kr)
   - API 제공: 공공데이터 포털 (data.go.kr)
   - 법적 안정성: 완전 공개 데이터

2. **네이버 부동산**
   - URL: [https://new.land.naver.com](https://new.land.naver.com)
   - 내부 API 활용 가능 (비공식)
   - 비교적 관대한 robots.txt 정책

3. **다른 부동산 플랫폼**
   - 직방 ([https://www.zigbang.com](https://www.zigbang.com))
   - 다방 ([https://www.dabangapp.com](https://www.dabangapp.com))
   - KB부동산 ([https://www.kbland.kr](https://www.kbland.kr))

### 7.2 호갱노노 제휴 문의

- 공식 API 사용 문의
- 데이터 제휴 계약 검토
- 파트너십 프로그램 확인

## 8. 네이버 API와의 비교

| 항목 | 호갱노노 | 네이버 부동산 |
|------|-----------|---------------|
| **기본 URL** | hogangnono.com/api | new.land.naver.com |
| **인증 방식** | 대부분 불필요 | 쿠키 기반 (NNB) |
| **Rate Limit** | 사실상 없음 | 5초 간격 권장 |
| **API 형식** | 비공식 REST API | Ajax/내부 API |
| **데이터 형식** | 표준 JSON | 비표준/변동적 |
| **robots.txt** | 전면 금지 | 일부 허용 |
| **개발자 친화성** | 낮음 (제한적) | 낮음 (비공식) |
| **데이터 품질** | 높음 | 높음 |
| **업데이트 주기** | 실시간 | 실시간 |

## 9. 참고용 웹 스크래핑 가이드

> **주의**: 이 섹션은 교육용이며, 실제 적용은 법적 문제를 초래할 수 있습니다.

### 9.1 기술적 접근

```python
import requests
import time
from playwright.sync_api import sync_playwright

class HogangnonoScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def search_apartments(self, bounds):
        """지역 내 아파트 검색"""
        params = {
            "map": "google",
            "level": "17",
            "startX": bounds["min_lng"],
            "endX": bounds["max_lng"],
            "startY": bounds["min_lat"],
            "endY": bounds["max_lat"],
            "tradeType": "0",
            "r": int(time.time() * 1000)
        }

        response = self.session.get(
            "https://hogangnono.com/api/apt/bounding",
            params=params
        )
        return response.json()

    def get_suggestions(self, query, lat, lng):
        """검색 제안 가져오기"""
        params = {
            "query": query,
            "x": lng,
            "y": lat
        }

        response = self.session.get(
            "https://hogangnono.com/api/v2/searches/suggestions/new",
            params=params
        )
        return response.json()
```

### 9.2 윤리적 고려

- 최소한의 요청만 보내기
- 새벽 시간대(02:00-05:00)에 실행
- 서버 부하 최소화
- 수집 데이터는 개인적 참고용으로만 사용
- 상업적 이용 절대 금지

## 10. FAQ

### Q1: 호갱노노에서 공식 API를 제공하나요?

A: 현재 공식 API는 제공되지 않고 있습니다. 웹 인터페이스를 통한 접근만 가능하며, 이는 서비스 약관상 제한될 수 있습니다.

### Q2: 호갱노노 데이터를 수집하면 법적 문제가 있나요?

A: 네, robots.txt에서 모든 크롤링을 금지하고 있어 무단 수집 시 서비스 약관 위반 및 법적 문제가 발생할 수 있습니다.

### Q3: 부동산 데이터는 어디서 안전하게 얻을 수 있나요?

A: 국토교통부 공공데이터 포털(data.go.kr)에서 제공하는 공식 API를 활용하는 것이 가장 안전하고 법적 문제가 없습니다.

### Q4: 호갱노노와 제휴를 맺고 싶은데 어떻게 해야 하나요?

A: 호갱노노 고객센터나 제휴 담당자에게 직접 문의하여 공식적인 협력 방안을 논의해야 합니다.

### Q5: 연구 목적으로 데이터를 수집해도 괜찮나요?

A: robots.txt의 명시적 금지 조항은 모든 종류의 자동화된 접근에 적용되므로, 연구 목적이라도 서면 허가 없이는 데이터 수집이 어렵습니다.

## 11. 참고 자료

- [국토교통부 실거래가 공개시스템](https://rt.molit.go.kr)
- [공공데이터 포털 부동산 API](https://www.data.go.kr)
- [네이버 부동산](https://new.land.naver.com)
- [robots.txt 표준](https://www.robotstxt.org)
- [전기통신사업법 전문](https://www.law.go.kr)

---

**면책 조항**: 이 가이드는 교육 및 참고 목적으로 작성되었으며, 법적 효력이 없습니다. 실제 데이터 수급 시에는 반드시 해당 서비스의 이용약관을 확인하고 법률 전문가와 상담하시기 바랍니다.
