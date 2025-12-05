# 점진적 크롤링 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 네이버 부동산 크롤러에 단지 상세 정보 및 매물 목록 조회 기능을 추가하고, 각 단계를 통합 테스트로 검증합니다.

**Architecture:** 기존 `NaverRealEstateCrawler`에 `fetch_complex_detail()`, `fetch_complex_listings()` 메서드를 추가하여 YAGNI 원칙에 따라 호출자가 필요한 수준만 선택할 수 있도록 합니다. Playwright 브라우저 컨텍스트를 재사용하여 세션 유지.

**Tech Stack:** Python 3.11+, Playwright (sync), pytest, structlog

---

## Task 1: API 탐색 - 단지 상세 정보 엔드포인트 찾기

**Files:**
- Create: `docs/api-exploration/complex-detail-api.md`

**Step 1: Playwright MCP로 네이버 부동산 접속**

Playwright MCP를 사용하여 네이버 부동산 모바일 사이트에 접속합니다.

Run: `mcp__playwright__browser_navigate` with URL `https://m.land.naver.com/complexes`

**Step 2: 실제 단지 ID 확보**

기존 통합 테스트를 실행하여 실제 단지 ID를 얻습니다.

Run:
```bash
pytest tests/integration/test_naver_integration.py::test_real_crawl_small_area -v -s 2>&1 | grep "complex_id"
```

Expected: 단지 ID 출력 (예: `"complex_id": "12345"`)

**Step 3: 단지 상세 페이지로 이동**

얻은 단지 ID로 상세 페이지에 접속합니다.

Run: `mcp__playwright__browser_navigate` with URL `https://m.land.naver.com/complex/info/{complex_id}`

**Step 4: Network 요청 캡처**

페이지 로딩 중 발생한 API 호출을 확인합니다.

Run: `mcp__playwright__browser_network_requests`

Expected: 단지 상세 정보를 반환하는 API 엔드포인트 발견

**Step 5: API 응답 구조 문서화**

발견한 API를 직접 호출하여 응답 구조를 확인합니다.

Run: `mcp__playwright__browser_evaluate` with:
```javascript
async (url) => {
    const response = await fetch(url);
    return await response.json();
}
```

**Step 6: 문서 작성**

API 엔드포인트, 파라미터, 응답 구조를 문서화합니다.

Create: `docs/api-exploration/complex-detail-api.md`
```markdown
# 단지 상세 정보 API

## 엔드포인트
`https://m.land.naver.com/complex/...`

## 파라미터
- hscpNo: 단지 ID

## 응답 구조
```json
{
  "주소 필드": "...",
  "편의시설": "...",
  ...
}
```
```

**Step 7: Commit**

```bash
git add docs/api-exploration/complex-detail-api.md
git commit -m "docs: 단지 상세 정보 API 탐색 결과"
```

---

## Task 2: API 탐색 - 매물 목록 엔드포인트 찾기

**Files:**
- Create: `docs/api-exploration/complex-listings-api.md`

**Step 1: 매물 목록 페이지로 이동**

단지 상세 페이지에서 매물 목록 탭/페이지로 이동합니다.

Run: `mcp__playwright__browser_navigate` or `mcp__playwright__browser_click`

**Step 2: Network 요청 캡처**

매물 목록 로딩 중 발생한 API 호출을 확인합니다.

Run: `mcp__playwright__browser_network_requests`

Expected: 매물 목록을 반환하는 API 엔드포인트 발견

**Step 3: API 응답 구조 문서화**

발견한 API를 직접 호출하여 응답 구조를 확인합니다.

Run: `mcp__playwright__browser_evaluate` with fetch

**Step 4: 문서 작성**

API 엔드포인트, 파라미터, 응답 구조를 문서화합니다.

Create: `docs/api-exploration/complex-listings-api.md`

**Step 5: Commit**

```bash
git add docs/api-exploration/complex-listings-api.md
git commit -m "docs: 매물 목록 API 탐색 결과"
```

---

## Task 3: fetch_complex_detail() 메서드 구현

**Files:**
- Modify: `src/crawler/crawlers/naver.py`

**Prerequisites:** Task 1 완료 (API 엔드포인트 확보)

**Step 1: 메서드 시그니처 추가**

```python
# src/crawler/crawlers/naver.py

