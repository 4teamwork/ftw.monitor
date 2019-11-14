from ftw.monitor.server import start_server
from ftw.monitor.server import stop_server
from ftw.monitor.warmup import instance_warmup_state
from plone.app.testing import IntegrationTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.app.testing.layers import FunctionalTesting
from plone.testing import z2
from unittest import TestCase
from zope.configuration import xmlconfig
from ZServer.datatypes import HTTPServerFactory
from ZServer.medusa.http_server import http_server
import socket
import threading
import time


class MonitorLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        xmlconfig.string(
            '<configure xmlns="http://namespaces.zope.org/zope">'
            '  <include package="z3c.autoinclude" file="meta.zcml" />'
            '  <includePlugins package="plone" />'
            '  <includePluginsOverrides package="plone" />'
            '</configure>',
            context=configurationContext)

        z2.installProduct(app, 'ftw.monitor')


class TCPHelper(object):
    """Mixin class for test cases to talk to TCP ports.
    """

    def send(self, ip, port, msg):
        """Send a message to a TCP port, return the reply.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, port))
        sock.send(msg)
        data = sock.recv(1024)
        sock.close()
        return data

    def wait_for(self, func, expected_return_value, timeout):
        """Test assertion method to repeatedly call a function until it
        returns the expected value, or fail if the timeout is exceeded.
        """
        start = time.time()
        while not time.time() - start > timeout:
            result = func()
            if result == expected_return_value:
                return result
            time.sleep(0.1)

        msg = ("Exceeded timeout of %rs while waiting for %r to return %r. "
               "Last returned value was %r" % (
                   timeout, func.__name__, expected_return_value, result))
        self.fail(msg)


def wait_for_warmup_threads_to_finish():
    """Will block and wait for any warmup threads to finish, until
    timeout is exceeded.

    This is required to get deterministic, synchronous behavior in tests.
    """
    timeout = 5.0
    elapsed = 0.0

    def warmup_threads_still_running():
        return any('warmup' in t.getName() for t in threading.enumerate())

    start = time.time()
    while not elapsed > timeout and warmup_threads_still_running():
        print "\nWaiting for a warmup thread to finish..."
        time.sleep(0.1)
        elapsed = time.time() - start


class MonitorTestCase(TestCase, TCPHelper):

    MONITOR_PORT = 9999

    def setUp(self):
        self.portal = self.layer['portal']

        instance_warmup_state['done'] = False
        instance_warmup_state['in_progress'] = False
        self.start_monitor_server()

    def tearDown(self):
        wait_for_warmup_threads_to_finish()

        self.stop_monitor_server()
        instance_warmup_state['done'] = False
        instance_warmup_state['in_progress'] = False

    def start_monitor_server(self):
        self.monitor_port = self.MONITOR_PORT
        db = self.portal._p_jar.db()
        start_server(self.MONITOR_PORT, db)

    def stop_monitor_server(self):
        stop_server()


MONITOR_FIXTURE = MonitorLayer()

MONITOR_INTEGRATION_TESTING = IntegrationTesting(
    bases=(MONITOR_FIXTURE,),
    name='ftw.monitor:integration')

MONITOR_ZSERVER_TESTING = FunctionalTesting(
    bases=(MONITOR_FIXTURE, z2.ZSERVER_FIXTURE),
    name="ftw.monitor:zserver")


class WarmupInProgress(object):
    """Context manager to reversibly monkey patch the warmup_in_progress flag.
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
        instance_warmup_state['done'] = False


class HTTPServerStub(http_server):
    """A ZServer derived class that should be picked as the server
    to base our monitor port on.
    """

    def __init__(self, *args, **kwargs):
        """Stub out http_server.__init__ - don't open sockets.
        """
        self.port = 10101
        if 'port' in kwargs:
            self.port = kwargs['port']


class HTTPServerFactoryStub(HTTPServerFactory):
    """A HTTPServerFactory derived class that should be picked as the server
    to base our monitor port on if invoked via bin/instance monitor.
    """

    def __init__(self, *args, **kwargs):
        self.port = 10101
        if 'port' in kwargs:
            self.port = kwargs['port']


class OtherServerStub(object):
    """Simulates some other kind of server we must ignore.
    """

    port = 7777
