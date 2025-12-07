# 네이버 부동산 API 문제 해결 계획 (TDD 접근)

## 문제 개요

- **현상**: 네이버 부동산 API(`m.land.naver.com/cluster/ajax/complexList`) 응답이 빈 결과(`result: []`)로 반환
- **상태**: 크롤러 코드는 정상 동작 (Rate limiting, URL 생성, 파라미터 처리 모두 정상)
- **원인 추정**: API 엔드포인트 변경 또는 인증 요구사항 추가

## TDD 해결 전략

### Red 단계: 실패하는 테스트 작성

1. **API 엔드포인트 테스트**
   ```python
   # tests/integration/test_naver_api_endpoints.py
   def test_direct_complex_list_api(self):
       """직접 API 호출 테스트 - 현재는 실패할 것"""
       # 실제 API 호출하여 빈 응답 확인
       # 이 테스트는 현재 실패해야 함
   ```

2. **세션 유효성 테스트**
   ```python
   def test_session_validation(self):
       """세션 확보 후 API 호출 테스트"""
       # 모바일 페이지 접속 → 세션 확보 → API 호출
       # 실패할 것으로 예상
   ```

3. **헤더 및 User-Agent 테스트**
   ```python
   def test_headers_impact(self):
       """다양한 헤더 조합으로 API 호출 테스트"""
       # User-Agent, Referer 등 헤더 변경 테스트
   ```

### Green 단계: 최소한의 수정으로 통과

1. **API 엔드포인트 분석**
   - 현재 엔드포인트: `/cluster/ajax/complexList`
   - 대체 후보:
     - `/complex/complexList` (PC 버전)
     - `/hspinfo/getComplexList` (최신 버전)
     - GraphQL 엔드포인트 확인

2. **세션 확보 개선**
   ```python
   # 현재: page.goto("https://m.land.naver.com/complexes")
   # 개선: 더 긴 대기 시간 및 특정 쿠키 확보
   page.goto("https://m.land.naver.com/complexes")
   page.wait_for_load_state("networkidle")
   time.sleep(5)  # 증가
   # 추가: 쿠키 및 localStorage 확인
   ```

3. **인증 파라미터 추가**
   ```python
   # 필요 시 CSRF 토큰 등 인증 파라미터 추가
   params = {
       "cortarNo": cortar_no,
       "rletTpCd": "A1",  # 필수 파라미터 확인
       "z": 15,  # 줌 레벨
       "_": int(time.time() * 1000),  # 타임스탬프
   }
   ```

### Refactor 단계: 코드 개선

1. **API 호출 모듈 분리**
   - `NaverApiClient` 클래스 생성
   - 세션 관리, 헤더 설정, 재시도 로직 캡슐화

2. **응답 검증 강화**
   - 빈 응답 외에 에러 메시지 검증
   - 응답 구조 변경 감지 로직

3. **다양한 엔드포인트 지원**
   - fallback 메커니즘 구현
   - 여러 API 버전 동시 지원

## 구현 단계 상세

### 1단계: 문제 분석 및 테스트 작성

**작업 내용:**
1. API 엔드포인트 직접 테스트
2. 네트워크 요청/응답 분석
3. 기존 테스트 실패 확인

**파일:**
- `tests/integration/test_naver_api_diagnosis.py` (신규)
- `tests/unit/test_naver_api_client.py` (신규)

### 2단계: 세션 관리 개선

**작업 내용:**
1. 모바일 페이지 접속 로직 수정
2. 쿠키 및 세션 토큰 확보
3. 헤더 정보 최적화

**파일:**
- `src/crawler/utils/naver_session.py` (신규)
- `src/crawler/crawlers/naver.py` (수정)

### 3단계: API 클라이언트 리팩토링

**작업 내용:**
1. 별도 API 클라이언트 클래스 생성
2. 인증 및 헤더 관리 분리
3. 재시도 및 fallback 로직 구현

**파일:**
- `src/crawler/api/naver_client.py` (신규)
- `src/crawler/crawlers/naver.py` (리팩토링)

### 4단계: 통합 테스트 및 검증

**작업 내용:**
1. 전체 크롤링 프로세스 테스트
2. 데이터 품질 검증
3. 성능 테스트

**파일:**
- `tests/integration/test_full_crawling_flow.py` (수정)

## 실행 계획

### 준비 작업
```bash
# 1. 실패하는 테스트 작성
touch tests/integration/test_naver_api_diagnosis.py

# 2. 네트워크 분석 도구 준비
# 필요 시 Wireshark 또는 Chrome DevTools 사용
```

### 일정
- **1일차**: 문제 분석 및 실패 테스트 작성
- **2일차**: 최소 수정으로 통과 (Green)
- **3일차**: 코드 개선 및 리팩토링
- **4일차**: 통합 테스트 및 검증

## 성공 기준

1. **API 응답 복구**
   - 빈 결과가 아닌 실제 단지 데이터 반환
   - 응답 시간 5초 이내

2. **안정성**
   - 연속 100회 요청 성공률 95% 이상
   - rate limiting 효과적 동작

3. **데이터 품질**
   - 기존 데이터 형식과 호환
   - 필수 필드 모두 포함

## 리스크 관리

### 높은 리스크
- API 완전 차단 또는 유료 전환
  - 대안: 공공 API 활용 또는 다른 포털 크롤링

### 중간 리스크
- 지속적인 인증 요구
  - 대안: 인증 자동화 또는 인증 정보 관리

### 낮은 리스크
- 응답 형식 변경
  - 대안: 유연한 파서 구현

## 부록: 문제 해결을 위한 체크리스트

- [ ] 현재 API 엔드포인트 테스트
- [ ] 모바일 웹에서 실제 동작 확인
- [ ] 네트워크 요청 헤더 분석
- [ ] 쿠키 및 세션 정보 확인
- [ ] 대체 API 엔드포인트 탐색
- [ ] 인증 방식 확인 (쿠키, 토큰, IP 등)
- [ ] rate limiting 정책 확인
- [ ] 데이터 형식 변경 가능성 확인