def fetch_complex_detail(self, complex_id: str) -> dict[str, Any]:
    """단지 상세 정보 조회

    Args:
        complex_id: 단지 ID (hscpNo)

    Returns:
        단지 상세 정보 dict
    """
    pass
```

**Step 2: API URL 구성**

Task 1에서 찾은 엔드포인트를 사용하여 URL을 구성합니다.

```python
def fetch_complex_detail(self, complex_id: str) -> dict[str, Any]:
    api_url = f"https://m.land.naver.com/complex/getComplexDetail?hscpNo={complex_id}"
    # 실제 엔드포인트는 Task 1 결과에 따라 수정

    self.logger.info("fetching_complex_detail", complex_id=complex_id)
```

**Step 3: Playwright evaluate로 API 호출**

```python
def fetch_complex_detail(self, complex_id: str) -> dict[str, Any]:
    api_url = f"https://m.land.naver.com/complex/getComplexDetail?hscpNo={complex_id}"

    self.logger.info("fetching_complex_detail", complex_id=complex_id)

    result = self.page.evaluate(
        """
        async (url) => {
            const response = await fetch(url);
            return await response.json();
        }
        """,
        api_url,
    )

    return self._parse_complex_detail(result)
```

**Step 4: _parse_complex_detail() 구현**

Task 1에서 확인한 응답 구조를 기반으로 모든 필드를 파싱합니다.

```python
def _parse_complex_detail(self, response: dict[str, Any]) -> dict[str, Any]:
    """단지 상세 정보 파싱

    API 응답에서 모든 유용한 필드를 추출합니다.
    """
    # Task 1 결과에 따라 실제 필드명 사용
    detail = {
        "road_address": response.get("roadAddress", ""),
        "jibun_address": response.get("jibunAddress", ""),
        "parking_count": response.get("parkingCount", 0),
        "construction_company": response.get("constructionCompany", ""),
        # API가 제공하는 모든 필드 추가
    }

    self.logger.info("parsed_complex_detail", complex_id=detail.get("complex_id"))
    return detail
```

**Step 5: Commit**

```bash
git add src/crawler/crawlers/naver.py
git commit -m "feat: fetch_complex_detail() 메서드 구현"
```

---

## Task 4: test_fetch_complex_detail() 통합 테스트 작성

**Files:**
- Modify: `tests/integration/test_naver_integration.py`

**Step 1: 테스트 골격 작성**

```python
# tests/integration/test_naver_integration.py

@pytest.mark.integration
def test_fetch_complex_detail(tmp_path: Path) -> None:
    """
    단지 상세 정보 조회 통합 테스트

    이 테스트는:
    - 실제 브라우저를 실행합니다
    - crawl()로 단지 1개를 얻습니다
    - fetch_complex_detail()로 상세 정보를 조회합니다
    - 추가 필드를 검증합니다

    실행: pytest tests/integration/test_naver_integration.py::test_fetch_complex_detail -v -s
    """
    pass
```

**Step 2: 크롤러 초기화 및 단지 1개 얻기**

```python
@pytest.mark.integration
def test_fetch_complex_detail(tmp_path: Path) -> None:
    # 체크포인트 초기화
    checkpoint_path = Path("output/checkpoint.json")
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    config = CrawlerConfig(timeout=30, headless=True, output_dir=str(tmp_path))
    crawler = NaverRealEstateCrawler(config)

    # 금천구 1개 동만 선택
    original_data = crawler.districts_data
    test_district = None
    for district in original_data["districts"]:
        if district["district_name"] == "금천구":
            test_district = district
            break

    assert test_district is not None
    crawler.districts_data = {
        "districts": [{
            "district_name": test_district["district_name"],
            "district_code": test_district["district_code"],
            "dongs": [test_district["dongs"][0]],  # 첫 번째 동만
        }]
    }

    # 단지 목록 크롤링
    complexes = crawler.crawl()
    assert len(complexes) > 0, "크롤링 결과가 비어있습니다"

    first_complex = complexes[0]
    complex_id = first_complex["complex_id"]
    print(f"\n테스트 대상 단지: {first_complex['complex_name']} (ID: {complex_id})")
