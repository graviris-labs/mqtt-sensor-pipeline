# Dockerfile for LIDAR 3D Point Cloud Visualizer
FROM python:3.9-slim

# Install system dependencies for OpenGL, 3D visualization, and OpenMP
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxrender1 \
    libxext6 \
    libx11-6 \
    sqlite3 \
    libgomp1 \
    libusb-1.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create data directory for SQLite access
RUN mkdir -p /data

# Copy application code
COPY visualizer.py .
COPY point_cloud_server.py .
COPY advanced_visualizer.py .

# Expose port for web interface
EXPOSE 8050

# Default command
CMD ["python", "point_cloud_server.py"]