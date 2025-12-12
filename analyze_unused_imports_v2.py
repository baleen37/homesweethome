#!/usr/bin/env python3
"""
Analyze Python files for truly unused imports.
This script identifies imports that are never referenced in the file OR exported.
"""

import ast
from pathlib import Path
from typing import Set, Dict, List, Tuple


class ImportAnalyzer(ast.NodeVisitor):
    """Visitor to collect all imports, used names, and exported names."""

    def __init__(self, filename: str):
        self.filename = filename
        self.imports: List[Tuple[str, str, str]] = []  # (module, name, alias)
        self.used_names: Set[str] = set()
        self.from_imports: Dict[str, List[Tuple[str, str]]] = {}  # module -> [(name, alias)]
        self.all_exports: Set[str] = set()
        self.has_all = False

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

    def visit_Assign(self, node: ast.Assign) -> None:
        """Track __all__ assignments."""
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                self.has_all = True
                if isinstance(node.value, (ast.List, ast.Tuple)):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            self.all_exports.add(elt.value)
                        elif isinstance(elt, ast.Str):  # Python < 3.8
                            self.all_exports.add(elt.s)
        self.generic_visit(node)


def analyze_file(file_path: Path) -> List[Tuple[str, str, str]]:
    """Analyze a Python file for truly unused imports."""
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

    analyzer = ImportAnalyzer(str(file_path))
    analyzer.visit(tree)

    unused_imports = []

    for module, name, alias in analyzer.imports:
        # Skip if the name is used directly
        if name in analyzer.used_names:
            continue

        # Skip if the name is exported via __all__
        if analyzer.has_all and name in analyzer.all_exports:
            continue

        # This is truly unused
        if alias:
            unused_imports.append(
                (
                    f"from {module.rsplit('.', 1)[0]} import {module.rsplit('.', 1)[1]} as {alias}",
                    name,
                    module,
                )
            )
        else:
            if "." in module:
                # For 'from x.y import z', check the actual module
                base_module = module.rsplit(".", 1)[0]
                import_name = module.rsplit(".", 1)[1]
                unused_imports.append((f"from {base_module} import {import_name}", name, module))
            else:
                unused_imports.append((f"import {module}", name, module))

    return unused_imports


def main():
    src_dir = Path("src")
    if not src_dir.exists():
        print(f"src directory not found at {src_dir}")
        return

    python_files = list(src_dir.rglob("*.py"))
    python_files.sort()

    total_unused = 0
    files_with_unused = []

    print("Analyzing Python files for TRULY unused imports...\n")
    print("(Ignoring imports that are exported via __all__)\n")
    print("=" * 80)

    for file_path in python_files:
        unused_imports = analyze_file(file_path)

        if unused_imports:
            files_with_unused.append((file_path, unused_imports))
            total_unused += len(unused_imports)

            # Show relative path
            rel_path = str(file_path)
            if rel_path.startswith("src/"):
                rel_path = rel_path[4:]

            print(f"\n📄 {rel_path}")
            for import_stmt, name, module in unused_imports:
                print(f"  ❌ {import_stmt}")

    # Summary
    print("\n" + "=" * 80)
    print("\n📊 SUMMARY")
    print(f"Total files analyzed: {len(python_files)}")
    print(f"Files with unused imports: {len(files_with_unused)}")
    print(f"Total unused imports: {total_unused}")

    # Detailed check for some files
    if files_with_unused:
        print("\n\n🔍 DETAILED ANALYSIS")
        print("-" * 80)

        for file_path, unused_imports in files_with_unused[:5]:  # Show first 5
            print(f"\n📄 {file_path}")
            print("  Context:")
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Show the import lines
            for i, line in enumerate(lines[:30], 1):  # First 30 lines
                if any(imp in line for _, _, imp in unused_imports):
                    print(f"  Line {i}: {line.rstrip()}")
                    # Show surrounding lines for context
                    for j in range(max(0, i - 2), min(len(lines), i + 2)):
                        if j != i - 1:
                            context_line = lines[j].rstrip()
                            if context_line:
                                print(f"  Line {j + 1}: {context_line}")
                    break

    # Write report
    with open("unused_imports_detailed_report.txt", "w", encoding="utf-8") as f:
        f.write("TRULY UNUSED IMPORTS REPORT\n")
        f.write("=" * 80 + "\n\n")

        for file_path, unused_imports in files_with_unused:
            f.write(f"{file_path}\n")
            f.write("-" * 40 + "\n")
            for import_stmt, name, module in unused_imports:
                f.write(f"  {import_stmt}\n")
                f.write(f"    -> Name '{name}' is never used and not exported\n")
            f.write("\n")

        f.write(f"\nTotal unused imports: {total_unused}\n")

    print("\n📝 Detailed report saved to: unused_imports_detailed_report.txt")


if __name__ == "__main__":
    main()
