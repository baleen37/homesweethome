# HomeSweetHome Crawler

Python 기반 웹 크롤링 프레임워크로, 호갱노노 부동산 데이터 수집에 최적화되어 있습니다.

## 🎯 주요 특징 (2025-12-12 MVP 단순화)

### ✅ 단순화된 아키텍처

1. **직관적인 구조**
   - 의존성 주입 제거 및 직접 의존성 생성
   - 단순한 에러 처리 (try/except)
   - 기본 로깅만 유지

2. **고정된 설정**
   - 환경별 YAML 파일 제거
   - Config 클래스로 단순화
   - 하드코딩된 기본값 사용

3. **단순화된 기능**
   - BBox 고정 4x4 그리드 분할
   - 기본 체크포인트 시스템
   - 단일 CSV Writer (HogangnonoCSVWriter)

4. **핵심 기능 유지**
   - 아파트 정보 수집
   - 실거래 내역 조회
   - 지역별 크롤링
   - 체크포인트를 통한 재개 기능

## 사용 방법

### Nix를 사용하는 경우 (권장)

```bash
# 1. Nix 설치 (https://nixos.org/download.html)
# 2. direnv 설치 및 설정
# macOS: brew install direnv
# Ubuntu: sudo apt install direnv

# 3. direnv 설정 (shell config에 추가)
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc
# 또는 zsh의 경우
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc

# 4. 프로젝트 진입 (자동으로 Nix 환경 활성화)
cd homesweethome
direnv allow  # 최초 1회만 실행

# 5. 의존성 설치
uv sync

# 6. Playwright 브라우저 설치
uv run playwright install chromium
```

### 기존 방식 (uv 직접 사용)

```bash
# 의존성 설치
uv sync

# Playwright 브라우저 설치
uv run playwright install chromium

# pre-commit 설치
uv run pre-commit install
```

## 프로젝트 구조

```
homesweethome/
├── src/
│   └── crawler/
│       ├── api/                 # API 클라이언트
│       │   ├── base_api_client.py
│       │   └── hogangnono_client.py
│       ├── crawlers/            # 크롤러 구현
│       │   ├── simple_crawler.py     # 메인 크롤러 (MVP)
│       │   └── improved_hogangnono_crawler.py
│       ├── data_mappers/        # 데이터 매핑
│       ├── models/              # 데이터 모델
│       ├── utils/               # 유틸리티
│       │   ├── checkpoint.py
│       │   ├── bbox_division.py
│       │   └── simple_error_handler.py
│       ├── validators/          # 데이터 검증
│       └── writers/             # CSV/파일 출력
│           ├── base_csv_writer.py
│           └── hogangnono_csv_writer.py
├── config.py                    # 단일 설정 파일
├── scripts/                     # 실행 스크립트
│   └── main_improved.py         # 메인 실행 스크립트
├── factories.py                 # 크롤러 팩토리
└── tests/                       # 테스트 코드
    ├── unit/                    # 단위 테스트
    └── integration/             # 통합 테스트
```

## 🚀 빠른 시작

### 1. SimpleCrawler 사용 (권장)

```python
from pathlib import Path
from crawler.factories import create_crawler

# 간단한 크롤러 생성
crawler = create_crawler(
    output_dir=Path("output"),
    region_bounds=(37.413294, 126.734086, 37.715133, 127.183394)  # 서울시
)

# 크롤링 실행
stats = crawler.crawl_and_save(
    districts=["강남구", "서초구"],
    full_period=False
)

# 결과 확인
print(f"처리된 구/군: {stats['districts_completed']}")
print(f"발견된 아파트: {stats['apartments_found']}")
print(f"에러 수: {stats['errors']}")
```

### 2. 직접 SimpleCrawler 사용

```python
from crawler.crawlers.simple_crawler import SimpleCrawler

# 직접 크롤러 생성
crawler = SimpleCrawler(
    output_dir="output",
    region_bounds=(37.413294, 126.734086, 37.715133, 127.183394)
)

# bbox 분할 테스트
bboxes = crawler.divide_bbox_simple(37.5, 126.9, 37.6, 127.0)
print(f"생성된 bbox 개수: {len(bboxes)}")
```

## 📋 실행 방법

### 기본 실행

```bash
# 기본 크롤링 (개선된 버전)
uv run python scripts/main_improved.py

# 환경 지정
uv run python scripts/main_improved.py --env development

# 특정 구만 크롤링
uv run python scripts/main_improved.py --district 강남구,서초구

# 출력 디렉토리 지정
uv run python scripts/main_improved.py --output results/20251212
```

### 고급 옵션

```bash
# 전체 기간 데이터 수집
uv run python scripts/main_improved.py --full-period

# 로그 레벨 지정
uv run python scripts/main_improved.py --log-level DEBUG

# 체크포인트에서 재개
uv run python scripts/main_improved.py --resume

# 병렬 처리 worker 수 지정
uv run python scripts/main_improved.py --workers 4
```

## 🏗️ 아키텍처

### 단순화된 구조

```
SimpleCrawler
├── HogangnonoAPIClient (API 통신)
├── HogangnonoDataMapper (데이터 변환)
├── HogangnonoCSVWriter (CSV 저장)
├── CheckpointManager (체크포인트)
└── SimpleErrorHandler (기본 에러 처리)
```

### 단순화된 에러 핸들링

```
API 요청
    ↓
try/except 블록
    ↓
에러 발생 시:
- 로깅
- 계속 진행 (스킵)
```

## 🔧 설정

### 단일 Config 클래스

하드코딩된 기본값을 사용하며, 필요한 경우 직접 수정할 수 있습니다:

