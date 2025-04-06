# Optimized Dockerfile for the sender (Raspberry Pi)
FROM python:3.9-alpine

WORKDIR /app

# Alpine needs to install build tools for some Python packages
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    && pip install --no-cache-dir paho-mqtt==1.6.1 \
    && apk del .build-deps

COPY sender.py .

CMD ["python", "sender.py"]