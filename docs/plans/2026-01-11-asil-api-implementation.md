# ASIL.kr API 전체 구현 계획

작성일: 2026-01-11
상태: 설계 계획 (READ-ONLY 모드)

## 1. 개요

본 계획은 asil.kr 웹사이트의 리버스 엔지니어링 결과를 바탕으로, 전체 API 클라이언트를 구현하는 상세 설계를 제공합니다. 현재 `AsilAptListCrawler`와 `AsilTradePriceCrawler`가 구현되어 있으며, 추가로 6개의 API 크롤러를 구현해야 합니다.

### 1.1 현재 상황

**이미 구현된 것:**
- `AsilAptListCrawler`: 아파트 목록 조회 (data_apt_list.jsp)
- `AsilTradePriceCrawler`: 실거래가 조회 (apt_price_m2_mjw_newver_6.jsp)

**테스트 상태:**
- 단위 테스트: 9개 통과
- 통합 테스트: 7개 통과

**발견된 문제:**
- 동적 면적 매칭 문제 (실제 테스트에서는 발견되지 않음, 이전에 기록된 문제)

### 1.2 새로 구현할 API

| API 엔드포인트 | 기능 | 우선순위 | 난이도 |
|---------------|------|---------|--------|
| data_apt_dong.jsp | 동/호 정보 조회 | 높음 | 낮음 |
| data_school_list_2024.jsp | 학군 정보 조회 | 중간 | 중간 |
| aptcount_ver_5_9.jsp | 지도 기반 아파트 카운트/검색 | 높음 | 중간 |
| data_traffic_naver.jsp | 교통정보 | 낮음 | 중간 |
| data_redevelop.jsp | 재개발 정보 | 낮음 | 높음 |
| data_education.jsp | 학군 정보 (지도용) | 낮음 | 중간 |

---

## 2. 각 API 크롤러별 상세 설계

### 2.1 AsilDongInfoCrawler (data_apt_dong.jsp)

**기능:** 특정 아파트의 동(Dong) 정보 조회

**상태:** ✅ 구현 완료

**파라미터:**
```python
def __init__(
    self,
    apt_code: str,  # 필수: 아파트 고유 코드
):
```

**실제 응답 데이터 구조:**
```json
{
  "data": [
    {"dong": "101"},
    {"dong": "102"},
    {"dong": "103"}
  ],
  "v": "1"
}
```

**구현 완료 사항:**
- ✅ BaseCrawler 상속
- ✅ get_url() 메서드 구현
- ✅ fetch() 메서드 구현 (UTF-8 인코딩)
- ✅ parse() 메서드 구현 (앞 \r\n 처리, 빈 응답 처리)
- ✅ 단위 테스트 작성 완료

**특이사항:**
- 응답 앞에 `\r\n` 8개가 선행하여 `strip()` 처리 필요
- 동(dong) 정보만 제공하며 호/층/면적 필드는 없음
- 빈 응답이 유효한 응답일 수 있음 (유효하지 않은 아파트 코드)

---

### 2.2 AsilSchoolInfoCrawler (data_school_list_2024.jsp)

**기능:** 특정 지역의 학군 정보 조회

**파라미터:**
```python
def __init__(
    self,
    dong_code: str,  # 필수: 법정동 코드
    school_type: str = "",  # 선택: 학교 유형 (초/중/고)
    lat: float | None = None,  # 선택: 위도
    lon: float | None = None,  # 선택: 경도
):
```

**예상 응답 데이터 구조:**
```json
[
  {
    "name": "역삼초등학교",
    "type": "초등학교",
    "distance": "0.5km",
    "lat": "37.5001",
    "lon": "127.0501"
  }
]
```

**구현 순서:**
1. 단위 테스트 작성
2. get_url() 메서드 구현 (좌표 기반 검색 지원)
3. fetch() 메서드 구현
4. parse() 메서드 구현 (거리 계산 로직 포함)
5. 통합 테스트 작성

