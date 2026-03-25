# VeloSim Production Deployment Guide

This guide provides instructions for deploying VeloSim to production using Ansible.

## Prerequisites

### Control Machine (Your Local Machine)
- Ansible 2.15+
- Python 3.8+
- SSH client

### Target Server
- Ubuntu 24.04 LTS
- Minimum 4GB RAM, 2 CPU cores, 20GB storage
- SSH access with sudo privileges
- Public IP address
- Domain name pointing to the server (for SSL)

## Quick Start

### 1. Clone and Setup

```bash
cd VeloSim/ansible
```

### 2. Configure Inventory

Edit `inventories/production`:

```ini
[velosim_servers]
velosim-prod-01 ansible_host=YOUR_SERVER_IP

[velosim_servers:vars]
ansible_user=ubuntu
ansible_ssh_private_key_file=~/.ssh/your_deploy_key
```

### 3. Configure Variables

Edit `group_vars/all.yml`:

```yaml
# Update these values
domain_name: "your-domain.com"
certbot_email: "admin@your-domain.com"

# Add your team members
velosim_users:
  - username: "admin"
    github_username: "your-github-username"
    sudo: true
  - username: "githubactions"
    github_username: "deployment-user-github"
    sudo: true
```

### 4. Deploy

```bash
# Run the complete deployment
ansible-playbook -i inventories/production deploy.yml

# You will be prompted for:
# - PostgreSQL password: This creates the application database user password
#   (not the postgres superuser, but the 'velosim' application user)

# Or run specific components
ansible-playbook -i inventories/production deploy.yml --tags "security,users"
ansible-playbook -i inventories/production deploy.yml --tags "application"
```

## Internal Services Access

Some services are configured for internal access only via SSH tunnels for security:

### Grafana Dashboard
```bash
# Create SSH tunnel
ssh -L 3001:localhost:3001 user@your-server

# Access Grafana at http://localhost:3001
# Login: admin / (password set in vault_grafana_password)
```

### PostgreSQL Direct Access
```bash
# Create SSH tunnel for database access
ssh -L 5432:localhost:5432 user@your-server

# Connect using local tools
psql -h localhost -p 5432 -U velosim -d velosim
```

## Configuration Details

### User Management

The playbook automatically:
- Downloads SSH keys from GitHub for each user
- Creates users with appropriate permissions
- Configures passwordless sudo for admin users
- Adds users to necessary groups (docker, ssh-users, sudo)

### Security Features

- SSH hardening with key-only authentication
- UFW firewall configured (SSH, HTTP, HTTPS only)
- Fail2ban for SSH protection
- Automatic security updates
- SSL certificates with auto-renewal

### Application Stack

- **Frontend**: React app served via Nginx
- **Backend**: FastAPI served via Docker
- **Database**: PostgreSQL in Docker container
- **Routing**: GraphHopper server for routing calculations
- **Proxy**: Nginx reverse proxy with SSL termination
- **Monitoring**: Optional Grafana dashboard

## GitHub Actions Deployment

### Setup Secrets

Configure these secrets in your GitHub repository:

```
DEPLOY_SSH_KEY: Private key for deployment user
DEPLOY_HOST: Server IP address
DEPLOY_USER: Username (usually 'githubactions')
DATABASE_URL: PostgreSQL connection string
DOMAIN_NAME: Your domain name (optional)
```

### SSH Key Generation

```bash
# On your local machine
ssh-keygen -t ed25519 -C "githubactions@velosim" -f ~/.ssh/velosim_deploy_key

# Add public key to GitHub user's keys (the user specified in velosim_users)
cat ~/.ssh/velosim_deploy_key.pub

# Add private key to GitHub Secrets as DEPLOY_SSH_KEY
cat ~/.ssh/velosim_deploy_key
```

### Automatic Deployment

The workflow triggers on pushes to main branch and:
1. Creates a backup of current state
2. Pulls latest code
3. Runs database migrations
4. Rebuilds and restarts services
5. Performs health checks
6. Rolls back on failure

## Directory Structure

After deployment, the server will have:

```
/opt/velosim/
├── source/                 # Git repository
├── docker-compose.prod.yml # Production Docker Compose
├── .env.prod              # Environment variables
├── graphhopper-data/       # GraphHopper routing data
├── logs/                  # Application logs
├── backups/               # Automated backups
│   ├── postgresql/        # Database backups
│   ├── ssl/               # SSL certificate backups
│   └── application/       # Application config backups
└── scripts/               # Management scripts
    ├── velosim-app.sh     # App management
    ├── backup-database.sh # Database backup
    ├── restore-database.sh# Database restore
    └── full-backup.sh     # Complete backup
```

## Management Commands

### Application Management

```bash
# Start/stop/restart application
sudo -u velosim /opt/velosim/scripts/velosim-app.sh start
sudo -u velosim /opt/velosim/scripts/velosim-app.sh stop
sudo -u velosim /opt/velosim/scripts/velosim-app.sh restart

# Check status
sudo -u velosim /opt/velosim/scripts/velosim-app.sh status

# View logs
sudo -u velosim /opt/velosim/scripts/velosim-app.sh logs
sudo -u velosim /opt/velosim/scripts/velosim-app.sh logs backend

# Update application
sudo -u velosim /opt/velosim/scripts/velosim-app.sh update
```

