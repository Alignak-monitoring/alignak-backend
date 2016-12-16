.. _configuration:

Configuration
=============

Introduction
------------

The backend uses a configuration file.
It is located in one of these folders:

* /usr/local/etc/alignak_backend/settings.json
* /etc/alignak_backend/settings.json

It's a JSON structured file.

Debug section
-------------

By default, debug mode is disabled, if you want to activate it, modify for::

    "DEBUG": true,


Webserver configuration
-----------------------

It's used in case you want to run the backend in developer mode.

Define IP listening (empty value = listen on all IP)::

    "HOST": "",

Define port listening::

    "PORT": 5000,

Define server name listening::

    "SERVER_NAME": null,


Cross-Origin Resource Sharing
-----------------------------

You can configure the Cross-Origin Resource Sharing (CORS) to define who can access with cross-origin.
To accept all::

    "X_DOMAINS": "*",


Pagination
----------

it's possible to modify the maximum pagination (limit) of items returned by the backend::

    "PAGINATION_LIMIT": 50,

And the default value for the pagination::

    "PAGINATION_DEFAULT": 25,

Rate limit
----------

It's possible to limit the number of requests.
For example, define value [300, 900] will limit 300 requests every 15 minutes.
You define the values for each methods (GET, POST, PATCH, DELETE). An example::

    "RATE_LIMIT_GET": [300, 900],
    "RATE_LIMIT_POST": null,
    "RATE_LIMIT_PATCH": null,
    "RATE_LIMIT_DELETE": null,


MongoDB access
--------------

You need to fill information about the MongoDB to access it in goal to store and get data.

The hostname of the server where the MongoDB run::

    "MONGO_HOST": "localhost",

The port of the MongoDB::

    "MONGO_PORT": 27017,

The database name of MongoDB used for the Backend::

    "MONGO_DBNAME": "alignak-backend",

The username and password to access MongoDB and the database defined previously::

    "MONGO_USERNAME": null,
    "MONGO_PASSWORD": null,

Timeseries databases
--------------------

To store the metrics, we need to configure Carbon/Graphite or/and InfluxDB.

For Carbon/Graphite::

    "GRAPHITE_HOST": "",
    "GRAPHITE_PORT": 8080,
    "CARBON_HOST": "",
    "CARBON_PORT": 2004,

For InfluxDB::

  "INFLUXDB_HOST": "",
  "INFLUXDB_PORT": 8086,
  "INFLUXDB_DATABASE": "alignak",
  "INFLUXDB_LOGIN": "admin",
  "INFLUXDB_PASSWORD": "admin",

The timeseries information are stored in the backend (like retention) and send with a scheduled
cron (internal in the Backend), so need to activate this cron, but only on 1 Backend in case you
have a cluster of Backend (many backends).

Activate with::

    "SCHEDULER_TIMESERIES_ACTIVE": true,

Grafana: the dashboard/graph tool
---------------------------------

The backend can create the dahboards (one per host) and the graphs (one per host and one per
services in the dashboad of the host related). Need too activate it on 1 Backend in case you have
a cluster of Backend (many backends).

For that, activate it::

    "SCHEDULER_GRAFANA_ACTIVE": true,

Define the hostname and port of Grafana::

    "GRAFANA_HOST": "",
    "GRAFANA_PORT": 3000,

Create an API KEY in Grafana with right *admin* and put it in configuration file::

  "GRAFANA_APIKEY": "",

The default values for the dashboards::

  "GRAFANA_TEMPLATE_DASHBOARD": {
    "timezone": "browser",
    "refresh": "1m"
  }

