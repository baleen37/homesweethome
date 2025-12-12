#!/usr/bin/env python3
"""
Find unused imports in Python files (TDD version).
"""

import ast
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple, NamedTuple


class ImportInfo(NamedTuple):
    """Information about an import."""

    module: str
    name: str
    alias: str
    line_no: int
    is_star_import: bool


class UnusedImportFinder(ast.NodeVisitor):
    """AST visitor to find imports and their usage."""

    def __init__(self):
        self.imports: List[ImportInfo] = []
        self.used_names: Set[str] = set()
        self.import_from_modules: Dict[str, List[ImportInfo]] = defaultdict(list)

    def visit_Import(self, node: ast.Import) -> None:
        """Handle regular import statements."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports.append(
                ImportInfo(
                    module=alias.name,
                    name=name,
                    alias=alias.asname or "",
                    line_no=node.lineno,
                    is_star_import=False,
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle from...import statements."""
        if node.module is None:
            # Handle 'from . import ...'
            return

        for alias in node.names:
            if alias.name == "*":
                # Star import - track the module
                self.imports.append(
                    ImportInfo(
                        module=node.module,
                        name="*",
                        alias="",
                        line_no=node.lineno,
                        is_star_import=True,
                    )
                )
            else:
                name = alias.asname if alias.asname else alias.name
                import_info = ImportInfo(
                    module=node.module,
                    name=name,
                    alias=alias.asname or "",
                    line_no=node.lineno,
                    is_star_import=False,
                )
                self.imports.append(import_info)
                self.import_from_modules[node.module].append(import_info)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Track usage of names."""
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Track usage of attributes (e.g., module.function)."""
        if isinstance(node.value, ast.Name):
            # This handles cases like 'module.function'
            self.used_names.add(node.value.id)
        elif isinstance(node.value, ast.Attribute):
            # Handle nested attributes like 'package.module.function'
            # Find the base module name
            current = node.value
            while isinstance(current, ast.Attribute):
                current = current.value
            if isinstance(current, ast.Name):
                self.used_names.add(current.id)
        self.generic_visit(node)


def analyze_file(file_path: Path) -> Tuple[List[ImportInfo], Set[str]]:
    """Analyze a Python file for unused imports."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")
        return [], set()

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as e:
        print(f"Warning: Syntax error in {file_path}: {e}")
        return [], set()

    finder = UnusedImportFinder()
    finder.visit(tree)

    unused_imports = []

    # Check each import
    for import_info in finder.imports:
        if import_info.is_star_import:
            # Star imports are generally considered bad practice
            # We'll flag them for manual review
            unused_imports.append(import_info)
        else:
            # Check if the imported name is used
            if import_info.name not in finder.used_names:
                # Special case: if it's from import, check if the module itself is used
                module_used = False
                if import_info.module:
                    # Check if the module is used with attribute access
                    for used_name in finder.used_names:
                        if used_name == import_info.module:
                            module_used = True
                            break

                if not module_used:
                    unused_imports.append(import_info)

    return unused_imports, finder.import_from_modules.keys()


def find_python_files(directory: Path) -> List[Path]:
    """Find all Python files in a directory recursively."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip __pycache__, .venv, and other virtual environment directories
        dirs[:] = [
            d
            for d in dirs
            if d not in ["__pycache__", ".venv", "venv", "env", ".git", ".pytest_cache"]
        ]
        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)
    return python_files


def main():
    """Main function to find unused imports."""
    base_dir = Path(".")

    # Directories to check
    directories = ["src", "tests", "scripts", "."]

    all_unused = defaultdict(list)
    star_imports = defaultdict(list)

    print("Scanning for unused imports...\n")

    for directory in directories:
        dir_path = base_dir / directory
        if not dir_path.exists():
            continue

        print(f"Checking {directory}/")
        python_files = find_python_files(dir_path)

        for file_path in python_files:
            # Skip the script itself and test files
            if file_path.name in ["find_unused_imports_tdd.py", "test_unused_imports_detection.py"]:
                continue

            unused, from_modules = analyze_file(file_path)

            if unused:
                rel_path = str(file_path.relative_to(base_dir))
                for import_info in unused:
                    if import_info.is_star_import:
                        star_imports[rel_path].append(import_info)
                    else:
                        all_unused[rel_path].append(import_info)

    # Print results
    print("\n" + "=" * 80)
    print("UNUSED IMPORTS REPORT")
    print("=" * 80)

    if not all_unused and not star_imports:
        print("\n✓ No unused imports found!")
    else:
        # Regular unused imports
        if all_unused:
            print(f"\n{len(all_unused)} files with unused imports:")
            print("-" * 80)
            for file_path, imports in sorted(all_unused.items()):
                print(f"\n{file_path}:")
                for imp in sorted(imports, key=lambda x: x.line_no):
                    if imp.alias:
                        print(
                            f"  Line {imp.line_no}: import {imp.module} as {imp.alias}  # '{imp.alias}' is never used"
                        )
                    else:
                        print(
                            f"  Line {imp.line_no}: import {imp.module}  # '{imp.name}' is never used"
                        )

        # Star imports
        if star_imports:
            print(f"\n{len(star_imports)} files with star imports (should be reviewed):")
            print("-" * 80)
            for file_path, imports in sorted(star_imports.items()):
                print(f"\n{file_path}:")
                for imp in sorted(imports, key=lambda x: x.line_no):
                    print(
                        f"  Line {imp.line_no}: from {imp.module} import *  # Star import - review manually"
                    )

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Files with unused imports: {len(all_unused)}")
    print(f"Files with star imports: {len(star_imports)}")
    total_unused = sum(len(imports) for imports in all_unused.values())
    total_star = sum(len(imports) for imports in star_imports.values())
    print(f"Total unused import statements: {total_unused}")
    print(f"Total star import statements: {total_star}")


if __name__ == "__main__":
    main()
