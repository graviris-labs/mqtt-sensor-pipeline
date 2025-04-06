#!/usr/bin/env python3
"""
LIDAR Point Cloud Web Server
Provides a web interface for visualizing LIDAR data as 3D point clouds.
Uses Dash and Plotly for interactive visualization.
"""
import os
import time
import json
import dash
from dash import dcc, html, callback
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import sqlite3
import logging

# Import the visualization core
from visualizer import LidarVisualizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('point-cloud-server')

# Initialize the visualizer
DB_PATH = os.environ.get("DB_PATH", "/data/sensor_data.db")
visualizer = LidarVisualizer(DB_PATH)

# Create the Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

# App title
app.title = "LIDAR 3D Point Cloud Visualizer"

# Define the layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("LIDAR 3D Point Cloud Visualizer", className="text-center my-4"), width=12)
    ]),
    
    dbc.Row([
        # Control panel
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Controls"),
                dbc.CardBody([
                    # Refresh button
                    dbc.Button("Refresh Data", id="refresh-button", color="primary", className="me-2 mb-3"),
                    
                    # Auto-refresh toggle
                    dbc.Checklist(
                        options=[{"label": "Auto-refresh (5s)", "value": True}],
                        value=[],
                        id="auto-refresh-toggle",
                        switch=True,
                        className="mb-3"
                    ),
                    
                    # Timestamp selector
                    html.Div([
                        html.Label("Select Timestamp:"),
                        dcc.Dropdown(id="timestamp-dropdown", placeholder="Select a timestamp"),
                    ], className="mb-3"),
                    
                    # Metadata section
                    html.Div([
                        html.H5("Scan Information"),
                        html.Div(id="scan-metadata")
                    ]),
                    
                    # Download button
                    dbc.Button("Download PLY", id="download-button", color="secondary", className="mt-3"),
                    dcc.Download(id="download-ply")
                ])
            ]),
            
            # Database info card
            dbc.Card([
                dbc.CardHeader("Database Information"),
                dbc.CardBody(id="db-info-content")
            ], className="mt-3")
        ], width=3),
        
        # Visualization panel
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("3D Point Cloud"),
                dbc.CardBody([
                    dcc.Graph(
                        id="point-cloud-graph",
                        figure=go.Figure(),
                        style={"height": "70vh"}
                    )
                ])
            ])
        ], width=9)
    ]),
    
    # Hidden div for storing state
    dcc.Store(id="timestamps-store"),
    
    # Interval component for auto-refresh
    dcc.Interval(
        id="auto-refresh-interval",
        interval=5*1000,  # 5 seconds
        disabled=True
    )
], fluid=True)

# Callback to toggle auto-refresh
@app.callback(
    Output("auto-refresh-interval", "disabled"),
    Input("auto-refresh-toggle", "value")
)
def toggle_auto_refresh(value):
    return not value or len(value) == 0

# Callback to update timestamp dropdown options
@app.callback(
    Output("timestamps-store", "data"),
    Output("timestamp-dropdown", "options"),
    Input("refresh-button", "n_clicks"),
    Input("auto-refresh-interval", "n_intervals")
)
def update_timestamp_options(n_clicks, n_intervals):
    # Get available timestamps
    timestamps = visualizer.get_timestamp_list(limit=100)
    
    # Format for dropdown
    options = [
        {"label": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"), "value": ts}
        for ts in timestamps
    ]
    
    # Store timestamps for later use
    return timestamps, options

# Callback to update the timestamp dropdown value to the latest timestamp
@app.callback(
    Output("timestamp-dropdown", "value"),
    Input("timestamps-store", "data"),
    State("timestamp-dropdown", "value")
)
def update_dropdown_value(timestamps, current_value):
    if not timestamps:
        return current_value
    
    # If there's no current selection or we're in auto-refresh mode, select the latest
    if current_value is None:
        return timestamps[0] if timestamps else None
    
    # Otherwise, keep the current selection
    return current_value

# Callback for the point cloud visualization
@app.callback(
    Output("point-cloud-graph", "figure"),
    Output("scan-metadata", "children"),
    Input("timestamp-dropdown", "value")
)
def update_point_cloud(timestamp):
    # Default empty figure
    empty_fig = go.Figure()
    empty_fig.update_layout(
        scene=dict(
            xaxis_title='X',
            yaxis_title='Y',
            zaxis_title='Z'
        ),
        title="No data available"
    )
    
    if timestamp is None:
        return empty_fig, "No data selected"
    
    # Generate point cloud for the selected timestamp
    fig = visualizer.process_scan_by_timestamp(timestamp)
    
    if fig is None:
        return empty_fig, "Failed to generate point cloud"
    
    # Get metadata for display
    metadata = visualizer.get_latest_metadata()
    
    metadata_html = html.Div([
        html.P(f"Timestamp: {metadata.get('datetime', 'Unknown')}"),
        html.P(f"Points: {metadata.get('point_count', 0)}")
    ])
    
    return fig, metadata_html

# Callback for database information
@app.callback(
    Output("db-info-content", "children"),
    Input("refresh-button", "n_clicks"),
    Input("auto-refresh-interval", "n_intervals")
)
def update_db_info(n_clicks, n_intervals):
    try:
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get message count
        cursor.execute("SELECT COUNT(*) FROM sensor_data")
        message_count = cursor.fetchone()[0]
        
        # Get time range
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM sensor_data")
        time_range = cursor.fetchone()
        
        if time_range[0] and time_range[1]:
            start_time = datetime.fromtimestamp(time_range[0]).strftime("%Y-%m-%d %H:%M:%S")
            end_time = datetime.fromtimestamp(time_range[1]).strftime("%Y-%m-%d %H:%M:%S")
            duration = time_range[1] - time_range[0]
            
            # Format duration
            if duration < 60:
                duration_str = f"{duration:.1f} seconds"
            elif duration < 3600:
                duration_str = f"{duration/60:.1f} minutes"
            else:
                duration_str = f"{duration/3600:.1f} hours"
        else:
            start_time = "N/A"
            end_time = "N/A"
            duration_str = "N/A"
        
        # Get scan count
        cursor.execute("SELECT COUNT(DISTINCT timestamp) FROM sensor_data")
        scan_count = cursor.fetchone()[0]
        
        conn.close()
        
        # Create info display
        return html.Div([
            html.P(f"Database: {os.path.basename(DB_PATH)}"),
            html.P(f"Total Messages: {message_count}"),
            html.P(f"Unique Scans: {scan_count}"),
            html.P(f"Time Range: {start_time} to {end_time}"),
            html.P(f"Duration: {duration_str}")
        ])
        
    except Exception as e:
        logger.error(f"Error getting database info: {e}")
        return "Database information unavailable"

# Callback for PLY file download
@app.callback(
    Output("download-ply", "data"),
    Input("download-button", "n_clicks"),
    State("timestamp-dropdown", "value"),
    prevent_initial_call=True
)
def download_point_cloud(n_clicks, timestamp):
    if timestamp is None:
        return None
    
    # Process the selected scan to ensure the point cloud is created
    visualizer.process_scan_by_timestamp(timestamp)
    
    # Generate a temporary filename
    filename = f"/tmp/point_cloud_{timestamp}.ply"
    
    # Save the point cloud
    if visualizer.save_point_cloud(filename):
        # Return the file as a download
        return dcc.send_file(filename)
    
    return None

# Run the app
if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8050))
    
    # Run with development server
    app.run_server(debug=True, host='0.0.0.0', port=port)
