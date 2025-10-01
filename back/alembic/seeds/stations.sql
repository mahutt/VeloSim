-- VeloSim Station Seed Data
-- This file contains initial station data for the VeloSim bike sharing system
-- Data sourced from Montreal GBFS feed: https://gbfs.velobixi.com/gbfs/2-2/en/station_information.json

-- Set client encoding to UTF-8
SET client_encoding = 'UTF8';

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
