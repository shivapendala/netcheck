import os
from flask import Flask, render_template, g, request, redirect, url_for, Response
import sqlite3
import subprocess
import datetime
import csv
import io

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, instance_path=BASE_DIR)
DATABASE = os.path.join(BASE_DIR, 'netcheck.db')

# -------------------------------
# Database helpers
# -------------------------------
def init_db():
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    # Devices table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ip TEXT NOT NULL,
            status TEXT DEFAULT 'Unknown'
        )
    ''')
    # Alerts table to log offline events
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_name TEXT NOT NULL,
            device_ip TEXT NOT NULL,
            message TEXT NOT NULL,
            alerted_at TEXT NOT NULL
        )
    ''')
    # History table to record each ping check
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_name TEXT NOT NULL,
            device_ip TEXT NOT NULL,
            status TEXT NOT NULL,
            response_time_ms INTEGER,
            checked_at TEXT NOT NULL
        )
    ''')
    db.commit()
    db.close()

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def get_devices():
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT id, name, ip, status FROM devices')
    rows = cur.fetchall()
    return [{'id': r[0], 'name': r[1], 'ip': r[2], 'status': r[3]} for r in rows]

def ping_device(ip):
    """Ping an IP address (Windows) and return a tuple (status, response_time_ms).
    status: "Online" or "Offline"
    response_time_ms: integer milliseconds if online, otherwise None.
    """
    try:
        result = subprocess.run(['ping', '-n', '1', '-w', '1000', ip], capture_output=True, text=True, timeout=2)
        output = result.stdout
        if result.returncode == 0 and 'Reply from' in output:
            import re
            match = re.search(r'time[=\<]\s*(\d+)', output)
            if match:
                return "Online", int(match.group(1))
            else:
                return "Online", None
        else:
            return "Offline", None
    except Exception:
        return "Offline", None

def update_status(name, ip, status):
    """Update the status column for a device identified by name and ip."""
    db = get_db()
    db.execute('UPDATE devices SET status = ? WHERE name = ? AND ip = ?', (status, name, ip))
    db.commit()

def record_history(name, ip, status, response_time_ms):
    """Insert a check record into the history table with timestamp."""
    db = get_db()
    timestamp = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')
    db.execute(
        'INSERT INTO history (device_name, device_ip, status, response_time_ms, checked_at) VALUES (?, ?, ?, ?, ?)',
        (name, ip, status, response_time_ms, timestamp)
    )
    db.commit()

def record_alert(name, ip, message):
    """Insert an alert record when a device is offline."""
    db = get_db()
    timestamp = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')
    db.execute(
        'INSERT INTO alerts (device_name, device_ip, message, alerted_at) VALUES (?, ?, ?, ?)',
        (name, ip, message, timestamp)
    )
    db.commit()

# -------------------------------
# Routes
# -------------------------------
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        name = request.form.get('name')
        ip = request.form.get('ip')
        if name and ip:
            db = get_db()
            db.execute('INSERT INTO devices (name, ip) VALUES (?, ?)', (name, ip))
            db.commit()
        return redirect(url_for('home'))
    # GET parameters for search and status filtering
    search = request.args.get('search', '').strip().lower()
    status_filter = request.args.get('status', '')
    devices = get_devices()
    if search:
        devices = [d for d in devices if search in d['name'].lower() or search in d['ip'].lower()]
    if status_filter in ('Online', 'Offline'):
        devices = [d for d in devices if d['status'].startswith(status_filter)]
    return render_template('index.html', title='NetCheck - Network Device Checker', devices=devices)

@app.route('/check/<int:device_id>', methods=['POST'])
def check_device(device_id):
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT name, ip FROM devices WHERE id = ?', (device_id,))
    row = cur.fetchone()
    if row:
        name, ip = row
        status, response_time_ms = ping_device(ip)
        update_status(name, ip, status)
        record_history(name, ip, status, response_time_ms)
        if status == 'Offline':
            record_alert(name, ip, 'Device went offline')
    return redirect(url_for('home'))

@app.route('/delete/<int:device_id>', methods=['POST'])
def delete_device(device_id):
    db = get_db()
    db.execute('DELETE FROM devices WHERE id = ?', (device_id,))
    db.commit()
    return redirect(url_for('home'))

@app.route('/history')
def history_page():
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT device_name, device_ip, status, response_time_ms, checked_at FROM history ORDER BY checked_at DESC')
    rows = cur.fetchall()
    history = [
        {
            'name': r[0],
            'ip': r[1],
            'status': r[2],
            'response_time_ms': r[3],
            'checked_at': r[4]
        }
        for r in rows
    ]
    return render_template('history.html', title='NetCheck - History', history=history)

@app.route('/alerts')
def alerts_page():
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT device_name, device_ip, message, alerted_at FROM alerts ORDER BY alerted_at DESC')
    rows = cur.fetchall()
    alerts = [
        {
            'name': r[0],
            'ip': r[1],
            'message': r[2],
            'alerted_at': r[3]
        }
        for r in rows
    ]
    return render_template('alerts.html', title='NetCheck - Alerts', alerts=alerts)

# CSV export routes
@app.route('/export/devices')
def export_devices():
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT name, ip, status FROM devices')
    rows = cur.fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'IP Address', 'Status'])
    writer.writerows(rows)
    csv_data = output.getvalue()
    output.close()
    return Response(csv_data, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=devices.csv'})

@app.route('/export/history')
def export_history():
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT device_name, device_ip, status, response_time_ms, checked_at FROM history')
    rows = cur.fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'IP Address', 'Status', 'Response Time (ms)', 'Checked At'])
    writer.writerows(rows)
    csv_data = output.getvalue()
    output.close()
    return Response(csv_data, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=history.csv'})

@app.route('/export/alerts')
def export_alerts():
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT device_name, device_ip, message, alerted_at FROM alerts')
    rows = cur.fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'IP Address', 'Message', 'Alerted At'])
    writer.writerows(rows)
    csv_data = output.getvalue()
    output.close()
    return Response(csv_data, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=alerts.csv'})

# -------------------------------
# Application entry point
# -------------------------------
if __name__ == '__main__':
    # Ensure the database file exists before initializing
    if not os.path.exists(DATABASE):
        open(DATABASE, 'a').close()
    init_db()
    # Run without debug mode for production; host set to 0.0.0.0 to be accessible on the network
    app.run(host='0.0.0.0', port=5000, debug=False)
