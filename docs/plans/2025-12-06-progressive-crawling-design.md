# 점진적 크롤링 설계 (Progressive Crawling Design)

**작성일**: 2025-12-06
**목적**: 통합 테스트를 통한 단계별 네이버 부동산 크롤링 개선

## 목표

구 → 동 → 단지 목록 → 단지 상세 → 개별 매물의 점진적 크롤링을 구현하고, 각 단계를 독립적인 통합 테스트로 검증합니다.

## 현재 상태

- `NaverRealEstateCrawler.crawl()`: 모든 동의 단지 목록만 크롤링
- 단지 기본 정보만 수집 (이름, 연도, 세대수, 가격 범위 등)
- 금천구 3개 동을 대상으로 통합 테스트 존재

## 설계 원칙

1. **YAGNI**: 메서드를 분리하여 호출자가 필요한 수준만 선택
2. **독립적 테스트**: 각 레벨을 별도 통합 테스트로 검증
3. **최대한의 데이터 수집**: API가 제공하는 모든 필드 수집, 나중에 선택적 사용
4. **단순한 체크포인트**: 마지막 동/단지만 추적

## 아키텍처 변경

### 크롤러 메서드 구조

**기존**:
```python
crawler.crawl() → list[dict[str, Any]]  # 모든 단지 기본 정보
```

**변경 후**:
```python
# 레벨 1: 단지 목록만 (현재와 동일)
crawler.crawl() → list[dict[str, Any]]

# 레벨 2: 단지 상세 정보
crawler.fetch_complex_detail(complex_id: str) → dict[str, Any]

# 레벨 3: 단지의 매물 목록
crawler.fetch_complex_listings(
    complex_id: str,
    trade_type: str = "A1"  # A1: 매매, B1: 전세, B2: 월세
) → list[dict[str, Any]]
```

### 데이터 구조

#### 현재 단지 기본 정보 (이미 구현됨)
- complex_id, complex_name, real_estate_type
- completion_year_month, total_dong_count, total_household_count
- min_area, max_area
- deal_count, lease_count, rent_count, total_article_count
- deal_price_min/max, lease_price_min/max

#### 추가될 단지 상세 정보 (API 탐색 후 결정)
- 주소 (도로명, 지번)
- 편의시설 정보
- 주차 대수
- 관리비
- 건설사
- 기타 API가 제공하는 모든 필드

#### 추가될 매물 정보 (API 탐색 후 결정)
- article_id, article_name
- floor, area (전용/공급 면적)
- price (매매가/전세가/월세)
- article_confirm_ymd
- direction
- 기타 API가 제공하는 모든 필드

## 통합 테스트 구조

### 테스트 파일: `tests/integration/test_naver_integration.py`

4개의 독립적인 통합 테스트:

1. **`test_crawl_complexes_basic()`**
   - 단지 목록만 크롤링 (기존 기능)
   - 금천구 1개 동 사용
   - 단지 기본 정보 검증

2. **`test_fetch_complex_detail()`**
   - 특정 단지의 상세 정보 조회
   - crawl()로 단지 1개 얻기 → fetch_complex_detail() 호출
   - 추가 필드 검증 (주소, 편의시설 등)

3. **`test_fetch_complex_listings()`**
   - 특정 단지의 매물 목록 조회
   - crawl()로 단지 1개 얻기 → fetch_complex_listings() 호출
   - 매물 데이터 검증 (호수, 면적, 가격 등)

4. **`test_crawl_full_pipeline()`**
   - 전체 파이프라인 (목록 → 상세 → 매물)
   - crawl() → 각 단지마다 detail + listings 호출
   - 최종 통합 데이터 검증
   - CSV 저장 검증

### 테스트 데이터 범위

- **금천구 1개 동만** 사용 (빠른 피드백)
- 기존 3개 동은 너무 많아서 축소
- 각 테스트는 30초 이내 완료 목표

### 테스트 실행 명령어

```bash
# 개별 테스트
pytest tests/integration/test_naver_integration.py::test_crawl_complexes_basic -v -s
pytest tests/integration/test_naver_integration.py::test_fetch_complex_detail -v -s
pytest tests/integration/test_naver_integration.py::test_fetch_complex_listings -v -s
pytest tests/integration/test_naver_integration.py::test_crawl_full_pipeline -v -s

# 전체 통합 테스트
pytest tests/integration/ -v -s
```