### Database Management

```bash
# Create backup
sudo -u velosim /opt/velosim/scripts/backup-database.sh

# Restore from backup
sudo -u velosim /opt/velosim/scripts/restore-database.sh backup_file.sql.gz

# View backup status
sudo -u velosim /opt/velosim/scripts/backup-status.sh
```

### SSL Certificate Management

```bash
# Check certificate status
sudo /usr/local/bin/check-ssl-certs.sh

# Manual renewal (if needed)
sudo certbot renew

# Test renewal
sudo certbot renew --dry-run
```

## Monitoring and Maintenance

### Health Checks

- **Application**: `https://your-domain.com/health`
- **Grafana**: `https://your-domain.com/grafana/` (admin:admin)

### Log Locations

- **Application logs**: `/opt/velosim/logs/`
- **Nginx logs**: `/var/log/nginx/your-domain.com/`
- **Docker logs**: `docker-compose -f /opt/velosim/docker-compose.prod.yml logs`

### Automated Backups

- Database backups: Daily at 2:00 AM
- Retention: 7 days
- Location: `/opt/velosim/backups/`

## Troubleshooting

### Common Issues

1. **Services not starting**: Check Docker logs and ensure sufficient disk space
2. **SSL certificate issues**: Verify domain DNS and run certbot manually
3. **Database connection issues**: Check PostgreSQL container status and credentials
4. **Permission issues**: Ensure velosim user has proper ownership of app directory

### Support Commands

```bash
# Check all services
docker-compose -f /opt/velosim/docker-compose.prod.yml ps

# Check system resources
htop
df -h
docker system df

# Check firewall status
sudo ufw status

# Check SSL certificate expiration
sudo /usr/local/bin/check-ssl-certs.sh

# View recent logs
sudo journalctl -u velosim -f
```

## 💾 Backup & Recovery

VeloSim includes comprehensive automated backup systems for production deployments, ensuring data safety and disaster recovery capabilities.

### What Gets Backed Up

| Component | Frequency | Retention | Location | Format |
|-----------|-----------|-----------|----------|---------|
| **PostgreSQL Database** | Daily at 2:00 AM | 7 days | `/opt/velosim/backups/postgresql/` | Compressed SQL dumps (`.sql.gz`) |
| **SSL Certificates** | Daily at 2:00 AM | 7 days | `/opt/velosim/backups/ssl/` | Tar archives (`.tar.gz`) |
| **Application Configuration** | Daily at 2:00 AM | 7 days | `/opt/velosim/backups/application/` | Tar archives (`.tar.gz`) |
| **Recent Application Logs** | Daily at 2:00 AM | 7 days | `/opt/velosim/backups/logs/` | Tar archives (`.tar.gz`) |

### Backup Scripts

The deployment includes three automated backup scripts:

#### Database-Only Backup
```bash
# Run database backup manually
/opt/velosim/scripts/backup-database.sh
```
- Creates timestamped PostgreSQL dump
- Compresses with gzip to save space
- Automatically removes backups older than 7 days

#### Full System Backup
```bash
# Run comprehensive backup manually
/opt/velosim/scripts/full-backup.sh
```
- Executes database backup
- Backs up SSL certificates (`/etc/letsencrypt`)
- Archives configuration files (`.env.prod`, `docker-compose.prod.yml`, scripts)
- Archives recent logs (last 7 days)
- Generates backup summary report

#### Backup Monitoring
```bash
# Check backup status and health
/opt/velosim/scripts/backup-status.sh
```
- Verifies recent backups exist
- Reports backup sizes and ages
- Checks available disk space
- Provides backup health summary

### Backup Configuration

Configure backup settings in `ansible/group_vars/all.yml`:

```yaml
# Backup Configuration
backup_retention_days: 7        # How many days to keep backups
backup_schedule_hour: 2         # Hour to run daily backups (0-23)
backup_schedule_minute: 0       # Minute to run daily backups (0-59)
```

### Automated Scheduling

Backups run automatically via cron:
- **Schedule**: Daily at 2:00 AM server time
- **User**: `velosim` application user
- **Command**: `/opt/velosim/scripts/full-backup.sh`

Check cron status:
```bash
# View scheduled backup job
crontab -u velosim -l

# Check recent backup execution logs
tail -f /var/log/velosim/backup.log
```

### Restore Procedures

#### Database Restore

1. **List Available Backups**:
   ```bash
   ls -la /opt/velosim/backups/postgresql/
   ```

2. **Restore from Backup**:
   ```bash
   /opt/velosim/scripts/restore-database.sh velosim_backup_20241116_020000.sql.gz
   ```
   - Prompts for confirmation before proceeding
   - Automatically stops application services during restore
   - Restarts services after successful restore

#### Full System Restore

1. **Stop Application Services**:
   ```bash
   cd /opt/velosim
   docker-compose -f docker-compose.prod.yml down
   ```

2. **Restore Database** (see above)

