#!/usr/bin/env python3
"""
ActivityWatch Employee Watcher
Runs on employee machines and sends activity data to central server.

Installation:
1. Install Python 3.8+ on the employee machine
2. Run: pip install requests pywin32
3. Edit CONFIG section below with server IP and employee details
4. Run: python aw_employee_watcher.py

For auto-start, use the install_service.bat script.
"""

import time
import socket
import logging
import requests
import ctypes
import sys
from datetime import datetime, timezone
from threading import Thread

# ============================================================
# CONFIGURATION - EDIT THESE VALUES
# ============================================================
CONFIG = {
    # Central server address (IP or hostname of the admin machine)
    "SERVER_URL": "http://192.168.1.100:5601",  # CHANGE THIS to your server IP

    # Employee information
    "EMPLOYEE_ID": "emp001",      # Unique ID for this employee
    "EMPLOYEE_NAME": "John Doe",  # Employee's name
    "EMPLOYEE_EMAIL": "",         # Optional email
    "DEPARTMENT": "Engineering",  # Department name

    # Polling intervals (in seconds)
    "WINDOW_POLL_INTERVAL": 5,    # How often to check active window
    "AFK_POLL_INTERVAL": 5,       # How often to check AFK status
    "AFK_TIMEOUT": 180,           # Seconds of inactivity before marking as AFK
}
# ============================================================

# Auto-detect device info
HOSTNAME = socket.gethostname()
DEVICE_ID = HOSTNAME

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'aw_watcher_{HOSTNAME}.log')
    ]
)
logger = logging.getLogger(__name__)


def get_active_window():
    """Get the currently active window title and application name (Windows)"""
    try:
        import win32gui
        import win32process
        import psutil

        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None, None

        # Get window title
        title = win32gui.GetWindowText(hwnd)

        # Get process name
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            process = psutil.Process(pid)
            app = process.name()
        except:
            app = "unknown"

        return app, title
    except Exception as e:
        logger.error(f"Error getting active window: {e}")
        return None, None


def get_idle_time():
    """Get system idle time in seconds (Windows)"""
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [('cbSize', ctypes.c_uint), ('dwTime', ctypes.c_uint)]

        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0
    except Exception as e:
        logger.error(f"Error getting idle time: {e}")
        return 0


