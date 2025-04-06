# SQLite Guide for Sensor Data Pipeline

This guide explains how SQLite is used in the project for storing and managing sensor data from your Raspberry Pi.

## Why SQLite?

SQLite is an excellent choice for this project for several reasons:

1. **Self-contained**: The entire database is stored in a single file on your Mac Mini
2. **Zero configuration**: No separate server process to manage
3. **Reliable**: ACID-compliant with excellent crash recovery
4. **Efficient**: Low memory and storage footprint, perfect for IoT data
5. **Portable**: The database file can be easily backed up or moved
6. **Cross-platform**: Works identically on macOS, Raspberry Pi OS, etc.

## Database Schema

The schema is designed specifically for sensor time-series data with a normalized structure:

### sensor_data

The main table that stores metadata about each received message:

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-incremented |
| timestamp | REAL | Original timestamp from the sensor |
| receive_time | REAL | Time when message was received |
| message_id | INTEGER | Sequence number from the sender |
| device_id | TEXT | Identifier of the source device |
| latency_ms | REAL | Calculated transmission latency |

### sensor_readings

Stores the actual sensor readings in a normalized format:

| Column | Type | Description |
|--------|------|-------------|
| data_id | INTEGER | Foreign key to sensor_data.id |
| angle | TEXT | Angle identifier (e.g., "angle_90") |
| value | REAL | Reading value (e.g., distance in cm) |

### performance_stats

Periodic snapshots of system performance metrics:

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| timestamp | REAL | When the stats were recorded |
| message_count | INTEGER | Total messages received so far |
| avg_latency | REAL | Average latency in milliseconds |
| min_latency | REAL | Minimum latency in milliseconds |
| max_latency | REAL | Maximum latency in milliseconds |
| p95_latency | REAL | 95th percentile latency |
| throughput | REAL | Messages per second |

## Indexes

The database includes the following indexes to optimize query performance:

- `idx_timestamp` on `sensor_data(timestamp)`: Speeds up time-based queries
- `idx_device` on `sensor_data(device_id)`: Faster filtering by device
- `idx_readings_data_id` on `sensor_readings(data_id)`: Faster joins

## Database Access

### From Within the Container

The database is accessible at `/data/sensor_data.db` inside the receiver container.

### From Your Mac

The database file is mapped to `./data/sensor_data.db` on your Mac Mini's filesystem.

## Useful SQLite Commands

### Opening the Database

```bash
# From your Mac terminal
sqlite3 ./data/sensor_data.db
```

### Basic Commands

```sql
-- Show all tables
.tables

-- Show schema for a specific table
.schema sensor_data

-- Set output mode to column for better readability
.mode column
.headers on

-- Display database file information
.dbinfo
```

### Performance Optimization

SQLite is already configured for optimal performance, but you can tune it further:

1. **Batch Transactions**: The receiver implements batch commits (every 100 messages) for better performance
2. **Pragmas**: You can add these to improve write performance:
   ```sql
   PRAGMA journal_mode = WAL;
   PRAGMA synchronous = NORMAL;
   ```

## Backing Up the Database

SQLite databases can be backed up while in use:

```bash
# Simple file copy backup
cp ./data/sensor_data.db ./data/sensor_data_backup.db

# Using SQLite's backup command
sqlite3 ./data/sensor_data.db ".backup ./data/sensor_data_backup.db"

# Create a SQL dump (can be used to restore)
sqlite3 ./data/sensor_data.db ".dump" > ./data/sensor_data_dump.sql
```

## Example Queries

### Basic Statistics

```sql
-- Get message count by device
SELECT device_id, COUNT(*) as message_count 
FROM sensor_data 
GROUP BY device_id;

-- Get average latency
SELECT AVG(latency_ms) as avg_latency 
FROM sensor_data;
```

### Time-Based Analysis

```sql
-- Get message count per hour
SELECT 
    strftime('%Y-%m-%d %H', datetime(timestamp, 'unixepoch')) as hour,
    COUNT(*) as message_count
FROM sensor_data
GROUP BY hour
ORDER BY hour;

-- Get latency trends
SELECT 
    strftime('%Y-%m-%d %H:%M', datetime(timestamp, 'unixepoch')) as minute,
    AVG(latency_ms) as avg_latency
FROM sensor_data
GROUP BY minute
ORDER BY minute;
```

### Sensor-Specific Queries

```sql
-- Get all readings for a specific angle
SELECT 
    s.timestamp,
    r.value,
    s.device_id
FROM sensor_data s
JOIN sensor_readings r ON s.id = r.data_id
WHERE r.angle = 'angle_180'
ORDER BY s.timestamp;

-- Get latest reading from each angle
SELECT 
    r.angle,
    r.value
FROM sensor_readings r
JOIN sensor_data s ON r.data_id = s.id
WHERE s.timestamp = (SELECT MAX(timestamp) FROM sensor_data)
ORDER BY r.angle;
```

## Managing Database Size

For long-term operation, consider these strategies to manage database growth:

1. **Periodic pruning**: Delete old data that's no longer needed
   ```sql
   -- Delete data older than 30 days
   DELETE FROM sensor_readings
   WHERE data_id IN (
       SELECT id FROM sensor_data
       WHERE timestamp < (strftime('%s', 'now') - 2592000)
   );
   
   DELETE FROM sensor_data
   WHERE timestamp < (strftime('%s', 'now') - 2592000);
   ```

2. **Vacuum**: Reclaim unused space after deleting data
   ```sql
   VACUUM;
   ```

3. **Partitioning**: For very large datasets, consider time-based partitioning with multiple database files

## Troubleshooting

### Database Locked

If you encounter "database is locked" errors, it means another process is writing to the database. Options:

1. Wait and retry the operation
2. Use the WAL journal mode:
   ```sql
   PRAGMA journal_mode = WAL;
   ```

### Corruption Recovery

In the rare case of database corruption:

```bash
# Recover with SQLite
sqlite3 ./data/sensor_data.db "PRAGMA integrity_check;"

# Use the dump method to recover data
sqlite3 ./data/sensor_data.db ".dump" > ./data/recover.sql
sqlite3 ./data/sensor_data_new.db < ./data/recover.sql
```
