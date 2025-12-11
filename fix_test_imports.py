#!/usr/bin/env python3
"""
Script to fix import issues in all test files by adding test_setup import.

This script will:
1. Find all Python test files in tests/ directory
2. Add the test_setup import if not already present
3. Ensure the import comes after any shebang or docstring but before other imports
"""

from pathlib import Path
from typing import List


def find_test_files(test_dir: Path) -> List[Path]:
    """Find all Python test files in the given directory."""
    test_files = []
    for file_path in test_dir.rglob("*.py"):
        if file_path.name.startswith("test_") and file_path.name != "test_setup.py":
            test_files.append(file_path)
    return test_files


def read_file_content(file_path: Path) -> List[str]:
    """Read file content as list of lines."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.readlines()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []


def write_file_content(file_path: Path, lines: List[str]) -> None:
    """Write lines to file."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        print(f"Error writing {file_path}: {e}")


def find_insert_position(lines: List[str]) -> int:
    """Find the best position to insert the test_setup import."""
    # Skip shebang if present
    pos = 0
    if lines and lines[0].startswith("#!"):
        pos = 1

    # Skip module docstring if present
    if pos < len(lines) and lines[pos].strip().startswith('"""'):
        pos += 1
        # Find end of docstring
        while pos < len(lines) and '"""' not in lines[pos]:
            pos += 1
        if pos < len(lines):
            pos += 1

    # Skip any blank lines
    while pos < len(lines) and not lines[pos].strip():
        pos += 1

    return pos


def has_test_setup_import(lines: List[str]) -> bool:
    """Check if file already imports test_setup."""
    for line in lines:
        if "import tests.test_setup" in line or "from tests.test_setup" in line:
            return True
    return False


def fix_test_file(file_path: Path) -> bool:
    """Fix imports in a single test file."""
    lines = read_file_content(file_path)
    if not lines:
        return False

    # Skip if already has test_setup import
    if has_test_setup_import(lines):
        print("  ✓ Already has test_setup import")
        return True

    # Skip conftest.py as it has special handling
    if file_path.name == "conftest.py":
        print("  ⚠ Skipping conftest.py (has special handling)")
        return True

    # Find insert position
    insert_pos = find_insert_position(lines)

    # Prepare import line
    import_line = (
        "# Import test setup to configure path and mocks\nimport tests.test_setup as _\n\n"
    )

    # Insert the import
    lines.insert(insert_pos, import_line)

    # Write back
    write_file_content(file_path, lines)
    print("  ✓ Fixed")
    return True


def main():
    """Main function to fix all test files."""
    test_dir = Path("tests")
    if not test_dir.exists():
        print(f"Error: {test_dir} directory not found")
        return

    test_files = find_test_files(test_dir)
    print(f"Found {len(test_files)} test files")

    fixed_count = 0
    for file_path in sorted(test_files):
        print(f"\nProcessing {file_path.relative_to(Path.cwd())}:")
        if fix_test_file(file_path):
            fixed_count += 1

    print(f"\n✅ Fixed {fixed_count} test files")


if __name__ == "__main__":
    main()
