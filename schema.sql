-- Normalised schema for an IoT sensor data store.
-- Reference tables (locations, sensors) are separated from the high-volume
-- fact table (readings) to avoid repeating text and to keep writes cheap.

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS readings;
DROP TABLE IF EXISTS sensors;
DROP TABLE IF EXISTS locations;

CREATE TABLE locations (
    location_id   INTEGER PRIMARY KEY,
    name          TEXT    NOT NULL,
    city          TEXT    NOT NULL,
    latitude      REAL    NOT NULL,
    longitude     REAL    NOT NULL
);

CREATE TABLE sensors (
    sensor_id     INTEGER PRIMARY KEY,
    location_id   INTEGER NOT NULL REFERENCES locations(location_id),
    sensor_type   TEXT    NOT NULL,      -- temperature | humidity | pm25
    unit          TEXT    NOT NULL,
    installed_on  TEXT    NOT NULL
);

-- Fact table: one row per measurement. Kept narrow and typed for volume.
CREATE TABLE readings (
    reading_id    INTEGER PRIMARY KEY,
    sensor_id     INTEGER NOT NULL REFERENCES sensors(sensor_id),
    ts            TEXT    NOT NULL,      -- ISO-8601 timestamp
    value         REAL    NOT NULL
);

-- Composite index supporting the most common access pattern:
-- "give me sensor X's readings over a time window, in order".
CREATE INDEX idx_readings_sensor_ts ON readings(sensor_id, ts);
