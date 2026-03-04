# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Final Image
FROM python:3.11-slim

# Install libimobiledevice and required dependencies
RUN apt-get update && apt-get install -y \
    libimobiledevice-utils \
    usbmuxd \
    avahi-daemon \
    dbus \
    libimobiledevice-1.0-6 \
    python3-dev \
    gcc \
    curl \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Set up entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Volumes
VOLUME [ "/var/lib/lockdown", "/app/config", "/backups" ]

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
