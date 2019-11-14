from Acquisition import aq_parent
from App.config import getConfiguration
from collections import namedtuple
from ftw.monitor.autowarmup import autowarmup
from ftw.monitor.autowarmup import autowarmup_enabled
from ftw.monitor.server import initialize_monitor_server
from ftw.monitor.server import stop_server
from ftw.monitor.testing import HTTPServerStub
from ftw.monitor.testing import MONITOR_INTEGRATION_TESTING
from ftw.monitor.testing import MONITOR_ZSERVER_TESTING
from ftw.monitor.testing import MonitorTestCase
from ftw.monitor.testing import TCPHelper
from ftw.monitor.testing import wait_for_warmup_threads_to_finish
from ftw.monitor.warmup import instance_warmup_state
from ftw.testbrowser import browsing
from unittest import TestCase
from zope.processlifetime import DatabaseOpenedWithRoot
import os


WarmupState = namedtuple('WarmupState', ['done', 'in_progress'])


class TestWarmup(MonitorTestCase):

    layer = MONITOR_INTEGRATION_TESTING

    @browsing
    def test_warmup_view_on_plone_site(self, browser):
        self.assertFalse(instance_warmup_state['done'])

        browser.open(self.portal, view='@@warmup')

        self.assertTrue(instance_warmup_state['done'])
        self.assertEqual('Warmup successful', browser.contents)

    @browsing
    def test_warmup_view_on_zope_app_root(self, browser):
        self.assertFalse(instance_warmup_state['done'])

        app = aq_parent(self.portal)
        browser.open(app, view='@@warmup')

        self.assertTrue(instance_warmup_state['done'])
        self.assertEqual('Warmup successful', browser.contents)


class TestAutoWarmupExplicit(MonitorTestCase):

    layer = MONITOR_ZSERVER_TESTING

    @browsing
    def test_autowarmup_explicitly(self, browser):

        def fetch_warmup_state():
            reply = self.send('127.0.0.1', self.monitor_port, 'warmup_state\r\n')
            warmup_state = WarmupState(*map(int, reply.strip().split()))
            return warmup_state

        warmup_state = fetch_warmup_state()
        self.assertEqual(0, warmup_state.done)

        zserver_port = self.layer['port']
        autowarmup(zserver_port)

        self.wait_for(fetch_warmup_state, WarmupState(done=1, in_progress=0), 5.0)


class TestAutoWarmupOnServerInitialization(TestCase, TCPHelper):

    layer = MONITOR_ZSERVER_TESTING

    def tearDown(self):
        wait_for_warmup_threads_to_finish()
        stop_server()
        config = getConfiguration()
        delattr(config, 'servers')

    def test_autowarmup_triggered_on_server_initialization(self):
        zserver_port = self.layer['port']
        expected_monitor_port = zserver_port + 80

        config = getConfiguration()
        config.servers = [HTTPServerStub(port=zserver_port)]

        db = self.layer['portal']._p_jar.db()
        event = DatabaseOpenedWithRoot(db)
        initialize_monitor_server(event)

        def fetch_warmup_state():
            reply = self.send('127.0.0.1', expected_monitor_port, 'warmup_state\r\n')
            warmup_state = WarmupState(*map(int, reply.strip().split()))
            return warmup_state

        self.wait_for(fetch_warmup_state, WarmupState(done=1, in_progress=0), 5.0)


class TestAutoWarmupControl(TestCase):

    def setUp(self):
        os.environ.pop('FTW_MONITOR_AUTOWARMUP', None)

    def tearDown(self):
        os.environ.pop('FTW_MONITOR_AUTOWARMUP', None)

    def test_autowarmup_is_enabled_by_default(self):
        self.assertTrue(autowarmup_enabled())

    def test_autowarmup_can_be_disabled_via_env_var(self):
        os.environ['FTW_MONITOR_AUTOWARMUP'] = 'false'
        self.assertFalse(autowarmup_enabled())
