#!/usr/bin/env python3
"""
SQLite Helper Utility
Provides helper functions for working with the sensor data SQLite database.
"""
import sqlite3
import os
import pandas as pd
import logging
import argparse
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('sqlite-helper')

def connect_to_db(db_path):
    """Connect to the SQLite database with optimal settings"""
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return None
    
    try:
        # Connect with optimized settings
        conn = sqlite3.connect(db_path)
        
        # Enable WAL mode for better concurrency and performance
        conn.execute("PRAGMA journal_mode = WAL")
        
        # Set synchronous mode to NORMAL for better performance
        # (still safe for most use cases)
        conn.execute("PRAGMA synchronous = NORMAL")
        
        # Use a larger page size for better performance with larger datasets
        conn.execute("PRAGMA page_size = 4096")
        
        # Enable foreign keys for data integrity
        conn.execute("PRAGMA foreign_keys = ON")
        
        logger.info(f"Connected to database: {db_path}")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to database: {e}")
        return None

def check_db_health(conn):
    """Check database health and size"""
    try:
        cursor = conn.cursor()
        
        # Run integrity check
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        
        # Get database size
        cursor.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]
        cursor.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        db_size_mb = (page_count * page_size) / (1024 * 1024)
        
        # Get table row counts
        cursor.execute("SELECT COUNT(*) FROM sensor_data")
        sensor_data_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sensor_readings")
        sensor_readings_count = cursor.fetchone()[0]
        
        print("\n=== Database Health Check ===")
        print(f"Integrity check: {integrity}")
        print(f"Database size: {db_size_mb:.2f} MB")
        print(f"sensor_data rows: {sensor_data_count}")
        print(f"sensor_readings rows: {sensor_readings_count}")
        
        if sensor_data_count > 0:
            # Get oldest and newest records
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM sensor_data")
            time_range = cursor.fetchone()
            if time_range[0] and time_range[1]:
                oldest = datetime.fromtimestamp(time_range[0])
                newest = datetime.fromtimestamp(time_range[1])
                print(f"Date range: {oldest} to {newest}")
                print(f"Total days of data: {(newest - oldest).days}")
        
        return True
    except sqlite3.Error as e:
        logger.error(f"Error checking database health: {e}")
        return False

def vacuum_database(conn):
    """Vacuum the database to reclaim space and optimize performance"""
    try:
        print("Vacuuming database (this may take a while)...")
        conn.execute("VACUUM")
        print("Database vacuum complete")
        return True
    except sqlite3.Error as e:
        logger.error(f"Error vacuuming database: {e}")
        return False

def optimize_database(conn):
    """Run ANALYZE to update statistics for the query optimizer"""
    try:
        print("Optimizing database...")
        conn.execute("ANALYZE")
        print("Database optimization complete")
        return True
    except sqlite3.Error as e:
        logger.error(f"Error optimizing database: {e}")
        return False

def prune_old_data(conn, days_to_keep=30):
    """Delete data older than the specified number of days"""
    try:
        cutoff_timestamp = datetime.now() - timedelta(days=days_to_keep)
        cutoff_unix = cutoff_timestamp.timestamp()
        
        print(f"Pruning data older than {cutoff_timestamp} ({days_to_keep} days)...")
        
        # Get count of rows to be deleted for reporting
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sensor_data WHERE timestamp < ?", (cutoff_unix,))
        count_to_delete = cursor.fetchone()[0]
        
        if count_to_delete == 0:
            print("No old data to prune")
            return True
        
        print(f"Will delete {count_to_delete} records from sensor_data and their related readings")
        confirm = input("Continue? (y/n): ")
        
        if confirm.lower() != 'y':
            print("Pruning cancelled")
            return False
        
        # Begin transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Delete from sensor_readings first (foreign key constraint)
        cursor.execute("""
        DELETE FROM sensor_readings
        WHERE data_id IN (
            SELECT id FROM sensor_data
            WHERE timestamp < ?
        )
        """, (cutoff_unix,))
        readings_deleted = cursor.rowcount
        
        # Then delete from sensor_data
        cursor.execute("DELETE FROM sensor_data WHERE timestamp < ?", (cutoff_unix,))
        data_deleted = cursor.rowcount
        
        # Commit changes
        conn.commit()
        
        print(f"Pruned {data_deleted} records from sensor_data")
        print(f"Pruned {readings_deleted} records from sensor_readings")
        
        return True
    except sqlite3.Error as e:
        logger.error(f"Error pruning database: {e}")
        conn.rollback()
        return False

