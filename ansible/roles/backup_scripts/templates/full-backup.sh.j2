#!/bin/bash
# VeloSim Comprehensive Backup Script
# Creates backups of database, configuration, and logs
# Manages retention policy across all backup types

set -e

# Configuration
BACKUP_BASE_DIR="{{ app_dir }}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$BACKUP_BASE_DIR/backup_${TIMESTAMP}.log"
RETENTION_DAYS={{ backup_retention_days }}

echo "Starting VeloSim backup at $(date)" | tee "$LOG_FILE"

# Ensure all backup directories exist
mkdir -p "$BACKUP_BASE_DIR"/{application,postgresql,ssl,logs}

# Backup database using dedicated script
echo "Backing up PostgreSQL database..." | tee -a "$LOG_FILE"
{{ app_dir }}/scripts/backup-database.sh >> "$LOG_FILE" 2>&1

# Backup SSL certificates if they exist
if [ -d "/etc/letsencrypt" ]; then
    echo "Backing up SSL certificates..." | tee -a "$LOG_FILE"
    tar -czf "$BACKUP_BASE_DIR/ssl/letsencrypt_backup_${TIMESTAMP}.tar.gz" -C /etc letsencrypt
fi

# Backup application configuration files
# These include environment variables and Docker Compose configuration
echo "Backing up application configuration..." | tee -a "$LOG_FILE"
tar -czf "$BACKUP_BASE_DIR/application/config_backup_${TIMESTAMP}.tar.gz" \
    -C {{ app_dir }} \
    .env.prod \
    docker-compose.prod.yml \
    scripts/ \
    --exclude="*.log" >> "$LOG_FILE" 2>&1

# Backup recent application logs (last 7 days)
echo "Backing up recent logs..." | tee -a "$LOG_FILE"
find {{ app_dir }}/logs -name "*.log" -mtime -7 -exec \
    tar -czf "$BACKUP_BASE_DIR/logs/recent_logs_${TIMESTAMP}.tar.gz" {} + 2>/dev/null || true

# Cleanup old backups to prevent disk space issues
echo "Cleaning up old backups..." | tee -a "$LOG_FILE"
find "$BACKUP_BASE_DIR" -name "*_backup_*.tar.gz" -mtime +${RETENTION_DAYS} -delete
find "$BACKUP_BASE_DIR" -name "*_backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

# Generate backup summary for monitoring
echo "Backup completed at $(date)" | tee -a "$LOG_FILE"
echo "Backup summary:" | tee -a "$LOG_FILE"
du -sh "$BACKUP_BASE_DIR"/* | tee -a "$LOG_FILE" 2>/dev/null || true

# Keep only last 10 backup logs to prevent log buildup
cd "$BACKUP_BASE_DIR"
ls -t backup_*.log 2>/dev/null | tail -n +11 | xargs -r rm

echo "Full backup process completed successfully" | tee -a "$LOG_FILE"

# Log to system log for centralized monitoring
echo "$(date): VeloSim backup completed successfully" >> /var/log/velosim/backup.log