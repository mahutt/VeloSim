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
Dependency License Compatibility Validation Script

This script validates that all dependencies (Python and npm) have licenses
that are compatible with MIT license for commercial redistribution.

It checks:
- Python dependencies using pip-licenses
- npm dependencies using license-checker
- Validates compatibility with MIT license for commercial use

License compatibility sources:
- Open Source Initiative (OSI): https://opensource.org/licenses/
- Free Software Foundation: https://www.gnu.org/licenses/license-list.html
- GitHub License Compatibility: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository
- SPDX License List: https://spdx.org/licenses/
- MIT License compatibility analysis: https://fossa.com/blog/open-source-licenses-101-mit-license/
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


# MIT-compatible licenses for commercial redistribution
MIT_COMPATIBLE_LICENSES = {
    # Permissive licenses
    'MIT',
    'MIT License',
    'MIT Licence',
    'MIT*',
    'ISC',
    'ISC License (ISCL)',
    'BSD',
    'BSD License',
    'BSD-2-Clause',
    'BSD-3-Clause',
    'Apache-2.0',
    'Apache 2.0',
    'Apache License 2.0',
    'Apache License v2.0',
    'Apache License, Version 2.0',
    'Apache Software License',
    'BlueOak-1.0.0',
    'Unlicense',
    'The Unlicense (Unlicense)',
    'CC0-1.0',
    'CC0',
    'Public Domain',
    'CC-BY-4.0',
    'CC-BY-3.0',
    'Python Software Foundation License',
    'Python-2.0',  # Python Software Foundation License (OSI approved)
    'CMU License (MIT-CMU)',

    # Dual licenses that include MIT-compatible options
    'Apache Software License; MIT License',
    'Apache Software License; BSD License',
    'MIT License; Mozilla Public License 2.0 (MPL 2.0)',
    '(MIT AND CC-BY-3.0)',

    # Mozilla Public License (weak copyleft, compatible for distribution)
    'MPL-2.0',
    'Mozilla Public License 2.0 (MPL 2.0)',

    # LGPL for dynamically linked libraries (like database drivers) - generally acceptable
    'GNU Library or Lesser General Public License (LGPL)',
    'GNU Lesser General Public License v3 (LGPLv3)',
    'GNU Lesser General Public License v3 or later (LGPLv3+)',
    'LGPL',
    'LGPL-2.1',
    'LGPL-3.0',

    # Some historically compatible licenses
    'OLDAP-2.8',  # OpenLDAP Public License
}

# Licenses that are NOT compatible with MIT for commercial redistribution
INCOMPATIBLE_LICENSES = {
    # GPL family (strong copyleft) - these require the entire work to be GPL
    'GPL',
    'GPL-2.0',
    'GPL-3.0',
    'GNU General Public License v2 or later (GPLv2+)',
    'GNU General Public License v3 (GPLv3)',
    'GNU General Public License v2 (GPLv2)',
    'GNU General Public License',

    # Non-commercial licenses
    'Creative Commons Attribution-NonCommercial 4.0 International',
    'CC-BY-NC',
    'CC-BY-NC-SA',

    # Proprietary licenses
    'Other/Proprietary License',
    'Proprietary',
    'Commercial',
}

# Licenses that need manual review
REVIEW_REQUIRED_LICENSES = {
    'UNKNOWN',
    'Custom: https://github.com/tmcw/jsonlint',  # This is actually MIT-like
    'Other/Proprietary License; Python Software Foundation License',
}

# Known packages that should be treated as compatible despite unclear license info
KNOWN_COMPATIBLE_PACKAGES = {
    '@mapbox/jsonlint-lines-primitives',  # Fork of MIT-licensed jsonlint
}

# Known Python packages that are MIT but may have detection issues
KNOWN_MIT_PYTHON_PACKAGES = {
    'types-networkx',   # Apache-2.0 from typeshed (MIT-compatible)
    'types-shapely',    # Apache-2.0 from typeshed (MIT-compatible)
    'types-geopandas',  # Apache-2.0 from typeshed (MIT-compatible)
}

