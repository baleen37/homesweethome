# 호갱노노 API Integration 테스트 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 호갱노노 API 엔드포인트별 integration 테스트를 작성하여 데이터 누락 원인을 파악

**Architecture:**
- 실제 API를 호출하는 integration 테스트 작성
- TDD 방식으로 테스트 먼저 작성, 실패 확인 후 구현
- 각 API 엔드포인트별로 독립적인 테스트 작성
- 600개 제한, 세션 관리, Rate limiting 검증

**Tech Stack:**
- pytest (테스트 프레임워크)
- requests (HTTP 클라이언트)
- pytest markers (integration 테스트 표시)

---

## Task 1: `/api/v2/regions` API 테스트 작성

**Files:**
- Modify: `tests/integration/test_hogangnono_api_endpoints.py`

**Step 1: 기존 테스트 파일 확인**

Run: `cat tests/integration/test_hogangnono_api_endpoints.py | head -50`

Expected: 기존 테스트 구조 확인

**Step 2: regions API 테스트 작성**

`tests/integration/test_hogangnono_api_endpoints.py`에 추가:

```python
import time

@pytest.mark.integration
def test_regions_api():
    """전체 지역 목록 조회 API 검증

    `/api/v2/regions` API를 실제로 호출하여 응답 구조와 서울 25개 구 데이터 확인
    """
    # 세션 생성 및 쿠키 획득
    session = requests.Session()
    session.get("https://hogangnono.com")

    # regions API 호출
    response = session.get(
        "https://hogangnono.com/api/v2/regions",
        headers={"X-Requested-With": "XMLHttpRequest"}
    )

    assert response.status_code == 200, f"API 호출 실패: {response.status_code}"

    data = response.json()

    # 응답 구조 검증
    assert "data" in data, "응답에 'data' 필드가 없음"
    assert "regionList" in data["data"], "응답에 'regionList' 필드가 없음"

    # 서울특별시 찾기
    seoul = next((r for r in data["data"]["regionList"] if r["regionCode"] == "11"), None)
    assert seoul is not None, "서울특별시 데이터를 찾을 수 없음"
    assert seoul["name"] == "서울", f"서울 이름이 잘못됨: {seoul['name']}"

    # 서울 25개 구 검증
    assert "children" in seoul, "서울에 children 필드가 없음"
    assert len(seoul["children"]) == 25, f"서울 구 개수 오류: {len(seoul['children'])}개 (예상: 25개)"

    # 구 데이터 필드 검증
    for district in seoul["children"]:
        assert "regionCode" in district, f"구 데이터에 regionCode 없음: {district}"
        assert "name" in district, f"구 데이터에 name 없음: {district}"
        assert "fullName" in district, f"구 데이터에 fullName 없음: {district}"

    print(f"✓ 서울 25개 구 확인: {[d['name'] for d in seoul['children']]}")
```

**Step 3: 테스트 실행하여 통과 확인**

Run: `pytest tests/integration/test_hogangnono_api_endpoints.py::test_regions_api -v -s`

Expected: PASSED (서울 25개 구 목록 출력)

**Step 4: 커밋**

```bash
git add tests/integration/test_hogangnono_api_endpoints.py
git commit -m "test: regions API integration 테스트 추가

/api/v2/regions API 실제 호출 테스트:
- 세션 쿠키 획득 후 API 호출
- 응답 구조 검증 (data.regionList)
- 서울 25개 구 존재 확인
- 필수 필드 검증 (regionCode, name, fullName)"
```

---

## Task 2: 작은 bbox POI 조회 테스트 작성

**Files:**
- Modify: `tests/integration/test_hogangnono_api_endpoints.py`

**Step 1: 작은 bbox 테스트 작성**

`tests/integration/test_hogangnono_api_endpoints.py`에 추가:

