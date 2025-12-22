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

"""
Build script for generating Sphinx documentation.

This script builds the HTML documentation from docstrings in the codebase.
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Build the Sphinx documentation."""
    docs_dir = Path(__file__).parent.parent / "docs"
    build_dir = docs_dir / "_build" / "html"

    print("Building VeloSim documentation...")
    print(f"Source: {docs_dir}")
    print(f"Output: {build_dir}")
    print()

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "sphinx",
                "-b",
                "html",
                str(docs_dir),
                str(build_dir),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        print(result.stdout)
        if result.stderr:
            print("Warnings:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)

        print()
        print("✓ Documentation built successfully!")
        print(f"Open {build_dir / 'index.html'} in your browser to view.")

    except subprocess.CalledProcessError as e:
        print("✗ Documentation build failed!", file=sys.stderr)
        print(e.stdout, file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(
            "✗ Sphinx not found. Install documentation dependencies:",
            file=sys.stderr,
        )
        print('  pip install -e ".[docs]"', file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
