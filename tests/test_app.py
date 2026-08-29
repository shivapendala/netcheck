import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import werkzeug
if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = '3.0.0'
import importlib

netcheck_app = importlib.import_module('app')
from utils.network_tools import ping_statistics
from utils.port_scanner import check_port, scan_common_ports
from utils.dns_checker import resolve_hostname, reverse_dns_lookup
from utils.alerts_dispatcher import build_alert_payload, dispatch_webhook


class TestNetCheckApp(unittest.TestCase):
    def setUp(self):
        self.fd, self.path = tempfile.mkstemp(suffix='.db')
        os.close(self.fd)
        netcheck_app.DATABASE = self.path
        netcheck_app.app.testing = True
        self.client = netcheck_app.app.test_client()
        with netcheck_app.app.app_context():
            netcheck_app.init_db()

    def tearDown(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def test_device_creation(self):
        response = self.client.post('/', data={'name': 'Router', 'ip': '192.168.1.1'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        resp = self.client.get('/')
        self.assertIn(b'Router', resp.data)
        self.assertIn(b'192.168.1.1', resp.data)

    def test_device_deletion(self):
        self.client.post('/', data={'name': 'Switch', 'ip': '10.0.0.2'}, follow_redirects=True)
        with netcheck_app.app.app_context():
            db = netcheck_app.get_db()
            cur = db.cursor()
            cur.execute('SELECT id FROM devices WHERE name=?', ('Switch',))
            device_id = cur.fetchone()[0]
        response = self.client.post(f'/delete/{device_id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        resp = self.client.get('/')
        self.assertNotIn(b'Switch', resp.data)

    @patch('app.ping_device')
    def test_ping_and_alert(self, mock_ping):
        mock_ping.return_value = ('Offline', None)
        self.client.post('/', data={'name': 'AP', 'ip': '10.0.0.3'}, follow_redirects=True)
        with netcheck_app.app.app_context():
            db = netcheck_app.get_db()
            cur = db.cursor()
            cur.execute('SELECT id FROM devices WHERE name=?', ('AP',))
            device_id = cur.fetchone()[0]
        self.client.post(f'/check/{device_id}', follow_redirects=True)
        with netcheck_app.app.app_context():
            cur = netcheck_app.get_db().cursor()
            cur.execute('SELECT COUNT(*) FROM history WHERE device_name=?', ('AP',))
            self.assertEqual(cur.fetchone()[0], 1)
            cur.execute('SELECT COUNT(*) FROM alerts WHERE device_name=?', ('AP',))
            self.assertEqual(cur.fetchone()[0], 1)

    def test_search_filter(self):
        self.client.post('/', data={'name': 'Server1', 'ip': '10.1.1.1'}, follow_redirects=True)
        self.client.post('/', data={'name': 'Server2', 'ip': '10.1.1.2'}, follow_redirects=True)
        self.client.post('/', data={'name': 'Printer', 'ip': '10.2.2.2'}, follow_redirects=True)
        resp = self.client.get('/?search=server')
        self.assertIn(b'Server1', resp.data)
        self.assertIn(b'Server2', resp.data)
        self.assertNotIn(b'Printer', resp.data)
        resp2 = self.client.get('/?status=Online')
        self.assertNotIn(b'Unknown', resp2.data)

    def test_csv_exports(self):
        self.client.post('/', data={'name': 'Camera', 'ip': '192.168.0.100'}, follow_redirects=True)
        resp = self.client.get('/export/devices')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'text/csv')
        data = resp.data.decode('utf-8')
        self.assertIn('Camera', data)
        self.assertIn('192.168.0.100', data)
        resp_hist = self.client.get('/export/history')
        self.assertEqual(resp_hist.status_code, 200)
        self.assertEqual(resp_hist.mimetype, 'text/csv')
        resp_alert = self.client.get('/export/alerts')
        self.assertEqual(resp_alert.status_code, 200)
        self.assertEqual(resp_alert.mimetype, 'text/csv')

    def test_network_tools(self):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.stdout = "Reply from 8.8.8.8: bytes=32 time=15ms TTL=117\nReply from 8.8.8.8: bytes=32 time=25ms TTL=117"
            stats = ping_statistics("8.8.8.8", count=2)
            self.assertEqual(stats["status"], "Online")
            self.assertEqual(stats["packets_received"], 2)
            self.assertEqual(stats["min_ms"], 15.0)
            self.assertEqual(stats["max_ms"], 25.0)
            self.assertEqual(stats["avg_ms"], 20.0)
            self.assertEqual(stats["packet_loss_pct"], 0.0)

    def test_port_scanner(self):
        with patch('socket.socket') as mock_sock:
            instance = mock_sock.return_value
            instance.connect_ex.return_value = 0
            res = check_port("127.0.0.1", 80)
            self.assertEqual(res["port"], 80)
            self.assertEqual(res["service"], "HTTP")
            self.assertTrue(res["is_open"])

    def test_dns_checker(self):
        with patch('socket.gethostbyname_ex') as mock_dns:
            mock_dns.return_value = ('example.com', [], ['93.184.216.34'])
            res = resolve_hostname('example.com')
            self.assertTrue(res['resolved'])
            self.assertEqual(res['primary_ip'], '93.184.216.34')

    def test_alerts_dispatcher(self):
        payload = build_alert_payload("Core-Router", "10.0.0.1", "Host unreachable")
        self.assertEqual(payload["event_type"], "device_outage")
        self.assertEqual(payload["device"]["name"], "Core-Router")
        self.assertEqual(payload["severity"], "critical")

        with patch('urllib.request.urlopen') as mock_url:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_url.return_value.__enter__.return_value = mock_resp
            success = dispatch_webhook("https://example.com/webhook", payload)
            self.assertTrue(success)


if __name__ == '__main__':
    unittest.main()