def export_data_to_csv(conn, output_dir, time_range=None):
    """Export data to CSV files with optional time filtering"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    try:
        # Build query with optional time filter
        query_filter = ""
        params = ()
        
        if time_range:
            start_time, end_time = time_range
            query_filter = " WHERE timestamp >= ? AND timestamp <= ?"
            params = (start_time.timestamp(), end_time.timestamp())
        
        # Export sensor_data
        sensor_data_query = f"SELECT * FROM sensor_data{query_filter} ORDER BY timestamp"
        sensor_data_df = pd.read_sql_query(sensor_data_query, conn, params=params)
        
        # Convert Unix timestamps to datetime for readability
        if 'timestamp' in sensor_data_df.columns:
            sensor_data_df['timestamp_readable'] = pd.to_datetime(sensor_data_df['timestamp'], unit='s')
        if 'receive_time' in sensor_data_df.columns:
            sensor_data_df['receive_time_readable'] = pd.to_datetime(sensor_data_df['receive_time'], unit='s')
        
        # Save to CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sensor_data_path = os.path.join(output_dir, f"sensor_data_{timestamp}.csv")
        sensor_data_df.to_csv(sensor_data_path, index=False)
        print(f"Exported {len(sensor_data_df)} records to {sensor_data_path}")
        
        # Export sensor_readings if there's data to export
        if len(sensor_data_df) > 0:
            # For readings, we need to join with sensor_data to apply the time filter
            readings_query = """
            SELECT r.*, s.timestamp
            FROM sensor_readings r
            JOIN sensor_data s ON r.data_id = s.id
            """
            
            if time_range:
                readings_query += " WHERE s.timestamp >= ? AND s.timestamp <= ?"
                
            readings_query += " ORDER BY s.timestamp, r.data_id"
            
            readings_df = pd.read_sql_query(readings_query, conn, params=params)
            readings_path = os.path.join(output_dir, f"sensor_readings_{timestamp}.csv")
            readings_df.to_csv(readings_path, index=False)
            print(f"Exported {len(readings_df)} records to {readings_path}")
        
        return True
    except (sqlite3.Error, pd.io.sql.DatabaseError) as e:
        logger.error(f"Error exporting data: {e}")
        return False

def rebuild_database(conn, output_path):
    """Rebuild the database to optimize storage and fix any corruption"""
    try:
        # Create new database
        new_conn = sqlite3.connect(output_path)
        
        # Export schema
        cursor = conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL")
        schema_statements = cursor.fetchall()
        
        # Apply schema to new database
        for statement in schema_statements:
            if statement[0].startswith('CREATE TABLE') or statement[0].startswith('CREATE INDEX'):
                new_conn.execute(statement[0])
        
        # Copy data
        print("Copying data to new database (this may take a while)...")
        
        # Copy sensor_data
        data_df = pd.read_sql_query("SELECT * FROM sensor_data", conn)
        data_df.to_sql('sensor_data', new_conn, if_exists='append', index=False)
        
        # Copy sensor_readings
        readings_df = pd.read_sql_query("SELECT * FROM sensor_readings", conn)
        readings_df.to_sql('sensor_readings', new_conn, if_exists='append', index=False)
        
        # Copy performance_stats if it exists
        try:
            stats_df = pd.read_sql_query("SELECT * FROM performance_stats", conn)
            stats_df.to_sql('performance_stats', new_conn, if_exists='append', index=False)
        except:
            print("No performance_stats table found")
        
        # Optimize the new database
        new_conn.execute("VACUUM")
        new_conn.execute("ANALYZE")
        
        new_conn.close()
        print(f"Database rebuilt and saved to {output_path}")
        
        return True
    except Exception as e:
        logger.error(f"Error rebuilding database: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='SQLite Helper for Sensor Database')
    parser.add_argument('--db', required=True, help='Path to SQLite database file')
    parser.add_argument('--action', required=True, choices=[
        'check', 'vacuum', 'optimize', 'prune', 'export', 'rebuild'
    ], help='Action to perform')
    parser.add_argument('--days', type=int, default=30, help='Days of data to keep when pruning')
    parser.add_argument('--output', help='Output directory or file path')
    
    args = parser.parse_args()
    
    # Connect to database
    conn = connect_to_db(args.db)
    if not conn:
        return 1
    
    try:
        # Perform requested action
        if args.action == 'check':
            check_db_health(conn)
        
        elif args.action == 'vacuum':
            vacuum_database(conn)
        
        elif args.action == 'optimize':
            optimize_database(conn)
        
        elif args.action == 'prune':
            prune_old_data(conn, args.days)
        
        elif args.action == 'export':
            if not args.output:
                logger.error("Output directory required for export action")
                return 1
            export_data_to_csv(conn, args.output)
        
        elif args.action == 'rebuild':
            if not args.output:
                logger.error("Output file path required for rebuild action")
                return 1
            rebuild_database(conn, args.output)
        
    finally:
        conn.close()
    
    return 0

if __name__ == "__main__":
    exit(main())
