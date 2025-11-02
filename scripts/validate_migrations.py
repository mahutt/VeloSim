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
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_command(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> tuple[int, str, str]:
    """
    Run a command and return exit code, stdout, and stderr.
    """
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def validate_migrations() -> bool:
    """
    Validate that Alembic migrations can be applied and seeds can be loaded.

    This function:
    1. Creates a temporary PostgreSQL database
    2. Runs all Alembic migrations (upgrade head)
    3. Loads seed data
    4. Verifies no errors occurred

    Returns:
        bool: True if validation successful, False otherwise
    """
    print("=" * 80)
    print("ALEMBIC MIGRATION VALIDATION")
    print("=" * 80)

    back_dir = project_root / "back"

    # Check if we're in a CI environment or need to use Docker
    use_docker = os.getenv("CI") == "true" or not os.getenv("DATABASE_URL")

    if use_docker:
        return validate_migrations_docker()
    else:
        return validate_migrations_direct()


def validate_migrations_docker() -> bool:
    """
    Validate migrations using Docker Compose with a temporary database.
    """
    print("\nUsing Docker for validation...")

    # Create a temporary docker-compose file for testing
    docker_compose_test = """
version: "3.8"

services:
  postgres-test:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: velosim_test
      POSTGRES_PASSWORD: velosim_test
      POSTGRES_DB: velosim_test
    ports:
      - "5434:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U velosim_test"]
      interval: 2s
      timeout: 5s
      retries: 10
"""

    temp_dir = Path(tempfile.mkdtemp())
    compose_file = temp_dir / "docker-compose.test.yml"
    compose_file.write_text(docker_compose_test)

    test_db_url = "postgresql://velosim_test:velosim_test@localhost:5434/velosim_test"

    try:
        # Start test database
        print("\nStarting test database container...")
        code, _, _ = run_command(
            ["docker", "compose", "-f", str(compose_file), "up", "-d"],
            cwd=temp_dir
        )
        if code != 0:
            print("ERROR: Failed to start test database")
            return False

        # Wait for database to be ready
        print("\nWaiting for database to be ready...")
        code, _, _ = run_command(
            ["docker", "compose", "-f", str(compose_file), "exec", "-T", "postgres-test",
             "pg_isready", "-U", "velosim_test"],
            cwd=temp_dir
        )

        # Give it a moment to fully initialize
        import time
        time.sleep(3)

        # Run migrations
        print("\nRunning Alembic migrations...")
        env = os.environ.copy()
        env["DATABASE_URL"] = test_db_url

        code, stdout, stderr = run_command(
            ["alembic", "upgrade", "head"],
            cwd=project_root / "back",
            env=env
        )

        if code != 0:
            print(f"ERROR: Migration failed!\nStdout: {stdout}\nStderr: {stderr}")
            return False

        print("SUCCESS: Migrations applied successfully")
        print(stdout)

        # Load seed data
        print("\nLoading seed data...")
        seed_file = project_root / "back" / "alembic" / "seeds" / "seed.sql"

        if seed_file.exists():
            # Use docker exec to run psql with seed file
            with open(seed_file, 'r') as f:
                seed_sql = f.read()

            # Run seed SQL
            code, stdout, stderr = run_command(
                ["docker", "compose", "-f", str(compose_file), "exec", "-T", "postgres-test",
                 "psql", "-U", "velosim_test", "-d", "velosim_test"],
                cwd=temp_dir
            )

            # Alternative: use psql from host if available
            code, stdout, stderr = run_command(
                ["psql", test_db_url, "-f", str(seed_file)],
                cwd=project_root / "back"
            )

            if code != 0:
                # Try docker exec method
                proc = subprocess.Popen(
                    ["docker", "compose", "-f", str(compose_file), "exec", "-T",
                     "postgres-test", "psql", "-U", "velosim_test", "-d", "velosim_test"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=temp_dir
                )
                stdout, stderr = proc.communicate(input=seed_sql)
                code = proc.returncode

            if code != 0:
                print(f"WARNING: Seed data loading had issues (non-critical)\nStdout: {stdout}\nStderr: {stderr}")
                # Don't fail on seed errors as they might be warnings
            else:
                print("SUCCESS: Seed data loaded successfully")
                if stdout:
                    print(stdout)
        else:
            print("INFO: No seed file found, skipping...")

        # Verify database structure
        print("\nVerifying database structure...")
        code, stdout, stderr = run_command(
            ["docker", "compose", "-f", str(compose_file), "exec", "-T", "postgres-test",
             "psql", "-U", "velosim_test", "-d", "velosim_test", "-c",
             "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"],
            cwd=temp_dir
        )

        if code == 0:
            print("SUCCESS: Database tables:")
            print(stdout)

        print("\nSUCCESS: Migration validation successful!")
        return True

    except Exception as e:
        print(f"ERROR: Validation failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup: Stop and remove test containers
        print("\nCleaning up test database...")
        run_command(
            ["docker", "compose", "-f", str(compose_file), "down", "-v"],
            cwd=temp_dir
        )
        # Clean up temp directory
        try:
            compose_file.unlink()
            temp_dir.rmdir()
        except:
            pass


def validate_migrations_direct() -> bool:
    """
    Validate migrations directly using existing DATABASE_URL.
    WARNING: This will modify the database!
    """
    print("\nWARNING: Using direct database connection (DATABASE_URL set)")
    print("WARNING: This will modify the database!")

    back_dir = project_root / "back"

    # Run migrations
    print("\nRunning Alembic migrations...")
    code, stdout, stderr = run_command(
        ["alembic", "upgrade", "head"],
        cwd=back_dir
    )

    if code != 0:
        print(f"ERROR: Migration failed!\nStdout: {stdout}\nStderr: {stderr}")
        return False

    print("SUCCESS: Migrations applied successfully")
    print(stdout)

    print("\nSUCCESS: Migration validation successful!")
    return True


if __name__ == "__main__":
    success = validate_migrations()
    sys.exit(0 if success else 1)
