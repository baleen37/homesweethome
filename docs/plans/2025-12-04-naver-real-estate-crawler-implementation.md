# 네이버 부동산 크롤러 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 서울시 전체 아파트 매매 매물을 Playwright + API 직접 호출로 크롤링하고 체크포인트 기반 중단/재개 지원

**Architecture:** NaverRealEstateCrawler가 DynamicCrawler를 상속하고, CheckpointManager로 진행 상황 관리. page.evaluate()로 fetch API 호출하여 JSON 직접 획득. CSVWriter로 점진적 저장.

**Tech Stack:** Python 3.11+, Playwright (sync API), structlog, CSV, JSON

---

## Task 1: CheckpointManager 클래스 구현

**Files:**
- Create: `src/crawler/utils/__init__.py`
- Create: `src/crawler/utils/checkpoint.py`
- Create: `tests/unit/test_checkpoint_manager.py`

**Step 1: Write the failing test for CheckpointManager**

`tests/unit/test_checkpoint_manager.py` 파일을 생성합니다:

```python
import json
from pathlib import Path

import pytest

from crawler.utils.checkpoint import CheckpointManager


@pytest.fixture
def temp_checkpoint_file(tmp_path: Path) -> Path:
    return tmp_path / "checkpoint.json"


def test_load_returns_none_when_file_does_not_exist(temp_checkpoint_file: Path) -> None:
    manager = CheckpointManager(str(temp_checkpoint_file))
    result = manager.load()
    assert result is None


def test_save_creates_checkpoint_file(temp_checkpoint_file: Path) -> None:
    manager = CheckpointManager(str(temp_checkpoint_file))
    checkpoint = {
        "last_completed": {"district": "강남구", "dong": "삼성동"},
        "completed_dongs": ["1168010100"],
        "failed_dongs": [],
        "total_complexes_crawled": 26,
    }
    manager.save(checkpoint)

    assert temp_checkpoint_file.exists()
    with open(temp_checkpoint_file) as f:
        saved = json.load(f)
    assert saved["last_completed"]["district"] == "강남구"
    assert saved["total_complexes_crawled"] == 26


def test_load_returns_saved_checkpoint(temp_checkpoint_file: Path) -> None:
    checkpoint = {
        "last_completed": {"district": "서초구", "dong": "반포동"},
        "completed_dongs": ["1165010100", "1165010200"],
        "failed_dongs": [],
        "total_complexes_crawled": 52,
    }
    with open(temp_checkpoint_file, "w") as f:
        json.dump(checkpoint, f)

    manager = CheckpointManager(str(temp_checkpoint_file))
    result = manager.load()

    assert result is not None
    assert result["last_completed"]["dong"] == "반포동"
    assert len(result["completed_dongs"]) == 2


def test_should_skip_dong_returns_true_for_completed(temp_checkpoint_file: Path) -> None:
    checkpoint = {
        "completed_dongs": ["1168010100", "1168010200"],
        "failed_dongs": [],
    }
    with open(temp_checkpoint_file, "w") as f:
        json.dump(checkpoint, f)

    manager = CheckpointManager(str(temp_checkpoint_file))
    manager.load()

    assert manager.should_skip_dong("1168010100") is True
    assert manager.should_skip_dong("1168010999") is False


def test_add_failed_dong_records_failure(temp_checkpoint_file: Path) -> None:
    manager = CheckpointManager(str(temp_checkpoint_file))
    manager.checkpoint = {
        "completed_dongs": [],
        "failed_dongs": [],
    }

    dong = {"cortarNo": "1168010300", "dong_name": "역삼동"}
    manager.add_failed_dong(dong, "API timeout")

    assert len(manager.checkpoint["failed_dongs"]) == 1
    assert manager.checkpoint["failed_dongs"][0]["cortarNo"] == "1168010300"
    assert manager.checkpoint["failed_dongs"][0]["error"] == "API timeout"
```

**Step 2: Run test to verify it fails**

실행:
```bash
uv run pytest tests/unit/test_checkpoint_manager.py -v
```

예상 결과: `ModuleNotFoundError: No module named 'crawler.utils'`

**Step 3: Write minimal CheckpointManager implementation**

`src/crawler/utils/__init__.py` 파일을 생성:

```python
```

`src/crawler/utils/checkpoint.py` 파일을 생성:

