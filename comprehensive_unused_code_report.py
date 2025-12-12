#!/usr/bin/env python3
"""Generate a comprehensive report of unused code in the Python codebase."""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class UnusedItem:
    """Represents an unused code item."""

    file_path: str
    line_number: int
    item_type: str  # 'function', 'class', 'method'
    name: str
    reason: str = ""


class CodeAnalyzer(ast.NodeVisitor):
    """AST visitor to collect defined and used items."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.defined_functions: Set[Tuple[str, int]] = set()
        self.defined_classes: Dict[str, List[Tuple[str, int]]] = {}
        self.used_names: Set[str] = set()
        self.imported_names: Dict[str, str] = {}
        self.from_imports: Dict[str, Set[str]] = defaultdict(set)
        self.current_class: Optional[str] = None
        self.function_calls: Set[Tuple[str, str]] = set()

    def visit_Module(self, node):
        """Visit module top-level."""
        self.generic_visit(node)

    def visit_Import(self, node):
        """Visit import statements."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imported_names[name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Visit from...import statements."""
        module = node.module or ""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.from_imports[module].add(name)
            if alias.name != "*":
                self.imported_names[name] = alias.name
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        """Visit function definitions."""
        # Skip test functions
        if node.name.startswith("test_"):
            self.generic_visit(node)
            return

        self.defined_functions.add((node.name, node.lineno))

        # Check if it's a method in a class
        if self.current_class:
            if self.current_class not in self.defined_classes:
                self.defined_classes[self.current_class] = []
            self.defined_classes[self.current_class].append((node.name, node.lineno))

        # Skip visiting function body for unused functions
        # But we need to check for nested functions/classes
        old_class = self.current_class
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                self.visit(child)
        self.current_class = old_class

    def visit_AsyncFunctionDef(self, node):
        """Visit async function definitions."""
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node):
        """Visit class definitions."""
        old_class = self.current_class
        self.current_class = node.name
        if node.name not in self.defined_classes:
            self.defined_classes[node.name] = []
        self.defined_classes[node.name].append(("__class__", node.lineno))

        # Visit methods but not other content
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.visit(child)
        self.current_class = old_class

    def visit_Name(self, node):
        """Visit name references."""
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        """Visit attribute access."""
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
            if isinstance(node.ctx, ast.Load):
                if hasattr(node, "attr"):
                    self.function_calls.add((node.value.id, node.attr))
        self.generic_visit(node)

    def visit_Call(self, node):
        """Visit function calls."""
        if isinstance(node.func, ast.Name):
            self.used_names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                self.function_calls.add((node.func.value.id, node.func.attr))
        self.generic_visit(node)


