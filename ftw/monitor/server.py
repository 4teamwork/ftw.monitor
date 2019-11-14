from App.config import getConfiguration
from ftw.monitor.autowarmup import autowarmup
from ftw.monitor.autowarmup import autowarmup_enabled
from zope.component import getUtilitiesFor
from ZServer.datatypes import HTTPServerFactory
from ZServer.medusa.http_server import http_server
import os
import time
import zc.monitor
import ZODB.ActivityMonitor
import ZODB.interfaces
import zope.component


startup_time = None


def get_uptime():
    global startup_time
    if startup_time is None:
        return 0
    return time.time() - startup_time


def initialize_monitor_server(opened_event):
    """Event handler for IDatabaseOpenedWithRoot that starts the monitor
    server on instance startup.
    """
    config = getConfiguration()
    instance_name = os.path.basename(config.instancehome)
    # Never warm up or monitor server for our maintenance instance
    if instance_name == 'instance0':
        return

    global startup_time
    startup_time = time.time()

    monitor_port = determine_monitor_port()
    if monitor_port:
        start_server(monitor_port, opened_event.database)

    # Trigger warmup for this instance (without blocking startup)
    base_port = determine_base_port()
    if base_port and autowarmup_enabled():
        autowarmup(base_port)


def determine_base_port(config=None, consider_factories=False):
    """Determine the HTTP instance's port.
    """
    if config is None:
        config = getConfiguration()

    # During normal instance startup, we'll have instantiated `http_server`
    # components in config.servers, and that's were we get the base port of
    # the running HTTP server from.
    #
    # When we encounter HTTPServerFactory's instead of their instantiation,
    # it means that the instance was invoked in a mode that does NOT start
    # the HTTP server(s) defined in zope.conf. These are for example:
    #
    # - bin/instance run <script>
    # - bin/instance debug
    # - bin/instance <zopectl_cmd>
    #
    # In most of these cases we'll want to avoid attempting to launch a
    # monitor server (and trigger a warmup request), and will therefore
    # return `None` for the base port.
    #
    # Also, we filter out any non-ZServer servers, like taskqueue servers
    zservers = [
        server for server in config.servers
        if isinstance(server, http_server)
    ]

    if consider_factories:
        # The exception to the above is the "bin/instance monitor" command:
        # From this command we want to talk to the already running monitor
        # server over TCP - we're not launching a new one. In that case we
        # therefore *do* consider server factories, to be able to determine
        # the port of the monitor server already running in a different
        # process of the same instance.
        zservers += [
            server for server in config.servers
            if isinstance(server, HTTPServerFactory)]

    assert len(zservers) in (0, 1)

    if not zservers:
        return None

    server = zservers[0]
    base_port = server.port
    return int(base_port)


def determine_monitor_port(config=None, consider_factories=False):
    """Determine the monitor ported based on the instance's base port.
    """
    base_port = determine_base_port(config=config,
                                    consider_factories=consider_factories)

    if not base_port:
        return None

    monitor_port = base_port + 80
    return monitor_port


def register_db(db):
    dbname = db.database_name
    zope.component.provideUtility(db, ZODB.interfaces.IDatabase, name=dbname)


def start_server(port, db):
    """Start a zc.monitor server on the given port.
    """
    register_db(db)
    for name, db in getUtilitiesFor(ZODB.interfaces.IDatabase):
        if db.getActivityMonitor() is None:
            db.setActivityMonitor(ZODB.ActivityMonitor.ActivityMonitor())

    port = int(port)
    zc.monitor.start(port)


def stop_server():
    """Stop a running zc.monitor server.

    Used for testing, see zc/monitor/README.txt.
    """
    zc.monitor.last_listener.close()
    zc.monitor.last_listener = None
    time.sleep(0.1)