```

**Step 3: fetch_complex_detail() 호출 및 검증**

```python
    # 단지 상세 정보 조회
    detail = crawler.fetch_complex_detail(complex_id)

    # 결과 검증
    assert detail is not None, "상세 정보가 None입니다"
    print(f"\n상세 정보 필드 수: {len(detail)}")

    # Task 3에서 구현한 필드 검증
    assert "road_address" in detail or "jibun_address" in detail, "주소 정보가 없습니다"

    # 추가 필드 검증 (API 응답에 따라)
    print(f"도로명 주소: {detail.get('road_address', 'N/A')}")
    print(f"지번 주소: {detail.get('jibun_address', 'N/A')}")
    print(f"주차 대수: {detail.get('parking_count', 'N/A')}")
```

**Step 4: 브라우저 정리 확인**

```python
    # 브라우저는 crawler.crawl() 내부에서 자동으로 close됨
    # 추가 정리 불필요
```

**Step 5: 테스트 실행**

Run:
```bash
pytest tests/integration/test_naver_integration.py::test_fetch_complex_detail -v -s
```

Expected: PASS

**Step 6: Commit**

```bash
git add tests/integration/test_naver_integration.py
git commit -m "test: fetch_complex_detail() 통합 테스트 추가"
```

---

## Task 5: fetch_complex_listings() 메서드 구현

**Files:**
- Modify: `src/crawler/crawlers/naver.py`

**Prerequisites:** Task 2 완료 (API 엔드포인트 확보)

**Step 1: 메서드 시그니처 추가**

```python
# src/crawler/crawlers/naver.py

def fetch_complex_listings(
    self,
    complex_id: str,
    trade_type: str = "A1"  # A1: 매매, B1: 전세, B2: 월세
) -> list[dict[str, Any]]:
    """단지의 매물 목록 조회

    Args:
        complex_id: 단지 ID (hscpNo)
        trade_type: 거래 유형 (A1: 매매, B1: 전세, B2: 월세)

    Returns:
        매물 정보 리스트
    """
    pass
```

**Step 2: API URL 구성**

```python
def fetch_complex_listings(
    self,
    complex_id: str,
    trade_type: str = "A1"
) -> list[dict[str, Any]]:
    api_url = f"https://m.land.naver.com/complex/getArticleList?hscpNo={complex_id}&tradTpCd={trade_type}"
    # 실제 엔드포인트는 Task 2 결과에 따라 수정

    self.logger.info(
        "fetching_complex_listings",
        complex_id=complex_id,
        trade_type=trade_type
    )
```

**Step 3: Playwright evaluate로 API 호출**

```python
def fetch_complex_listings(
    self,
    complex_id: str,
    trade_type: str = "A1"
) -> list[dict[str, Any]]:
    api_url = f"https://m.land.naver.com/complex/getArticleList?hscpNo={complex_id}&tradTpCd={trade_type}"

    self.logger.info(
        "fetching_complex_listings",
        complex_id=complex_id,
        trade_type=trade_type
    )

    result = self.page.evaluate(
        """
        async (url) => {
            const response = await fetch(url);
            return await response.json();
        }
        """,
        api_url,
    )

    return self._parse_complex_listings(result)
```

**Step 4: _parse_complex_listings() 구현**

```python
def _parse_complex_listings(self, response: dict[str, Any]) -> list[dict[str, Any]]:
    """매물 목록 파싱

    API 응답에서 모든 매물 정보를 추출합니다.
    """
    # Task 2 결과에 따라 실제 응답 구조 사용
    items = response.get("articleList", [])  # 실제 키 이름은 API 응답에 따라
    results = []

    for item in items:
        listing = {
            "article_id": item.get("articleNo", ""),
            "article_name": item.get("articleName", ""),
            "floor": item.get("floor", ""),
            "area": item.get("area", ""),
            "supply_area": item.get("supplyArea", ""),
            "price": item.get("price", ""),
            "article_confirm_ymd": item.get("articleConfirmYmd", ""),
            "direction": item.get("direction", ""),
            # API가 제공하는 모든 필드 추가
        }
        results.append(listing)

    self.logger.info("parsed_listings", count=len(results))
    return results
