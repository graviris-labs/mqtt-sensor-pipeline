# Multi-stage build for LIDAR 3D Point Cloud Visualizer

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

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxrender1 \
    libx11-6 \
    sqlite3 \
    libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create data directory for SQLite access
RUN mkdir -p /data

# Copy Python packages from builder stage
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY visualizer.py .
COPY point_cloud_server.py .
COPY advanced_visualizer.py .

# Expose port for web interface
EXPOSE 8050

# Default command
CMD ["python", "point_cloud_server.py"]