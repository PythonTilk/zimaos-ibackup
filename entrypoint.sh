#!/bin/bash

# Clean up stale PID files to allow clean restarts
rm -f /run/dbus/pid /run/avahi-daemon/pid /run/avahi-daemon//pid

# Start dbus (required by avahi)
mkdir -p /var/run/dbus
dbus-daemon --system --fork

# Start Avahi for mDNS discovery (needed for wifi sync)
avahi-daemon -D

# Start usbmuxd in background (daemonize)
usbmuxd --allow-heartless-wifi &

# Start the FastAPI backend
exec uvicorn main:app --host 0.0.0.0 --port 8000
