# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Build libimobiledevice from source for Avahi/mDNS support
FROM python:3.11-slim AS lib-builder

RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    git \
    autoconf \
    automake \
    libtool-bin \
    libssl-dev \
    libusb-1.0-0-dev \
    libavahi-client-dev \
    libcurl4-openssl-dev \
    python3-dev \
    cython3 \
    clang \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

RUN git clone https://github.com/libimobiledevice/libplist.git && \
    cd libplist && ./autogen.sh --without-cython && make -j$(nproc) && make install

RUN git clone https://github.com/libimobiledevice/libimobiledevice-glue.git && \
    cd libimobiledevice-glue && \
    PKG_CONFIG_PATH=/usr/local/lib/pkgconfig ./autogen.sh && \
    make -j$(nproc) && make install

RUN git clone https://github.com/libimobiledevice/libtatsu.git && \
    cd libtatsu && \
    PKG_CONFIG_PATH=/usr/local/lib/pkgconfig ./autogen.sh && \
    make -j$(nproc) && make install

RUN git clone https://github.com/libimobiledevice/libusbmuxd.git && \
    cd libusbmuxd && \
    PKG_CONFIG_PATH=/usr/local/lib/pkgconfig ./autogen.sh && \
    make -j$(nproc) && make install

RUN git clone https://github.com/libimobiledevice/libimobiledevice.git && \
    cd libimobiledevice && \
    PKG_CONFIG_PATH=/usr/local/lib/pkgconfig ./autogen.sh --without-cython && \
    make -j$(nproc) && make install

RUN git clone https://github.com/tihmstar/libgeneral.git && \
    cd libgeneral && \
    PKG_CONFIG_PATH=/usr/local/lib/pkgconfig ./autogen.sh && \
    make -j$(nproc) && make install

RUN git clone https://github.com/tihmstar/usbmuxd2.git && \
    cd usbmuxd2 && \
    sed -i 's/-std=c++20/-std=c++17/g' configure.ac && \
    CC=clang CXX=clang++ PKG_CONFIG_PATH=/usr/local/lib/pkgconfig ./autogen.sh && \
    make -j$(nproc) && make install

# Stage 3: Final Image
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    avahi-daemon \
    avahi-utils \
    dbus \
    libssl3 \
    libusb-1.0-0 \
    libavahi-client3 \
    curl \
    iputils-ping \
    libcurl4 \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy compiled libraries and binaries from builder
COPY --from=lib-builder /usr/local/lib/ /usr/local/lib/
COPY --from=lib-builder /usr/local/bin/ /usr/local/bin/
COPY --from=lib-builder /usr/local/sbin/ /usr/local/sbin/

# Update library cache so it finds the newly copied libs
RUN ldconfig

# Add usbmux user
RUN adduser --system --no-create-home --group usbmux

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
