#!/bin/bash

# Start Avahi for mDNS discovery (needed for wifi sync)
/etc/init.d/avahi-daemon start

# Start usbmuxd in background
usbmuxd -U usbmux -v

# Start the FastAPI backend
exec uvicorn main:app --host 0.0.0.0 --port 8000
