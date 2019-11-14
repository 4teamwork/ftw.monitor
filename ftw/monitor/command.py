from ftw.monitor.server import determine_monitor_port
import socket


def netcat(hostname, port, content):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((hostname, port))
    s.sendall(content)
    while 1:
        data = s.recv(1024)
        if data == "":
            break
        print data.strip()
    s.close()


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
