# Playwright 크롤링 데이터 검증 시스템

호갱노노 웹사이트의 실제 데이터와 크롤링된 CSV 데이터를 비교하여 크롤링 정확도를 검증하는 시스템입니다.

## 기능

1. **실시간 웹 데이터 비교**: Playwright를 사용하여 호갱노노 웹사이트에 접속하고 실제 데이터를 추출
2. **정확도 측정**: CSV 데이터와 웹 데이터를 필드별로 비교하여 정확도 계산
3. **다양한 검증 시나리오**: 지역별, 랜덤 샘플링, 종합 검증 지원
4. **상세 보고서 생성**: JSON 및 HTML 형식의 검증 보고서 생성
5. **데이터 품질 분석**: 누락된 데이터, 잘못된 데이터 식별 및 개선 제안

## 설치

### 의존성 설치

```bash
# playwright 설치
pip install playwright
playwright install

# 필요한 Python 패키지 설치
pip install structlog
```

## 사용 방법

### 1. 기본 검증 실행

```bash
# 종합 검증 (권장)
python run_verification.py --csv-path output/complexes.csv --mode comprehensive

# 특정 지역 검증
python run_verification.py --csv-path output/complexes.csv --mode region --region "종로구" --sample-size 10

# 랜덤 샘플링 검증
python run_verification.py --csv-path output/complexes.csv --mode random --sample-size 20
```

### 2. 직접 검증 스크립트 실행

```python
import asyncio
from test_playwright_verification import PlaywrightDataVerifier

async def main():
    verifier = PlaywrightDataVerifier("output/complexes.csv")
    report = await verifier.verify_sample_data(sample_size=10, region="강남구")
    verifier.save_report(report)

asyncio.run(main())
```

## 검증 결과

### 보고서 형식

1. **JSON 보고서**: 상세 데이터가 포함된 기계 가독 형식
2. **HTML 보고서**: 시각화된 사람 가독 형식

### 보고서 내용

- 전체 정확도 통계
- 필드별 정확도 분석
- 누락된 데이터 목록
- 잘못된 데이터 목록
- 개선 제안

### 보고서 예시

```
=== 검증 완료 ===
총 비교 수: 10
일치 데이터: 7
전체 정확도: 85.2%
보고서 저장 위치: verification_reports/
```

## 검증 필드

시스템은 다음 필드들을 검증합니다:

- `complex_name`: 아파트명
- `completion_year_month`: 건축년도 (±1년 오차 허용)
- `total_household_count`: 세대수 (±10세대 오차 허용)
- `deal_count`: 거래 건수 (±5건 오차 허용)
- `address`: 주소

## 검증 모드

### 1. 지역별 검증 (region)

특정 지역의 아파트 데이터만 검증합니다.

```bash
python run_verification.py --mode region --region "종로구"
```

### 2. 랜덤 샘플링 (random)

전체 데이터에서 무작위로 샘플을 추출하여 검증합니다.

```bash
python run_verification.py --mode random --sample-size 15
```

### 3. 종합 검증 (comprehensive)

여러 지역과 다양한 샘플링 크기로 종합적으로 검증합니다.

- 종로구 (10개)
- 강남구 (10개)
- 서초구 (8개)
- 마포구 (8개)
- 랜덤 샘플링 (10개, 15개)

## 결과 해석

### 정확도 점수

- 90-100%: 매우 우수
- 80-89%: 우수
- 70-79%: 보통
- 60-69%: 개선 필요
- 60% 미만: 심각한 문제

### 개선 제안 유형

1. **데이터 매핑 로직 검토**: 특정 필드의 정확도가 낮을 때
2. **웹사이트 구조 변경 확인**: 데이터가 누락될 때
3. **정규화 규칙 검토**: 숫자형 필드 파싱 오류 시
4. **전체적인 크롤러 검토**: 전체 정확도가 80% 미만일 때

## 주의사항

1. **웹사이트 접속 제한**: 과도한 요청은 IP 차단될 수 있으니 적절한 간격을 두고 실행
2. **동적 데이터**: 실시간으로 변하는 데이터(거래 건수 등)는 약간의 오차가 있을 수 있음
3. **브라우저 설치**: 최초 실행 시 Playwright 브라우저 설치 필요
4. **인터넷 연결**: 웹사이트 접속을 위한 안정적인 인터넷 연결 필요

## 출력 디렉토리 구조

```
verification_reports/
├── verification_report_YYYYMMDD_HHMMSS.json
├── verification_report_YYYYMMDD_HHMMSS.html
├── 종로구/
│   ├── verification_report_YYYYMMDD_HHMMSS.json
│   └── verification_report_YYYYMMDD_HHMMSS.html
├── 강남구/
│   └── ...
├── random_sampling_10/
│   └── ...
└── comprehensive_report_YYYYMMDD_HHMMSS.json
```

## 예제 시나리오

### 시나리오 1: 신규 아파트 데이터 크롤링 후 검증

```bash
# 1. 크롤링 실행
python scripts/main.py --region "종로구"

# 2. 검증 실행
python run_verification.py --csv-path output/complexes.csv --mode region --region "종로구"

# 3. 보고서 확인
open verification_reports/종로구/verification_report_*.html
```

### 시나리오 2: 주기적인 데이터 품질 모니터링

```bash
# 종합 검증 실행 (cron 등 주기적 실행)
python run_verification.py --csv-path output/complexes.csv --mode comprehensive

# 결과 확인
open verification_reports/comprehensive_report_*.json
```

### 시나리오 3: 특정 필드의 정확도 개선 후 검증

```bash
# 소규모 샘플로 빠르게 검증
python run_verification.py --csv-path output/complexes.csv --mode random --sample-size 5

# 결과 분석 후 문제 해결
# ...
```

## 문제 해결

### 공통 문제

1. **"CSV 파일을 찾을 수 없습니다"**
   - CSV 파일 경로 확인
   - 크롤링이 성공적으로 완료되었는지 확인

2. **"웹 데이터 추출 실패"**
   - 인터넷 연결 확인
   - 호갱노노 웹사이트 접속 가능 여부 확인
   - Playwright 브라우저 설치 확인

3. **"데이터 일치율이 너무 낮습니다"**
   - 크롤러의 데이터 추출 로직 확인
   - 웹사이트 구조 변경 확인
   - 데이터 매핑 규칙 검토
