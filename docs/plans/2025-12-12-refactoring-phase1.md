# Phase 1: 기반 정비 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 프로젝트 기반 정비 - 의존성 정리, 테스트 인프라 복구, 기본 모니터링 설정

**Architecture:** 가장 먼저 프로젝트의 기술 부채를 해결하고 안정적인 기반을 구축

**Tech Stack:** Python 3.12+, pytest, pyproject.toml, vulture

---

## Task 1: 의존성 정리

### Task 1.1: pyproject.toml에서 미사용 의존성 제거

**Files:**
- Modify: `pyproject.toml`

**Step 1: 미사용 의존성 확인**

```bash
# 현재 pyproject.toml 확인
cat pyproject.toml
```

**Step 2: 미사용 의존성 제거**

제거할 의존성 목록:
- beautifulsoup4 (사용하지 않음)
- lxml (사용하지 않음)
- nest-asyncio (사용하지 않음)
- pytest-cov (대신 coverage 사용)
- python-dotenv (사용하지 않음)

**Step 3: 누락된 의존성 추가**

추가할 의존성 목록:
- aiohttp (실제 사용 중)
- pyyaml (실제 사용 중)
- dependency-injector (실제 사용 중)

**Step 4: 테스트 실행**

```bash
# 의존성 업데이트
uv sync

# 테스트 실행 가능한지 확인
pytest tests/unit/test_config.py -v
```

**Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "refactor: 정리 - 미사용 의존성 제거 및 누락된 의존성 추가"
```

### Task 1.2: 미사용 import 제거

**Files:**
- Create: `scripts/remove_unused_imports.py`
- Multiple files in src/ and tests/

**Step 1: vulture 설치 및 설정**

```bash
# vulture 추가
uv add vulture

# .vulture.cfg 생성
cat > .vulture.cfg << EOF
[paths]
src/
tests/

[ignore]
@vulture/whitelist.py
EOF
```

**Step 2: 미사용 import 식별 스크립트 작성**

```python
# scripts/remove_unused_imports.py
import subprocess
import sys
from pathlib import Path

def find_unused_imports():
    """vulture로 미사용 import 찾기"""
    result = subprocess.run(
        ['vulture', 'src/', 'tests/', '--min-confidence', '80'],
        capture_output=True,
        text=True
    )
    return result.stdout

def main():
    unused = find_unused_imports()
    if unused:
        print("미사용 import 발견:")
        print(unused)
        return 1
    else:
        print("미사용 import 없음")
        return 0

if __name__ == '__main__':
    sys.exit(main())
```

**Step 3: 미사용 import 확인**

```bash
python scripts/remove_unused_imports.py
```

**Step 4: 주요 파일에서 미사용 import 수동 제거**

확인할 파일 목록:
- `src/crawler/crawlers/hogangnono.py`
- `src/crawler/api/hogangnono_client.py`
- `src/crawler/writers/hogangnono_csv_writer.py`
- `tests/unit/test_hogangnono_crawler.py`

**Step 5: 테스트 실행**

```bash
pytest tests/unit/test_config.py tests/unit/test_base_csv_writer.py -v
```

**Step 6: Commit**

```bash
git add scripts/remove_unused_imports.py .vulture.cfg
# 수정된 파일들 add
git commit -m "refactor: 정리 - 미사용 import 제거 스크립트 추가 및 적용"
```

## Task 2: 테스트 인프라 복구

### Task 2.1: Import 오류 수정 (HogangnonoDataMapper)

**Files:**
- Modify: `tests/unit/test_hogangnono_crawler.py`
- Check: `src/crawler/data_mappers/hogangnono_data_mapper.py`

**Step 1: 오류 확인**

```bash
# 실패하는 테스트 확인
pytest tests/unit/test_hogangnono_crawler.py::TestHogangnonoCrawler::test_init -v
```

**Step 2: import 경로 수정**

```python
# tests/unit/test_hogangnono_crawler.py 상단
# 기존:
from crawler.data_mappers.HogangnonoDataMapper import HogangnonoDataMapper

