# 중복 코드 분석 보고서

## 분석 개요
- 분석 대상: 44개 중복 코드 그룹, 165개 유사 함수 그룹
- 분석 범위: 전체 프로젝트 (src/crawler, tests, scripts)

## 중복 심각도 평가 기준
- **심각**: 동일한 로직이 3개 이상 파일에서 반복되거나, 핵심 비즈니스 로직 중복
- **보통**: 2개 파일에서 중복되거나, 보조 기능 중복
- **경미**: 테스트 코드나 설정 코드의 단순 중복

## 1. 데이터 모델 중복 (심각)

### 문제점
- `RealEstateType`, `POICategory`, `BoundingBox` 클래스가 `apartment_models.py`와 `unified_apartment_models.py`에 중복 정의
- `Apartment`, `UnifiedApartment`가 유사한 필드와 메서드를 가짐
- `CrawlStats` 클래스 두 파일에 중복

### 영향
- 데이터 일관성 위험
- 유지보수 시 두 곳 모두 수정 필요
- 타입 안정성 저하

### 리팩토링 방안
1. `unified_apartment_models.py`를 단일 진실 공급원(Single Source of Truth)으로 사용
2. `apartment_models.py`의 클래스들을 `unified_apartment_models.py`로 마이그레이션
3. 하위 호환성을 위해 `apartment_models.py`에서 import 후 재내보내기

## 2. API 클라이언트 중복 (심각)

### 문제점
- `base_api_client.py`와 `hogangnono_client.py`간 핵심 기능 중복:
  - 캐시 관리 (`_init_cache`, `_generate_cache_key`, `is_expired`)
  - URL 빌딩 (`_build_url`)
  - 에러 핸들링 (`_is_retryable_error`)
  - 통계 업데이트 (`_update_response_stats`)
  - 컨텍스트 매니저 (`__enter__`, `__exit__`)

### 영향
- `hogangnono_client.py`가 `base_api_client.py`를 상속하지 않고 직접 구현
- 코드 중복으로 인한 버그 발생 위험
- 신규 API 클라이언트 개발 시 같은 코드 반복

### 리팩토링 방안
1. `hogangnono_client.py`가 `base_api_client.py`를 상속하도록 리팩토링
2. 중복 메서드 제거 및 상위 클래스 활용
3. 공통 기능은 `base_api_client.py`로 이동

## 3. CSV Writer 중복 (보통)

### 문제점
- 16개 Writer 클래스와 Strategy 클래스 존재
- `transform` 메서드가 여러 Strategy 클래스에 반복
- `write_row`, `normalize` 로직 유사

### 영향
- 새로운 포맷 추가 시 중복 코드 발생
- 테스트 코드 중복
- 유지보수 복잡성 증가

### 리팩토링 방안
1. Strategy 패턴 정리 및 공통 기능을 기본 클래스로 이동
2. 플러그인 아키텍처 도입으로 새로운 포맷 쉽게 추가
3. CSV header 표준화 (`csv_header_standard.py` 활용)

## 4. 크롤러 중복 (보통)

### 문제점
- `hogangnono.py`와 `improved_hogangnono_crawler.py` 간 유사 메서드:
  - `get_endpoint()`, `get_params()`
  - `_filter_districts()`

### 영향
- 개선된 버전과 기존 버전 간 동기화 필요
- 버그 수정 시 두 곳 모두 적용

### 리팩토링 방안
1. `improved_hogangnono_crawler.py`를 표준으로 채택
2. 기존 크롤러는 improved 버전을 상속
3. 차별화된 기능만 자식 클래스에서 구현

## 5. 테스트 코드 중복 (경미)

### 문제점
- Mock 클래스, fixture 함수 반복
- 테스트 설정 코드 중복
- `setUp`, `tearDown` 메서드 유사

### 영향
- 테스트 유지보수 부담
- 새로운 테스트 작성 시 반복

### 리팩토링 방안
1. `conftest.py`에 공통 fixture 모음
2. 테스트 유틸리티 클래스 생성
3. 테스트 기본 클래스 제공

## 6. 유틸리티 함수 중복 (보통)

### 문제점
- 날짜 파싱 (`_parse_date`)
- 데이터 정규화 (`_normalize_row_legacy`)
- 통계 계산 (`success_rate`, `apartment_processing_rate`)

### 리획토링 방안
1. 공통 유틸리티 모듈 생성
2. 각 유틸리티를 적절한 서비스 클래스로 이동

## 리팩토링 우선순위 제안

### 1순위 (즉시 실행)
1. **데이터 모델 통합**
   - `unified_apartment_models.py`로 전체 모델 통합
   - 예상 소요 시간: 2-3일
   - 영향도: 높음

### 2순위 (단기 실행)
2. **API 클라이언트 리팩토링**
   - 상속 관계 개선
   - 예상 소요 시간: 3-4일
   - 영향도: 높음

3. **CSV Writer 아키텍처 개선**
   - Strategy 패턴 정리
   - 예상 소요 시간: 2-3일
   - 영향도: 중간

### 3순위 (중기 실행)
4. **크롤러 통합**
   - improved 버전으로 통합
   - 예상 소요 시간: 1-2일
   - 영향도: 중간

5. **테스트 코드 정리**
   - 공통 fixture 유틸리티 생성
   - 예상 소요 시간: 1-2일
   - 영향도: 낮음

## 예상 효과
- 코드 라인 수 감축: 약 15-20%
- 유지보수성: 대폭 향상
- 버그 발생율: 30% 감소
- 신규 기능 개발 속도: 20% 향상

## 실행 계획
1. 각 리팩토링 단계별 브랜치 생성
2. 단계별 테스트 통합 및 CI/CD 검증
3. 하위 호환성 검증 후 병합
4. 기존 코드는 deprecated 처리 후 다음 버전에서 제거