```

**Step 5: Rate limiting 추가**

```python
def fetch_complex_listings(
    self,
    complex_id: str,
    trade_type: str = "A1"
) -> list[dict[str, Any]]:
    api_url = f"https://m.land.naver.com/complex/getArticleList?hscpNo={complex_id}&tradTpCd={trade_type}"

    self.logger.info(
        "fetching_complex_listings",
        complex_id=complex_id,
        trade_type=trade_type
    )

    result = self.page.evaluate(
        """
        async (url) => {
            const response = await fetch(url);
            return await response.json();
        }
        """,
        api_url,
    )

    time.sleep(0.5)  # Rate limiting

    return self._parse_complex_listings(result)
```

**Step 6: Commit**

```bash
git add src/crawler/crawlers/naver.py
git commit -m "feat: fetch_complex_listings() 메서드 구현"
```

---

## Task 6: test_fetch_complex_listings() 통합 테스트 작성

**Files:**
- Modify: `tests/integration/test_naver_integration.py`

**Step 1: 테스트 골격 작성**

```python
# tests/integration/test_naver_integration.py

@pytest.mark.integration
def test_fetch_complex_listings(tmp_path: Path) -> None:
    """
    매물 목록 조회 통합 테스트

    이 테스트는:
    - 실제 브라우저를 실행합니다
    - crawl()로 단지 1개를 얻습니다
    - fetch_complex_listings()로 매물 목록을 조회합니다
    - 매물 데이터를 검증합니다

    실행: pytest tests/integration/test_naver_integration.py::test_fetch_complex_listings -v -s
    """
    pass
```

**Step 2: 크롤러 초기화 및 단지 1개 얻기**

```python
@pytest.mark.integration
def test_fetch_complex_listings(tmp_path: Path) -> None:
    # 체크포인트 초기화
    checkpoint_path = Path("output/checkpoint.json")
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    config = CrawlerConfig(timeout=30, headless=True, output_dir=str(tmp_path))
    crawler = NaverRealEstateCrawler(config)

    # 금천구 1개 동만 선택
    original_data = crawler.districts_data
    test_district = None
    for district in original_data["districts"]:
        if district["district_name"] == "금천구":
            test_district = district
            break

    assert test_district is not None
    crawler.districts_data = {
        "districts": [{
            "district_name": test_district["district_name"],
            "district_code": test_district["district_code"],
            "dongs": [test_district["dongs"][0]],
        }]
    }

    # 단지 목록 크롤링
    complexes = crawler.crawl()
    assert len(complexes) > 0

    # 매물이 있는 단지 찾기
    target_complex = None
    for c in complexes:
        if c.get("total_article_count", 0) > 0:
            target_complex = c
            break

    if target_complex is None:
        pytest.skip("매물이 있는 단지가 없습니다")

    complex_id = target_complex["complex_id"]
    print(f"\n테스트 대상 단지: {target_complex['complex_name']} (ID: {complex_id})")
    print(f"총 매물 수: {target_complex.get('total_article_count', 0)}")
```

**Step 3: fetch_complex_listings() 호출 및 검증**

```python
    # 매물 목록 조회
    listings = crawler.fetch_complex_listings(complex_id)

    # 결과 검증
    assert listings is not None, "매물 목록이 None입니다"
    assert isinstance(listings, list), "매물 목록이 리스트가 아닙니다"

    print(f"\n조회된 매물 수: {len(listings)}")

    if len(listings) > 0:
        first_listing = listings[0]
        print(f"\n첫 번째 매물:")
        print(f"  매물 ID: {first_listing.get('article_id', 'N/A')}")
        print(f"  층: {first_listing.get('floor', 'N/A')}")
        print(f"  면적: {first_listing.get('area', 'N/A')}")
        print(f"  가격: {first_listing.get('price', 'N/A')}")

        # 필수 필드 검증
        assert "article_id" in first_listing, "매물 ID가 없습니다"
        # 기타 필드는 API 응답에 따라 유연하게 (없을 수도 있음)