```python
import json
from datetime import datetime
from pathlib import Path
from typing import Any


class CheckpointManager:
    def __init__(self, filepath: str) -> None:
        self.filepath = Path(filepath)
        self.checkpoint: dict[str, Any] = {
            "last_completed": {},
            "completed_dongs": [],
            "failed_dongs": [],
            "total_complexes_crawled": 0,
            "last_updated": None,
        }

    def load(self) -> dict[str, Any] | None:
        if not self.filepath.exists():
            return None

        with open(self.filepath) as f:
            self.checkpoint = json.load(f)
        return self.checkpoint

    def save(self, checkpoint: dict[str, Any]) -> None:
        self.checkpoint = checkpoint
        self.checkpoint["last_updated"] = datetime.now().isoformat()

        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w") as f:
            json.dump(self.checkpoint, f, indent=2, ensure_ascii=False)

    def should_skip_dong(self, cortar_no: str) -> bool:
        return cortar_no in self.checkpoint.get("completed_dongs", [])

    def add_failed_dong(self, dong: dict[str, Any], error: str) -> None:
        self.checkpoint.setdefault("failed_dongs", []).append(
            {
                "cortarNo": dong["cortarNo"],
                "dong_name": dong.get("dong_name", ""),
                "error": error,
                "timestamp": datetime.now().isoformat(),
            }
        )
```

**Step 4: Run test to verify it passes**

실행:
```bash
uv run pytest tests/unit/test_checkpoint_manager.py -v
```

예상 결과: 모든 테스트 PASS

**Step 5: Commit**

```bash
git add src/crawler/utils/ tests/unit/test_checkpoint_manager.py
git commit -m "feat: CheckpointManager 구현 및 테스트 추가"
```

---

## Task 2: 서울시 지역 데이터 수집 및 JSON 파일 작성

**Files:**
- Create: `src/crawler/data/seoul_districts.json`
- Create: `scripts/collect_seoul_data.py`

**Note:** 이 작업은 네이버 부동산 사이트를 직접 탐색하여 서울시 구/동 목록과 cortarNo를 수집해야 합니다. 자동화하거나 수동으로 수집할 수 있습니다.

**Step 1: Create data directory**

실행:
```bash
mkdir -p src/crawler/data
```

**Step 2: Create helper script to collect Seoul district data**

`scripts/collect_seoul_data.py` 파일을 생성:

```python
"""
서울시 구/동 데이터 수집 스크립트

네이버 부동산 사이트를 Playwright로 탐색하여 서울시 전체 구/동 목록과
cortarNo, 좌표 범위를 수집합니다.

실행: python scripts/collect_seoul_data.py
"""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def collect_seoul_districts() -> dict:
    """
    네이버 부동산에서 서울시 구/동 데이터 수집

    TODO: 실제 구현 필요
    - 네이버 부동산 지역 검색 페이지 접속
    - 서울시 선택 후 구/동 목록 추출
    - 각 동의 cortarNo와 좌표 범위 추출
    """
    # 임시로 샘플 데이터 반환 (실제로는 크롤링해야 함)
    return {
        "districts": [
            {
                "district_name": "강남구",
                "district_code": "1168000000",
                "dongs": [
                    {
                        "dong_name": "삼성동",
                        "cortarNo": "1168010100",
                        "bounds": {
                            "leftLon": 127.05,
                            "rightLon": 127.07,
                            "topLat": 37.52,
                            "bottomLat": 37.50,
                        },
                    },
                    {
                        "dong_name": "역삼동",
                        "cortarNo": "1168010200",
                        "bounds": {
                            "leftLon": 127.03,
                            "rightLon": 127.05,
                            "topLat": 37.51,
                            "bottomLat": 37.49,
                        },
                    },
                ],
            },
            {
                "district_name": "서초구",
                "district_code": "1165000000",
                "dongs": [
                    {
                        "dong_name": "반포동",
                        "cortarNo": "1165010100",
                        "bounds": {
                            "leftLon": 126.99,
                            "rightLon": 127.01,
                            "topLat": 37.51,
                            "bottomLat": 37.49,
                        },
                    },
                ],
            },
        ]
    }


def main() -> None:
    print("서울시 구/동 데이터 수집 중...")

    data = collect_seoul_districts()

    output_path = Path("src/crawler/data/seoul_districts.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    total_dongs = sum(len(d["dongs"]) for d in data["districts"])
    print(f"✓ {len(data['districts'])}개 구, {total_dongs}개 동 데이터 저장")
    print(f"✓ 저장 위치: {output_path}")


if __name__ == "__main__":
    main()
```

**Step 3: Run script to create initial data file**

실행:
```bash
python scripts/collect_seoul_data.py
```

예상 결과: `src/crawler/data/seoul_districts.json` 파일이 생성되고 샘플 데이터가 저장됨

**Step 4: Verify JSON file structure**

실행:
```bash
cat src/crawler/data/seoul_districts.json
```

예상 결과: 구/동 데이터가 올바른 JSON 형식으로 저장되어 있음

**Step 5: Commit**

```bash
git add src/crawler/data/seoul_districts.json scripts/collect_seoul_data.py
git commit -m "feat: 서울시 구/동 데이터 수집 스크립트 및 초기 데이터 추가"
```

