"""패턴 기반 중복 코드 분석 테스트

실제로 중복이 의심되는 패턴들을 구체적으로 확인합니다.
"""

import ast
from pathlib import Path
from typing import Dict, Any


def analyze_api_clients():
    """API 클라이언트들의 패턴 분석"""
    print("\n=== API 클라이언트 패턴 분석 ===")

    # HogangnonoAPIClient와 MemoryEfficientAPIClient 비교
    hogangnono_path = Path("src/crawler/api/hogangnono_client.py")
    memory_path = Path("src/crawler/api/memory_efficient_client.py")

    patterns = {
        "HogangnonoAPIClient": extract_patterns(hogangnono_path),
        "MemoryEfficientAPIClient": extract_patterns(memory_path),
    }

    print("\n1. 공통 기능 비교:")
    common_methods = set(patterns["HogangnonoAPIClient"]["methods"].keys()) & set(
        patterns["MemoryEfficientAPIClient"]["methods"].keys()
    )

    for method in common_methods:
        print(f"\n- {method}:")
        print(f"  HogangnonoAPIClient: {patterns['HogangnonoAPIClient']['methods'][method]} 줄")
        print(
            f"  MemoryEfficientAPIClient: {patterns['MemoryEfficientAPIClient']['methods'][method]} 줄"
        )

    print("\n2. 유사한 기능 (다른 이름):")
    similar_functions = [
        ("_make_request", "fetch_streaming"),
        ("get_apartments_bounding", "fetch_batch_concurrent"),
        ("_initialize_session", "_init_session"),
    ]

    for func1, func2 in similar_functions:
        if (
            func1 in patterns["HogangnonoAPIClient"]["methods"]
            and func2 in patterns["MemoryEfficientAPIClient"]["methods"]
        ):
            print(f"\n- {func1} (HogangnonoAPIClient) <-> {func2} (MemoryEfficientAPIClient)")
            print("  두 함수 모두 HTTP 요청 처리 로직 포함")


def analyze_csv_writers():
    """CSV 작성자들의 패턴 분석"""
    print("\n\n=== CSV 작성자 패턴 분석 ===")

    writer_files = [
        "base_csv_writer.py",
        "hogangnono_csv_writer.py",
        "dataclass_csv_writer.py",
        "memory_optimized_csv_writer.py",
    ]

    all_patterns = {}
    for filename in writer_files:
        filepath = Path(f"src/crawler/writers/{filename}")
        class_name = filename.replace(".py", "").replace("_", " ").title().replace(" ", "")
        all_patterns[class_name] = extract_patterns(filepath)

    print("\n1. 공통 메서드 패턴:")
    method_counts = {}

    for class_name, patterns in all_patterns.items():
        for method in patterns["methods"]:
            if method not in method_counts:
                method_counts[method] = []
            method_counts[method].append(class_name)

    # 여러 클래스에서 사용되는 메서드
    for method, classes in method_counts.items():
        if len(classes) >= 2 and method.startswith("_"):
            print(f"\n- {method}: {', '.join(classes)}에서 사용")

    print("\n2. 초기화 패턴:")
    for class_name, patterns in all_patterns.items():
        if "__init__" in patterns["methods"]:
            print(f"\n- {class_name}.__init__: {patterns['methods']['__init__']} 줄")

    print("\n3. 데이터 처리 패턴:")
    data_methods = ["write", "append", "_normalize", "_validate"]
    for method in data_methods:
        print(f"\n{method} 메서드 구현:")
        for class_name, patterns in all_patterns.items():
            if method in patterns["methods"]:
                print(f"  - {class_name}.{method}: {patterns['methods'][method]} 줄")


def analyze_validators():
    """검증기들의 패턴 분석"""
    print("\n\n=== 검증기 패턴 분석 ===")

    validator_files = ["apartment_validator.py", "csv_validator.py", "data_validator.py"]

    validator_patterns = {}
    for filename in validator_files:
        filepath = Path(f"src/crawler/validators/{filename}")
        validator_patterns[filename] = extract_patterns(filepath)

    print("\n1. 검증 로직 패턴:")
    for filename, patterns in validator_patterns.items():
        print(f"\n- {filename}:")
        print(f"  총 메서드 수: {len(patterns['methods'])}")
        print(f"  주요 메서드: {', '.join(list(patterns['methods'].keys())[:5])}")

    print("\n2. is_/has_ 접두사 메서드:")
    for filename, patterns in validator_patterns.items():
        is_methods = [
            m for m in patterns["methods"] if m.startswith(("is_", "has_", "validate_", "check_"))
        ]
        if is_methods:
            print(f"\n- {filename}: {is_methods}")


def extract_patterns(filepath: Path) -> Dict[str, Any]:
    """파일에서 패턴 추출"""
    patterns = {"imports": [], "classes": {}, "methods": {}, "functions": {}}

    if not filepath.exists():
        return patterns

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            tree = ast.parse(content)

        # 클래스와 함수 정보 추출
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                end_line = node.end_lineno if hasattr(node, "end_lineno") else node.lineno
                patterns["classes"][node.name] = {
                    "line": node.lineno,
                    "lines": end_line - node.lineno,
                    "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                }

            elif isinstance(node, ast.FunctionDef):
                end_line = node.end_lineno if hasattr(node, "end_lineno") else node.lineno
                patterns["methods"][node.name] = end_line - node.lineno

        # 임포트 정보
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    patterns["imports"].append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    patterns["imports"].append(f"from {module} import {alias.name}")

    except Exception as e:
        print(f"Error processing {filepath}: {e}")

    return patterns


def find_code_smells():
    """코드 스멀(나쁜 냄새) 패턴 찾기"""
    print("\n\n=== 코드 스멀 분석 ===")

    # 긴 함수/메서드 찾기
    print("\n1. 긴 메서드 (50줄 이상):")
    base_dir = Path("src/crawler")

    for py_file in base_dir.rglob("*.py"):
        if "test_" in py_file.name:
            continue

        patterns = extract_patterns(py_file)

        for method_name, lines in patterns["methods"].items():
            if lines >= 50:
                print(f"\n- {py_file.name}.{method_name}: {lines} 줄")

    # 많은 메서드를 가진 클래스 찾기
    print("\n\n2. 큰 클래스 (15개 이상의 메서드):")

    for py_file in base_dir.rglob("*.py"):
        if "test_" in py_file.name:
            continue

        patterns = extract_patterns(py_file)

        for class_name, info in patterns["classes"].items():
            method_count = len(info["methods"])
            if method_count >= 15:
                print(f"\n- {py_file.name}.{class_name}: {method_count}개 메서드")


if __name__ == "__main__":
    print("패턴 기반 중복 코드 분석 시작...")

    analyze_api_clients()
    analyze_csv_writers()
    analyze_validators()
    find_code_smells()

    print("\n\n분석 완료!")
