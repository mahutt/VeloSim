-- Set client encoding to UTF-8
SET client_encoding = 'UTF8';


-- VeloSim User seed data

-- Clear existing data (if any)
TRUNCATE TABLE users RESTART IDENTITY CASCADE;

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


-- VeloSim Scenario Seed Data
-- Contains initial simulation scenarios for testing and development

TRUNCATE TABLE scenarios RESTART IDENTITY CASCADE;

INSERT INTO scenarios (name, content, description, user_id, date_created, date_updated)
VALUES
(
    'Test Scenario 1',
    '{
        "start_time": "day1:08:00",
        "end_time": "day1:12:00",
        "vehicle_battery_capacity": 20,
        "vehicles": [
            { "name": "Vehicle 1", "position": [-73.5610, 45.5070], "battery_count": 1 },
            { "name": "Vehicle 2", "position": [-73.5670, 45.5090], "battery_count": 20 }
        ],
        "drivers": [
            { "name": "Driver 1", "shift": { "start_time": "day1:08:00", "end_time": "day1:12:00", "lunch_break": "day1:10:00" } },
            { "name": "Driver 2", "shift": { "start_time": "day1:08:00", "end_time": "day1:12:00", "lunch_break": "day1:10:00" } }
        ],
        "stations": [
            { "name": "Metcalfe / de Maisonneuve", "position": [-73.57314, 45.50137], "initial_task_count": 1, "scheduled_tasks": ["day1:09:30"] },
            { "name": "Sanguinet / de Maisonneuve", "position": [-73.56261, 45.51344], "initial_task_count": 0, "scheduled_tasks": ["day1:09:45"] },
            { "name": "St-Denis / Ste-Catherine", "position": [-73.56391, 45.51007], "initial_task_count": 0, "scheduled_tasks": [] },
            { "name": "St-André / Ontario", "position": [-73.56353, 45.52188], "initial_task_count": 0, "scheduled_tasks": [] },
            { "name": "St-André / de Maisonneuve", "position": [-73.55974, 45.51708], "initial_task_count": 0, "scheduled_tasks": [] },
            { "name": "de la Commune / des Soeurs-Grises", "position": [-73.55273, 45.49798], "initial_task_count": 0, "scheduled_tasks": [] },
            { "name": "Notre-Dame / St-Gabriel", "position": [-73.55504, 45.50711], "initial_task_count": 0, "scheduled_tasks": [] },
            { "name": "de la Commune / Place Jacques-Cartier", "position": [-73.55183, 45.50761], "initial_task_count": 0, "scheduled_tasks": [] },
            { "name": "de Maisonneuve / Mansfield (sud)", "position": [-73.57346, 45.50205], "initial_task_count": 0, "scheduled_tasks": [] },
            { "name": "Métro Place-d''Armes (St-Urbain / Viger)", "position": [-73.55969, 45.50632], "initial_task_count": 0, "scheduled_tasks": [] }
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
        "start_time": "day1:13:00",
        "end_time": "day1:17:00",
        "vehicle_battery_capacity": 50,
        "vehicles": [
            { "name": "Vehicle 3", "position": [-73.5740, 45.5030], "battery_count": 50 }
        ],
        "drivers": [
            { "name": "Driver 3", "shift": { "start_time": "day1:13:00", "end_time": "day1:17:00", "lunch_break": "day1:15:00" } }
        ],
        "stations": [
            { "name": "St-Denis / Ste-Catherine", "position": [-73.56391, 45.51007], "initial_task_count": 1, "scheduled_tasks": ["day1:14:00"] },
            { "name": "St-André / Ontario", "position": [-73.56353, 45.52188], "initial_task_count": 0, "scheduled_tasks": ["day1:15:30"] }
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
