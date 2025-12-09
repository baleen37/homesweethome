# 호갱노노 API Integration 테스트 설계

**작성일**: 2025-12-09
**업데이트**: 2025-12-09 (실제 API 구조 반영)
**목적**: 호갱노노 크롤러의 데이터 누락 문제를 API별 integration test로 파악하고 개선

## 문제 정의

현재 `main.py` 실행 시 `hogangnono_complexes.csv`와 `hogangnono_transactions.csv`에 예상보다 훨씬 적은 데이터만 수집됨 (약 600개). 실제 호갱노노에는 더 많은 데이터가 있으나 크롤러가 일부만 수집하고 있으며, 어디서 데이터를 놓치는지 파악이 필요함.

## 실제 API 구조 분석

`hogangnono_api_analysis_report.md` 분석 결과:

1. **API 엔드포인트**:
   - `/api/v2/regions` - 전체 지역 목록 (시/도 > 구/군)
   - `/api/v2/pois-bounding` - bbox 기반 POI 조회 (아파트 단지 정보)
   - `/api/v2/searches/suggestions/new` - 검색 기반 지역 제안

2. **주요 제약사항**:
   - bbox당 최대 600개 제한
   - 페이지네이션 없음
   - 세션 쿠키 필요
   - 좌표 기반 시스템 (지역명 기반 API 없음)

3. **데이터 누락 가설**:
   - bbox 크기가 너무 커서 600개 제한에 걸림
   - 밀집 지역(강남, 서초 등)에서 600개 이후 데이터가 잘림
   - 크롤러가 600개 제한을 감지하지 못하고 넘어감

## 해결 방안

**Integration 테스트 위주** 전략:
- 각 API 엔드포인트를 실제로 호출해서 검증
- API 응답 구조, 필드, 제약사항 확인
- E2E 테스트는 별도 (전체 크롤링 흐름)

**Fixture는 최소화**:
- API 변경 감지용으로만 사용
- 간단한 파싱 로직 단위 테스트용

---

## 1. API별 Integration 테스트

### 1.1. `/api/v2/regions` API 테스트

**목적**: 전체 지역 목록 조회 API 검증

```python
# tests/integration/test_hogangnono_api_endpoints.py

def test_regions_api():
    """전체 지역 목록 조회 API 검증"""
    response = requests.get(
        "https://hogangnono.com/api/v2/regions",
        headers={"X-Requested-With": "XMLHttpRequest"}
    )

    assert response.status_code == 200
    data = response.json()

    # 응답 구조 검증
    assert "data" in data
    assert "regionList" in data["data"]

    # 서울특별시 찾기
    seoul = next((r for r in data["data"]["regionList"] if r["regionCode"] == "11"), None)
    assert seoul is not None
    assert seoul["name"] == "서울"

    # 서울 25개 구 검증
    assert "children" in seoul
    assert len(seoul["children"]) == 25

    # 구 데이터 필드 검증
    for district in seoul["children"]:
        assert "regionCode" in district
        assert "name" in district
        assert "fullName" in district
```

**검증 항목**:
- API 응답 성공 여부
- 응답 구조 (data.regionList)
- 서울 25개 구 존재 여부
- 필수 필드 (regionCode, name, fullName)

---

### 1.2. `/api/v2/pois-bounding` API 테스트 (작은 bbox)

**목적**: 작은 bbox로 POI 조회 (600개 제한 안 걸림)

```python
def test_pois_bounding_small_bbox():
    """작은 bbox로 POI 조회 (600개 제한 안 걸림)"""
    params = {
        "level": 16,
        "startX": 127.00,
        "endX": 127.01,
        "startY": 37.50,
        "endY": 37.51,
        "types": "1"  # 아파트만
    }

    response = requests.get(
        "https://hogangnono.com/api/v2/pois-bounding",
        params=params
    )

    assert response.status_code == 200
    data = response.json()

    assert "data" in data
    assert isinstance(data["data"], list)
    assert len(data["data"]) < 600  # 600개 제한 안 걸림

    # POI 필드 검증
    if len(data["data"]) > 0:
        poi = data["data"][0]
        assert "id" in poi
        assert "name" in poi
        assert "lat" in poi
        assert "lng" in poi
        assert "category" in poi
        assert poi["category"] == 1  # 아파트
```

