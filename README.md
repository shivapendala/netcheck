# NetCheck

A simple Flask web application for monitoring network devices.

## Features
- Add, delete, and view devices.
- Manual "Check Now" to ping devices and record status.
- History page showing past ping results.
- Alerts page for offline devices.
- Search and filter devices by name/IP and status.
- Export devices, history, and alerts as CSV files.
- Automated test suite with pytest.

## Prerequisites
- Python 3.10+ (tested on Windows)

## Setup
1. Open a command prompt in the project root (`d:/networking/NetCheck`).
2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the Application
```bash
python app.py
```
The app will start on `http://0.0.0.0:5000`. Open this URL in a browser.

## Running Tests
```bash
pytest -q
```
All tests should pass.

## Project Structure
- `app.py` – Flask application and routes.
- `templates/` – HTML templates.
- `static/css/style.css` – Premium dark‑mode styling.
- `tests/` – Pytest suite.
- `requirements.txt` – Python dependencies.

## License
MIT