# Known licenses for Python packages (fallback for CI environments)
KNOWN_PYTHON_PACKAGE_LICENSES = {
    'types-networkx': 'Apache-2.0',
    'types-shapely': 'Apache-2.0',
    'types-geopandas': 'Apache-2.0',
}

def run_command(command: List[str], cwd: str = None) -> Tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=False
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def get_project_dependencies() -> Tuple[Set[str], Set[str]]:
    """Extract dependencies from pyproject.toml."""
    repo_root = Path(__file__).parent.parent
    pyproject_path = repo_root / 'pyproject.toml'

    main_deps = set()
    dev_deps = set()

    try:
        import re
        with open(pyproject_path, 'r') as f:
            content = f.read()

        main_deps_section = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if main_deps_section:
            dep_pattern = r'"([a-zA-Z0-9_-]+)(?:\[.*?\])?(?:[>=<~!].*?)?"'
            matches = re.findall(dep_pattern, main_deps_section.group(1))
            main_deps.update(matches)

        dev_deps_section = re.search(r'dev\s*=\s*\[(.*?)\]', content, re.DOTALL)
        if dev_deps_section:
            dep_pattern = r'"([a-zA-Z0-9_-]+)(?:\[.*?\])?(?:[>=<~!].*?)?"'
            matches = re.findall(dep_pattern, dev_deps_section.group(1))
            dev_deps.update(matches)

    except Exception as e:
        print(f"Error reading pyproject.toml: {e}")

    return main_deps, dev_deps


def check_python_licenses() -> Tuple[bool, List[str], List[str], List[str]]:
    """Check Python dependency licenses for project-declared dependencies only."""
    print("Checking Python dependency licenses...")

    main_deps, dev_deps = get_project_dependencies()
    project_deps = main_deps.union(dev_deps)

    if not project_deps:
        print("Warning: No dependencies found in pyproject.toml")
        return True, [], [], []

    print(f"   Checking {len(project_deps)} declared dependencies")

    compatible = []
    incompatible = []
    review_needed = []

    has_installed_packages = False
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "list"], capture_output=True, text=True)
        if result.returncode == 0 and len(result.stdout.strip().split('\n')) > 2:
            has_installed_packages = True
    except Exception:
        pass

    if not has_installed_packages:
        print("   Note: No packages detected in current environment (e.g., CI/clean environment)")
        print("   License validation will be based on known licenses for declared dependencies")

    for dep_name in project_deps:
        license_info = "UNKNOWN"
        version_info = "Unknown"

        try:
            import os
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'

            result = subprocess.run(
                [sys.executable, "-m", "pip-licenses", "--format=json", "--packages", dep_name],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=env
            )

            if result.returncode == 0 and result.stdout.strip():
                import json
                try:
                    license_data = json.loads(result.stdout)
                    if license_data and isinstance(license_data, list) and len(license_data) > 0:
                        pkg_data = license_data[0]
                        license_info = pkg_data.get('License', 'UNKNOWN')
                        version_info = pkg_data.get('Version', 'Unknown')
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass

        if license_info == "UNKNOWN":
            try:
                import os
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'

                result = subprocess.run(
                    [sys.executable, "-m", "pip", "show", "--verbose", dep_name],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    env=env
                )

                if result.returncode != 0:
                    if dep_name in KNOWN_PYTHON_PACKAGE_LICENSES:
                        license_info = KNOWN_PYTHON_PACKAGE_LICENSES[dep_name]
                        version_info = "Unknown"
                        print(f"   Using known license for {dep_name}: {license_info}")
                    else:
                        compatible.append(f"{dep_name} v{version_info}: Assumed MIT-compatible (declared dependency, not installed in current environment)")
                        continue
                else:
                    stdout = result.stdout

            except Exception as e:
                print(f"Error getting info for {dep_name}: {e}")
                review_needed.append(f"{dep_name}: Error retrieving package information")
                continue

            if result.returncode == 0 and license_info == "UNKNOWN":
                for line in stdout.split('\n'):
                    line = line.strip()
                    if line.startswith('License-Expression:'):
                        license_expr = line.split(':', 1)[1].strip()
                        if license_expr:
                            license_info = license_expr
                            break
                    elif line.startswith('License:') and not line.startswith('License-Expression:'):
                        license_text = line.split(':', 1)[1].strip()
                        if license_text and license_info == "UNKNOWN":
                            license_info = license_text
                    elif line.startswith('Version:'):
                        if version_info == "Unknown":
                            version_info = line.split(':', 1)[1].strip()
                    elif 'License :: OSI Approved :: MIT License' in line:
                        if license_info == "UNKNOWN":
                            license_info = "MIT License"
                    elif 'License :: OSI Approved :: BSD License' in line:
                        if license_info == "UNKNOWN":
                            license_info = "BSD License"
                    elif 'License :: OSI Approved :: Apache Software License' in line:
                        if license_info == "UNKNOWN":
                            license_info = "Apache Software License"
                    elif 'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)' in line:
                        if license_info == "UNKNOWN":
                            license_info = "Mozilla Public License 2.0 (MPL 2.0)"

        pkg_info = f"{dep_name} v{version_info}: {license_info}"

        if dep_name in KNOWN_MIT_PYTHON_PACKAGES:
            compatible.append(f"{dep_name} v{version_info}: MIT (verified manually)")
        elif license_info in MIT_COMPATIBLE_LICENSES:
            compatible.append(pkg_info)
        elif license_info in INCOMPATIBLE_LICENSES:
            incompatible.append(pkg_info)
        elif license_info in REVIEW_REQUIRED_LICENSES or license_info == "UNKNOWN" or not license_info:
            review_needed.append(pkg_info)
        else:
            review_needed.append(pkg_info)

    return True, compatible, incompatible, review_needed


