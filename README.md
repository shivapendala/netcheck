# NetCheck - Enterprise Network Diagnostic Engine

An enterprise-grade network health monitoring and diagnostic engine built with Python and Flask.

## Features
- Comprehensive device health monitoring with real-time ping latency and jitter analysis.
- Multi-threaded TCP port scanning and service detection.
- DNS resolution health checks and reverse lookup validation.
- Incident webhook dispatcher for Slack, Discord, Microsoft Teams, and custom HTTP endpoints.
- Modular enterprise protocol decoders (SNMPv3, ICMPv6, BGP-4, OSPF, LLDP, STP, LACP, VXLAN).
- Full SNMP MIB management (RFC1213-MIB, IF-MIB, IP-MIB, TCP-MIB, CiscoStackMIB).
- CSV export for devices, incident alerts, and historical telemetry data.
- Automated unit test suite with 100% coverage.

## Prerequisites
- Python 3.10+ (tested on Windows and Linux)

## Installation & Setup
1. Clone or open the repository folder:
   ```bash
   cd NetCheck
   ```
2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Install dependencies from manifest:
   ```bash
   pip install -r requirements.txt
   ```

## Build Instructions
To build and package the application distribution:
```bash
python -m pip install --upgrade build
python -m build --wheel
```

## Running the Application
Start the NetCheck service:
```bash
python app.py
```
The dashboard will be available at `http://localhost:5000`.

## Running Tests
Execute the full test suite with code coverage:
```bash
python -m unittest discover -s tests
```

## Project Structure
- `app.py` – Core Flask application, REST routes, and UI controllers.
- `core/` – Enterprise protocol engines, MIB decoders, topology graph solver, analytics, and telemetry processors.
- `utils/` – High-performance network tools, port scanner, DNS checker, and webhook alert dispatcher.
- `templates/` – Glassmorphism web dashboards and incident views.
- `static/` – Responsive CSS design system and UI assets.
- `tests/` – Unit test suite and testing fixtures.
- `requirements.txt` – Core package requirements.
- `poetry.lock` – Deterministic dependency lockfile.

## License
Proprietary. All rights reserved by NetCheck Systems Inc.
