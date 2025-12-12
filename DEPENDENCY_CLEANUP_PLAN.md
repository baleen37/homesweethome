# 프로젝트 의존성 정리 계획

## 분석 결과 요약

### 주요 발견사항
1. **총 161개의 Python 파일** 분석 완료
2. **순환 의존성 없음** - 좋은 아키텍처 구조
3. **사용되지 않는 외부 의존성 다수 존재**
4. **일부 파일에서 과도한 의존성** 사용
5. **표준 라이브러리 vs 외부 라이브러리 사용 패턴** 개선 필요

## 1. pyproject.toml 의존성 정리

### 1.1 제거 필요한 의존성 (즉시 실행)
다음 의존성들은 pyproject.toml에 정의되어 있지만 실제로 사용되지 않습니다:

```yaml
# 제거할 의존성
dependencies:
- "beautifulsoup4>=4.12.0"      # 미사용
- "lxml>=5.0.0"                 # 미사용
- "nest-asyncio>=1.6.0"         # 미사용
- "python-dotenv>=1.0.0"        # .env 대신 yaml 사용
- "pytest-cov>=7.0.0"           # pytest로 커버리지 충분
```

### 1.2 추가 필요한 의존성
실제 사용되지만 정의되지 않은 의존성들:

```yaml
# 추가할 의존성
dependencies:
- "aiohttp>=3.8.0"              # HTTP 비동기 클라이언트
- "pyyaml>=6.0"                 # YAML 설정 파일
- "dependency-injector>=4.48.3" # 사용 중

dev-dependencies:
- "pytest>=8.0.0"               # 테스트 프레임워크
- "requests-mock>=1.12.1"       # 테스트용 모의 요청
```

## 2. 잠재적 미사용 Import 정리

### 2.1 단일 사용되는 Import들 (검토 필요)
다음 import들은 한 번만 사용되며 실제 필요성 검토 필요:

- `aiohttp` - memory_efficient_client.py에서만 사용
- `ijson` - large_dataset_processor.py에서만 사용
- `yaml` - factories.py에서만 사용
- `dependency_injector` - factories.py에서만 사용
- `astor` - clean_unused_imports_automated.py에서만 사용

### 2.2 테스트 관련 Import 정리
- `test_playwright_verification` - run_verification.py에서만 사용
- `find_unused_imports_tdd` - remove_unused_imports.py에서만 사용

## 3. 의존성 집중도 개선

### 3.1 의존성이 많은 파일 개선 (우선순위: 높음)

| 파일 | 의존성 수 | 개선 방안 |
|------|-----------|-----------|
| src/crawler/api/hogangnono_client.py | 30개 | - Facade 패턴 도입<br>- 기능별로 클래스 분리 |
| src/crawler/crawlers/hogangnono.py | 28개 | - Strategy 패턴으로 책임 분리 |
| src/crawler/crawlers/improved_hogangnono_crawler.py | 24개 | - 중복 코드 제거<br>- 공통 기능 추출 |
| src/crawler/crawlers/integrated_crawler.py | 20개 | - 컴포넌트 분리<br>- 의존성 주입 적용 |

### 3.2 내부 모듈 의존성 최적화

#### Writers 모듈
- `crawler.writers`가 55회 내부 모듈을 import
- 패키지 수준에서 __init__.py에 공통 import 정리

#### Utils 모듈
- 너무 많은 유틸리티가 분산
- 기능별로 세분화 (예: http_utils, file_utils 등)

## 4. 표준 라이브러리 활용 최적화

### 4.1 외부 라이브러리 대체 가능성 검토

| 현재 라이브러리 | 사용량 | 표준 라이브러리 대체 가능 여부 |
|----------------|--------|-----------------------------|
| pandas | 4회 | 간단한 CSV 처리라 csv 모듈 가능 |
| numpy | 2회 | 기본 통계라 statistics 모듈 가능 |
| pydantic | 7회 | 복잡한 검증이 필요하여 유지 |

### 4.2 추천 대체 방안

#### pandas → csv
```python
# 현재
import pandas as pd
df = pd.read_csv('file.csv')

# 개선
import csv
with open('file.csv', 'r') as f:
    reader = csv.DictReader(f)
    data = list(reader)
```

#### numpy → statistics
```python
# 현재
import numpy as np
mean = np.mean(numbers)

# 개선
import statistics
mean = statistics.mean(numbers)
```

## 5. 실행 계획

### 단계 1: pyproject.toml 정리 (1일)
1. 미사용 의존성 제거
2. 필요한 의존성 추가
3. 버전 최신화

### 단계 2: 미사용 Import 제거 (2-3일)
1. vulture 도구로 미사용 import 식별
2. 각 파일별로 검토 및 제거
3. 테스트 실행으로 기능 확인

### 단계 3: 고의존성 파일 리팩토링 (1주)
1. hogangnono_client.py 리팩토링
   - API 요청, 데이터 처리, 에러 핸들링 분리
2. hogangnono.py 리팩토링
   - 크롤링 전략 별로 클래스 분리
3. 통합 테스트 실행

### 단계 4: 내부 모듈 구조 개선 (3-4일)
1. Utils 패키지 재구성
2. Writers 패키지 공통화
3. Validators 통합

### 단계 5: 표준 라이브러리 전환 (2일)
1. pandas/csv 전환
2. numpy/statistics 전환
3. 성능 비교 및 테스트

## 6. 예상 효과

### 6.1 직접적 효과
- **의존성 감소**: 약 20-30% 외부 라이브러리 의존성 감소
- **설치 속도 향상**: 불필요한 패키지 제거로 빠른 설치
- **유지보수 용이성**: 명확한 의존성 구조

### 6.2 장기적 효과
- **보안**: 불필요한 외부 라이브러리로 인한 보안 위험 감소
- **성능**: 표준 라이브러리 사용으로 최적화
- **이식성**: 외부 의존성 감소로 더 높은 이식성

## 7. 리스크 관리

### 7.1 주의사항
- 테스트 커버리지 100% 유지
- 변경사항은 작은 단위로 진행
- 각 단계별로 Git 커밋

### 7.2 롤백 계획
- 각 단계별 브랜치 관리
- 기능별로 독립적으로 테스트
- 문제 발생시 즉시 롤백 가능

## 8. 도구 및 자동화

### 8.1 사용할 도구
- **vulture**: 미사용 코드 탐지
- **pytest**: 테스트 자동화
- **ruff**: 코드 정적 분석
- **mypy**: 타입 검증

### 8.2 CI/CD 개선
- 의존성 변경 감지
- 자동 테스트 실행
- 성능 회귀 감지

## 9. 성공 지표

### 9.1 정량적 지표
- 외부 의존성 수: 33개 → 25개 이하
- 평균 파일당 의존성: 15% 감소
- 설치 시간: 20% 개선

### 9.2 정성적 지표
- 코드 이해도 향상
- 신규 개발자 온보딩 시간 단축
- 버그 발생률 감소

## 10. 다음 단계

1. **즉시 실행**: pyproject.toml에서 미사용 의존성 제거
2. **1주 내**: 미사용 import 정리 완료
3. **2주 내**: 고의존성 파일 리팩토링 시작
4. **1개월 내**: 전체 계획 완료 및 문서화

---

*본 계획은 프로젝트의 현재 상태를 바탕으로 작성되었으며, 진행 중 발생하는 이슈에 따라 유연하게 조정될 수 있습니다.*
