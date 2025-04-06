#!/usr/bin/env python3
"""
Example: Real Lidar Sensor Integration
This shows how to adapt the sender script for a real lidar sensor.
"""
import paho.mqtt.client as mqtt
import time
import json
import os
import logging
import threading

# For lidar integration - example using RPLidar from Slamtec
# pip install rplidar-py
from rplidar import RPLidar

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('lidar-sender')

# Configuration from environment variables
BROKER_ADDRESS = os.environ.get("BROKER_ADDRESS", "mqtt-broker")
PORT = int(os.environ.get("BROKER_PORT", 1883))
TOPIC = os.environ.get("TOPIC", "sensor/test")
DEVICE_ID = os.environ.get("DEVICE_ID", "raspi_lidar")
LIDAR_PORT = os.environ.get("LIDAR_PORT", "/dev/ttyUSB0")
PUBLISH_RATE = float(os.environ.get("PUBLISH_RATE", 5.0))  # Hz

# Global variables
lidar = None
latest_scan = {}
scan_lock = threading.Lock()
running = True

def lidar_thread():
    """Thread function to continuously read from lidar"""
    global lidar, latest_scan, running
    
    try:
        logger.info(f"Connecting to lidar on port {LIDAR_PORT}")
        lidar = RPLidar(LIDAR_PORT)
        
        # Display device information
        info = lidar.get_info()
        logger.info(f"Lidar info: {info}")
        
        # Get health status
        health = lidar.get_health()
        logger.info(f"Lidar health: {health}")
        
        # Start scanning
        logger.info("Starting lidar scan...")
        
        for scan in lidar.iter_scans():
            if not running:
                break
                
            # Process the scan data
            scan_data = {}
            for (_, angle, distance) in scan:
                # Round the angle to nearest integer for simplicity
                angle_key = f"angle_{int(angle)}"
                scan_data[angle_key] = distance
            
            # Update the latest scan with thread safety
            with scan_lock:
                latest_scan = scan_data.copy()
    
    except Exception as e:
        logger.error(f"Error in lidar thread: {e}")
    finally:
        if lidar:
            lidar.stop()
            lidar.disconnect()
        logger.info("Lidar thread stopped")

def publish_thread(client):
    """Thread function to publish lidar data at a consistent rate"""
    global latest_scan, running
    
    logger.info(f"Starting publisher thread (rate: {PUBLISH_RATE} Hz)")
    
    message_id = 0
    period = 1.0 / PUBLISH_RATE
    
    while running:
        start_time = time.time()
        
        # Get a copy of the latest scan with thread safety
        with scan_lock:
            scan_data = latest_scan.copy()
        
        # Only publish if we have data
        if scan_data:
            # Prepare message payload
            data = {
                "timestamp": time.time(),
                "device_id": DEVICE_ID,
                "message_id": message_id,
                "send_time": time.time(),
                "readings": scan_data
            }
            
            # Publish
            payload = json.dumps(data)
            client.publish(TOPIC, payload)
            
            # Log occasionally
            if message_id % 50 == 0:
                logger.info(f"Published message {message_id} with {len(scan_data)} readings")
            
            message_id += 1
        
        # Sleep to maintain consistent publishing rate
        elapsed = time.time() - start_time
        sleep_time = max(0, period - elapsed)
        time.sleep(sleep_time)

def main():
    """Main function"""
    global running
    
    # Connect to MQTT broker
    client = mqtt.Client()
    
    # Add connection retry logic
    connected = False
    retry_count = 0
    max_retries = 10
    
    while not connected and retry_count < max_retries:
        try:
            logger.info(f"Attempting to connect to broker at {BROKER_ADDRESS}:{PORT} (attempt {retry_count+1})")
            client.connect(BROKER_ADDRESS, PORT)
            connected = True
            logger.info("Connected to MQTT broker!")
        except Exception as e:
            retry_count += 1
            logger.error(f"Connection failed: {e}")
            time.sleep(5)
    
    if not connected:
        logger.error("Failed to connect to MQTT broker after multiple attempts")
        return 1
    
    try:
        # Start lidar thread
        lidar_thread_obj = threading.Thread(target=lidar_thread)
        lidar_thread_obj.daemon = True
        lidar_thread_obj.start()
        
        # Give lidar time to start up
        time.sleep(2)
        
        # Start publisher thread
        publisher_thread_obj = threading.Thread(target=publish_thread, args=(client,))
        publisher_thread_obj.daemon = True
        publisher_thread_obj.start()
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        running = False
        time.sleep(2)  # Give threads time to clean up
    finally:
        client.disconnect()
    
    return 0

if __name__ == "__main__":
    exit(main())
