from ftw.monitor.server import start_server
from ftw.monitor.server import stop_server
from ftw.monitor.warmup import instance_warmup_state
from plone.app.testing import IntegrationTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.testing import z2
from unittest2 import TestCase
from zope.configuration import xmlconfig
from ZServer.datatypes import HTTPServerFactory
from ZServer.medusa.http_server import http_server
import socket


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


class MonitorTestCase(TestCase, TCPHelper):

    MONITOR_PORT = 9999

    def setUp(self):
        self.portal = self.layer['portal']

        instance_warmup_state['done'] = False
        instance_warmup_state['in_progress'] = False
        self.start_monitor_server()

    def tearDown(self):
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
