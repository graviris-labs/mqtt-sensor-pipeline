#!/usr/bin/env python3
"""
Mac Mini MQTT Receiver - SQLite Optimized
Receives and stores sensor data in SQLite database.
"""
import paho.mqtt.client as mqtt
import time
import json
import statistics
import os
import sqlite3
from datetime import datetime
import pathlib
import logging
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mqtt-receiver')

# Configuration from environment variables
BROKER_ADDRESS = os.environ.get("BROKER_ADDRESS", "mqtt-broker")
PORT = int(os.environ.get("BROKER_PORT", 1883))
TOPIC = os.environ.get("TOPIC", "sensor/test")
DATA_DIR = os.environ.get("DATA_DIR", "/data")
DB_FILENAME = os.environ.get("DB_FILENAME", "sensor_data.db")

# Statistics tracking
latencies = []
message_counts = 0
start_time = None
last_report_time = time.time()
reporting_interval = 5  # Report stats every 5 seconds

# Global DB connection
db_connection = None
db_cursor = None

def ensure_db_schema(db_cursor):
    """Ensure the database has the correct schema"""
    try:
        # Check if sensor_data table exists
        db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sensor_data'")
        if not db_cursor.fetchone():
            logger.info("Creating database schema...")
            
            # Enable foreign keys
            db_cursor.execute("PRAGMA foreign_keys = ON")
            
            # Use WAL mode for better performance
            db_cursor.execute("PRAGMA journal_mode = WAL")
            
            # Create sensor_data table
            db_cursor.execute('''
            CREATE TABLE sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                receive_time REAL NOT NULL,
                message_id INTEGER,
                device_id TEXT NOT NULL,
                latency_ms REAL
            )
            ''')
            
            # Create sensor_readings table
            db_cursor.execute('''
            CREATE TABLE sensor_readings (
                data_id INTEGER NOT NULL,
                angle TEXT NOT NULL,
                value REAL NOT NULL,
                FOREIGN KEY (data_id) REFERENCES sensor_data(id)
            )
            ''')
            
            # Create performance_stats table
            db_cursor.execute('''
            CREATE TABLE performance_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                message_count INTEGER NOT NULL,
                avg_latency REAL,
                min_latency REAL,
                max_latency REAL,
                p95_latency REAL,
                throughput REAL
            )
            ''')
            
            # Create indexes
            db_cursor.execute('CREATE INDEX idx_timestamp ON sensor_data(timestamp)')
            db_cursor.execute('CREATE INDEX idx_device ON sensor_data(device_id)')
            db_cursor.execute('CREATE INDEX idx_readings_data_id ON sensor_readings(data_id)')
            
            logger.info("Database schema created successfully")
        else:
            logger.info("Database schema already exists")
            
            # Ensure foreign keys are enabled
            db_cursor.execute("PRAGMA foreign_keys = ON")
            
    except sqlite3.Error as e:
        logger.error(f"Error setting up database schema: {e}")
        raise

def setup_database():
    """Set up SQLite database for storing sensor data"""
    global db_connection, db_cursor
    
    # Ensure data directory exists
    pathlib.Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    
    # Database file path
    db_path = os.path.join(DATA_DIR, DB_FILENAME)
    
    try:
        # Connect to database with optimal settings
        db_connection = sqlite3.connect(db_path)
        db_cursor = db_connection.cursor()
        
        # Ensure schema exists
        ensure_db_schema(db_cursor)
        
        logger.info(f"Database ready at {db_path}")
        return db_path
    except sqlite3.Error as e:
        logger.error(f"Database setup error: {e}")
        if db_connection:
            db_connection.close()
        raise

def close_database():
    """Close database connection safely"""
    global db_connection
    
    if db_connection:
        db_connection.commit()
        db_connection.close()
        logger.info("Database connection closed")

def on_connect(client, userdata, flags, rc):
    """Callback for when client connects to the broker"""
    logger.info(f"Connected to broker with result code {rc}")
    client.subscribe(TOPIC)
    
    global start_time
    start_time = time.time()

def on_message(client, userdata, msg):
    """Callback for when a message is received from the broker"""
    global message_counts, latencies, last_report_time, db_connection, db_cursor
    
    # Parse the received message
    receive_time = time.time()
    try:
        data = json.loads(msg.payload)
        
        # Calculate latency
        latency = None
        if "send_time" in data:
            latency = (receive_time - data["send_time"]) * 1000  # Convert to ms
            latencies.append(latency)
        
        message_counts += 1
        
        # Store data in SQLite
        store_message(data, receive_time, latency)
        
        # Print occasional message details
        if message_counts % 100 == 0:
            logger.info(f"Received message {message_counts}: {data.get('message_id')}")
        
        # Report statistics periodically
        if time.time() - last_report_time > reporting_interval:
            report_statistics()
            last_report_time = time.time()
            
    except json.JSONDecodeError:
        logger.error(f"Error decoding message: {msg.payload}")
    except Exception as e:
        logger.error(f"Error processing message: {e}")

