# 호갱노노 아파트 매물 수집 TDD 접근법

## 개요
Test-Driven Development(TDD) 원칙에 따라 호갱노노 아파트 매물 수집 기능을 안정적으로 구현하기 위한 접근법입니다.

## 1. Red 단계: 실패할 테스트 설계

### 1.1 단위 테스트 (API 클라이언트)

#### 1.1.1 SearchParams 클래스 테스트
```python
# tests/unit/test_search_params.py
import pytest
from crawler.api.hogangnono_client import SearchParams

def test_search_params_with_bbox():
    """bbox 파라미터로 SearchParams 생성 테스트"""
    bbox = (126.734086, 37.413294, 127.183394, 37.715133)
    params = SearchParams(bbox=bbox)

    assert params.startX == 126.734086
    assert params.startY == 37.413294
    assert params.endX == 127.183394
    assert params.endY == 37.715133

def test_search_params_invalid_level():
    """유효하지 않은 level 값에 대한 예외 처리 테스트"""
    with pytest.raises(ValueError, match="level must be between"):
        SearchParams(level=19)

def test_search_params_invalid_trade_type():
    """유효하지 않은 tradeType 값에 대한 예외 처리 테스트"""
    with pytest.raises(ValueError, match="tradeType must be one of"):
        SearchParams(tradeType=3)

def test_search_params_to_dict():
    """SearchParams를 딕셔너리로 변환하는 테스트"""
    params = SearchParams(
        startX=126.7,
        endX=127.0,
        startY=37.4,
        endY=37.5,
        tradeType=1
    )

    result = params.to_dict()

    assert result["startX"] == 126.7
    assert result["endX"] == 127.0
    assert result["startY"] == 37.4
    assert result["endY"] == 37.5
    assert result["tradeType"] == 1
    assert "level" in result
    assert "map" in result
```

#### 1.1.2 APIResponse 클래스 테스트
```python
# tests/unit/test_api_response.py
import pytest
from unittest.mock import Mock
from requests import Response
from crawler.api.hogangnono_client import APIResponse

def test_api_response_from_success_json():
    """성공 JSON 응답 파싱 테스트"""
    mock_response = Mock(spec=Response)
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"success": True, "data": {"items": []}}

    api_response = APIResponse.from_response(mock_response)

    assert api_response.success is True
    assert api_response.data == {"items": []}
    assert api_response.error is None
    assert api_response.status_code == 200

def test_api_response_from_error():
    """에러 응답 파싱 테스트"""
    mock_response = Mock(spec=Response)
    mock_response.status_code = 404
    mock_response.reason = "Not Found"
    mock_response.headers = {"content-type": "application/json"}

    api_response = APIResponse.from_response(mock_response)

    assert api_response.success is False
    assert "HTTP error: 404" in api_response.error
    assert api_response.status_code == 404

def test_api_response_from_html():
    """HTML 응답 파싱 테스트"""
    mock_response = Mock(spec=Response)
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html"}
    mock_response.text = "<html><body>Test</body></html>"

    api_response = APIResponse.from_response(mock_response)

    assert api_response.success is True
    assert api_response.data["raw_content"] == "<html><body>Test</body></html>"
```

#### 1.1.3 HogangnonoAPIClient 테스트
```python
# tests/unit/test_hogangnono_client.py
import pytest
from unittest.mock import Mock, patch
from crawler.config import CrawlerConfig
from crawler.api.hogangnono_client import HogangnonoAPIClient, SearchParams

@pytest.fixture
def config():
    return CrawlerConfig.from_env()

@pytest.fixture
def client(config):
    return HogangnonoAPIClient(config)

def test_initialize_session_success(client):
    """세션 초기화 성공 테스트"""
    with patch.object(client.session, 'get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.cookies = []
        mock_get.return_value = mock_response

        result = client._initialize_session()

        assert result is True
        assert client._session_initialized is True

def test_get_apartments_bounding(client):
    """아파트 목록 API 호출 테스트"""
    search_params = SearchParams(
        bbox=(126.7, 37.4, 127.0, 37.5),
        tradeType=0
    )

    with patch.object(client, '_make_request') as mock_request:
        mock_response = Mock()
        mock_response.success = True
        mock_response.data = {"data": []}
        mock_request.return_value = mock_response

        result = client.get_apartments_bounding(search_params)

        assert result.success is True
        mock_request.assert_called_once_with(
            method="GET",
            endpoint="/api/v2/pois-bounding",
            params=search_params.to_dict()
        )

def test_parse_complexes_from_ranks(client):
    """ranks/rolling 응답 파싱 테스트"""
    ranks_data = {
        "data": {
            "rolling": [
                {
                    "hash": "test123",
                    "name": "테스트아파트",
                    "sidoName": "서울특별시",
                    "sigunguName": "강남구",
                    "dongName": "역삼동",
                    "regionName": "서울특별시 강남구 역삼동",
                    "rank": 1,
                    "visitor": 1000
                }
            ]
        }
    }

    complexes = client.parse_complexes_from_ranks(ranks_data)

    assert len(complexes) == 1
    assert complexes[0]["id"] == "test123"
    assert complexes[0]["aptName"] == "테스트아파트"
    assert complexes[0]["region1"] == "서울특별시"
```

