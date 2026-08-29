"""Multi-threaded TCP port scanning service for NetCheck."""
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional


DEFAULT_PORTS = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    8080: "HTTP-Alt",
}


def check_port(host: str, port: int, timeout: float = 1.0) -> Dict[str, any]:
    """Check whether a specific TCP port is open on the target host."""
    service_name = DEFAULT_PORTS.get(port, "Unknown")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        res = sock.connect_ex((host, port))
        is_open = (res == 0)
    except Exception:
        is_open = False
    finally:
        sock.close()

    return {
        "port": port,
        "service": service_name,
        "is_open": is_open,
    }


def scan_common_ports(host: str, ports: Optional[List[int]] = None, max_workers: int = 10, timeout: float = 1.0) -> List[Dict[str, any]]:
    """Scan multiple TCP ports concurrently using thread pool."""
    target_ports = ports if ports is not None else sorted(list(DEFAULT_PORTS.keys()))
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_port = {
            executor.submit(check_port, host, p, timeout): p
            for p in target_ports
        }
        for future in as_completed(future_to_port):
            try:
                results.append(future.result())
            except Exception:
                results.append({
                    "port": future_to_port[future],
                    "service": DEFAULT_PORTS.get(future_to_port[future], "Unknown"),
                    "is_open": False,
                })

    return sorted(results, key=lambda x: x["port"])
