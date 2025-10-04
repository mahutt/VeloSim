-- VeloSim Station Task Seed Data
-- This file contains initial station task data for the VeloSim bike sharing system
-- Tasks represent maintenance and operational work needed at stations

-- Set client encoding to UTF-8
SET client_encoding = 'UTF8';

-- Clear existing data (if any)
TRUNCATE TABLE station_tasks RESTART IDENTITY CASCADE;

-- Insert initial station task data (one task for each status)
INSERT INTO station_tasks (type, status, date_created, date_updated, station_id) VALUES
    ('BATTERY_SWAP', 'UNASSIGNED', '2025-10-01 09:00:00', '2025-10-01 09:00:00', 1),
    ('BATTERY_SWAP', 'ABANDONED', '2025-10-01 10:30:00', '2025-10-01 10:30:00', 2),
    ('BATTERY_SWAP', 'ASSIGNED', '2025-10-01 11:15:00', '2025-10-01 11:15:00', 3),
    ('BATTERY_SWAP', 'IN_PROGRESS', '2025-10-01 14:20:00', '2025-10-01 14:20:00', 4),
    ('BATTERY_SWAP', 'COMPLETED', '2025-10-01 08:00:00', '2025-10-01 16:45:00', 5);

-- Verify the data was inserted
SELECT
    id,
    type,
    status,
    station_id,
    date_created,
    date_updated
FROM station_tasks
ORDER BY id;

-- Display summary
SELECT
    COUNT(*) as total_tasks
FROM station_tasks;

SELECT
    status,
    COUNT(*) as count
FROM station_tasks
GROUP BY status
ORDER BY status;

\echo 'Station task seed data loaded successfully!'
\echo 'Total tasks inserted:'
SELECT COUNT(*) FROM station_tasks;
\echo 'Tasks by status:'
SELECT status, COUNT(*) FROM station_tasks GROUP BY status ORDER BY status;