class EmployeeWatcher:
    """Main watcher class that monitors window activity and AFK status"""

    def __init__(self):
        self.server_url = CONFIG["SERVER_URL"]
        self.employee_id = CONFIG["EMPLOYEE_ID"]
        self.running = False
        self.last_window = None
        self.last_afk_status = None

    def register_employee(self):
        """Register this employee and device with the server"""
        try:
            # Register/update employee
            employee_data = {
                "id": CONFIG["EMPLOYEE_ID"],
                "name": CONFIG["EMPLOYEE_NAME"],
                "email": CONFIG["EMPLOYEE_EMAIL"],
                "department": CONFIG["DEPARTMENT"],
                "role": "employee"
            }
            r = requests.post(
                f"{self.server_url}/api/0/admin/employees",
                json=employee_data,
                timeout=10
            )
            if r.status_code in [200, 201]:
                logger.info(f"Employee registered: {CONFIG['EMPLOYEE_ID']}")
            else:
                logger.warning(f"Employee registration response: {r.status_code}")

            # Register device
            device_data = {
                "id": DEVICE_ID,
                "hostname": HOSTNAME,
                "employee_id": CONFIG["EMPLOYEE_ID"],
                "device_type": "desktop",
                "os_info": f"Windows {sys.getwindowsversion().major}"
            }
            r = requests.post(
                f"{self.server_url}/api/0/admin/devices",
                json=device_data,
                timeout=10
            )
            if r.status_code in [200, 201]:
                logger.info(f"Device registered: {DEVICE_ID}")

        except Exception as e:
            logger.error(f"Error registering employee/device: {e}")

    def create_bucket(self, bucket_id, bucket_type, client):
        """Create a bucket on the server"""
        try:
            bucket_data = {
                "id": bucket_id,
                "name": bucket_id,
                "type": bucket_type,
                "client": client,
                "hostname": HOSTNAME
            }
            r = requests.post(
                f"{self.server_url}/api/0/buckets/{bucket_id}",
                json=bucket_data,
                timeout=10
            )
            if r.status_code in [200, 304]:
                logger.info(f"Bucket ready: {bucket_id}")
                return True
        except Exception as e:
            logger.error(f"Error creating bucket {bucket_id}: {e}")
        return False

    def send_heartbeat(self, bucket_id, data, pulsetime=60):
        """Send a heartbeat event to the server"""
        try:
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "duration": 0,
                "data": data,
                "employee_id": self.employee_id,
                "device_id": DEVICE_ID
            }
            r = requests.post(
                f"{self.server_url}/api/0/buckets/{bucket_id}/heartbeat?pulsetime={pulsetime}",
                json=event,
                timeout=5
            )
            return r.status_code == 200
        except requests.exceptions.ConnectionError:
            logger.warning("Cannot connect to server - will retry")
            return False
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
            return False

    def watch_windows(self):
        """Monitor active window and send heartbeats"""
        bucket_id = f"aw-watcher-window_{DEVICE_ID}"
        self.create_bucket(bucket_id, "currentwindow", "aw-watcher-window")

        poll_interval = CONFIG["WINDOW_POLL_INTERVAL"]
        pulsetime = poll_interval * 2.0

        while self.running:
            try:
                app, title = get_active_window()
                if app and title:
                    window_data = {"app": app, "title": title}
                    if window_data != self.last_window:
                        logger.debug(f"Window changed: {app} - {title[:50]}")
                    self.send_heartbeat(bucket_id, window_data, pulsetime)
                    self.last_window = window_data
            except Exception as e:
                logger.error(f"Window watcher error: {e}")

            time.sleep(poll_interval)

    def watch_afk(self):
        """Monitor AFK status and send heartbeats"""
        bucket_id = f"aw-watcher-afk_{DEVICE_ID}"
        self.create_bucket(bucket_id, "afkstatus", "aw-watcher-afk")

        poll_interval = CONFIG["AFK_POLL_INTERVAL"]
        afk_timeout = CONFIG["AFK_TIMEOUT"]

        while self.running:
            try:
                idle_time = get_idle_time()
                is_afk = idle_time >= afk_timeout
                status = "afk" if is_afk else "not-afk"

                if status != self.last_afk_status:
                    logger.info(f"AFK status changed: {status}")
                    self.last_afk_status = status

                self.send_heartbeat(bucket_id, {"status": status}, pulsetime=60)

            except Exception as e:
                logger.error(f"AFK watcher error: {e}")

            time.sleep(poll_interval)

    def start(self):
        """Start the watcher"""
        logger.info("=" * 60)
        logger.info("ActivityWatch Employee Watcher")
        logger.info("=" * 60)
        logger.info(f"Server: {self.server_url}")
        logger.info(f"Employee: {self.employee_id}")
        logger.info(f"Device: {DEVICE_ID}")
        logger.info("=" * 60)

        # Test server connection
        try:
            r = requests.get(f"{self.server_url}/api/0/info", timeout=5)
            if r.status_code == 200:
                logger.info("Connected to server successfully")
            else:
                logger.error(f"Server returned: {r.status_code}")
                return
        except Exception as e:
            logger.error(f"Cannot connect to server: {e}")
            logger.error("Please check SERVER_URL in configuration")
            return

        # Register employee and device
        self.register_employee()

        # Start watchers
        self.running = True

        window_thread = Thread(target=self.watch_windows, daemon=True)
        afk_thread = Thread(target=self.watch_afk, daemon=True)

        window_thread.start()
        afk_thread.start()

        logger.info("Watchers started - Press Ctrl+C to stop")

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping watchers...")
            self.running = False

        logger.info("Watcher stopped")

    def stop(self):
        """Stop the watcher"""
        self.running = False


if __name__ == "__main__":
    watcher = EmployeeWatcher()
    watcher.start()
