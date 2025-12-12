# Test Runner

Python의 내장 unittest 모듈을 사용하여 pytest 없이 테스트를 실행할 수 있는 간단한 테스트 러너 스크립트입니다.

## 기능

- Python의 내장 `unittest` 모듈 사용 (pytest 불필요)
- `tests/` 디렉토리에서 모든 테스트 자동 발견
- `src/` 디렉토리의 모듈을 import 할 수 있도록 Python path 자동 설정
- pytest 스타일의 테스트 클래스를 unittest로 동적 변환
- structlog 의존성이 없는 경우 mock 모듈 자동 설치
- clear한 출력으로 테스트 결과 표시

## 사용법

### 모든 테스트 실행
```bash
python test_runner.py
```

### 상세 출력
```bash
python test_runner.py -v
```

### 간단한 출력 (점과 요약만 표시)
```bash
python test_runner.py -q
```

### 특정 패턴이 포함된 테스트만 실행
```bash
python test_runner.py --pattern base_csv_writer
python test_runner.py --pattern integration
python test_runner.py --pattern unit
```

### 발견된 테스트 목록만 확인 (실행하지 않음)
```bash
python test_runner.py --list
```

## 지원하는 기능

### 테스트 스타일
- unittest.TestCase를 상속받은 표준 unittest 테스트
- `Test`로 시작하는 클래스의 pytest 스타일 테스트 (자동 변환)

### Fixtures
- `tmp_path` fixture: 임시 디렉토리를 생성하여 제공
- `pytest.skip`: unittest의 skipTest로 변환
- `pytest.raises`: unittest의 assertRaises로 변환
- `pytest.mark.parametrize`: 기본 지원 (단순한 경우만)

### 의존성 모킹
- `pytest` 모듈: unittest로 변환하는 mock 제공
- `pytest.MonkeyPatch`: 더미 구현 제공
- `structlog`: 설치되지 않은 경우 mock 모듈 자동 설치

## 제한 사항

- 복잡한 pytest fixtures는 지원되지 않을 수 있습니다
- `pytest.mark.parametrize`의 복잡한 사용은 지원되지 않습니다
- 일부 테스트 파일의 구조적 문제(예: 클래스 내부의 import 문)는 처리되지 않을 수 있습니다
- pydantic과 같은 외부 의존성이 필요한 테스트는 실행되지 않습니다

## 예제

```bash
# CSV writer 관련 테스트 실행
$ python test_runner.py --pattern csv_writer

# 상세 출력으로 특정 테스트 실행
$ python test_runner.py --pattern data_transformation -v

# 발견된 모든 테스트 목록 확인
$ python test_runner.py --list
```

## 요구 사항

- Python 3.7+
- 테스트를 실행하기 위한 최소한의 의존성 (unittest, pathlib 등)

## 에러 처리

- import 실패: 해당 모듈을 건너뛰고 계속 실행
- 로드 실패: 에러 메시지를 출력하고 다음 모듈로 진행
- 실행 실패: 실패/에러/건너뛴 테스트 수를 요약하여 표시