**Note:** 실제 사용 시에는 `collect_seoul_districts()` 함수를 구현하여 전체 서울시 데이터를 수집해야 합니다. 현재는 샘플 데이터만 포함되어 있습니다.

---

## Task 3: NaverRealEstateCrawler 기본 구조 구현

**Files:**
- Create: `src/crawler/crawlers/naver.py`
- Create: `tests/unit/test_naver_crawler.py`
- Create: `tests/fixtures/naver_api_response.json`

**Step 1: Write the failing test for NaverRealEstateCrawler**

`tests/fixtures/naver_api_response.json` 파일을 생성:

```json
{
  "totalCount": 2,
  "list": [
    {
      "markerId": "149239",
      "markerType": "COMPLEX",
      "latitude": 37.458919,
      "longitude": 126.898166,
      "complexName": "테스트아파트1",
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
      "dealCount": 5,
      "leaseCount": 3,
      "rentCount": 0,
      "shortTermRentCount": 0,
      "totalArticleCount": 8,
      "existPriceTab": false,
      "isComplexTourExist": false
    },
    {
      "markerId": "149240",
      "markerType": "COMPLEX",
      "latitude": 37.460000,
      "longitude": 126.900000,
      "complexName": "테스트아파트2",
      "realEstateTypeCode": "APT",
      "realEstateTypeName": "아파트",
      "completionYearMonth": "201512",
      "totalDongCount": 3,
      "totalHouseholdCount": 500,
      "floorAreaRatio": 350,
      "minArea": "84.00",
      "maxArea": "120.00",
      "priceCount": 0,
      "representativeArea": 0,
      "isPresales": false,
      "photoCount": 10,
      "dealCount": 2,
      "leaseCount": 1,
      "rentCount": 0,
      "shortTermRentCount": 0,
      "totalArticleCount": 3,
      "existPriceTab": false,
      "isComplexTourExist": true
    }
  ]
}
```

`tests/unit/test_naver_crawler.py` 파일을 생성:

```python
import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler


@pytest.fixture
def crawler_config() -> CrawlerConfig:
    return CrawlerConfig(timeout=30, headless=True, output_dir="output")


@pytest.fixture
def sample_api_response() -> dict:
    fixture_path = Path(__file__).parent.parent / "fixtures" / "naver_api_response.json"
    with open(fixture_path) as f:
        return json.load(f)


def test_get_url_returns_naver_real_estate_url(crawler_config: CrawlerConfig) -> None:
    crawler = NaverRealEstateCrawler(crawler_config)
    url = crawler.get_url()
    assert url == "https://new.land.naver.com/complexes"


def test_load_districts_data_returns_districts(crawler_config: CrawlerConfig) -> None:
    crawler = NaverRealEstateCrawler(crawler_config)
    districts = crawler._load_districts_data()

    assert "districts" in districts
    assert len(districts["districts"]) > 0
    assert "district_name" in districts["districts"][0]
    assert "dongs" in districts["districts"][0]


def test_parse_extracts_complex_data_from_api_response(
    crawler_config: CrawlerConfig, sample_api_response: dict
) -> None:
    crawler = NaverRealEstateCrawler(crawler_config)
    results = crawler._parse_api_response(sample_api_response)

    assert len(results) == 2
    assert results[0]["complex_name"] == "테스트아파트1"
    assert results[0]["marker_id"] == "149239"
    assert results[0]["latitude"] == 37.458919
    assert results[0]["longitude"] == 126.898166
    assert results[0]["real_estate_type"] == "아파트"
    assert results[0]["completion_year_month"] == "202403"
    assert results[0]["total_dong_count"] == 1
    assert results[0]["total_household_count"] == 151
    assert results[0]["floor_area_ratio"] == 499
    assert results[0]["min_area"] == "70.79"
    assert results[0]["max_area"] == "78.25"
    assert results[0]["deal_count"] == 5
    assert results[0]["lease_count"] == 3
    assert results[0]["total_article_count"] == 8


def test_parse_handles_empty_list(crawler_config: CrawlerConfig) -> None:
    crawler = NaverRealEstateCrawler(crawler_config)
    results = crawler._parse_api_response({"totalCount": 0, "list": []})

    assert len(results) == 0
```

**Step 2: Run test to verify it fails**

실행:
```bash
uv run pytest tests/unit/test_naver_crawler.py -v
```

예상 결과: `ModuleNotFoundError: No module named 'crawler.crawlers.naver'`

**Step 3: Write minimal NaverRealEstateCrawler implementation**

`src/crawler/crawlers/naver.py` 파일을 생성:

