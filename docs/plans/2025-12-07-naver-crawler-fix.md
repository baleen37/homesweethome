# 네이버 부동산 크롤러 API 인증 수정 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 네이버 부동산 크롤러가 API 인증 문제로 0개 단지를 반환하는 문제를 수정하여 정상적으로 데이터를 수집하도록 함

**Architecture:** 모바일 API(m.land.naver.com)로 전환하고 브라우저 세션을 확보하여 인증 문제를 해결. Rate limiting을 강화하여 429 에러를 방지.

**Tech Stack:** Python 3.11+, Playwright, structlog, 모바일 API endpoints

---

## Task 1: API 엔드포인트 수정

**Files:**
- Modify: `src/crawler/crawlers/naver.py:182-229`

**Step 1: API 엔드포인트를 모바일로 변경**

```python
# _fetch_dong_data 메서드 수정
def _fetch_dong_data(self, dong: dict[str, Any]) -> list[dict[str, Any]]:
    """법정동별 단지 데이터 수집 (모바일 API 사용)"""
    start_time = time.time()
    dong_name = dong.get("dong_name", "")
    cortar_no = dong.get("cortarNo", "")

    # BrowserManager를 사용하여 브라우저 리소스 관리
    with self.browser_manager.managed_browser() as page:
        self.page = page  # 일시적으로 저장

        # 모바일 페이지 접속하여 세션 확보
        page.goto("https://m.land.naver.com/complexes")
        page.wait_for_load_state("networkidle")
        time.sleep(3)  # 세션 안정화

        # bounds 정보 가져오기
        bounds = dong.get("bounds", {
            "leftLon": 127.047294,
            "rightLon": 127.063564,
            "topLat": 37.527949,
            "bottomLat": 37.513261
        })

        # 중심 좌표 계산
        center_lon = (bounds["leftLon"] + bounds["rightLon"]) / 2
        center_lat = (bounds["topLat"] + bounds["bottomLat"]) / 2

        # 모바일 API URL 생성
        api_url = (
            f"https://m.land.naver.com/cluster/ajax/complexList?"
            f"cortarNo={cortar_no}&"
            f"rletTpCd=APT&"
            f"tradTpCd=A1&"
            f"z=17&"
            f"lat={center_lat}&"
            f"lon={center_lon}&"
            f"btm={bounds['bottomLat']}&"
            f"lft={bounds['leftLon']}&"
            f"top={bounds['topLat']}&"
            f"rgt={bounds['rightLon']}"
        )
```

**Step 2: API 호출 부분 수정**

```python
        # 브라우저 컨텍스트에서 API 호출
        result = page.evaluate("""
            async (url) => {
                try {
                    const response = await fetch(url, {
                        method: 'GET',
                        credentials: 'same-origin',
                        headers: {
                            'Accept': 'application/json, text/plain, */*',
                            'Accept-Language': 'ko-KR,ko;q=0.9',
                            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
                        }
                    });

                    if (!response.ok) {
                        const errorText = await response.text();
                        throw new Error(`HTTP ${response.status}: ${errorText}`);
                    }

                    return await response.json();
                } catch (error) {
                    console.error('API call failed:', error);
                    return { error: error.message };
                }
            }
        """, api_url)
```

**Step 3: 파싱 메서드 호출**

```python
        # 데이터 파싱
        if result and result.get("error"):
            self.logger.error("api_call_failed", dong_name=dong_name, error=result["error"])
            return []

        return self._parse_complex_list_api(result)
```

**Step 4: 테스트 실행**

```bash
uv run scripts/main.py --district 강남구
```

Expected: 단지 수가 0개 이상으로 나타남

**Step 5: 커밋**

```bash
git add src/crawler/crawlers/naver.py
git commit -m "fix: 네이버 부동산 크롤러 API 엔드포인트를 모바일로 변경"
```

## Task 2: 응답 파싱 메서드 수정

**Files:**
- Modify: `src/crawler/crawlers/naver.py` (새 메서드 추가)

**Step 1: 모바일 API 응답 파싱 메서드 작성**

