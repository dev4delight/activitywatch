#!/usr/bin/env python3
"""
Enterprise Sync Service
Connects local ActivityWatch client to central server
Handles authentication, privacy, & offline sync
"""

import os
import json
import requests
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnterpriseSyncService:
    """Main sync orchestrator"""
    
    def __init__(self, 
                 server_url: str,           # Central server URL
                 employee_id: str,          # Employee identifier
                 api_key: str,              # API authentication key
                 device_id: str = None,     # Machine identifier
                 sync_interval: int = 300):  # Sync every 5 mins
        
        self.server_url = server_url
        self.employee_id = employee_id
        self.api_key = api_key
        self.device_id = device_id or self._get_device_id()
        self.sync_interval = sync_interval
        self.local_server = "http://localhost:5600"
        self.last_sync = None
        
    def _get_device_id(self) -> str:
        """Generate unique device identifier"""
        import socket
        import uuid
        hostname = socket.gethostname()
        mac = uuid.getnode()
        return f"{hostname}_{mac}"
    
    def sync_loop(self):
        """Main sync loop - runs continuously"""
        logger.info(f"Starting sync service for {self.employee_id}")
        
        while True:
            try:
                self.sync_events()
                time.sleep(self.sync_interval)
            except Exception as e:
                logger.error(f"Sync error: {e}")
                time.sleep(10)  # Retry sooner on error
    
    def sync_events(self):
        """Fetch events from local server & upload to central"""
        try:
            # 1. Fetch events from local ActivityWatch server
            events = self._fetch_local_events()
            
            if not events:
                logger.debug("No new events to sync")
                return
            
            # 2. Apply privacy filters
            events = self._apply_privacy_filters(events)
            
            # 3. Create sync payload
            payload = self._create_payload(events)
            
            # 4. Upload to central server
            response = self._upload_to_server(payload)
            
            if response.status_code == 200:
                self.last_sync = datetime.now()
                logger.info(f"Synced {len(events)} events successfully")
            else:
                logger.error(f"Upload failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Sync failed: {e}")
    
    def _fetch_local_events(self, limit: int = 500) -> List[Dict]:
        """Get events from local aw-server"""
        bucket_ids = [
            f"aw-watcher-window_{self.device_id}",
            f"aw-watcher-afk_{self.device_id}",
            f"aw-watcher-web_{self.device_id}"
        ]
        
        all_events = []
        for bucket_id in bucket_ids:
            try:
                url = f"{self.local_server}/api/0/buckets/{bucket_id}/events"
                response = requests.get(url, params={"limit": limit})
                if response.status_code == 200:
                    all_events.extend(response.json())
            except requests.exceptions.ConnectionError:
                logger.warning("Could not connect to local server")
                return []
        
        return all_events
    
    def _apply_privacy_filters(self, events: List[Dict]) -> List[Dict]:
        """Remove/redact sensitive data before upload"""
        import re
        
        # List of domains/apps to exclude
        EXCLUDE_PATTERNS = [
            r"localhost",
            r"127\.0\.0\.1",
            r"gmail\.com/mail",  # Private email
            r"facebook\.com",
            r"reddit\.com",
        ]
        
        # Patterns to redact in titles
        REDACT_PATTERNS = {
            "password": r"password[:\s]*[^\s]+",
            "token": r"token[:\s]*[^\s]+",
            "apikey": r"(api[_-]?key|apikey)[:\s]*[^\s]+",
            "ssn": r"\d{3}-\d{2}-\d{4}",
        }
        
        filtered_events = []
        for event in events:
            data = event.get("data", {})
            url = data.get("url", "")
            title = data.get("title", "")
            
            # Skip excluded patterns
            if any(re.search(pattern, url + title) for pattern in EXCLUDE_PATTERNS):
                continue
            
            # Redact sensitive data in title
            for pattern in REDACT_PATTERNS.values():
                title = re.sub(pattern, "[REDACTED]", title, flags=re.IGNORECASE)
            
            event["data"]["title"] = title
            filtered_events.append(event)
        
        return filtered_events
    
    def _create_payload(self, events: List[Dict]) -> Dict:
        """Package events for upload"""
        import gzip
        
        payload = {
            "employee_id": self.employee_id,
            "device_id": self.device_id,
            "timestamp": datetime.utcnow().isoformat(),
            "events": events,
            "event_count": len(events),
            "sync_version": "1.0"
        }
        
        # Compress payload
        payload_json = json.dumps(payload).encode('utf-8')
        compressed = gzip.compress(payload_json)
        
        # Create checksum for integrity
        checksum = hashlib.sha256(compressed).hexdigest()
        
        return {
            "data": compressed,
            "checksum": checksum,
            "metadata": {
                "event_count": len(events),
                "size_bytes": len(compressed)
            }
        }
    
    def _upload_to_server(self, payload: Dict) -> requests.Response:
        """Send events to central server"""
        url = f"{self.server_url}/api/0/sync/events"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/octet-stream",
            "X-Checksum": payload["checksum"],
            "X-Event-Count": str(payload["metadata"]["event_count"])
        }
        
        response = requests.post(
            url,
            data=payload["data"],
            headers=headers,
            timeout=30
        )
        
        return response


if __name__ == "__main__":
    # Load config from environment or file
    config = {
        "server_url": os.getenv("AW_SERVER_URL", "https://activitywatch.company.com"),
        "employee_id": os.getenv("EMPLOYEE_ID"),
        "api_key": os.getenv("AW_API_KEY"),
        "sync_interval": int(os.getenv("SYNC_INTERVAL", "300"))
    }
    
    sync = EnterpriseSyncService(**config)
    sync.sync_loop()