```python
import json
from pathlib import Path
from typing import Any

from crawler.crawlers.base import BaseCrawler
from crawler.utils.checkpoint import CheckpointManager


class NaverRealEstateCrawler(BaseCrawler):
    def __init__(self, config: Any) -> None:
        super().__init__(config)
        self.checkpoint_manager = CheckpointManager("output/checkpoint.json")
        self.districts_data = self._load_districts_data()

    def get_url(self) -> str:
        return "https://new.land.naver.com/complexes"

    def fetch(self, url: str) -> str:
        # 이 메서드는 사용하지 않지만 추상 메서드이므로 구현 필요
        return ""

    def parse(self, html: str) -> list[dict[str, Any]]:
        # 이 메서드는 사용하지 않지만 추상 메서드이므로 구현 필요
        return []

    def _load_districts_data(self) -> dict[str, Any]:
        data_path = Path(__file__).parent.parent / "data" / "seoul_districts.json"
        with open(data_path, encoding="utf-8") as f:
            return json.load(f)

    def _parse_api_response(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        items = response.get("list", [])
        results = []

        for item in items:
            results.append(
                {
                    "marker_id": item["markerId"],
                    "complex_name": item["complexName"],
                    "latitude": item["latitude"],
                    "longitude": item["longitude"],
                    "real_estate_type": item["realEstateTypeName"],
                    "completion_year_month": item["completionYearMonth"],
                    "total_dong_count": item["totalDongCount"],
                    "total_household_count": item["totalHouseholdCount"],
                    "floor_area_ratio": item["floorAreaRatio"],
                    "min_area": item["minArea"],
                    "max_area": item["maxArea"],
                    "deal_count": item["dealCount"],
                    "lease_count": item["leaseCount"],
                    "total_article_count": item["totalArticleCount"],
                }
            )

        self.logger.info("parsed_complexes", count=len(results))
        return results
```

**Step 4: Run test to verify it passes**

실행:
```bash
uv run pytest tests/unit/test_naver_crawler.py -v
```

예상 결과: 모든 테스트 PASS

**Step 5: Commit**

```bash
git add src/crawler/crawlers/naver.py tests/unit/test_naver_crawler.py tests/fixtures/naver_api_response.json
git commit -m "feat: NaverRealEstateCrawler 기본 구조 구현"
```

---

## Task 4: API 호출 로직 구현 (Playwright page.evaluate)

**Files:**
- Modify: `src/crawler/crawlers/naver.py`
- Modify: `tests/unit/test_naver_crawler.py`

**Step 1: Write the failing test for fetch_dong_data**

`tests/unit/test_naver_crawler.py`에 추가:

```python
def test_fetch_dong_data_calls_api_with_correct_url(crawler_config: CrawlerConfig) -> None:
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock page.evaluate
    mock_page = Mock()
    mock_page.evaluate.return_value = {
        "totalCount": 1,
        "list": [
            {
                "markerId": "123",
                "complexName": "테스트단지",
                "latitude": 37.5,
                "longitude": 127.0,
                "realEstateTypeName": "아파트",
                "completionYearMonth": "202001",
                "totalDongCount": 1,
                "totalHouseholdCount": 100,
                "floorAreaRatio": 200,
                "minArea": "60",
                "maxArea": "80",
                "dealCount": 0,
                "leaseCount": 0,
                "totalArticleCount": 0,
            }
        ],
    }
    crawler.page = mock_page

    dong = {
        "cortarNo": "1168010100",
        "dong_name": "삼성동",
        "bounds": {
            "leftLon": 127.05,
            "rightLon": 127.07,
            "topLat": 37.52,
            "bottomLat": 37.50,
        },
    }

    results = crawler._fetch_dong_data(dong)

    assert len(results) == 1
    assert results[0]["complex_name"] == "테스트단지"
    mock_page.evaluate.assert_called_once()
```

**Step 2: Run test to verify it fails**

실행:
```bash
uv run pytest tests/unit/test_naver_crawler.py::test_fetch_dong_data_calls_api_with_correct_url -v
```

예상 결과: `AttributeError: 'NaverRealEstateCrawler' object has no attribute '_fetch_dong_data'`

**Step 3: Implement _fetch_dong_data method**

`src/crawler/crawlers/naver.py`에 추가:

```python
def _fetch_dong_data(self, dong: dict[str, Any]) -> list[dict[str, Any]]:
    cortar_no = dong["cortarNo"]
    bounds = dong["bounds"]

    api_url = (
        f"https://new.land.naver.com/api/complexes/single-markers/2.0?"
        f"cortarNo={cortar_no}&"
        f"zoom=17&"
        f"priceType=RETAIL&"
        f"realEstateType=APT&"
        f"tradeType=A1&"
        f"leftLon={bounds['leftLon']}&"
        f"rightLon={bounds['rightLon']}&"
        f"topLat={bounds['topLat']}&"
        f"bottomLat={bounds['bottomLat']}"
    )

    self.logger.info(
        "fetching_dong_data",
        dong=dong.get("dong_name", ""),
        cortar_no=cortar_no,
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

    return self._parse_api_response(result)
```

