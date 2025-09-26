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

#!/usr/bin/env python3
"""
License Header Addition Script

This script automatically adds MIT license headers to source files that are missing them.
Run this to fix license header validation failures.
"""

import os
import sys
from pathlib import Path
from validate_license_headers import (
    LICENSE_HEADERS,
    FILE_EXTENSIONS,
    find_source_files,
    check_license_header
)

def add_license_header(file_path: Path) -> bool:
    """Add the appropriate license header to a file."""
    try:
        # Read the current content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Get the header type for this file
        extension = file_path.suffix.lower()
        if extension not in FILE_EXTENSIONS:
            return False

        header_type = FILE_EXTENSIONS[extension]
        header = LICENSE_HEADERS[header_type]

        # Add header to the beginning of the file
        new_content = header + '\n\n' + content

        # Write the updated content back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True

    except Exception as e:
        print(f"Error adding license header to {file_path}: {e}")
        return False

def main():
    """Main function to add license headers to files missing them."""
    repo_root = Path(__file__).parent.parent

    print("Adding MIT license headers to source files...")
    print(f"Repository root: {repo_root}")

    source_files = find_source_files(repo_root)
    files_without_headers = []

    # Find files without headers
    for file_path in source_files:
        if not check_license_header(file_path):
            files_without_headers.append(file_path)

    if not files_without_headers:
        print("[OK] All source files already have proper MIT license headers!")
        return

    print(f"Found {len(files_without_headers)} files without license headers")

    # Ask for confirmation
    response = input(f"Do you want to add license headers to all {len(files_without_headers)} files? (y/N): ")
    if response.lower() not in ['y', 'yes']:
        print("Operation cancelled.")
        return

    # Add headers to files
    success_count = 0
    for file_path in files_without_headers:
        relative_path = file_path.relative_to(repo_root)
        if add_license_header(file_path):
            print(f"[OK] Added header to: {relative_path}")
            success_count += 1
        else:
            print(f"[ERROR] Failed to add header to: {relative_path}")

    print(f"\n[OK] Successfully added license headers to {success_count}/{len(files_without_headers)} files!")

    if success_count < len(files_without_headers):
        print("Some files failed. Please check the errors above and add headers manually.")
        sys.exit(1)

if __name__ == "__main__":
    main()
