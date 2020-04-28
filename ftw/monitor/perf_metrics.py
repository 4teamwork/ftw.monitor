from ftw.monitor.server import get_uptime
from time import time
from ZODB.interfaces import IDatabase
from zope.component import getUtility
from Zope2 import app as App  # noqa
import json
import psutil
import Zope2


def perf_metrics(connection, database='-', sampling_interval=300):
    r"""Get performance related metrics.

    Usage: Send the message 'perf_metrics\r\n' to the zc.monitor TCP port.

    The plugin will then respond with a JSON encoded dictionary containing
    several performance related metrics.

    You can pass a database name, where "-" is an alias for the main database.

    By default, the statistics are for a sampling interval of 5
    minutes.  You can request another sampling interval, up to an
    hour, by passing a sampling interval in seconds after the database name.
    The sampling interval applies to statistics tracked by the ZODB
    ActivityMonitor.
    """
    app = App()

    # Make sure we have a connected storage available
    try:
        dbchooser = app.Control_Panel.Database
        for dbname in dbchooser.getDatabaseNames():
            storage = dbchooser[dbname]._getDB()._storage
            is_connected = getattr(storage, 'is_connected', None)
            if is_connected is not None and not is_connected():
                msg = {'error': 'Database %r disconnected.' % dbname}
                connection.write('%s\n' % json.dumps(msg))
                return

        # Get DB. These will be registered during startup in f.m.server
        if database == '-':
            database = 'main'
        db = getUtility(IDatabase, database)

        metrics = collect_performance_metrics(db, sampling_interval)
        connection.write('%s\n' % json.dumps(metrics))

    finally:
        app._p_jar.close()


def collect_performance_metrics(db, sampling_interval):
    instance_stats = get_instance_stats()
    cache_stats = get_cache_stats(db)
    db_stats = get_db_stats(db, sampling_interval)
    memory_stats = get_memory_stats()
    metrics = {
        'instance': instance_stats,
        'cache': cache_stats,
        'db': db_stats,
        'memory': memory_stats,
    }
    return metrics


def get_instance_stats():
    return {'uptime': int(get_uptime())}


def get_memory_stats():
    meminfo = psutil.Process().memory_full_info()
    pss = getattr(meminfo, 'pss', -1)  # pss is Linux only
    return {'rss': meminfo.rss, 'uss': meminfo.uss, 'pss': pss}


def get_cache_stats(db):
    max_size = db.getCacheSize()
    ngsize = size = 0
    for detail in db.cacheDetailSize():
        ngsize += detail['ngsize']
        size += detail['size']

    return {'size': size, 'ngsize': ngsize, 'max_size': max_size}


def get_db_stats(db, sampling_interval):
    conflicts = Zope2.zpublisher_exception_hook.conflict_errors
    unresolved_conflicts = Zope2.zpublisher_exception_hook.unresolved_conflict_errors

    am = db.getActivityMonitor()
    if am is None:
        activity = -1, -1, -1
    else:
        now = time()
        start = now - int(sampling_interval)
        analysis = am.getActivityAnalysis(start, now, 1)[0]
        activity = (analysis['loads'],
                    analysis['stores'],
                    analysis['connections'],
                    )

    db_stats = {
        'loads': activity[0],
        'stores': activity[1],
        'connections': activity[2],
        'conflicts': conflicts,
        'unresolved_conflicts': unresolved_conflicts,
        'total_objs': db.objectCount(),
        'size_in_bytes': db.getSize(),
    }
    return db_stats
