#!/usr/bin/env python3
"""Find unused functions, classes, and methods in the Python codebase."""

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
        self.defined_classes: Dict[
            str, List[Tuple[str, int]]
        ] = {}  # class -> [(method, line), ...]
        self.used_names: Set[str] = set()
        self.imported_names: Dict[str, str] = {}  # imported_name -> original_name
        self.from_imports: Dict[str, Set[str]] = defaultdict(set)  # module -> set of names
        self.current_class: Optional[str] = None
        self.function_calls: Set[Tuple[str, str]] = (
            set()
        )  # (class_name, method_name) for method calls

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
        self.defined_functions.add((node.name, node.lineno))

        # Check if it's a method in a class
        if self.current_class:
            if self.current_class not in self.defined_classes:
                self.defined_classes[self.current_class] = []
            self.defined_classes[self.current_class].append((node.name, node.lineno))

        # Skip visiting function body to avoid collecting names from unused functions
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
        """Visit attribute access (e.g., obj.method or Class.method)."""
        if isinstance(node.value, ast.Name):
            # Handle Class.method or obj.method
            if isinstance(node.ctx, ast.Load):
                self.used_names.add(node.value.id)
                if hasattr(node, "attr"):
                    # This could be a method call
                    self.function_calls.add((node.value.id, node.attr))
        elif isinstance(node.value, ast.Attribute):
            # Handle nested attributes like module.Class.method
            pass
        self.generic_visit(node)

    def visit_Call(self, node):
        """Visit function calls."""
        if isinstance(node.func, ast.Name):
            self.used_names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                self.function_calls.add((node.func.value.id, node.func.attr))
        self.generic_visit(node)


def analyze_file(file_path: Path) -> Tuple[CodeAnalyzer, List[str]]:
    """Analyze a single Python file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        analyzer = CodeAnalyzer(str(file_path))
        tree = ast.parse(content)
        analyzer.visit(tree)

        return analyzer, []
    except Exception as e:
        return None, [f"Error analyzing {file_path}: {e}"]


def find_unused_items(src_dir: Path) -> List[UnusedItem]:
    """Find all unused functions, classes, and methods."""
    all_files = list(src_dir.rglob("*.py"))

    # Analyze all files
    analyzers = {}
    errors = []

    for file_path in all_files:
        analyzer, file_errors = analyze_file(file_path)
        if analyzer:
            analyzers[str(file_path)] = analyzer
        errors.extend(file_errors)

    # Print any analysis errors
    for error in errors:
        print(f"Warning: {error}", file=sys.stderr)

    # Collect all defined and used items
    all_defined_functions = set()
    all_defined_classes = {}
    all_used_names = set()
    all_method_calls = set()

    # Get items from src directory only
    for file_path, analyzer in analyzers.items():
        if "/src/" in file_path:
            all_defined_functions.update(analyzer.defined_functions)
            all_defined_classes.update(analyzer.defined_classes)
            all_used_names.update(analyzer.used_names)
            all_method_calls.update(analyzer.function_calls)

    # Check imports from all files (including root directory scripts)
    for file_path, analyzer in analyzers.items():
        all_used_names.update(analyzer.imported_names.keys())
        for module, names in analyzer.from_imports.items():
            # Handle relative imports
            if module.startswith("."):
                continue
            all_used_names.update(names)

    unused_items = []

    # Check for unused functions
    for func_name, line_no in all_defined_functions:
        # Skip special methods and main functions
        if func_name.startswith("_") and not func_name.startswith("__"):
            continue
        if func_name in ["main", "__init__"]:
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
        # Skip if it's just the class marker
        if len(methods) == 1 and methods[0][0] == "__class__":
            class_line = methods[0][1]

            # Check if class is used
            if class_name not in all_used_names:
                # Find which file this class belongs to
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
                if method_name in ["__init__", "__str__", "__repr__"]:
                    continue

                # Check if method is used directly
                if (
                    class_name,
                    method_name,
                ) not in all_method_calls and method_name not in all_used_names:
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

    if not src_dir.exists():
        print(f"Error: src directory {src_dir} does not exist")
        return 1

    print("Analyzing Python codebase for unused code...")
    print(f"Scanning directory: {src_dir}")
    print("-" * 80)

    unused_items = find_unused_items(src_dir)

    # Group by file
    items_by_file = defaultdict(list)
    for item in unused_items:
        items_by_file[item.file_path].append(item)

    # Print results
    total_unused = 0
    for file_path in sorted(items_by_file.keys()):
        items = items_by_file[file_path]
        print(f"\n📁 {file_path}")
        print("-" * 40)

        for item in sorted(items, key=lambda x: x.line_number):
            print(f"  Line {item.line_number}: {item.item_type} '{item.name}'")
            print(f"    → {item.reason}")
            total_unused += 1

    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"Total unused items found: {total_unused}")

    # Count by type
    by_type = defaultdict(int)
    for item in unused_items:
        by_type[item.item_type] += 1

    for item_type, count in sorted(by_type.items()):
        print(f"  {item_type.capitalize()}: {count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
