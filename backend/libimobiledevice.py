import subprocess
import json
import re
import os
import shutil
import logging

logger = logging.getLogger(__name__)


class LibIMobileDevice:
    @staticmethod
    def _run_cmd(cmd: list):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return True, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)

    @classmethod
    def get_connected_devices(cls):
        """Returns list of dicts: [{'udid': '...', 'type': 'usb|network'}]"""
        success, out, err = cls._run_cmd(["idevice_id", "-l", "-d"])
        devices = []
        if success:
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    udid = parts[0]
                    conn = parts[1]  # usually (USB) or (Network)
                    conn_type = "network" if "Network" in conn else "usb"
                    devices.append({"udid": udid, "type": conn_type})
        return devices

    @classmethod
    def get_device_info(cls, udid: str):
        success, out, err = cls._run_cmd(["ideviceinfo", "-u", udid, "-x"])
        if not success:
            return None

        import plistlib

        try:
            # Output is XML plist
            plist = plistlib.loads(out.encode("utf-8"))
            return plist
        except Exception as e:
            return None

    @classmethod
    def is_paired(cls, udid: str):
        success, out, err = cls._run_cmd(["idevicepair", "-u", udid, "validate"])
        return "SUCCESS" in out

    @classmethod
    def pair_device(cls, udid: str):
        success, out, err = cls._run_cmd(["idevicepair", "-u", udid, "pair"])
        if "SUCCESS" in out:
            return (
                True,
                "Paired successfully. You might need to accept Trust on the device.",
            )
        elif "ERROR" in out or err:
            return False, err if err else out
        return False, "Unknown error during pairing"

    @classmethod
    def backup_device(cls, udid: str, dest_path: str, strategy: str = "incremental"):
        if strategy == "full":
            logger.info(
                f"Full backup requested for {udid}. Removing old backup dir: {dest_path}"
            )
            # Be careful with rm -rf, make sure dest_path is sane
            if os.path.exists(dest_path) and len(dest_path) > 5:
                shutil.rmtree(dest_path, ignore_errors=True)

        os.makedirs(dest_path, exist_ok=True)

        # Enable wifi sync if on USB
        cls._run_cmd(["idevicepair", "-u", udid, "wifi", "on"])

        # Run backup
        cmd = ["idevicebackup2", "-u", udid, "backup", dest_path]
        logger.info(f"Running backup command: {' '.join(cmd)}")

        # We run this one with Popen to stream logs or wait
        # For simplicity, we block here. In prod, we'd want to stream to DB
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )

        if process.stdout:
            for line in process.stdout:
                # We could save this to DB logs here
                logger.info(f"[BACKUP {udid}] {line.strip()}")

        process.wait()

        if process.returncode == 0:
            return True, "Backup completed successfully"
        else:
            return False, f"Backup failed with code {process.returncode}"