```

**Step 4: 테스트 실행**

Run:
```bash
pytest tests/integration/test_naver_integration.py::test_fetch_complex_listings -v -s
```

Expected: PASS (매물이 있는 경우) 또는 SKIPPED (매물이 없는 경우)

**Step 5: Commit**

```bash
git add tests/integration/test_naver_integration.py
git commit -m "test: fetch_complex_listings() 통합 테스트 추가"
```

---

## Task 7: test_crawl_complexes_basic() 리팩토링

**Files:**
- Modify: `tests/integration/test_naver_integration.py`

**목적:** 기존 `test_real_crawl_small_area`를 금천구 1개 동으로 축소하고 이름 변경

**Step 1: 기존 테스트 확인**

Read: `tests/integration/test_naver_integration.py`의 `test_real_crawl_small_area`

**Step 2: 테스트 이름 변경 및 단순화**

```python
@pytest.mark.integration
def test_crawl_complexes_basic(tmp_path: Path) -> None:
    """
    레벨 1: 단지 목록만 크롤링 (기본 기능)

    이 테스트는:
    - 실제 브라우저를 실행합니다 (headless=True)
    - 실제 네이버 부동산 모바일 API를 호출합니다
    - 금천구 1개 동만 크롤링합니다
    - 단지 기본 정보를 검증합니다

    실행: pytest tests/integration/test_naver_integration.py::test_crawl_complexes_basic -v -s
    """
    # 체크포인트 초기화
    checkpoint_path = Path("output/checkpoint.json")
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    config = CrawlerConfig(timeout=30, headless=True, output_dir=str(tmp_path))
    crawler = NaverRealEstateCrawler(config)

    # 금천구 1개 동만 선택
    original_data = crawler.districts_data
    test_district = None
    for district in original_data["districts"]:
        if district["district_name"] == "금천구":
            test_district = district
            break

    assert test_district is not None, "금천구를 찾을 수 없습니다"

    crawler.districts_data = {
        "districts": [{
            "district_name": test_district["district_name"],
            "district_code": test_district["district_code"],
            "dongs": [test_district["dongs"][0]],  # 첫 번째 동만
        }]
    }

    # 실제 크롤링 실행
    results = crawler.crawl()

    # 결과 검증
    assert len(results) > 0, "크롤링 결과가 비어있습니다"
    print(f"\n크롤링된 단지 수: {len(results)}")

    # 첫 번째 결과 필드 검증
    first_result = results[0]
    assert "complex_id" in first_result
    assert "complex_name" in first_result
    assert "real_estate_type" in first_result
    assert "completion_year_month" in first_result
    assert "total_dong_count" in first_result
    assert "total_household_count" in first_result
    assert "min_area" in first_result
    assert "max_area" in first_result

    # CSV 저장 검증
    output_path = tmp_path / "test_output.csv"
    writer = CSVWriter(output_path)
    writer.write(results)

    assert output_path.exists()
    assert output_path.stat().st_size > 0

    with open(output_path, encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) > 1  # 헤더 + 데이터
        assert "complex_id" in lines[0]

    print(f"CSV 저장 완료: {output_path}")
    print(f"CSV 라인 수: {len(lines)}")

    # 체크포인트 검증
    assert checkpoint_path.exists(), "체크포인트 파일이 생성되지 않았습니다"
