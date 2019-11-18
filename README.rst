Introduction
============

``ftw.monitor`` automatically starts a `zc.monitor <https://pypi.org/project/zc.monitor/>`_ server on instance boot.

This monitor server supports a ``health_check`` command that can be used as
a TCP health check in HAProxy or service monitoring framworks.

``ftw.monitor`` is an alternative to `collective.monitor <https://pypi.org/project/collective.monitor/>`_
or `five.z2monitor <https://pypi.org/project/five.z2monitor/>`_ in that it
completly relies on **autoconfiguration**. No product-config or ZCML is needed,
the monitor port will always be picked automatically based on the instance's base port:

``monitor_port = instance_port + 80``


.. contents:: Table of Contents


Compatibility
-------------

Plone 4.3.x


Installation
============

- Add the package to your buildout configuration:

.. code:: ini

    [instance]
    eggs +=
        ...
        ftw.monitor

Usage
=====

Once ``ftw.monitor`` is included in your instance(s) eggs, it will
automatically start a monitor server upon instance boot:

.. code::

    INFO ZServer HTTP server started at Mon May  6 14:53:08 2019
        Hostname: 0.0.0.0
        Port: 8080

    ...

    INFO zc.ngi.async.server listening on ('', 8160)


The monitor server port is derived from the instance's port:

``monitor_port = instance_port + 80``

The monitor server can be inspected and tested using **netcat**:

.. code:: sh

    $ echo 'help' | nc -i 1 localhost 8160

    Supported commands:
      dbinfo -- Get database statistics
      health_check -- Check whether the instance is alive and ready to serve requests.
      help -- Get help about server commands
      interactive -- Turn on monitor's interactive mode
      monitor -- Get general process info
      quit -- Quit the monitor
      zeocache -- Get ZEO client cache statistics
      zeostatus -- Get ZEO client status information

Alternatively, a ``bin/instance monitor <cmd>`` script is provided that
essentially does the same thing (sending the given command to the respective
monitor port and displaying the response):

.. code:: sh

    $ bin/instance monitor help


Health Check
------------

The ``health_check`` command provided by ``ftw.monitor`` allows to check
whether a Zope instance is alive and ready to serve requests.

If so, it will respond with ``OK\n``:

.. code:: sh

    $ echo 'health_check' | nc -i 1 localhost 8160

    OK


While a warmup is in progress (see below), the ``health_check`` will
respond with an according message.


Warmup
------

Because health checks and instance warmup are tricky to deal with separately,
``ftw.monitor`` also provides a mechanism for warming up Plone sites.

A ``@@warmup`` view is provided on both the **Plone site root** as well as
**Zope application root** levels which will warm up either that specific
Plone site, or all Plone sites in that Zope instance.

The warmup view will look for an ``IWarmupPerformer`` multiadapter that adapts
a Plone site and request, and will execute the necessary actions to warm up
that Plone site.

There is a default ``IWarmupPerformer`` implementation in ``ftw.monitor``
which will load catalog BTrees and forward index BTrees of the most used
catalog indexes (``allowedRolesAndUsers`` and ``object_provides``).

While the warmup is in progress, the ``health_check`` command will not yet
indicate the instance as being healthy:

.. code:: sh

    $ echo 'health_check' | nc -i 1 localhost 8160

    Warmup in progress


At this point, ``ftw.monitor`` does *not* yet automatically call this warmup
view on instance startup. This can be achieved by using ``collective.warmup``
and configuring it appropriately.


Automatic Warmup
----------------

By default, ``ftw.monitor`` will automatically warm up a booting instance, by
sending a request to the `@@warmup` view. The instance will be considered
healthy (by the ``health_check`` command) once the warmup has been performed
successfully.

If this behavior is not desired, automatic warmup can be disabled by setting
the ``FTW_MONITOR_AUTOWARMUP`` environment variable to ``0`` before starting
the instance(s):

```bash
export FTW_MONITOR_AUTOWARMUP=0
```


HAProxy example
---------------

The following is an example of how to use the ``health_check`` command as
a HAProxy TCP health check:


.. code:: sh

    backend plone03
        # ...
        option tcp-check
        tcp-check connect
        tcp-check send health_check\r\n
        tcp-check expect string OK

        server plone0301 127.0.0.1:10301 cookie p01 check port 10381 inter 10s downinter 15s maxconn 5 rise 1 slowstart 60s
        server plone0302 127.0.0.1:10302 cookie p02 check port 10382 inter 10s downinter 15s maxconn 5 rise 1 slowstart 60s
        server maintenance 127.0.0.1:10319 backup

Note in particular that ``option tcp-check`` changes all health checks for
this backend to TCP mode. So the ``maintenance`` server in this example,
which is an HTTP server, needs to have health checks turned off.


collective.warmup example
-------------------------

If using `ftw-buildouts <https://github.com/4teamwork/ftw-buildouts/#warmup/>`_
to configure ``collective.warmup``, the following configuration can be used:


.. code:: ini

    [warmup-configuration]
    base_path = /@@warmup


Development
===========

1. Fork this repo
2. Clone your fork
3. Shell: ``ln -s development.cfg buildout.cfg``
4. Shell: ``python bootstrap.py``
5. Shell: ``bin/buildout``

Run ``bin/test`` to test your changes.

Or start an instance by running ``bin/instance fg``.


Links
=====

- Github: https://github.com/4teamwork/ftw.monitor
- Issues: https://github.com/4teamwork/ftw.monitor/issues
- Pypi: http://pypi.python.org/pypi/ftw.monitor


Copyright
=========

This package is copyright by `4teamwork <http://www.4teamwork.ch/>`_.

``ftw.monitor`` is licensed under GNU General Public License, version 2.
