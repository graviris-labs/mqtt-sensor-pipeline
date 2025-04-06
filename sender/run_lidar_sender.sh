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
  echo ""
  echo "Example:"
  echo "  $0 --address 192.168.1.100 --lidar-port /dev/ttyUSB0"
}

# Default values
BROKER_PORT=1883
TOPIC="sensor/lidar"
DEVICE_ID="raspi_lidar"
LIDAR_PORT="/dev/ttyUSB0"
PUBLISH_RATE=5.0

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

# Check if lidar device exists
if [ ! -e "$LIDAR_PORT" ]; then
  echo "Warning: Lidar device at $LIDAR_PORT not found. Make sure it's connected."
  read -p "Continue anyway? (y/n): " continue_anyway
  if [ "$continue_anyway" != "y" ]; then
    exit 1
  fi
fi

# Build the container if it doesn't exist
if ! docker image inspect mqtt-lidar-sender &>/dev/null; then
  echo "Building mqtt-lidar-sender container..."
  
  # Create a temporary Dockerfile for the lidar sender
  cat > Dockerfile.lidar << EOF
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir rplidar-py

# Copy the sender code and lidar integration example
COPY sender.py .
COPY ../examples/lidar_integration.py .

# Make the script executable
COPY run_lidar_sender.sh .
RUN chmod +x run_lidar_sender.sh

# Set the entrypoint to the lidar integration script
CMD ["python3", "lidar_integration.py"]
EOF

  # Build the image
  docker build -t mqtt-lidar-sender -f Dockerfile.lidar .
  
  # Clean up the temporary Dockerfile
  rm Dockerfile.lidar
fi

# Run the container with the specified environment variables
echo "Starting lidar sender with:"
echo "  BROKER_ADDRESS: $BROKER_ADDRESS"
echo "  BROKER_PORT: $BROKER_PORT"
echo "  TOPIC: $TOPIC"
echo "  DEVICE_ID: $DEVICE_ID"
echo "  LIDAR_PORT: $LIDAR_PORT"
echo "  PUBLISH_RATE: $PUBLISH_RATE"
echo ""

docker run --rm \
  --device=$LIDAR_PORT:$LIDAR_PORT \
  -e BROKER_ADDRESS="$BROKER_ADDRESS" \
  -e BROKER_PORT="$BROKER_PORT" \
  -e TOPIC="$TOPIC" \
  -e DEVICE_ID="$DEVICE_ID" \
  -e LIDAR_PORT="$LIDAR_PORT" \
  -e PUBLISH_RATE="$PUBLISH_RATE" \
  mqtt-lidar-sender
