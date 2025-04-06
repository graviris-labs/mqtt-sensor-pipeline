-- SQLite Schema for Sensor Data
-- This schema is optimized for lidar and other sensor data storage

-- Enable foreign keys for data integrity
PRAGMA foreign_keys = ON;

-- Use WAL mode for better performance and concurrency
PRAGMA journal_mode = WAL;

-- Main sensor data table - stores metadata about each message
CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,           -- Original timestamp from sensor
    receive_time REAL NOT NULL,        -- Time message was received
    message_id INTEGER,                -- Message sequence number
    device_id TEXT NOT NULL,           -- Source device identifier
    latency_ms REAL                    -- Transmission latency in milliseconds
);

-- Sensor readings table - normalized storage of sensor values
CREATE TABLE IF NOT EXISTS sensor_readings (
    data_id INTEGER NOT NULL,          -- Foreign key to sensor_data.id
    angle TEXT NOT NULL,               -- Angle identifier (e.g. "angle_90")
    value REAL NOT NULL,               -- Reading value (e.g. distance in cm)
    FOREIGN KEY (data_id) REFERENCES sensor_data(id)
);

-- Performance statistics table - periodic snapshots of system performance
CREATE TABLE IF NOT EXISTS performance_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,           -- When stats were recorded
    message_count INTEGER NOT NULL,    -- Total messages received so far
    avg_latency REAL,                  -- Average latency in milliseconds
    min_latency REAL,                  -- Minimum latency in milliseconds
    max_latency REAL,                  -- Maximum latency in milliseconds
    p95_latency REAL,                  -- 95th percentile latency
    throughput REAL                    -- Messages per second
);

-- Create indexes for better query performance
CREATE INDEX idx_timestamp ON sensor_data(timestamp);
CREATE INDEX idx_device ON sensor_data(device_id);
CREATE INDEX idx_readings_data_id ON sensor_readings(data_id);

-- Example queries

-- Get average latency by device
SELECT device_id, AVG(latency_ms) as avg_latency
FROM sensor_data
GROUP BY device_id;

-- Get message count over time (grouped by minute)
SELECT 
    strftime('%Y-%m-%d %H:%M', datetime(timestamp, 'unixepoch')) as minute,
    COUNT(*) as message_count
FROM sensor_data
GROUP BY minute
ORDER BY minute;

-- Get latest readings for a specific device
SELECT 
    s.timestamp,
    r.angle,
    r.value
FROM sensor_data s
JOIN sensor_readings r ON s.id = r.data_id
WHERE s.device_id = 'raspi_lidar'
AND s.timestamp = (
    SELECT MAX(timestamp) 
    FROM sensor_data 
    WHERE device_id = 'raspi_lidar'
);

-- Get throughput statistics by hour
SELECT 
    strftime('%Y-%m-%d %H', datetime(timestamp, 'unixepoch')) as hour,
    COUNT(*) as message_count,
    COUNT(*) / (MAX(timestamp) - MIN(timestamp)) as messages_per_second
FROM sensor_data
GROUP BY hour
ORDER BY hour;