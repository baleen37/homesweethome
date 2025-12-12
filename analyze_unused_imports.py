#!/usr/bin/env python3
"""
Analyze Python files for unused imports.
This script identifies imports that are never referenced in the file.
"""

import ast
from pathlib import Path
from typing import Set, Dict, List, Tuple


class ImportVisitor(ast.NodeVisitor):
    """Visitor to collect all imports and used names in a Python file."""

    def __init__(self):
        self.imports: List[Tuple[str, str, str]] = []  # (module, name, alias)
        self.used_names: Set[str] = set()
        self.from_imports: Dict[str, List[Tuple[str, str]]] = {}  # module -> [(name, alias)]

    def visit_Import(self, node: ast.Import) -> None:
        """Handle 'import x' statements."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name.split(".")[0]
            self.imports.append((alias.name, name, alias.asname or ""))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle 'from x import y' statements."""
        if node.module:
            module = node.module
            if module not in self.from_imports:
                self.from_imports[module] = []
            for alias in node.names:
                if alias.name == "*":
                    # Can't analyze star imports properly
                    continue
                name = alias.asname if alias.asname else alias.name
                self.from_imports[module].append((alias.name, name))
                self.imports.append((f"{module}.{alias.name}", name, alias.asname or ""))
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Track all name usages."""
        self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Track attribute access like module.function."""
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
        self.generic_visit(node)


def analyze_file(file_path: Path) -> List[Tuple[str, str]]:
    """Analyze a Python file for unused imports."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        return []

    visitor = ImportVisitor()
    visitor.visit(tree)

    unused_imports = []

    for module, name, alias in visitor.imports:
        if name not in visitor.used_names:
            if alias:
                unused_imports.append((f"import {module} as {alias}", f"{module} as {alias}"))
            else:
                if "." in module:
                    # For 'import x.y.z' only used as x, check if x is used
                    base_name = module.split(".")[0]
                    if base_name not in visitor.used_names:
                        unused_imports.append((f"import {module}", module))
                else:
                    unused_imports.append((f"import {module}", module))

    return unused_imports


def main():
    src_dir = Path("src")
    if not src_dir.exists():
        print(f"src directory not found at {src_dir}")
        return

    python_files = list(src_dir.rglob("*.py"))

    # Sort files for consistent output
    python_files.sort()

    total_unused = 0
    files_with_unused = []

    print("Analyzing Python files for unused imports...\n")
    print("=" * 80)

    # Special focus on writers package
    writers_files = [f for f in python_files if "writers" in str(f)]
    other_files = [f for f in python_files if "writers" not in str(f)]

    # Analyze writers files first
    if writers_files:
        print(f"\n📁 WRITERS PACKAGE ({len(writers_files)} files)")
        print("-" * 80)

        for file_path in writers_files:
            unused_imports = analyze_file(file_path)
            if unused_imports:
                files_with_unused.append((file_path, unused_imports))
                total_unused += len(unused_imports)

                rel_path = str(file_path)
                print(f"\n📄 {rel_path}")
                for import_stmt, module_name in unused_imports:
                    print(f"  ❌ {import_stmt}")

    # Analyze other files
    if other_files:
        print(f"\n\n📁 OTHER FILES ({len(other_files)} files)")
        print("-" * 80)

        # Group by directory
        other_files_by_dir = {}
        for f in other_files:
            parent = f.parent
            key = str(parent.relative_to(src_dir))
            if key not in other_files_by_dir:
                other_files_by_dir[key] = []
            other_files_by_dir[key].append(f)

        for dir_name, files in sorted(other_files_by_dir.items()):
            print(f"\n📂 {dir_name}/")
            for file_path in files:
                unused_imports = analyze_file(file_path)
                if unused_imports:
                    files_with_unused.append((file_path, unused_imports))
                    total_unused += len(unused_imports)

                    rel_path = str(file_path)
                    print(f"  📄 {file_path.name}")
                    for import_stmt, module_name in unused_imports:
                        print(f"    ❌ {import_stmt}")

    # Summary
    print("\n" + "=" * 80)
    print("\n📊 SUMMARY")
    print(f"Total files analyzed: {len(python_files)}")
    print(f"Files with unused imports: {len(files_with_unused)}")
    print(f"Total unused imports: {total_unused}")

    if total_unused > 0:
        print("\n🔧 To remove all unused imports, run:")
        print("python remove_unused_imports.py")

    # Also write detailed report to file
    with open("unused_imports_report.txt", "w", encoding="utf-8") as f:
        f.write("UNUSED IMPORTS REPORT\n")
        f.write("=" * 80 + "\n\n")

        for file_path, unused_imports in files_with_unused:
            f.write(f"{file_path}\n")
            f.write("-" * 40 + "\n")
            for import_stmt, _ in unused_imports:
                f.write(f"  {import_stmt}\n")
            f.write("\n")

        f.write(f"\nTotal unused imports: {total_unused}\n")

    print("\n📝 Detailed report saved to: unused_imports_report.txt")


if __name__ == "__main__":
    main()
