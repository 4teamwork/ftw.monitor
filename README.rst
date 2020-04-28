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

In addition, ``ftw.monitor`` also provides a ``perf_metrics`` command that
allows to interrogate an instance for performance related metrics.


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
      perf_metrics -- Get performance related metrics
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


Automatic Warmup
----------------

By default, ``ftw.monitor`` will automatically warm up a booting instance, by
sending a request to the `@@warmup` view. The instance will be considered
healthy (by the ``health_check`` command) once the warmup has been performed
successfully.

If this behavior is not desired, automatic warmup can be disabled by setting
the ``FTW_MONITOR_AUTOWARMUP`` environment variable to ``0`` before starting
the instance(s):

.. code:: bash

    export FTW_MONITOR_AUTOWARMUP=0


Performance Metrics
-------------------

The ``perf_metrics`` command can be used to query an instance for various
metrics that are related to performance.

Syntax: ``perf_metrics [dbname] [sampling-interval]``

You can pass a database name, where "-" is an alias for the ``main`` database,
which is the default. The sampling interval (specified in seconds)
defaults to 5m, and affects DB statistics retrieved from the ZODB
ActivityMonitor, specifically ``loads``, ``stores`` and ``connections``.

The maximum history length (and therefore sampling interval) configured in
the ActivityMonitor is 3600s in a stock installation.     

The command will return the metrics as a JSON encoded string
(*whitespace added for clarity*).

.. code:: json

    {
        "instance": {
            "uptime": 39
        },
        "cache": {
            "size": 3212,
            "ngsize": 1438,
            "max_size": 30000
        },
        "db": {
            "loads": 1114,
            "stores": 28,
            "connections": 459,
            "conflicts": 7,
            "unresolved_conflicts": 3,
            "total_objs": 13336,
            "size_in_bytes": 5796849
        },
        "memory": {
            "rss": 312422400,
            "uss": 298905600,
            "pss": 310822823
        }
    }

**instance**

- ``uptime`` - Time since instance start (in seconds)

**cache**

- ``size`` - Number of objects in cache
- ``ngsize`` - Number of non-ghost objects in cache
- ``max_size`` - Cache size (in number of objects)

**db**

- ``loads`` - Number of object loads in sampling interval
- ``stores`` - Number of object stores in sampling interval
- ``connections`` - Number of connections in sampling interval
- ``conflicts`` - Total number of conflicts since instance start
- ``unresolved_conflicts`` - Total number of unresolved conflicts since instance start
- ``total_objs`` - Total number of objects in the storage 
- ``size_in_bytes`` - Size of the storage in bytes (so FileStorage's ``Data.fs``, usually. Excludes BlobStorage)

.. note::
    - loads, stores and connections are cumulative across all connections in the pool of that instance.
    - total_objs and size_in_bytes may or may not be reported correctly when using ``RelStorage``, depending on the SQL adapter

**memory**

- ``rss`` - RSS (Resident Set Size) in bytes
- ``uss`` - USS (`Unique Set Size`_) in bytes
- ``pss`` - PSS (Proportional Set Size) in bytes (Linux only, ``-1`` on other platforms)


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


Switching to ftw.monitor
------------------------

In order to switch to ``ftw.monitor`` for health monitoring, the following
steps are necessary:

- Configure your zope instance to only use one ZServer thread. ``ftw.monitor``
  is intended for use in setups with one thread per instance.
  Example using buildout and ``plone.recipe.zope2instance``:

  .. code:: ini
  
      [instance0]
      zserver-threads = 1

- Remove any ``HttpOk`` plugins from your supervisor configuration. With only
  one thread per instance, that approach to service monitoring can't work
  any more, and *must* be disabled.

  If you're extending from ``production.cfg`` and/or ``zeoclients/<n>.cfg``
  from ``ftw-buildouts``, you can get rid of the ``HttpOk`` supervisor plugins
  like this (after extending from one of these configs):

  .. code:: ini
  
      [supervisor]
      eventlisteners-httpok =

- Remove ``collective.warmup`` (if present). Since ``ftw.monitor`` includes
  its own auto-warmup logic, the use of ``collective.warmup`` is unnecessary
  (or even detrimental).

  If you're extending from ``warmup.cfg`` from
  ``ftw-buildouts``, you can neutralize  ``collective.warmup`` with a section
  like this (after extending from ``warmup.cfg``):

  .. code:: ini
  
      [buildout]
      warmup-parts =
      warmup-eggs =
      warmup-instance-env-vars =

- Change your HAProxy health checks to TCP checks instead of HTTP. See the
  section above for an example of an appropriate HAProxy configuration.



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

.. _`Unique Set Size`: https://psutil.readthedocs.io/en/latest/#psutil.Process.memory_full_info
