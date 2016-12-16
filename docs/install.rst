.. _install:

Installation
============

Requirements
------------

To use this Alignak backend, you first need to install and run MongoDB_

.. _MongoDB: http://docs.mongodb.org/manual/

As an excerpt of the MongoDB installation documentation, this script will install the Mongo DB community edition on a Linux Ubuntu 16::

    sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 0C49F3730359A14518585931BC711F9BA15703C6
    echo "deb http://repo.mongodb.org/apt/ubuntu xenial/mongodb-org/testing multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-3.4.list
    sudo apt-get update
    sudo apt-get install -y mongodb-org
    sudo service mongod start


.. warning:: Check for your specific Unix/Linux distribution in the `MongoDB_` installation documentation.


If you want to run with uwsgi, you need to install uwsgi and its python plugin (on Debian)::

    sudo apt-get install uwsgi uwsgi-plugin-python

Install with pip
----------------

With pip
~~~~~~~~

You can install with pip::

    pip install alignak_backend


From source
~~~~~~~~~~~

You can install it from source::

    git clone https://github.com/Alignak-monitoring/alignak-backend
    cd alignak-backend
    pip install .


For contributors
~~~~~~~~~~~~~~~~

If you want to hack into the codebase (e.g for future contribution), just install like this::

    pip install -e .


Install from source without pip
-------------------------------

If you are on Debian::

    sudo apt-get -y install python python-dev python-pip git


Get the project sources::

    git clone https://github.com/Alignak-monitoring/alignak-backend


Install python prerequisites (Normally, you can install with user *alignak* )::

    pip install -r alignak-backend/requirements.txt


And install::

    cd alignak-backend
    sudo python setup.py install