### 1.2 통합 테스트 (실제 API 호출)

#### 1.2.1 API 엔드포인트 테스트
```python
# tests/integration/test_hogangnono_api_endpoints.py
import pytest
from crawler.config import CrawlerConfig
from crawler.api.hogangnono_client import HogangnonoAPIClient, SearchParams

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_api_call_pois_bounding():
    """실제 POI bounding API 호출 테스트"""
    config = CrawlerConfig.from_env()
    client = HogangnonoAPIClient(config)

    # 강남구 일대 좌표
    search_params = SearchParams(
        bbox=(127.04, 37.50, 127.06, 37.52),
        tradeType=0,
        aptType=1
    )

    try:
        result = client.get_apartments_bounding(search_params)

        # API 응답 검증
        assert result.success is True
        assert result.data is not None

        # 데이터 구조 검증
        if "data" in result.data and result.data["data"]:
            first_item = result.data["data"][0]
            assert "id" in first_item or "name" in first_item

    finally:
        client.close()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_api_call_ranks_rolling():
    """실제 ranks/rolling API 호출 테스트"""
    config = CrawlerConfig.from_env()
    client = HogangnonoAPIClient(config)

    try:
        result = client.fetch_ranks_rolling()

        # API 응답 검증
        assert isinstance(result, dict)
        assert "data" in result

    finally:
        client.close()
```

### 1.3 엔드투엔드 테스트

#### 1.3.1 전체 크롤링 플로우 테스트
```python
# tests/e2e/test_hogangnono_crawling.py
import pytest
from pathlib import Path
from crawler.config import CrawlerConfig
from crawler.crawlers.hogangnono import HogangnonoCrawler

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_crawling_workflow():
    """전체 크롤링 워크플로우 테스트"""
    config = CrawlerConfig.from_env()
    output_dir = Path("test_output")

    # 테스트용 작은 영역 (강남구 일부)
    test_bounds = (37.50, 127.04, 37.52, 127.06)

    crawler = HogangnonoCrawler(
        config=config,
        output_dir=output_dir,
        region_bounds=test_bounds
    )

    try:
        # 크롤링 실행
        complexes, transactions = crawler.crawl_region(
            region_bounds=test_bounds,
            apt_type="apart",
            trade_type="sale",
            max_pages=2
        )

        # 결과 검증
        assert isinstance(complexes, list)
        assert isinstance(transactions, list)

        if complexes:
            assert "complex_id" in complexes[0]
            assert "complex_name" in complexes[0]

        # CSV 저장 테스트
        crawler.save_to_csv(complexes, transactions)

        # 파일 생성 확인
        assert (output_dir / "hogangnono_complexes.csv").exists()
        assert (output_dir / "hogangnono_transactions.csv").exists()

    finally:
        # 테스트 파일 정리
        import shutil
        if output_dir.exists():
            shutil.rmtree(output_dir)
```

## 2. Test Doubles 준비

### 2.1 Mock 응답 데이터
```python
# tests/fixtures/hogangnono_responses.py

MOCK_POIS_BOUNDING_RESPONSE = {
    "success": True,
    "data": [
        {
            "id": "complex_123",
            "name": "테스트아파트",
            "lat": 37.5172,
            "lng": 127.0473,
            "type": "아파트",
            "region1": "서울특별시",
            "region2": "강남구",
            "region3": "역삼동",
            "address": "서울특별시 강남구 역삼동 123-45",
            "buildDate": "2005",
            "households": 300,
            "floors": 15,
            "trade": {
                "type": "sale",
                "area": "84.95",
                "price": "12억5,000",
                "floor": "5층",
                "date": "2024.11.01"
            }
        }
    ]
}

MOCK_RANKS_ROLLING_RESPONSE = {
    "success": True,
    "data": {
        "rolling": [
            {
                "hash": "rank_123",
                "name": "인기아파트",
                "sidoName": "서울특별시",
                "sigunguName": "강남구",
                "dongName": "대치동",
                "regionName": "서울특별시 강남구 대치동",
                "rank": 1,
                "prevRank": 2,
                "visitor": 5000,
                "rankType": "weekly",
                "statusTag": "hot"
            }
        ]
    }
}
```

