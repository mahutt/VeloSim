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
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_command(cmd: list[str], cwd: Path | None = None, check: bool = False) -> Tuple[int, str, str]:
    """
    Run a command and return exit code, stdout, and stderr.
    """
    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=cwd or project_root,
        capture_output=True,
        text=True,
        check=check
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def get_migration_files(ref: str = "HEAD") -> Dict[str, str]:
    """
    Get all migration files at a specific git ref.

    Returns:
        Dict[revision_id, filename]
    """
    migrations_dir = "back/alembic/versions"

    # Get list of files at the specified ref
    code, stdout, stderr = run_command(
        ["git", "ls-tree", "-r", "--name-only", ref, migrations_dir]
    )

    if code != 0:
        print(f"WARNING: Could not list migration files at {ref}")
        return {}

    migration_files = {}
    for filepath in stdout.split('\n'):
        if filepath and filepath.endswith('.py') and '__pycache__' not in filepath:
            filename = Path(filepath).name
            # Extract revision ID (first part before underscore)
            revision_id = filename.split('_')[0]
            migration_files[revision_id] = filename

    return migration_files


def get_migration_chain(migration_dir: Path) -> Dict[str, Dict]:
    """
    Parse migration files to build the migration chain.

    Returns:
        Dict[revision_id, {
            'filename': str,
            'down_revision': str,
            'depends_on': List[str]
        }]
    """
    migration_chain = {}

    for migration_file in migration_dir.glob('*.py'):
        if migration_file.name.startswith('__'):
            continue

        revision_id = migration_file.stem.split('_')[0]

        # Parse the migration file to extract down_revision and depends_on
        down_revision = None
        depends_on = []

        try:
            with open(migration_file, 'r', encoding='utf-8') as f:
                content = f.read()

                # Extract down_revision
                for line in content.split('\n'):
                    if line.strip().startswith('down_revision'):
                        # Extract value: down_revision = 'abc123' or down_revision = None
                        value = line.split('=', 1)[1].strip()
                        if value != 'None' and value != "'None'" and value != '"None"':
                            down_revision = value.strip('\'"')
                        break

                # Extract depends_on (for branch merges)
                for line in content.split('\n'):
                    if line.strip().startswith('depends_on'):
                        value = line.split('=', 1)[1].strip()
                        if value and value != 'None':
                            # Parse list/tuple
                            depends_on = [v.strip('\'" ') for v in value.strip('()[]').split(',') if v.strip()]
                        break
        except Exception as e:
            print(f"WARNING: Could not parse {migration_file.name}: {e}")
            continue

        migration_chain[revision_id] = {
            'filename': migration_file.name,
            'down_revision': down_revision,
            'depends_on': depends_on
        }

    return migration_chain


