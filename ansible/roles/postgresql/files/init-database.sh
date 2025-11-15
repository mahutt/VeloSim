#!/bin/bash
# PostgreSQL initialization script for VeloSim production
# Enables required extensions and sets up permissions
# This script runs when the PostgreSQL container starts for the first time

set -e

# Create database if it doesn't exist and enable extensions
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Enable UUID extension for generating unique identifiers
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    
    -- Enable PostGIS extension for geospatial data (bike stations, routes)
    CREATE EXTENSION IF NOT EXISTS "postgis";
    
    -- Enable query performance statistics
    CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
    
    -- Grant all necessary permissions to the application user
    GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;
    
    -- Grant usage on public schema
    GRANT USAGE ON SCHEMA public TO $POSTGRES_USER;
    GRANT CREATE ON SCHEMA public TO $POSTGRES_USER;
EOSQL

echo "PostgreSQL initialization completed successfully"