```

**Step 3: 기존 test_real_crawl_small_area 제거 여부 결정**

- 기존 테스트가 3개 동을 사용한다면, 유지하고 새 테스트 추가
- 또는 기존 테스트를 완전히 교체

(Jiho 확인 필요 - 일단 새 테스트 추가하고 기존 유지)

**Step 4: 테스트 실행**

Run:
```bash
pytest tests/integration/test_naver_integration.py::test_crawl_complexes_basic -v -s
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/integration/test_naver_integration.py
git commit -m "test: test_crawl_complexes_basic 추가 (금천구 1개 동)"
```

---

## Task 8: test_crawl_full_pipeline() 통합 테스트 작성

**Files:**
- Modify: `tests/integration/test_naver_integration.py`

**Step 1: 테스트 골격 작성**

```python
@pytest.mark.integration
def test_crawl_full_pipeline(tmp_path: Path) -> None:
    """
    레벨 4: 전체 파이프라인 (목록 → 상세 → 매물)

    이 테스트는:
    - crawl()로 단지 목록을 얻습니다
    - 각 단지에 대해 fetch_complex_detail() 호출
    - 각 단지에 대해 fetch_complex_listings() 호출
    - 통합 데이터를 CSV로 저장합니다

    실행: pytest tests/integration/test_naver_integration.py::test_crawl_full_pipeline -v -s
    """
    pass
```

**Step 2: 크롤러 초기화**

```python
@pytest.mark.integration
def test_crawl_full_pipeline(tmp_path: Path) -> None:
    # 체크포인트 초기화
    checkpoint_path = Path("output/checkpoint.json")
    if checkpoint_path.exists():
        checkpoint_path.unlink()

    config = CrawlerConfig(timeout=30, headless=True, output_dir=str(tmp_path))
    crawler = NaverRealEstateCrawler(config)

    # 금천구 1개 동만 선택
    original_data = crawler.districts_data
    test_district = None
    for district in original_data["districts"]:
        if district["district_name"] == "금천구":
            test_district = district
            break

    assert test_district is not None
    crawler.districts_data = {
        "districts": [{
            "district_name": test_district["district_name"],
            "district_code": test_district["district_code"],
            "dongs": [test_district["dongs"][0]],
        }]
    }
```

**Step 3: 전체 파이프라인 실행**

```python
    # 단지 목록 크롤링
    complexes = crawler.crawl()
    assert len(complexes) > 0
    print(f"\n크롤링된 단지 수: {len(complexes)}")

    # 각 단지에 대해 상세 정보 및 매물 조회
    enriched_data = []

    for idx, complex_info in enumerate(complexes[:3]):  # 처음 3개만 테스트
        complex_id = complex_info["complex_id"]
        print(f"\n[{idx+1}/{min(3, len(complexes))}] {complex_info['complex_name']}")

        try:
            # 상세 정보 조회
            detail = crawler.fetch_complex_detail(complex_id)
            complex_info.update(detail)
            print(f"  상세 정보 조회 완료")

            # 매물 목록 조회
            listings = crawler.fetch_complex_listings(complex_id)

            # 매물 정보 집계 (단지 중심 CSV이므로)
            if listings:
                prices = [
                    float(l.get("price", "0").replace(",", ""))
                    for l in listings
                    if l.get("price")
                ]
                if prices:
                    complex_info["avg_listing_price"] = sum(prices) / len(prices)
                    complex_info["min_listing_price"] = min(prices)
                    complex_info["max_listing_price"] = max(prices)
                complex_info["active_listings_count"] = len(listings)
                print(f"  매물 {len(listings)}개 조회 완료")
            else:
                print(f"  매물 없음")

        except Exception as e:
            print(f"  오류: {e}")
            continue

        enriched_data.append(complex_info)
```

**Step 4: CSV 저장 및 검증**

```python
    # CSV 저장
    output_path = tmp_path / "full_pipeline_output.csv"
    writer = CSVWriter(output_path)
    writer.write(enriched_data)

    assert output_path.exists()
    assert output_path.stat().st_size > 0

    # CSV 내용 검증
    with open(output_path, encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) > 1
        header = lines[0]

        # 기본 필드
        assert "complex_id" in header
        assert "complex_name" in header

        # 상세 정보 필드 (있으면)
        # assert "road_address" in header or "jibun_address" in header

        # 매물 집계 필드 (있으면)
        # assert "avg_listing_price" in header or "active_listings_count" in header

    print(f"\nCSV 저장 완료: {output_path}")
    print(f"통합 데이터 행 수: {len(enriched_data)}")
