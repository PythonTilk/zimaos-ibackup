# ZimaOS iPhone Auto Backup

A fully containerized solution designed for **ZimaOS** (and other Linux environments) to automatically back up your iOS devices (iPhones/iPads) over Wi-Fi. 

Powered by [`libimobiledevice`](https://libimobiledevice.org/) under the hood, this project wraps the command-line tools into a sleek React frontend and an automated Python backend.

![ZimaOS iPhone Backup](https://img.shields.io/badge/Status-Active-brightgreen.svg) ![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)

## Features

- 📱 **Wireless Backups:** Once initially paired via USB, all subsequent backups happen seamlessly over Wi-Fi.
- 🎨 **Web Interface:** A modern, responsive React + Tailwind CSS web UI to monitor device status, trigger backups, and change settings.
- ⏰ **Automated Scheduling:** A background task checks every hour to see if an authorized, reachable iOS device is due for a backup (default interval: 24 hours).
- ⚙️ **Custom Strategies:** Choose between standard **Incremental** backups (faster, saves space) or **Full** overwrites for each device.
- 🐳 **Dockerized:** Easy deployment using `docker-compose`.

## Prerequisites

- A Linux host (ZimaOS, CasaOS, Ubuntu, Debian, etc.)
- Docker and Docker Compose installed.
- A physical USB connection for the initial pairing process.

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/PythonTilk/zimaos-ibackup.git
   cd zimaos-ibackup
   ```

2. **Customize Storage Volumes (Optional):**
   Open `docker-compose.yml` and adjust the storage mapping if you want backups saved to a specific pool.
   ```yaml
   volumes:
     - /var/lib/lockdown:/var/lib/lockdown      # Persists pairing certs
     - /dev/bus/usb:/dev/bus/usb                # USB Passthrough
     - /var/run/udev:/var/run/udev:ro           # USB hot-plug detection
     - ./config:/app/config                     # App configuration/DB
     - /your/custom/zimaos/pool:/backups        # <--- Change this to your preferred storage!
   ```

3. **Start the container:**
   ```bash
   docker-compose up -d --build
   ```

4. **Access the Web Interface:**
   Open your browser and navigate to:
   `http://<YOUR_ZIMAOS_IP>:8000`

## How to Use (Initial Pairing)

To enable automatic wireless backups, you must pair your device over USB **once**.

1. Connect your iPhone/iPad to the ZimaOS machine using a **USB cable**.
2. Open the web interface. Your device should appear as **Connected (usb)** but "Not Paired".
3. Click the **"Pair"** button in the web UI.
4. Unlock your iPhone. It will prompt you to **"Trust this Computer"**. Accept it and enter your passcode.
5. In the web interface, set your desired Backup Path and Strategy, then hit **Save Settings**.
6. Unplug the USB cable. As long as your iPhone is on the same local network (Wi-Fi), it will now show as **Connected (network)**.
7. **Done!** The background scheduler will automatically back up your device.

## Troubleshooting

- **Device not showing up?** Ensure your `docker-compose.yml` uses `network_mode: host`. iOS wireless sync relies on Bonjour (mDNS) broadcast packets which cannot easily traverse Docker bridge networks.
- **Pairing fails?** Re-plug the USB cable, ensure the device is unlocked *before* clicking pair, and check the container logs for details.
- **Backup fails?** Ensure the mapped backup destination path has enough free space and correct write permissions for the container.

## Architecture

- **Backend:** Python + FastAPI + APScheduler
- **Frontend:** React + Vite + Tailwind CSS
- **Core Libs:** `usbmuxd`, `libimobiledevice-utils`, `avahi-daemon`

## License

MIT License. See [LICENSE](LICENSE) for details.
