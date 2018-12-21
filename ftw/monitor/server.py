from zope.component import getUtilitiesFor
import time
import zc.monitor
import ZODB.ActivityMonitor
import ZODB.interfaces
import zope.component


MONITOR_PORT = 8888


def initialize_monitor_server(opened_event):
    """Event handler for IDatabaseOpenedWithRoot that starts the monitor
    server on instance startup.
    """
    start_server(MONITOR_PORT, opened_event.database)


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