```python
@pytest.mark.integration
def test_pois_bounding_small_bbox():
    """작은 bbox로 POI 조회 (600개 제한 안 걸림)

    `/api/v2/pois-bounding` API를 작은 bbox로 호출하여
    600개 제한에 걸리지 않는 정상 동작 확인
    """
    # 세션 생성 및 쿠키 획득
    session = requests.Session()
    session.get("https://hogangnono.com")

    # 작은 bbox 파라미터 (0.01도 = 약 1km)
    params = {
        "level": 16,
        "startX": 127.00,
        "endX": 127.01,
        "startY": 37.50,
        "endY": 37.51,
        "types": "1"  # 아파트만
    }

    response = session.get(
        "https://hogangnono.com/api/v2/pois-bounding",
        params=params
    )

    assert response.status_code == 200, f"API 호출 실패: {response.status_code}"

    data = response.json()

    assert "data" in data, "응답에 'data' 필드가 없음"
    assert isinstance(data["data"], list), f"data는 list여야 함: {type(data['data'])}"

    poi_count = len(data["data"])
    assert poi_count < 600, f"600개 제한에 걸림: {poi_count}개"

    # POI 필드 검증
    if poi_count > 0:
        poi = data["data"][0]
        required_fields = ["id", "name", "lat", "lng", "category", "address"]
        for field in required_fields:
            assert field in poi, f"POI에 {field} 필드 없음: {poi.keys()}"

        assert poi["category"] == 1, f"category=1(아파트)여야 함: {poi['category']}"

    print(f"✓ 작은 bbox: {poi_count}개 POI (600개 제한 안 걸림)")
```

**Step 2: 테스트 실행하여 통과 확인**

Run: `pytest tests/integration/test_hogangnono_api_endpoints.py::test_pois_bounding_small_bbox -v -s`

Expected: PASSED (POI 개수 출력)

**Step 3: 커밋**

```bash
git add tests/integration/test_hogangnono_api_endpoints.py
git commit -m "test: pois-bounding API 작은 bbox 테스트 추가

작은 bbox (0.01도 = 약 1km) 테스트:
- POI 데이터 구조 검증
- 필수 필드 확인 (id, name, lat, lng, category, address)
- category=1 (아파트) 필터링 확인
- 600개 제한 안 걸리는지 확인"
```

---

## Task 3: 600개 제한 감지 테스트 작성

**Files:**
- Modify: `tests/integration/test_hogangnono_api_endpoints.py`

**Step 1: 600개 제한 감지 테스트 작성**

`tests/integration/test_hogangnono_api_endpoints.py`에 추가:

```python
@pytest.mark.integration
def test_pois_bounding_600_limit_detection():
    """큰 bbox로 600개 제한 감지

    큰 bbox로 API를 호출하여 600개 제한에 걸리는지 확인
    데이터 누락의 주요 원인 파악
    """
    # 세션 생성
    session = requests.Session()
    session.get("https://hogangnono.com")

    # 큰 bbox 파라미터 (강남 전체를 커버)
    params = {
        "level": 16,
        "startX": 127.00,
        "endX": 127.10,  # 10km 범위
        "startY": 37.45,
        "endY": 37.55,
        "types": "1"
    }

    response = session.get(
        "https://hogangnono.com/api/v2/pois-bounding",
        params=params
    )

    assert response.status_code == 200, f"API 호출 실패: {response.status_code}"

    data = response.json()
    poi_count = len(data["data"])

    print(f"큰 bbox POI 개수: {poi_count}")

    # 600개 제한 감지
    if poi_count == 600:
        print("⚠️  600개 제한 감지 - bbox 분할 필요!")
        print("이 지역은 데이터가 잘렸을 가능성 높음")
        # 600개 제한에 걸린 경우 경고만 하고 테스트 통과
        assert True
    else:
        print(f"✓ 600개 제한 안 걸림: {poi_count}개")
        assert poi_count < 600
```

**Step 2: 테스트 실행하여 600개 제한 확인**

Run: `pytest tests/integration/test_hogangnono_api_endpoints.py::test_pois_bounding_600_limit_detection -v -s`

Expected: PASSED (600개 제한 감지 메시지 출력 가능성)

**Step 3: 커밋**

