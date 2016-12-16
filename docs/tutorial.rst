.. _tutorial:

Using backend with CURL
=======================

Login
~~~~~

Log-in to the backend and get the user token::

    curl -H "Content-Type: application/json" -X POST -d '{"username":"admin","password":"admin"}' http://127.0.0.1:5000/login

    {
        "token": "1481711206846-c8bfa208-023a-43a6-aa3b-ca31d307e1d0"
    }


Once your get the token, you can use it directly in the http request as the username for a simple authentication::

    curl -X GET --header 'Accept: application/json' -u username:password http://1481711206846-c8bfa208-023a-43a6-aa3b-ca31d307e1d0:@127.0.0.1:5000/

.. note :: Syntax for the url is: http://username:password@127.0.0.1:5000 and you replace username with the token and set password as an empty field.

The best solution is to use the curl parameter that sets the HTTP Authorization according to the username/password couple::

    curl -X GET --header 'Accept: application/json' -u 1481711206846-c8bfa208-023a-43a6-aa3b-ca31d307e1d0: http://127.0.0.1:5000/


Get information from the backend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Getting the hosts list::

    curl -X GET --header 'Accept: application/json' -u 1481711206846-c8bfa208-023a-43a6-aa3b-ca31d307e1d0: http://127.0.0.1:5000/host


Creating an host
~~~~~~~~~~~~~~~~

Create a new host::

    curl -H "Content-Type: application/json" -X POST -d '{"username":"admin","password":"admin"}' http://127.0.0.1:5000/login
