-- Set client encoding to UTF-8
SET client_encoding = 'UTF8';

-- VeloSim Station Seed Data
-- This file contains initial station data for the VeloSim bike sharing system
-- Data sourced from Montreal GBFS feed: https://gbfs.velobixi.com/gbfs/2-2/en/station_information.json

-- Clear existing data (if any)
TRUNCATE TABLE stations RESTART IDENTITY CASCADE;

-- Insert initial station data (10 real Montreal stations)
INSERT INTO stations (name, latitude, longitude) VALUES
    ('Metcalfe / de Maisonneuve', 45.501375027330134, -73.57314596652985),
    ('Sanguinet / de Maisonneuve', 45.51344071811516, -73.56261849403381),
    ('St-Denis / Ste-Catherine', 45.510079193884, -73.5639146839003),
    ('St-André / Ontario', 45.521889, -73.56353),
    ('St-André / de Maisonneuve', 45.517085960784756, -73.55974848376083),
    ('de la Commune / des Soeurs-Grises', 45.497986472604876, -73.55273187160492),
    ('Notre-Dame / St-Gabriel', 45.50711760282556, -73.55504930019379),
    ('de la Commune / Place Jacques-Cartier', 45.50761009451047, -73.55183601379395),
    ('de Maisonneuve / Mansfield (sud)', 45.502053864057466, -73.57346534729004),
    ('Métro Place-d''Armes (St-Urbain / Viger)', 45.50632340391333, -73.5596989095211);

-- Verify the data was inserted
SELECT
    id,
    name,
    latitude,
    longitude
FROM stations
ORDER BY id;

-- Display summary
SELECT
    COUNT(*) as total_stations
FROM stations;

\echo 'Station seed data loaded successfully!'
\echo 'Total stations inserted:'
SELECT COUNT(*) FROM stations;

-- VeloSim Station Task Seed Data
-- This file contains initial station task data for the VeloSim bike sharing system
-- Tasks represent maintenance and operational work needed at stations

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


-- VeloSim User seed data

-- Clear existing data (if any)
TRUNCATE TABLE users RESTART IDENTITY CASCADE;

-- Insert initial station data (10 real Montreal users)
-- Seed data for users table
INSERT INTO users (username, password_hash, is_admin, date_created, date_updated) VALUES
('admin', '$argon2id$v=19$m=65536,t=3,p=4$TTVHTUpLZ0xaSUl4czlCdw$rOCKPpchPyYQcY1fHtsQyQ', true, '2025-01-01 00:00:00', '2025-01-01 00:00:00');
-- password: velosim

-- Verify the data was inserted
SELECT
    id,
    username,
    is_admin,
    date_created,
    date_updated
FROM users
ORDER BY id;

-- Display summary
SELECT
    COUNT(*) as total_users
FROM users;

\echo 'User seed data loaded successfully!'
\echo 'Total users inserted:'
SELECT COUNT(*) FROM users;

-- VeloSim Refresh Token seed data

-- Set client encoding to UTF-8
SET client_encoding = 'UTF8';

-- Clear existing data (if any)
TRUNCATE TABLE refresh_tokens RESTART IDENTITY CASCADE;

-- Insert initial refresh token data
INSERT INTO refresh_tokens (user_id, id, token_name, user_agent, creation_ip, date_expires, date_created, date_updated) VALUES
(1, 'JDh-dF6CyBs8DoZNdW_7Sg', 'Chrome on macOS', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36', '2a00:1450:4001:812::200e', '2026-05-01 00:00:00', '2025-01-01 00:00:00', '2025-01-01 00:00:00');

-- Verify the data was inserted
SELECT
    id,
    user_id,
    token_name,
    user_agent,
    creation_ip,
    date_expires,
    date_created,
    date_updated
FROM refresh_tokens
ORDER BY id;

-- Display summary
SELECT
    COUNT(*) as total_refresh_tokens
FROM refresh_tokens;

\echo 'Refresh token seed data loaded successfully!'
\echo 'Total refresh tokens inserted:'
SELECT COUNT(*) FROM refresh_tokens;

-- VeloSim Simulation Instance seed data

-- Clear existing data (if any)
TRUNCATE TABLE sim_instances RESTART IDENTITY CASCADE;

-- Insert initial simulation instance data
INSERT INTO sim_instances (user_id) VALUES
(1);

-- Verify the data was inserted
SELECT
    id,
    user_id
FROM sim_instances
ORDER BY id;

-- Display summary
SELECT
    COUNT(*) as total_sim_instances
FROM sim_instances;

\echo 'Simulation instance seed data loaded successfully!'
\echo 'Total simulation instances inserted:'
SELECT COUNT(*) FROM sim_instances;
