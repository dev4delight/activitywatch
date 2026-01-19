#!/usr/bin/env python3
"""
ActivityWatch Client Watcher
Collects window and AFK data and sends to MySQL server
"""

import time
import socket
import requests
from datetime import datetime, timezone
import threading
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Server configuration
SERVER_URL = "http://localhost:5601"
DEVICE_ID = socket.gethostname()
EMPLOYEE_ID = "default"  # Changed to match default for aw-webui compatibility

# Collection settings
WINDOW_POLL_INTERVAL = 5  # seconds
AFK_TIMEOUT = 180  # 3 minutes of no input = AFK

class WindowWatcher:
    """Watches active window using heartbeat mechanism (like aw-watcher-window)"""

    def __init__(self):
        self.last_window = None
        self.last_timestamp = None
        self._init_bucket()

    def _init_bucket(self):
        """Initialize bucket with correct type"""
        try:
            bucket_id = f"aw-watcher-window_{DEVICE_ID}"
            requests.post(
                f"{SERVER_URL}/api/0/buckets/{bucket_id}",
                json={
                    "client": "aw-watcher-window",
                    "type": "currentwindow",
                    "hostname": DEVICE_ID
                },
                timeout=5
            )
            logger.info(f"Initialized bucket: {bucket_id}")
        except Exception as e:
            logger.warning(f"Failed to init bucket: {e}")

    def get_active_window(self):
        """Get currently active window info"""
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32

            # Get foreground window
            hwnd = user32.GetForegroundWindow()

            # Get window title
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value

            # Get process name
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            try:
                import psutil
                process = psutil.Process(pid.value)
                app = process.name()
            except:
                app = "Unknown"

            return {"app": app, "title": title}

        except Exception as e:
            logger.error(f"Error getting window: {e}")
            return {"app": "Unknown", "title": "Unknown"}

    def run(self):
        """Main window watching loop - sends heartbeats every poll interval"""
        logger.info("Window watcher started")

        while True:
            try:
                window = self.get_active_window()

                # Send heartbeat - server handles duration calculation
                self.send_heartbeat(window)

                time.sleep(WINDOW_POLL_INTERVAL)

            except Exception as e:
                logger.error(f"Window watcher error: {e}")
                time.sleep(10)

    def send_heartbeat(self, window_data):
        """Send window heartbeat to server"""
        try:
            event = {
                "employee_id": EMPLOYEE_ID,
                "device_id": DEVICE_ID,
                "data": window_data,
                "duration": 0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Use heartbeat endpoint with pulsetime = poll_time * 2
            pulsetime = WINDOW_POLL_INTERVAL * 2.0
            response = requests.post(
                f"{SERVER_URL}/api/0/buckets/aw-watcher-window_{DEVICE_ID}/heartbeat?pulsetime={pulsetime}",
                json=event,
                timeout=5
            )

            if response.status_code == 200:
                pass  # Normal heartbeat
            else:
                logger.warning(f"Heartbeat failed: {response.status_code}")

        except requests.exceptions.ConnectionError:
            logger.warning("Server not available, will retry...")
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")


class AFKWatcher:
    """Watches for AFK (away from keyboard) status"""

    def __init__(self):
        self.last_input_time = datetime.now(timezone.utc)
        self.is_afk = False
        self._init_bucket()

    def _init_bucket(self):
        """Initialize bucket with correct type and send initial not-afk event"""
        try:
            bucket_id = f"aw-watcher-afk_{DEVICE_ID}"
            requests.post(
                f"{SERVER_URL}/api/0/buckets/{bucket_id}",
                json={
                    "client": "aw-watcher-afk",
                    "type": "afkstatus",
                    "hostname": DEVICE_ID
                },
                timeout=5
            )
            logger.info(f"Initialized bucket: {bucket_id}")

            # Send initial not-afk event so aw-webui has data
            requests.post(
                f"{SERVER_URL}/api/0/buckets/{bucket_id}/heartbeat?pulsetime=60",
                json={
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "duration": 0,
                    "data": {"status": "not-afk"}
                },
                timeout=5
            )
            logger.info("Sent initial not-afk event")
        except Exception as e:
            logger.warning(f"Failed to init bucket: {e}")

    def get_idle_time(self):
        """Get system idle time in seconds (Windows)"""
        try:
            import ctypes

            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [
                    ('cbSize', ctypes.c_uint),
                    ('dwTime', ctypes.c_uint),
                ]

            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)

            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
                millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
                return millis / 1000.0

            return 0

        except Exception as e:
            logger.error(f"Error getting idle time: {e}")
            return 0

    def run(self):
        """Main AFK watching loop"""
        logger.info("AFK watcher started")

        while True:
            try:
                idle_seconds = self.get_idle_time()
                now = datetime.now(timezone.utc)

                was_afk = self.is_afk
                self.is_afk = idle_seconds > AFK_TIMEOUT

                # Always send heartbeat with current status
                # This accumulates duration when status stays the same
                status = "afk" if self.is_afk else "not-afk"
                self.send_afk_heartbeat(status)

                # Log status changes
                if self.is_afk != was_afk:
                    logger.info(f"AFK status changed: {status}")

                time.sleep(5)

            except Exception as e:
                logger.error(f"AFK watcher error: {e}")
                time.sleep(10)

    def send_afk_heartbeat(self, status):
        """Send AFK heartbeat to server - uses heartbeat endpoint for duration accumulation"""
        try:
            event = {
                "employee_id": EMPLOYEE_ID,
                "device_id": DEVICE_ID,
                "data": {"status": status},
                "duration": 0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Use heartbeat endpoint with pulsetime to accumulate duration
            response = requests.post(
                f"{SERVER_URL}/api/0/buckets/aw-watcher-afk_{DEVICE_ID}/heartbeat?pulsetime=60",
                json=event,
                timeout=5
            )

            if response.status_code == 200:
                pass  # Normal heartbeat response, don't log every time

        except Exception as e:
            logger.error(f"Error sending AFK event: {e}")


def main():
    print("=" * 50)
    print("ActivityWatch Client Watcher")
    print("=" * 50)
    print(f"Server: {SERVER_URL}")
    print(f"Device ID: {DEVICE_ID}")
    print(f"Employee ID: {EMPLOYEE_ID}")
    print("=" * 50)

    # Check server connection
    try:
        response = requests.get(f"{SERVER_URL}/api/0/health", timeout=5)
        if response.status_code == 200:
            print("[OK] Server is running")
        else:
            print("[WARNING] Server returned unexpected status")
    except:
        print("[WARNING] Cannot connect to server - will retry")

    # Start watchers in separate threads
    window_watcher = WindowWatcher()
    afk_watcher = AFKWatcher()

    window_thread = threading.Thread(target=window_watcher.run, daemon=True)
    afk_thread = threading.Thread(target=afk_watcher.run, daemon=True)

    window_thread.start()
    afk_thread.start()

    print("\nWatchers started. Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping watchers...")


if __name__ == "__main__":
    main()