# 수정:
from src.crawler.data_mappers.hogangnono_data_mapper import HogangnonoDataMapper
```

**Step 3: 테스트 실행**

```bash
pytest tests/unit/test_hogangnono_crawler.py::TestHogangnonoCrawler::test_init -v
```

**Step 4: 다른 import 오류 수정**

`tests/integration/test_e2e_crawling.py`도 동일한 방식으로 수정

**Step 5: Commit**

```bash
git add tests/unit/test_hogangnono_crawler.py tests/integration/test_e2e_crawling.py
git commit -m "fix: HogangnonoDataMapper import 경로 수정"
```

### Task 2.2: 누락된 api_response_validator 모듈 생성

**Files:**
- Create: `src/crawler/validators/api_response_validator.py`

**Step 1: 테스트 실행하여 오류 확인**

```bash
pytest tests/unit/test_api_response_validator.py -v
```

**Step 2: 필요한 기능 파악**

테스트 파일에서 필요한 기능 확인:
- APIResponseValidator 클래스
- validate 메서드
- is_valid 메서드

**Step 3: API 응답 검증기 구현**

```python
# src/crawler/validators/api_response_validator.py
from typing import Any, Dict, Optional
from src.crawler.models.api_responses import APIResponse

class APIResponseValidator:
    """API 응답 데이터의 유효성을 검증합니다."""

    def __init__(self):
        self.required_fields = ['status', 'data']
        self.valid_status_codes = [200, 201, 202]

    def validate(self, response: APIResponse) -> tuple[bool, Optional[str]]:
        """
        API 응답의 유효성 검증

        Returns:
            tuple: (is_valid, error_message)
        """
        if not isinstance(response, APIResponse):
            return False, "APIResponse 타입이 아닙니다"

        if response.status not in self.valid_status_codes:
            return False, f"유효하지 않은 상태 코드: {response.status}"

        if not response.data:
            return False, "응답 데이터가 비어있습니다"

        return True, None

    def is_valid(self, response: Dict[str, Any]) -> bool:
        """간단한 유효성 검증"""
        return all(field in response for field in self.required_fields)
```

**Step 4: __init__.py에 추가**

```python
# src/crawler/validators/__init__.py
from .api_response_validator import APIResponseValidator

__all__ = ['APIResponseValidator', ...]
```

**Step 5: 테스트 실행**

```bash
pytest tests/unit/test_api_response_validator.py -v
```

**Step 6: Commit**

```bash
git add src/crawler/validators/api_response_validator.py src/crawler/validators/__init__.py
git commit -m "feat: 추가 - APIResponseValidator 클래스 구현"
```

## Task 3: 기본 모니터링 설정

### Task 3.1: 성능 메트릭 수집 기본 설정

**Files:**
- Create: `src/crawler/monitoring/basic_metrics.py`
- Create: `tests/unit/test_basic_metrics.py`

**Step 1: 테스트 작성**

```python
# tests/unit/test_basic_metrics.py
import time
from unittest.mock import Mock, patch
from src.crawler.monitoring.basic_metrics import MetricsCollector

def test_metrics_collector_init():
    collector = MetricsCollector()
    assert collector.metrics == {}

def test_record_metric():
    collector = MetricsCollector()
    collector.record('api_call', 1.5, {'endpoint': '/test'})

    metrics = collector.get_metrics('api_call')
    assert len(metrics) == 1
    assert metrics[0]['duration'] == 1.5
    assert metrics[0]['metadata']['endpoint'] == '/test'

def test_get_average_duration():
    collector = MetricsCollector()
    collector.record('test_op', 1.0)
    collector.record('test_op', 2.0)
    collector.record('test_op', 3.0)

    avg = collector.get_average_duration('test_op')
    assert avg == 2.0