**검증 항목**:
- API 응답 성공 여부
- POI 데이터 구조
- 필수 필드 (id, name, lat, lng, category)
- category=1 (아파트) 필터링

---

### 1.3. 600개 제한 감지 테스트

**목적**: 큰 bbox로 600개 제한 확인

```python
def test_pois_bounding_600_limit():
    """큰 bbox로 600개 제한 확인"""
    # 강남 전체를 커버하는 큰 bbox
    params = {
        "level": 16,
        "startX": 127.00,
        "endX": 127.10,  # 큰 범위
        "startY": 37.45,
        "endY": 37.55,
        "types": "1"
    }

    response = requests.get(
        "https://hogangnono.com/api/v2/pois-bounding",
        params=params
    )

    data = response.json()
    count = len(data["data"])

    # 600개 제한에 걸렸다면 정확히 600개
    if count == 600:
        print("⚠️ 600개 제한 감지 - bbox 분할 필요")
        assert True
    else:
        assert count < 600
```

**검증 항목**:
- 600개 제한 감지 로직
- 큰 bbox에서 제한 발생 확인
- 경고 메시지 출력

---

### 1.4. 강남구 중심 bbox 테스트

**목적**: 강남구 중심 좌표로 POI 수집

```python
def test_gangnam_district_collection():
    """강남구 중심 좌표로 POI 수집"""
    # 강남구 중심 좌표 (보고서 기준)
    gangnam_center = (37.5172, 127.0473)

    # 0.01도 간격 bbox (약 1km)
    params = {
        "level": 16,
        "startX": gangnam_center[1] - 0.01,
        "endX": gangnam_center[1] + 0.01,
        "startY": gangnam_center[0] - 0.01,
        "endY": gangnam_center[0] + 0.01,
        "types": "1"
    }

    response = requests.get(
        "https://hogangnono.com/api/v2/pois-bounding",
        params=params
    )

    data = response.json()
    apartments = data["data"]

    # 최소한 N개 이상의 아파트가 있어야 함
    assert len(apartments) > 0

    # 모든 POI가 강남구인지 확인
    for apt in apartments:
        assert "강남구" in apt["address"]
        assert apt["category"] == 1

    print(f"강남구 중심 2km x 2km: {len(apartments)}개 아파트")
```

**검증 항목**:
- 강남구 중심 좌표로 데이터 수집
- 모든 POI가 강남구인지 확인
- 아파트 개수 출력

---

### 1.5. 세션 관리 테스트

**목적**: 세션 쿠키 필요 여부 확인

```python
def test_session_cookie_requirement():
    """세션 쿠키 필요 여부 확인"""
    # 1. 쿠키 없이 호출
    response_no_cookie = requests.get(
        "https://hogangnono.com/api/v2/regions",
        headers={"X-Requested-With": "XMLHttpRequest"}
    )

    # 2. 메인 페이지 접속 후 쿠키 획득
    session = requests.Session()
    session.get("https://hogangnono.com")

    response_with_cookie = session.get(
        "https://hogangnono.com/api/v2/regions",
        headers={"X-Requested-With": "XMLHttpRequest"}
    )

    # 결과 비교
    print(f"쿠키 없음: {response_no_cookie.status_code}")
    print(f"쿠키 있음: {response_with_cookie.status_code}")

    # 세션 필요 시 테스트 실패로 알림
    assert response_with_cookie.status_code == 200
```

**검증 항목**:
- 세션 쿠키 필요 여부 확인
- 쿠키 없이 호출 시 동작 확인
- 쿠키 있을 때 정상 동작 확인

---

### 1.6. Rate Limiting 테스트

**목적**: Rate limiting 정책 확인

```python
def test_rate_limiting():
    """Rate limiting 정책 확인"""
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
    for i in range(10):
        response = session.get(
            "https://hogangnono.com/api/v2/pois-bounding",
            params=params
        )
        status_codes.append(response.status_code)
        time.sleep(0.5)  # 0.5초 간격

    # 429 (Too Many Requests) 발생 여부 확인
    has_rate_limit = 429 in status_codes

    if has_rate_limit:
        print("⚠️ Rate limiting 감지 - 간격 조정 필요")

    # 최소 일부는 성공해야 함
    assert 200 in status_codes
```

