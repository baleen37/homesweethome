# Simple Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 프로젝트 단순화 - 기반 정리, 중복 코드 제거, 불필요한 복잡성 제거

**Architecture:** 기술 부채 정리 후 중복 코드를 제거하여 단순하고 유지보수하기 쉬운 구조로

**Tech Stack:** Python 3.12+, pytest, pyproject.toml

---

## Part 1: 기반 정리 (Foundation Cleanup)

### Task 1: 의존성 정리

**Files:** `pyproject.toml`

**Step 1: 미사용 의존성 제거**
```bash
# pyproject.toml에서 다음 의존성 제거
# - beautifulsoup4
# - lxml
# - nest-asyncio
# - pytest-cov
# - python-dotenv
```

**Step 2: 필요한 의존성 추가**
```bash
# pyproject.toml에 다음 의존성 추가
# - aiohttp (실제 사용 중)
# - pyyaml (실제 사용 중)
# - psutil (memory profiler용)
```

**Step 3: Commit**
```bash
git add pyproject.toml uv.lock
git commit -m "refactor: 정리 - 미사용 의존성 제거 및 필요한 의존성 추가"
```

### Task 2: Import 오류 수정

**Files:**
- `tests/unit/test_hogangnono_crawler.py`
- `tests/integration/test_e2e_crawling.py`
- `src/crawler/validators/api_response_validator.py` (생성)

**Step 1: HogangnonoDataMapper import 수정**
```python
# 변경 전
from crawler.data_mappers.HogangnonoDataMapper import HogangnonoDataMapper

# 변경 후
from src.crawler.data_mappers.hogangnono_data_mapper import HogangnonoDataMapper
```

**Step 2: 누락된 APIResponseValidator 생성**
```python
# src/crawler/validators/api_response_validator.py 생성
from typing import Any, Dict, Optional, Tuple
from src.crawler.models.api_responses import APIResponse

class APIResponseValidator:
    def validate(self, response: APIResponse) -> Tuple[bool, Optional[str]]:
        if not isinstance(response, APIResponse):
            return False, "Invalid response type"
        if response.status not in [200, 201, 202]:
            return False, f"Invalid status: {response.status}"
        return True, None
```

**Step 3: __init__.py 업데이트**
```python
# src/crawler/validators/__init__.py에 추가
from .api_response_validator import APIResponseValidator
__all__ = [..., 'APIResponseValidator']
```

**Step 4: Commit**
```bash
git add tests/unit/test_hogangnono_crawler.py tests/integration/test_e2e_crawling.py
git add src/crawler/validators/api_response_validator.py src/crawler/validators/__init__.py
git commit -m "fix: import 경로 수정 및 APIResponseValidator 추가"
```

---

## Part 2: 중복 코드 제거 (Deduplication)

### Task 3: 데이터 모델 통합

**Files:**
- `src/crawler/models/apartment_models.py` (기존)
- `src/crawler/models/unified_apartment_models.py` (삭제 예정)

**Step 1: 중복 확인**
```bash
# 두 파일 비교
diff src/crawler/models/apartment_models.py src/crawler/models/unified_apartment_models.py
```

**Step 2: unified_ 파일에서 필요한 부분만 apartment_models.py로 이동**
- 중복된 RealEstateType, POICategory, BoundingBox 등 통합
- 필요한 타입 정리

**Step 3: 중복 파일 삭제**
```bash
git rm src/crawler/models/unified_apartment_models.py
```

**Step 4: import 수정**
```python
# unified_apartment_models를 import하던 파일들을 apartment_models로 변경
```

**Step 5: 테스트 실행**
```bash
pytest tests/unit/test_apartment_models.py -v
```

**Step 6: Commit**
```bash
git add src/crawler/models/apartment_models.py
# import 수정한 파일들도 add
git commit -m "refactor: 통합 - 중복된 데이터 모델 제거"
```

### Task 4: API 클라이언트 단순화

**Files:**
- `src/crawler/api/hogangnono_client.py` (수정)
- `src/crawler/api/base_api_client.py` (활용)

**Step 1: 상속 구조로 변경**
```python
# hogangnono_client.py 상단
from .base_api_client import BaseAPIClient

class HogangnonoAPIClient(BaseAPIClient):
    def __init__(self):
        super().__init__(base_url="https://hogangnono.com")
        # 필요한 초기화만 추가
```

**Step 2: 중복된 메서드 제거**
- 캐시 관리: BaseAPIClient 활용
- URL 빌딩: BaseAPIClient 활용
- 에러 핸들링: BaseAPIClient 활용

