#!/bin/bash
# Script to initialize the SQLite database schema

# Ensure data directory exists
mkdir -p ./data

# Check if database already exists
if [ -f "./data/sensor_data.db" ]; then
  echo "Database already exists at ./data/sensor_data.db"
  read -p "Do you want to recreate it? (y/n): " confirm
  if [ "$confirm" != "y" ]; then
    echo "Exiting without changes"
    exit 0
  fi
  echo "Backing up existing database..."
  cp ./data/sensor_data.db "./data/sensor_data_backup_$(date +%Y%m%d_%H%M%S).db"
fi

# Create new database with schema
echo "Creating new database..."
cat ./examples/schema.sql | docker run -i --rm \
  -v "$(pwd)/data:/data" \
  alpine:latest \
  sh -c "cat > /tmp/schema.sql && sqlite3 /data/sensor_data.db < /tmp/schema.sql"

# Verify database was created
if [ $? -eq 0 ]; then
  echo "Database successfully created at ./data/sensor_data.db"
  echo "Schema initialized with tables:"
  docker run -i --rm \
    -v "$(pwd)/data:/data" \
    alpine:latest \
    sqlite3 /data/sensor_data.db ".tables"
else
  echo "Error creating database"
  exit 1
fi

echo "Setup complete!"
