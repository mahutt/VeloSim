#!/bin/bash
# VeloSim Database Restore Script
# Restores PostgreSQL database from compressed backup files
# Includes safety checks and service management

set -e

BACKUP_DIR="{{ app_dir }}/backups/postgresql"
APP_DIR="{{ app_dir }}"

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo "Available backups:"
    ls -la "$BACKUP_DIR"
    exit 1
fi

BACKUP_FILE="$1"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

if [ ! -f "$BACKUP_PATH" ]; then
    echo "Backup file not found: $BACKUP_PATH"
    exit 1
fi

echo "Restoring from backup: $BACKUP_FILE"
echo "WARNING: This will replace all data in the database!"
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled"
    exit 1
fi

# Stop application containers to prevent data corruption during restore
echo "Stopping application services..."
cd "$APP_DIR"
docker-compose -f docker-compose.prod.yml stop backend frontend

# Restore database from compressed backup
echo "Restoring database..."
gunzip -c "$BACKUP_PATH" | docker exec -i velosim-postgres psql -U {{ postgres_user }} -d {{ postgres_db }}

# Restart application containers
echo "Restarting application services..."
docker-compose -f docker-compose.prod.yml start backend frontend

echo "Database restore completed successfully"
echo "$(date): Database restored from $BACKUP_FILE" >> /var/log/velosim/backup.log