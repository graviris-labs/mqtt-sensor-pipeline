#!/bin/bash
# Script to run the sender container on Raspberry Pi with environment variables

# Display usage information
show_usage() {
  echo "Usage: $0 [options]"
  echo ""
  echo "Options:"
  echo "  -h, --help            Show this help message"
  echo "  -a, --address IP      Set the MQTT broker address (required)"
  echo "  -p, --port PORT       Set the MQTT broker port (default: 1883)"
  echo "  -t, --topic TOPIC     Set the MQTT topic (default: sensor/test)"
  echo "  -i, --interval SEC    Set the message sending interval in seconds (default: 0.1)"
  echo "  -c, --count COUNT     Set the number of messages to send (default: 1000)"
  echo "  -d, --device ID       Set the device identifier (default: raspi_test)"
  echo ""
  echo "Example:"
  echo "  $0 --address 192.168.1.100 --topic sensor/lidar"
}

# Default values
BROKER_PORT=1883
TOPIC="sensor/test"
INTERVAL=0.1
MESSAGE_COUNT=1000
DEVICE_ID="raspi_test"

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
    -i|--interval)
      INTERVAL="$2"
      shift 2
      ;;
    -c|--count)
      MESSAGE_COUNT="$2"
      shift 2
      ;;
    -d|--device)
      DEVICE_ID="$2"
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

# Build the container if it doesn't exist
if ! docker image inspect mqtt-sender &>/dev/null; then
  echo "Building mqtt-sender container..."
  docker build -t mqtt-sender .
fi

# Run the container with the specified environment variables
echo "Starting sender with:"
echo "  BROKER_ADDRESS: $BROKER_ADDRESS"
echo "  BROKER_PORT: $BROKER_PORT"
echo "  TOPIC: $TOPIC"
echo "  INTERVAL: $INTERVAL"
echo "  MESSAGE_COUNT: $MESSAGE_COUNT"
echo "  DEVICE_ID: $DEVICE_ID"
echo ""

docker run --rm \
  -e BROKER_ADDRESS="$BROKER_ADDRESS" \
  -e BROKER_PORT="$BROKER_PORT" \
  -e TOPIC="$TOPIC" \
  -e INTERVAL="$INTERVAL" \
  -e MESSAGE_COUNT="$MESSAGE_COUNT" \
  -e DEVICE_ID="$DEVICE_ID" \
  mqtt-sender