**Step 4: Run test to verify it passes**

실행:
```bash
uv run pytest tests/unit/test_naver_crawler.py::test_fetch_dong_data_calls_api_with_correct_url -v
```

예상 결과: 테스트 PASS

**Step 5: Commit**

```bash
git add src/crawler/crawlers/naver.py tests/unit/test_naver_crawler.py
git commit -m "feat: API 호출 로직 구현 (page.evaluate + fetch)"
```

---

## Task 5: 에러 처리 및 재시도 로직 추가

**Files:**
- Modify: `src/crawler/crawlers/naver.py`
- Modify: `tests/unit/test_naver_crawler.py`

**Step 1: Write the failing test for retry logic**

`tests/unit/test_naver_crawler.py`에 추가:

```python
import time


def test_fetch_with_retry_retries_on_timeout(crawler_config: CrawlerConfig) -> None:
    crawler = NaverRealEstateCrawler(crawler_config)

    mock_page = Mock()
    mock_page.evaluate.side_effect = [
        TimeoutError("Timeout 1"),
        TimeoutError("Timeout 2"),
        {"totalCount": 1, "list": [{"markerId": "123", "complexName": "성공"}]},
    ]
    crawler.page = mock_page

    dong = {
        "cortarNo": "1168010100",
        "dong_name": "삼성동",
        "bounds": {"leftLon": 127.05, "rightLon": 127.07, "topLat": 37.52, "bottomLat": 37.50},
    }

    with patch("time.sleep"):  # 테스트 속도를 위해 sleep mock
        results = crawler._fetch_with_retry(dong)

    assert len(results) == 1
    assert mock_page.evaluate.call_count == 3


def test_fetch_with_retry_records_failure_after_max_retries(
    crawler_config: CrawlerConfig,
) -> None:
    crawler = NaverRealEstateCrawler(crawler_config)

    mock_page = Mock()
    mock_page.evaluate.side_effect = TimeoutError("Always timeout")
    crawler.page = mock_page

    dong = {
        "cortarNo": "1168010100",
        "dong_name": "삼성동",
        "bounds": {"leftLon": 127.05, "rightLon": 127.07, "topLat": 37.52, "bottomLat": 37.50},
    }

    with patch("time.sleep"):
        results = crawler._fetch_with_retry(dong, max_retries=3)

    assert len(results) == 0
    assert mock_page.evaluate.call_count == 3
    assert len(crawler.checkpoint_manager.checkpoint["failed_dongs"]) == 1
```

**Step 2: Run test to verify it fails**

실행:
```bash
uv run pytest tests/unit/test_naver_crawler.py::test_fetch_with_retry_retries_on_timeout -v
```

예상 결과: `AttributeError: 'NaverRealEstateCrawler' object has no attribute '_fetch_with_retry'`

**Step 3: Implement _fetch_with_retry method**

`src/crawler/crawlers/naver.py`에 추가 (import도 추가):

```python
import time

# ... (기존 코드)

def _fetch_with_retry(
    self, dong: dict[str, Any], max_retries: int = 3
) -> list[dict[str, Any]]:
    for attempt in range(max_retries):
        try:
            data = self._fetch_dong_data(dong)
            time.sleep(0.5)  # Rate limiting
            return data
        except TimeoutError:
            self.logger.warning(
                "fetch_timeout",
                dong=dong.get("dong_name", ""),
                attempt=attempt + 1,
                max_retries=max_retries,
            )
            if attempt == max_retries - 1:
                self.checkpoint_manager.add_failed_dong(dong, "Timeout after retries")
                return []
            time.sleep(2**attempt)  # 지수 백오프
        except Exception as e:
            self.logger.error(
                "fetch_error",
                dong=dong.get("dong_name", ""),
                error=str(e),
            )
            self.checkpoint_manager.add_failed_dong(dong, str(e))
            return []
    return []
```

**Step 4: Run test to verify it passes**

실행:
```bash
uv run pytest tests/unit/test_naver_crawler.py -v
```

예상 결과: 모든 테스트 PASS

**Step 5: Commit**

```bash
git add src/crawler/crawlers/naver.py tests/unit/test_naver_crawler.py
git commit -m "feat: 에러 처리 및 재시도 로직 추가"
```

---

## Task 6: 전체 크롤링 로직 구현 (crawl 메서드 오버라이드)

**Files:**
- Modify: `src/crawler/crawlers/naver.py`
- Modify: `tests/unit/test_naver_crawler.py`