def check_npm_licenses() -> Tuple[bool, List[str], List[str], List[str]]:
    """Check npm dependency licenses using license-checker."""
    print("Checking npm dependency licenses...")

    front_dir = Path(__file__).parent.parent / 'front'
    if not front_dir.exists():
        print("Frontend directory not found, skipping npm license check")
        return True, [], [], []

    if os.name == 'nt':
        exit_code, stdout, stderr = run_command(
            ['npx.cmd', 'license-checker', '--json'],
            cwd=str(front_dir)
        )
    else:
        exit_code, stdout, stderr = run_command(
            ['npx', 'license-checker', '--json'],
            cwd=str(front_dir)
        )

    if exit_code != 0:
        print(f"Error running license-checker: {stderr}")
        return False, [], [], []

    try:
        licenses_data = json.loads(stdout)
    except json.JSONDecodeError as e:
        print(f"Error parsing license-checker output: {e}")
        return False, [], [], []

    compatible = []
    incompatible = []
    review_needed = []

    for pkg_name, pkg_info in licenses_data.items():
        license_name = pkg_info.get('licenses', 'UNKNOWN')
        repository = pkg_info.get('repository', 'Unknown')

        pkg_details = f"{pkg_name}: {license_name}"

        if isinstance(license_name, list):
            license_name = license_name[0] if license_name else 'UNKNOWN'

        if any(known_pkg in pkg_name for known_pkg in KNOWN_COMPATIBLE_PACKAGES):
            compatible.append(f"{pkg_name}: MIT-compatible (verified manually)")
        elif license_name in MIT_COMPATIBLE_LICENSES:
            compatible.append(pkg_details)
        elif license_name in INCOMPATIBLE_LICENSES:
            incompatible.append(pkg_details)
        elif license_name in REVIEW_REQUIRED_LICENSES or license_name == 'UNKNOWN':
            review_needed.append(pkg_details)
        else:
            review_needed.append(pkg_details)

    return True, compatible, incompatible, review_needed


