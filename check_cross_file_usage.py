#!/usr/bin/env python3
"""
Check for imports that might not be used elsewhere in the codebase.
"""

import ast
from pathlib import Path
from typing import Dict, Set, List, Tuple


def get_imported_names(file_path: Path) -> Set[str]:
    """Get all names that a file imports from other modules."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return set()

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return set()

    imported_names = set()

    # Track what this file exports via __all__
    exported_names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                exported_names.add(elt.value)
                            elif isinstance(elt, ast.Str):
                                exported_names.add(elt.s)

    # Get all imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name.split(".")[0]
                imported_names.add(name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in node.names:
                    if alias.name != "*":
                        name = alias.asname if alias.asname else alias.name
                        imported_names.add(name)

    # Return imports that are NOT exported (since those are public API)
    return imported_names - exported_names


def get_defined_names(file_path: Path) -> Set[str]:
    """Get all names (functions, classes, variables) defined in a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return set()

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return set()

    defined_names = set()

    for node in ast.walk(tree):
        # Classes and functions
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            defined_names.add(node.name)
        # Variable assignments at module level
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defined_names.add(target.id)

    return defined_names


def analyze_cross_file_usage():
    """Analyze which imported modules are actually used across the codebase."""
    src_dir = Path("src")
    python_files = list(src_dir.rglob("*.py"))

    # Build a map of what each file defines
    file_definitions: Dict[str, Set[str]] = {}
    for file_path in python_files:
        file_definitions[str(file_path)] = get_defined_names(file_path)

    # Check each file's imports
    suspicious_imports: List[Tuple[str, str, List[str]]] = []

    for file_path in python_files:
        imported_names = get_imported_names(file_path)
        if not imported_names:
            continue

        # Check if these imports are used in the file
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        unused_in_file = set()

        for name in imported_names:
            # Simple check: does the name appear in the code?
            if name not in content:
                unused_in_file.add(name)

        if unused_in_file:
            suspicious_imports.append((str(file_path), list(unused_in_file), imported_names))

    # Report
    print("Checking for suspicious imports (imported but never used in file)...\n")
    print("=" * 80)

    total_suspicious = 0
    for file_path, unused_list, all_imports in suspicious_imports:
        rel_path = str(file_path)
        if rel_path.startswith("src/"):
            rel_path = rel_path[4:]

        print(f"\n📄 {rel_path}")
        print(f"  Total imports: {len(all_imports)}")
        print(f"  Potentially unused: {len(unused_list)}")

        # Show specific unused imports
        for name in sorted(unused_list):
            # Find the import statement
            with open(file_path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    if f"import {name}" in line or "from " in line and f" {name}" in line:
                        print(f"    Line {i}: {line.rstrip()}")
                        break

        total_suspicious += len(unused_list)

    print("\n" + "=" * 80)
    print("\n📊 SUMMARY")
    print(f"Files with suspicious imports: {len(suspicious_imports)}")
    print(f"Total suspicious imports: {total_suspicious}")


def check_duplicate_imports():
    """Check for duplicate imports in files."""
    src_dir = Path("src")
    python_files = list(src_dir.rglob("*.py"))

    print("\n\nChecking for duplicate imports...\n")
    print("=" * 80)

    files_with_duplicates = 0

    for file_path in python_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            continue

        # Track imports
        imports: Dict[str, List[int]] = {}

        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line.startswith(("import ", "from ")):
                # Normalize the import (remove aliases for comparison)
                normalized = line
                if " as " in normalized:
                    normalized = normalized.split(" as ")[0]

                if normalized not in imports:
                    imports[normalized] = []
                imports[normalized].append(i)

        # Check for duplicates
        duplicates = {imp: lines for imp, lines in imports.items() if len(lines) > 1}

        if duplicates:
            files_with_duplicates += 1
            rel_path = str(file_path)
            if rel_path.startswith("src/"):
                rel_path = rel_path[4:]

            print(f"\n📄 {rel_path}")
            for imp, line_numbers in duplicates.items():
                print("  Duplicate import found:")
                print(f"    {imp}")
                print(f"    Lines: {', '.join(map(str, line_numbers))}")

    print(f"\n📊 Files with duplicate imports: {files_with_duplicates}")


if __name__ == "__main__":
    analyze_cross_file_usage()
    check_duplicate_imports()
