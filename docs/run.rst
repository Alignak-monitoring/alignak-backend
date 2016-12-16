.. _run:

Run
===

Production mode
---------------

First create a file anywhere on your system, named 'alignakbackend.py' and containing::

    from alignak_backend.app import app

You can use many possibilities, but we suggest you use uwsgi and start it in the same directory as the file created previously.

With sockets (+ nginx / apache in frontal)::

   uwsgi -s /tmp/uwsgi.sock -w alignakbackend:app --enable-threads -p 4

With direct http port::

   uwsgi --wsgi-file alignakbackend.py -w alignakbackend:app --socket 0.0.0.0:80 --protocol=http --enable-threads -p 4

Maybe, you will have to add the python plugin on some Linux distributions (Debian)::

   uwsgi --plugin python --wsgi-file alignakbackend.py -w alignakbackend:app --socket 0.0.0.0:80 --protocol=http --enable-threads -p 4


Alignak-backend runs on port 80 as specified in arguments, so you should use ``http://ip:80/`` or ``http://ip/`` as a base URL for the API.

Developer mode
--------------

To run in developper mode (meaning with few connections), you can start the backend with this command::

    alignak_backend

On start, some useful information are printed on the console::

    *** Starting uWSGI 2.0.12-debian (64bit) on [Thu Dec 15 08:32:51 2016] ***
    compiled with version: 5.3.1 20160412 on 13 April 2016 08:36:06
    os: Linux-4.4.0-53-generic #74-Ubuntu SMP Fri Dec 2 15:59:10 UTC 2016
    nodename: Alignak-VirtualBox
    machine: x86_64
    clock source: unix
    pcre jit disabled
    detected number of CPU cores: 2
    current working directory: /home/alignak/alignak-backend
    detected binary path: /usr/bin/uwsgi-core
    *** WARNING: you are running uWSGI without its master process manager ***
    your processes number limit is 15649
    your memory page size is 4096 bytes
    detected max file descriptor number: 1024
    lock engine: pthread robust mutexes
    thunder lock: disabled (you can enable it with --thunder-lock)
    uwsgi socket 0 bound to TCP address 0.0.0.0:5000 fd 3
    Python version: 2.7.12 (default, Nov 19 2016, 06:48:10)  [GCC 5.4.0 20160609]
    Python main interpreter initialized at 0x26e7760
    python threads support enabled
    your server socket listen backlog is limited to 100 connections
    your mercy for graceful operations on workers is 60 seconds
    mapped 291072 bytes (284 KB) for 4 cores
    *** Operational MODE: preforking ***
    --------------------------------------------------------------------------------
    Alignak_Backend, version 0.5.5
    Copyright (c) 2015 - Alignak team
    License GNU Affero General Public License, version 3
    --------------------------------------------------------------------------------
    Doc: https://github.com/Alignak-monitoring-contrib/alignak-backend
    Release notes: Alignak REST Backend
    --------------------------------------------------------------------------------
    Using settings file: /etc/alignak-backend/settings.json
    Application settings: {'CARBON_PORT': 2004, 'XML': False, 'GRAPHITE_PORT': 8080, 'JOBS': [], 'PAGINATION_DEFAULT': 25, u'GRAFANA_HOST': None, 'GRAPHITE_HOST': u'', u'RATE_LIMIT_POST': None, 'PORT': 5000, u'MONGO_USERNAME': None, 'SERVER_NAME': None, 'X_HEADERS': 'Authorization, If-Match, X-HTTP-Method-Override, Content-Type', 'X_DOMAINS': u'*', 'SCHEDULER_TIMESERIES_ACTIVE': False, u'GRAFANA_PORT': 3000, 'INFLUXDB_PORT': 8086, u'RATE_LIMIT_DELETE': None, 'INFLUXDB_DATABASE': u'alignak', 'SCHEDULER_TIMEZONE': 'Etc/GMT', u'MONGO_PASSWORD': None, 'CARBON_HOST': u'', 'MONGO_PORT': 27017, 'RESOURCE_METHODS': ['GET', 'POST', 'DELETE'], 'MONGO_DBNAME': u'alignak-backend', 'HOST': u'', u'GRAFANA_APIKEY': u'', 'DEBUG': False, u'RATE_LIMIT_PATCH': None, 'INFLUXDB_PASSWORD': u'admin', 'PAGINATION_LIMIT': 50, 'INFLUXDB_HOST': u'', 'INFLUXDB_LOGIN': u'admin', 'SCHEDULER_GRAFANA_ACTIVE': False, 'ITEM_METHODS': ['GET', 'PATCH', 'DELETE'], u'RATE_LIMIT_GET': None, 'MONGO_HOST': u'localhost', 'MONGO_QUERY_BLACKLIST': ['$where'], u'GRAFANA_TEMPLATE_DASHBOARD': {u'timezone': u'browser', u'refresh': u'1m'}}
    WSGI app 0 (mountpoint='') ready in 3 seconds on interpreter 0x26e7760 pid: 1721 (default app)
    *** uWSGI is running in multiple interpreter mode ***
    spawned uWSGI worker 1 (pid: 1721, cores: 1)
    spawned uWSGI worker 2 (pid: 1729, cores: 1)
    spawned uWSGI worker 3 (pid: 1730, cores: 1)
    spawned uWSGI worker 4 (pid: 1731, cores: 1)


Alignak-backend runs on port 5000, so you should use ``http://ip:5000/`` as a base URL for the API.
