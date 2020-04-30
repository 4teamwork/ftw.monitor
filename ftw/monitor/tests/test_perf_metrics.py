from ftw.monitor import server
from ftw.monitor.server import get_uptime
from ftw.monitor.testing import MONITOR_INTEGRATION_TESTING
from ftw.monitor.testing import MonitorTestCase
import json
import time


TEST_ZODB_NAME = 'unnamed'


class TestPerformanceMetricsPlugin(MonitorTestCase):

    layer = MONITOR_INTEGRATION_TESTING

    def request_perf_metrics(self):
        cmd = 'perf_metrics %s\r\n' % TEST_ZODB_NAME
        reply = self.send('127.0.0.1', self.monitor_port, cmd)
        return json.loads(reply)

    def test_monitor_server_responds_to_perf_metrics(self):
        perf_metrics = self.request_perf_metrics()

        self.assertItemsEqual(
            ['instance', 'cache', 'db', 'memory'],
            perf_metrics.keys())

    def test_perf_metrics_contains_instance_metrics(self):
        # Temporarily monkey patch startup time
        fake_start_time = time.time() - 35
        previous_startup_time = server.startup_time
        server.startup_time = fake_start_time

        instance_metrics = self.request_perf_metrics()['instance']
        expected_uptime = get_uptime()

        # Revert monkey patch
        server.startup_time = previous_startup_time

        actual_uptime = instance_metrics['uptime']
        self.assertIsInstance(actual_uptime, int)
        self.assertAlmostEqual(expected_uptime, actual_uptime, delta=2)

    def test_perf_metrics_contains_cache_metrics(self):
        cache_metrics = self.request_perf_metrics()['cache']

        self.assertIsInstance(cache_metrics, dict)
        self.assertItemsEqual(
            ['size', 'ngsize', 'max_size'],
            cache_metrics.keys())

        for value in cache_metrics.values():
            self.assertIsInstance(value, int)

        db = self.portal._p_jar.db()
        self.assertEqual(cache_metrics['max_size'], db.getCacheSize())

    def test_perf_metrics_contains_db_metrics(self):
        db_metrics = self.request_perf_metrics()['db']
        self.assertIsInstance(db_metrics, dict)
        self.assertItemsEqual([
            'loads',
            'stores',
            'connections',
            'conflicts',
            'unresolved_conflicts',
            'total_objs',
            'size_in_bytes'],
            db_metrics.keys())

        for value in db_metrics.values():
            self.assertIsInstance(value, int)

        db = self.portal._p_jar.db()
        self.assertEqual(db_metrics['total_objs'], db.objectCount())
        self.assertEqual(db_metrics['size_in_bytes'], db.getSize())

    def test_perf_metrics_contains_memory_metrics(self):
        memory_metrics = self.request_perf_metrics()['memory']
        self.assertIsInstance(memory_metrics, dict)
        self.assertItemsEqual(
            ['rss', 'uss', 'pss'],
            memory_metrics.keys())

        for value in memory_metrics.values():
            self.assertIsInstance(value, int)
