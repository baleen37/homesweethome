#!/usr/bin/env python3
"""
Remove unused imports from Python files automatically.
"""

import os
import re
from pathlib import Path
from typing import List

# Import the detection functions
from find_unused_imports_tdd import ImportInfo, analyze_file, find_python_files


def remove_imports_from_source(source: str, unused_imports: List[ImportInfo]) -> str:
    """Remove unused imports from source code."""
    lines = source.splitlines(keepends=True)

    # Get line numbers of unused imports
    lines_to_remove = set()
    for import_info in unused_imports:
        lines_to_remove.add(import_info.line_no - 1)  # Convert to 0-based index

    # Filter out lines with unused imports
    new_lines = []
    for i, line in enumerate(lines):
        if i in lines_to_remove:
            # Check if it's a multi-line import
            stripped = line.strip()
            if stripped.endswith("\\"):
                # This is part of a multi-line import, remove the continuation
                continue
            elif i > 0 and lines[i - 1].strip().endswith("\\"):
                # This line continues a previous import that was removed
                continue
            elif stripped.startswith(("import ", "from ")):
                # Single line import, remove it
                continue
            else:
                # Import might be embedded in a line, need more careful handling
                # For now, keep the line
                new_lines.append(line)
        else:
            # Check if previous line was a continuation of a removed import
            if i > 0 and (i - 1) in lines_to_remove and lines[i - 1].strip().endswith("\\"):
                # Skip this line as it's part of a removed multi-line import
                continue
            else:
                new_lines.append(line)

    # Join lines and clean up extra blank lines
    result = "".join(new_lines)

    # Remove multiple consecutive blank lines
    result = re.sub(r"\n\s*\n\s*\n", "\n\n", result)

    return result


def process_file(file_path: Path) -> int:
    """Process a single file to remove unused imports."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            original_source = f.read()
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")
        return 0

    unused_imports, _ = analyze_file(file_path)

    if not unused_imports:
        return 0

    print(f"\n{file_path}:")
    for imp in sorted(unused_imports, key=lambda x: x.line_no):
        if imp.alias:
            print(f"  Removing: import {imp.module} as {imp.alias}")
        else:
            print(
                f"  Removing: {'from ' + imp.module + ' import ' if imp.module else 'import'} {imp.name}"
            )

    new_source = remove_imports_from_source(original_source, unused_imports)

    if new_source != original_source:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_source)
            return len(unused_imports)
        except Exception as e:
            print(f"Error: Could not write to {file_path}: {e}")
            return 0

    return 0


def main():
    """Main function to remove unused imports."""
    base_dir = Path(".")

    # Directories to check
    directories = ["src", "tests", "scripts", "."]

    total_removed = 0
    files_processed = 0

    print("Removing unused imports...\n")

    # First, run find_unused_imports_tdd.py to show what will be removed
    print("=== DRY RUN - Showing what will be removed ===")
    os.system(
        "python find_unused_imports_tdd.py 2>&1 | grep -v '^Warning:' | grep -A 1000 'UNUSED IMPORTS REPORT'"
    )

    print("\n" + "=" * 80)
    print("ACTUAL REMOVAL")
    print("=" * 80)

    # Ask for confirmation
    response = input("\nDo you want to proceed with removing these unused imports? (y/N): ")
    if response.lower() not in ["y", "yes"]:
        print("Aborted.")
        return

    for directory in directories:
        dir_path = base_dir / directory
        if not dir_path.exists():
            continue

        print(f"\nProcessing {directory}/")
        python_files = find_python_files(dir_path)

        for file_path in python_files:
            # Skip the script itself
            if file_path.name in [
                "remove_unused_imports.py",
                "find_unused_imports_tdd.py",
                "test_unused_imports_detection.py",
            ]:
                continue

            removed_count = process_file(file_path)
            if removed_count > 0:
                total_removed += removed_count
                files_processed += 1

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Files processed: {files_processed}")
    print(f"Total unused imports removed: {total_removed}")


if __name__ == "__main__":
    main()