```python
def _parse_complex_list_api(self, response: dict[str, Any]) -> list[dict[str, Any]]:
    """모바일 API 응답 파싱"""
    # 모바일 API는 "result" 키에 데이터가 들어있음
    items = response.get("result", [])

    if not items:
        return []

    results = []
    for item in items:
        # HTML 태그 제거 함수
        def clean_price(price_str: str) -> str:
            if not price_str:
                return ""
            return price_str.replace("<em class='txt_unit'>", "").replace("</em>", "").strip()

        results.append({
            "complex_id": item.get("hscpNo", ""),
            "complex_name": item.get("hscpNm", ""),
            "real_estate_type": item.get("hscpTypeNm", ""),
            "completion_year_month": item.get("useAprvYmd", ""),
            "total_dong_count": item.get("totDongCnt", 0),
            "total_household_count": item.get("totHsehCnt", 0),
            "min_area": item.get("minSpc", ""),
            "max_area": item.get("maxSpc", ""),
            "deal_count": item.get("dealCnt", 0),
            "lease_count": item.get("leaseCnt", 0),
            "rent_count": item.get("rentCnt", 0),
            "deal_price_min": clean_price(item.get("dealPrcMin", "")),
            "deal_price_max": clean_price(item.get("dealPrcMax", "")),
            "lease_price_min": clean_price(item.get("leasePrcMin", "")),
            "lease_price_max": clean_price(item.get("leasePrcMax", "")),
        })

    return results
```

**Step 2: 기존 DOM 파싱 코드 제거**

```python
# 기존의 page.evaluate DOM 파싱 코드 삭제
# 아래 코드를 완전히 제거:
"""
result = page.evaluate("""
    () => {
        const data = [];
        // 단지 목록 추출
        const complexes = document.querySelectorAll('a.item_link');
        // ... 나머지 DOM 파싱 코드
    }
""")
"""
```

**Step 3: 테스트 실행**

```bash
uv run scripts/main.py --district 강남구
```

Expected: 파싱된 단지 정보가 정상적으로 출력됨

**Step 4: 커밋**

```bash
git add src/crawler/crawlers/naver.py
git commit -m "feat: 모바일 API 응답 파싱 메서드 추가"
```

## Task 3: Rate Limiting 강화

**Files:**
- Modify: `src/crawler/crawlers/naver.py:229` (API 호출 후 추가)

**Step 1: API 호출 간 대기 시간 추가**

```python
        # API 호출 성공 후 Rate Limiting
        if not result.get("error"):
            # 다음 API 호출까지 최소 5초 대기
            time.sleep(5)
```

**Step 2: 429 에러 핸들링 추가**

```python
        # API 에러 핸들링
        if result and result.get("error"):
            if "429" in str(result["error"]) or "Too Many Requests" in str(result["error"]):
                self.logger.warning(
                    "rate_limit_hit",
                    dong_name=dong_name,
                    wait_time=10
                )
                time.sleep(10)  # Rate limit 걸리면 10초 대기
            else:
                self.logger.error(
                    "api_call_failed",
                    dong_name=dong_name,
                    error=result["error"]
                )
            return []
```

**Step 3: 레이턴 시간 로깅 개선**

```python
        # 응답 시간 로깅
        response_time = time.time() - start_time
        self.crawl_logger.log_api_call(
            endpoint="/cluster/ajax/complexList",
            params={"cortarNo": cortar_no, "dong_name": dong_name},
            response_time=response_time,
            response_size=len(str(result)) if result else 0,
            status_code=200 if result and not result.get("error") else 500,
        )
```

**Step 4: 테스트 실행**

```bash
uv run scripts/main.py --district 강남구
```

Expected: 429 에러 없이 정상적으로 데이터 수집

**Step 5: 커밋**

```bash
git add src/crawler/crawlers/naver.py
git commit -m "feat: Rate Limiting 강화 및 에러 핸들링 개선"
```

## Task 4: 단지 상세 정보 API 수정

**Files:**
- Modify: `src/crawler/crawlers/naver.py` (fetch_complex_listings 메서드)

**Step 1: 단지 매물 목록 API 수정**

```python
def fetch_complex_listings(self, complex_id: str, trade_type: str = "A1") -> list[dict[str, Any]]:
    """단지별 매물 목록 수집 (모바일 API 사용)"""
    self.logger.info(
        "fetching_complex_listings",
        complex_id=complex_id,
        trade_type=trade_type,
    )

    with self.browser_manager.managed_browser() as page:
        # 모바일 페이지 접속
        page.goto("https://m.land.naver.com/complexes")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        all_listings = []
        page = 1
        max_pages = 10

        while page <= max_pages:
            # 모바일 API URL
            api_url = (
                f"https://m.land.naver.com/cluster/ajax/articleList?"
                f"complexNo={complex_id}&"
                f"tradTpCd={trade_type}&"
                f"page={page}&"
                f"showR0=N"
            )

            # 브라우저 컨텍스트에서 API 호출
            result = page.evaluate("""
                async (url) => {
                    try {
                        const response = await fetch(url, {
                            method: 'GET',
                            credentials: 'same-origin',
                            headers: {
                                'Accept': 'application/json, text/plain, */*',
                                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15'
                            }
                        });

                        if (!response.ok) {
                            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                        }

                        return await response.json();
                    } catch (error) {
                        console.error('API call failed:', error);
                        throw error;
                    }
                }
            """, api_url)

            # 데이터 파싱
            listings = self._parse_complex_listings(result)

            if not listings:
                break

            all_listings.extend(listings)

            if len(result.get("result", [])) < 20:
                break

            page += 1
            time.sleep(4)  # 페이지별 대기

    return all_listings
```