3. **Restore Configuration Files**:
   ```bash
   cd /opt/velosim/backups/application
   tar -xzf config_backup_20241116_020000.tar.gz -C /opt/velosim/
   ```

4. **Restore SSL Certificates** (if needed):
   ```bash
   sudo tar -xzf /opt/velosim/backups/ssl/letsencrypt_backup_20241116_020000.tar.gz -C /etc/
   ```

5. **Restart Application**:
   ```bash
   cd /opt/velosim
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Monitoring Backup Health

#### Check Backup Status
```bash
# Quick status check
/opt/velosim/scripts/backup-status.sh

# View backup logs
tail -f /var/log/velosim/backup.log

# Check backup directory size
du -sh /opt/velosim/backups/
```

#### Backup Alerts

Monitor these conditions for backup health:
- ✅ **Healthy**: Recent backup exists (< 25 hours old)
- ⚠️ **Warning**: No backup in last 25 hours
- ❌ **Critical**: No backup in last 48 hours
- 💾 **Disk Space**: Monitor backup directory size vs. available space

### Disaster Recovery

#### Complete System Recovery

1. **Deploy Fresh Instance** using Ansible playbooks
2. **Stop Services** before restoring data
3. **Restore Database** from most recent backup
4. **Restore Configuration** and SSL certificates
5. **Verify Application** functionality and data integrity
6. **Update DNS** if IP address changed

### Best Practices

1. **Test Restores Regularly**: Verify backup integrity by testing restore procedures
2. **Monitor Disk Space**: Ensure adequate space for backups and database growth
3. **Off-Site Backups**: Consider copying backups to external storage for disaster recovery
4. **Backup Verification**: Check backup logs and run status scripts regularly
5. **Documentation**: Keep recovery procedures updated and accessible

## 🗂️ Log Management & Rotation

VeloSim production deployments include automated log rotation to prevent disk space issues and maintain system performance.

### Log Rotation Configuration

#### System Logs (`/var/log/velosim/`)
```bash
# Rotation policy for system logs
/var/log/velosim/*.log {
    daily          # Rotate daily
    missingok      # Don't error if log file is missing
    rotate 30      # Keep 30 days of rotated logs
    compress       # Compress rotated logs
    delaycompress  # Compress on next rotation (not current)
    notifempty     # Don't rotate empty files
    copytruncate   # Copy and truncate original (for active logs)
    create 644 velosim velosim  # Create new log with these permissions
}
```

#### Application Logs (`/opt/velosim/logs/`)
```bash
# Rotation policy for application logs
/opt/velosim/logs/*.log {
    daily          # Rotate daily
    missingok      # Don't error if log file is missing
    rotate 7       # Keep 7 days of rotated logs
    compress       # Compress rotated logs
    delaycompress  # Compress on next rotation
    notifempty     # Don't rotate empty files
    copytruncate   # Copy and truncate original
    create 644 velosim velosim  # Create new log with these permissions
}
```

### Log Types and Locations

| Log Type | Location | Retention | Description |
|----------|----------|-----------|-------------|
| **System Logs** | `/var/log/velosim/` | 30 days | Deployment, backup, and system events |
| **Application Logs** | `/opt/velosim/logs/` | 7 days | FastAPI backend, simulation engine |
| **Docker Container Logs** | Docker logging | 10MB × 3 files | Container stdout/stderr |
| **Nginx Access/Error** | `/var/log/nginx/` | 30 days | Web server requests and errors |
| **PostgreSQL Logs** | Container logs | 10MB × 3 files | Database queries and errors |

### Docker Container Logging

Production containers use JSON file logging with rotation:
```yaml
services:
  postgres:
    logging:
      driver: json-file
      options:
        max-size: "10m"    # Rotate at 10MB
        max-file: "3"      # Keep 3 files (30MB total)
```

### Log Management Commands

```bash
# Check log rotation status
sudo logrotate -d /etc/logrotate.d/velosim

# Force log rotation (testing)
sudo logrotate -f /etc/logrotate.d/velosim

# View recent application logs
tail -f /opt/velosim/logs/*.log

# View Docker container logs
docker logs velosim-backend --tail 100 -f
docker logs velosim-postgres --tail 100 -f

# Check log disk usage
du -sh /opt/velosim/logs/
du -sh /var/log/velosim/
```

### Monitoring Log Health

Monitor these log-related metrics:
- 📁 **Disk usage** of log directories
- 🔄 **Rotation frequency** and success
- 📈 **Log growth rate** to adjust retention
- ⚠️ **Error patterns** in application logs


### Production Management Commands

```bash
# Deployment
ansible-playbook -i inventories/production deploy.yml

# Service management
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml logs -f
docker-compose -f docker-compose.prod.yml restart backend

# Backup and restore
/opt/velosim/scripts/full-backup.sh
/opt/velosim/scripts/backup-status.sh
/opt/velosim/scripts/restore-database.sh backup_file.sql.gz

# Log management
tail -f /opt/velosim/logs/*.log
docker logs velosim-backend -f
sudo logrotate -f /etc/logrotate.d/velosim
```