### 2.2 Fake API 서버 (pytest-httpx 사용)
```python
# tests/conftest.py
import pytest
from unittest.mock import Mock
import json

@pytest.fixture
def mock_hogangnono_api(httpx_mock):
    """호갱노노 API Mock 서버"""

    # POI bounding 엔드포인트 Mock
    httpx_mock.add_response(
        url="https://hogangnono.com/api/v2/pois-bounding",
        json=MOOCK_POIS_BOUNDING_RESPONSE,
        status_code=200
    )

    # Ranks rolling 엔드포인트 Mock
    httpx_mock.add_response(
        url="https://hogangnono.com/api/v2/ranks/rolling",
        json=MOCK_RANKS_ROLLING_RESPONSE,
        status_code=200
    )

    # 메인 페이지 Mock (세션 초기화용)
    httpx_mock.add_response(
        url="https://hogangnono.com",
        text="<html><body>Home</body></html>",
        status_code=200
    )

    yield httpx_mock
```

## 3. Green 단계 계획

### 3.1 최소한의 구현 순서

1. **SearchParams 클래스 구현**
   - `__init__`: 파라미터 유효성 검사
   - `to_dict`: API 요청 파라미터 변환

2. **APIResponse 클래스 구현**
   - `from_response`: HTTP 응답 파싱

3. **HogangnonoAPIClient 핵심 기능**
   - `_initialize_session`: 세션 및 쿠키 초기화
   - `get_apartments_bounding`: 아파트 목록 조회
   - `parse_pois_from_bounding`: 응답 데이터 파싱

4. **HogangnonoCrawler 기본 기능**
   - `get_endpoint`: API 엔드포인트 반환
   - `get_params`: 요청 파라미터 생성
   - `parse_response`: 응답 데이터 파싱

### 3.2 점진적 구현 전략

```python
# 첫 번째: 가장 간단한 테스트부터 통과
def test_search_params_basic():
    params = SearchParams()
    assert params.level == 17
    assert params.tradeType == 0

# 두 번째: 유효성 검사 추가
def test_search_params_validation():
    with pytest.raises(ValueError):
        SearchParams(level=20)

# 세 번째: 복잡한 파라미터 조합
def test_search_params_complex():
    params = SearchParams(
        bbox=(126.7, 37.4, 127.0, 37.5),
        tradeType=1,
        aptType=0
    )
    dict_params = params.to_dict()
    assert "startX" in dict_params
    assert "tradeType" in dict_params
```

## 4. Refactor 단계 계획

### 4.1 코드 중복 제거
- 공통 헤더 설정 함수 추출
- 파라미터 검증 로직 통합
- 에러 처리 패턴 표준화

### 4.2 성능 최적화
- 캐싱 메커니즘 도입 (단지 정보 등)
- 동시 처리 고려 (Async API 호출)
- 메모리 사용량 최적화

### 4.3 가독성 개선
- 명확한 변수명 사용
- 적절한 주석 추가
- 복잡한 로직 분리

### 4.4 리팩토링 예시
```python
# Before: 반복적인 에러 처리
def get_complex_list(self, cortar_no):
    try:
        response = self._make_request(...)
        if not response.success:
            self.logger.error(f"Failed: {response.error}")
            return None
        return response.data
    except Exception as e:
        self.logger.error(f"Error: {e}")
        return None

# After: 공통 에러 핸들러 사용
def get_complex_list(self, cortar_no):
    return self._handle_api_response(
        lambda: self._make_request(...),
        "get_complex_list"
    )

def _handle_api_response(self, api_call, operation_name):
    """공통 API 응답 처리 핸들러"""
    try:
        response = api_call()
        if response.success:
            return response.data
        self.logger.error(f"{operation_name} failed: {response.error}")
        return None
    except Exception as e:
        self.logger.error(f"{operation_name} error: {e}")
        return None
```

## 5. 실행 계획

### 5.1 Phase 1: 기반 구조 (1-2일)
1. 테스트 환경 설정
2. SearchParams 클래스 TDD
3. APIResponse 클래스 TDD

### 5.2 Phase 2: API 클라이언트 (2-3일)
1. HogangnonoAPIClient 기본 기능 TDD
2. 세션 관리 및 인증
3. Mock 데이터 준비

### 5.3 Phase 3: 크롤러 구현 (2-3일)
1. HogangnonoCrawler 기본 기능 TDD
2. 데이터 파싱 및 변환
3. CSV 저장 기능

### 5.4 Phase 4: 통합 및 최적화 (1-2일)
1. 통합 테스트
2. 성능 최적화
3. 리팩토링

## 6. 성공 기준

- 모든 단위 테스트 통과 (90% 이상 커버리지)
- 통합 테스트로 실제 API 연동 확인
- 엔드투엔드 테스트로 전체 플로우 검증
- 코드 리뷰 통과
- 성능 벤치마크达标

## 7. 리스크 관리

- API 변경에 대한 유연한 대응 (Mock으로 격리)
- Rate limiting으로 IP 차단 방지
- 에러 핸들링으로 안정성 확보
- 체크포인트로 중단 지점부터 재개 가능