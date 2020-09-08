from fnmatch import fnmatch
from ftw.monitor.utils import netcat
from os.path import basename
from os.path import join as pjoin
import ConfigParser
import json
import logging
import os
import socket
import sys


logger = logging.getLogger(__name__)
logging.basicConfig()


def dump_all_perf_metrics(deployment_dir):
    """Retrieves perf_metrics from all running instances and dumps them in
    InfluxDB line protocol format.
    """
    instances = find_instances(deployment_dir)
    deployment_name = basename(deployment_dir.rstrip(os.path.sep))
    metrics = retrieve_all_perf_metrics(instances)
    influx_lines = to_influxdb_line_protocol(metrics, deployment_name)
    return influx_lines


def find_instances(deployment_dir):
    """Get a list of Zope instances based on filenames in bin/ directory,
    and annotate them with their ports.
    """
    base_port = get_base_port(deployment_dir)

    instances = []
    instance_names = sorted(filter(
        lambda n: fnmatch(n, 'instance?'),
        os.listdir(pjoin(deployment_dir, 'bin'))))

    for instance_name in instance_names:
        instance_num = int(instance_name[-1])
        instances.append({
            'name': instance_name,
            'number': instance_num,
            'port': base_port + instance_num
        })
    return instances


def get_deployment_dir():
    """Locate the base directory of the deployment.

    This relies on the fact that this code is invoked via a console_script
    entry point, and the CWD plus the command line together consitute the
    full, absolute path to the script.

    The same strategy can't be used in other situations, like zopectl
    commands. That's why this helper function currently lives in this module,
    it's not intended to be reused without modification.
    """
    scriptname = 'bin/dump-perf-metrics'
    script_location = pjoin(os.getcwd(), sys.argv[0])
    assert script_location.endswith(scriptname)
    deployment_dir, _ = script_location.split(scriptname)
    return deployment_dir


def get_supervisor_conf(deployment_dir):
    """Return the parsed supervisord.conf
    """
    conf_path = pjoin(deployment_dir, 'parts', 'supervisor', 'supervisord.conf')
    config = ConfigParser.RawConfigParser()
    config.readfp(open(conf_path, 'rb'))
    return config


def get_supervisor_port(deployment_dir):
    """Determine the supervisor deamon port for a deployment.
    """
    supervisor_conf = get_supervisor_conf(deployment_dir)
    bind_addr = supervisor_conf.get('inet_http_server', 'port')
    supervisor_port = int(bind_addr.split(':')[-1])
    return supervisor_port


def get_base_port(deployment_dir):
    """Determine the base port for a deployment.
    """
    supervisor_port = get_supervisor_port(deployment_dir)
    base_port = supervisor_port - 99
    return base_port


def fetch_perf_metrics(monitor_port, command='perf_metrics'):
    """Given a single monitor port, fetch perf_metrics from it and parse
    them as JSON.

    Socket errors like connection refused or timeouts are logged on stderr,
    but otherwise are handled defensively.
    """
    try:
        host = '127.0.0.1'
        reply = netcat(host, monitor_port, '%s\r\n' % command, timeout=1)

    except socket.error as exc:
        logger.warn('%s:%s - %s' % (host, monitor_port, exc))
        return {}

    return json.loads(reply)


def to_influxdb_line_protocol(collected_metrics, deployment_name):
    """
    Convert a dict of metrics for multiple process to InfluxDB line protocol.

    Format:
    weather,location=us-midwest temperature=82 1465839830100400200
      |    -------------------- --------------  |
      |             |             |             |
      |             |             |             |
    +-----------+--------+-+---------+-+---------+
    |measurement|,tag_set| |field_set| |timestamp|
    +-----------+--------+-+---------+-+---------+
    """
    lines = []

    measurement = 'deployments'

    for process_name, metrics in sorted(collected_metrics.items()):
        tags = {
            'deployment': deployment_name,
            'process': process_name,
        }
        tag_set = ','.join(
            ['%s=%s' % (tag, val) for tag, val in sorted(tags.items())])

        flattened_fields = []
        for category, fields in sorted(metrics.items()):
            for fn, value in sorted(fields.items()):
                fqfn = '%s.%s' % (category, fn)
                flattened_fields.append('%s=%s' % (fqfn, value))

        field_set = ','.join(flattened_fields)

        line = '%s,%s %s\n' % (measurement, tag_set, field_set)
        lines.append(line)

    return ''.join(lines)


def retrieve_all_perf_metrics(instances, command='perf_metrics'):
    """Fetch perf_metrics from all reachable instances.
    """
    collected_metrics = {}

    for instance in instances:
        if instance['name'] == 'instance0':
            continue

        monitor_port = instance['port'] + 80
        perf_metrics = fetch_perf_metrics(monitor_port, command=command)
        if perf_metrics:
            collected_metrics[instance['name']] = perf_metrics

    return collected_metrics
