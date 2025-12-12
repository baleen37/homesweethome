#!/usr/bin/env python3
"""
라이브러리 사용 패턴 분석 도구
"""

import ast
import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict

# 표준 라이브러리 목록
STANDARD_LIBRARY = {
    "abc",
    "aifc",
    "argparse",
    "array",
    "ast",
    "asynchat",
    "asyncio",
    "asyncore",
    "atexit",
    "audioop",
    "base64",
    "bdb",
    "binascii",
    "binhex",
    "bisect",
    "builtins",
    "bz2",
    "cProfile",
    "calendar",
    "cgi",
    "cgitb",
    "chunk",
    "cmath",
    "cmd",
    "code",
    "codecs",
    "codeop",
    "collections",
    "colorsys",
    "compileall",
    "concurrent",
    "configparser",
    "contextlib",
    "contextvars",
    "copy",
    "copyreg",
    "csv",
    "ctypes",
    "curses",
    "dataclasses",
    "datetime",
    "decimal",
    "difflib",
    "dis",
    "doctest",
    "email",
    "encodings",
    "ensurepip",
    "enum",
    "errno",
    "faulthandler",
    "fcntl",
    "filecmp",
    "fileinput",
    "fnmatch",
    "fractions",
    "ftplib",
    "functools",
    "gc",
    "getopt",
    "getpass",
    "gettext",
    "glob",
    "grp",
    "gzip",
    "hashlib",
    "heapq",
    "hmac",
    "html",
    "http",
    "imaplib",
    "imghdr",
    "imp",
    "importlib",
    "inspect",
    "io",
    "ipaddress",
    "itertools",
    "json",
    "keyword",
    "linecache",
    "locale",
    "logging",
    "lzma",
    "mailbox",
    "mailcap",
    "marshal",
    "math",
    "mimetypes",
    "mmap",
    "modulefinder",
    "multiprocessing",
    "netrc",
    "nntplib",
    "numbers",
    "operator",
    "os",
    "ossaudiodev",
    "pathlib",
    "pdb",
    "pickle",
    "pickletools",
    "pipes",
    "pkgutil",
    "platform",
    "plistlib",
    "poplib",
    "posix",
    "pprint",
    "profile",
    "pstats",
    "pty",
    "pwd",
    "py_compile",
    "pyclbr",
    "pydoc",
    "pydoc_data",
    "pyexpat",
    "queue",
    "quopri",
    "random",
    "re",
    "readline",
    "reprlib",
    "resource",
    "rlcompleter",
    "runpy",
    "sched",
    "secrets",
    "select",
    "selectors",
    "shelve",
    "shlex",
    "shutil",
    "signal",
    "site",
    "smtpd",
    "smtplib",
    "sndhdr",
    "socket",
    "socketserver",
    "sqlite3",
    "sre",
    "sre_compile",
    "sre_constants",
    "sre_parse",
    "ssl",
    "stat",
    "statistics",
    "string",
    "stringprep",
    "struct",
    "subprocess",
    "sunau",
    "symbol",
    "symtable",
    "sys",
    "sysconfig",
    "syslog",
    "tabnanny",
    "tarfile",
    "telnetlib",
    "tempfile",
    "termios",
    "textwrap",
    "threading",
    "time",
    "timeit",
    "tkinter",
    "token",
    "tokenize",
    "trace",
    "traceback",
    "tracemalloc",
    "tty",
    "turtle",
    "types",
    "typing",
    "unicodedata",
    "unittest",
    "urllib",
    "uu",
    "uuid",
    "venv",
    "warnings",
    "wave",
    "weakref",
    "webbrowser",
    "winreg",
    "winsound",
    "wsgiref",
    "xdrlib",
    "xml",
    "xmlrpc",
    "zipapp",
    "zipfile",
    "zipimport",
    "zlib",
    "zoneinfo",
    "pathlib",
    "dataclasses",
    "typing_extensions",
    "contextvars",
    "importlib.metadata",
    "importlib.resources",
    "importlib.abc",
    "asyncio",
    "concurrent.futures",
    "multiprocessing",
    "threading",
    "queue",
    "selectors",
    "socket",
    "ssl",
    "urllib",
    "http",
    "email",
    "json",
    "csv",
    "xml",
    "xmlrpc",
    "sqlite3",
    "hashlib",
    "hmac",
    "secrets",
    "base64",
    "binascii",
    "quopri",
    "uu",
    "struct",
    "codecs",
    "string",
    "re",
    "difflib",
    "textwrap",
    "unicodedata",
    "stringprep",
    "readline",
    "rlcompleter",
    "cmd",
    "shlex",
    "pydoc",
    "doctest",
    "unittest",
    "argparse",
    "getopt",
    "logging",
    "warnings",
    "pdb",
    "profile",
    "cProfile",
    "pstats",
    "timeit",
    "trace",
    "tracemalloc",
    "faulthandler",
    "gc",
    "inspect",
    "site",
    "pkgutil",
    "importlib",
    "sysconfig",
    "platform",
    "errno",
    "ctypes",
    "mmap",
    "select",
    "selectors",
    "signal",
    "time",
    "threading",
    "concurrent",
    "multiprocessing",
    "subprocess",
    "sched",
    "queue",
    "contextvars",
    "asyncio",
    "socket",
    "ssl",
    "email",
    "smtplib",
    "poplib",
    "imaplib",
    "urllib",
    "http",
    "xmlrpc",
    "ipaddress",
    "uuid",
    "hashlib",
    "hmac",
    "secrets",
    "base64",
    "binascii",
    "quopri",
    "uu",
    "struct",
    "codecs",
    "string",
    "re",
    "difflib",
    "textwrap",
    "unicodedata",
    "stringprep",
    "readline",
    "rlcompleter",
    "cmd",
    "shlex",
    "pydoc",
    "doctest",
    "unittest",
    "argparse",
    "getopt",
    "logging",
    "warnings",
    "pdb",
    "profile",
    "cProfile",
    "pstats",
    "timeit",
    "trace",
    "tracemalloc",
    "faulthandler",
    "gc",
    "inspect",
    "site",
    "pkgutil",
    "importlib",
    "importlib.metadata",
    "importlib.resources",
    "zipimport",
    "sysconfig",
    "platform",
    "errno",
    "ctypes",
    "mmap",
    "select",
    "selectors",
    "signal",
    "time",
    "threading",
    "concurrent",
    "multiprocessing",
    "subprocess",
    "sched",
    "queue",
    "contextvars",
    "asyncio",
    "socket",
    "ssl",
    "email",
    "smtplib",
    "poplib",
    "imaplib",
    "urllib",
    "http",
    "xmlrpc",
    "ipaddress",
    "uuid",
    "hashlib",
    "hmac",
    "secrets",
    "base64",
    "binascii",
    "quopri",
    "uu",
    "struct",
    "codecs",
    "string",
    "re",
    "difflib",
    "textwrap",
    "unicodedata",
    "stringprep",
    "readline",
    "rlcompleter",
    "cmd",
    "shlex",
    "pydoc",
    "doctest",
    "unittest",
    "argparse",
    "getopt",
    "logging",
    "warnings",
    "pdb",
    "profile",
    "cProfile",
    "pstats",
    "timeit",
    "trace",
    "tracemalloc",
    "faulthandler",
    "gc",
    "inspect",
    "site",
    "pkgutil",
    "importlib",
    "importlib.metadata",
    "importlib.resources",
    "zipimport",
    "sysconfig",
    "platform",
    "errno",
    "ctypes",
    "mmap",
    "select",
    "selectors",
    "signal",
    "time",
    "threading",
    "concurrent",
    "multiprocessing",
    "subprocess",
    "sched",
    "queue",
    "contextvars",
    "asyncio",
    "socket",
    "ssl",
    "email",
    "smtplib",
    "poplib",
    "imaplib",
    "urllib",
    "http",
    "xmlrpc",
    "ipaddress",
    "uuid",
    "hashlib",
    "hmac",
    "secrets",
    "base64",
    "binascii",
    "quopri",
    "uu",
    "struct",
    "codecs",
    "string",
    "re",
    "difflib",
    "textwrap",
    "unicodedata",
    "stringprep",
    "readline",
    "rlcompleter",
    "cmd",
    "shlex",
    "pydoc",
    "doctest",
    "unittest",
    "argparse",
    "getopt",
    "logging",
    "warnings",
    "pdb",
    "profile",
    "cProfile",
    "pstats",
    "timeit",
    "trace",
    "tracemalloc",
    "faulthandler",
    "gc",
    "inspect",
    "site",
    "pkgutil",
    "importlib",
    "importlib.metadata",
    "importlib.resources",
    "zipimport",
    "sysconfig",
    "platform",
    "errno",
    "ctypes",
    "mmap",
    "select",
    "selectors",
    "signal",
    "time",
    "threading",
    "concurrent",
    "multiprocessing",
    "subprocess",
    "sched",
    "queue",
    "contextvars",
    "asyncio",
    "socket",
    "ssl",
    "email",
    "smtplib",
    "poplib",
    "imaplib",
    "urllib",
    "http",
    "xmlrpc",
    "ipaddress",
    "uuid",
    "hashlib",
    "hmac",
    "secrets",
    "base64",
    "binascii",
    "quopri",
    "uu",
    "struct",
    "codecs",
    "string",
    "re",
    "difflib",
    "textwrap",
    "unicodedata",
    "stringprep",
}


class LibraryPatternVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports = []
        self.from_imports = []
        self.function_calls = []
        self.class_usage = []

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            for alias in node.names:
                self.from_imports.append(f"{node.module}.{alias.name}")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.function_calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            # 모듈.함�数() 형태의 호출
            if isinstance(node.func.value, ast.Name):
                self.function_calls.append(f"{node.func.value.id}.{node.func.attr}")
        self.generic_visit(node)


def analyze_file(file_path: Path) -> Dict:
    """단일 파일의 라이브러리 사용 패턴 분석"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        visitor = LibraryPatternVisitor()
        visitor.visit(tree)

        # 라이브러리 분류
        std_lib_imports = []
        third_party_imports = []
        internal_imports = []

        for imp in visitor.imports:
            module_root = imp.split(".")[0]
            if module_root in STANDARD_LIBRARY:
                std_lib_imports.append(imp)
            elif imp.startswith(".") or imp.startswith("crawler") or imp.startswith("src"):
                internal_imports.append(imp)
            else:
                third_party_imports.append(imp)

        for imp in visitor.from_imports:
            module_root = imp.split(".")[0]
            if module_root in STANDARD_LIBRARY:
                std_lib_imports.append(imp)
            elif imp.startswith(".") or imp.startswith("crawler") or imp.startswith("src"):
                internal_imports.append(imp)
            else:
                third_party_imports.append(imp)

        return {
            "file_path": str(file_path),
            "imports": visitor.imports,
            "from_imports": visitor.from_imports,
            "function_calls": visitor.function_calls,
            "std_lib_imports": std_lib_imports,
            "third_party_imports": third_party_imports,
            "internal_imports": internal_imports,
        }

    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return None


def main():
    base_dir = Path(".")
    all_files = []

    # 모든 Python 파일 수집
    for file_path in base_dir.rglob("*.py"):
        if any(
            part in str(file_path)
            for part in [
                ".venv",
                "venv",
                "__pycache__",
                ".pytest_cache",
                ".mypy_cache",
                "build",
                "dist",
            ]
        ):
            continue
        all_files.append(file_path)

    print(f"총 {len(all_files)}개의 파일 분석 중...\n")

    # 전체 통계
    total_stats = {
        "std_lib_count": Counter(),
        "third_party_count": Counter(),
        "internal_count": Counter(),
        "std_lib_files": set(),
        "third_party_files": set(),
        "internal_files": set(),
    }

    # 파일별 상세 분석
    file_analyses = []
    pattern_by_directory = defaultdict(
        lambda: {"std_lib": Counter(), "third_party": Counter(), "internal": Counter()}
    )

    for file_path in all_files:
        analysis = analyze_file(file_path)
        if analysis:
            file_analyses.append(analysis)

            # 디렉터리별 패턴 수집
            relative_path = file_path.relative_to(base_dir)
            directory = str(relative_path.parent)

            # 표준 라이브러리
            for imp in analysis["std_lib_imports"]:
                module_root = imp.split(".")[0]
                total_stats["std_lib_count"][module_root] += 1
                total_stats["std_lib_files"].add(str(relative_path))
                pattern_by_directory[directory]["std_lib"][module_root] += 1

            # 외부 라이브러리
            for imp in analysis["third_party_imports"]:
                module_root = imp.split(".")[0]
                total_stats["third_party_count"][module_root] += 1
                total_stats["third_party_files"].add(str(relative_path))
                pattern_by_directory[directory]["third_party"][module_root] += 1

            # 내부 모듈
            for imp in analysis["internal_imports"]:
                # 상대 경로나 내부 모듈명 정리
                clean_imp = imp.lstrip(".").split(".")[0]
                if clean_imp:
                    total_stats["internal_count"][clean_imp] += 1
                    total_stats["internal_files"].add(str(relative_path))
                    pattern_by_directory[directory]["internal"][clean_imp] += 1

    # 결과 출력
    print("=" * 80)
    print("라이브러리 사용 패턴 분석")
    print("=" * 80)

    # 1. 전체 사용 통계
    print("\n1. 라이브러리 유형별 사용 현황:")
    print(
        f"   표준 라이브러리: {len(total_stats['std_lib_count'])}개 모듈, {sum(total_stats['std_lib_count'].values())}회 사용"
    )
    print(
        f"   외부 라이브러리: {len(total_stats['third_party_count'])}개 모듈, {sum(total_stats['third_party_count'].values())}회 사용"
    )
    print(
        f"   내부 모듈: {len(total_stats['internal_count'])}개 모듈, {sum(total_stats['internal_count'].values())}회 사용"
    )

    # 2. 가장 많이 사용된 표준 라이브러리
    print("\n2. 가장 많이 사용된 표준 라이브러리 (상위 20개):")
    for lib, count in total_stats["std_lib_count"].most_common(20):
        print(f"   {lib}: {count}회")

    # 3. 가장 많이 사용된 외부 라이브러리
    print("\n3. 가장 많이 사용된 외부 라이브러리:")
    for lib, count in total_stats["third_party_count"].most_common():
        print(f"   {lib}: {count}회")

    # 4. 가장 많이 사용된 내부 모듈
    print("\n4. 가장 많이 사용된 내부 모듈 (상위 20개):")
    for lib, count in total_stats["internal_count"].most_common(20):
        print(f"   {lib}: {count}회")

    # 5. 디렉터리별 패턴
    print("\n5. 디렉터리별 라이브러리 사용 패턴:")
    for directory, patterns in sorted(pattern_by_directory.items()):
        if any(counts for counts in patterns.values()):
            print(f"\n   {directory}/")

            if patterns["std_lib"]:
                print(
                    f"     표준 라이브러리: {', '.join([f'{lib}({count})' for lib, count in patterns['std_lib'].most_common(5)])}"
                )

            if patterns["third_party"]:
                print(
                    f"     외부 라이브러리: {', '.join([f'{lib}({count})' for lib, count in patterns['third_party'].most_common()])}"
                )

            if patterns["internal"]:
                print(
                    f"     내부 모듈: {', '.join([f'{lib}({count})' for lib, count in patterns['internal'].most_common(5)])}"
                )

    # 6. 잠재적 개선 사항
    print("\n\n6. 개선 제안:")
    print("-" * 40)

    # 과도한 의존성을 가진 파일
    file_dependency_count = []
    for analysis in file_analyses:
        total_deps = len(analysis["std_lib_imports"]) + len(analysis["third_party_imports"])
        file_dependency_count.append((analysis["file_path"], total_deps))

    file_dependency_count.sort(key=lambda x: x[1], reverse=True)

    print("\n   가장 많은 의존성을 가진 파일:")
    for file_path, count in file_dependency_count[:10]:
        print(f"     - {file_path}: {count}개")

    # 사용되지 않는 pyproject.toml 의존성
    used_third_party = set(total_stats["third_party_count"].keys())
    pyproject_deps = {
        "requests",
        "beautifulsoup4",
        "lxml",
        "playwright",
        "python-dotenv",
        "structlog",
        "pydantic",
        "nest-asyncio",
        "pandas",
        "psutil",
        "dependency-injector",
        "pytest-cov",
        "numpy",
    }

    unused_deps = pyproject_deps - used_third_party
    if unused_deps:
        print("\n   pyproject.toml에 있지만 사용되지 않는 의존성:")
        for dep in sorted(unused_deps):
            print(f"     - {dep}")

    missing_deps = used_third_party - pyproject_deps
    if missing_deps:
        print("\n   사용되지만 pyproject.toml에 없는 의존성:")
        for dep in sorted(missing_deps):
            print(f"     - {dep}")

    # 표준 라이브러리 대체 가능성
    alternatives = {
        "pandas": "csv 모듈 (간단한 CSV 처리 시)",
        "numpy": "statistics 모듈 (기본 통계 계산 시)",
        "requests": "urllib (간단한 HTTP 요청 시)",
        "pydantic": "dataclasses (간단한 데이터 검증 시)",
    }

    print("\n   표준 라이브러리 대체 검토:")
    for third_party, alternative in alternatives.items():
        if third_party in used_third_party:
            print(f"     - {third_party}: {alternative}")

    # 분석 결과 저장
    result = {
        "summary": {
            "total_files": len(all_files),
            "std_lib_modules": len(total_stats["std_lib_count"]),
            "third_party_modules": len(total_stats["third_party_count"]),
            "internal_modules": len(total_stats["internal_count"]),
        },
        "std_lib_usage": dict(total_stats["std_lib_count"]),
        "third_party_usage": dict(total_stats["third_party_count"]),
        "internal_usage": dict(total_stats["internal_count"]),
        "patterns_by_directory": {
            dir: {k: dict(v) for k, v in patterns.items()}
            for dir, patterns in pattern_by_directory.items()
        },
    }

    with open("library_patterns_analysis.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("\n\n분석 결과가 'library_patterns_analysis.json'에 저장되었습니다.")


if __name__ == "__main__":
    main()
