-- Set client encoding to UTF-8
SET client_encoding = 'UTF8';


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


-- VeloSim Station Seed Data
-- Contains initial station data for the VeloSim bike sharing system
-- Data sourced from Montreal GBFS feed: https://gbfs.velobixi.com/gbfs/2-2/en/station_information.json

-- Clear existing data (if any)
TRUNCATE TABLE stations RESTART IDENTITY CASCADE;

-- Insert initial station data (10 real Montreal stations)
INSERT INTO stations (name, latitude, longitude, sim_instance_id) VALUES
    ('Metcalfe / de Maisonneuve', 45.50137, -73.57314, 1),
    ('Sanguinet / de Maisonneuve', 45.51344, -73.56261, 1),
    ('St-Denis / Ste-Catherine', 45.51007, -73.56391, 1),
    ('St-André / Ontario', 45.52188, -73.56353, 1),
    ('St-André / de Maisonneuve', 45.51708, -73.55974, 1),
    ('de la Commune / des Soeurs-Grises', 45.49798, -73.55273, 1),
    ('Notre-Dame / St-Gabriel', 45.50711, -73.55504, 1),
    ('de la Commune / Place Jacques-Cartier', 45.50761, -73.55183, 1),
    ('de Maisonneuve / Mansfield (sud)', 45.50205, -73.57346, 1),
    ('Métro Place-d''Armes (St-Urbain / Viger)', 45.50632, -73.55969, 1);

-- Verify the data was inserted
SELECT
    id,
    name,
    latitude,
    longitude,
    sim_instance_id
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
    route_end_longitude,
    sim_instance_id
) VALUES
    ('VEHICLE_DRIVER', '2025-10-01 08:00:00', '2025-10-01 08:00:00', 45.50700, -73.56100, 45.50700, -73.56100, 45.51500, -73.55500, 1),
    ('VEHICLE_DRIVER', '2025-10-01 08:15:00', '2025-10-01 08:15:00', 45.50900, -73.56700, 45.50900, -73.56700, 45.52000, -73.56000, 1),
    ('VEHICLE_DRIVER', '2025-10-01 09:00:00', '2025-10-01 09:00:00', 45.50300, -73.57400, 45.50300, -73.57400, 45.49800, -73.55200, 1);

-- Verify the data was inserted
SELECT
    id,
    type,
    latitude,
    longitude,
    route_start_latitude,
    route_start_longitude,
    route_end_latitude,
    route_end_longitude,
    sim_instance_id
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
INSERT INTO station_tasks (type, status, date_created, date_updated, station_id, resource_id, sim_instance_id) VALUES
    ('BATTERY_SWAP', 'OPEN', '2025-10-01 09:00:00', '2025-10-01 09:00:00', 1, NULL, 1),
    ('BATTERY_SWAP', 'ASSIGNED', '2025-10-01 11:15:00', '2025-10-01 11:15:00', 2, 2, 1),
    ('BATTERY_SWAP', 'IN_PROGRESS', '2025-10-01 14:20:00', '2025-10-01 14:20:00', 3, NULL, 1),
    ('BATTERY_SWAP', 'CLOSED', '2025-10-01 08:00:00', '2025-10-01 16:45:00', 4, NULL, 1);

-- Verify the data was inserted
SELECT
    id,
    type,
    status,
    station_id,
    date_created,
    date_updated,
    sim_instance_id
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


-- VeloSim Scenario Seed Data
-- Contains initial simulation scenarios for testing and development

TRUNCATE TABLE scenarios RESTART IDENTITY CASCADE;

INSERT INTO scenarios (name, content, description, user_id, date_created, date_updated)
VALUES
(
    'Test Scenario 1',
    '{
        "start_time": "08:00",
        "end_time": "12:00",
        "resources": [
            { "resource_id": 1, "resource_position": [45.5070, -73.5610] },
            { "resource_id": 2, "resource_position": [45.5090, -73.5670] }
        ],
        "stations": [
            { "station_id": 1, "station_name": "Metcalfe / de Maisonneuve", "station_position": [45.50137, -73.57314] },
            { "station_id": 2, "station_name": "Sanguinet / de Maisonneuve", "station_position": [45.51344, -73.56261] }
        ],
        "initial_tasks": [
            { "id": "t1", "station_id": 1, "assigned_resource_id": 1 }
        ],
        "scheduled_tasks": [
            { "id": "t3", "station_id": 1, "time": 5400 },
            { "id": "t4", "station_id": 2, "time": 6300 }
        ]
    }',
    'Test description for Scenario 1.',
    1,
    NOW(),
    NOW()
),
(
    'Test Scenario 2',
    '{
        "start_time": "13:00",
        "end_time": "17:00",
        "resources": [
            { "resource_id": 3, "resource_position": [45.5030, -73.5740] }
        ],
        "stations": [
            { "station_id": 3, "station_name": "St-Denis / Ste-Catherine", "station_position": [45.51007, -73.56391] },
            { "station_id": 4, "station_name": "St-André / Ontario", "station_position": [45.52188, -73.56353] }
        ],
        "initial_tasks": [
            { "id": "t5", "station_id": 3, "assigned_resource_id": 3 }
        ],
        "scheduled_tasks": [
            { "id": "t7", "station_id": 3, "time": 50400 },
            { "id": "t8", "station_id": 4, "time": 55800 }
        ]
    }',
    'Test description for Scenario 2.',
    1,
    NOW(),
    NOW()
);

SELECT id, name, description, user_id, date_created FROM scenarios ORDER BY id;
SELECT COUNT(*) AS total_scenarios FROM scenarios;

\echo 'Scenario seed data loaded successfully!'
