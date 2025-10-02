#!/bin/bash
# Migration script for Unix-like systems (macOS, Linux) using direct Alembic commands

set -e

echo "Starting Alembic migration process..."

# Run migration commands
case "$1" in
    "generate")
        if [ -z "$2" ]; then
            echo "❌ Error: Please provide a migration message"
            echo "Usage: $0 generate \"migration message\""
            exit 1
        fi
        echo "📝 Generating new migration: $2"
        alembic revision --autogenerate -m "$2"
        ;;
    "upgrade")
        echo "⬆️  Running migrations..."
        alembic upgrade head
        ;;
    "current"|"status")
        echo "📊 Checking current migration status..."
        alembic current
        ;;
    "downgrade")
        echo "⬇️  Rolling back last migration..."
        alembic downgrade -1
        ;;
    "history")
        echo "📜 Showing migration history..."
        alembic history
        ;;
    "init")
        echo "🏗️  Initializing Alembic..."
        alembic init alembic
        ;;
    "seed")
        echo "🌱 Seeding database with initial data..."
        psql -h localhost -p 5433 -U velosim -d velosim -f alembic/seeds/stations.sql
        if [ $? -eq 0 ]; then
            echo "✅ Database seeded successfully"
        else
            echo "❌ Database seeding failed"
            exit 1
        fi
        ;;
    *)
        echo "Usage: $0 {current|generate|upgrade|downgrade|history|init|seed|status}"
        echo ""
        echo "Commands:"
        echo "  current          - Check current migration status"
        echo "  generate \"msg\"   - Generate new migration"
        echo "  upgrade          - Run pending migrations"
        echo "  downgrade        - Rollback last migration"
        echo "  history          - Show migration history"
        echo "  init             - Initialize Alembic"
        echo "  seed             - Seed database with initial station data"
        echo "  status           - Alias for current"
        echo ""
        echo "Examples:"
        echo "  $0 current"
        echo "  $0 generate \"Add stations table\""
        echo "  $0 upgrade"
        echo "  $0 seed"
        ;;
esac
