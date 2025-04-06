# Environment Variables Guide

This document explains all the environment variables used in the MQTT Sensor Data Pipeline.

## Using Environment Variables

The project uses a `.env` file in the root directory to manage environment variables. You can customize the system by editing this file.

### On Mac Mini

The Docker Compose setup automatically reads from the `.env` file. After editing the file, restart the services:

```bash
docker compose down
docker compose up -d
```

### On Raspberry Pi

Use the provided script with command-line options:

```bash
./run_sender.sh --address 192.168.1.100 --topic sensor/lidar
```

Or set them directly when running the Docker container:

```bash
docker run -e BROKER_ADDRESS=192.168.1.100 -e TOPIC=sensor/lidar mqtt-sender
```

## Available Environment Variables

### MQTT Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `MQTT_BROKER_PORT` | Port for MQTT broker communication | `1883` |
| `MQTT_WEBSOCKET_PORT` | Port for MQTT WebSocket connections | `9001` |
| `MQTT_TOPIC` | Topic for publishing/subscribing to messages | `sensor/test` |

### Database Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_DIR` | Directory to store the SQLite database | `./data` |
| `DB_FILENAME` | Name of the SQLite database file | `sensor_data.db` |

### Sender Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `BROKER_ADDRESS` | Address of the MQTT broker | `mqtt-broker` |
| `SEND_INTERVAL` | Time between messages in seconds | `0.1` |
| `MESSAGE_COUNT` | Number of test messages to send | `1000` |
| `DEVICE_ID` | Identifier for the sending device | `raspi_test` |

### Web UI Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `SQLITEBROWSER_PORT` | Port for the SQLite Browser web interface | `3000` |

### Network Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `MAC_MINI_IP` | IP address of the Mac Mini on the local network | `192.168.1.X` |

## Environment Files for Different Environments

You can create multiple environment files for different setups:

### Development Setup

Create a `.env.dev` file:

```
MQTT_BROKER_PORT=1883
MQTT_TOPIC=sensor/dev
DB_FILENAME=sensor_data_dev.db
SEND_INTERVAL=0.5
MESSAGE_COUNT=100
```

Run with:

```bash
docker compose --env-file .env.dev up -d
```

### Production Setup

Create a `.env.prod` file:

```
MQTT_BROKER_PORT=1883
MQTT_TOPIC=sensor/lidar
DB_FILENAME=sensor_data_prod.db
SEND_INTERVAL=0.1
MAC_MINI_IP=192.168.1.100
```

Run with:

```bash
docker compose --env-file .env.prod up -d
```

## Environment Variables in the Receiver

The receiver container uses the following variables:

| Variable | Description | Usage |
|----------|-------------|-------|
| `BROKER_ADDRESS` | Address of the MQTT broker | Connection target |
| `BROKER_PORT` | Port of the MQTT broker | Connection port |
| `TOPIC` | MQTT topic to subscribe to | Message subscription |
| `DATA_DIR` | Directory for data storage | Database location |
| `DB_FILENAME` | Name of the database file | Database filename |

These are automatically set from the Docker Compose environment configuration.