```

**Step 5: 테스트 실행**

Run:
```bash
pytest tests/integration/test_naver_integration.py::test_crawl_full_pipeline -v -s
```

Expected: PASS

**Step 6: Commit**

```bash
git add tests/integration/test_naver_integration.py
git commit -m "test: test_crawl_full_pipeline 전체 파이프라인 테스트 추가"
```

---

## Task 9: 체크포인트 로직 단순화

**Files:**
- Modify: `src/crawler/utils/checkpoint.py`

**Step 1: 현재 CheckpointManager 구조 확인**

Read: `src/crawler/utils/checkpoint.py`

**Step 2: CheckpointManager 단순화**

기존 복잡한 구조를 제거하고 간단한 구조로 변경합니다.

```python
# src/crawler/utils/checkpoint.py

import json
from pathlib import Path
from typing import Any


class CheckpointManager:
    def __init__(self, checkpoint_path: str) -> None:
        self.checkpoint_path = Path(checkpoint_path)
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any] | None:
        """체크포인트 로드"""
        if not self.checkpoint_path.exists():
            return None

        with open(self.checkpoint_path, encoding="utf-8") as f:
            return json.load(f)

    def save(self, last_dong: str, last_complex: str | None = None) -> None:
        """체크포인트 저장

        Args:
            last_dong: 마지막으로 완료한 동 코드
            last_complex: 해당 동에서 마지막으로 처리한 단지 ID (없으면 None)
        """
        checkpoint = {
            "last_dong": last_dong,
            "last_complex": last_complex,
            "failed_dongs": self.load().get("failed_dongs", []) if self.load() else []
        }

        with open(self.checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)

    def should_skip_dong(self, dong_code: str) -> bool:
        """해당 동을 건너뛰어야 하는지 확인"""
        checkpoint = self.load()
        if not checkpoint:
            return False

        last_dong = checkpoint.get("last_dong")
        if not last_dong:
            return False

        # 마지막 완료 동보다 작거나 같으면 skip
        return dong_code <= last_dong

    def should_skip_complex(self, dong_code: str, complex_id: str) -> bool:
        """해당 단지를 건너뛰어야 하는지 확인"""
        checkpoint = self.load()
        if not checkpoint:
            return False

        # 다른 동이면 skip 안 함
        if checkpoint.get("last_dong") != dong_code:
            return False

        # 같은 동이면 last_complex와 비교
        last_complex = checkpoint.get("last_complex")
        if not last_complex:
            return False

        return complex_id <= last_complex

    def add_failed_dong(self, dong_code: str, error: str) -> None:
        """실패한 동 추가"""
        checkpoint = self.load() or {}
        failed = checkpoint.get("failed_dongs", [])

        failed.append({
            "dong_code": dong_code,
            "error": error
        })

        checkpoint["failed_dongs"] = failed

        with open(self.checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)
```

**Step 3: NaverRealEstateCrawler 업데이트**

`crawl()` 메서드에서 새 체크포인트 로직 사용:

```python
# src/crawler/crawlers/naver.py의 crawl() 메서드 수정

def crawl(self) -> list[dict[str, Any]]:
    """서울시 전체 구/동을 순회하며 크롤링"""
    self.logger.info("crawling_start")

    all_results: list[dict[str, Any]] = []
    url = self.get_url()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=self.config.headless)
        self.page = browser.new_page()
        self.page.goto(url, timeout=self.config.timeout * 1000)
        self.page.wait_for_load_state("networkidle")

        self.logger.info("browser_ready")

        for district in self.districts_data["districts"]:
            for dong in district["dongs"]:
                dong_code = dong["cortarNo"]

                # 체크포인트: 동 스킵 확인
                if self.checkpoint_manager.should_skip_dong(dong_code):
                    self.logger.info("skipping_completed_dong", dong=dong["dong_name"])
                    continue

                self.logger.info(
                    "crawling_dong",
                    district=district["district_name"],
                    dong=dong["dong_name"],
                )

                results = self._fetch_with_retry(dong)
                all_results.extend(results)

                # 체크포인트 저장 (동 완료)
                self.checkpoint_manager.save(dong_code, None)

        browser.close()

    self.logger.info("crawling_complete", total_complexes=len(all_results))
    return all_results
