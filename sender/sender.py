#!/usr/bin/env python3
"""
Raspberry Pi MQTT Sender - Test Script
Simulates lidar data transmission for testing message broker setup.
"""
import paho.mqtt.client as mqtt
import time
import json
import random
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mqtt-sender')

# Configuration from environment variables
BROKER_ADDRESS = os.environ.get("BROKER_ADDRESS", "mqtt-broker")
PORT = int(os.environ.get("BROKER_PORT", 1883))
TOPIC = os.environ.get("TOPIC", "sensor/test")
INTERVAL = float(os.environ.get("INTERVAL", 0.1))  # 10 messages per second
MESSAGE_COUNT = int(os.environ.get("MESSAGE_COUNT", 1000))
DEVICE_ID = os.environ.get("DEVICE_ID", "raspi_test")

def generate_test_data():
    """Generate dummy data that simulates lidar-like readings"""
    timestamp = time.time()
    # Simulate distance readings (in cm) at different angles
    readings = {
        f"angle_{i}": round(random.uniform(10, 500), 2)  # Distance in cm
        for i in range(0, 360, 10)  # Every 10 degrees
    }
    
    data = {
        "timestamp": timestamp,
        "device_id": DEVICE_ID,
        "readings": readings
    }
    return data

def main():
    """Main function to run the sender"""
    # Connect to broker
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
            logger.info("Connected!")
        except Exception as e:
            retry_count += 1
            logger.error(f"Connection failed: {e}")
            time.sleep(5)  # Wait before retrying

    if not connected:
        logger.error("Failed to connect to MQTT broker after multiple attempts")
        return 1

    logger.info(f"Starting to publish {MESSAGE_COUNT} test messages to {BROKER_ADDRESS}:{PORT}")
    logger.info(f"Publishing to topic: {TOPIC}")

    # Track start time for performance measurement
    start_time = time.time()
    
    try:
        # Send test messages
        for message_id in range(MESSAGE_COUNT):
            data = generate_test_data()
            data["message_id"] = message_id
            
            # Add a timestamp just before sending
            data["send_time"] = time.time()
            
            payload = json.dumps(data)
            client.publish(TOPIC, payload)
            
            # Print progress every 100 messages
            if message_id % 100 == 0:
                logger.info(f"Published message {message_id}")
            
            time.sleep(INTERVAL)
            
        # Calculate and log performance metrics
        elapsed_time = time.time() - start_time
        actual_rate = MESSAGE_COUNT / elapsed_time
        logger.info(f"Test publishing complete! {MESSAGE_COUNT} messages in {elapsed_time:.2f} seconds")
        logger.info(f"Actual publish rate: {actual_rate:.2f} messages/second")
        
    except KeyboardInterrupt:
        logger.info("Sender stopped by user")
    except Exception as e:
        logger.error(f"Error during publishing: {e}")
    finally:
        client.disconnect()
        logger.info("Disconnected from broker")
    
    return 0

if __name__ == "__main__":
    exit(main())
