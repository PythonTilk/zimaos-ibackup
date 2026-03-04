#!/bin/bash

# Start dbus (required by avahi)
mkdir -p /var/run/dbus
dbus-daemon --system --fork

# Start Avahi for mDNS discovery (needed for wifi sync)
avahi-daemon -D

# Start usbmuxd in background
usbmuxd -U usbmux -v

# Start the FastAPI backend
exec uvicorn main:app --host 0.0.0.0 --port 8000