**Step 1: Write the failing test for full crawl flow**

`tests/unit/test_naver_crawler.py`에 추가:

```python
def test_crawl_iterates_through_all_dongs(crawler_config: CrawlerConfig) -> None:
    crawler = NaverRealEstateCrawler(crawler_config)

    # Mock Playwright context
    mock_browser = Mock()
    mock_page = Mock()
    mock_page.evaluate.return_value = {
        "totalCount": 1,
        "list": [
            {
                "markerId": "123",
                "complexName": "단지1",
                "latitude": 37.5,
                "longitude": 127.0,
                "realEstateTypeName": "아파트",
                "completionYearMonth": "202001",
                "totalDongCount": 1,
                "totalHouseholdCount": 100,
                "floorAreaRatio": 200,
                "minArea": "60",
                "maxArea": "80",
                "dealCount": 0,
                "leaseCount": 0,
                "totalArticleCount": 0,
            }
        ],
    }

    with patch("crawler.crawlers.naver.sync_playwright") as mock_playwright:
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = (
            mock_browser
        )
        mock_browser.new_page.return_value = mock_page
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None

        with patch("time.sleep"):  # 테스트 속도 향상
            results = crawler.crawl()

    # 샘플 데이터는 2개 구, 3개 동이므로 3개 단지 크롤링 예상
    assert len(results) == 3
    assert mock_page.evaluate.call_count == 3
```

**Step 2: Run test to verify it fails**

실행:
```bash
uv run pytest tests/unit/test_naver_crawler.py::test_crawl_iterates_through_all_dongs -v
```

예상 결과: 테스트 FAIL (crawl 메서드가 아직 구현되지 않음)

**Step 3: Implement crawl method**

`src/crawler/crawlers/naver.py`의 crawl 메서드를 오버라이드 (import도 추가):

```python
from playwright.sync_api import sync_playwright, Page

# ... (기존 코드)

def crawl(self) -> list[dict[str, Any]]:
    """서울시 전체 구/동을 순회하며 크롤링"""
    self.logger.info("crawling_start")

    # 체크포인트 로드
    checkpoint = self.checkpoint_manager.load()
    if checkpoint:
        self.logger.info("checkpoint_loaded", checkpoint=checkpoint["last_completed"])

    all_results: list[dict[str, Any]] = []
    url = self.get_url()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=self.config.headless)
        self.page: Page = browser.new_page()
        self.page.goto(url, timeout=self.config.timeout * 1000)
        self.page.wait_for_load_state("networkidle")

        self.logger.info("browser_ready")

        total_dongs = sum(
            len(district["dongs"]) for district in self.districts_data["districts"]
        )
        completed_count = 0

        for district in self.districts_data["districts"]:
            for dong in district["dongs"]:
                # 체크포인트에서 완료된 동 건너뛰기
                if self.checkpoint_manager.should_skip_dong(dong["cortarNo"]):
                    self.logger.info("skipping_completed_dong", dong=dong["dong_name"])
                    completed_count += 1
                    continue

                self.logger.info(
                    "crawling_dong",
                    district=district["district_name"],
                    dong=dong["dong_name"],
                    progress=f"{completed_count}/{total_dongs}",
                )

                results = self._fetch_with_retry(dong)
                all_results.extend(results)

                # 체크포인트 업데이트
                self.checkpoint_manager.checkpoint["last_completed"] = {
                    "district": district["district_name"],
                    "dong": dong["dong_name"],
                }
                self.checkpoint_manager.checkpoint.setdefault("completed_dongs", []).append(
                    dong["cortarNo"]
                )
                self.checkpoint_manager.checkpoint["total_complexes_crawled"] = len(
                    all_results
                )
                self.checkpoint_manager.save(self.checkpoint_manager.checkpoint)

                completed_count += 1

        browser.close()

    self.logger.info("crawling_complete", total_complexes=len(all_results))
    return all_results
```

**Step 4: Run test to verify it passes**

실행:
```bash
uv run pytest tests/unit/test_naver_crawler.py -v
```

예상 결과: 모든 테스트 PASS

**Step 5: Commit**

```bash
git add src/crawler/crawlers/naver.py tests/unit/test_naver_crawler.py
git commit -m "feat: 전체 크롤링 로직 구현 (crawl 메서드)"
```

---

## Task 7: CSV Writer append 모드 통합

**Files:**
- Modify: `src/crawler/writers/csv_writer.py`
- Modify: `tests/unit/test_csv_writer.py`

**Step 1: Write the failing test for append with existing headers**

`tests/unit/test_csv_writer.py`에 추가 (파일이 없으면 생성):