```bash
git add tests/integration/test_hogangnono_api_endpoints.py
git commit -m "test: 600개 제한 감지 테스트 추가

큰 bbox (10km 범위)로 600개 제한 감지:
- 정확히 600개 응답 시 경고 출력
- 데이터 누락의 주요 원인 파악
- bbox 분할 필요성 확인"
```

---

## Task 4: 강남구 중심 bbox 테스트 작성

**Files:**
- Modify: `tests/integration/test_hogangnono_api_endpoints.py`

**Step 1: 강남구 중심 테스트 작성**

`tests/integration/test_hogangnono_api_endpoints.py`에 추가:

```python
@pytest.mark.integration
def test_gangnam_district_poi_collection():
    """강남구 중심 좌표로 POI 수집

    강남구 중심 좌표 기반으로 2km x 2km 영역의 아파트 데이터 수집
    모든 POI가 강남구인지 확인
    """
    # 세션 생성
    session = requests.Session()
    session.get("https://hogangnono.com")

    # 강남구 중심 좌표 (hogangnono_api_analysis_report.md 기준)
    gangnam_center = (37.5172, 127.0473)

    # 0.01도 간격 bbox (약 2km x 2km)
    params = {
        "level": 16,
        "startX": gangnam_center[1] - 0.01,
        "endX": gangnam_center[1] + 0.01,
        "startY": gangnam_center[0] - 0.01,
        "endY": gangnam_center[0] + 0.01,
        "types": "1"
    }

    response = session.get(
        "https://hogangnono.com/api/v2/pois-bounding",
        params=params
    )

    assert response.status_code == 200, f"API 호출 실패: {response.status_code}"

    data = response.json()
    apartments = data["data"]

    # 최소한 아파트가 있어야 함
    assert len(apartments) > 0, "강남구 중심에서 아파트를 찾지 못함"

    # 모든 POI 검증
    gangnam_count = 0
    for apt in apartments:
        assert apt["category"] == 1, f"category가 아파트가 아님: {apt['category']}"

        # 주소에 강남구가 포함되어야 함
        if "강남구" in apt["address"]:
            gangnam_count += 1

    # 대부분이 강남구여야 함 (bbox 경계에 걸친 다른 구 POI 일부 포함 가능)
    gangnam_ratio = gangnam_count / len(apartments)
    assert gangnam_ratio > 0.8, f"강남구 비율이 너무 낮음: {gangnam_ratio:.1%}"

    print(f"✓ 강남구 중심 2km x 2km: {len(apartments)}개 아파트")
    print(f"  강남구 POI: {gangnam_count}개 ({gangnam_ratio:.1%})")
```

**Step 2: 테스트 실행**

Run: `pytest tests/integration/test_hogangnono_api_endpoints.py::test_gangnam_district_poi_collection -v -s`

Expected: PASSED (강남구 아파트 개수 출력)

**Step 3: 커밋**

```bash
git add tests/integration/test_hogangnono_api_endpoints.py
git commit -m "test: 강남구 중심 POI 수집 테스트 추가

강남구 중심 좌표 (37.5172, 127.0473) 기반:
- 2km x 2km 영역 아파트 수집
- 모든 POI category=1 확인
- 강남구 주소 비율 검증 (80% 이상)"
```

---

## Task 5: 세션 관리 테스트 작성

**Files:**
- Modify: `tests/integration/test_hogangnono_api_endpoints.py`

**Step 1: 세션 쿠키 필요성 테스트 작성**

`tests/integration/test_hogangnono_api_endpoints.py`에 추가:

