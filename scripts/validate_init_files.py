#!/usr/bin/env python3
"""
MIT License

Copyright (c) 2025 VeloSim Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
import sys
from pathlib import Path
from typing import List, Set


def find_python_directories(root_path: Path) -> Set[Path]:
    """Find all directories that contain Python files or subdirectories with Python files."""
    python_dirs = set()

    def has_python_content(directory: Path) -> bool:
        """Check if directory has Python files or subdirectories with Python files."""
        # Skip alembic versions directory (contains auto-generated migration files)
        if 'alembic' in directory.parts and 'versions' in directory.parts:
            return False

        # Check for .py files in current directory
        if any(f.suffix == '.py' for f in directory.iterdir() if f.is_file()):
            return True

        # Check subdirectories recursively
        for item in directory.iterdir():
            if item.is_dir() and not item.name.startswith('.') and item.name != '__pycache__':
                if has_python_content(item):
                    return True

        return False

    def collect_dirs(directory: Path):
        """Recursively collect directories that should have __init__.py files."""
        if not directory.exists() or not directory.is_dir():
            return

        # Skip hidden directories and __pycache__
        if directory.name.startswith('.') or directory.name == '__pycache__':
            return

        # If this directory has Python content, it should have __init__.py
        if has_python_content(directory):
            python_dirs.add(directory)

        # Recursively check subdirectories
        for item in directory.iterdir():
            if item.is_dir():
                collect_dirs(item)

    collect_dirs(root_path)
    return python_dirs


def check_init_files(directories: List[str]) -> bool:
    """Check if all specified directories have __init__.py files."""
    missing_init_files = []
    all_python_dirs = set()

    for dir_name in directories:
        root_path = Path(dir_name)
        if not root_path.exists():
            print(f"[WARNING] Directory '{dir_name}' does not exist")
            continue

        python_dirs = find_python_directories(root_path)
        all_python_dirs.update(python_dirs)

    # Check each Python directory for __init__.py
    for py_dir in sorted(all_python_dirs):
        init_file = py_dir / "__init__.py"
        if not init_file.exists():
            missing_init_files.append(py_dir)

    # Report results
    if missing_init_files:
        print("[ERROR] Missing __init__.py files in the following directories:")
        for missing_dir in sorted(missing_init_files):
            print(f"   - {missing_dir}")
        print()
        print("[INFO] To fix this, run:")
        for missing_dir in sorted(missing_init_files):
            print(f"   touch {missing_dir}/__init__.py")
        return False
    else:
        print("[SUCCESS] All Python directories have __init__.py files")
        if all_python_dirs:
            print(f"[INFO] Checked {len(all_python_dirs)} directories:")
            for py_dir in sorted(all_python_dirs):
                print(f"   - {py_dir}")
        return True


def main():
    """Main function to check __init__.py files in back and sim directories."""
    print("[INFO] Checking for __init__.py files in Python directories...")
    print()

    directories_to_check = ["back", "sim"]
    success = check_init_files(directories_to_check)

    if not success:
        print()
        print("[ERROR] __init__.py validation failed!")
        print("Please add __init__.py files to all Python directories.")
        sys.exit(1)
    else:
        print()
        print("[SUCCESS] __init__.py validation passed!")
        sys.exit(0)
if __name__ == "__main__":
    main()
