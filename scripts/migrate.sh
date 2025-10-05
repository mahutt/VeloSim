#!/bin/bash
# Migration script for Unix-like systems (macOS, Linux) using direct Alembic commands

set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

# Change to back directory where alembic.ini is located
cd "$SCRIPT_DIR/../back"

echo "INFO  [velosim.migrate] Starting Alembic migration process..."

# Run migration commands
case "$1" in
    "generate")
        if [ -z "$2" ]; then
            echo "ERROR [velosim.migrate] Please provide a migration message"
            echo "Usage: $0 generate \"migration message\""
            exit 1
        fi
        echo "INFO  [velosim.migrate] Generating new migration: $2"
        alembic revision --autogenerate -m "$2"
        ;;
    "upgrade")
        echo "INFO  [velosim.migrate] Running migrations..."
        alembic upgrade head
        ;;
    "current"|"status")
        echo "INFO  [velosim.migrate] Checking current migration status..."
        alembic current
        ;;
    "downgrade")
        echo "INFO  [velosim.migrate] Rolling back last migration..."
        alembic downgrade -1
        ;;
    "history")
        echo "INFO  [velosim.migrate] Showing migration history..."
        alembic history
        ;;
    "init")
        echo "INFO  [velosim.migrate] Initializing Alembic..."
        alembic init alembic
        ;;
    "seed")
        echo "INFO  [velosim.migrate] Seeding database with initial data..."
        python "$SCRIPT_DIR/db_manager.py" seed
        if [ $? -eq 0 ]; then
            echo "INFO  [velosim.migrate] Database seeded successfully"
        else
            echo "ERROR [velosim.migrate] Database seeding failed"
            exit 1
        fi
        ;;
    "dropseed")
        echo "INFO  [velosim.migrate] Dropping database, running migrations, and seeding..."
        python "$SCRIPT_DIR/db_manager.py" dropseed
        if [ $? -eq 0 ]; then
            echo "INFO  [velosim.migrate] Database reset completed successfully"
        else
            echo "ERROR [velosim.migrate] Database reset failed"
            exit 1
        fi
        ;;
    *)
        echo "Usage: $0 {current|generate|upgrade|downgrade|history|init|seed|dropseed|status}"
        echo ""
        echo "Commands:"
        echo "  current          - Check current migration status"
        echo "  generate \"msg\"   - Generate new migration"
        echo "  upgrade          - Run pending migrations"
        echo "  downgrade        - Rollback last migration"
        echo "  history          - Show migration history"
        echo "  init             - Initialize Alembic"
        echo "  seed             - Seed database with initial station data"
        echo "  dropseed         - Drop database, run migrations, and seed data"
        echo "  status           - Alias for current"
        echo ""
        echo "Examples:"
        echo "  $0 current"
        echo "  $0 generate \"Add stations table\""
        echo "  $0 upgrade"
        echo "  $0 seed"
        ;;
esac