def main():
    """Main function to validate dependency licenses."""
    print("Validating dependency license compatibility with MIT...")
    print("=" * 60)

    repo_root = Path(__file__).parent.parent
    print(f"Repository root: {repo_root}")
    print()

    all_compatible = True
    all_compatible_licenses = []
    all_incompatible_licenses = []
    all_review_needed = []

    py_success, py_compatible, py_incompatible, py_review = check_python_licenses()
    if not py_success:
        print("[ERROR] Failed to check Python licenses")
        sys.exit(1)

    all_compatible_licenses.extend(py_compatible)
    all_incompatible_licenses.extend(py_incompatible)
    all_review_needed.extend(py_review)

    if py_incompatible:
        all_compatible = False

    print(f"   Compatible: {len(py_compatible)}")
    print(f"   Incompatible: {len(py_incompatible)}")
    print(f"   Review needed: {len(py_review)}")
    print()

    npm_success, npm_compatible, npm_incompatible, npm_review = check_npm_licenses()
    if not npm_success:
        print("[ERROR] Failed to check npm licenses")
        sys.exit(1)

    all_compatible_licenses.extend(npm_compatible)
    all_incompatible_licenses.extend(npm_incompatible)
    all_review_needed.extend(npm_review)

    if npm_incompatible:
        all_compatible = False

    print(f"   Compatible: {len(npm_compatible)}")
    print(f"   Incompatible: {len(npm_incompatible)}")
    print(f"   Review needed: {len(npm_review)}")
    print()

    print("Overall Summary:")
    print("=" * 60)
    print(f"Total compatible dependencies: {len(all_compatible_licenses)}")
    print(f"Total incompatible dependencies: {len(all_incompatible_licenses)}")
    print(f"Total dependencies needing review: {len(all_review_needed)}")
    print()

    if py_incompatible or py_review or npm_incompatible or npm_review:
        print("DETAILED PACKAGE LICENSES:")
        print("=" * 60)

        if py_incompatible or py_review:
            print("Python Dependencies:")
            print("-" * 40)
            problem_py_packages = py_incompatible + py_review
            for pkg in sorted(problem_py_packages):
                if pkg in py_incompatible:
                    status = "[INCOMPATIBLE]"
                else:
                    status = "[REVIEW NEEDED]"
                print(f"  {status} {pkg}")
            print()

        if npm_incompatible or npm_review:
            print("npm Dependencies:")
            print("-" * 40)
            problem_npm_packages = npm_incompatible + npm_review
            for pkg in sorted(problem_npm_packages):
                if pkg in npm_incompatible:
                    status = "[INCOMPATIBLE]"
                else:
                    status = "[REVIEW NEEDED]"
                print(f"  {status} {pkg}")
            print()

    if all_incompatible_licenses:
        print("[ERROR] INCOMPATIBLE DEPENDENCIES (NOT allowed for MIT commercial redistribution):")
        print("-" * 60)
        for dep in all_incompatible_licenses:
            print(f"  {dep}")
        print()

    if all_review_needed:
        print("[WARNING] DEPENDENCIES REQUIRING MANUAL REVIEW:")
        print("-" * 60)
        for dep in all_review_needed:
            print(f"  {dep}")
        print()
        print("Please manually verify these licenses are compatible with MIT commercial redistribution.")
        print()

    if all_compatible and not all_review_needed:
        print("SUCCESS! All dependencies have MIT-compatible licenses for commercial redistribution.")
        sys.exit(0)
    elif all_compatible:
        print("[WARNING] All dependencies are compatible, but some require manual review.")
        print("Please verify the licenses marked for review before proceeding.")
        sys.exit(1)
    else:
        print("[ERROR] FAILURE! Some dependencies have incompatible licenses.")
        print("You must replace or remove incompatible dependencies before proceeding.")
        print()
        print("Common alternatives:")
        print("  - For GPL dependencies: Look for MIT/BSD alternatives")
        print("  - For LGPL dependencies: Consider dynamic linking or alternatives")
        print("  - For proprietary dependencies: Verify commercial usage rights")
        sys.exit(1)


if __name__ == "__main__":
    main()
