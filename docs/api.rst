.. _api:

Developer Interface
===================

This part of the documentation is related to the REST API used to interact with this backend.
The examples in this part of the documentation use :

   * IP as 127.0.0.1
   * a resource name as service

Browse Alignak backend API (Swagger)
------------------------------------

The Alignak backend API can be browsed with a Web Browser on this URL::

    http://127.0.0.1:5000/docs

This URL is served by the Swagger UI embedded into the Alignak backend.


Authentication in the backend
-----------------------------

The backend API needs an authentication for each request. Some user accounts are defined with *username*, *password* and *token*.

To access any backend enpoint, you need to provide the *token* associated to the user account.

Get the authentication token
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

POST on *http://127.0.0.1:5000/login* with fields:

* *username*: xxx
* *password*: xxx

Example 1, JSON data in request body::

    curl -H "Content-Type: application/json" -X POST -d '{"username":"admin","password":"admin"}' http://127.0.0.1:5000/login

Example 2, HTML form data::

    curl -X POST -H "Cache-Control: no-cache" -H "Content-Type: multipart/form-data" -F "username=admin" -F "password=admin" 'http://127.0.0.1:5000/login'

The response will provide the token to use in the next requests.

Example of answer::

    {
        "token": "1442583814636-bed32565-2ff7-4023-87fb-34a3ac93d34c"
    }

Generate new token (so revoke old)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to generate a new token (mean revoke old token), add this field to the request made
when you get the token:

* *action*: *generate*

Example::

    curl -H "Content-Type: application/json" -X POST -d '{"username":"admin","password":"admin","action":"generate"}' http://127.0.0.1:5000/login


How to use the token
~~~~~~~~~~~~~~~~~~~~

For all method you request on an endpoint, you need to provide the token.
You can use *basic auth*: use the token as a username and set password as empty.


GET method (get)
----------------

Get all available enpoints
--------------------------

All resources available in the backend are listed on the root endpoint of the backend::

    http://127.0.0.1:5000


All items
~~~~~~~~~

The endpoint to get all items of a resource is::

    http://127.0.0.1:5000/service

The items will be in response in section *_items*.


~~~~~~~~~~~~~~~~~~~~~
All items + filtering
~~~~~~~~~~~~~~~~~~~~~

We can filter items to get with this syntax::

    http://127.0.0.1:5000/service?where={"service_description": "ping"}

~~~~~~~~~~~~~~~~~~~
All items + sorting
~~~~~~~~~~~~~~~~~~~

We can sort items to get with this syntax::

    http://127.0.0.1:5000/service?sort=service_description

If you want to sort descending::

    http://127.0.0.1:5000/service?sort=-service_description

~~~~~~~~~~~~~~~~~~~~
All items + embedded
~~~~~~~~~~~~~~~~~~~~

In this example, service resource has data relation with host resource through the *host_name* field.
If you get items, you will receive an _id like *55d113976376e9835e1b2feb* in this field.

It's possible to have all fields of the host, instead of its _id, in the response with::

    http://127.0.0.1:5000/service?embedded={"host_name":1}

~~~~~~~~~~~~~~~~~~~~~~
All items + projection
~~~~~~~~~~~~~~~~~~~~~~

Projection is used to get only some fields for each items.
For example, to get only *service_description* of services::

    http://127.0.0.1:5000/service?projection={"service_description":1}

~~~~~~~~~~
Pagination
~~~~~~~~~~

The pagination is by default configured to 25 per request/page. It's possible to increase it to
the limit of 50 with::

    http://127.0.0.1:5000/service?max_results=50

In case of have many pages, in the items got, you have section::

    _links: {
        self: {
            href: "service",
            title: "service"
        },
        last: {
            href: "service?page=13",
            title: "last page"
        },
        parent: {
            href: "/",
            title: "home"
        },
        next: {
            href: "service?page=2",
            title: "next page"
        }
    },

So if you receive *_links/next*, there is a next page that can be found with *_links/next/href*.

~~~~~~~~~~~~~~~~
Meta information
~~~~~~~~~~~~~~~~

In the answer, you have a meta section::

    _meta: {
        max_results: 25,
        total: 309,
        page: 1
    }


One item
~~~~~~~~

To get only one item, we query with the *_id* in endpoint, like::

    http://127.0.0.1:5000/service/55d113976376e9835e1b3fee

It's possible in this case to use:

* projection_
* embedded_


.. _projection: #all-items-projection
.. _embedded: #all-items-embedded

POST method (add)
-----------------

This method is used to *create a new item*.
It's required to use HTTP *POST* method.

You need to point to the endpoint of the resource like::

    http://127.0.0.1:5000/service

and send JSON data like::

    {"service_description":"ping","notification_interval":60}

