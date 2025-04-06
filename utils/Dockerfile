# Dockerfile for database utilities
FROM python:3.9-slim

WORKDIR /app

# Install SQLite and dependencies
RUN apt-get update && \
    apt-get install -y sqlite3 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy utility scripts
COPY *.py ./

# Create output directory
RUN mkdir -p /output

ENTRYPOINT ["python"]
CMD ["db_analyzer.py", "--help"]
