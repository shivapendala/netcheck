"""Webhook alert dispatcher and incident notification system."""
import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Optional


def build_alert_payload(device_name: str, device_ip: str, message: str, severity: str = "critical") -> Dict[str, any]:
    """Format structured JSON payload for external incident webhooks."""
    return {
        "event_type": "device_outage",
        "severity": severity,
        "device": {
            "name": device_name,
            "ip": device_ip,
        },
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "NetCheck Monitor",
    }


def dispatch_webhook(webhook_url: str, payload: Dict[str, any], timeout_seconds: int = 5) -> bool:
    """Send JSON payload to a specified webhook endpoint."""
    if not webhook_url:
        return False
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "NetCheck-Monitor/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            return response.status in (200, 201, 202, 204)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, Exception):
        return False
