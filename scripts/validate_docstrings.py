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

import ast
import sys
from pathlib import Path
from typing import List, Tuple, Optional


class DocstringValidator(ast.NodeVisitor):
    """Validates that functions have complete docstrings with Args and Returns."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def _validate_function_docstring(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        """
        Validate docstring for a function or async function node.

        Args:
            node: The function definition node to validate
        """
        # Skip private functions (those starting with _)
        if node.name.startswith("_"):
            return

        # Skip if no arguments and no return type
        has_args = len(node.args.args) > 1 or (
            len(node.args.args) == 1 and node.args.args[0].arg != "self"
        )
        has_return = node.returns is not None and str(node.returns) != "None"

        # If function has no args and no return, it only needs a basic docstring
        if not has_args and not has_return:
            if not ast.get_docstring(node):
                self.errors.append(
                    f"{self.filepath}:{node.lineno}: Function '{node.name}' "
                    f"is missing a docstring"
                )
            return

        # Get the docstring
        docstring = ast.get_docstring(node)
        if not docstring:
            self.errors.append(
                f"{self.filepath}:{node.lineno}: Function '{node.name}' "
                f"is missing a docstring"
            )
            return

        # Check for Args section if function has parameters
        if has_args:
            if "Args:" not in docstring and "Parameters:" not in docstring:
                self.errors.append(
                    f"{self.filepath}:{node.lineno}: Function '{node.name}' "
                    f"has parameters but docstring is missing 'Args:' section"
                )

        # Check for Returns section if function has return type annotation
        if has_return:
            if "Returns:" not in docstring and "Return:" not in docstring:
                self.errors.append(
                    f"{self.filepath}:{node.lineno}: Function '{node.name}' "
                    f"has return type but docstring is missing 'Returns:' section"
                )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """
        Visit synchronous function definition nodes.

        Args:
            node: The function definition node to visit
        """
        self._validate_function_docstring(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """
        Visit asynchronous function definition nodes.

        Args:
            node: The async function definition node to visit
        """
        self._validate_function_docstring(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """
        Visit class definition nodes.

        Args:
            node: The class definition node to visit
        """
        docstring = ast.get_docstring(node)
        if not docstring:
            self.errors.append(
                f"{self.filepath}:{node.lineno}: Class '{node.name}' is missing a docstring"
            )
        elif not docstring.strip():
            self.errors.append(
                f"{self.filepath}:{node.lineno}: Class '{node.name}' has an empty docstring"
            )
        else:
            # Check for one-line summary (first non-empty line)
            lines = [line.strip() for line in docstring.split('\n') if line.strip()]
            if not lines:
                self.errors.append(
                    f"{self.filepath}:{node.lineno}: Class '{node.name}' docstring is empty"
                )
            elif not lines[0].endswith(('.', '?', '!')):
                self.warnings.append(
                    f"{self.filepath}:{node.lineno}: Class '{node.name}' docstring summary should end with punctuation"
                )

        self.generic_visit(node)


def validate_file(filepath: Path) -> Tuple[List[str], List[str]]:
    """
    Validate docstrings in a single Python file.

    Args:
        filepath: Path to the Python file to validate

    Returns:
        Tuple of (errors, warnings) found in the file
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(filepath))

        validator = DocstringValidator(filepath)
        validator.visit(tree)

        return validator.errors, validator.warnings

    except SyntaxError as e:
        return [f"{filepath}: Syntax error: {e}"], []
    except Exception as e:
        return [f"{filepath}: Error reading file: {e}"], []


def main() -> int:
    """
    Main entry point for docstring validation.

    Returns:
        Exit code (0 for success, 1 for errors found)
    """
    # Get the project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Define directories to check
    back_dir = project_root / "back"
    sim_dir = project_root / "sim"

    # Patterns to exclude
    exclude_patterns = [
        "**/alembic/**",
        "**/__pycache__/**",
        "**/tests/*",
        "**/tests/**/*",
        "**/.venv/*",
        "**/.venv/**/*",
        "**/venv/*",
        "**/venv/**/*",
        "**/.pytest_cache/**",
    ]

    all_errors: List[str] = []
    all_warnings: List[str] = []

    # Find all Python files
    python_files: List[Path] = []
    for directory in [back_dir, sim_dir]:
        if directory.exists():
            for py_file in directory.rglob("*.py"):
                # Check if file should be excluded using pathlib pattern matching
                relative_path = py_file.relative_to(project_root)
                should_exclude = False

                # Check if path contains .venv, venv, or alembic directories
                if '.venv' in relative_path.parts or 'venv' in relative_path.parts or 'alembic' in relative_path.parts:
                    should_exclude = True
                else:
                    # Check each exclude pattern using pathlib.match()
                    for pattern in exclude_patterns:
                        if relative_path.match(pattern):
                            should_exclude = True
                            break

                if not should_exclude:
                    python_files.append(py_file)

    if not python_files:
        print("No Python files found to validate.")
        return 0

    print(f"Validating docstrings in {len(python_files)} files...")
    print("=" * 80)

    # Validate each file
    files_with_errors = 0
    for filepath in sorted(python_files):
        errors, warnings = validate_file(filepath)

        if errors:
            files_with_errors += 1
            all_errors.extend(errors)

        if warnings:
            all_warnings.extend(warnings)

    # Print results
    if all_errors:
        print("\nDOCSTRING VALIDATION ERRORS:")
        print("=" * 80)
        for error in all_errors:
            print(f"  {error}")
        print("=" * 80)
        print(f"\nFound {len(all_errors)} errors in {files_with_errors} files.")
        print("\nDocstring Format Guide:")
        print("  Functions with parameters should include an 'Args:' section")
        print("  Functions with return values should include a 'Returns:' section")
        print("\n  Example:")
        print('  """')
        print("  Brief description of what the function does.")
        print()
        print("  Args:")
        print("      param1: Description of first parameter")
        print("      param2: Description of second parameter")
        print()
        print("  Returns:")
        print("      Description of return value")
        print('  """')
        print()
        return 1

    if all_warnings:
        print("\nDOCSTRING WARNINGS:")
        print("=" * 80)
        for warning in all_warnings:
            print(f"  {warning}")
        print("=" * 80)

    print("\nAll docstrings are properly formatted!")
    print(f"Validated {len(python_files)} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
