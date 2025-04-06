# Dockerfile for the receiver (Mac Mini)
FROM python:3.9-slim

WORKDIR /app

# Create data directory
RUN mkdir -p /data

# Install dependencies including SQLite
RUN apt-get update && \
    apt-get install -y sqlite3 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY receiver.py .

# Ensure SQLite is properly configured
RUN echo ".databases" | sqlite3

CMD ["python", "receiver.py"]