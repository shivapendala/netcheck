"""DNS health checking and hostname resolution diagnostics."""
import socket
import time
from typing import Dict, List, Optional


def resolve_hostname(hostname: str) -> Dict[str, any]:
    """Resolve an IP or hostname, measuring resolution latency in milliseconds."""
    start_time = time.perf_counter()
    try:
        ip_addresses = socket.gethostbyname_ex(hostname)[2]
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "query": hostname,
            "resolved": True,
            "ip_addresses": ip_addresses,
            "primary_ip": ip_addresses[0] if ip_addresses else None,
            "resolution_time_ms": round(elapsed_ms, 2),
            "error": None,
        }
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "query": hostname,
            "resolved": False,
            "ip_addresses": [],
            "primary_ip": None,
            "resolution_time_ms": round(elapsed_ms, 2),
            "error": str(exc),
        }


def reverse_dns_lookup(ip_address: str) -> Optional[str]:
    """Perform a reverse PTR DNS lookup to find hostname from IP."""
    try:
        host, _, _ = socket.gethostbyaddr(ip_address)
        return host
    except Exception:
        return None
