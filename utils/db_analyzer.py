#!/usr/bin/env python3
"""
SQLite Database Analyzer for Sensor Data
Utility script to analyze and extract insights from the stored sensor data.
"""
import sqlite3
import pandas as pd
import argparse
import os
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

def connect_to_db(db_path):
    """Connect to the SQLite database"""
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        print(f"Connected to database: {db_path}")
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def get_summary_stats(conn):
    """Get summary statistics from the database"""
    cursor = conn.cursor()
    
    # Get basic stats
    cursor.execute("SELECT COUNT(*) FROM sensor_data")
    total_messages = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT device_id) FROM sensor_data")
    unique_devices = cursor.fetchone()[0]
    
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM sensor_data")
    time_range = cursor.fetchone()
    start_time = datetime.fromtimestamp(time_range[0])
    end_time = datetime.fromtimestamp(time_range[1])
    duration = end_time - start_time
    
    # Get latency stats
    cursor.execute("""
    SELECT 
        AVG(latency_ms) as avg_latency,
        MIN(latency_ms) as min_latency,
        MAX(latency_ms) as max_latency
    FROM sensor_data
    WHERE latency_ms IS NOT NULL
    """)
    latency_stats = cursor.fetchone()
    
    # Print results
    print("\n=== Database Summary ===")
    print(f"Total messages: {total_messages}")
    print(f"Unique devices: {unique_devices}")
    print(f"Time range: {start_time} to {end_time}")
    print(f"Duration: {duration}")
    print(f"Average latency: {latency_stats[0]:.2f} ms")
    print(f"Min latency: {latency_stats[1]:.2f} ms")
    print(f"Max latency: {latency_stats[2]:.2f} ms")
    
    return {
        'total_messages': total_messages,
        'unique_devices': unique_devices,
        'start_time': start_time,
        'end_time': end_time,
        'duration': duration,
        'avg_latency': latency_stats[0],
        'min_latency': latency_stats[1],
        'max_latency': latency_stats[2]
    }

def analyze_latency_trends(conn, output_path=None):
    """Analyze latency trends over time"""
    # Get latency data
    query = """
    SELECT timestamp, latency_ms 
    FROM sensor_data 
    WHERE latency_ms IS NOT NULL
    ORDER BY timestamp
    """
    
    df = pd.read_sql_query(query, conn)
    
    # Convert timestamp to datetime
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
    
    # Calculate rolling average
    df['rolling_avg'] = df['latency_ms'].rolling(window=50).mean()
    
    # Plot
    plt.figure(figsize=(12, 6))
    plt.plot(df['datetime'], df['latency_ms'], 'b.', alpha=0.3, label='Raw latency')
    plt.plot(df['datetime'], df['rolling_avg'], 'r-', linewidth=2, label='50-point rolling average')
    
    plt.title('Latency Over Time')
    plt.xlabel('Time')
    plt.ylabel('Latency (ms)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    if output_path:
        plt.savefig(os.path.join(output_path, 'latency_trend.png'))
        print(f"Latency trend chart saved to {output_path}/latency_trend.png")
    else:
        plt.show()
    
    # Calculate additional statistics
    latency_stats = df['latency_ms'].describe(percentiles=[0.5, 0.95, 0.99])
    print("\n=== Latency Statistics ===")
    print(latency_stats)
    
    return df

def analyze_sensor_readings(conn, output_path=None):
    """Analyze sensor readings from the database"""
    # Check if there are sensor readings in the database
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sensor_readings")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("No sensor readings found in the database")
        return None
    
    # Get some sample readings to analyze
    # Limit to last 1000 readings for performance
    query = """
    SELECT s.timestamp, r.angle, r.value
    FROM sensor_readings r
    JOIN sensor_data s ON r.data_id = s.id
    ORDER BY s.timestamp DESC
    LIMIT 1000
    """
    
    df = pd.read_sql_query(query, conn)
    
    # Convert angle strings to numeric if possible
    if 'angle' in df.columns:
        try:
            # Extract numeric part if angle is in format like 'angle_90'
            df['angle_value'] = df['angle'].str.extract(r'(\d+)').astype(float)
        except:
            print("Could not convert angles to numeric values")
    
    # If we have angle_value, we can create a polar plot for the latest reading
    if 'angle_value' in df.columns:
        # Get the latest timestamp
        latest_timestamp = df['timestamp'].max()
        latest_data = df[df['timestamp'] == latest_timestamp]
        
        if len(latest_data) > 0:
            plt.figure(figsize=(10, 10))
            ax = plt.subplot(111, projection='polar')
            
            # Convert to radians for polar plot
            theta = np.radians(latest_data['angle_value'])
            r = latest_data['value']
            
            ax.plot(theta, r, 'bo-')
            ax.set_title('Latest Sensor Reading (Polar View)')
            ax.grid(True)
            
            if output_path:
                plt.savefig(os.path.join(output_path, 'latest_reading.png'))
                print(f"Latest reading chart saved to {output_path}/latest_reading.png")
            else:
                plt.show()
    
    # Summarize readings
    print("\n=== Sensor Reading Summary ===")
    print(f"Total readings analyzed: {len(df)}")
    if 'value' in df.columns:
        print(f"Average value: {df['value'].mean():.2f}")
        print(f"Min value: {df['value'].min():.2f}")
        print(f"Max value: {df['value'].max():.2f}")
    
    return df

def export_to_csv(conn, output_path):
    """Export data to CSV files"""
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    
    # Export main sensor data
    sensor_data_query = """
    SELECT * FROM sensor_data
    ORDER BY timestamp
    """
    
    sensor_df = pd.read_sql_query(sensor_data_query, conn)
    sensor_csv_path = os.path.join(output_path, 'sensor_data.csv')
    sensor_df.to_csv(sensor_csv_path, index=False)
    print(f"Sensor data exported to {sensor_csv_path}")
    
    # Export performance stats if they exist
    try:
        stats_query = "SELECT * FROM performance_stats ORDER BY timestamp"
        stats_df = pd.read_sql_query(stats_query, conn)
        stats_csv_path = os.path.join(output_path, 'performance_stats.csv')
        stats_df.to_csv(stats_csv_path, index=False)
        print(f"Performance stats exported to {stats_csv_path}")
    except:
        print("No performance stats table found")
    
    return True

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Analyze sensor data from SQLite database')
    parser.add_argument('--db', required=True, help='Path to SQLite database file')
    parser.add_argument('--output', help='Output directory for charts and exported data')
    parser.add_argument('--export', action='store_true', help='Export data to CSV')
    
    args = parser.parse_args()
    
    # Create output directory if specified
    if args.output and not os.path.exists(args.output):
        os.makedirs(args.output)
    
    # Connect to database
    conn = connect_to_db(args.db)
    if not conn:
        return 1
    
    try:
        # Run analyses
        stats = get_summary_stats(conn)
        latency_df = analyze_latency_trends(conn, args.output)
        readings_df = analyze_sensor_readings(conn, args.output)
        
        # Export if requested
        if args.export and args.output:
            export_to_csv(conn, args.output)
    finally:
        conn.close()
    
    return 0

if __name__ == "__main__":
    exit(main())