```python
import csv
from pathlib import Path

import pytest

from crawler.writers.csv_writer import CSVWriter


@pytest.fixture
def temp_csv_file(tmp_path: Path) -> Path:
    return tmp_path / "test.csv"


def test_append_to_existing_file_without_writing_header(temp_csv_file: Path) -> None:
    writer = CSVWriter(temp_csv_file)

    # 첫 번째 쓰기 (헤더 포함)
    data1 = [{"name": "Alice", "age": 30}]
    writer.write(data1)

    # 두 번째 쓰기 (헤더 없이 추가)
    data2 = [{"name": "Bob", "age": 25}, {"name": "Charlie", "age": 35}]
    writer.append(data2)

    # 파일 읽어서 검증
    with open(temp_csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 3
    assert rows[0]["name"] == "Alice"
    assert rows[1]["name"] == "Bob"
    assert rows[2]["name"] == "Charlie"
```

**Step 2: Run test to verify it passes (이미 구현되어 있음)**

실행:
```bash
uv run pytest tests/unit/test_csv_writer.py -v
```

예상 결과: 테스트 PASS (CSVWriter.append는 이미 구현되어 있음)

**Step 3: No changes needed (CSVWriter already supports append)**

CSVWriter는 이미 append 메서드를 지원하므로 추가 구현 불필요.

**Step 4: Commit test**

```bash
git add tests/unit/test_csv_writer.py
git commit -m "test: CSVWriter append 모드 테스트 추가"
```

---

## Task 8: main.py에 NaverRealEstateCrawler 통합

**Files:**
- Modify: `scripts/main.py`

**Step 1: Write the failing test for main script**

통합 테스트는 별도 파일에서 수행. 여기서는 main.py 수정만 진행.

**Step 2: Update main.py to use NaverRealEstateCrawler**

`scripts/main.py` 수정:

```python
import argparse
from datetime import datetime
from pathlib import Path

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler
from crawler.writers.csv_writer import CSVWriter


def main() -> None:
    parser = argparse.ArgumentParser(description="HomeSweetHome Crawler - 네이버 부동산")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="출력 파일 경로 (기본: output/seoul_apartments_{timestamp}.csv)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="중단된 지점부터 재개",
    )

    args = parser.parse_args()

    # 출력 파일명 생성
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"output/seoul_apartments_{timestamp}.csv")
    else:
        output_path = args.output

    config = CrawlerConfig.from_env()

    print("네이버 부동산 크롤링 시작...")
    if args.resume:
        print("체크포인트에서 재개합니다.")

    crawler = NaverRealEstateCrawler(config)
    results = crawler.crawl()

    writer = CSVWriter(output_path)

    # 첫 실행이면 write, 재개면 append
    if args.resume and output_path.exists():
        writer.append(results)
    else:
        writer.write(results)

    print(f"{len(results)}개 아파트 단지 정보를 {output_path}에 저장했습니다.")

    # 실패 리포트
    failed = crawler.checkpoint_manager.checkpoint.get("failed_dongs", [])
    if failed:
        print(f"\n실패한 동: {len(failed)}개")
        for fail in failed[:5]:  # 최대 5개만 출력
            print(f"  - {fail['dong_name']} ({fail['cortarNo']}): {fail['error']}")


if __name__ == "__main__":
    main()
```

**Step 3: Run main script to verify it works**

실행:
```bash
python scripts/main.py --output output/test_crawl.csv
```

예상 결과: 샘플 데이터 3개 동에서 크롤링 성공, CSV 파일 생성

**Step 4: Test resume functionality**

실행:
```bash
python scripts/main.py --output output/test_crawl.csv --resume
```

예상 결과: 체크포인트 로드, 이미 완료된 동 건너뛰기

**Step 5: Commit**

```bash
git add scripts/main.py
git commit -m "feat: main.py에 NaverRealEstateCrawler 통합"
```

---

## Task 9: 통합 테스트 작성

**Files:**
- Create: `tests/integration/test_naver_integration.py`

**Step 1: Write integration test**

`tests/integration/test_naver_integration.py` 파일을 생성:

