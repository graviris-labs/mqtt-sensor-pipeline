# MQTT Sensor Data Pipeline

A containerized solution for transmitting and storing sensor data from a Raspberry Pi to a Mac Mini using MQTT and SQLite.

## Quick Start

1. **On Mac Mini**:
   ```bash
   # Clone the repository
   git clone https://github.com/your-username/mqtt-sensor-pipeline.git
   cd mqtt-sensor-pipeline
   
   # Edit .env file to set your Mac Mini's IP
   nano .env
   
   # Start the services
   docker compose up -d
   ```

2. **On Raspberry Pi**:
   ```bash
   # Copy the sender directory
   scp -r user@mac-mini:/path/to/mqtt-sensor-pipeline/sender .
   cd sender
   
   # Run the sender
   ./run_sender.sh --address 192.168.1.X
   ```

3. **Access the SQLite browser** at `http://mac-mini-ip:3000`

## Project Structure

```
mqtt-sensor-pipeline/
├── docker-compose.yml           # Main orchestration file with SQLite setup
├── mosquitto/                   # MQTT broker configuration
│   └── config/
│       └── mosquitto.conf
├── sender/                      # Raspberry Pi sender component
│   ├── Dockerfile
│   ├── requirements.txt
│   └── sender.py
├── receiver/                    # Mac Mini receiver component
│   ├── Dockerfile
│   ├── requirements.txt
│   └── receiver.py
├── examples/                    # Example code and schemas
│   ├── schema.sql               # SQLite database schema
│   └── lidar_integration.py     # Example for real lidar integration
├── utils/                       # Utility scripts
│   ├── db_analyzer.py           # For analyzing stored data
│   ├── sqlite_helper.py         # Database maintenance utilities
│   ├── requirements.txt         # Utility dependencies
│   └── Dockerfile               # Container for utilities
├── scripts/                     # Helper scripts
│   └── setup_database.sh        # Manual database initialization
├── docs/                        # Documentation
│   ├── sqlite_guide.md          # Guide to using SQLite
│   └── env_variables.md         # Environment variables documentation
├── .env                         # Environment variables configuration
└── data/                        # Persistent data storage (mounted volume)
    └── sensor_data.db           # SQLite database
```

## Features

- **Lightweight containerized architecture** optimized for Raspberry Pi
- **MQTT message broker** for reliable and efficient communication
- **SQLite storage** for structured data persistence
- **Performance metrics** tracking for latency and throughput
- **Data analysis tools** for visualizing and analyzing stored data
- **Dual database initialization** for robust setup

## Getting Started

### Prerequisites

- Docker and Docker Compose on the Mac Mini
- Docker on the Raspberry Pi
- Network connectivity between Raspberry Pi and Mac Mini

### Setup Instructions

#### On Mac Mini:

1. Clone this repository:
   ```bash
   git clone https://github.com/your-username/mqtt-sensor-pipeline.git
   cd mqtt-sensor-pipeline
   ```

2. Create necessary directories:
   ```bash
   mkdir -p mosquitto/config mosquitto/data mosquitto/log data
   ```

3. Copy the configuration file to the mosquitto directory:
   ```bash
   cp examples/mosquitto.conf mosquitto/config/
   ```

4. Edit the `.env` file to set your configuration:
   ```bash
   # Update MAC_MINI_IP to your actual IP address
   MAC_MINI_IP=192.168.1.100
   ```

5. Start the services:
   ```bash
   docker compose up -d
   ```
   This will start:
   - The MQTT broker
   - The database initialization service
   - The receiver service
   - The SQLite browser web interface

#### On Raspberry Pi:

1. Copy the `sender` directory to your Raspberry Pi.

2. Make the run script executable:
   ```bash
   chmod +x run_sender.sh
   ```

3. Run the sender using the script:
   ```bash
   ./run_sender.sh --address 192.168.1.X
   ```
   (Replace 192.168.1.X with your Mac Mini's IP address)

   Or manually build and run the container:
   ```bash
   docker build -t mqtt-sender .
   docker run -e BROKER_ADDRESS=192.168.1.X mqtt-sender
   ```

## Database Setup

The system uses a dual approach for database initialization:

1. **Docker Compose Initialization**:
   - The `db-init` service in `docker-compose.yml` checks for and creates the database
   - Runs once during system startup

2. **Receiver Self-Check**:
   - The receiver code checks if the database exists and has the correct schema
   - Creates tables and indexes if needed
   - This ensures the database is ready even if you run the receiver independently

### Manual Database Setup (if needed):

You can also manually initialize the database:
```bash
./scripts/setup_database.sh
```

## Data Storage

The system uses SQLite for efficient, reliable storage with the following schema:

- **sensor_data**: Core message metadata (timestamp, device ID, message ID, latency)
- **sensor_readings**: Structured sensor values
- **performance_stats**: Periodic performance metrics

## Accessing the Data

### Using the SQLite Browser

After starting the services, access the browser at:
```
http://localhost:3000
```

### Using the Database Utilities

```bash
# Run the analyzer
cd utils
docker compose run db-analyzer

# Run database maintenance
cd utils
docker compose run sqlite-helper --action vacuum
```

## Analyzing the Data

Use the provided `db_analyzer.py` script to analyze and visualize the collected data:

```bash
cd utils
docker compose run db-analyzer --output ./output --export
```

This will:
- Generate summary statistics
- Create latency trend visualizations
- Analyze sensor reading patterns
- Export data to CSV format for further analysis

## Customization

### Environment Variables

The project uses environment variables for configuration, managed through the `.env` file.

For a complete list of all available variables and their documentation, see [Environment Variables Guide](docs/env_variables.md).

Key variables include:

- `BROKER_ADDRESS`: IP/hostname of the MQTT broker
- `MQTT_TOPIC`: Topic for publishing/subscribing
- `DB_FILENAME`: SQLite database filename
- `MAC_MINI_IP`: IP address of your Mac Mini

You can create different environment files (e.g., `.env.dev`, `.env.prod`) for different setups.

## SQLite Management

The system includes several tools for SQLite database management:

1. **Web-based SQLite Browser**:
   - Access at `http://localhost:3000`
   - View and query the database
   - Modify data if needed

2. **SQLite Helper Utility**:
   ```bash
   cd utils
   docker compose run sqlite-helper --db /data/sensor_data.db --action check
   ```
   
   Available actions:
   - `check`: Check database health and size
   - `vacuum`: Reclaim storage space
   - `optimize`: Optimize database performance
   - `prune`: Delete old data
   - `export`: Export data to CSV
   - `rebuild`: Recreate database to optimize structure

## Next Steps

After testing with the simulation data, you can:

1. Modify the sender script to read from your actual lidar sensor
2. Adjust the database schema to store your specific sensor data structure
3. Develop custom visualization or analysis tools for your sensor data

## Performance Considerations

The system is designed for performance on constrained devices:

- The SQLite database uses indexed fields for efficient queries
- WAL journal mode enables better concurrent access
- Batch database operations improve throughput
- Connection retry logic ensures reliability
- Periodic performance statistics help identify bottlenecks

## License

[Your chosen license]