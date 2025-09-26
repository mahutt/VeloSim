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
Validate that commit messages include an issue number.
This script checks for patterns like #123, fixes #123, closes #456, etc.
"""
import re
import sys
from pathlib import Path


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
        print("Usage: validate_commit_issue.py <commit_msg_file>")
        sys.exit(1)

    commit_msg_file = Path(sys.argv[1])

    if not commit_msg_file.exists():
        print(f"Commit message file {commit_msg_file} not found")
        sys.exit(1)

    commit_message = commit_msg_file.read_text(encoding='utf-8').strip()

    # Skip validation for merge commits
    if commit_message.startswith('Merge '):
        sys.exit(0)

    # Skip validation for revert commits
    if commit_message.startswith('Revert '):
        sys.exit(0)

    if not validate_issue_number(commit_message):
        print("[FAIL] Commit message must reference an issue number!")
        print("Examples of valid formats:")
        print("  - feat: add user authentication #123")
        print("  - fix: resolve login bug fixes #456")
        print("  - docs: update README closes #789")
        print("  - refactor: improve performance resolves #101")
        sys.exit(1)

    print("[PASS] Issue number validation passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