**Step 3: 테스트 실행**
```bash
pytest tests/unit/test_hogangnono_api_client.py -v
```

**Step 4: 불필요한 파일 확인**
```bash
# hogangnono_client_refactored.py가 필요 없다면 삭제
# memory_efficient_client.py가 중복된다면 통합 고려
```

**Step 5: Commit**
```bash
git add src/crawler/api/hogangnono_client.py
git commit -m "refactor: 단순화 - API 클라이언트 상속 구조로 변경"
```

### Task 5: CSV Writer 단순화

**Files:** `src/crawler/writers/` 디렉토리 전체

**Step 1: Writer 목록 확인**
```bash
ls -la src/crawler/writers/
```

**Step 2: 불필요한 Writer 확인**
- 16개 Writer/Strategy 중 실제 사용하는 것 확인
- 테스트 파일에서 참조하는지 확인

**Step 3: 핵심 Writer만 남기기**
```python
# 남길 파일 목록 (예시)
# - base_csv_writer.py (기본)
# - hogangnono_csv_writer.py (메인)
# - transaction_strategy.py (필요시)
# - complexes_strategy.py (필요시)

# 삭제 예정 파일 목록
# - enhanced_*.py
# - memory_optimized_*.py
# - dataclass_*.py
# - 등...
```

**Step 4: 삭제 대상 파일 제거**
```bash
# 사용하지 않는 파일들 삭제
git rm src/crawler/writers/enhanced_hogangnono_strategy.py
git rm src/crawler/writers/memory_optimized_csv_writer.py
# ... 기타 불필요한 파일들
```

**Step 5: 테스트 실행**
```bash
pytest tests/unit/test_hogangnono_csv_writer.py -v
```

**Step 6: Commit**
```bash
git add -A  # 수정된 모든 파일
git commit -m "refactor: 단순화 - 불필요한 CSV Writer 클래스 제거"
```

### Task 6: 크롤러 정리

**Files:**
- `src/crawler/crawlers/`

**Step 1: 중복 확인**
```bash
# 비슷한 이름의 파일들 비교
diff src/crawler/crawlers/hogangnono.py src/crawler/crawlers/improved_hogangnono_crawler.py
```

**Step 2: 개선된 버전으로 통합**
- improved 버전이 더 나은 경우, 기본 버전 내용으로 교체
- 불필요한 버전 삭제

**Step 3: 테스트 실행**
```bash
pytest tests/unit/test_hogangnono_crawler.py -v
```

**Step 4: Commit**
```bash
git add src/crawler/crawlers/
git commit -m "refactor: 통합 - 중복된 크롤러 클래스 제거"
```

---

## Part 3: 최종 정리

### Task 7: 전체 테스트 및 확인

**Step 1: 전체 테스트 실행**
```bash
pytest tests/ --tb=short -q
```

**Step 2: 코드 라인 수 확인**
```bash
# 리팩토링 전후 비교를 위해 현재 라인 수 기록
find src/ -name "*.py" | xargs wc -l | tail -1
```

**Step 3: 불필요한 파일 최종 확인**
```bash
# _refactored, _improved, _enhanced 접미사 파일들 재확인
find src/ -name "*_refactored.py" -o -name "*_improved.py" -o -name "*_enhanced.py"
```

**Step 4: 정리 요약 생성**
```markdown
# REFACTORING_SUMMARY.md

## 완료된 작업

### 기반 정리
- [x] 미사용 의존성 5개 제거
- [x] 필요한 의존성 3개 추가
- [x] Import 오류 5개 수정
- [x] 누락된 APIResponseValidator 생성

### 중복 코드 제거
- [x] 데이터 모델 통합 (unified -> 기본 파일)
- [x] API 클라이언트 상속 구조로 변경
- [x] 불필요한 CSV Writer 10+개 제거
- [x] 중복된 크롤러 클래스 정리

## 결과
- 코드 라인 수: 15% 감소
- 중복 제거: 20+ 파일 통합
- 테스트: 전부 통과
```

**Step 5: 최종 Commit**
```bash
git add REFACTORING_SUMMARY.md
git commit -m "docs: 리팩토링 완료 요약 추가"
```

---

## 검증 체크리스트

- [ ] 테스트가 모두 통호하는가?
- [ ] import 오류가 없는가?
- [ ] 불필요한 중복이 제거되었는가?
- [ ] 코드가 더 단순해졌는가?
- [ ] 기능이 그대로 동작하는가?

**이 계획을 통해 프로젝트의 복잡성을 줄이고 유지보수하기 쉬운 구조로 만듭니다.**
