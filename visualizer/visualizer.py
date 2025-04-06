#!/usr/bin/env python3
"""
LIDAR Point Cloud Visualization Core
Processes LIDAR data from SQLite database and creates 3D point cloud visualizations.
With thread-safe database connection handling.
"""
import sqlite3
import numpy as np
import pandas as pd
import open3d as o3d
import matplotlib.pyplot as plt
from matplotlib import cm
import time
import os
import logging
import json
from scipy.spatial.transform import Rotation
import plotly.graph_objects as go
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('lidar-visualizer')

class LidarVisualizer:
    """Class to handle LIDAR data visualization with thread-safe SQLite connections"""
    
    def __init__(self, db_path=None):
        """Initialize with database path"""
        self.db_path = db_path or os.path.join('/data', 'sensor_data.db')
        self.conn = None
        self.latest_timestamp = None
        self.point_cloud = None
        self.local = threading.local()  # Thread-local storage for database connections
        
    def get_connection(self):
        """Get a thread-local database connection"""
        if not hasattr(self.local, 'conn') or self.local.conn is None:
            try:
                self.local.conn = sqlite3.connect(self.db_path)
                logger.info(f"Connected to database at {self.db_path} in thread {threading.get_ident()}")
            except sqlite3.Error as e:
                logger.error(f"Database connection error: {e}")
                return None
        return self.local.conn
    
    def close_connection(self):
        """Close the thread-local database connection"""
        if hasattr(self.local, 'conn') and self.local.conn is not None:
            self.local.conn.close()
            self.local.conn = None
            logger.info(f"Closed database connection in thread {threading.get_ident()}")
    
    def get_latest_scan(self):
        """Get the latest complete LIDAR scan from the database"""
        conn = self.get_connection()
        if not conn:
            return None
        
        try:
            # Get the latest timestamp
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(timestamp) FROM sensor_data")
            latest_time = cursor.fetchone()[0]
            
            if not latest_time:
                logger.warning("No data found in database")
                return None
            
            # Get the latest scan data
            query = """
            SELECT s.id, s.timestamp, s.device_id, r.angle, r.value
            FROM sensor_data s
            JOIN sensor_readings r ON s.id = r.data_id
            WHERE s.timestamp = ?
            ORDER BY r.angle
            """
            
            cursor.execute(query, (latest_time,))
            rows = cursor.fetchall()
            
            if not rows:
                logger.warning("No readings found for the latest timestamp")
                return None
            
            self.latest_timestamp = latest_time
            
            # Process into a structured format
            readings = {}
            device_id = rows[0][2]  # All rows have the same device_id for this timestamp
            
            for row in rows:
                angle_key = row[3]  # The angle column (e.g., "angle_90")
                distance = row[4]   # The value column (distance measurement)
                readings[angle_key] = distance
            
            return {
                "timestamp": latest_time,
                "device_id": device_id,
                "readings": readings
            }
            
        except sqlite3.Error as e:
            logger.error(f"Database query error: {e}")
            return None
    
    def get_historical_scan(self, timestamp):
        """Get a specific LIDAR scan by timestamp"""
        conn = self.get_connection()
        if not conn:
            return None
        
        try:
            # Get the scan data for the specified timestamp
            query = """
            SELECT s.id, s.timestamp, s.device_id, r.angle, r.value
            FROM sensor_data s
            JOIN sensor_readings r ON s.id = r.data_id
            WHERE s.timestamp = ?
            ORDER BY r.angle
            """
            
            cursor = conn.cursor()
            cursor.execute(query, (timestamp,))
            rows = cursor.fetchall()
            
            if not rows:
                logger.warning(f"No readings found for timestamp {timestamp}")
                return None
            
            # Process into a structured format
            readings = {}
            device_id = rows[0][2]  # All rows have the same device_id for this timestamp
            
            for row in rows:
                angle_key = row[3]  # The angle column (e.g., "angle_90")
                distance = row[4]   # The value column (distance measurement)
                readings[angle_key] = distance
            
            return {
                "timestamp": timestamp,
                "device_id": device_id,
                "readings": readings
            }
            
        except sqlite3.Error as e:
            logger.error(f"Database query error in thread {threading.get_ident()}: {e}")
            return None
    
    def get_timestamp_list(self, limit=100):
        """Get a list of available timestamps from the database"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            query = """
            SELECT DISTINCT timestamp 
            FROM sensor_data 
            ORDER BY timestamp DESC 
            LIMIT ?
            """
            
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            timestamps = [row[0] for row in cursor.fetchall()]
            
            return timestamps
            
        except sqlite3.Error as e:
            logger.error(f"Database query error: {e}")
            return []
    
    def convert_readings_to_points(self, scan_data):
        """Convert LIDAR angle/distance readings to 3D points"""
        if not scan_data or 'readings' not in scan_data:
            return None, None
        
        readings = scan_data['readings']
        points = []
        colors = []
        
        # Maximum distance for color normalization
        max_distance = max(readings.values())
        
        # Generate a colormap
        colormap = cm.get_cmap('viridis')
        
        for angle_key, distance in readings.items():
            # Extract angle value from key (e.g., "angle_90" -> 90)
            try:
                angle_deg = float(angle_key.split('_')[1])
            except (IndexError, ValueError):
                logger.warning(f"Could not parse angle from {angle_key}")
                continue
            
            # Convert to radians
            angle_rad = np.radians(angle_deg)
            
            # Default to 2D planar LIDAR data (all points on the X-Y plane)
            # LIDAR is typically mounted horizontally, so distances are in the X-Y plane
            x = distance * np.cos(angle_rad)
            y = distance * np.sin(angle_rad)
            z = 0.0  # Planar LIDAR assumption
            
            # Append point
            points.append([x, y, z])
            
            # Add color based on distance (normalized to [0,1])
            norm_distance = distance / max_distance if max_distance > 0 else 0
            color = colormap(norm_distance)[:3]  # RGB components only
            colors.append(color)
        
        return np.array(points), np.array(colors)
    
    def create_open3d_point_cloud(self, points, colors):
        """Create an Open3D point cloud from points and colors"""
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        pcd.colors = o3d.utility.Vector3dVector(colors)
        return pcd
    
    def visualize_point_cloud(self, pcd):
        """Visualize the point cloud using Open3D"""
        # Add coordinate frame
        coord_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(
            size=20.0, origin=[0, 0, 0]
        )
        
        # Visualize
        o3d.visualization.draw_geometries([pcd, coord_frame])
    
    def create_plotly_point_cloud(self, points, colors):
        """Create a Plotly figure for point cloud visualization"""
        if points is None or len(points) == 0:
            return None
        
        # Convert colors to format expected by Plotly
        colors_rgb = [f'rgb({int(r*255)},{int(g*255)},{int(b*255)})' for r, g, b in colors]
        
        # Create scatter3d plot
        fig = go.Figure(data=[
            go.Scatter3d(
                x=points[:, 0],
                y=points[:, 1],
                z=points[:, 2],
                mode='markers',
                marker=dict(
                    size=3,
                    color=colors_rgb,
                    opacity=0.8
                )
            )
        ])
        
        # Add coordinate axes
        axis_length = max(np.max(np.abs(points[:, 0])), np.max(np.abs(points[:, 1])), np.max(np.abs(points[:, 2]))) * 0.1
        
        # X-axis (red)
        fig.add_trace(go.Scatter3d(
            x=[0, axis_length], y=[0, 0], z=[0, 0],
            line=dict(color='red', width=4),
            name='X-axis'
        ))
        
        # Y-axis (green)
        fig.add_trace(go.Scatter3d(
            x=[0, 0], y=[0, axis_length], z=[0, 0],
            line=dict(color='green', width=4),
            name='Y-axis'
        ))
        
        # Z-axis (blue)
        fig.add_trace(go.Scatter3d(
            x=[0, 0], y=[0, 0], z=[0, axis_length],
            line=dict(color='blue', width=4),
            name='Z-axis'
        ))
        
        # Update layout
        fig.update_layout(
            title=f"LIDAR Point Cloud (Timestamp: {self.latest_timestamp})",
            scene=dict(
                xaxis_title='X (cm)',
                yaxis_title='Y (cm)',
                zaxis_title='Z (cm)',
                aspectmode='data'  # Keep the aspect ratio true to the data
            ),
            margin=dict(l=0, r=0, b=0, t=40)
        )
        
        return fig
    
    def process_latest_scan(self):
        """Process the latest scan and return a Plotly figure"""
        scan_data = self.get_latest_scan()
        
        if not scan_data:
            return None
        
        points, colors = self.convert_readings_to_points(scan_data)
        
        if points is None or len(points) == 0:
            return None
        
        # Store the point cloud in memory for later use
        self.point_cloud = self.create_open3d_point_cloud(points, colors)
        
        # Create and return a Plotly figure
        return self.create_plotly_point_cloud(points, colors)
    
    def process_scan_by_timestamp(self, timestamp):
        """Process a scan by timestamp and return a Plotly figure"""
        scan_data = self.get_historical_scan(timestamp)
        
        if not scan_data:
            return None
        
        points, colors = self.convert_readings_to_points(scan_data)
        
        if points is None or len(points) == 0:
            return None
        
        # Store the point cloud in memory for later use
        self.point_cloud = self.create_open3d_point_cloud(points, colors)
        
        # Create and return a Plotly figure
        return self.create_plotly_point_cloud(points, colors)
    
    def save_point_cloud(self, filename):
        """Save the current point cloud to a file"""
        if self.point_cloud is None:
            logger.warning("No point cloud to save")
            return False
        
        try:
            # Save as PLY file
            o3d.io.write_point_cloud(filename, self.point_cloud)
            logger.info(f"Point cloud saved to {filename}")
            return True
        except Exception as e:
            logger.error(f"Error saving point cloud: {e}")
            return False
    
    def get_latest_metadata(self):
        """Get metadata about the latest scan"""
        if not self.latest_timestamp:
            scan_data = self.get_latest_scan()
            if not scan_data:
                return {}
        
        return {
            "timestamp": self.latest_timestamp,
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.latest_timestamp)),
            "point_count": len(self.point_cloud.points) if self.point_cloud else 0
        }

# For testing/standalone use
if __name__ == "__main__":
    # Default database path within the container
    db_path = os.environ.get("DB_PATH", "/data/sensor_data.db")
    
    print(f"Using database at {db_path}")
    
    visualizer = LidarVisualizer(db_path)
    
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        exit(1)
    
    # Get the latest scan
    scan_data = visualizer.get_latest_scan()
    
    if not scan_data:
        print("No scan data available")
        exit(1)
    
    print(f"Found scan at timestamp {scan_data['timestamp']} for device {scan_data['device_id']}")
    print(f"Total readings: {len(scan_data['readings'])}")
    
    # Convert to point cloud
    points, colors = visualizer.convert_readings_to_points(scan_data)
    
    if points is None:
        print("Could not convert readings to points")
        exit(1)
    
    print(f"Generated {len(points)} points in point cloud")
    
    # Create and visualize
    pcd = visualizer.create_open3d_point_cloud(points, colors)
    print("Displaying point cloud visualization...")
    visualizer.visualize_point_cloud(pcd)
    
    # Save to file
    output_path = "latest_point_cloud.ply"
    visualizer.save_point_cloud(output_path)
    
    # Make sure to close the connection when done
    visualizer.close_connection()
    
    print("Done")