```python
@pytest.mark.integration
def test_session_cookie_requirement():
    """세션 쿠키 필요 여부 확인

    쿠키 없이 API 호출 vs 쿠키 있을 때 API 호출 비교
    세션 관리의 필요성 확인
    """
    # 1. 쿠키 없이 호출
    response_no_cookie = requests.get(
        "https://hogangnono.com/api/v2/regions",
        headers={"X-Requested-With": "XMLHttpRequest"}
    )

    # 2. 메인 페이지 접속 후 쿠키 획득
    session = requests.Session()
    main_response = session.get("https://hogangnono.com")
    assert main_response.status_code == 200, "메인 페이지 접속 실패"

    response_with_cookie = session.get(
        "https://hogangnono.com/api/v2/regions",
        headers={"X-Requested-With": "XMLHttpRequest"}
    )

    # 결과 비교
    print(f"쿠키 없음: {response_no_cookie.status_code}")
    print(f"쿠키 있음: {response_with_cookie.status_code}")

    # 쿠키 있을 때는 반드시 성공
    assert response_with_cookie.status_code == 200, "세션이 있어도 API 호출 실패"

    # 쿠키 없이도 성공하는지 확인
    if response_no_cookie.status_code == 200:
        print("✓ 세션 쿠키 없이도 API 호출 가능")
    else:
        print("⚠️  세션 쿠키 필요 - 메인 페이지 접속 후 쿠키 획득 필수")
```

**Step 2: 테스트 실행**

Run: `pytest tests/integration/test_hogangnono_api_endpoints.py::test_session_cookie_requirement -v -s`

Expected: PASSED (세션 쿠키 필요 여부 확인)

**Step 3: 커밋**

```bash
git add tests/integration/test_hogangnono_api_endpoints.py
git commit -m "test: 세션 쿠키 필요성 테스트 추가

쿠키 없이 vs 쿠키 있을 때 API 호출 비교:
- 메인 페이지 접속으로 쿠키 획득
- regions API 호출 성공 여부 확인
- 세션 관리 필요성 파악"
```

---

## Task 6: Rate Limiting 테스트 작성

**Files:**
- Modify: `tests/integration/test_hogangnono_api_endpoints.py`

**Step 1: Rate limiting 테스트 작성**

`tests/integration/test_hogangnono_api_endpoints.py`에 추가:

```python
@pytest.mark.integration
@pytest.mark.slow
def test_rate_limiting_policy():
    """Rate limiting 정책 확인

    연속 10회 API 호출로 429 에러 발생 여부 확인
    안전한 요청 간격 파악
    """
    # 세션 생성
    session = requests.Session()
    session.get("https://hogangnono.com")

    params = {
        "level": 16,
        "startX": 127.00,
        "endX": 127.01,
        "startY": 37.50,
        "endY": 37.51,
        "types": "1"
    }

    # 연속 10회 호출
    status_codes = []
    response_times = []

    print("\n연속 API 호출 테스트 (0.5초 간격):")
    for i in range(10):
        start_time = time.time()

        response = session.get(
            "https://hogangnono.com/api/v2/pois-bounding",
            params=params
        )

        elapsed = time.time() - start_time
        status_codes.append(response.status_code)
        response_times.append(elapsed)

        print(f"  {i+1}. Status: {response.status_code}, Time: {elapsed:.2f}s")

        time.sleep(0.5)  # 0.5초 간격

    # 429 (Too Many Requests) 발생 여부
    has_rate_limit = 429 in status_codes

    if has_rate_limit:
        print("\n⚠️  Rate limiting 감지 - 요청 간격 조정 필요")
        rate_limit_index = status_codes.index(429)
        print(f"   {rate_limit_index + 1}번째 요청에서 429 에러")
    else:
        print("\n✓ 0.5초 간격으로 10회 연속 호출 성공")

    # 최소 일부는 성공해야 함
    success_count = status_codes.count(200)
    assert success_count > 0, f"모든 요청 실패: {status_codes}"

    # 평균 응답 시간
    avg_time = sum(response_times) / len(response_times)
    print(f"   평균 응답 시간: {avg_time:.2f}s")
```

**Step 2: 테스트 실행**

Run: `pytest tests/integration/test_hogangnono_api_endpoints.py::test_rate_limiting_policy -v -s`

Expected: PASSED (Rate limiting 정책 확인, 약 5-6초 소요)

**Step 3: 커밋**

```bash
git add tests/integration/test_hogangnono_api_endpoints.py
git commit -m "test: Rate limiting 정책 테스트 추가

연속 10회 API 호출 (0.5초 간격):
- 429 에러 발생 여부 확인
- 응답 시간 측정
- 안전한 요청 간격 파악
- pytest.mark.slow 마커 추가"
```

