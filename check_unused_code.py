#!/usr/bin/env python3
"""
Check for potentially unused functions and classes in the codebase.
"""

import ast
from pathlib import Path
from typing import Dict, Set, List, Tuple
from collections import defaultdict


class CodeUsageAnalyzer(ast.NodeVisitor):
    """Analyzer to track function/class definitions and their usage."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.definitions: Dict[str, Tuple[int, str]] = {}  # name -> (line, type)
        self.usages: Set[str] = set()
        self.exports: Set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.definitions[node.name] = (node.lineno, "function")
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.definitions[node.name] = (node.lineno, "async_function")
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.definitions[node.name] = (node.lineno, "class")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Load, ast.Del)):
            self.usages.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Track method calls like obj.method()
        if isinstance(node.value, ast.Name):
            # We can't determine if it's the same object, so track all
            pass
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        # Track __all__ exports
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                if isinstance(node.value, (ast.List, ast.Tuple)):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            self.exports.add(elt.value)
                        elif isinstance(elt, ast.Str):  # Python < 3.8
                            self.exports.add(elt.s)
        self.generic_visit(node)


def analyze_potentially_unused_code():
    """Analyze the codebase for potentially unused functions and classes."""
    src_dir = Path("src")
    python_files = list(src_dir.rglob("*.py"))

    # Skip __init__.py files as they mainly re-export
    python_files = [f for f in python_files if f.name != "__init__.py"]

    # Collect all definitions
    all_definitions: Dict[str, List[Tuple[str, int, str]]] = defaultdict(
        list
    )  # name -> [(filepath, line, type)]

    # Collect all usages
    all_usages: Set[str] = set()

    # First pass: collect all definitions
    for file_path in python_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue

        analyzer = CodeUsageAnalyzer(str(file_path))
        analyzer.visit(tree)

        for name, (line, typ) in analyzer.definitions.items():
            # Skip special methods
            if name.startswith("__") and name.endswith("__"):
                continue
            # Skip private methods (not unused, just internal)
            if name.startswith("_"):
                continue

            all_definitions[name].append((str(file_path), line, typ))

        # Also track exports
        all_usages.update(analyzer.exports)

    # Second pass: collect all usages
    for file_path in python_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue

        analyzer = CodeUsageAnalyzer(str(file_path))
        analyzer.visit(tree)
        all_usages.update(analyzer.usages)

    # Find potentially unused code
    potentially_unused = []

    for name, definitions in all_definitions.items():
        if name not in all_usages and len(definitions) == 1:
            # Only report if defined once (not overridden in different files)
            filepath, line, typ = definitions[0]
            potentially_unused.append((name, filepath, line, typ))

    # Sort by file
    potentially_unused.sort(key=lambda x: x[1])

    # Report
    print("Checking for potentially unused functions and classes...\n")
    print("(Excluding: special methods, private methods, and exported items)\n")
    print("=" * 80)

    # Group by file
    by_file: Dict[str, List[Tuple[str, int, str]]] = defaultdict(list)
    for name, filepath, line, typ in potentially_unused:
        rel_path = filepath
        if rel_path.startswith("src/"):
            rel_path = rel_path[4:]
        by_file[rel_path].append((name, line, typ))

    for filepath, items in sorted(by_file.items()):
        print(f"\n📄 {filepath}")
        for name, line, typ in sorted(items, key=lambda x: x[1]):
            print(f"  Line {line}: {typ.replace('_', ' ').title()} '{name}'")

    print("\n" + "=" * 80)
    print("\n📊 SUMMARY")
    print(f"Total potentially unused items: {len(potentially_unused)}")
    print(f"Files with unused items: {len(by_file)}")

    # Check for empty files or nearly empty files
    print("\n\nChecking for nearly empty files...")
    print("-" * 80)

    empty_files = []
    for file_path in python_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = [
                    line
                    for line in content.split("\n")
                    if line.strip() and not line.strip().startswith("#")
                ]

                # Count actual code lines (excluding imports and docstrings)
                code_lines = []
                in_docstring = False

                for line in lines:
                    if '"""' in line or "'''" in line:
                        in_docstring = not in_docstring
                        continue

                    if not in_docstring and not line.strip().startswith(
                        ("import ", "from ", "__all__")
                    ):
                        code_lines.append(line)

                if len(code_lines) <= 5:  # Very little actual code
                    rel_path = str(file_path)
                    if rel_path.startswith("src/"):
                        rel_path = rel_path[4:]
                    empty_files.append((rel_path, len(code_lines)))
        except Exception:
            continue

    if empty_files:
        print("\nFiles with very little code (≤5 lines):")
        for filepath, count in sorted(empty_files):
            print(f"  📄 {filepath} ({count} lines of code)")


if __name__ == "__main__":
    analyze_potentially_unused_code()