**Step 2: 테스트 실행**

```bash
# 단일 단지 테스트
uv run python -c "
from crawler.crawlers.naver import NaverRealEstateCrawler
from crawler.config import CrawlerConfig
import structlog

logger = structlog.get_logger()
config = CrawlerConfig()
crawler = NaverRealEstateCrawler(config)

# 강남구 청담동 테스트
dong_data = {
    'cortarNo': '1168010500',
    'dong_name': '청담동',
    'bounds': {
        'leftLon': 127.047294,
        'rightLon': 127.063564,
        'topLat': 37.527949,
        'bottomLat': 37.513261
    }
}

complexes = crawler._fetch_dong_data(dong_data)
print(f'단지 수: {len(complexes)}')
if complexes:
    print(f'첫 번째 단지: {complexes[0]}')
"
```

Expected: 단지 수 0개 이상, 첫 번째 단지 정보 출력

**Step 3: 커밋**

```bash
git add src/crawler/crawlers/naver.py
git commit -m "fix: 단지 매물 목록 API를 모바일로 변경"
```

## Task 5: 통합 테스트

**Files:**
- Test: 전체 스크립트 실행

**Step 1: 체크포인트 파일 삭제**

```bash
rm -f output/checkpoint.json
```

**Step 2: 단일 구 테스트**

```bash
uv run scripts/main.py --district 강남구
```

Expected:
- 강남구의 여러 동에서 단지 수집
- 각 동에서 0개 이상의 단지 수집
- output/ 디렉토리에 CSV 파일 생성

**Step 3: 전체 구 테스트 (선택사항)**

```bash
uv run scripts/main.py
```

Expected:
- 전체 25개 구 데이터 수집
- 총 단지 수 100개 이상
- 처리 시간 10-20분

**Step 4: 결과 확인**

```bash
ls -la output/
head -10 output/complexes.csv
head -10 output/transactions.csv
```

Expected: CSV 파일에 데이터 포함됨

**Step 5: 최종 커밋**

```bash
git add .
git commit -m "fix: 네이버 부동산 크롤러 정상 동작 확인"
```

## Task 6: 문서 업데이트

**Files:**
- Modify: `docs/guides/naver-real-estate-api-guide.md`
- Modify: `README.md` (필요시)

**Step 1: API 가이드 문서 업데이트**

```markdown
# 네이버 부동산 API 크롤링 완전 가이드

## 현재 상태 (2025-12-07)

✅ **동작 중**: 모바일 API(m.land.naver.com)를 사용하여 정상적으로 데이터 수집

## 주요 변경사항

- API 엔드포인트: `new.land.naver.com/api/` → `m.land.naver.com/cluster/ajax/`
- 인증 방식: 모바일 페이지에서 세션 확보 필요
- Rate Limiting: API 호출 간 최소 5초 대기
```

**Step 2: README 업데이트**

```markdown
## 네이버 부동산 크롤링

**상태**: ✅ 정상 동작 (2025-12-07 수정 완료)

### 실행 방법

```bash
# 전체 구 크롤링
uv run scripts/main.py

# 특정 구만 크롤링
uv run scripts/main.py --district 강남구
```

### 결과 확인

- 단지 정보: `output/complexes.csv`
- 거래내역: `output/transactions.csv`
```

**Step 3: 커밋**

```bash
git add docs/guides/naver-real-estate-api-guide.md README.md
git commit -m "docs: 네이버 부동산 크롤러 수정 완료 문서 업데이트"
```

## 확인 목록

- [ ] API 엔드포인트가 모바일로 변경됨
- [ ] 세션 확보 로직이 추가됨
- [ ] Rate Limiting이 강화됨
- [ ] 단지 데이터가 정상적으로 수집됨 (0개 이상)
- [ ] CSV 파일에 데이터가 저장됨
- [ ] 문서가 업데이트됨