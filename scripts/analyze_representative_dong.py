"""대표동 패턴 분석 및 해결책 제안"""

from crawler.asil import AsilAptListCrawler


def finalize_solution():
    """최종 해결책 제안"""
    print("=" * 70)
    print("문래동 크롤링 중복 문제: 근본 원인 분석 및 해결책")
    print("=" * 70)
    print()

    # 1. 근본 원인
    print("## 1. 근본 원인")
    print()
    print("ASIL API는 영등포구의 특정 동(본동) 조회 시 해당 동 전체를 반환:")
    print()

    examples = [
        ("1156010100", "영등포동", 9, "영등포동 + 1~8가"),
        ("1156011700", "당산동", 7, "당산동 + 1~6가"),
        ("1156011900", "문래동", 6, "문래동 + 1~6가"),
    ]

    for code, name, count, desc in examples:
        result = AsilAptListCrawler(dong_code=code).crawl()
        print(f"  - {name} ({code})")
        print(f"    조회 결과: {desc} (총 {count}개 동)")
        print(f"    아파트 수: {len(result)}개")
        print()

    print("따라서 문래동1~6가를 각각 조회하면:")
    print("  - 문래동(1가): 문래동 전체 66개 반환")
    print("  - 문래2~6가: 각각 0개 또는 다른 지역 반환")
    print("  - 결과: 중복 발생")
    print()

    # 2. 일반적인 패턴
    print("## 2. 일반적인 패턴 (다른 지역)")
    print()
    print("대부분의 지역은 각 동이 독립적으로 동작:")
    print()

    normal_examples = [
        ("1171010100", "잠실1동", "잠실동만 반환"),
        ("1168010800", "역삼1동", "논현동 등 반환 (다른 지역)"),
        ("1171010200", "잠실2동", "신천동 등 반환 (다른 지역)"),
    ]

    for code, name, behavior in normal_examples:
        result = AsilAptListCrawler(dong_code=code).crawl()
        unique_dongs = len(set(apt.dong for apt in result))
        print(f"  - {name} ({code})")
        print(f"    동작: {behavior}")
        print(f"    고유 dong 코드: {unique_dongs}개")
        print()

    # 3. 대표동 자동 식별
    print('## 3. "대표동" 자동 식별 방법')
    print()
    print("방법 A: API 응답 패턴 분석 (가장 신뢰성 높음)")
    print("  - API 응답에 여러 dong 코드가 포함되면 대표동으로 간주")
    print("  - 반환된 dongname 목록을 분석하여 그룹화")
    print('  - 예: {"문래동", "문래동2가", ..., "문래동6가"} → 대표동 확인')
    print()
    print("방법 B: dongname 정규화")
    print('  - dongname에서 숫자와 "가"/"동" 접미사 제거')
    print('  - 예: "문래1가" → "문래", "문래동" → "문래"')
    print("  - 같은 그룹으로 묶어서 중복 제거")
    print()

    # 4. 구현 제안
    print("## 4. 구현 제안")
    print()
    print("### 4.1 대표동 감지 클래스")
    print()
    print("```python")
    print("class RepresentativeDongDetector:")
    print('    """대표동 여부를 자동 감지하는 클래스"""')
    print()
    print("    def is_representative(self, apt_list: list[AsilAptListDTO]) -> bool:")
    print('        """여러 dong을 반환하는지 확인"""')
    print("        unique_dongs = len(set(apt.dong for apt in apt_list))")
    print("        return unique_dongs > 1")
    print()
    print("    def get_dong_group(self, apt_list: list[AsilAptListDTO]) -> set[str]:")
    print('        """속한 모든 dong 코드 반환"""')
    print("        return set(apt.dong for apt in apt_list)")
    print()
    print("    def get_base_dongname(self, dongname: str) -> str:")
    print('        """동 이름에서 숫자 접미사 제거"""')
    print('        # "문래1가" → "문래", "문래동" → "문래"')
    print('        base = re.sub(r"[0-9]+가?$", "", dongname)')
    print('        return re.sub(r"동$", "", base)')
    print("```")
    print()

    print("### 4.2 중복 제거 로직")
    print()
    print("```python")
    print("def crawl_dongs_without_duplicates(dong_codes: list[str]) -> list[AsilAptListDTO]:")
    print('    """중복 없이 여러 동 크롤링"""')
    print("    detector = RepresentativeDongDetector()")
    print("    seen_dong_groups = set()")
    print("    all_results = []")
    print()
    print("    for code in dong_codes:")
    print("        result = AsilAptListCrawler(dong_code=code).crawl()")
    print("        ")
    print("        if detector.is_representative(result):")
    print("            # 대표동인 경우: 결과 저장하고 그룹 기록")
    print("            base_name = detector.get_base_dongname(result[0].dongname)")
    print("            seen_dong_groups.add(base_name)")
    print("            all_results.extend(result)")
    print("        else:")
    print("            # 일반동인 경우: 아직 속한 그룹이 없는지 확인")
    print("            base_name = detector.get_base_dongname(result[0].dongname)")
    print("            if base_name not in seen_dong_groups:")
    print("                all_results.extend(result)")
    print("    ")
    print("    return all_results")
    print("```")
    print()

    print("### 4.3 성능 최적화")
    print()
    print("- 대표동 조회 결과를 캐싱")
    print("- 같은 그룹의 다른 동 조회 시 캐시된 결과 활용")
    print("- 불필요한 API 요청 최소화")
    print()

    # 5. 결론
    print("## 5. 결론")
    print()
    print("✓ 문래동 중복 문제는 ASIL API의 대표동 패턴 때문")
    print("✓ 영등포구 외에도 다른 지역에 유사한 패턴 가능성")
    print("✓ 자동 감지 방식으로 범용적으로 해결 가능")
    print("✓ dongname 정규화 + 그룹 추적으로 중복 제거")
    print()
    print("다음 단계:")
    print("1. RepresentativeDongDetector 클래스 구현")
    print("2. 기존 크롤링 명령어에 중복 제거 로직 추가")
    print("3. 테스트 케이스 작성 (문래동, 당산동, 영등포동)")
    print("4. E2E 테스트로 중복 제거 확인")
    print()
    print("=" * 70)


if __name__ == "__main__":
    finalize_solution()