---

## Task 7: Fixture Recorder 구현

**Files:**
- Create: `tests/helpers/record_fixtures.py`

**Step 1: Fixture recorder 스크립트 작성**

Create `tests/helpers/record_fixtures.py`:

```python
"""API 응답 Fixture 수집 스크립트

실제 호갱노노 API를 호출하여 응답을 JSON 파일로 저장합니다.
API 변경 감지 및 파싱 로직 단위 테스트용으로 사용됩니다.
"""

import json
import requests
from pathlib import Path


def record_fixtures() -> None:
    """필요 최소한의 fixtures만 수집"""
    print("호갱노노 API Fixtures 수집 시작...")

    # 세션 생성 및 쿠키 획득
    session = requests.Session()
    print("1. 메인 페이지 접속 (쿠키 획득)...")
    session.get("https://hogangnono.com")

    # Fixtures 디렉토리 생성
    fixtures_dir = Path("tests/fixtures")
    fixtures_dir.mkdir(exist_ok=True)

    # 1. regions API 응답 저장
    print("2. /api/v2/regions API 호출...")
    resp = session.get(
        "https://hogangnono.com/api/v2/regions",
        headers={"X-Requested-With": "XMLHttpRequest"}
    )

    if resp.status_code == 200:
        save_json(fixtures_dir / "hogangnono_regions_response.json", resp.json())
        print("   ✓ regions API 응답 저장")
    else:
        print(f"   ✗ regions API 실패: {resp.status_code}")

    # 2. pois-bounding API 샘플 저장
    print("3. /api/v2/pois-bounding API 호출...")
    resp = session.get(
        "https://hogangnono.com/api/v2/pois-bounding",
        params={
            "level": 16,
            "startX": 127.0,
            "endX": 127.01,
            "startY": 37.5,
            "endY": 37.51,
            "types": "1"
        }
    )

    if resp.status_code == 200:
        save_json(fixtures_dir / "hogangnono_pois_sample.json", resp.json())
        print("   ✓ pois-bounding API 응답 저장")
    else:
        print(f"   ✗ pois-bounding API 실패: {resp.status_code}")

    print("\n✓ Fixtures 저장 완료")


def save_json(path: Path, data: dict) -> None:
    """JSON 파일 저장"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    record_fixtures()
```

**Step 2: Fixture recorder 실행**

Run: `python tests/helpers/record_fixtures.py`

Expected: Fixtures 저장 완료 메시지

**Step 3: 생성된 파일 확인**

Run: `ls -la tests/fixtures/`

Expected: `hogangnono_regions_response.json`, `hogangnono_pois_sample.json` 존재

**Step 4: 커밋**

```bash
git add tests/helpers/record_fixtures.py tests/fixtures/
git commit -m "feat: Fixture recorder 구현

실제 API 응답을 JSON으로 저장:
- regions API 응답
- pois-bounding API 응답 샘플
- API 변경 감지 및 단위 테스트용"
```

---

## Task 8: pytest markers 설정

**Files:**
- Modify: `pytest.ini` (또는 `pyproject.toml`)

**Step 1: pytest.ini에 integration 마커 추가**

Create or modify `pytest.ini`:

```ini
[pytest]
markers =
    integration: Integration tests that call real APIs (slow)
    slow: Slow tests (e.g., rate limiting tests)
```

**Step 2: pyproject.toml 사용 시**

If using `pyproject.toml`, add:

```toml
[tool.pytest.ini_options]
markers = [
    "integration: Integration tests that call real APIs (slow)",
    "slow: Slow tests (e.g., rate limiting tests)",
]
```

**Step 3: 마커 동작 확인**

Run: `pytest tests/integration/test_hogangnono_api_endpoints.py -m integration -v`

Expected: integration 마커가 있는 테스트만 실행

**Step 4: 커밋**

