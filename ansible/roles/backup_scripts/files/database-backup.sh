#!/bin/bash
# VeloSim Database Backup Script
# Creates compressed PostgreSQL backups with timestamp naming
# Maintains retention policy to prevent disk space issues

set -e

# Configuration
BACKUP_DIR="{{ app_dir }}/backups/postgresql"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="velosim_backup_${TIMESTAMP}.sql"
RETENTION_DAYS={{ backup_retention_days }}

echo "Starting PostgreSQL backup at $(date)"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Create backup using docker exec
# This connects to the running PostgreSQL container and dumps the database
docker exec velosim-postgres pg_dump -U {{ postgres_user }} -d {{ postgres_db }} > "${BACKUP_DIR}/${BACKUP_FILE}"

# Compress the backup to save space
gzip "${BACKUP_DIR}/${BACKUP_FILE}"

# Remove backups older than retention period
# This prevents the backup directory from growing indefinitely
find "${BACKUP_DIR}" -name "velosim_backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
echo "Backup size: $(du -h "${BACKUP_DIR}/${BACKUP_FILE}.gz" | cut -f1)"

# Log backup completion for monitoring
echo "$(date): Database backup completed successfully" >> /var/log/velosim/backup.log