# 호갱노노 API 가이드 검증 보고서

## 1. 검증 개요

검증 일시: 2025-12-07
검증 대상: docs/guides/hogangnono-api-guide.md
검증 방법: 실제 API 호출 테스트

## 2. 주요 검증 결과

### 2.1 심각한 오류

1. **기본 URL 오류**
   - 가이드 기술: `https://api.hogangnono.com`
   - 실제 URL: `https://hogangnono.com/api`
   - 오류: `api.hogangnono.com` 도메인이 존재하지 않음 (DNS 오류)

2. **API 버전 오류**
   - 가이드 기술: `/api/v1/*`
   - 실제 버전: `/api/v2/*`
   - 오류: v1 엔드포인트 모두 404 응답

3. **존재하지 않는 엔드포인트**
   - `/api/v1/search/properties` → 없음
   - `/api/v1/complexes/{complexId}` → 없음
   - `/api/v1/transactions/real-price` → 없음

### 2.2 파라미터 관련 오류

1. **파라미터 이름 불일치**
   - 가이드: `locationCode`, `tradeType`, `propertyType`
   - 실제: 엔드포인트별 상이 (사실상 파라미터 필요 없는 API가 대부분)

2. **한글 파라미터 처리**
   - 가이드: 한글 파라미터 사용 가능함으로 기술
   - 실제: 한글 파라미터 시 400 에러 발생

### 2.3 인증 방식 오류

1. **불필요한 인증**
   - 가이드: JWT, API 키 필요로 기술
   - 실제: 인증 없이 호출 가능한 API가 대부분

2. **잘못된 헤더 정보**
   - 가이드: `X-API-Key`, `Authorization: Bearer`
   - 실제: 해당 헤더 사용하지 않음

### 2.4 응답 형식 오류

1. **응답 구조 불일치**
   - 가이드: `{success: true, data: {...}}`
   - 실제: `{data: {...}, status: "success"}` (success 필드가 상위 레벨에 없음)

2. **필드 이름 불일치**
   - 가이드: `list`, `total`, `page`, `size`
   - 실제: `regionList`, `notice`, `faq` 등 엔드포인트별 상이

## 3. 실제 작동하는 API

### 3.1 확인된 작동 API

1. `GET /api/v2/regions/list` - 지역 목록
2. `GET /api/v2/regions/{regionCode}` - 지역 상세 정보
3. `GET /api/v2/news/latest` - 최신 뉴스
4. `GET /api/v2/notices` - 공지사항
5. `GET /api/v2/faqs` - FAQ

### 3.2 인증/파라미터 필요 API

다음 API들은 400 에러 응답 (인증이나 추가 파라미터 필요):
- `GET /api/v2/apts/closest`
- `GET /api/v2/items/local`
- `GET /api/v2/searches/new`
- `GET /api/v2/ranks/popular`
- `GET /api/search/address`

## 4. 수정 권장 사항

### 4.1 기본 정보 수정

```markdown
### 기본 URL
- **올바른 URL**: `https://hogangnono.com/api`
- **잘못된 URL**: `https://api.hogangnono.com` (삭제 필요)

### API 버전
- **현재 버전**: v2
- **사용 중단**: v1 (존재하지 않음)
```

### 4.2 코드 예시 전체 수정

Python 코드 예시:
```python
class HogangnonoAPIClient:
    def __init__(self):
        # 수정: 올바른 기본 URL
        self.base_url = "https://hogangnono.com/api"

        # 수정: 불필요한 API 키 제거
        self.session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15",
            # 수정: 필요한 헤더 추가
            "Referer": "https://hogangnono.com/",
            "Origin": "https://hogangnono.com"
        })

    def get_regions(self) -> Dict:
        """지역 목록 조회 (실제 작동하는 API)"""
        self._wait_for_rate_limit()

        response = self.session.get(
            f"{self.base_url}/v2/regions/list"  # 수정: v2 사용
        )
        response.raise_for_status()
        return response.json()
```

Node.js 코드 예시도 유사하게 수정 필요.

### 4.3 API 엔드포인트 목록 완전 재작성

```markdown
### 확인된 작동 API 엔드포인트

1. 지역 정보
   - `GET /api/v2/regions/list` - 전체 지역 목록
   - `GET /api/v2/regions/{regionCode}` - 지역 상세 정보

2. 뉴스/공지
   - `GET /api/v2/news/latest` - 최신 부동산 뉴스
   - `GET /api/v2/notices` - 공지사항
   - `GET /api/v2/faqs` - 자주 묻는 질문

3. 인증 필요 API (사용 전 확인 필요)
   - `GET /api/v2/apts/closest` - 가까운 아파트
   - `GET /api/v2/items/local` - 지역 매물
   - `GET /api/v2/searches/new` - 부동산 검색
```

### 4.4 응답 형식 예시 수정

```json
{
  "data": {
    "regionList": [...]
  },
  "status": "success"
}
```

## 5. 결론

호갱노노 API 가이드는 현재 **전면 수정이 필요**한 상태입니다.

1. 기본 URL이 완전히 잘못되어 있음
2. API 버전이 v2로 변경되었으나 v1으로 기술되어 있음
3. 실제 존재하지 않는 엔드포인트가 다수 포함됨
4. 인증 방식, 파라미터, 응답 형식 등 대부분의 기술이 실제와 불일치

**권장 조치**: 가이드 전체를 실제 API 기반으로 재작성하고, 실제 작동하는 코드 예시로 교체해야 합니다.