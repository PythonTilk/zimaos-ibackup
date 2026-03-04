from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import logging

from database import get_db
from libimobiledevice import LibIMobileDevice

logger = logging.getLogger(__name__)

# Run backup jobs sequentially to avoid overloading usbmuxd and disk IO
scheduler = BackgroundScheduler({"apscheduler.job_defaults.max_instances": "1"})


def run_backup_job(udid: str, backup_path: str, strategy: str):
    logger.info(f"Starting backup task for device {udid}")

    db = get_db()

    # 1. Log start
    db.execute(
        """INSERT INTO logs (udid, level, message) VALUES (?, 'INFO', ?)""",
        (udid, "Backup started"),
    )
    db.commit()

    try:
        success, msg = LibIMobileDevice.backup_device(udid, backup_path, strategy)

        if success:
            db.execute(
                """UPDATE devices SET last_backup_time = CURRENT_TIMESTAMP WHERE udid = ?""",
                (udid,),
            )
            db.execute(
                """INSERT INTO logs (udid, level, message) VALUES (?, 'INFO', ?)""",
                (udid, "Backup finished successfully"),
            )
            logger.info(f"Backup {udid} success: {msg}")
        else:
            db.execute(
                """INSERT INTO logs (udid, level, message) VALUES (?, 'ERROR', ?)""",
                (udid, f"Backup failed: {msg}"),
            )
            logger.error(f"Backup {udid} failed: {msg}")

    except Exception as e:
        logger.exception("Error in backup job")
        db.execute(
            """INSERT INTO logs (udid, level, message) VALUES (?, 'ERROR', ?)""",
            (udid, f"Exception during backup: {str(e)}"),
        )
    finally:
        db.commit()


def check_for_backups():
    logger.info("Running hourly check for backups")

    db = get_db()

    # Get reachable paired devices
    connected = LibIMobileDevice.get_connected_devices()
    reachable_udids = [d["udid"] for d in connected]

    # Check DB for devices due for backup
    devices = db.execute("""SELECT * FROM devices""").fetchall()

    for row in devices:
        device = dict(row)
        udid = device["udid"]

        if udid not in reachable_udids:
            continue

        if not LibIMobileDevice.is_paired(udid):
            continue

        # Check last backup time
        last_backup = device.get("last_backup_time")
        if not last_backup:
            # Never backed up
            should_backup = True
        else:
            try:
                last_time = datetime.strptime(last_backup, "%Y-%m-%d %H:%M:%S")
                if datetime.now() - last_time > timedelta(hours=24):
                    should_backup = True
                else:
                    should_backup = False
            except ValueError:
                should_backup = True  # Corrupt date, assume yes

        if should_backup:
            logger.info(f"Device {udid} is due for backup. Enqueueing.")
            # Run it async using apscheduler job
            scheduler.add_job(
                run_backup_job,
                args=[udid, device["backup_path"], device["overwrite_strategy"]],
            )


def start_scheduler():
    scheduler.add_job(
        check_for_backups,
        trigger=IntervalTrigger(hours=1),
        id="hourly_backup_check",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started. Background tasks enabled.")
