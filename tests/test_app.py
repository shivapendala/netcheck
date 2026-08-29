import os
import tempfile
import pytest
from unittest.mock import patch

# Import the Flask app module dynamically
import importlib

netcheck_app = importlib.import_module('app')

@pytest.fixture
def client():
    # Create a temporary SQLite database file
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    # Override the global DATABASE path in the app module
    netcheck_app.DATABASE = path
    netcheck_app.app.testing = True
    with netcheck_app.app.test_client() as client:
        with netcheck_app.app.app_context():
            netcheck_app.init_db()
        yield client
    os.unlink(path)

def test_device_creation(client):
    response = client.post('/', data={'name': 'Router', 'ip': '192.168.1.1'}, follow_redirects=True)
    assert response.status_code == 200
    resp = client.get('/')
    assert b'Router' in resp.data
    assert b'192.168.1.1' in resp.data

def test_device_deletion(client):
    client.post('/', data={'name': 'Switch', 'ip': '10.0.0.2'}, follow_redirects=True)
    with netcheck_app.app.app_context():
        db = netcheck_app.get_db()
        cur = db.cursor()
        cur.execute('SELECT id FROM devices WHERE name=?', ('Switch',))
        device_id = cur.fetchone()[0]
    response = client.post(f'/delete/{device_id}', follow_redirects=True)
    assert response.status_code == 200
    resp = client.get('/')
    assert b'Switch' not in resp.data

@patch('app.ping_device')
def test_ping_and_alert(mock_ping, client):
    mock_ping.return_value = ('Offline', None)
    client.post('/', data={'name': 'AP', 'ip': '10.0.0.3'}, follow_redirects=True)
    with netcheck_app.app.app_context():
        db = netcheck_app.get_db()
        cur = db.cursor()
        cur.execute('SELECT id FROM devices WHERE name=?', ('AP',))
        device_id = cur.fetchone()[0]
    client.post(f'/check/{device_id}', follow_redirects=True)
    with netcheck_app.app.app_context():
        cur = netcheck_app.get_db().cursor()
        cur.execute('SELECT COUNT(*) FROM history WHERE device_name=?', ('AP',))
        assert cur.fetchone()[0] == 1
        cur.execute('SELECT COUNT(*) FROM alerts WHERE device_name=?', ('AP',))
        assert cur.fetchone()[0] == 1

def test_search_filter(client):
    client.post('/', data={'name': 'Server1', 'ip': '10.1.1.1'}, follow_redirects=True)
    client.post('/', data={'name': 'Server2', 'ip': '10.1.1.2'}, follow_redirects=True)
    client.post('/', data={'name': 'Printer', 'ip': '10.2.2.2'}, follow_redirects=True)
    resp = client.get('/?search=server')
    assert b'Server1' in resp.data
    assert b'Server2' in resp.data
    assert b'Printer' not in resp.data
    resp = client.get('/?status=Online')
    assert b'Unknown' not in resp.data

def test_csv_exports(client):
    client.post('/', data={'name': 'Camera', 'ip': '192.168.0.100'}, follow_redirects=True)
    resp = client.get('/export/devices')
    assert resp.status_code == 200
    assert resp.mimetype == 'text/csv'
    data = resp.data.decode('utf-8')
    assert 'Camera' in data
    assert '192.168.0.100' in data
    resp_hist = client.get('/export/history')
    assert resp_hist.status_code == 200
    assert resp_hist.mimetype == 'text/csv'
    resp_alert = client.get('/export/alerts')
    assert resp_alert.status_code == 200
    assert resp_alert.mimetype == 'text/csv'
