from App.config import getConfiguration
from zope.component import getUtilitiesFor
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


def determine_monitor_port():
    """Determine the monitor ported based on the instance's base port.
    """
    config = getConfiguration()
    assert len(config.servers) == 1
    server = config.servers[0]
    monitor_port = int(server.server_port) + 80
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