```

**Step 2: 테스트 실행 (실패 확인)**

```bash
pytest tests/unit/test_basic_metrics.py -v
```

**Step 3: 메트릭 수집기 구현**

```python
# src/crawler/monitoring/basic_metrics.py
import time
from collections import defaultdict, deque
from typing import Dict, List, Any, Optional

class MetricsCollector:
    """간단한 성능 메트릭 수집기"""

    def __init__(self, max_history: int = 1000):
        self.metrics: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.max_history = max_history

    def record(self, operation_type: str, duration: float, metadata: Optional[Dict] = None):
        """메트릭 기록"""
        metric = {
            'timestamp': time.time(),
            'duration': duration,
            'metadata': metadata or {}
        }

        self.metrics[operation_type].append(metric)

        # 히스토리 크기 제한
        if len(self.metrics[operation_type]) > self.max_history:
            self.metrics[operation_type] = self.metrics[operation_type][-self.max_history:]

    def get_metrics(self, operation_type: str) -> List[Dict[str, Any]]:
        """특정 타입의 모든 메트릭 반환"""
        return self.metrics.get(operation_type, [])

    def get_average_duration(self, operation_type: str) -> Optional[float]:
        """평균 소요 시간 계산"""
        metrics = self.get_metrics(operation_type)
        if not metrics:
            return None

        durations = [m['duration'] for m in metrics]
        return sum(durations) / len(durations)

    def get_stats(self, operation_type: str) -> Dict[str, Any]:
        """상세 통계"""
        metrics = self.get_metrics(operation_type)
        if not metrics:
            return {}

        durations = [m['duration'] for m in metrics]
        return {
            'count': len(metrics),
            'avg_duration': sum(durations) / len(durations),
            'min_duration': min(durations),
            'max_duration': max(durations),
            'total_duration': sum(durations)
        }
```

**Step 4: 테스트 실행**

```bash
pytest tests/unit/test_basic_metrics.py -v
```

**Step 5: Commit**

```bash
git add src/crawler/monitoring/basic_metrics.py tests/unit/test_basic_metrics.py
git commit -m "feat: 추가 - 기본 성능 메트릭 수집기"
```

### Task 3.2: 메모리 사용량 추적 기능

**Files:**
- Modify: `src/crawler/utils/memory_profiler.py` (기존 파일 개선)
- Test: `tests/unit/test_memory_profiler.py`

**Step 1: 현재 memory_profiler 확인**

```bash
cat src/crawler/utils/memory_profiler.py
```

**Step 2: 테스트 작성**

```python
# tests/unit/test_memory_profiler.py
from src.crawler.utils.memory_profiler import MemoryProfiler, track_memory_usage

def test_memory_profiler_init():
    profiler = MemoryProfiler()
    assert profiler.snapshots == []

def test_memory_snapshot():
    profiler = MemoryProfiler()
    initial = profiler.take_snapshot()

    assert 'memory_mb' in initial
    assert 'timestamp' in initial
    assert len(profiler.snapshots) == 1

def test_memory_usage_context_manager():
    with track_memory_usage() as tracker:
        # 메모리 사용 작업
        large_list = [i for i in range(100000)]

    assert len(tracker.snapshots) >= 2
    assert any('delta_mb' in snap for snap in tracker.snapshots)
```

**Step 3: MemoryProfiler 개선**

```python
# src/crawler/utils/memory_profiler.py
import time
import psutil
import os
from typing import Dict, List, Optional
from contextlib import contextmanager

