from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import os
import subprocess
from datetime import datetime
import json
import logging

from scheduler import start_scheduler
from libimobiledevice import LibIMobileDevice
from database import init_db, get_db

app = FastAPI()

# Enable CORS for frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize DB
init_db()


# Start Background Scheduler
@app.on_event("startup")
def startup_event():
    logger.info("Starting background scheduler...")
    start_scheduler()


# Mount frontend
app.mount("/static", StaticFiles(directory="frontend/dist", html=True), name="static")


@app.get("/api/devices")
def get_devices():
    db = get_db()

    # 1. Scan for currently connected devices
    connected_devices = LibIMobileDevice.get_connected_devices()

    # 2. Get saved devices from DB
    saved_devices = db.execute("SELECT * FROM devices").fetchall()
    saved_dict = {row["udid"]: dict(row) for row in saved_devices}

    # Merge data
    results = []

    for dev in connected_devices:
        udid = dev["udid"]
        conn_type = dev["type"]

        info = LibIMobileDevice.get_device_info(udid)
        name = info.get("DeviceName", "Unknown") if info else "Unknown"

        if udid in saved_dict:
            device_data = saved_dict[udid]
            device_data["connected"] = True
            device_data["connection_type"] = conn_type
            device_data["name"] = name
            results.append(device_data)
        else:
            new_dev = {
                "udid": udid,
                "name": name,
                "connected": True,
                "connection_type": conn_type,
                "last_backup": None,
                "backup_path": f"/backups/{udid}",
                "overwrite_strategy": "incremental",  # or 'full'
                "paired": LibIMobileDevice.is_paired(udid),
            }
            results.append(new_dev)

            # Save to DB
            db.execute(
                """INSERT OR IGNORE INTO devices 
                          (udid, name, backup_path, overwrite_strategy) 
                          VALUES (?, ?, ?, ?)""",
                (udid, name, new_dev["backup_path"], new_dev["overwrite_strategy"]),
            )
            db.commit()

    # Add offline saved devices
    connected_udids = [d["udid"] for d in connected_devices]
    for udid, data in saved_dict.items():
        if udid not in connected_udids:
            data["connected"] = False
            data["connection_type"] = None
            data["paired"] = False
            results.append(data)

    return results


@app.post("/api/devices/{udid}/pair")
def pair_device(udid: str):
    success, msg = LibIMobileDevice.pair_device(udid)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "success", "message": "Paired successfully"}


class DeviceConfig(BaseModel):
    backup_path: str
    overwrite_strategy: str


@app.post("/api/devices/{udid}/config")
def update_config(udid: str, config: DeviceConfig):
    db = get_db()
    db.execute(
        """UPDATE devices SET backup_path = ?, overwrite_strategy = ? WHERE udid = ?""",
        (config.backup_path, config.overwrite_strategy, udid),
    )
    db.commit()
    return {"status": "success"}


@app.post("/api/devices/{udid}/backup")
def trigger_backup(udid: str, background_tasks: BackgroundTasks):
    db = get_db()
    row = db.execute("SELECT * FROM devices WHERE udid = ?", (udid,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Device not found in DB")

    device_data = dict(row)

    # We trigger in background
    from scheduler import run_backup_job

    background_tasks.add_task(
        run_backup_job,
        udid,
        device_data["backup_path"],
        device_data["overwrite_strategy"],
    )

    return {"status": "success", "message": "Backup started in background"}


@app.get("/api/logs")
def get_logs(udid: str | None = None):
    db = get_db()
    if udid:
        logs = db.execute(
            "SELECT * FROM logs WHERE udid = ? ORDER BY timestamp DESC LIMIT 50",
            (udid,),
        ).fetchall()
    else:
        logs = db.execute(
            "SELECT * FROM logs ORDER BY timestamp DESC LIMIT 50"
        ).fetchall()
    return [dict(log) for log in logs]
