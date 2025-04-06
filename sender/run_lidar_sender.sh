#!/bin/bash
# Script to run the lidar integration container on Raspberry Pi with environment variables

# Display usage information
show_usage() {
  echo "Usage: $0 [options]"
  echo ""
  echo "Options:"
  echo "  -h, --help            Show this help message"
  echo "  -a, --address IP      Set the MQTT broker address (required)"
  echo "  -p, --port PORT       Set the MQTT broker port (default: 1883)"
  echo "  -t, --topic TOPIC     Set the MQTT topic (default: sensor/lidar)"
  echo "  -d, --device ID       Set the device identifier (default: raspi_lidar)"
  echo "  -l, --lidar-port PORT Set the lidar device port (default: /dev/ttyUSB0)"
  echo "  -r, --rate RATE       Set the publish rate in Hz (default: 5.0)"
  echo "  -s, --simulate        Run in simulation mode (no physical lidar required)"
  echo ""
  echo "Example:"
  echo "  $0 --address 192.168.1.100 --lidar-port /dev/ttyUSB0"
  echo "  $0 --address 192.168.1.100 --simulate"
}

# Default values
BROKER_PORT=1883
TOPIC="sensor/lidar"
DEVICE_ID="raspi_lidar"
LIDAR_PORT="/dev/ttyUSB0"
PUBLISH_RATE=5.0
SIMULATE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    -h|--help)
      show_usage
      exit 0
      ;;
    -a|--address)
      BROKER_ADDRESS="$2"
      shift 2
      ;;
    -p|--port)
      BROKER_PORT="$2"
      shift 2
      ;;
    -t|--topic)
      TOPIC="$2"
      shift 2
      ;;
    -d|--device)
      DEVICE_ID="$2"
      shift 2
      ;;
    -l|--lidar-port)
      LIDAR_PORT="$2"
      shift 2
      ;;
    -r|--rate)
      PUBLISH_RATE="$2"
      shift 2
      ;;
    -s|--simulate)
      SIMULATE=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      show_usage
      exit 1
      ;;
  esac
done

# Check for required parameters
if [ -z "$BROKER_ADDRESS" ]; then
  echo "Error: MQTT broker address is required"
  show_usage
  exit 1
fi

# Check if lidar device exists when not in simulation mode
if [ "$SIMULATE" != "true" ] && [ ! -e "$LIDAR_PORT" ]; then
  echo "Warning: Lidar device at $LIDAR_PORT not found. Make sure it's connected."
  echo "You can use --simulate to run in simulation mode without a physical device."
  read -p "Continue anyway? (y/n): " continue_anyway
  if [ "$continue_anyway" != "y" ]; then
    exit 1
  fi
fi

# Copy the lidar integration script to the current directory
if [ -f "../examples/lidar_integration.py" ]; then
  cp ../examples/lidar_integration.py .
elif [ -f "../../examples/lidar_integration.py" ]; then
  cp ../../examples/lidar_integration.py .
else
  echo "Error: Could not find lidar_integration.py in ../examples or ../../examples"
  exit 1
fi

# Create a simulated version of the lidar integration script
cat > lidar_simulation.py << 'EOF'
#!/usr/bin/env python3
"""
Simulated Lidar Integration
This is a modified version of lidar_integration.py that simulates lidar data.
"""
import paho.mqtt.client as mqtt
import time
import json
import os
import logging
import threading
import random
import math

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('lidar-simulator')

# Configuration from environment variables
BROKER_ADDRESS = os.environ.get("BROKER_ADDRESS", "mqtt-broker")
PORT = int(os.environ.get("BROKER_PORT", 1883))
TOPIC = os.environ.get("TOPIC", "sensor/lidar")
DEVICE_ID = os.environ.get("DEVICE_ID", "raspi_lidar")
PUBLISH_RATE = float(os.environ.get("PUBLISH_RATE", 5.0))  # Hz

# Global variables
latest_scan = {}
scan_lock = threading.Lock()
running = True

