#!/usr/bin/env python3
"""dataclass vs Pydantic 실제 차이 예시

실행:
    uv run python scripts/example_dataclass_vs_pydantic.py
"""

import json
import time
from dataclasses import asdict, dataclass, field

# Pydantic은 이미 프로젝트 의존성에 있음
from pydantic import BaseModel, Field, ValidationError, field_validator

# ============================================================================
# 1. 기본 정의 비교
# ============================================================================


# dataclass 버전
@dataclass
class StatsDataclass:
    """dataclass 버전 - 검증 없음"""

    total: int = 0
    success: int = 0
    codes: list[str] = field(default_factory=list)

    def add(self, code: str, is_success: bool) -> None:
        self.total += 1
        if is_success:
            self.success += 1
        self.codes.append(code)


# Pydantic 버전
class StatsPydantic(BaseModel):
    """Pydantic 버전 - 자동 검증"""

    total: int = 0
    success: int = 0
    codes: list[str] = Field(default_factory=list)

    def add(self, code: str, is_success: bool) -> None:
        self.total += 1
        if is_success:
            self.success += 1
        self.codes.append(code)

    @field_validator("total", "success")
    @classmethod
    def validate_non_negative(cls, v: int) -> int:
        """음수 검증"""
        if v < 0:
            raise ValueError("음수는 허용되지 않습니다")
        return v


# ============================================================================
# 2. 실제 동작 차이 테스트
# ============================================================================


def test_validation_difference():
    """검증 동작 차이"""
    print("\n" + "=" * 60)
    print("1. 검증(Validation) 동작 차이")
    print("=" * 60)

    # dataclass - 검증 없음
    print("\n[dataclass] 잘못된 타입 전달:")
    dc = StatsDataclass(total="문자열", success="100")  # 타입 틀려도 에러 없음
    print(f"  total: {dc.total!r} (타입: {type(dc.total).__name__})")
    print("  → 문제없이 생성됨 (버그 가능성)")

    # Pydantic - 자동 검증
    print("\n[Pydantic] 잘못된 타입 전달:")
    try:
        StatsPydantic(total="문자열", success="100")
    except ValidationError as e:
        print("  → ValidationError 발생!")
        print(f"  → 에러 메시지: {e.error_count()}개")


def test_json_conversion():
    """JSON 변환 차이"""
    print("\n" + "=" * 60)
    print("2. JSON 변환 차이")
    print("=" * 60)

    dc = StatsDataclass(total=100, success=80, codes=["A001", "B002"])
    pyd = StatsPydantic(total=100, success=80, codes=["A001", "B002"])

    print("\n[dataclass] JSON 변환:")
    print(f"  → asdict(): {asdict(dc)}")
    print(f"  → JSON 변환: {json.dumps(asdict(dc), ensure_ascii=False)}")

    print("\n[Pydantic] JSON 변환:")
    print(f"  → model_dump(): {pyd.model_dump()}")
    print(f"  → model_dump_json(): {pyd.model_dump_json()}")


def test_type_coercion():
    """타입 강제 변환 차이"""
    print("\n" + "=" * 60)
    print("3. 타입 강제 변환 (Type Coercion)")
    print("=" * 60)

    # dataclass - 변환 없음
    print("\n[dataclass] 문자열 '123'을 int 필드에 전달:")
    dc = StatsDataclass(total="123")  # 문자열 그대로 저장
    print(f"  total: {dc.total!r} (여전히 문자열)")

    # Pydantic - 자동 변환
    print("\n[Pydantic] 문자열 '123'을 int 필드에 전달:")
    pyd = StatsPydantic(total="123")  # 자동으로 int로 변환
    print(f"  total: {pyd.total!r} (자동으로 int로 변환됨)")


def test_performance():
    """성능 비교"""
    print("\n" + "=" * 60)
    print("4. 성능 비교 (객체 생성 100,000회)")
    print("=" * 60)

    iterations = 100_000

    # dataclass 벤치마크
    start = time.perf_counter()
    for i in range(iterations):
        _ = StatsDataclass(total=i, success=i // 2, codes=[f"CODE{i}"])
    dc_time = time.perf_counter() - start

    # Pydantic 벤치마크
    start = time.perf_counter()
    for i in range(iterations):
        _ = StatsPydantic(total=i, success=i // 2, codes=[f"CODE{i}"])
    pyd_time = time.perf_counter() - start

    print(f"\n  dataclass: {dc_time:.4f}초")
    print(f"  Pydantic:  {pyd_time:.4f}초")
    print(f"  차이:      {pyd_time / dc_time:.1f}배 느림")


def test_immutability():
    """불변성 (Frozen)"""
    print("\n" + "=" * 60)
    print("5. 불변성 (Immutability)")
    print("=" * 60)

    # dataclass frozen
    @dataclass(frozen=True)
    class FrozenDataclass:
        value: int

    # Pydantic frozen
    class FrozenPydantic(BaseModel):
        value: int

        model_config = {"frozen": True}

    print("\n[dataclass frozen=True] 값 변경 시도:")
    dc = FrozenDataclass(value=10)
    try:
        dc.value = 20
    except Exception as e:
        print(f"  → {type(e).__name__}: {e}")

    print("\n[Pydantic frozen=True] 값 변경 시도:")
    pyd = FrozenPydantic(value=10)
    try:
        pyd.value = 20
    except Exception as e:
        print(f"  → {type(e).__name__}: {e}")


# ============================================================================
# 실제 크롤링 상황 시뮬레이션
# ============================================================================


def simulate_crawl_stats():
    """실제 크롤링 상황에서의 사용"""
    print("\n" + "=" * 60)
    print("6. 실제 크롤링 통계 사용 시뮬레이션")
    print("=" * 60)

    # dataclass로 통계 관리
    @dataclass
    class CrawlStats:
        total_processed: int = 0
        data_found: int = 0
        empty_dongs: int = 0
        error_dongs: int = 0

    stats = CrawlStats()

    # 크롤링 시뮬레이션
    print("\n[dataclass] 크롤링 진행:")
    for i in range(10):
        stats.total_processed += 1
        if i % 3 == 0:
            stats.data_found += 1
        elif i % 3 == 1:
            stats.empty_dongs += 1
        else:
            stats.error_dongs += 1

    print(
        f"  처리: {stats.total_processed}, 데이터: {stats.data_found}, "
        f"공백: {stats.empty_dongs}, 에러: {stats.error_dongs}"
    )
    print("  → 검증 없이 단순 카운트만 필요하므로 dataclass 적합")


# ============================================================================
# 메인
# ============================================================================


def main():
    print("\n" + "=" * 60)
    print("dataclass vs Pydantic 실제 차이")
    print("=" * 60)

    test_validation_difference()
    test_json_conversion()
    test_type_coercion()
    test_performance()
    test_immutability()
    simulate_crawl_stats()

    print("\n" + "=" * 60)
    print("요약")
    print("=" * 60)
    print("""
[dataclass 사용 경우]
  • 내부 데이터 구조 (검증 불필요)
  • 성능이 중요한 루프
  • 단순한 데이터 컨테이너
  예: 크롤링 통계, 내부 계산 결과

[Pydantic 사용 경우]
  • API 경계 (외부 입력/출력)
  • 데이터 무결성이 중요한 경우
  • JSON 변환이 빈번한 경우
  예: API 응답 DTO, 사용자 입력 검증
    """)


if __name__ == "__main__":
    main()
