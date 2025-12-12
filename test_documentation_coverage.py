#!/usr/bin/env python3
"""
문서화 커버리지 테스트
README.md, API 모듈, 복잡한 비즈니스 로직, 설정 파일들의 문서화 상태를 평가합니다.
"""

import ast
import sys
from pathlib import Path
from typing import Dict


class DocumentationCoverageAnalyzer:
    """문서화 커버리지를 분석하는 클래스"""

    def __init__(self):
        self.root_path = Path(__file__).parent
        self.results = {}

    def analyze_readme(self) -> Dict[str, any]:
        """README.md 문서화 상태 분석"""
        readme_path = self.root_path / "README.md"

        if not readme_path.exists():
            return {"exists": False, "score": 0}

        content = readme_path.read_text(encoding="utf-8")

        # 필수 섹션 확인
        required_sections = [
            "# 프로젝트 소개",
            "## 설치 방법",
            "## 사용 방법",
            "## 프로젝트 구조",
            "## API 문서",
            "## 기여 가이드",
        ]

        sections_found = sum(1 for section in required_sections if section in content)
        section_score = (sections_found / len(required_sections)) * 100

        # 설명 상세도 평가
        detail_score = min(len(content) / 2000 * 100, 100)  # 2000자를 100%로 기준

        return {
            "exists": True,
            "section_score": section_score,
            "detail_score": detail_score,
            "overall_score": (section_score + detail_score) / 2,
        }

    def analyze_python_module(self, module_path: Path) -> Dict[str, any]:
        """Python 모듈의 문서화 상태 분석"""
        if not module_path.exists():
            return {"exists": False, "score": 0}

        content = module_path.read_text(encoding="utf-8")

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return {"exists": True, "parseable": False, "score": 0}

        docstring_count = 0
        function_count = 0
        class_count = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_count += 1
                if ast.get_docstring(node):
                    docstring_count += 1
            elif isinstance(node, ast.ClassDef):
                class_count += 1
                if ast.get_docstring(node):
                    docstring_count += 1

        total_items = function_count + class_count
        docstring_ratio = (docstring_count / total_items * 100) if total_items > 0 else 0

        # 인라인 주석 확인
        comment_lines = sum(1 for line in content.split("\n") if line.strip().startswith("#"))
        total_lines = len([line for line in content.split("\n") if line.strip()])
        comment_ratio = (comment_lines / total_lines * 100) if total_lines > 0 else 0

        return {
            "exists": True,
            "parseable": True,
            "functions": function_count,
            "classes": class_count,
            "docstrings": docstring_count,
            "docstring_ratio": docstring_ratio,
            "comment_ratio": comment_ratio,
            "score": (docstring_ratio * 0.7 + comment_ratio * 0.3),
        }

    def analyze_api_modules(self) -> Dict[str, Dict]:
        """API 관련 모듈들의 문서화 상태 분석"""
        api_modules = [
            "src/crawler/api/base_api_client.py",
            "src/crawler/api/hogangnono_client.py",
            "src/crawler/api/memory_efficient_client.py",
        ]

        results = {}
        for module in api_modules:
            path = self.root_path / module
            results[module] = self.analyze_python_module(path)

        return results

    def analyze_business_logic(self) -> Dict[str, Dict]:
        """복잡한 비즈니스 로직 모듈들의 문서화 상태 분석"""
        business_modules = [
            "src/crawler/crawlers/hogangnono.py",
            "src/crawler/crawlers/apartment_search_crawler.py",
            "src/crawler/crawlers/improved_hogangnono_crawler.py",
            "src/crawler/writers/complex_strategy.py",
        ]

        results = {}
        for module in business_modules:
            path = self.root_path / module
            if path.exists():
                results[module] = self.analyze_python_module(path)

        return results

    def analyze_config_files(self) -> Dict[str, Dict]:
        """설정 파일들의 문서화 상태 분석"""
        config_files = ["config/development.yaml", "config/production.yaml"]

        results = {}
        for config_file in config_files:
            path = self.root_path / config_file
            if path.exists():
                content = path.read_text(encoding="utf-8")

                # 주석(설명)이 있는 설정 항목 비율
                lines = content.split("\n")
                commented_keys = 0
                total_keys = 0

                for idx, line in enumerate(lines):
                    line = line.strip()
                    if ":" in line and not line.startswith("#"):
                        total_keys += 1
                        # 이전 줄에 주석이 있는지 확인
                        if idx > 0:
                            prev_line = lines[idx - 1].strip()
                            if prev_line.startswith("#"):
                                commented_keys += 1

                comment_ratio = (commented_keys / total_keys * 100) if total_keys > 0 else 0

                results[config_file] = {
                    "exists": True,
                    "total_keys": total_keys,
                    "commented_keys": commented_keys,
                    "comment_ratio": comment_ratio,
                    "score": comment_ratio,
                }
            else:
                results[config_file] = {"exists": False, "score": 0}

        return results

    def generate_report(self) -> str:
        """문서화 커버리지 보고서 생성"""
        report = []
        report.append("=" * 80)
        report.append("문서화 커버리지 평가 보고서 (개선 후)")
        report.append("=" * 80)
        report.append("")

        # README 분석
        readme_result = self.analyze_readme()
        report.append("1. README.md")
        report.append(f"   존재 여부: {'✓' if readme_result['exists'] else '✗'}")
        if readme_result.get("exists"):
            report.append(f"   섹션 커버리지: {readme_result['section_score']:.1f}%")
            report.append(f"   내용 상세도: {readme_result['detail_score']:.1f}%")
            report.append(f"   종합 점수: {readme_result['overall_score']:.1f}%")
        report.append("")

        # API 모듈 분석
        api_results = self.analyze_api_modules()
        report.append("2. API 모듈 문서화")
        for module, result in api_results.items():
            report.append(f"   {module}:")
            report.append(f"     존재 여부: {'✓' if result.get('exists') else '✗'}")
            if result.get("exists") and result.get("parseable"):
                report.append(f"     Docstring 비율: {result['docstring_ratio']:.1f}%")
                report.append(f"     주석 비율: {result['comment_ratio']:.1f}%")
                report.append(f"     문서화 점수: {result['score']:.1f}%")
        report.append("")

        # 비즈니스 로직 분석
        business_results = self.analyze_business_logic()
        report.append("3. 비즈니스 로직 문서화")
        for module, result in business_results.items():
            report.append(f"   {module}:")
            report.append(f"     존재 여부: {'✓' if result.get('exists') else '✗'}")
            if result.get("exists") and result.get("parseable"):
                report.append(f"     Docstring 비율: {result['docstring_ratio']:.1f}%")
                report.append(f"     주석 비율: {result['comment_ratio']:.1f}%")
                report.append(f"     문서화 점수: {result['score']:.1f}%")
        report.append("")

        # 설정 파일 분석
        config_results = self.analyze_config_files()
        report.append("4. 설정 파일 문서화")
        for config_file, result in config_results.items():
            report.append(f"   {config_file}:")
            report.append(f"     존재 여부: {'✓' if result['exists'] else '✗'}")
            if result.get("exists"):
                report.append(
                    f"     주석 처리된 설정: {result['commented_keys']}/{result['total_keys']}"
                )
                report.append(f"     주석 비율: {result['comment_ratio']:.1f}%")
        report.append("")

        # 종합 평가
        report.append("=" * 80)
        report.append("종합 평가 및 권장 사항")
        report.append("=" * 80)

        # 전체 점수 계산
        all_scores = []
        if readme_result.get("exists"):
            all_scores.append(readme_result["overall_score"])

        for result in api_results.values():
            if result.get("exists") and result.get("parseable"):
                all_scores.append(result["score"])

        for result in business_results.values():
            if result.get("exists") and result.get("parseable"):
                all_scores.append(result["score"])

        for result in config_results.values():
            if result.get("exists"):
                all_scores.append(result["score"])

        if all_scores:
            overall_score = sum(all_scores) / len(all_scores)
            report.append(f"\n전체 문서화 커버리지: {overall_score:.1f}%")

            if overall_score < 50:
                report.append("\n⚠️  심각: 문서화 수준이 매우 부족합니다. 즉시 개선이 필요합니다.")
            elif overall_score < 70:
                report.append("\n⚠️  주의: 문서화가 부족한 부분이 많습니다. 개선이 필요합니다.")
            elif overall_score < 85:
                report.append("\n✓  양호: 문서화 수준이 적절합니다. 일부 개선이 권장됩니다.")
            else:
                report.append("\n✓  우수: 문서화 수준이 매우 좋습니다.")

        return "\n".join(report)


