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
License Header Validation Script

This script validates that all source files contain the required MIT license header.
It checks Python (.py), JavaScript (.js), TypeScript (.ts), JSX (.jsx), and TSX (.tsx) files.
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Set

# Define the expected license header for different file types
LICENSE_HEADERS = {
    'python': '''"""
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
"""''',

    'javascript': '''/**
 * MIT License
 *
 * Copyright (c) 2025 VeloSim Contributors
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */'''
}

# File extensions and their corresponding license header type
FILE_EXTENSIONS = {
    '.py': 'python',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'javascript',
    '.tsx': 'javascript'
}

# Files and directories to exclude from license header checks
EXCLUDED_PATHS = {
    # Configuration files
    'eslint.config.js',
    'vite.config.ts',
    'vitest.config.ts',
    'react-router.config.ts',

    # Test setup files
    'tests/setup.ts',
    'setup.ts',

    # Build/dist/coverage directories
    'dist',
    'build',
    'coverage',
    'coverage_html',
    'htmlcov',  # HTML coverage reports
    'node_modules',
    '.git',
    '.venv',  # Virtual environment directory
    '.react-router',  # React Router cache directory

    # Package files
    '__pycache__',
    '.pytest_cache',
    'velosim.egg-info',

    # Migration directories (auto-generated files)
    'versions',  # Alembic versions directory
    'alembic/versions',  # Full path

    # Playwright test artifacts (auto-generated)
    'playwright-report',  # Playwright HTML reports
    'test-results',  # Playwright test results and videos

    # Python package init files
    '__init__.py',  # All __init__.py files
}

def normalize_whitespace(text: str) -> str:
    """Normalize whitespace for comparison."""
    # Remove leading/trailing whitespace and normalize internal whitespace
    lines = [line.strip() for line in text.strip().split('\n')]
    return '\n'.join(lines)

def check_license_header(file_path: Path) -> bool:
    """Check if a file contains the required license header."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Get the expected header for this file type
        extension = file_path.suffix.lower()
        if extension not in FILE_EXTENSIONS:
            return True  # Skip unsupported file types

        header_type = FILE_EXTENSIONS[extension]
        expected_header = LICENSE_HEADERS[header_type]

        # Normalize both headers for comparison
        normalized_expected = normalize_whitespace(expected_header)

        # For Python files, check if it starts with the docstring
        if header_type == 'python':
            # Handle shebang line - skip it if present
            content_to_check = content
            if content.startswith('#!'):
                first_newline = content.find('\n')
                if first_newline != -1:
                    content_to_check = content[first_newline + 1:].lstrip()

            # Extract the first docstring or comment block
            if content_to_check.startswith('"""'):
                end_pos = content_to_check.find('"""', 3)
                if end_pos != -1:
                    actual_header = content_to_check[:end_pos + 3]
                    normalized_actual = normalize_whitespace(actual_header)
                    return normalized_expected in normalized_actual or normalized_actual in normalized_expected

        # For JavaScript/TypeScript files, check if it starts with the comment block
        elif header_type == 'javascript':
            # Handle shebang line - skip it if present
            content_to_check = content
            if content.startswith('#!'):
                first_newline = content.find('\n')
                if first_newline != -1:
                    content_to_check = content[first_newline + 1:].lstrip()

            if content_to_check.startswith('/**'):
                end_pos = content_to_check.find('*/', 3)
                if end_pos != -1:
                    actual_header = content_to_check[:end_pos + 2]
                    normalized_actual = normalize_whitespace(actual_header)
                    return normalized_expected in normalized_actual or normalized_actual in normalized_expected

        return False

    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

def should_exclude_path(file_path: Path, repo_root: Path) -> bool:
    """Check if a path should be excluded from license header validation."""
    relative_path = file_path.relative_to(repo_root)

    # Check if any part of the path matches excluded items
    for part in relative_path.parts:
        if part in EXCLUDED_PATHS:
            return True

    # Check if the filename matches excluded items
    if file_path.name in EXCLUDED_PATHS:
        return True

    return False

def find_source_files(repo_root: Path) -> List[Path]:
    """Find all source files that need license headers."""
    source_files = []

    for ext in FILE_EXTENSIONS.keys():
        pattern = f"**/*{ext}"
        for file_path in repo_root.glob(pattern):
            if file_path.is_file() and not should_exclude_path(file_path, repo_root):
                source_files.append(file_path)

    return sorted(source_files)

def main():
    """Main function to validate license headers."""
    repo_root = Path(__file__).parent.parent

    print("Validating MIT license headers in source files...")
    print(f"Repository root: {repo_root}")

    source_files = find_source_files(repo_root)
    print(f"Found {len(source_files)} source files to check")

    missing_headers = []

    for file_path in source_files:
        if not check_license_header(file_path):
            missing_headers.append(file_path)

    if missing_headers:
        print(f"\n[ERROR] {len(missing_headers)} files are missing proper MIT license headers:")
        for file_path in missing_headers:
            relative_path = file_path.relative_to(repo_root)
            print(f"  - {relative_path}")

        print("\nTo fix this issue, add the appropriate license header to the top of each file:")
        print("\nFor Python files (.py):")
        print('"""')
        print("MIT License")
        print()
        print("Copyright (c) 2025 VeloSim Contributors")
        print("...")
        print('"""')

        print("\nFor JavaScript/TypeScript files (.js, .jsx, .ts, .tsx):")
        print("/**")
        print(" * MIT License")
        print(" * ")
        print(" * Copyright (c) 2025 VeloSim Contributors")
        print(" * ...")
        print(" */")

        sys.exit(1)
    else:
        print(f"\n[OK] All {len(source_files)} source files have proper MIT license headers!")
        sys.exit(0)

if __name__ == "__main__":
    main()
