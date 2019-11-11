from App.config import getConfiguration
from ftw.monitor.server import determine_monitor_port
from ftw.monitor.testing import HTTPServerFactoryStub
from ftw.monitor.testing import HTTPServerStub
from ftw.monitor.testing import MONITOR_INTEGRATION_TESTING
from ftw.monitor.testing import MonitorTestCase
from ftw.monitor.testing import OtherServerStub
from ftw.monitor.testing import WarmupInProgress
from unittest2 import TestCase


class TestMonitorServer(MonitorTestCase):

    layer = MONITOR_INTEGRATION_TESTING

    def test_monitor_server_responds_to_help(self):
        reply = self.send('127.0.0.1', self.monitor_port, 'help\r\n')
        self.assertEqual('Supported commands:', reply.splitlines()[0])

    def test_health_check_returns_ok(self):
        reply = self.send('127.0.0.1', self.monitor_port, 'health_check\r\n')
        self.assertEqual('OK\n', reply)

    def test_health_check_fails_if_storage_is_disconnected(self):
        try:
            db = self.layer['portal']._p_jar.db()
            db._storage.is_connected = lambda: False

            reply = self.send('127.0.0.1', self.monitor_port, 'health_check\r\n')
            self.assertEqual("Error: Database 'testing' disconnected.\n", reply)
        finally:
            delattr(db._storage, 'is_connected')

    def test_health_check_fails_if_warmup_in_progress(self):
        with WarmupInProgress(True):
            reply = self.send('127.0.0.1', self.monitor_port, 'health_check\r\n')
        self.assertEqual('Warmup in progress\n', reply)


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