```bash
git add pytest.ini  # or pyproject.toml
git commit -m "config: pytest integration 마커 설정

integration, slow 마커 추가:
- integration: 실제 API 호출 테스트
- slow: 느린 테스트 (rate limiting 등)"
```

---

## Task 9: 전체 테스트 실행 및 결과 분석

**Files:**
- None (테스트 실행만)

**Step 1: Integration 테스트 전체 실행**

Run: `pytest tests/integration/test_hogangnono_api_endpoints.py -m integration -v -s`

Expected: 모든 테스트 실행 및 결과 확인

**Step 2: 결과 분석 및 기록**

Create `docs/test-results/2025-12-09-api-integration-results.md`:

```markdown
# API Integration 테스트 결과

**실행일**: 2025-12-09
**테스트 파일**: `tests/integration/test_hogangnono_api_endpoints.py`

## 테스트 결과 요약

| 테스트 | 결과 | 비고 |
|--------|------|------|
| test_regions_api | PASS/FAIL | [결과 설명] |
| test_pois_bounding_small_bbox | PASS/FAIL | [POI 개수] |
| test_pois_bounding_600_limit_detection | PASS/FAIL | [600개 제한 여부] |
| test_gangnam_district_poi_collection | PASS/FAIL | [강남구 POI 개수] |
| test_session_cookie_requirement | PASS/FAIL | [쿠키 필요 여부] |
| test_rate_limiting_policy | PASS/FAIL | [Rate limiting 감지 여부] |

## 주요 발견사항

### 1. 600개 제한
- [감지 여부 및 영향받는 bbox 크기]

### 2. 세션 관리
- [쿠키 필요 여부]

### 3. Rate Limiting
- [안전한 요청 간격]

## 데이터 누락 원인 분석

[테스트 결과 기반 분석]

## 다음 단계

[크롤러 개선 방향]
```

**Step 3: 테스트 결과 문서 커밋**

```bash
git add docs/test-results/2025-12-09-api-integration-results.md
git commit -m "docs: API integration 테스트 결과 기록

6개 테스트 실행 결과:
- 600개 제한 감지 여부
- 세션 쿠키 필요성
- Rate limiting 정책
- 데이터 누락 원인 분석"
```

---

## Task 10: README 업데이트

**Files:**
- Modify: `README.md` or `CLAUDE.md`

**Step 1: 테스트 실행 방법 추가**

`CLAUDE.md`의 "테스트" 섹션에 추가:

```markdown
### Integration 테스트 실행

```bash
# API 엔드포인트별 integration 테스트
pytest tests/integration/test_hogangnono_api_endpoints.py -m integration -v

# 특정 테스트만 실행
pytest tests/integration/test_hogangnono_api_endpoints.py::test_regions_api -v

# Rate limiting 테스트 제외 (느림)
pytest tests/integration/test_hogangnono_api_endpoints.py -m "integration and not slow" -v
```

### Fixture 수집

```bash
# API 응답 fixtures 수집
python tests/helpers/record_fixtures.py
```
```

**Step 2: 커밋**

```bash
git add CLAUDE.md
git commit -m "docs: Integration 테스트 실행 방법 추가

CLAUDE.md에 추가:
- API integration 테스트 실행 명령
- Fixture 수집 방법
- pytest 마커 활용법"
```

---

## 검증 체크리스트

구현 완료 후 다음 항목 확인:

- [ ] 6개 integration 테스트 모두 작성됨
- [ ] 모든 테스트가 `@pytest.mark.integration` 마커 포함
- [ ] Fixture recorder 스크립트 정상 동작
- [ ] pytest markers 설정 완료
- [ ] 테스트 결과 문서 작성
- [ ] README/CLAUDE.md 업데이트
- [ ] 모든 변경사항 커밋됨

---

## 참고 자료

- 설계 문서: `docs/plans/2025-12-09-fixture-based-testing-design.md`
- API 분석 보고서: `hogangnono_api_analysis_report.md`
- 기존 테스트: `tests/integration/test_hogangnono_api_endpoints.py`
- @superpowers:test-driven-development - TDD 방법론
- @superpowers:verification-before-completion - 완료 전 검증