def analyze_file(file_path: Path) -> Tuple[Optional[CodeAnalyzer], List[str]]:
    """Analyze a single Python file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        analyzer = CodeAnalyzer(str(file_path))
        tree = ast.parse(content)
        analyzer.visit(tree)

        return analyzer, []
    except SyntaxError as e:
        return None, [f"Syntax error in {file_path}: {e}"]
    except Exception as e:
        return None, [f"Error analyzing {file_path}: {e}"]


def find_unused_items(src_dir: Path, root_dir: Path) -> List[UnusedItem]:
    """Find all unused functions, classes, and methods."""
    # Find all Python files
    src_files = list(src_dir.rglob("*.py"))
    root_files = list(root_dir.glob("*.py"))
    all_files = src_files + root_files

    # Analyze all files
    analyzers = {}
    errors = []

    for file_path in all_files:
        analyzer, file_errors = analyze_file(file_path)
        if analyzer:
            analyzers[str(file_path)] = analyzer
        errors.extend(file_errors)

    # Collect all defined and used items
    all_defined_functions = set()
    all_defined_classes = {}
    all_used_names = set()
    all_method_calls = set()

    # Get items from src directory only for definitions
    for file_path, analyzer in analyzers.items():
        if "/src/" in file_path:
            all_defined_functions.update(analyzer.defined_functions)
            all_defined_classes.update(analyzer.defined_classes)

    # Get used names from all files (including root directory)
    for file_path, analyzer in analyzers.items():
        all_used_names.update(analyzer.used_names)
        all_method_calls.update(analyzer.function_calls)
        all_used_names.update(analyzer.imported_names.keys())
        for module, names in analyzer.from_imports.items():
            # Handle relative imports
            if module.startswith("."):
                continue
            all_used_names.update(names)

    unused_items = []

    # Check for unused functions
    for func_name, line_no in all_defined_functions:
        # Skip special methods and common patterns
        if func_name.startswith("_") and not func_name.startswith("__"):
            continue
        if func_name in ["main", "__init__", "run", "execute"]:
            continue
        # Skip dunder methods that might be called internally
        if func_name.startswith("__") and func_name.endswith("__"):
            continue

        if func_name not in all_used_names:
            # Find which file this function belongs to
            for file_path, analyzer in analyzers.items():
                if (func_name, line_no) in analyzer.defined_functions:
                    unused_items.append(
                        UnusedItem(
                            file_path=file_path,
                            line_number=line_no,
                            item_type="function",
                            name=func_name,
                            reason=f"Function '{func_name}' is never called or referenced",
                        )
                    )
                    break

    # Check for unused classes
    for class_name, methods in all_defined_classes.items():
        # Check if it's just the class marker
        has_real_methods = any(m[0] != "__class__" for m in methods)

        if not has_real_methods:
            # Empty class
            class_line = methods[0][1]
            if class_name not in all_used_names:
                for file_path, analyzer in analyzers.items():
                    if class_name in analyzer.defined_classes:
                        unused_items.append(
                            UnusedItem(
                                file_path=file_path,
                                line_number=class_line,
                                item_type="class",
                                name=class_name,
                                reason=f"Class '{class_name}' is never instantiated or referenced",
                            )
                        )
                        break
        else:
            # Check for unused methods in classes
            for method_name, line_no in methods:
                if method_name == "__class__":
                    continue

                # Skip special methods
                if method_name.startswith("_") and not method_name.startswith("__"):
                    continue
                if method_name in ["__init__", "__str__", "__repr__", "__post_init__"]:
                    continue
                if method_name.startswith("__") and method_name.endswith("__"):
                    continue

                # Check if method is used directly
                method_used = False

                # Check direct calls
                if (class_name, method_name) in all_method_calls:
                    method_used = True

                # Check if used as a standalone name
                if method_name in all_used_names:
                    method_used = True

                # Check context manager methods if class is used with 'with'
                if (
                    method_name in ["__enter__", "__exit__", "__aenter__", "__aexit__"]
                    and class_name in all_used_names
                ):
                    method_used = True

                if not method_used:
                    # Find which file this method belongs to
                    for file_path, analyzer in analyzers.items():
                        if class_name in analyzer.defined_classes:
                            for method_name, line_no in analyzer.defined_classes[class_name]:
                                if method_name == method_name and line_no == line_no:
                                    unused_items.append(
                                        UnusedItem(
                                            file_path=file_path,
                                            line_number=line_no,
                                            item_type="method",
                                            name=f"{class_name}.{method_name}",
                                            reason=f"Method '{method_name}' in class '{class_name}' is never called",
                                        )
                                    )
                                    break

    return unused_items


def main():
    """Main function."""
    src_dir = Path("/Users/jito.hello/dev/wooto/homesweethome/src")
    root_dir = Path("/Users/jito.hello/dev/wooto/homesweethome")

    print("🔍 COMPREHENSIVE UNUSED CODE ANALYSIS")
    print("=" * 80)
    print(f"Scanning src directory: {src_dir}")
    print(f"Scanning root directory: {root_dir}")
    print("-" * 80)

    unused_items = find_unused_items(src_dir, root_dir)

    # Group by file and prioritize by directory
    writers_items = []
    other_items = []

    for item in unused_items:
        if "writers/" in item.file_path:
            writers_items.append(item)
        else:
            other_items.append(item)

    # Sort writers items first
    print("\n\n🎯 WRITERS PACKAGE UNUSED CODE")
    print("=" * 80)

    writers_by_file = defaultdict(list)
    for item in writers_items:
        writers_by_file[item.file_path].append(item)

    for file_path in sorted(writers_by_file.keys()):
        items = writers_by_file[file_path]
        print(f"\n📁 {file_path}")
        print("-" * 40)
        for item in sorted(items, key=lambda x: x.line_number):
            print(f"  Line {item.line_number:4d}: {item.item_type:8s} '{item.name}'")

    # Other files
    print("\n\n📂 OTHER FILES UNUSED CODE")
    print("=" * 80)

    other_by_file = defaultdict(list)
    for item in other_items:
        other_by_file[item.file_path].append(item)

    for file_path in sorted(other_by_file.keys()):
        items = other_by_file[file_path]
        print(f"\n📁 {file_path}")
        print("-" * 40)
        for item in sorted(items, key=lambda x: x.line_number):
            print(f"  Line {item.line_number:4d}: {item.item_type:8s} '{item.name}'")

    # Summary
    print("\n\n📊 SUMMARY")
    print("=" * 80)
    print(f"Total unused items found: {len(unused_items)}")

    # Count by type
    by_type = defaultdict(int)
    writers_count = len(writers_items)
    for item in unused_items:
        by_type[item.item_type] += 1

    print("\nBy type:")
    for item_type, count in sorted(by_type.items()):
        print(f"  {item_type.capitalize()}: {count}")

    print("\nBy location:")
    print(f"  Writers package: {writers_count}")
    print(f"  Other files: {len(other_items)}")

    # Files with most unused code
    file_counts = defaultdict(int)
    for item in unused_items:
        file_counts[item.file_path] += 1

    print("\nFiles with most unused code:")
    for file_path, count in sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {Path(file_path).name}: {count} items")

    return 0


if __name__ == "__main__":
    sys.exit(main())