def store_message(data, receive_time, latency):
    """Store message in SQLite database with optimized schema"""
    global db_connection, db_cursor
    
    timestamp = data.get("timestamp", time.time())
    message_id = data.get("message_id", -1)
    device_id = data.get("device_id", "unknown")
    
    try:
        # Insert main record
        db_cursor.execute('''
        INSERT INTO sensor_data 
        (timestamp, receive_time, message_id, device_id, latency_ms)
        VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, receive_time, message_id, device_id, latency))
        
        # Get the ID of the inserted record
        data_id = db_cursor.lastrowid
        
        # Store readings if available
        if "readings" in data and isinstance(data["readings"], dict):
            readings = data["readings"]
            reading_data = []
            
            for angle, value in readings.items():
                reading_data.append((data_id, angle, value))
            
            # Batch insert for better performance
            db_cursor.executemany('''
            INSERT INTO sensor_readings (data_id, angle, value)
            VALUES (?, ?, ?)
            ''', reading_data)
        
        # Commit every 100 messages for balance of performance and safety
        if message_counts % 100 == 0:
            db_connection.commit()
            
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        # Try to commit what we can
        db_connection.commit()

def report_statistics():
    """Report performance statistics"""
    if not latencies:
        return
    
    runtime = time.time() - start_time
    throughput = message_counts / runtime
    
    logger.info("\n--- Communication Statistics ---")
    logger.info(f"Messages received: {message_counts}")
    logger.info(f"Average throughput: {throughput:.2f} msg/sec")
    
    # Latency statistics
    avg_latency = statistics.mean(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
    
    logger.info(f"Latency (ms) - Avg: {avg_latency:.2f}, Min: {min_latency:.2f}, Max: {max_latency:.2f}, p95: {p95_latency:.2f}")
    logger.info("-------------------------------")
    
    # Every 10 reporting intervals, save detailed statistics to database
    if message_counts % (100 * reporting_interval) == 0:
        save_statistics_snapshot(avg_latency, min_latency, max_latency, p95_latency, throughput)

def save_statistics_snapshot(avg_latency, min_latency, max_latency, p95_latency, throughput):
    """Save a snapshot of current statistics to the database"""
    try:
        # Create statistics table if it doesn't exist
        db_cursor.execute('''
        CREATE TABLE IF NOT EXISTS performance_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            message_count INTEGER,
            avg_latency REAL,
            min_latency REAL,
            max_latency REAL,
            p95_latency REAL,
            throughput REAL
        )
        ''')
        
        # Insert stats
        db_cursor.execute('''
        INSERT INTO performance_stats
        (timestamp, message_count, avg_latency, min_latency, max_latency, p95_latency, throughput)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (time.time(), message_counts, avg_latency, min_latency, max_latency, p95_latency, throughput))
        
        db_connection.commit()
        logger.info("Performance statistics snapshot saved to database")
    except sqlite3.Error as e:
        logger.error(f"Error saving performance stats: {e}")

def handle_exit(sig, frame):
    """Handle clean shutdown on exit signals"""
    logger.info("Shutting down receiver...")
    report_statistics()  # Final report
    close_database()
    sys.exit(0)

def main():
    """Main function to run the receiver"""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    try:
        # Set up database
        db_path = setup_database()
        logger.info(f"Using database: {db_path}")
        
        # Set up MQTT client
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        
        # Connect with retry logic
        connected = False
        retry_count = 0
        max_retries = 30
        
        while not connected and retry_count < max_retries:
            try:
                logger.info(f"Attempting to connect to broker at {BROKER_ADDRESS}:{PORT} (attempt {retry_count+1})")
                client.connect(BROKER_ADDRESS, PORT)
                connected = True
                logger.info("Connected!")
            except Exception as e:
                retry_count += 1
                logger.error(f"Connection failed: {e}")
                time.sleep(5)  # Wait before retrying
        
        if not connected:
            logger.error("Failed to connect to MQTT broker after multiple attempts")
            return 1
        
        logger.info(f"Listening for messages on topic: {TOPIC}")
        
        client.loop_forever()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        close_database()
    
    return 0

if __name__ == "__main__":
    exit(main())