**검증 항목**:
- Rate limiting 정책 존재 여부
- 429 에러 발생 확인
- 안전한 요청 간격 파악

---

## 2. Fixture (최소화)

### 2.1. Fixture 역할

Integration 테스트 위주이므로 Fixture는 단순하게:

```
tests/fixtures/
├── hogangnono_regions_response.json  # /api/v2/regions API 응답
└── hogangnono_pois_sample.json       # /api/v2/pois-bounding 응답 샘플
```

**용도**:
- API 변경 감지
- 간단한 파싱 로직 단위 테스트

---

### 2.2. Fixture Recorder

```python
# tests/helpers/record_fixtures.py

import json
import requests
from pathlib import Path

def record_fixtures():
    """필요 최소한의 fixtures만 수집"""
    session = requests.Session()
    session.get("https://hogangnono.com")

    fixtures_dir = Path("tests/fixtures")
    fixtures_dir.mkdir(exist_ok=True)

    # 1. regions API
    resp = session.get(
        "https://hogangnono.com/api/v2/regions",
        headers={"X-Requested-With": "XMLHttpRequest"}
    )
    save_json(fixtures_dir / "hogangnono_regions_response.json", resp.json())

    # 2. pois-bounding API 샘플
    resp = session.get(
        "https://hogangnono.com/api/v2/pois-bounding",
        params={"level": 16, "startX": 127.0, "endX": 127.01,
                "startY": 37.5, "endY": 37.51, "types": "1"}
    )
    save_json(fixtures_dir / "hogangnono_pois_sample.json", resp.json())

    print("✓ Fixtures 저장 완료")

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    record_fixtures()
```

**실행 방법**:
```bash
python tests/helpers/record_fixtures.py
```

---

## 3. 테스트 실행 전략

### Integration 테스트

```bash
# API 엔드포인트별 테스트 실행
pytest tests/integration/test_hogangnono_api_endpoints.py -v

# 특정 API 테스트만
pytest tests/integration/test_hogangnono_api_endpoints.py::test_regions_api -v

# 600개 제한 테스트만
pytest tests/integration/test_hogangnono_api_endpoints.py::test_pois_bounding_600_limit -v
```

### E2E 테스트 (별도)

```bash
# 전체 크롤링 흐름 테스트
pytest tests/integration/test_e2e_crawling.py -v
```

---

## 4. 기대 효과

1. **API별 정확성 검증** - 각 엔드포인트가 제대로 동작하는지 확인
2. **600개 제한 감지** - 어느 bbox에서 제한에 걸리는지 파악
3. **세션 요구사항 확인** - 쿠키 필요 여부 명확화
4. **Rate limiting 정책 파악** - 안전한 요청 간격 설정
5. **데이터 누락 원인 파악** - 어디서 데이터를 놓치는지 명확화

---

## 5. 구현 순서

1. **API 엔드포인트별 integration 테스트 작성**
   - `/api/v2/regions` 테스트
   - `/api/v2/pois-bounding` 테스트 (작은 bbox, 큰 bbox)
   - 세션 관리 테스트
   - Rate limiting 테스트

2. **Fixture recorder 구현** (최소화)
   - regions API 응답 저장
   - pois-bounding API 샘플 저장

3. **테스트 실행 및 분석**
   - 600개 제한 발생 여부 확인
   - 세션 쿠키 필요 여부 확인
   - Rate limiting 정책 파악

4. **데이터 누락 원인 분석**
   - 600개 제한으로 인한 누락
   - bbox 분할 전략 수립
   - 크롤러 개선 방향 결정

---

## 6. 다음 단계

Integration 테스트로 문제를 파악한 후:

1. **bbox 분할 전략 설계**
   - 600개 제한 감지 시 자동으로 bbox 분할
   - 작은 bbox로 재귀적 수집

2. **크롤러 개선**
   - adaptive bbox 크기 조정
   - 600개 제한 대응 로직 추가

3. **E2E 테스트 강화**
   - 전체 서울 크롤링 완성도 검증
   - 예상 데이터 개수 vs 실제 수집 개수 비교

---

*본 설계는 `hogangnono_api_analysis_report.md` 분석 결과를 기반으로 작성되었습니다.*
