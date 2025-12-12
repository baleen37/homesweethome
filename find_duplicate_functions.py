#!/usr/bin/env python3
"""
Find duplicate functions and classes in the codebase.
This helps identify opportunities for refactoring and reducing code duplication.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Tuple
import hashlib
from collections import defaultdict


class FunctionSignature(ast.NodeVisitor):
    """Extract function signatures and docstrings."""

    def __init__(self):
        self.functions = []
        self.classes = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Extract signature
        args = []
        for arg in node.args.args:
            args.append(arg.arg)

        # Extract docstring
        docstring = ast.get_docstring(node) or ""

        # Calculate hash of the function body (excluding docstring)
        body_nodes = []
        for n in node.body:
            if not (
                isinstance(n, ast.Expr)
                and isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, str)
            ):
                body_nodes.append(ast.dump(n))

        body_hash = hashlib.md5("".join(body_nodes).encode()).hexdigest()[:16]

        self.functions.append(
            {
                "name": node.name,
                "args": args,
                "docstring": docstring[:100],  # First 100 chars
                "body_hash": body_hash,
                "line": node.lineno,
                "type": "function",
            }
        )

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        # Handle async functions the same way
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        # Extract docstring
        docstring = ast.get_docstring(node) or ""

        # Count methods
        methods = []
        for n in node.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(n.name)

        # Calculate hash of class body
        body_nodes = []
        for n in node.body:
            body_nodes.append(ast.dump(n))

        body_hash = hashlib.md5("".join(body_nodes).encode()).hexdigest()[:16]

        self.classes.append(
            {
                "name": node.name,
                "docstring": docstring[:100],
                "methods": methods,
                "body_hash": body_hash,
                "line": node.lineno,
                "type": "class",
            }
        )

        self.generic_visit(node)


def analyze_file(file_path: Path) -> Tuple[List[Dict], List[Dict]]:
    """Analyze a Python file for functions and classes."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception:
        return [], []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return [], []

    extractor = FunctionSignature()
    extractor.visit(tree)

    return extractor.functions, extractor.classes


def find_duplicates() -> Dict[str, List[Dict]]:
    """Find duplicate functions and classes across the codebase."""
    base_dir = Path(".")
    directories = ["src", "tests", "scripts"]

    # Group by function signature
    function_groups = defaultdict(list)
    class_groups = defaultdict(list)

    print("Analyzing Python files for duplicate code...\n")

    for directory in directories:
        dir_path = base_dir / directory
        if not dir_path.exists():
            continue

        print(f"Scanning {directory}/")

        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if d not in ["__pycache__", ".venv", "venv"]]

            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    rel_path = str(file_path.relative_to(base_dir))

                    functions, classes = analyze_file(file_path)

                    # Group functions by signature
                    for func in functions:
                        # Create a signature key
                        sig_key = f"{func['name']}({', '.join(func['args'])})"
                        function_groups[sig_key].append({**func, "file": rel_path})

                    # Group classes by method count and names
                    for cls in classes:
                        cls_key = f"{cls['name']}({len(cls['methods'])})"
                        class_groups[cls_key].append({**cls, "file": rel_path})

    # Find potential duplicates
    duplicates = {}

    # Check for duplicate function signatures
    for sig, funcs in function_groups.items():
        if len(funcs) > 1:
            # Check if they have the same body
            body_groups = defaultdict(list)
            for func in funcs:
                body_groups[func["body_hash"]].append(func)

            for body_hash, same_body_funcs in body_groups.items():
                if len(same_body_funcs) > 1:
                    duplicates[f"function:{sig}"] = same_body_funcs

    # Check for duplicate class structures
    for sig, classes in class_groups.items():
        if len(classes) > 1:
            # Check if they have the same body structure
            body_groups = defaultdict(list)
            for cls in classes:
                body_groups[cls["body_hash"]].append(cls)

            for body_hash, same_body_classes in body_groups.items():
                if len(same_body_classes) > 1:
                    duplicates[f"class:{sig}"] = same_body_classes

    return duplicates


def find_similar_functions() -> List[Dict]:
    """Find functions with similar names or functionality."""
    base_dir = Path(".")
    directories = ["src", "tests"]

    all_functions = []

    for directory in directories:
        dir_path = base_dir / directory
        if not dir_path.exists():
            continue

        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if d not in ["__pycache__", ".venv", "venv"]]

            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    rel_path = str(file_path.relative_to(base_dir))

                    functions, _ = analyze_file(file_path)

                    for func in functions:
                        all_functions.append({**func, "file": rel_path})

    # Find functions with similar names
    similar = []
    name_groups = defaultdict(list)

    for func in all_functions:
        # Normalize function name
        normalized = func["name"].lower().replace("_", "")
        name_groups[normalized].append(func)

    for name, funcs in name_groups.items():
        if len(funcs) > 1:
            similar.append({"type": "similar_names", "pattern": name, "functions": funcs})

    return similar


def main():
    """Main function."""
    print("Finding duplicate and similar code...\n")

    # Find exact duplicates
    duplicates = find_duplicates()

    # Find similar functions
    similar = find_similar_functions()

    # Print results
    print("\n" + "=" * 80)
    print("DUPLICATE CODE REPORT")
    print("=" * 80)

    if duplicates:
        print(f"\nFound {len(duplicates)} groups of duplicate code:\n")

        for key, items in sorted(duplicates.items()):
            print(f"{key}:")
            for item in items:
                print(f"  - {item['file']}:{item['line']}")
                if item["docstring"]:
                    print(f"    Doc: {item['docstring'][:50]}...")
            print()
    else:
        print("\n✓ No exact duplicate code found!\n")

    print("=" * 80)
    print("SIMILAR CODE REPORT")
    print("=" * 80)

    if similar:
        print(f"\nFound {len(similar)} groups of similarly named functions:\n")

        for item in similar[:10]:  # Show first 10
            print(f"Similar pattern '{item['pattern']}':")
            for func in item["functions"][:3]:  # Show first 3
                print(
                    f"  - {func['file']}:{func['line']} -> {func['name']}({', '.join(func['args'])})"
                )
            if len(item["functions"]) > 3:
                print(f"  ... and {len(item['functions']) - 3} more")
            print()
    else:
        print("\n✓ No obviously similar functions found!\n")

    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print("\n1. For duplicate code:")
    print("   - Extract common functionality into shared utilities")
    print("   - Use inheritance or composition to eliminate duplication")
    print("   - Consider using decorators for common patterns\n")

    print("2. For similar functions:")
    print("   - Review if they can be consolidated into a single parameterized function")
    print("   - Check if they're serving different purposes and need renaming")
    print("   - Consider creating a class to group related functionality\n")


if __name__ == "__main__":
    main()