```

**Step 4: 기존 체크포인트 파일 정리**

기존 복잡한 구조의 체크포인트는 호환되지 않으므로, 테스트에서 초기화하도록 이미 구현됨.

**Step 5: 테스트 실행**

Run:
```bash
pytest tests/integration/test_naver_integration.py::test_real_crawl_with_checkpoint -v -s
```

Expected: PASS (기존 체크포인트 테스트도 동작해야 함)

**Step 6: Commit**

```bash
git add src/crawler/utils/checkpoint.py src/crawler/crawlers/naver.py
git commit -m "refactor: 체크포인트 로직 단순화 (last_dong, last_complex)"
```

---

## Task 10: 전체 테스트 실행 및 검증

**Files:**
- None (검증 단계)

**Step 1: 전체 통합 테스트 실행**

Run:
```bash
pytest tests/integration/test_naver_integration.py -v -s
```

Expected: 모든 테스트 PASS

**Step 2: 개별 테스트 확인**

```bash
pytest tests/integration/test_naver_integration.py::test_crawl_complexes_basic -v -s
pytest tests/integration/test_naver_integration.py::test_fetch_complex_detail -v -s
pytest tests/integration/test_naver_integration.py::test_fetch_complex_listings -v -s
pytest tests/integration/test_naver_integration.py::test_crawl_full_pipeline -v -s
```

Expected: 각각 PASS

**Step 3: 성공 기준 체크리스트 검증**

설계 문서의 성공 기준 확인:
- [ ] 4개의 통합 테스트 모두 통과
- [ ] 단지 상세 정보의 모든 필드 수집
- [ ] 매물 정보의 모든 필드 수집
- [ ] 체크포인트 로직으로 중단 후 재개 가능
- [ ] CSV 파일에 모든 데이터 저장
- [ ] 각 통합 테스트는 30초 이내 완료

**Step 4: 문서 업데이트**

프로젝트 README 또는 CLAUDE.md에 새 기능 및 테스트 추가 내용 반영 (필요 시)

**Step 5: 최종 커밋**

```bash
git add -A
git commit -m "feat: 점진적 크롤링 구현 완료

- fetch_complex_detail(): 단지 상세 정보 조회
- fetch_complex_listings(): 매물 목록 조회
- 4개의 독립적인 통합 테스트 추가
- 체크포인트 로직 단순화
- 전체 파이프라인 통합

테스트: pytest tests/integration/test_naver_integration.py -v -s"
```

---

## Notes

### API 탐색 시 주의사항

- Task 1, 2에서 실제 API 엔드포인트를 찾지 못할 수도 있습니다
- 그 경우 네이버 부동산의 다른 경로 시도 (예: `/complex/{id}`, `/info/{id}` 등)
- 최악의 경우 HTML 파싱으로 대체 가능 (하지만 API가 더 안정적)

### 테스트 데이터 범위

- 금천구 1개 동만 사용하여 빠른 피드백
- 실제 운영 시에는 전체 서울시 크롤링 가능

### Rate Limiting

- 현재 500ms 대기 사용 중
- 상세 조회 추가 시 네이버 차단 방지를 위해 더 늘려야 할 수 있음
- 필요 시 1000ms로 조정

### CSV 출력

- 현재는 단지 중심 CSV (1행 = 1단지)
- 매물 정보는 집계하여 저장
- 나중에 매물 중심 CSV로 변경 가능 (Jiho 결정)

### 체크포인트

- 단순화된 구조로 동/단지 수준 재개 지원
- 실패한 동은 별도 리스트로 관리하여 재시도 가능
