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
Comprehensive commit message validation script.
Validates both conventional commit format and issue number requirements.
Skips validation for merge commits and revert commits.
"""
import re
import sys
from pathlib import Path


def is_merge_commit(commit_message: str) -> bool:
    """Check if the commit message indicates a merge commit."""
    merge_patterns = [
        "Merge branch",
        "Merge pull request",
        "Merge remote-tracking branch",
        "Merge tag",
    ]
    return any(commit_message.startswith(pattern) for pattern in merge_patterns)


def is_revert_commit(commit_message: str) -> bool:
    """Check if the commit message indicates a revert commit."""
    return commit_message.startswith("Revert ")


def validate_conventional_commit(commit_message: str) -> bool:
    """Validate that commit message follows conventional commit format."""
    # Basic conventional commit pattern
    conventional_pattern = r'^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\(.+\))?: .+'
    return re.match(conventional_pattern, commit_message) is not None


def validate_issue_number(commit_message: str) -> bool:
    """
    Check if commit message contains an issue number reference.

    Patterns accepted:
    - #123 (direct reference)
    - fixes #123, closes #123, resolves #123
    - fix #123, close #123, resolve #123
    - Fixes #123, Closes #123, Resolves #123
    - Fix #123, Close #123, Resolve #123
    """
    # Pattern to match issue references
    issue_patterns = [
        r'#\d+',  # Direct reference like #123
        r'(?:fix|fixes|close|closes|resolve|resolves)\s+#\d+',  # Action words with issue
        r'(?:Fix|Fixes|Close|Closes|Resolve|Resolves)\s+#\d+',  # Capitalized action words
    ]

    for pattern in issue_patterns:
        if re.search(pattern, commit_message, re.IGNORECASE):
            return True

    return False


def main():
    """Main validation function."""
    if len(sys.argv) != 2:
        print("Usage: validate_commit_wrapper.py <commit_msg_file>")
        sys.exit(1)

    commit_msg_file = Path(sys.argv[1])

    if not commit_msg_file.exists():
        print(f"Commit message file {commit_msg_file} not found")
        sys.exit(1)

    commit_message = commit_msg_file.read_text(encoding='utf-8').strip()

    # Skip all validation for merge and revert commits
    if is_merge_commit(commit_message):
        print("[SKIP] Merge commit detected - skipping all commit message validation")
        sys.exit(0)

    if is_revert_commit(commit_message):
        print("[SKIP] Revert commit detected - skipping all commit message validation")
        sys.exit(0)

    # For regular commits, validate both conventional format and issue number
    validation_errors = []

    # Check conventional commit format
    if not validate_conventional_commit(commit_message):
        validation_errors.append("conventional_format")

    # Check issue number requirement
    if not validate_issue_number(commit_message):
        validation_errors.append("issue_number")

    if validation_errors:
        print(f"[FAIL] Commit message validation failed")
        print(f"Message: {commit_message}")
        print()

        if "conventional_format" in validation_errors:
            print("❌ Conventional commit format validation failed")
            print("Conventional Commits start with one of the below types, followed by a colon:")
            print("  build, chore, ci, docs, feat, fix, perf, refactor, revert, style, test")
            print()
            print("Examples:")
            print("  feat: implement new API")
            print("  fix: remove infinite loop")
            print("  fix(account): remove infinite loop")
            print()

        if "issue_number" in validation_errors:
            print("❌ Issue number validation failed")
            print("Commit message must reference an issue number!")
            print("Examples of valid formats:")
            print("  feat: add user authentication #123")
            print("  fix: resolve login bug fixes #456")
            print("  docs: update README closes #789")
            print("  refactor: improve performance resolves #101")
            print()

        print("See: https://www.conventionalcommits.org/")
        sys.exit(1)
    else:
        print("[PASS] All commit message validations passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
