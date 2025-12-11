# Hogangnono API MVP Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Stabilize and optimize the hogangnono API integration by implementing rate limiting fixes, header standardization, session management improvements, and minimal bounding box division to handle the 600 POI limit.

**Architecture:** Fix existing hogangnono client implementation with minimal changes while maintaining backward compatibility. Focus on API guide compliance and robust error handling.

**Tech Stack:** Python, requests, pytest, dataclasses, asyncio

---

## Task 1: Fix Rate Limiting Settings

**Files:**
- Modify: `src/crawler/api/hogangnono_client.py:402-406`
- Test: `tests/unit/test_hogangnono_client.py`

**Step 1: Write failing test for rate limiting values**

```python
# tests/unit/test_hogangnono_client.py
def test_rate_limiting_initial_values():
    """Rate limiting should start at 2s with 1s minimum (per API guide)"""
    client = HogangnonoClient(CrawlerConfig())

    # Check initial values
    assert client.rate_limiter.current_delay == 2.0, f"Expected 2.0, got {client.rate_limiter.current_delay}"
    assert client.rate_limiter.min_delay == 1.0, f"Expected 1.0, got {client.rate_limiter.min_delay}"

    # Check bounds
    assert client.rate_limiter.max_delay == 10.0
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_hogangnono_client.py::test_rate_limiting_initial_values -v
```
Expected: FAIL with assertion error (current values are 5.0 and 1.5)

**Step 3: Update rate limiting initialization**

```python
# src/crawler/api/hogangnono_client.py (in __init__ method)
self.rate_limiter = AdaptiveRateLimiter(
    initial_delay=2.0,  # Changed from 5.0 to 2.0 per API guide
    min_delay=1.0,     # Changed from 1.5 to 1.0 per API guide
    max_delay=10.0
)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_hogangnono_client.py::test_rate_limiting_initial_values -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/crawler/api/hogangnono_client.py tests/unit/test_hogangnono_client.py
git commit -m "fix: adjust rate limiting to API guide recommendations (2s initial, 1s min)"
```

---

## Task 2: Standardize Required Headers

**Files:**
- Modify: `src/crawler/api/hogangnono_client.py`
- Test: `tests/unit/test_hogangnono_client.py`

**Step 1: Write failing test for required headers**

```python
# tests/unit/test_hogangnono_client.py
def test_required_headers_always_present():
    """All API requests must include required headers per API guide"""
    client = HogangnonoClient(CrawlerConfig())
    headers = client._get_api_headers()

    required_headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://hogangnono.com/",
        "Origin": "https://hogangnono.com"
    }

    for key, value in required_headers.items():
        assert key in headers, f"Missing required header: {key}"
        assert headers[key] == value, f"Incorrect {key}: expected {value}, got {headers[key]}"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_hogangnono_client.py::test_required_headers_always_present -v
```
Expected: FAIL if headers are missing or incorrect

**Step 3: Add header constants and ensure they're always included**

```python
# src/crawler/api/hogangnono_client.py (add at module level)
_REQUIRED_HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://hogangnono.com/",
    "Origin": "https://hogangnono.com"
}

# Modify _get_api_headers method to always include required headers
def _get_api_headers(self) -> dict:
    """Get standard API headers with all required fields"""
    headers = {
        "User-Agent": self.user_agent,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        **_REQUIRED_HEADERS  # Ensure all required headers are included
    }
    return headers
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_hogangnono_client.py::test_required_headers_always_present -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/crawler/api/hogangnono_client.py tests/unit/test_hogangnono_client.py
git commit -m "feat: standardize required API headers per API guide"
```

---

## Task 3: Add Session Auto-Recovery on Auth Errors

**Files:**
- Modify: `src/crawler/api/hogangnono_client.py`
- Test: `tests/unit/test_hogangnono_client.py`

**Step 1: Write failing test for session recovery**

```python
# tests/unit/test_hogangnono_client.py
def test_session_recovery_on_401():
    """Should automatically reinitialize session on 401/403 errors"""
    import requests_mock

    config = CrawlerConfig()
    client = HogangnonoClient(config)

    with requests_mock.Mocker() as m:
        # First call returns 401
        m.get("https://hogangnono.com/api/v2/regions",
              status_code=401,
              json={"error": "Unauthorized"})

        # Session reinitialization
        m.get("https://hogangnono.com/", status_code=200)

        # Second call after reinit succeeds
        m.get("https://hogangnono.com/api/v2/regions",
              status_code=200,
              json={"data": {"regionList": []}, "status": "success"})

        # Should succeed after auto-recovery
        response = client.get_regions()
        assert response.success
        assert client._session_initialized == True
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_hogangnono_client.py::test_session_recovery_on_401 -v
```
Expected: FAIL (session recovery not implemented)