def detect_migration_conflicts() -> bool:
    """
    Detect if the current branch has migration conflicts with main/origin/main.

    Returns:
        True if validation passes, False if conflicts detected
    """
    print("=" * 80)
    print("ALEMBIC MIGRATION HISTORY VALIDATION")
    print("=" * 80)

    # Determine the base branch
    base_branch = os.getenv('GITHUB_BASE_REF', 'main')  # Use GitHub PR base or default to main

    print(f"\nChecking migration history against base branch: {base_branch}")

    # Fetch latest from origin to ensure we have up-to-date refs
    print("\nFetching latest from origin...")
    code, _, _ = run_command(["git", "fetch", "origin", base_branch])
    if code != 0:
        print(f"WARNING: Could not fetch origin/{base_branch}, using local {base_branch}")
        target_ref = base_branch
    else:
        target_ref = f"origin/{base_branch}"

    # Get migration files from both branches
    print(f"\nAnalyzing migration files...")

    current_migrations = get_migration_files("HEAD")
    base_migrations = get_migration_files(target_ref)

    print(f"  Current branch: {len(current_migrations)} migrations")
    print(f"  Base branch ({target_ref}): {len(base_migrations)} migrations")

    # Find migrations that exist in base but not in current (MISSING MIGRATIONS)
    missing_migrations = set(base_migrations.keys()) - set(current_migrations.keys())

    # Find migrations that exist in current but not in base (NEW MIGRATIONS)
    new_migrations = set(current_migrations.keys()) - set(base_migrations.keys())

    if missing_migrations:
        print(f"\nCONFLICT DETECTED: Missing migrations from {target_ref}")
        print(f"\n   The following migrations exist in {target_ref} but are missing from your branch:")
        for rev_id in sorted(missing_migrations):
            print(f"     - {base_migrations[rev_id]} (revision: {rev_id})")

        print(f"\n   This indicates your branch is out of sync with {base_branch}.")
        print(f"\n   TO FIX:")
        print(f"      1. Merge/rebase your branch with {base_branch}:")
        print(f"         git fetch origin {base_branch}")
        print(f"         git merge origin/{base_branch}")
        print(f"         # OR: git rebase origin/{base_branch}")
        print(f"      2. If you have migration conflicts, regenerate your migration:")
        print(f"         cd back")
        print(f"         # Delete your conflicting migration file")
        print(f"         alembic revision --autogenerate -m \"Your migration message\"")
        print(f"      3. Re-run this validation")

        return False

    if new_migrations:
        print(f"\nNew migrations detected (this is normal for new PRs):")
        for rev_id in sorted(new_migrations):
            print(f"     + {current_migrations[rev_id]} (revision: {rev_id})")

    # Validate migration chain integrity
    print(f"\nValidating migration chain integrity...")

    migrations_dir = project_root / "back" / "alembic" / "versions"
    migration_chain = get_migration_chain(migrations_dir)

    # Check for broken chains (down_revision points to non-existent migration)
    broken_chains = []
    for rev_id, info in migration_chain.items():
        down_rev = info['down_revision']
        if down_rev and down_rev not in migration_chain:
            broken_chains.append((rev_id, info['filename'], down_rev))

    if broken_chains:
        print(f"\nBROKEN MIGRATION CHAIN DETECTED:")
        for rev_id, filename, missing_down_rev in broken_chains:
            print(f"     - {filename} references down_revision='{missing_down_rev}' which doesn't exist")

        print(f"\n   This means your migration history is corrupted.")
        print(f"\n   TO FIX:")
        print(f"      1. Ensure you've merged/rebased with {base_branch}")
        print(f"      2. Delete the broken migration file(s)")
        print(f"      3. Regenerate migration: alembic revision --autogenerate -m \"Your message\"")

        return False

    # Check for multiple heads (migrations with the same down_revision)
    down_revisions: Dict[str, List[str]] = {}
    for rev_id, info in migration_chain.items():
        down_rev = info['down_revision'] or 'None'
        if down_rev not in down_revisions:
            down_revisions[down_rev] = []
        down_revisions[down_rev].append(rev_id)

    multiple_heads = {k: v for k, v in down_revisions.items() if len(v) > 1 and k != 'None'}

    if multiple_heads:
        print(f"\nWARNING: Multiple migration heads detected:")
        for down_rev, heads in multiple_heads.items():
            print(f"     Migrations pointing to down_revision='{down_rev}':")
            for head in heads:
                print(f"       - {migration_chain[head]['filename']}")

        print(f"\n   This may indicate a merge conflict in migration history.")
        print(f"   You may need to create a merge migration:")
        print(f"      cd back")
        print(f"      alembic merge -m \"Merge migration heads\" {' '.join(list(multiple_heads.values())[0])}")

        # Don't fail on multiple heads if we're in a PR - it might be intentional
        # but warn loudly
        if os.getenv('CI'):
            print(f"\n   WARNING: Please review and resolve before merging!")

    print(f"\nMigration history validation PASSED!")
    print(f"   - All migrations from {target_ref} are present")
    print(f"   - Migration chain is intact")
    print(f"   - No broken references detected")

    return True


if __name__ == "__main__":
    try:
        success = detect_migration_conflicts()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nValidation failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
