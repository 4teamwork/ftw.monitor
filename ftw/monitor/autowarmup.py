import logging
import os
import requests
import threading


log = logging.getLogger('ftw.monitor')


def autowarmup(port):
    """Send a warmup request to a booting instance in a non-blocking way.
    """
    log.info("Autowarmup starting...")

    # Fire off a daemon thread that triggers the warmup in order to not block
    # instance startup. Doing a blocking request here would deadlock.
    warmup_thread = threading.Thread(
        name='warmup-%s' % port,
        target=trigger_warmup,
        args=(port,))
    warmup_thread.setDaemon(True)

    # Start the thread. No need to ever join it - it will either terminate on
    # its own once the warmup response is received, or, since it's a daemon
    # thread, will be killed when the main thread exits.
    warmup_thread.start()


def trigger_warmup(port):
    """Dispatch a warmup request to the @@warmup view on the Zope app root.
    """
    url = 'http://localhost:%s/@@warmup' % port

    # Time until ZServer starts accepting connections on the socket.
    # With the fast-listen option this is usually very quick, but we
    # still allow for a reasonable grace period.
    connect_timeout = 20

    # Time to first byte received (or more specifically, time between bytes).
    # Since the warmup view doesn't stream a progress response, this needs
    # to cover the entire duration of the warmup
    # (otherwise a ReadTimeout exception will be raised)
    read_timeout = 60 * 30

    response = requests.get(url, timeout=(connect_timeout, read_timeout))
    log.info("Warmup response: %r (%r)" % (response, response.content))
    log.info("Autowarmup request finished.")


def autowarmup_enabled():
    """Determine whether autowarmup is enabled.
    """
    env_flag = os.environ.get('FTW_MONITOR_AUTOWARMUP', 'true')
    return env_flag.lower() not in ('0', 'false', 'no', 'off')
