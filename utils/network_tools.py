"""Network diagnostic and ICMP latency calculation tools."""
import re
import subprocess
from typing import Dict, List, Optional, Tuple


def ping_statistics(host: str, count: int = 4, timeout_ms: int = 1000) -> Dict[str, Optional[float]]:
    """
    Execute ICMP ping with multiple samples and compute min, max, avg latency, and packet loss.
    Compatible with Windows and Unix ping commands.
    """
    cmd = ["ping", "-n", str(count), "-w", str(timeout_ms), host]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=(count * timeout_ms / 1000) + 3)
        output = proc.stdout
    except Exception:
        return {
            "status": "Offline",
            "packets_sent": count,
            "packets_received": 0,
            "packet_loss_pct": 100.0,
            "min_ms": None,
            "avg_ms": None,
            "max_ms": None,
            "jitter_ms": None,
        }

    times = [int(m) for m in re.findall(r"time[=<]\s*(\d+)\s*ms", output, re.IGNORECASE)]
    received = len(times)
    loss = ((count - received) / count) * 100.0 if count > 0 else 100.0

    if not times:
        return {
            "status": "Offline",
            "packets_sent": count,
            "packets_received": 0,
            "packet_loss_pct": 100.0,
            "min_ms": None,
            "avg_ms": None,
            "max_ms": None,
            "jitter_ms": None,
        }

    avg_ms = sum(times) / len(times)
    min_ms = min(times)
    max_ms = max(times)
    jitter = (max_ms - min_ms) if len(times) > 1 else 0.0

    return {
        "status": "Online",
        "packets_sent": count,
        "packets_received": received,
        "packet_loss_pct": loss,
        "min_ms": float(min_ms),
        "avg_ms": round(avg_ms, 2),
        "max_ms": float(max_ms),
        "jitter_ms": round(jitter, 2),
    }