If you want to add a relation with another resource, you must add the id of the resource, like::

    {"service_description":"ping","notification_interval":60,"host_name":"55d113976376e9835e1b2feb"}

You will receive a response with the new *_id* and the *_etag* like::

    {"_updated": "Tue, 25 Aug 2015 14:10:02 GMT", "_links": {"self": {"href": "service/55dc773a6376e90ac95f836f", "title": "Service"}}, "_created": "Tue, 25 Aug 2015 14:10:02 GMT", "_status": "OK", "_id": "55dc773a6376e90ac95f836f", "_etag": "3c996dc10cb86173fa79f807e0d84e88c2f3a28f"}


PATCH method (update)
---------------------

This method is used to *update fields* of an item.
It's required to use HTTP *PATCH* method.

You need to point to the item endpoint of the resource like::

    http://127.0.0.1:5000/service/55dc773a6376e90ac95f836f

You need to add in headers the *_etag* you got when adding the object or when you got data of this item::

    "If-Match: 3c996dc10cb86173fa79f807e0d84e88c2f3a28f"

and send JSON data like::

    {"service_description":"pong"}


DELETE method (delete)
----------------------

It's required to use HTTP *DELETE* method.

All items
~~~~~~~~~

The endpoint to delete all items of a resource is::

    http://127.0.0.1:5000/service

One item
~~~~~~~~

The endpoint to delete an item of a resource is::

    http://127.0.0.1:5000/service/55dc773a6376e90ac95f836f



Rights management
-----------------

The is a right management into backend. With that, it will very simple to create a frontend with
user rights ;)

Right to all data without restrictions in a realm
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You have the possibility to give access (read, create, update and delete) to all resource to a
user/contact (it's like you have by default with *admin* account)

In *contact* resource, set:

* *back_role_super_admin* to *True*
* *_realm* to the realm id you want
* *_sub_realm* to *True* if you want this realm + all children or *False* for only this realm


Right to a resource in a realm
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add a resource *contactrestrictrole* for each crud (create, read, update, delete) and resource

For that, add a right read of commands with the *contactrestrictrole*:

* *contact* to id of the contact
* *realm* to the id of the realm where you want have the read access
* *sub_realm* to *True* if want have the read access in all realm children
* *resource* with the name of resource, in our case *command*
* *crud* to *read* because we want read access

For each resource and each crud you need add a *contactrestrictrole*.


Rights to an object of a resource in a realm
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It's possible to give access to an object of a resource.

For example, you have 3 hosts in the realm *reamlxxx* and want give access to read only to host
*host 1*. We can do this with crud *custom* in *contactrestrictrole* (see previous point and
replace the crud *read* by *custom*).

When it's crud *custom* defined, you need add user/contact id in the object.
So in the host, modify the fields:

* *_users_read* to the user/contact id

Remember the realm id of the resource (*realm* or *_realm* according the resource) must be same
than realm of the *contactrestrictrole* or in a children of the realm if *sub_realm* is *True*


How to  use templates
---------------------

Resources use template system
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The resources using the backend template system are:

   * host
   * service


Use simple template system
~~~~~~~~~~~~~~~~~~~~~~~~~~

To use the simple templating system, you just need to create a template object (*host* or *service*) with these fields:

   * *_is_template*: True

It is as simple as creating an *host* and you just need to add *_is_template = True* in the provided data.

For a *service* template, you need link it to an host, so link it to an host template.

To add a new object (*host* or *service*) linked to one of the template objects, create the object (host/service) with those fields:

   * *_templates*: [*id_of_template*]

You can link an object to more than one template.

When adding the object, if we define for example a field *notification_period*, this field will not be erased by the template(s) field

In case you modify one field of the template, the backend will report the value to all objects use this template


Complex template system
~~~~~~~~~~~~~~~~~~~~~~~

There is a *complex* template system.

You can defined, like for simple template system, host template with one or many services templates
linked to this host.


If you create a host with fields:
* *_templates*: [*id_of_template*]
* *_templates_with_services*: True


The backend will create the host + all services related to the services templates linked to the host.

With an example, it's better! We have the templates::

    standard_template (host)
            |------------------> check_cpu_template (service)
            |------------------> check_mem_template (service)
            |------------------> check_load_template (service)

We create a host linked to *standard_template* template and with *_templates_with_services* to True.

We have now::

    standard_template (host)
            |------------------> check_cpu_template (service)
            |------------------> check_mem_template (service)
            |------------------> check_load_template (service)
    myhost (host)
            |------------------> check_cpu (service)
            |------------------> check_mem (service)
            |------------------> check_load (service)



Timeseries databases
--------------------

To store the metrics, we need to configure Carbon/Graphite or/and InfluxDB.

These timeseries interfaces can be defined by realm + sub realm, and so you can have multiple
timeseries database in a realm.

For Carbon/Graphite, use resource _graphite_, composed with information:

* *carbon_address*: address of carbon (IP, DNS),
* *carbon_port*: port of carbon, default 2004,
* *graphite_address*: address of graphite (IP, DNS),
* *graphite_port*: port of graphite, default 8080,
* *prefix*: a prefix to use in carbon for our data
* *grafana*: id of grafana

Curl example::

    curl -X POST -H "Content-Type: application/json"
    -H "Authorization: Basic MTQ3NjU2NDExMDA0MS1kN2FlNDYwZi1mZWQ3LTQ5YjQtYWMwZS04NTRlNGU0ODhmOWU6"
    -H "Cache-Control: no-cache" -d '[
	{
        "name": "graphite_001",
        "carbon_address": "192.168.0.200",
        "carbon_port": 2004,
        "graphite_address": "192.168.0.200",
        "graphite_port": 8080,
        "prefix": "001.a",
        "grafana": "5864c1c98bde9c8bd787a779",
        "_realm": "5864c1c98bde9c8bd787a781",
        "_sub_realm": true
	}
    ]' "http://192.168.0.10:5000/graphite"