```python
# config.py 참조
class Config:
    BASE_URL = "https://hogangnono.com"
    RATE_LIMIT_DELAY = 2.0
    MAX_WORKERS = 4
    # ...
max_workers: 8              # 병렬 처리 worker 수

# 에러 핸들링
error_handling:
  max_retries: 3
  circuit_breaker_threshold: 10
  skip_404_errors: true
```

## 📊 출력 데이터

### 파일 구조

```
output/
├── complexes.csv           # 단지 정보
├── transactions.csv        # 거래 내역
├── checkpoint.json         # 진행 상황
├── error_stats.json        # 에러 통계
└── logs/                   # 로그 파일
```

### 주요 필드

#### Complexes (단지 정보)
- `aptSeq`: 단지 고유 ID
- `aptName`: 단지명
- `address`: 주소
- `buildYear`: 건축년도
- `poi_category`: POI 유형 (아파트/대중교통/공공시설/기타)
- `validation_result`: 검증 결과

#### Transactions (거래 내역)
- `complex_id`: 단지 ID
- `complex_name`: 단지명
- `trade_date`: 거래일 (YYYYMM)
- `deal_price`: 거래가
- `area`: 전용면적
- `floor`: 층

## 🧪 테스트

### 단위 테스트

```bash
# 전체 테스트
uv run pytest -v

# 단위 테스트
uv run pytest tests/unit/ -v

# 특정 테스트
uv run pytest tests/unit/test_enhanced_error_handler.py -v
```

### 통합 테스트

```bash
# 전체 통합 테스트
uv run pytest tests/integration/ -v

# 에러 시나리오 테스트
uv run pytest tests/integration/test_error_scenarios.py -v

# 성능 벤치마킹
uv run python scripts/benchmark.py
```

### 테스트용 Mock 크롤러

```python
from crawler.factories import CrawlerFactory
from pathlib import Path

factory = CrawlerFactory()

# Mock API를 사용하는 테스트 크롤러
test_crawler = factory.create_test_crawler(
    output_dir=Path("test_output"),
    mock_api=True
)
```

## 🔍 모니터링 및 디버깅


### 체크포인트 상태

```python
from crawler.utils.checkpoint import CheckpointManager

checkpoint = CheckpointManager("output/checkpoint.json")
stats = checkpoint.get_stats()

print(f"완료된 구/군: {len(stats['completed_districts'])}")
print(f"남은 구/군: {len(stats['remaining_districts'])}")
```

## ⚡ 성능 팁

1. **캐싱 활용**
   - 아파트 데이터와 동 코드를 자동 캐싱
   - 중복 API 호출 방지

2. **배치 처리**
   - 50개 단위로 배치 처리
   - 메모리 사용량 최적화

3. **병렬 처리**
   - 멀티스레딩 지원
   - worker 수 조절로 성능 최적화

4. **bbox 분할**
   - POI API 1000개 제한 우회
   - 적응적 분할로 최적화

## 🐛 문제 해결

### 흔한 문제들

1. **Rate Limit (429 에러)**
   - 해결: `rate_limit_delay` 증가
   - 설정: `rate_limit_delay: 3.0`

2. **많은 404 에러**
   - 해결: ID 필터링 강화
   - 확인: `validation_result` 필드

3. **메모리 부족**
   - 해결: `batch_size` 감소
   - 설정: `batch_size: 20`

4. **느린 속도**
   - 해결: `max_workers` 증가
   - 주의: API 제한 확인

### 로그 분석

```bash
# DEBUG 레벨 로그
tail -f output/logs/crawler.log | grep DEBUG

# 에러만 보기
tail -f output/logs/crawler.log | grep ERROR

# 404 에러 모니터링
tail -f output/logs/crawler.log | grep "apartment_not_found"
```

## 🤝 기여

1. Fork
2. Feature 브랜치 생성
3. 커밋 (`git commit -m 'Add some feature'`)
4. Push (`git push origin feature`)
5. Pull Request

## 📝 라이선스

MIT License

## API 문서

### 주요 API 클라이언트

#### BaseAPIClient
- 기본 API 통신 기능 제공
- 재시도 로직 및 에러 핸들링

#### HogangnonoAPIClient
- 호갱노노 API 전용 클라이언트
- 부동산 데이터 조회 기능

### API 엔드포인트

| 엔드포인트 | 설명 | 파라미터 |
|-----------|------|----------|
| `/aparts` | 아파트 목록 조회 | bbox, page, size |
| `/aparts/{id}` | 아파트 상세 정보 | apartment_id |
| `/aparts/{id}/transactions` | 거래 내역 | apartment_id, period |
| `/poi` | POI 정보 | bbox, category, limit |

자세한 API 문서는 [src/crawler/api/](src/crawler/api/) 디렉토리의 각 모듈 docstring을 참조하세요.

## 기여 가이드

### 코드 컨벤션

1. **Python 스타일 가이드**
   - PEP 8 준수
   - Black formatter 사용
   - isort for imports

2. **커밋 메시지**
   - feat: 새 기능
   - fix: 버그 수정
   - docs: 문서화
   - test: 테스트
   - refactor: 리팩토링

3. **PR 프로세스**
   - Fork 및 브랜치 생성
   - 테스트 통과 확인
   - 코드 리뷰 요청

### 개발 환경 설정

```bash
# 개발 환경 설정
git clone https://github.com/username/homesweethome.git
cd homesweethome
direnv allow
uv sync
uv run pre-commit install

# 테스트 실행
uv run pytest -v

# 문서화 커버리지 확인
python test_documentation_coverage.py
```

## 🔗 관련 문서

- [아키텍처 가이드](docs/architecture.md)
- [테스트 가이드](docs/testing.md)
- [배포 가이드](docs/deployment.md)