def test_documentation_coverage():
    """문서화 커버리지 테스트 실행"""
    analyzer = DocumentationCoverageAnalyzer()
    report = analyzer.generate_report()

    # 보고서 출력
    print(report)

    # 테스트 결과 저장
    with open("DOCUMENTATION_COVERAGE_REPORT_FINAL.md", "w", encoding="utf-8") as f:
        f.write(report)

    print("\n보고서가 DOCUMENTATION_COVERAGE_REPORT_FINAL.md 파일에 저장되었습니다.")

    # 전체 점수가 70점 미만이면 테스트 실패로 간주
    analyzer = DocumentationCoverageAnalyzer()
    all_scores = []

    readme_result = analyzer.analyze_readme()
    if readme_result.get("exists"):
        all_scores.append(readme_result["overall_score"])

    api_results = analyzer.analyze_api_modules()
    for result in api_results.values():
        if result.get("exists") and result.get("parseable"):
            all_scores.append(result["score"])

    business_results = analyzer.analyze_business_logic()
    for result in business_results.values():
        if result.get("exists") and result.get("parseable"):
            all_scores.append(result["score"])

    config_results = analyzer.analyze_config_files()
    for result in config_results.values():
        if result.get("exists"):
            all_scores.append(result["score"])

    if all_scores and (sum(all_scores) / len(all_scores)) < 70:
        print("\n❌ 문서화 커버리지 테스트 실패: 70% 미만")
        sys.exit(1)
    else:
        print("\n✅ 문서화 커버리지 테스트 통과!")
        sys.exit(0)


if __name__ == "__main__":
    test_documentation_coverage()
