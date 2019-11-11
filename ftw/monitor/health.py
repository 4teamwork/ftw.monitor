from ftw.monitor.warmup import instance_warmup_state
from Zope2 import app as App  # noqa


def health_check(connection):
    r"""Check whether the instance is alive and ready to serve requests.

    IZ3MonitorPlugin implementation that can be used as a health check by
    HAProxy or monitoring tools.

    Usage: Send the message 'health_check\r\n' to the zc.monitor TCP port.
    If the instance is healthy, the plugin responds with 'OK\n'.
    """
    app = App()

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

    if instance_warmup_state['in_progress']:
        return red('Warmup in progress')

    return green()