class MemoryProfiler:
    """메모리 사용량 프로파일러"""

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.snapshots: List[Dict[str, float]] = []
        self.start_memory: Optional[float] = None

    def get_memory_mb(self) -> float:
        """현재 메모리 사용량 (MB)"""
        return self.process.memory_info().rss / 1024 / 1024

    def take_snapshot(self) -> Dict[str, float]:
        """메모리 스냅샷 기록"""
        current_memory = self.get_memory_mb()
        snapshot = {
            'timestamp': time.time(),
            'memory_mb': current_memory
        }

        if self.snapshots:
            delta = current_memory - self.snapshots[-1]['memory_mb']
            snapshot['delta_mb'] = delta

        self.snapshots.append(snapshot)
        return snapshot

    def get_peak_memory(self) -> Optional[float]:
        """최대 메모리 사용량"""
        if not self.snapshots:
            return None
        return max(s['memory_mb'] for s in self.snapshots)

    def get_total_increase(self) -> Optional[float]:
        """시작 이후 총 메모리 증가량"""
        if len(self.snapshots) < 2:
            return None
        return self.snapshots[-1]['memory_mb'] - self.snapshots[0]['memory_mb']

    def reset(self):
        """프로파일러 초기화"""
        self.snapshots = []
        self.start_memory = None

@contextmanager
def track_memory_usage():
    """메모리 사용량 추적 컨텍스트 매니저"""
    profiler = MemoryProfiler()
    profiler.take_snapshot()  # 시작 스냅샷

    try:
        yield profiler
    finally:
        profiler.take_snapshot()  # 종료 스냅샷
```

**Step 4: 테스트 실행**

```bash
pytest tests/unit/test_memory_profiler.py -v
```

**Step 5: 필요시 psutil 추가**

```bash
# psutil이 없다면 추가
uv add psutil
```

**Step 6: Commit**

```bash
git add src/crawler/utils/memory_profiler.py tests/unit/test_memory_profiler.py
# pyproject.toml에 psutil 추가했다면 함께 commit
git commit -m "refactor: 개선 - MemoryProfiler 기능 강화"
```

## Task 4: Phase 1 완료 확인

### Task 4.1: 모든 테스트 실행

**Step 1: 기본 테스트 실행**

```bash
pytest tests/unit/test_config.py tests/unit/test_base_csv_writer.py tests/unit/test_basic_metrics.py tests/unit/test_memory_profiler.py -v
```

**Step 2: import 오류 수정 확인**

```bash
pytest tests/unit/test_hogangnono_crawler.py::TestHogangnonoCrawler::test_init -v
pytest tests/unit/test_api_response_validator.py -v
```

**Step 3: 전체 테스트 확인**

```bash
pytest tests/ --tb=short -q
```

### Task 4.2: 의존성 상태 확인

**Step 1: vulture 재실행**

```bash
python scripts/remove_unused_imports.py
```

**Step 2: uv tree 확인**

```bash
uv tree
```

### Task 4.3: 최종 정리

**Step 1: 불필요한 파일 확인**

```bash
# 임시 파일 정리
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
```

**Step 2: Phase 1 완료 문서 작성**

```bash
# PHASE1_SUMMARY.md에 완료된 작업 기록
echo "# Phase 1 완료 요약

## 완료된 작업
- [x] 미사용 의존성 5개 제거
- [x] 누락된 의존성 3개 추가
- [x] 미사용 import 정리
- [x] HogangnonoDataMapper import 오류 수정
- [x] APIResponseValidator 모듈 생성
- [x] 기본 성능 메트릭 수집기 구현
- [x] MemoryProfiler 개선

## 남은 작업
- 없음

## 다음 Phase
- Phase 2: 중복 코드 제거" > PHASE1_SUMMARY.md
```

**Step 3: 최종 Commit**

```bash
git add PHASE1_SUMMARY.md
git commit -m "docs: Phase 1 완료 요약 추가"
```

---

## Phase 1 실행 전체 검증 체크리스트

- [ ] 모든 import 오류가 해결되었는가?
- [ ] 필요한 의존성만 남았는가?
- [ ] 기본 테스트들이 통과하는가?
- [ ] 메트릭 수집 기능이 동작하는가?
- [ ] 메모리 프로파일러가 개선되었는가?

**Phase 1이 성공적으로 완료되면 Phase 2: 중복 코드 제거를 진행합니다.**
