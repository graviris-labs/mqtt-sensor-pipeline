# Multi-stage build for the receiver

# Builder stage
FROM python:3.9-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.9-slim

WORKDIR /app

# Create data directory
RUN mkdir -p /data

# Install only the required runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    sqlite3 \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder stage
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY receiver.py .

CMD ["python", "receiver.py"]