For InfluxDB, use resource _influxdb_:

* *address*: address of influxdb (IP, DNS),
* *port*: port of influxdb, default 8086,
* *database*: database name in influxdb
* *login*: login to access to influxdb
* *password*: password to access to influxdb
* *grafana*: id of grafana

Curl example::

    curl -X POST -H "Content-Type: application/json"
    -H "Authorization: Basic MTQ3NjU2NDExMDA0MS1kN2FlNDYwZi1mZWQ3LTQ5YjQtYWMwZS04NTRlNGU0ODhmOWU6"
    -H "Cache-Control: no-cache" -d '[
	{
        "name": "influx_001",
        "address": "192.168.0.200",
        "port": 8086,
        "database": "alignak",
        "login": "alignak",
        "password": "mypass",
        "grafana": "5864c1c98bde9c8bd787a779",
        "_realm": "5864c1c98bde9c8bd787a781",
        "_sub_realm": true
	}
    ]' "http://192.168.0.10:5000/influxdb"


The timeseries information are stored in the backend (like retention) and send with a scheduled
cron (internal in the Backend), so need to activate this cron, but only on one Backend in case you
have a cluster of Backend (many backends).

Activate in configuration file with::

    "SCHEDULER_TIMESERIES_ACTIVE": true,

IMPORTANT: you can't have more than one timeserie database (carbon / influxdb) linked to a grafana
on each realm!

Grafana: the dashboard/graph tool
---------------------------------

The backend can create the dashboards (one per host) and the graphs (one per host and one per
services in the dashboard of the host related).

We need define grafana server and activate the _cron_ on one Backend in case you have
a cluster of Backend (many backends).

For that, activate it in configuration file::

    "SCHEDULER_GRAFANA_ACTIVE": true,

Define the Grafana with resource _grafana_:

* *address*: address of grafana (IP, DNS),
* *port*: port of grafana, default 3000
* *apikey*: the API KEY in grafana with right *admin*
* *timezone*: the timezone used, default _browser_
* *refresh*: refresh time of dashboards, default _1m_ (all 1 minutes)

Curl example::

    curl -X POST -H "Content-Type: application/json"
    -H "Authorization: Basic MTQ3NjU2NDExMDA0MS1kN2FlNDYwZi1mZWQ3LTQ5YjQtYWMwZS04NTRlNGU0ODhmOWU6"
    -H "Cache-Control: no-cache" -d '[
	{
        "name": "influx_001",
        "address": "192.168.0.11",
        "port": 3000,
        "apikey": "43483998029a049494b536aa684398439d",
        "_realm": "5864c1c98bde9c8bd787a781",
        "_sub_realm": true
	}
    ]' "http://192.168.0.10:5000/grafana"


You can create many grafana in the backend, for example a different grafana for each realm. This
possibility can be used to give different access to grafana to different users (with different
grafana server or with same grafana server but with different organizations and so different
API KEYS).

List of resources
-----------------

List of resources and information.


Configuration part
~~~~~~~~~~~~~~~~~~

List of resources used for configuration:

.. toctree::
   :maxdepth: 2
   :glob:

   resources/config*

Action part
~~~~~~~~~~~

List of action resources:

.. toctree::
   :maxdepth: 2
   :glob:

   resources/action*


Live state part
~~~~~~~~~~~~~~~

List of live states (last check date, current state...):

.. toctree::
   :maxdepth: 2
   :glob:

   resources/live*

Retention part
~~~~~~~~~~~~~~

List of retentions resources:

.. toctree::
   :maxdepth: 2
   :glob:

   resources/retention*

Log part
~~~~~~~~

List of log resources:

.. toctree::
   :maxdepth: 2
   :glob:

   resources/log*

