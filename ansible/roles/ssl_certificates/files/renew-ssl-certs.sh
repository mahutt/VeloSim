#!/bin/bash
# SSL Certificate Renewal Script for VeloSim
# Automatically renews Let's Encrypt certificates and reloads Nginx
# Includes dry-run testing to prevent service disruption

set -e

echo "$(date): Starting SSL certificate renewal check..."

# Test renewal first to catch any configuration issues
if certbot renew --dry-run --quiet; then
    echo "$(date): Dry run successful, proceeding with actual renewal..."
    
    # Perform actual renewal
    # --quiet suppresses normal output, --post-hook runs after successful renewal
    certbot renew --quiet --post-hook "systemctl reload nginx"
    
    echo "$(date): SSL certificate renewal completed successfully"
else
    echo "$(date): ERROR - SSL certificate renewal dry run failed!"
    # Log to system for alerting
    logger "VeloSim SSL renewal dry run failed"
    exit 1
fi