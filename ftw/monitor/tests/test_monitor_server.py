from App.config import getConfiguration
from ftw.monitor import server as monitor_server
from ftw.monitor.health import STARTSECS
from ftw.monitor.server import determine_monitor_port
from ftw.monitor.server import initialize_monitor_server
from ftw.monitor.server import stop_server
from ftw.monitor.testing import HTTPServerFactoryStub
from ftw.monitor.testing import HTTPServerStub
from ftw.monitor.testing import MONITOR_INTEGRATION_TESTING
from ftw.monitor.testing import MONITOR_ZSERVER_TESTING
from ftw.monitor.testing import MonitorTestCase
from ftw.monitor.testing import OtherServerStub
from ftw.monitor.testing import TCPHelper
from ftw.monitor.testing import wait_for_warmup_threads_to_finish
from ftw.monitor.testing import WarmupInProgress
from unittest import TestCase
from zope.processlifetime import DatabaseOpenedWithRoot
import time


class TestMonitorServer(MonitorTestCase):

    layer = MONITOR_INTEGRATION_TESTING

    def test_monitor_server_responds_to_help(self):
        reply = self.send('127.0.0.1', self.monitor_port, 'help\r\n')
        self.assertEqual('Supported commands:', reply.splitlines()[0])

    def test_health_check_returns_ok_when_startsecs_passed(self):
        monitor_server.startup_time = time.time() - (STARTSECS + 1)
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
        monitor_server.startup_time = time.time() - (STARTSECS + 1)

        with WarmupInProgress(True):
            reply = self.send('127.0.0.1', self.monitor_port, 'health_check\r\n')
        self.assertEqual('Warmup in progress\n', reply)

    def test_health_check_fails_if_instance_was_just_booted(self):
        reply = self.send('127.0.0.1', self.monitor_port, 'health_check\r\n')
        self.assertEqual('Instance is booting\n', reply)


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

        monitor_port = determine_monitor_port(consider_factories=True)
        self.assertEqual(10101 + 80, monitor_port)

    def test_http_server_factories_are_not_considered_by_default(self):
        config = getConfiguration()
        config.servers = [OtherServerStub(), HTTPServerFactoryStub()]

        monitor_port = determine_monitor_port()
        self.assertIsNone(monitor_port)


class TestMonitorStartup(TestCase, TCPHelper):

    layer = MONITOR_ZSERVER_TESTING

    def tearDown(self):
        wait_for_warmup_threads_to_finish()
        stop_server()

        config = getConfiguration()
        delattr(config, 'servers')

    def test_health_check_will_eventually_turn_green_after_startup(self):
        zserver_port = self.layer['port']
        config = getConfiguration()
        config.servers = [HTTPServerStub(port=zserver_port)]

        db = self.layer['portal']._p_jar.db()
        event = DatabaseOpenedWithRoot(db)
        initialize_monitor_server(event)

        expected_monitor_port = zserver_port + 80
        reply = self.send('127.0.0.1', expected_monitor_port, 'health_check\r\n')
        self.assertEqual('Instance is booting\n', reply)

        def fetch_health_check():
            reply = self.send('127.0.0.1', expected_monitor_port, 'health_check\r\n')
            return reply

        self.wait_for(fetch_health_check, 'OK\n', 5.0)
