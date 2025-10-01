-- VeloSim Database Initialization
-- This file will be executed when the PostgreSQL container starts for the first time

-- Create basic extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Database is ready for future schema migrations
SELECT 'VeloSim database initialized successfully' as status;
