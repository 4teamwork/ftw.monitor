from ftw.monitor.dump_metrics import fetch_perf_metrics
from ftw.monitor.dump_metrics import find_instances
from ftw.monitor.dump_metrics import get_base_port
from ftw.monitor.dump_metrics import get_supervisor_conf
from ftw.monitor.dump_metrics import get_supervisor_port
from ftw.monitor.dump_metrics import retrieve_all_perf_metrics
from ftw.monitor.dump_metrics import to_influxdb_line_protocol
from ftw.monitor.testing import MONITOR_INTEGRATION_TESTING
from ftw.monitor.testing import MonitorTestCase
from ftw.testing.layer import TEMP_DIRECTORY
from os.path import join as pjoin
from unittest import TestCase
import os
import textwrap


TEST_ZODB_NAME = 'unnamed'


def parse_influx_line(line):
    """Parse a single InfluxDB line protocol line.

    Format:
    measurement,tag1=val1,tag2=val2 fld1=val1,fld2=val2
    """
    preamble, field_set = line.split(' ')
    measurement, tag_set = preamble.split(',', 1)

    tags = dict([pair.split('=') for pair in tag_set.split(',')])
    fields = dict([pair.split('=') for pair in field_set.split(',')])

    return {
        'measurement': measurement,
        'tags': tags,
        'fields': fields,
    }


class TestDumpMetrics(MonitorTestCase):

    layer = MONITOR_INTEGRATION_TESTING

    def test_retrieve_all_perf_metrics(self):
        pseudo_instance_port = self.monitor_port - 80

        result = retrieve_all_perf_metrics([
            {'name': 'instance1', 'port': pseudo_instance_port},
            {'name': 'instance2', 'port': pseudo_instance_port},

        ], command='perf_metrics %s' % TEST_ZODB_NAME)

        self.assertItemsEqual(['instance1', 'instance2'], result.keys())

        self.assertItemsEqual(
            [u'instance', u'cache', u'db', u'memory'],
            result['instance1'].keys())

    def test_fetch_perf_metrics(self):
        metrics = fetch_perf_metrics(
            self.monitor_port, command='perf_metrics %s' % TEST_ZODB_NAME)

        self.assertItemsEqual(
            [u'instance', u'cache', u'db', u'memory'], metrics.keys())


class TestDumpMetricsUnit(TestCase):

    layer = TEMP_DIRECTORY

    def _create_fake_deployment_directory(self):
        deployment_dir = self.layer['temp_directory']
        bin_dir = pjoin(deployment_dir, 'bin')
        os.makedirs(bin_dir)

        for instance_no in range(0, 5):
            instance_name = 'instance%s' % instance_no
            path = pjoin(bin_dir, instance_name)
            path.touch()

        supervisor_dir = pjoin(deployment_dir, 'parts', 'supervisor')
        os.makedirs(supervisor_dir)

        supervisord_conf_path = pjoin(supervisor_dir, 'supervisord.conf')
        with open(supervisord_conf_path, 'w') as sv_conf:
            sv_conf.write(textwrap.dedent("""\
            [inet_http_server]
            port = 127.0.0.1:17799
            username = supervisor
            password = admin
            """))

        return deployment_dir

    def test_to_influxdb_line_protocol(self):
        metrics = {
            'instance1': {
                'cache':
                    {'size': 10,
                     'max_size': 20},
                'memory':
                    {'pss': 5,
                     'rss': 15},
            },
            'instance2': {
                'cache':
                    {'size': 11,
                     'max_size': 22},
                'memory':
                    {'pss': 7,
                     'rss': 42},
            },
        }

        expected = textwrap.dedent("""\
        deployments,deployment=01-foo.example.org,process=instance1 cache.max_size=20,cache.size=10,memory.pss=5,memory.rss=15
        deployments,deployment=01-foo.example.org,process=instance2 cache.max_size=22,cache.size=11,memory.pss=7,memory.rss=42
        """)  # noqa

        influx_lines = to_influxdb_line_protocol(metrics, '01-foo.example.org')
        self.assertEqual(expected, influx_lines)

    def test_get_supervisor_conf(self):
        deployment_dir = self._create_fake_deployment_directory()

        conf = get_supervisor_conf(deployment_dir)
        bind_addr = conf.get('inet_http_server', 'port')
        self.assertEqual('127.0.0.1:17799', bind_addr)

    def test_get_supervisor_port(self):
        deployment_dir = self._create_fake_deployment_directory()

        port = get_supervisor_port(deployment_dir)
        self.assertEqual(17799, port)

    def test_get_base_port(self):
        deployment_dir = self._create_fake_deployment_directory()

        port = get_base_port(deployment_dir)
        self.assertEqual(17700, port)

    def test_find_instances(self):
        deployment_dir = self._create_fake_deployment_directory()

        instances = find_instances(deployment_dir)
        self.assertEqual([
            {'name': u'instance0', 'number': 0, 'port': 17700},
            {'name': u'instance1', 'number': 1, 'port': 17701},
            {'name': u'instance2', 'number': 2, 'port': 17702},
            {'name': u'instance3', 'number': 3, 'port': 17703},
            {'name': u'instance4', 'number': 4, 'port': 17704}],
            instances)
