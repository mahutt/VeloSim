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

import subprocess
import sys
import re


def get_current_branch() -> str:
    """Get the current Git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Error getting current branch: {e}")
        sys.exit(1)


def validate_branch_name(branch_name: str) -> tuple[bool, str, str]:
    """
    Validate branch name against the convention: [prefix]/[issue-number]-[hyphen-separated-name]

    Returns:
        tuple: (is_valid, branch_type, error_message)
    """
    # Skip validation for main/master branches
    if branch_name in ["main", "master", "develop", "HEAD"]:
        return True, "main", ""

    # Define valid prefixes and their patterns
    valid_patterns = {
        "feature": r"^feature/\d+-[\w-]+$",
        "bugfix": r"^bugfix/\d+-[\w-]+$",
        "ci": r"^ci/\d+-[\w-]+$",
        "docs": r"^docs/\d+-[\w-]+$",
        "hotfix": r"^hotfix/\d+-[\w-]+$",
        "refactor": r"^refactor/\d+-[\w-]+$",
    }

    # Check against each pattern
    for branch_type, pattern in valid_patterns.items():
        if re.match(pattern, branch_name):
            return True, branch_type, ""

    # If no pattern matches, create error message
    error_msg = f"""
[ERROR] Invalid branch name: '{branch_name}'

Required format: [prefix]/[issue-number]-[hyphen-separated-name]

Valid prefixes:
  - feature/  - New features and enhancements
  - bugfix/   - Bug fixes and patches
  - ci/       - CI/CD and infrastructure changes
  - docs/     - Documentation only changes
  - hotfix/   - Critical production fixes
  - refactor/ - Code refactoring

Examples:
  - feature/123-user-authentication
  - bugfix/456-fix-memory-leak
  - ci/789-add-coverage-checks
  - docs/101-update-api-documentation

To rename your branch:
  git branch -m {branch_name} [new-valid-name]
"""

    return False, "invalid", error_msg


def main():
    """Main function to validate the current branch name."""
    print("[INFO] Checking branch naming convention...")

    # Get current branch
    branch_name = get_current_branch()
    print(f"[INFO] Current branch: {branch_name}")

    # Validate branch name
    is_valid, branch_type, error_message = validate_branch_name(branch_name)

    if is_valid:
        print(f"[SUCCESS] Valid {branch_type} branch: {branch_name}")
        sys.exit(0)
    else:
        print(error_message)
        sys.exit(1)
if __name__ == "__main__":
    main()