## 체크포인트 단순화

### 현재 구조 (과도함)
```json
{
  "last_completed": {"district": "금천구", "dong": "가산동"},
  "completed_dongs": ["1153010100"],
  "total_complexes_crawled": 150
}
```

### 단순화된 구조
```json
{
  "last_dong": "1153010100",
  "last_complex": "12345",
  "failed_dongs": []
}
```

**필드 설명**:
- `last_dong`: 마지막으로 완료한 동 코드
- `last_complex`: 해당 동에서 마지막으로 처리한 단지 ID
- `failed_dongs`: 실패한 동 목록 (재시도용)

**재개 로직**:
- 동을 순회하면서 `last_dong`보다 작거나 같으면 skip
- 같은 동 내에서는 `last_complex`보다 작거나 같은 단지 skip
- 새 동 시작하면 `last_complex` null로 초기화

## CSV 출력 전략

**옵션 A: 단지 중심 CSV** (현재 구조 유지, 일단 이것으로 시작)
- 1행 = 1단지
- 상세 정보는 추가 컬럼
- 매물 정보는 집계 (평균가, 최소가, 최대가 등)

**옵션 B: 매물 중심 CSV** (나중에 고려)
- 1행 = 1매물
- 단지 정보는 각 행에 중복
- 더 상세한 분석 가능

→ 일단 옵션 A로 구현, 나중에 Jiho가 결정

## 구현 순서

### Phase 1: API 탐색
1. Playwright MCP로 네이버 부동산 접속
2. 단지 상세 페이지로 이동
3. DevTools Network 탭에서 API 호출 캡처
4. 단지 상세 API 엔드포인트 및 응답 구조 문서화
5. 매물 목록 API 엔드포인트 및 응답 구조 문서화

### Phase 2: 단지 상세 정보 구현
1. `fetch_complex_detail()` 메서드 구현
2. 모든 응답 필드 파싱
3. `test_fetch_complex_detail()` 작성
4. 테스트 통과 확인

### Phase 3: 매물 목록 구현
1. `fetch_complex_listings()` 메서드 구현
2. 모든 매물 필드 파싱
3. `test_fetch_complex_listings()` 작성
4. 테스트 통과 확인

### Phase 4: 전체 파이프라인 통합
1. `test_crawl_full_pipeline()` 작성
2. CSV 출력 포맷 구현
3. 체크포인트 로직 단순화
4. 전체 테스트 통과 확인

## API 엔드포인트 (탐색 필요)

**추정되는 엔드포인트**:

단지 상세:
```
https://m.land.naver.com/complex/info/{complex_id}
또는
https://m.land.naver.com/complex/getComplexDetail?hscpNo={complex_id}
```

매물 목록:
```
https://m.land.naver.com/complex/article/{complex_id}?tradTpCd=A1
또는
https://m.land.naver.com/complex/getArticleList?hscpNo={complex_id}&tradTpCd=A1
```

→ **실제 탐색 후 확정**

## 고려사항

1. **Rate Limiting**: 현재 500ms 대기, 상세 조회 추가 시 조정 필요할 수 있음
2. **에러 처리**: 각 메서드에 재시도 로직 추가
3. **세션 관리**: 브라우저 컨텍스트를 공유하여 쿠키 유지
4. **성능**: 단지 수백 개 × 상세 조회 → 시간 오래 걸림, 체크포인트 중요

## 성공 기준

- [ ] 4개의 통합 테스트 모두 통과
- [ ] 단지 상세 정보의 모든 필드 수집
- [ ] 매물 정보의 모든 필드 수집
- [ ] 체크포인트 로직으로 중단 후 재개 가능
- [ ] CSV 파일에 모든 데이터 저장
- [ ] 각 통합 테스트는 30초 이내 완료

## 참고 문서

- `docs/analysis/naver-real-estate-final-approach.md`: 네이버 부동산 API 분석
- `naver-real-estate-crawling.md`: API 엔드포인트 및 DOM 구조
- `src/crawler/crawlers/naver.py`: 현재 크롤러 구현
- `tests/integration/test_naver_integration.py`: 기존 통합 테스트