**테스트 항목:**
- dong_code 기반 검색
- 좌표 기반 검색
- 학교 유형 필터링
- 거리 정렬 기능
- 복합 필터링

**기술적 난이도:** 중간
- 좌표 기반 검색 로직 필요
- 거리 계산 (Haversine formula)
- 다양한 필터 조합 지원

---

### 2.3 AsilMapSearchCrawler (aptcount_ver_5_9.jsp)

**기능:** 지도 범위 내 아파트 수 및 목록 조회

**파라미터:**
```python
def __init__(
    self,
    lat: float,  # 필수: 중심 위도
    lon: float,  # 필수: 중심 경도
    zoom: int,  # 필수: 줌 레벨
    map_bounds: dict | None = None,  # 선택: 지도 경계 (lat_min, lat_max, lon_min, lon_max)
    building_type: str = "",  # 선택: 건물 유형
    min_household: int = 0,  # 선택: 최소 세대수
):
```

**예상 응답 데이터 구조:**
```json
{
  "count": 45,
  "apartments": [
    {
      "seq": "20340925",
      "name": "역삼자이",
      "lat": "37.5001",
      "lon": "127.0501",
      "household": "408"
    }
  ]
}
```

**구현 순서:**
1. 단위 테스트 작성
2. get_url() 메서드 구현 (지도 좌표 변환)
3. fetch() 메서드 구현
4. parse() 메서드 구현 (중첩된 JSON 구조)
5. utils/geo.py의 Mercator projection 활용
6. 통합 테스트 작성

**테스트 항목:**
- 필수 좌표 파라미터 검증
- 지도 경계 계산
- 줌 레벨별 결과 차이
- 건물 유형 필터링
- 빈 결과 처리

**기술적 난이도:** 중간
- 지도 좌표 시스템 이해 필요
- utils/geo.py와의 연동
- 지도 경계 계산 로직

---

### 2.4 AsilTrafficCrawler (data_traffic_naver.jsp)

**기능:** 네이버 지도 기반 교통정보 조회

**파라미터:**
```python
def __init__(
    self,
    apt_code: str,  # 필수: 아파트 고유 코드
    dest_lat: float,  # 필수: 목적지 위도
    dest_lon: float,  # 필수: 목적지 경도
    transport_type: str = "subway",  # 선택: 교통수단 (subway/bus/walk)
):
```

**예상 응답 데이터 구조:**
```json
{
  "routes": [
    {
      "type": "지하철",
      "time": "35분",
      "transfers": 1,
      "stations": ["역삼역", "선릉역", "..."]
    }
  ]
}
```

**구현 순서:**
1. 단위 테스트 작성
2. get_url() 메서드 구현
3. fetch() 메서드 구현 (타사 API 연동 가능성)
4. parse() 메서드 구현 (복잡한 경로 데이터)
5. 통합 테스트 작성

**테스트 항목:**
- 경로 조회 기능
- 소요 시간 파싱
- 환승 정보 파싱
- 교통수단별 필터링
- 오류 처리 (경로 없음)

**기술적 난이도:** 중간
- 네이버 API 연동 가능성
- 복잡한 경로 데이터 파싱
- 여러 교통수단 지원

---

### 2.5 AsilRedevelopCrawler (data_redevelop.jsp)

**기능:** 재개발/재건축 구역 정보 조회

**파라미터:**
```python
def __init__(
    self,
    dong_code: str,  # 필수: 법정동 코드
    status: str = "",  # 선택: 진행상태 (예정/진행/완료)
):
```

**예상 응답 데이터 구조:**
```json
[
  {
    "name": "역삼동 재개발 구역",
    "status": "진행 중",
    "area": "25,000㎡",
    "households": "300세대",
    "expected_completion": "2027년"
  }
]
```

**구현 순서:**
1. 단위 테스트 작성
2. get_url() 메서드 구현
3. fetch() 메서드 구현
4. parse() 메서드 구현
5. 통합 테스트 작성

