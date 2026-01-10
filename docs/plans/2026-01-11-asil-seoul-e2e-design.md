# ASIL 서울 아파트 E2E 테스트 설계

**Goal**: e2e 테스트로 서울 내 아파트 정보를 수집하고 CSV로 내보내기

**Constraints**:
- 샘플링: 최대 50개 아파트로 제한
- 동 코드: 하드코딩된 3~5개 샘플 사용
- 필드: ASIL API 반환 필드 그대로 사용

---

## 아키텍처

### 테스트 파일
`tests/e2e/test_asil_seoul_e2e.py`

### 구조
1. `SEOUL_DONG_CODES`: 서울 샘플 동 코드 하드코딩 상수 (3~5개)
2. `export_to_csv()`: CSV 내보내기 헬퍼 함수
3. `test_crawl_seoul_apartments()`: 메인 e2e 테스트 함수

### 실행 흐름
```
각 dong_code 반복:
  → AsilAptListCrawler로 아파트 목록 가져오기
  → 결과 누적
  → 최대 50개 도달 시 중단
  → CSV로 저장 (output/asil_seoul_apt_{timestamp}.csv)
```

---

## 데이터 구조

### 하드코딩 동 코드
```python
SEOUL_DONG_CODES = {
    "1168010100": "역삼동",
    "1168010200": "청담동",
    "1168010300": "삼성동",
    "1150010700": "사직동",
    "1156010500": "행당동",
}
```

### CSV 헬퍼 함수
```python
def export_to_csv(data: list[dict], filepath: str) -> None:
    """딕셔너리 리스트를 CSV로 내보내기

    - 첫 번째 아이템의 키들을 헤더로 사용
    - output 디렉토리가 없으면 생성
    - UTF-8 인코딩
    """
```

### 파일명
`output/asil_seoul_apt_{timestamp}.csv`

---

## 메인 테스트 및 샘플링

### 메인 e2e 테스트
```python
@pytest.mark.e2e
def test_crawl_seoul_apartments(tmp_path, monkeypatch):
    """e2e: 서울 아파트 목록 크롤링 후 CSV 내보내기

    검증:
    1. ASIL API에서 성공적으로 데이터 가져옴
    2. 최대 50개 아파트로 제한됨
    3. CSV 파일이 생성됨
    4. CSV 내용이 파싱 가능함
    """
```

### 샘플링 로직
```python
MAX_APARTMENTS = 50
all_apartments = []

for dong_code, dong_name in SEOUL_DONG_CODES.items():
    if len(all_apartments) >= MAX_APARTMENTS:
        break

    crawler = AsilAptListCrawler(dong_code=dong_code)
    results = crawler.crawl()

    # 남은 용량만큼만 추가
    remaining = MAX_APARTMENTS - len(all_apartments)
    all_apartments.extend(results[:remaining])
```

### 테스트 검증 항목
1. `len(all_apartments) <= 50`
2. CSV 파일 존재 확인
3. CSV 로드하여 레코드 수 검증

---

## 구현 Task 목록

1. `tests/e2e/test_asil_seoul_e2e.py` 생성
2. `SEOUL_DONG_CODES` 상수 정의
3. `export_to_csv()` 헬퍼 함수 구현
4. `test_crawl_seoul_apartments()` 테스트 구현
5. `pytest -v -m e2e`로 실행 검증
