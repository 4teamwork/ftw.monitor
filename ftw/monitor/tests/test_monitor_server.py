from App.config import getConfiguration
from ftw.monitor.server import determine_monitor_port
from ftw.monitor.server import start_server
from ftw.monitor.server import stop_server
from ftw.monitor.testing import MONITOR_INTEGRATION_TESTING
from unittest2 import TestCase
from ZServer.datatypes import HTTPServerFactory
from ZServer.medusa.http_server import http_server
import socket


class WarmupInProgress(object):
    """Context manager to reversibly monkey patch the warmup in_progress flag.
    """

    def __init__(self, value):
        self.value = value

    def __enter__(self):
        from ftw.monitor.warmup import instance_warmup_state
        self._original_value = instance_warmup_state['in_progress']
        instance_warmup_state['in_progress'] = self.value
        return self

    def __exit__(self, exc_type, exc_value, tb):
        from ftw.monitor.warmup import instance_warmup_state
        instance_warmup_state['in_progress'] = self._original_value
        instance_warmup_state['done'] = True


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

    def test_health_check_fails_if_warmup_in_progress(self):
        with WarmupInProgress(True):
            reply = self.send('127.0.0.1', 7777, 'health_check\r\n')
        self.assertEqual('Warmup in progress\n', reply)


class HTTPServerStub(http_server):
    """A ZServer derived class that should be picked as the server
    to base our monitor port on.
    """

    def __init__(self, *args, **kwargs):
        """Stub out http_server.__init__ - don't open sockets.
        """
        self.port = 10101


class HTTPServerFactoryStub(HTTPServerFactory):
    """A HTTPServerFactory derived class that should be picked as the server
    to base our monitor port on if invoked via bin/instance monitor.
    """

    def __init__(self, *args, **kwargs):
        self.port = 10101


class OtherServerStub(object):
    """Simulates some other kind of server we must ignore.
    """

    port = 7777


class TestMonitorServerPort(TestCase):

    layer = MONITOR_INTEGRATION_TESTING

    def tearDown(self):
        config = getConfiguration()
        delattr(config, 'servers')

    def test_monitor_server_port_is_based_on_instance_port(self):
        config = getConfiguration()
        config.servers = [OtherServerStub(), HTTPServerStub()]

        monitor_port = determine_monitor_port()
        self.assertEqual(10101 + 80, monitor_port)

    def test_monitor_server_port_can_be_determined_from_http_server_factory(self):
        config = getConfiguration()
        config.servers = [OtherServerStub(), HTTPServerFactoryStub()]

        monitor_port = determine_monitor_port()
        self.assertEqual(10101 + 80, monitor_port)
