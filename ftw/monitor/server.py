from App.config import getConfiguration
from zope.component import getUtilitiesFor
from ZServer.datatypes import HTTPServerFactory
from ZServer.medusa.http_server import http_server
import time
import zc.monitor
import ZODB.ActivityMonitor
import ZODB.interfaces
import zope.component


def initialize_monitor_server(opened_event):
    """Event handler for IDatabaseOpenedWithRoot that starts the monitor
    server on instance startup.
    """
    monitor_port = determine_monitor_port()
    start_server(monitor_port, opened_event.database)


def determine_base_port(config=None):
    """Determine the HTTP instance's port.
    """
    if config is None:
        config = getConfiguration()

    # Filter out any non-ZServer servers, like taskqueue servers
    zservers = filter(
        lambda s: isinstance(s, (http_server, HTTPServerFactory)),
        config.servers)
    assert len(zservers) == 1

    # During normal instance startup, we'll have instantiated `http_server`
    # components in config.servers. When invoked via bin/instance monitor
    # however, these components will not have been instantiated, and
    # config.servers will contain HTTPServerFactory's instead (which have a
    # `port` attribute instead of `server_port`).
    server = zservers[0]
    if isinstance(server, http_server):
        base_port = server.server_port
    elif isinstance(server, HTTPServerFactory):
        base_port = server.port

    return int(base_port)


def determine_monitor_port(config=None):
    """Determine the monitor ported based on the instance's base port.
    """
    base_port = determine_base_port(config)
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