**테스트 항목:**
- 지역별 재개발 구역 조회
- 진행상태 필터링
- 면적 파싱 (콤마 제거)
- 세대수 파싱
- 완료 예정일 파싱

**기술적 난이도:** 높음
- 데이터 구조 불확실
- 상태 코드 매핑 복잡
- 날짜 파싱 (다양한 형식)

---

### 2.6 AsilEducationMapCrawler (data_education.jsp)

**기능:** 지도용 학군 정보 (좌표 기반)

**파라미터:**
```python
def __init__(
    self,
    lat: float,  # 필수: 중심 위도
    lon: float,  # 필수: 중심 경도
    radius: int = 1000,  # 선택: 검색 반경 (m)
    school_level: str = "",  # 선택: 학교 급 (초/중/고)
):
```

**예상 응답 데이터 구조:**
```json
[
  {
    "name": "역삼초등학교",
    "level": "초등학교",
    "lat": "37.5001",
    "lon": "127.0501",
    "students": 450,
    "rating": "4.5"
  }
]
```

**구현 순서:**
1. 단위 테스트 작성
2. get_url() 메서드 구현
3. fetch() 메서드 구현
4. parse() 메서드 구현
5. 통합 테스트 작성

**테스트 항목:**
- 반경 내 학교 검색
- 학교 급별 필터링
- 평점 데이터 파싱
- 중심점 기반 거리 계산

**기술적 난이도:** 중간
- data_school_list_2024.jsp와 중복 가능
- 반경 검색 로직
- 좌표 기반 필터링

---

## 3. 전체 구현 순서

### Phase 1: 기반 보강 (우선순위: 최상)

1. **동적 면적 매칭 문제 수정**
   - AsilTradePriceCrawler의 면적 매칭 로직 개선
   - 실제 API 응답에서 가능한 면적 목록 추출 기능 추가

### Phase 2: 핵심 API 구현 (우선순위: 높음)

2. **AsilDongInfoCrawler** (data_apt_dong.jsp)
   - 단위 테스트 → 구현 → 통합 테스트
   - 예상 시간: 1시간

3. **AsilMapSearchCrawler** (aptcount_ver_5_9.jsp)
   - utils/geo.py 연동
   - 지도 좌표 변환 로직
   - 예상 시간: 2시간

### Phase 3: 추가 정보 API (우선순위: 중간)

4. **AsilSchoolInfoCrawler** (data_school_list_2024.jsp)
   - 거리 계산 로직
   - 예상 시간: 1.5시간

5. **AsilTrafficCrawler** (data_traffic_naver.jsp)
   - 네이버 API 연동 확인
   - 예상 시간: 1.5시간

### Phase 4: 부가 정보 API (우선순위: 낮음)

6. **AsilRedevelopCrawler** (data_redevelop.jsp)
   - 복잡한 상태 코드 처리
   - 예상 시간: 2시간

7. **AsilEducationMapCrawler** (data_education.jsp)
   - AsilSchoolInfoCrawler와 중복 검토
   - 예상 시간: 1시간

---

## 4. 공통 구현 패턴

모든 크롤러는 다음 패턴을 따릅니다:

```python
class Asil[Name]Crawler(BaseCrawler):
    """asil.kr [기능] 크롤러"""

    BASE_URL = "https://asil.kr/app/data/[endpoint].jsp"
    ENCODING = "utf-8"  # 또는 "euc_kr"

    def __init__(self, [required_params], [optional_params]):
        """파라미터 설명"""
        self.[param] = [param]
        ...

    def get_url(self) -> str:
        """API 요청 URL 생성"""
        params = {...}
        return f"{self.BASE_URL}?{urlencode(params)}"

    def fetch(self, url: str) -> str:
        """URL에서 데이터 가져오기"""
        request = Request(url, headers={...})
        with urlopen(request, timeout=10) as response:
            return response.read().decode(self.ENCODING)

    def parse(self, content: str) -> list[dict]:
        """응답 파싱"""
        data = json.loads(content)
        return [파싱 로직]
```

