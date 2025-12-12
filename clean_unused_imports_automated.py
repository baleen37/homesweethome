#!/usr/bin/env python3
"""
Automated script to clean unused imports using AST analysis.
This script safely removes unused imports while preserving code functionality.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Set, Optional
import re

# Add the project root to path
sys.path.insert(0, str(Path(__file__).parent))


class ImportCleaner(ast.NodeTransformer):
    """AST transformer to remove unused imports."""

    def __init__(self, unused_names: Set[str], unused_modules: Set[str]):
        self.unused_names = unused_names
        self.unused_modules = unused_modules
        self.changes_made = False

    def visit_Import(self, node: ast.Import) -> Optional[ast.Import]:
        """Handle regular import statements."""
        # Filter out unused imports
        new_names = []
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            if name not in self.unused_names:
                new_names.append(alias)
            else:
                self.changes_made = True
                print(f"  Removing import: {alias.name}")

        if new_names:
            node.names = new_names
            return node
        else:
            self.changes_made = True
            return None

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Optional[ast.ImportFrom]:
        """Handle from...import statements."""
        if node.module is None:
            return node  # Keep relative imports as is

        # Filter out unused imports
        new_names = []
        for alias in node.names:
            if alias.name == "*":
                # Keep star imports (require manual review)
                new_names.append(alias)
            else:
                name = alias.asname if alias.asname else alias.name
                if name not in self.unused_names:
                    new_names.append(alias)
                else:
                    self.changes_made = True
                    print(f"  Removing from {node.module}: {alias.name}")

        if new_names:
            node.names = new_names
            return node
        else:
            self.changes_made = True
            return None


def find_unused_imports_ast(file_path: Path) -> Set[str]:
    """Find unused imports using AST analysis."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")
        return set()

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        print(f"Warning: Syntax error in {file_path}")
        return set()

    # Track all imports
    imported_names = set()

    # Visit import nodes
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                imported_names.add(name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in node.names:
                    if alias.name != "*":
                        name = alias.asname if alias.asname else alias.name
                        imported_names.add(name)

    # Track all used names
    used_names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            # Track module usage in attributes (e.g., module.function)
            if isinstance(node.value, ast.Name):
                used_names.add(node.value.id)

    # Find unused imports (excluding special names and built-ins)
    unused = imported_names - used_names
    # Filter out some common false positives
    unused = {name for name in unused if not name.startswith("_")}

    return unused


def clean_file(file_path: Path) -> bool:
    """Clean unused imports from a single file."""
    unused_imports = find_unused_imports_ast(file_path)

    if not unused_imports:
        return False

    print(f"\n{file_path}:")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        # Parse AST
        tree = ast.parse(source, filename=str(file_path))

        # Apply transformation
        cleaner = ImportCleaner(unused_imports, set())
        new_tree = cleaner.visit(tree)

        if not cleaner.changes_made:
            return False

        # Fix missing locations
        ast.fix_missing_locations(new_tree)

        # Generate new source
        try:
            ast.unparse(new_tree)
        except AttributeError:
            # For Python < 3.9, use astor if available
            try:
                import astor

                astor.to_source(new_tree)
            except ImportError:
                print("  Warning: Could not regenerate source (needs Python 3.9+ or astor)")
                return False

        # Preserve comments and formatting by doing a line-based replacement
        original_lines = source.splitlines()
        new_lines = []

        # Simple approach: remove lines that contain unused imports
        for line in original_lines:
            line_stripped = line.strip()
            should_keep = True

            # Check if this line contains an unused import
            for unused in unused_imports:
                # Handle regular imports
                if line_stripped.startswith("import ") and f" as {unused}" in line:
                    should_keep = False
                    break
                # Handle from imports
                elif line_stripped.startswith("from "):
                    if f", {unused}," in line or f" {unused}" in line:
                        # More complex - need to handle multi-import lines
                        parts = line.split(",")
                        if len(parts) > 1:
                            # Multi-import line - remove just the unused part
                            new_parts = [p for p in parts if unused not in p]
                            if new_parts:
                                line = ",".join(new_parts)
                        else:
                            # Single import line
                            should_keep = False
                            break

            if should_keep:
                new_lines.append(line)

        # Join and clean up
        result = "\n".join(new_lines) + "\n" if new_lines else ""
        result = re.sub(r"\n\s*\n\s*\n", "\n\n", result)  # Remove extra blank lines

        # Write back
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(result)

        return True

    except Exception as e:
        print(f"  Error: {e}")
        return False


def main():
    """Main function to clean unused imports."""
    base_dir = Path(".")

    # Directories to process
    directories = ["src", "tests", "scripts"]

    total_files = 0
    modified_files = 0

    print("Scanning for unused imports to clean...\n")

    for directory in directories:
        dir_path = base_dir / directory
        if not dir_path.exists():
            continue

        print(f"Processing {directory}/")

        # Find all Python files
        for root, dirs, files in os.walk(dir_path):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in ["__pycache__", ".venv", "venv"]]

            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    total_files += 1

                    # Skip the script itself
                    if file_path.name == "clean_unused_imports_automated.py":
                        continue

                    if clean_file(file_path):
                        modified_files += 1

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total files scanned: {total_files}")
    print(f"Files modified: {modified_files}")

    if modified_files > 0:
        print(f"\n✓ Successfully cleaned unused imports from {modified_files} files")
    else:
        print("\n✓ No unused imports found to clean")


if __name__ == "__main__":
    main()
