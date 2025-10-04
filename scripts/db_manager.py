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
import argparse
from pathlib import Path
from urllib.parse import urlparse

# Add the back directory to Python path so we can import config
back_dir = Path(__file__).parent.parent / "back"
sys.path.insert(0, str(back_dir))

try:
    from core.config import settings
except ImportError:
    print("ERROR [velosim.db_manager] Could not import settings. Make sure the back/ directory exists and contains core/config.py")
    sys.exit(1)


def parse_database_url(url: str) -> dict:
    """Parse DATABASE_URL into components."""
    parsed = urlparse(url)
    return {
        'host': parsed.hostname or 'localhost',
        'port': parsed.port or 5432,
        'username': parsed.username or 'postgres',
        'password': parsed.password or '',
        'database': parsed.path.lstrip('/') if parsed.path else 'postgres',
    }


def run_command(cmd: list, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a command with proper error handling."""
    print(f"INFO  [velosim.db_manager] Running: {' '.join(cmd)}")
    try:
        # Run commands from the back directory where alembic.ini is located
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture,
            text=True,
            cwd=back_dir
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"ERROR [velosim.db_manager] Command failed: {e}")
        if capture and e.stdout:
            print(f"DEBUG [velosim.db_manager] stdout: {e.stdout}")
        if capture and e.stderr:
            print(f"DEBUG [velosim.db_manager] stderr: {e.stderr}")
        raise


def run_psql_command(sql: str, db_name: str = None) -> bool:
    """Run a PostgreSQL command using the configured database."""
    db_config = parse_database_url(settings.DATABASE_URL)

    # Use specified database or default to postgres for admin operations
    target_db = db_name or db_config['database']

    cmd = [
        'psql',
        '-h', db_config['host'],
        '-p', str(db_config['port']),
        '-U', db_config['username'],
        '-d', target_db,
        '-c', sql
    ]

    # Set password environment variable if provided
    env = os.environ.copy()
    if db_config['password']:
        env['PGPASSWORD'] = db_config['password']

    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"ERROR [velosim.db_manager] SQL command failed: {result.stderr}")
            return False
        return True
    except subprocess.CalledProcessError:
        return False


def seed_database():
    """Seed the database with initial data from all seed files."""
    print("INFO  [velosim.db_manager] Seeding database with initial data...")

    # Check if seeds directory exists
    seeds_dir = back_dir / "alembic" / "seeds"
    if not seeds_dir.exists():
        print(f"ERROR [velosim.db_manager] Seeds directory not found: {seeds_dir}")
        return False

    # Get all .sql files in the seeds directory, sorted alphabetically
    seed_files = sorted(seeds_dir.glob("*.sql"))
    if not seed_files:
        print(f"ERROR [velosim.db_manager] No seed files found in: {seeds_dir}")
        return False

    print(f"INFO  [velosim.db_manager] Found {len(seed_files)} seed file(s): {[f.name for f in seed_files]}")

    db_config = parse_database_url(settings.DATABASE_URL)

    # Set password environment variable if provided
    env = os.environ.copy()
    if db_config['password']:
        env['PGPASSWORD'] = db_config['password']

    # Process each seed file
    for seed_file in seed_files:
        print(f"INFO  [velosim.db_manager] Processing seed file: {seed_file.name}")

        cmd = [
            'psql',
            '-h', db_config['host'],
            '-p', str(db_config['port']),
            '-U', db_config['username'],
            '-d', db_config['database'],
            '-q',  # Quiet mode - suppress most output
            '-f', str(seed_file)
        ]

        try:
            result = subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
            print(f"INFO  [velosim.db_manager] Successfully processed: {seed_file.name}")
        except subprocess.CalledProcessError as e:
            print(f"ERROR [velosim.db_manager] Failed to process {seed_file.name}: {e}")
            if e.stderr:
                print(f"DEBUG [velosim.db_manager] stderr: {e.stderr}")
            return False

    print("INFO  [velosim.db_manager] All seed files processed successfully")
    return True
def drop_database():
    """Drop the target database."""
    db_config = parse_database_url(settings.DATABASE_URL)
    target_db = db_config['database']

    print(f"INFO  [velosim.db_manager] Dropping database: {target_db}")

    # First, terminate all connections to the target database
    terminate_sql = f"""
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = '{target_db}' AND pid <> pg_backend_pid();
    """

    if not run_psql_command(terminate_sql, 'postgres'):
        print("WARN  [velosim.db_manager] Could not terminate connections (database might not exist)")

    # Drop the database
    drop_sql = f"DROP DATABASE IF EXISTS {target_db};"
    if run_psql_command(drop_sql, 'postgres'):
        print(f"INFO  [velosim.db_manager] Database {target_db} dropped successfully")
        return True
    else:
        print(f"ERROR [velosim.db_manager] Failed to drop database {target_db}")
        return False


def create_database():
    """Create the target database."""
    db_config = parse_database_url(settings.DATABASE_URL)
    target_db = db_config['database']

    print(f"INFO  [velosim.db_manager] Creating database: {target_db}")

    create_sql = f"CREATE DATABASE {target_db};"
    if run_psql_command(create_sql, 'postgres'):
        print(f"INFO  [velosim.db_manager] Database {target_db} created successfully")
        return True
    else:
        print(f"ERROR [velosim.db_manager] Failed to create database {target_db}")
        return False


def run_migrations():
    """Run all pending migrations."""
    print("INFO  [velosim.db_manager] Running migrations...")
    try:
        run_command(['alembic', 'upgrade', 'head'])
        print("INFO  [velosim.db_manager] Migrations completed successfully")
        return True
    except subprocess.CalledProcessError:
        print("ERROR [velosim.db_manager] Migrations failed")
        return False


def dropseed():
    """Drop database, recreate, run migrations, and seed data."""
    print("INFO  [velosim.db_manager] Starting database reset (drop + migrate + seed)...")

    # Step 1: Drop database
    if not drop_database():
        return False

    # Step 2: Create database
    if not create_database():
        return False

    # Step 3: Run migrations
    if not run_migrations():
        return False

    # Step 4: Seed database
    if not seed_database():
        return False

    print("INFO  [velosim.db_manager] Database reset completed successfully!")
    return True


def main():
    parser = argparse.ArgumentParser(description='VeloSim Database Management Tool')
    parser.add_argument('command', choices=['seed', 'dropseed', 'drop', 'create', 'migrate'],
                      help='Database operation to perform')

    args = parser.parse_args()

    print(f"INFO  [velosim.db_manager] VeloSim Database Tool - {args.command}")
    print(f"INFO  [velosim.db_manager] Using DATABASE_URL: {settings.DATABASE_URL}")

    success = False

    if args.command == 'seed':
        success = seed_database()
    elif args.command == 'dropseed':
        success = dropseed()
    elif args.command == 'drop':
        success = drop_database()
    elif args.command == 'create':
        success = create_database()
    elif args.command == 'migrate':
        success = run_migrations()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