**Step 3: Implement session recovery logic**

```python
# src/crawler/api/hogangnono_client.py (modify _make_request method)
def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
    """Make HTTP request with session management"""
    self._initialize_session()

    response = self.session.request(method, url, **kwargs)

    # Auto-recover from auth errors
    if response.status_code in [401, 403]:
        self._session_initialized = False
        self._initialize_session()
        response = self.session.request(method, url, **kwargs)

    return response
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_hogangnono_client.py::test_session_recovery_on_401 -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/crawler/api/hogangnono_client.py tests/unit/test_hogangnono_client.py
git commit -m "feat: add automatic session recovery on auth errors (401/403)"
```

---

## Task 4: Implement Simple Bounding Box Division

**Files:**
- Modify: `src/crawler/crawlers/hogangnono.py`
- Test: `tests/unit/test_hogangnono.py`

**Step 1: Write failing test for bbox division**

```python
# tests/unit/test_hogangnono.py
def test_simple_bbox_division():
    """Should divide bounding box into 2x2 grid to handle 600 POI limit"""
    crawler = HogangnonoCrawler()

    bbox = {
        "startX": 126.0,
        "endX": 128.0,
        "startY": 37.0,
        "endY": 38.0
    }

    divided = crawler._divide_bounding_box(bbox)

    # Should return 4 boxes
    assert len(divided) == 4, f"Expected 4 boxes, got {len(divided)}"

    # Check first box (bottom-left)
    assert divided[0]["startX"] == 126.0
    assert divided[0]["endX"] == 127.0
    assert divided[0]["startY"] == 37.0
    assert divided[0]["endY"] == 37.5

    # Check last box (top-right)
    assert divided[3]["startX"] == 127.0
    assert divided[3]["endX"] == 128.0
    assert divided[3]["startY"] == 37.5
    assert divided[3]["endY"] == 38.0
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_hogangnono.py::test_simple_bbox_division -v
```
Expected: FAIL (method doesn't exist)

**Step 3: Implement simple bbox division**

```python
# src/crawler/crawlers/hogangnono.py (add new method)
def _divide_bounding_box(self, bbox: dict, grid_size: int = 2) -> list[dict]:
    """Divide bounding box into grid to overcome 600 POI limit

    Args:
        bbox: Dictionary with startX, endX, startY, endY
        grid_size: Number of divisions per side (default 2x2)

    Returns:
        List of bbox dictionaries
    """
    x_range = bbox["endX"] - bbox["startX"]
    y_range = bbox["endY"] - bbox["startY"]

    x_step = x_range / grid_size
    y_step = y_range / grid_size

    boxes = []
    for i in range(grid_size):
        for j in range(grid_size):
            box = {
                "startX": bbox["startX"] + (i * x_step),
                "endX": bbox["startX"] + ((i + 1) * x_step),
                "startY": bbox["startY"] + (j * y_step),
                "endY": bbox["startY"] + ((j + 1) * y_step)
            }
            boxes.append(box)

    return boxes

# Modify _fetch_apartments_in_district to use division
def _fetch_apartments_in_district(self, district_info):
    """Fetch apartments with bbox division if needed"""
    # Get bounding box for district
    bbox = self._get_district_bbox(district_info)

    # Try with single bbox first
    apartments = self.api_client.get_pois_bounding(
        startX=bbox["startX"],
        endX=bbox["endX"],
        startY=bbox["startY"],
        endY=bbox["endY"],
        level=14,
        apt=""
    )

    # If exactly 600 results, likely truncated - divide and retry
    if len(apartments.data) == 600:
        all_apartments = []
        divided_boxes = self._divide_bounding_box(bbox)

        for sub_bbox in divided_boxes:
            sub_apartments = self.api_client.get_pois_bounding(
                startX=sub_bbox["startX"],
                endX=sub_bbox["endX"],
                startY=sub_bbox["startY"],
                endY=sub_bbox["endY"],
                level=14,
                apt=""
            )
            all_apartments.extend(sub_apartments.data)

        apartments.data = all_apartments

    return apartments
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_hogangnono.py::test_simple_bbox_division -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add src/crawler/crawlers/hogangnono.py tests/unit/test_hogangnono.py
git commit -m "feat: implement simple 2x2 bbox division to handle 600 POI limit"
```

---

## Task 5: Add Integration Test for POI Limit Handling

**Files:**
- Modify: `tests/integration/test_hogangnono_api_endpoints.py`

**Step 1: Add POI limit detection test**

```python
# tests/integration/test_hogangnono_api_endpoints.py
@pytest.mark.integration
@pytest.mark.slow
def test_pois_bounding_limit_detection(client):
    """Should handle 600 POI limit by dividing bounding box"""
    # Use dense area like Gangnam-gu
    gangnam_bbox = {
        "startX": 127.04,
        "endX": 127.12,
        "startY": 37.48,
        "endY": 37.52
    }

    # Get apartments with bbox division
    apartments = []
    divided_boxes = client._divide_bounding_box(gangnam_bbox)

    assert len(divided_boxes) == 4, "Should divide into 4 boxes"

    for bbox in divided_boxes:
        response = client.get_pois_bounding(
            startX=bbox["startX"],
            endX=bbox["endX"],
            startY=bbox["startY"],
            endY=bbox["endY"],
            level=14,
            apt=""
        )
        assert response.success
        apartments.extend(response.data)

    # Should collect more than 600 apartments total
    assert len(apartments) > 600, f"Expected >600 apartments, got {len(apartments)}"
```

**Step 2: Run integration test**

```bash
pytest tests/integration/test_hogangnono_api_endpoints.py::test_pois_bounding_limit_detection -v -s
```
Expected: PASS (takes ~10 seconds due to rate limiting)

**Step 3: Commit**

```bash
git add tests/integration/test_hogangnono_api_endpoints.py
git commit -m "test: add integration test for POI limit handling with bbox division"
```

---

## Task 6: Update CI to Skip Slow Tests by Default

**Files:**
- Modify: `.github/workflows/ci.yml`

**Step 1: Update CI workflow to exclude slow tests**

```yaml
# .github/workflows/ci.yml (modify test step)
- name: Run Tests
  run: |
    # Run all tests except slow ones by default
    pytest tests/unit -v --cov=src
    pytest tests/integration -v -m "not slow"

    # Report coverage
    pytest --cov=src --cov-report=xml
```

**Step 2: Run test to verify CI config**

```bash
# Test locally that slow tests are skipped
pytest tests/integration -v -m "not slow"
# Should run integration tests quickly
```

**Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: skip slow integration tests by default for faster CI"
```

---

## Task 7: Add Documentation

**Files:**
- Modify: `docs/guides/hogangnono-api-guide.md`
- Create: `docs/implementation/bbox-division.md`

**Step 1: Update API guide with implementation notes**

```markdown
# docs/guides/hogangnono-api-guide.md (append to FAQ)

### Implementation Notes

#### Bounding Box Division
Our implementation automatically divides bounding boxes when 600 POIs are detected:
- Uses simple 2x2 grid division (4 sub-boxes)
- Automatically retries with divided boxes when limit reached
- Maintains rate limiting across all sub-requests

#### Rate Limiting
We've optimized our rate limiting based on API guide recommendations:
- Initial delay: 2 seconds (reduced from 5)
- Minimum delay: 1 second (reduced from 1.5)
- Adaptive adjustment based on API responses

#### Session Management
- Automatic recovery on 401/403 errors
- Session cookies managed transparently
- Headers standardized per API guide requirements
```

**Step 2: Create bbox division documentation**

```markdown
# docs/implementation/bbox-division.md

# Bounding Box Division Implementation

## Overview
To overcome the 600 POI limit in `/api/v2/pois-bounding`, we implement automatic bounding box division.

## Algorithm
1. Make initial request with full bbox
2. If exactly 600 results returned, divide bbox into 2x2 grid
3. Request each sub-bbox sequentially
4. Aggregate all results

## Example
```python
# Dense area like Gangnam-gu
bbox = {"startX": 127.04, "endX": 127.12, "startY": 37.48, "endY": 37.52}
divided = crawler._divide_bounding_box(bbox)  # Returns 4 boxes
```

## Performance Impact
- Increases API calls from 1 to 4 for dense areas
- Total time increases proportionally (4x with rate limiting)
- Necessary for complete data collection in dense areas
```

**Step 3: Commit**

```bash
git add docs/guides/hogangnono-api-guide.md docs/implementation/bbox-division.md
git commit -m "docs: add implementation notes and bbox division documentation"
```

---

## Summary of Changes

This plan implements the MVP improvements to stabilize and optimize the hogangnono API integration:

1. **Rate limiting optimization** - Reduced delays per API guide
2. **Header standardization** - All required headers always included
3. **Session auto-recovery** - Handles 401/403 errors transparently
4. **Bounding box division** - Overcomes 600 POI limit with 2x2 grid
5. **Integration testing** - Verifies real-world API behavior
6. **CI optimization** - Faster feedback by skipping slow tests
7. **Documentation** - Clear implementation guidance

All changes are minimal and backward compatible, focusing on stability and API guide compliance.

**Plan complete and saved to `docs/plans/2025-01-11-hogangnono-api-mvp.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
