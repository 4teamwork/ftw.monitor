from ftw.monitor.autowarmup import autowarmup_enabled
from ftw.monitor.server import get_uptime
from ftw.monitor.warmup import instance_warmup_state
from Zope2 import app as App  # noqa


# For this long after instance start the health check won't turn green,
# unless wqe get a positive indication that warmup has been performed.
# (This is to avoid status flickering during startup).
STARTSECS = 20


def health_check(connection):
    r"""Check whether the instance is alive and ready to serve requests.

    IZ3MonitorPlugin implementation that can be used as a health check by
    HAProxy or monitoring tools.

    Usage: Send the message 'health_check\r\n' to the zc.monitor TCP port.
    If the instance is healthy, the plugin responds with 'OK\n'.
    """
    app = App()
    uptime = get_uptime()

    def green():
        """Signal healthy status.
        """
        connection.write('OK\n')

    def red(msg):
        """Signal unhealthy status (with a message describing why).
        """
        connection.write('%s\n' % msg)

    try:
        dbchooser = app.Control_Panel.Database
        for dbname in dbchooser.getDatabaseNames():
            storage = dbchooser[dbname]._getDB()._storage
            is_connected = getattr(storage, 'is_connected', None)
            if is_connected is not None and not is_connected():
                return red('Error: Database %r disconnected.' % dbname)
    finally:
        app._p_jar.close()

    # Avoid flickering status on startup (briefly turning green because
    # monitor server was started, but warmup hasn't been triggered yet)
    if uptime < STARTSECS and autowarmup_enabled():
        if not (instance_warmup_state['in_progress'] or
                instance_warmup_state['done']):
            return red('Instance is booting')

    if instance_warmup_state['in_progress']:
        return red('Warmup in progress')

    return green()
