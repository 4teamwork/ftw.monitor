from ftw.monitor.dump_metrics import dump_all_perf_metrics
from ftw.monitor.dump_metrics import get_deployment_dir
from ftw.monitor.server import determine_monitor_port
from ftw.monitor.utils import netcat


def monitor(zope2Cmd, *args):
    """Send a command to the monitor server via TCP and display the response.

    Usage: bin/instance monitor <monitor_cmd>
    """
    monitor_port = determine_monitor_port(zope2Cmd.options.configroot,
                                          consider_factories=True)

    if args == ('',):
        content = 'help'
    else:
        content = ' '.join(args)
    netcat('127.0.0.1', int(monitor_port), '%s\n' % content)


def dump_perf_metrics():
    """Collect and dump performance metrics for all instances in
    InfluxDB line protocol format.
    """
    deployment_dir = get_deployment_dir()
    print dump_all_perf_metrics(deployment_dir)
