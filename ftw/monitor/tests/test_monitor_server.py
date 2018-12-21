from ftw.monitor.server import start_server
from ftw.monitor.server import stop_server
from ftw.monitor.testing import MONITOR_INTEGRATION_TESTING
from unittest2 import TestCase
import socket


class TestMonitorServer(TestCase):

    layer = MONITOR_INTEGRATION_TESTING

    def setUp(self):
        db = self.layer['portal']._p_jar.db()
        start_server(7777, db)

    def tearDown(self):
        stop_server()

    def send(self, ip, port, msg):
        """Send a message to a TCP port, return the reply.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, port))
        sock.send(msg)
        data = sock.recv(1024)
        sock.close()
        return data

    def test_monitor_server_responds_to_help(self):
        reply = self.send('127.0.0.1', 7777, 'help\r\n')
        self.assertEqual('Supported commands:', reply.splitlines()[0])

    def test_health_check_returns_ok(self):
        reply = self.send('127.0.0.1', 7777, 'health_check\r\n')
        self.assertEqual('OK\n', reply)

    def test_health_check_fails_if_storage_is_disconnected(self):
        try:
            db = self.layer['portal']._p_jar.db()
            db._storage.is_connected = lambda: False

            reply = self.send('127.0.0.1', 7777, 'health_check\r\n')
            self.assertEqual("Error: Database 'testing' disconnected.\n", reply)
        finally:
            delattr(db._storage, 'is_connected')