---

## 5. 테스트 전략

### 5.1 단위 테스트 패턴

```python
class TestAsil[Name]Crawler:
    def test_inherits_from_base_crawler(self):
        """BaseCrawler 상속 여부"""

    def test_requires_[param]_parameter(self):
        """필수 파라미터 검증"""

    def test_get_url_returns_correct_endpoint(self):
        """URL 생성 검증"""

    def test_parse_returns_list_of_dicts(self):
        """파싱 결과 구조 검증"""
```

### 5.2 통합 테스트 패턴

```python
@pytest.mark.integration
class TestAsil[Name]CrawlerIntegration:
    def test_fetch_real_[data](self):
        """실제 데이터 조회"""

    def test_crawl_template_method_works(self):
        """템플릿 메서드 동작 확인"""
```

---

## 6. 예상되는 기술적 리스크 및 대응

| 리스크 | 확률 | 영향 | 대응 방안 |
|--------|------|------|----------|
| API 파라미터 변경 | 중간 | 높음 | 실제 트래픽 캡처로 파라미터 검증 |
| 인증 도입 | 낮음 | 높음 | User-Agent/Referer 헤더 최신화 |
| 인코딩 불일치 | 중간 | 중간 | EUC-KR/UTF-8 자동 감지 |
| Rate Limiting | 낮음 | 중간 | 요청 간 지연 추가 |
| 응답 구조 변경 | 낮음 | 중간 | 유연한 파싱 로직 |

---

## 7. 코드 스타일 가이드

- **주석 언어:** 한국어
- **라인 길이:** 100자 (ruff 설정)
- **타입 힌트:** 필수 (Python 3.11+)
- **문서화:** Google style docstring
- **커밋 메시지:** `feat:`, `fix:`, `test:` 접두사

---

## 8. 완료 체크리스트

### 각 크롤러별

- [ ] BaseCrawler 상속
- [ ] 필수 파라미터 검증
- [ ] URL 생성 테스트 통과
- [ ] fetch 메서드 구현 (인코딩 처리)
- [ ] parse 메서드 구현 (JSON 파싱)
- [ ] 단위 테스트 100% 통과
- [ ] 통합 테스트 통과
- [ ] 코드 리뷰 통과
- [ ] ruff 포맷팅 통과

### 프로젝트 전체

- [ ] 모든 단위 테스트 통과 (`uv run pytest -v -m unit`)
- [ ] 모든 통합 테스트 통과 (`uv run pytest -v -m integration`)
- [ ] 코드 커버리지 80% 이상
- [ ] 사후 문서화 (README 업데이트)

---

## 9. 참고 자료

- 기존 구현: `src/crawler/asil.py`
- 베이스 클래스: `src/crawler/base.py`
- 지리 유틸리티: `src/crawler/utils/geo.py`
- 기존 계획서: `docs/plans/2026-01-10-anti-bot-mvp.md`

---

### Critical Files for Implementation

다음 파일들은 본 계획 실행 시 가장 중요한 참조 파일들입니다:

- `/Users/baleen/dev/homesweethome/src/crawler/asil.py` - 기존 구현 패턴을 따르기 위한 참조 (AsilAptListCrawler, AsilTradePriceCrawler)
- `/Users/baleen/dev/homesweethome/src/crawler/base.py` - Template Method 패턴 정의 (BaseCrawler 추상 클래스)
- `/Users/baleen/dev/homesweethome/tests/unit/test_asil_crawler.py` - 단위 테스트 작성 패턴 참조
- `/Users/baleen/dev/homesweethome/tests/integration/test_asil_integration.py` - 통합 테스트 작성 패턴 참조
- `/Users/baleen/dev/homesweethome/src/crawler/utils/geo.py` - AsilMapSearchCrawler 구현 시 Mercator projection 활용