```python
import pytest
from pathlib import Path

from crawler.config import CrawlerConfig
from crawler.crawlers.naver import NaverRealEstateCrawler
from crawler.writers.csv_writer import CSVWriter


@pytest.mark.integration
@pytest.mark.skip(reason="네트워크 의존 테스트 - 수동 실행")
def test_crawl_one_dong_and_save_to_csv(tmp_path: Path) -> None:
    """
    실제 네이버 부동산 API를 호출하여 1개 동만 크롤링하는 통합 테스트

    실행: pytest tests/integration/test_naver_integration.py -v -m integration
    """
    config = CrawlerConfig(timeout=30, headless=True, output_dir=str(tmp_path))
    crawler = NaverRealEstateCrawler(config)

    # 테스트용으로 1개 동만 크롤링
    districts_backup = crawler.districts_data
    crawler.districts_data = {
        "districts": [
            {
                "district_name": "강남구",
                "dongs": [districts_backup["districts"][0]["dongs"][0]],
            }
        ]
    }

    results = crawler.crawl()

    # 결과 검증
    assert len(results) > 0
    assert "complex_name" in results[0]
    assert "marker_id" in results[0]
    assert "latitude" in results[0]

    # CSV 저장 검증
    output_path = tmp_path / "test_output.csv"
    writer = CSVWriter(output_path)
    writer.write(results)

    assert output_path.exists()
    assert output_path.stat().st_size > 0


@pytest.mark.integration
@pytest.mark.skip(reason="체크포인트 복구 테스트 - 수동 실행")
def test_checkpoint_resume(tmp_path: Path) -> None:
    """
    체크포인트 저장 및 재개 기능 통합 테스트
    """
    config = CrawlerConfig(timeout=30, headless=True, output_dir=str(tmp_path))

    # 첫 번째 크롤링 (2개 동 중 1개만)
    crawler1 = NaverRealEstateCrawler(config)
    districts_data = crawler1.districts_data

    # 임의로 중단 시뮬레이션
    crawler1.districts_data = {
        "districts": [
            {
                "district_name": districts_data["districts"][0]["district_name"],
                "dongs": [districts_data["districts"][0]["dongs"][0]],
            }
        ]
    }

    results1 = crawler1.crawl()
    checkpoint_path = Path("output/checkpoint.json")
    assert checkpoint_path.exists()

    # 두 번째 크롤링 (재개)
    crawler2 = NaverRealEstateCrawler(config)
    checkpoint = crawler2.checkpoint_manager.load()
    assert checkpoint is not None
    assert len(checkpoint["completed_dongs"]) == 1

    results2 = crawler2.crawl()

    # 첫 번째 동은 건너뛰고 나머지만 크롤링
    total_results = len(results1) + len(results2)
    assert total_results > 0
```

**Step 2: Run integration test (optional)**

실행:
```bash
uv run pytest tests/integration/test_naver_integration.py -v -m integration
```

예상 결과: 테스트가 skip됨 (수동 실행용)

**Step 3: Commit**

```bash
git add tests/integration/test_naver_integration.py
git commit -m "test: 통합 테스트 추가 (네이버 부동산 크롤러)"
```

---

## Task 10: 최종 검증 및 문서 업데이트

**Files:**
- Modify: `README.md` (if needed)
- Modify: `CLAUDE.md` (if needed)

**Step 1: Run all tests**

실행:
```bash
uv run pytest tests/unit/ -v
```

예상 결과: 모든 단위 테스트 PASS

**Step 2: Run linting and type checking**

실행:
```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
```

예상 결과: 모든 검사 PASS

**Step 3: Test full crawl with sample data**

실행:
```bash
python scripts/main.py
```

예상 결과: 샘플 데이터(3개 동)에서 크롤링 성공, CSV 생성

**Step 4: Verify checkpoint functionality**

실행:
```bash
# 체크포인트 확인
cat output/checkpoint.json

# 재개 테스트
python scripts/main.py --resume
```

예상 결과: 이미 완료된 동 건너뛰기, 로그에 "skipping_completed_dong" 출력

**Step 5: Update documentation (if needed)**

CLAUDE.md나 README.md에 사용법 추가가 필요하면 업데이트

**Step 6: Final commit**

```bash
git add -A
git commit -m "docs: 최종 검증 완료 및 문서 업데이트"
```

---

## 실행 후 다음 단계

구현이 완료되면 다음 작업이 필요합니다:

1. **서울시 전체 데이터 수집**: `scripts/collect_seoul_data.py`의 `collect_seoul_districts()` 함수를 실제로 구현하여 서울시 25개 구, 400~500개 동의 cortarNo와 좌표를 수집합니다.

2. **실제 크롤링 테스트**: 수동으로 통합 테스트를 실행하여 실제 네이버 부동산 API가 정상 작동하는지 확인합니다.

3. **데이터 검증**: 크롤링된 CSV 데이터를 검토하여 누락된 필드나 잘못된 값이 없는지 확인합니다.

4. **성능 최적화**: 필요시 rate limiting 간격 조정, 병렬 처리 고려 등.

## 주의사항

- **법적/윤리적 준수**: 네이버 부동산 이용약관 확인 필요
- **Rate limiting**: 서버 부하 방지를 위해 0.5초 대기 유지
- **장시간 실행**: 서울시 전체 크롤링 시 10~15분 소요 예상
- **체크포인트**: 중단 시 `output/checkpoint.json` 확인하여 재개 가능