def generate_simulated_scan():
    """Generate simulated lidar scan data"""
    # Simulate a rotating object at a fixed distance with some noise
    scan_data = {}
    base_distance = 100.0  # cm
    
    for angle in range(0, 360, 1):  # 1-degree resolution
        # Add some objects at different distances
        if 45 <= angle <= 135:
            # Object to the right
            distance = 50.0 + random.uniform(-5, 5)
        elif 225 <= angle <= 315:
            # Object to the left
            distance = 75.0 + random.uniform(-5, 5)
        else:
            # Open space with some noise
            distance = base_distance + random.uniform(-10, 10)
            
        # Add some simulated walls
        if angle < 10 or angle > 350:
            # Wall in front
            distance = 200.0 + random.uniform(-2, 2)
            
        angle_key = f"angle_{angle}"
        scan_data[angle_key] = distance
    
    return scan_data

def lidar_simulation_thread():
    """Thread function to continuously generate simulated lidar data"""
    global latest_scan, running
    
    logger.info("Starting lidar simulation")
    
    while running:
        # Generate simulated scan data
        scan_data = generate_simulated_scan()
        
        # Update the latest scan with thread safety
        with scan_lock:
            latest_scan = scan_data.copy()
        
        # Simulate the scan rate of a real lidar (10Hz)
        time.sleep(0.1)
    
    logger.info("Lidar simulation thread stopped")

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
        # Start simulation thread
        lidar_thread_obj = threading.Thread(target=lidar_simulation_thread)
        lidar_thread_obj.daemon = True
        lidar_thread_obj.start()
        
        # Give simulation time to start up
        time.sleep(1)
        
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
EOF

# Build the container if it doesn't exist
if ! docker image inspect mqtt-lidar-sender &>/dev/null; then
  echo "Building mqtt-lidar-sender container..."
  
  # Create a temporary Dockerfile for the lidar sender
  cat > Dockerfile.lidar << EOF
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for rplidar (only needed for real lidar)
RUN apt-get update && apt-get install -y \\
    build-essential \\
    python3-dev \\
    libusb-1.0-0-dev \\
    && apt-get clean \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir pyserial rplidar

# Copy the sender code and lidar scripts
COPY sender.py .
COPY lidar_integration.py .
COPY lidar_simulation.py .

# Set the entrypoint script based on environment variable
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
EOF

  # Create an entrypoint script to choose between real and simulated lidar
  cat > entrypoint.sh << 'EOF'
#!/bin/bash
if [ "$SIMULATE" = "true" ]; then
  echo "Running in simulation mode"
  exec python3 lidar_simulation.py
else
  echo "Running with real lidar device"
  exec python3 lidar_integration.py
fi
EOF

  # Build the image
  docker build -t mqtt-lidar-sender -f Dockerfile.lidar .
  
  # Clean up the temporary files
  rm Dockerfile.lidar entrypoint.sh
fi

# Run the container with the specified environment variables
echo "Starting lidar sender with:"
echo "  BROKER_ADDRESS: $BROKER_ADDRESS"
echo "  BROKER_PORT: $BROKER_PORT"
echo "  TOPIC: $TOPIC"
echo "  DEVICE_ID: $DEVICE_ID"
if [ "$SIMULATE" = "true" ]; then
  echo "  MODE: Simulation (no physical device needed)"
else
  echo "  MODE: Real device"
  echo "  LIDAR_PORT: $LIDAR_PORT"
fi
echo "  PUBLISH_RATE: $PUBLISH_RATE"
echo ""

if [ "$SIMULATE" = "true" ]; then
  # Run without device mapping in simulation mode
  docker run --rm \
    -e BROKER_ADDRESS="$BROKER_ADDRESS" \
    -e BROKER_PORT="$BROKER_PORT" \
    -e TOPIC="$TOPIC" \
    -e DEVICE_ID="$DEVICE_ID" \
    -e PUBLISH_RATE="$PUBLISH_RATE" \
    -e SIMULATE="true" \
    mqtt-lidar-sender
else
  # Run with device mapping for real lidar
  docker run --rm \
    --device=$LIDAR_PORT:$LIDAR_PORT \
    -e BROKER_ADDRESS="$BROKER_ADDRESS" \
    -e BROKER_PORT="$BROKER_PORT" \
    -e TOPIC="$TOPIC" \
    -e DEVICE_ID="$DEVICE_ID" \
    -e LIDAR_PORT="$LIDAR_PORT" \
    -e PUBLISH_RATE="$PUBLISH_RATE" \
    -e SIMULATE="false" \
    mqtt-lidar-sender
fi

# Clean up the copied files
rm -f lidar_integration.py lidar_simulation.py
