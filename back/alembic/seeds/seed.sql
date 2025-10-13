-- Set client encoding to UTF-8
SET client_encoding = 'UTF8';

-- VeloSim Station Seed Data
-- Contains initial station data for the VeloSim bike sharing system
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


-- VeloSim Resource Seed Data
-- Contains initial resource data for the VeloSim bike sharing system
-- Resources represent an assignable unit (in the form of a driver+vehicle pair)

-- Clear existing data (if any)
TRUNCATE TABLE resources RESTART IDENTITY CASCADE;

-- Insert initial resource data
INSERT INTO resources (
    type,
    date_created,
    date_updated,
    latitude,
    longitude,
    route_start_latitude,
    route_start_longitude,
    route_end_latitude,
    route_end_longitude
) VALUES
    ('VEHICLE_DRIVER', '2025-10-01 08:00:00', '2025-10-01 08:00:00', 45.50700, -73.56100, 45.50700, -73.56100, 45.51500, -73.55500),
    ('VEHICLE_DRIVER', '2025-10-01 08:15:00', '2025-10-01 08:15:00', 45.50900, -73.56700, 45.50900, -73.56700, 45.52000, -73.56000),
    ('VEHICLE_DRIVER', '2025-10-01 09:00:00', '2025-10-01 09:00:00', 45.50300, -73.57400, 45.50300, -73.57400, 45.49800, -73.55200);

-- Verify the data was inserted
SELECT
    id,
    type,
    latitude,
    longitude,
    route_start_latitude,
    route_start_longitude,
    route_end_latitude,
    route_end_longitude
FROM resources
ORDER BY id;

-- Display summary
SELECT COUNT(*) AS total_resources FROM resources;

\echo 'Resource seed data loaded successfully!'
\echo 'Total resources inserted:'
SELECT COUNT(*) FROM resources;


-- VeloSim Station Task Seed Data
-- Contains initial station task data for the VeloSim bike sharing system
-- Tasks represent maintenance and operational work needed at stations

-- Clear existing data (if any)
TRUNCATE TABLE station_tasks RESTART IDENTITY CASCADE;

-- Insert initial station task data (one task for each status)
INSERT INTO station_tasks (type, status, date_created, date_updated, station_id, resource_id) VALUES
    ('BATTERY_SWAP', 'OPEN', '2025-10-01 09:00:00', '2025-10-01 09:00:00', 1, NULL),
    ('BATTERY_SWAP', 'ASSIGNED', '2025-10-01 11:15:00', '2025-10-01 11:15:00', 2, 2),
    ('BATTERY_SWAP', 'DISPATCHED', '2025-10-01 14:20:00', '2025-10-01 14:20:00', 3, NULL),
    ('BATTERY_SWAP', 'CLOSED', '2025-10-01 08:00:00', '2025-10-01 16:45:00', 4, NULL);

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
