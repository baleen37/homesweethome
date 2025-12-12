# MVP 리팩토링 계획

## 목표
복잡한 코드를 제거하고 성능 최적화 기능을 제거하여 최대한 단순한 MVP 버전으로 리팩토링합니다.

## 대상
- HomeSweetHome 크롤러 코드베이스 단순화
- 유지보수성 향상 및 이해도 증진

## 태스크 목록

### Task 1: 불필요한 의존성 제거
- dependency-injector 라이브러리 제거
- Container 클래스 및 DI 설정 제거
- requirements.txt 정리

### Task 2: Writer 클래스 단순화 (22개 → 2개)
- HogangnonoCSVWriter 하나로 통합
- base_csv_writer.py만 유지
- 나머지 20개 writer 파일 제거
- 팩토리, 전략 패턴 제거

### Task 3: 설정 관리 단순화
- 환경별 YAML 파일 제거
- Config 클래스 하나로 단순화 (하드코딩된 값)
- ConfigurationManager 제거

### Task 4: 에러 핸들링 단순화
- EnhancedErrorHandler 제거
- CircuitBreaker 제거
- try/except 블록으로 단순화
- 기본 로깅만 유지

### Task 5: 성능 최적화 기능 제거
- BBox 적응적 분할 → 고정 4x4 그리드
- 캐싱 시스템 제거
- AdaptiveRateLimiter 제거
- 통계 수집 및 진행 추적 제거

### Task 6: 체크포인트 시스템 단순화
- CheckpointManager 단순화
- 완료된 구/군 목록만 파일에 저장
- 복잡한 상태 관리 제거

### Task 7: 유틸리티 단순화
- retry.py: 단순한 재시도 함수로 변경
- bbox_divider.py: 고정된 분할 로직으로 변경
- 불필요한 유틸리티 파일 제거

### Task 8: 메인 크롤러 단순화
- ImprovedHogangnonoCrawler → SimpleCrawler
- DI 제거 및 직접 의존성 생성
- 메인 로직 단순화

### Task 9: 테스트 단순화
- 불필요한 테스트 제거
- 단순화된 컴포넌트에 맞게 테스트 수정
- 기본 기능 테스트만 유지

### Task 10: 최종 정리 및 검증
- import 문 정리
- 미사용 코드 제거 확인
- 기본 동작 검증
- 문서 업데이트
