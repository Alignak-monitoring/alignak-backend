.. _install:

Installation
============

Requirements
------------

Python
~~~~~~~

To use the Alignak backend, you first need to have a Python interpreter installed on your system.

To check if Python is installed::

   # Ubuntu 16.04
   $ python --version
   Python 2.7.12

Many systems or Linux distributions (Debian and Ubuntu) are shipped with both Python 2 and Python 3::

   # Ubuntu 16.04
   $ python --version
   Python 2.7.12

   $ python3 --version
   Python 3.5.2

It is also important to install the ``pip`` for Python 3::

   # For Debian-like
   $ sudo apt install python3-pip
   $ pip -V
   pip 8.1.1 from /usr/lib/python3/dist-packages (python 3.5)

   # For CentOS-like
   $ sudo yum install python34-pip

For a CentOS7 Linux, you must install Python 3::

   $ sudo yum install python34

As defined in some PEP, the ``python`` command is mapped to Python 2. This may be a little tricky to use Python 3 per default. Thanks to ``update-alternatives`` it is easy to choose the default Python interpreter::

   # Nothing configured (it is often the case...)
   update-alternatives --list python
   update-alternatives: error: no alternatives for python

   $ sudo update-alternatives --install /usr/bin/python python /usr/bin/python2.7 1
   update-alternatives: using /usr/bin/python2.7 to provide /usr/bin/python (python) in auto mode

   $ sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.5 2
   update-alternatives: using /usr/bin/python3.5 to provide /usr/bin/python (python) in auto mode

   $ update-alternatives --list python
   /usr/bin/python2.7
   /usr/bin/python3.5

   # Python 3.5 is now the default one!
   $ python --version
   Python 3.5.2

   # Change this
   $ update-alternatives --config python
   There are 2 choices for the alternative python (providing /usr/bin/python).

     Selection    Path                Priority   Status
   ------------------------------------------------------------
   * 0            /usr/bin/python3.5   2         auto mode
     1            /usr/bin/python2.7   1         manual mode
     2            /usr/bin/python3.5   2         manual mode

   Press <enter> to keep the current choice[*], or type selection number:

   # Back to Python 2.7 if you choose 1
   $ python --version
   Python 2.7.12

.. note:: that you may need to choose Python 2 as the default interpreter for some operations on your system :/

MongoDB
~~~~~~~

To use this Alignak backend, you need to install and run MongoDB_

.. _MongoDB: http://docs.mongodb.org/manual/

An excerpt for installing MongoDB on an Ubuntu Xenial::

    sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 9DA31620334BD75D9DCB49F368818C72E52529D4
    echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu xenial/mongodb-org/4.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-4.0.list
    sudo apt-get update
    sudo apt-get install -y mongodb-org
    sudo systemctl enable mongod.service
    sudo systemctl start mongod.service


An excerpt for installing MongoDB on CentOS 7::

    sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 9DA31620334BD75D9DCB49F368818C72E52529D4
    sudo vi /etc/yum.repos.d/mongodb-org-3.6.repo
         [mongodb-org-3.6]
         name=MongoDB Repository
         baseurl=https://repo.mongodb.org/yum/redhat/$releasever/mongodb-org/3.6/x86_64/
         gpgcheck=1
         enabled=1
         gpgkey=https://www.mongodb.org/static/pgp/server-3.6.asc

    sudo yum update
    sudo yum install -y mongodb-org
    sudo systemctl enable mongod.service
    sudo systemctl start mongod.service


Configuring MongoDB is not mandatory because the Alignak backend do not require any authenticated connection to the database. But if you wish a more secure DB access with user authentication, you must configure MongoDB::

   mongo

   # Not necessary, but interesting... with the most recent 4.0 version, anew monitoring tool is available;)
   > db.enableFreeMonitoring()
   {
      "state" : "enabled",
      "message" : "To see your monitoring data, navigate to the unique URL below. Anyone you share the URL with will also be able to view this page. You can disable monitoring at any time by running db.disableFreeMonitoring().",
      "url" : "https://cloud.mongodb.com/freemonitoring/cluster/KAI3EQPMSZHNGDELYLDNA6QVCPZ5IK6B",
      "userReminder" : "",
      "ok" : 1
   }

   # Create an admin user for the server
   > use admin
   > db.createUser(
      {
         user: "alignak",
         pwd: "alignak",
         roles: [ { role: "userAdminAnyDatabase", db: "admin" } ]
      }
   )

   Successfully added user: {
      "user" : "alignak",
      "roles" : [
         {
            "role" : "userAdminAnyDatabase",
            "db" : "admin"
         }
      ]
   }

   # Exit and restart the server
   Ctrl+C

   # Configure mongo in authorization mode
   sudo vi /etc/mongod.conf
      security:
         authorization: enabled

   # Restart mongo
   sudo systemctl restart mongod.service
   # As of now, you will need to authenticate for any operation on the MongoDB databases

   mongo -u alignak -p alignak
   > show dbs
   admin   0.000GB
   config  0.000GB
   local   0.000GB


   > use alignak
   > db.createUser(
      {
         user: "alignak",
         pwd: "alignak",
         roles: [ "readWrite", "dbAdmin" ]
      }
   )

   Successfully added user: { "user" : "alignak", "roles" : [ "readWrite", "dbAdmin" ] }

   > db.test.save( { test: "test" } )
   # This will create atest collection in the database, which will create the DB in mongo server

   > show dbs
   admin    0.000GB
   alignak  0.001GB
   config   0.000GB
   local    0.000GB


uWSGI
~~~~~

We recommend to use uWSGI as an application server for the Alignak backend.

You can install uWsgi with the python packaging::

   sudo pip install uWSGI

To get pip3 for Python 3 packages installation::

   sudo apt-get install python3-pip
   sudo pip install uWSGI

If you prefer using your Unix/Linux ditribution packaging to install uWSGI and the alignak backend, please refer to your distribution packages for installing. You will also need to install the uWSGI Python plugin.

As an example on Debian (for python 2)::

   sudo apt-get install uwsgi uwsgi-plugin-python

As an example on Debian (for python 3)::

   sudo apt-get install uwsgi uwsgi-plugin-python3

As an example on CentOS (for python 2)::

   # Il faut les dépôts EPEL !
   sudo yum install epel-release

   sudo yum install uwsgi uwsgi-plugin-python

.. warning:: If you get some errors with the plugins, you will need to set some options in the alignak backend */usr/local/etc/alignak-backend/uwsgi.ini* configuration file. See this configuration file commented accordingly.

Install on Debian-like Linux
----------------------------

Installing Alignak Backend for a Debian based Linux distribution (eg. Debian, Ubuntu, etc.) is using ``deb`` packages and it is the recommended way. You can find packages in the Alignak dedicated repositories.

To proceed with installation, you must register the alignak repository and store its public key on your system. This script is an example (for Ubuntu 16) to be adapted to your system::

Create the file */etc/apt/sources.list.d/alignak.list* with the following content::

   # Alignak DEB stable packages
   sudo echo deb https://dl.bintray.com/alignak/alignak-deb-stable xenial main | sudo tee -a /etc/apt/sources.list.d/alignak.list

If your system complains about missing GPG key, you can add the publib BinTray GPG key::

   sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv D401AB61

If you wish to use the non-stable versions (eg. current develop or any other specific branch), you can also add the repository source for the test versions::

   # Alignak DEB testing packages
   sudo echo deb https://dl.bintray.com/alignak/alignak-deb-testing xenial main | sudo tee -a /etc/apt/sources.list.d/alignak.list

.. note:: According to your OS, replace {xenial} in the former script example:

    - Debian 8: ``jessie``
    - Ubuntu 16.04: ``xenial``
    - Ubuntu 14.04: ``trusty``
    - Ubuntu 12.04: ``precise``

And then update the repositories list::

   sudo apt-get update


Once the download sources are set, you can simply use the standard package tool to have more information about Alignak packages and available versions::

   apt-cache search alignak-backend


Or you can simply use the standard package tool to install Alignak::

   sudo apt install alignak-backend

   # Check Alignak installation
   # It copied the default shipped files and sample configuration.
   ll /usr/local/share/alignak-backend/
      total 28
      drwxrwxr-x 4 root root 4096 juil.  1 11:02 ./
      drwxr-xr-x 9 root root 4096 juil.  1 11:02 ../
      -rwxrwxr-x 1 root root  572 juil.  1 11:01 alignak-backend-uwsgi*
      drwxrwxr-x 4 root root 4096 juil.  1 11:02 bin/
      drwxrwxr-x 2 root root 4096 juil.  1 11:02 etc/
      -rwxrwxr-x 1 root root 3758 juil.  1 11:01 post-install.sh*
      -rw-rw-r-- 1 root root  507 juil.  1 11:01 requirements.txt

   # It installed the Alignak systemctl services
   ll /lib/systemd/system/alignak*
      -rw-r--r-- 1 root root 1715 juil.  1 11:12 /lib/systemd/system/alignak-backend.service

   # Alignak backend service status
   sudo systemctl status alignak-backend
   $ sudo systemctl status alignak-backend
      ● alignak-backend.service - uWSGI instance to serve Alignak backend
         Loaded: loaded (/lib/systemd/system/alignak-backend.service; enabled; vendor preset: enabled)
         Active: inactive (dead)

.. note:: that immediately after the installation the *alignak-backend* service is enabled and started! This is a side effect of the packaging tool that is used (*fpm*).

A post-installation script (repository *bin/post-install.sh*) is started at the end of the installation procedure to install the required Python packages. This script is copied during the installation in the default installation directory: */usr/local/share/alignak*. It is using the Python pip tool to get the Python packages listed in the default installation directory *requirements.txt* file.


It is recommended to install a log rotation because the Alignak backend log may be realltyy verbose ! Using the ``logrotate`` is easy. Create a file */etc/logrotate.d/alignak-backend* with this content::

   "/var/log/alignak-backend/*.log" {
     copytruncate
     daily
     rotate 5
     compress
     delaycompress
     missingok
     notifempty
   }


Install on RHEL-like Linux
--------------------------

Installing Alignak backend for an RPM based Linux distribution (eg. RHEL, CentOS, etc.) is using ``rpm`` packages and it is the recommended way. You can find packages in the Alignak dedicated repositories.

To proceed with installation, you must register the alignak repositories on your system.

Create the file */etc/yum.repos.d/alignak-stable.repo* with the following content::

   [Alignak-rpm-stable]
   name=Alignak RPM stable packages
   baseurl=https://dl.bintray.com/alignak/alignak-rpm-stable
   gpgcheck=0
   repo_gpgcheck=0
   enabled=1

And then update the repositories list::

   sudo yum repolist


If you wish to use the non-stable versions (eg. current develop or any other specific branch), you can also create a repository source for the test versions. Then create a file */etc/yum.repos.d/alignak-testing.repo* with the following content::

   [Alignak-rpm-testing]
   name=Alignak RPM testing packages
   baseurl=https://dl.bintray.com/alignak/alignak-rpm-testing
   gpgcheck=0
   repo_gpgcheck=0
   enabled=1

The Alignak packages repositories contain several version of the application. The versioning scheme is the same as the Alignak one.



Once the download sources are set, you can simply use the standard package tool to have more information about Alignak packages and available versions.
 ::

   yum search alignak
   # Note that it exists some Alignak packages in the EPEL repository but it is an old version. Contact us for more information...
      Loaded plugins: fastestmirror
      Loading mirror speeds from cached hostfile
       * base: mirrors.atosworldline.com
       * epel: mirror.speedpartner.de
       * extras: mirrors.atosworldline.com
       * updates: mirrors.standaloneinstaller.com
      =========================================================================== N/S matched: alignak ===========================================================================
      alignak.noarch : Alignak, modern Nagios compatible monitoring framework
      alignak-all.noarch : Meta-package to pull in all alignak
      alignak-arbiter.noarch : Alignak Arbiter
      alignak-broker.noarch : Alignak Broker
      alignak-common.noarch : Alignak Common
      alignak-poller.noarch : Alignak Poller
      alignak-reactionner.noarch : Alignak Reactionner
      alignak-receiver.noarch : Alignak Poller
      alignak-scheduler.noarch : Alignak Scheduler

        Name and summary matches only, use "search all" for everything.

   yum info alignak
      Loaded plugins: fastestmirror
      Loading mirror speeds from cached hostfile
       * base: mirrors.atosworldline.com
       * epel: mirror.speedpartner.de
       * extras: mirrors.atosworldline.com
       * updates: mirrors.standaloneinstaller.com
      Available Packages
      Name        : alignak
      Arch        : noarch
      Version     : 1.1.0rc5_test
      Release     : 1
      Size        : 816 k
      Repo        : alignak-testing
      Summary     : Alignak, modern Nagios compatible monitoring framework
      URL         : http://alignak.net
      License     : AGPL
      Description : Alignak, modern Nagios compatible monitoring framework


Or you can simply use the standard package tool to install Alignak and its dependencies.
 ::

   sudo yum install alignak

   # Check Alignak installation
   # It copied the default shipped files and sample configuration.
   ll /usr/local/share/alignak/
      total 8
      drwxr-xr-x. 5 root root   49 May 24 17:52 bin
      drwxr-xr-x. 6 root root  144 May 24 17:52 etc
      -rwxrwxr-x. 1 root root 2179 Jun 22  2018 post-install.sh
      -rw-rw-r--. 1 root root 1889 Jun 22  2018 requirements.txt

Contrary to the debian installer, no post-installation script is started nor system services are installed. You must then::

   sudo /usr/local/share/alignak/post-install.sh

This will install the Alignak required Python packages. This script is copied during the installation in the default installation directory: */usr/local/share/alignak*. It is using the Python pip tool to get the Python packages listed in the default installation directory *requirements.txt* file.

.. note:: as stated :ref:`formerly in this document <Installation/requirements>`, this hack is necessary to be sure that we use the expected versions of the needed Python libraries...

To terminate the installation of the system services you must::

   sudo cp /usr/local/share/alignak/bin/systemd/alignak* /lib/systemd/system

   ll /lib/systemd/system
      -rw-r--r--. 1 root root  777 May 24 17:48 /lib/systemd/system/alignak-arbiter@.service
      -rw-r--r--. 1 root root  770 May 24 17:48 /lib/systemd/system/alignak-broker@.service
      -rw-r--r--. 1 root root  770 May 24 17:48 /lib/systemd/system/alignak-poller@.service
      -rw-r--r--. 1 root root  805 May 24 17:48 /lib/systemd/system/alignak-reactionner@.service
      -rw-r--r--. 1 root root  784 May 24 17:48 /lib/systemd/system/alignak-receiver@.service
      -rw-r--r--. 1 root root  791 May 24 17:48 /lib/systemd/system/alignak-scheduler@.service
      -rw-r--r--. 1 root root 1286 May 24 17:48 /lib/systemd/system/alignak.service

   sudo systemctl enable alignak
      Created symlink from /etc/systemd/system/multi-user.target.wants/alignak.service to /usr/lib/systemd/system/alignak.service.

.. note:: more information about the default shipped configuration is available :ref: `on this page <configuration/default_configuration>`.


Once you achieved this tricky part, running Alignak daemons is easy. All you need is to inform the Alignak daemons where they will find the configuration to use and start the `alignak` system service. All this is explained :ref:`in this chapter <run_alignak/services_systemd>`.


Install on FreeBSD Unix
-----------------------

There is no package available currentmy for FreeBSD. You can install with pip as explained hereunder.

Install with pip
----------------

.. note:: the recommended way for installing on a production server is mostly often to use the packages existing for your distribution. Thanks to recent ``pip`` integration and to the strong *requirements.txt* shipped with the Alignak backend, installing with pip is a reliable installation mode.

The pip installation provides:

   - a startup script using an uwsgi server,
   - for FreeBSD users, an rc.d sample script
   - for systemd based systems (Debian, CentOS), an alignak-backend service unit example.

All this stuff is available in the */usr/local/share/alignak-backend* directory::

Installation with ``pip``::

   $ sudo pip install alignak-backend
      ...
      ...
      Successfully installed Eve-0.7.9 Eve-Swagger-0.0.11 alignak-backend-1.4.11.2 apscheduler-3.5.1 cerberus-0.9.2 certifi-2018.4.16 chardet-3.0.4 click-6.7 configparser-3.5.0 docopt-0.6.2 dominate-2.3.1 events-0.2.2 flask-1.0.2 flask-apscheduler-1.8.0 flask-bootstrap-3.3.7.1 flask-pymongo-0.5.2 future-0.16.0 idna-2.7 influxdb-5.1.0 itsdangerous-0.24 jsmin-2.2.2 jsonschema-2.6.0 pymongo-3.7.0 python-dateutil-2.7.3 pytz-2018.5 requests-2.19.1 simplejson-3.16.0 statsd-3.2.2 tzlocal-1.5.1 urllib3-1.23 visitor-0.1.3 werkzeug-0.11.15

   # Set-up user account and directories
   $ sudo /usr/local/share/alignak-backend/post-install.sh
      -----
      Alignak-backend post-install
      -----
      ...
      ...
      Creating some necessary directories
      alignak user and members of its group alignak are granted 775 on /usr/local/var/run/alignak-backend
      alignak user and members of its group alignak are granted 775 on /usr/local/var/log/alignak-backend
      Add your own user account as a member of alignak group to run daemons from your shell!
      Created.

Configure Linux systemd services
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
::

   # Set-up system services
   $ sudo cp /usr/local/share/alignak-backend/bin/systemd/alignak-backend.service /lib/systemd/system
   # Note that if you are using default Python 2 as default interpreter, you must edit the service file
   # and replace `--plugin python3` with `--plugin python`!

   $ sudo systemctl enable alignak-backend
   Created symlink from /etc/systemd/system/multi-user.target.wants/alignak-backend.service to /lib/systemd/system/alignak-backend.service.

   $ sudo systemctl status alignak-backend
   ● alignak-backend.service - uWSGI instance to serve Alignak backend
      Loaded: loaded (/lib/systemd/system/alignak-backend.service; enabled; vendor preset: enabled)
      Active: inactive (dead)

   $ sudo systemctl start alignak-backend

Configure freeBSD system service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
::

    # Enable the system service
    echo 'alignak_backend_enable="YES"' >> /etc/rc.conf
    # Declare the configuration file
    echo 'alignak_backend_config="/root/git/DCS_IPM/config/alignak-backend/settings.json"' >> /etc/rc.conf
    # Enable uwsgi log
    echo 'alignak_backend_log="YES"' >> /etc/rc.conf
    # Define network interface
    echo 'alignak_backend_host="0.0.0.0"' >> /etc/rc.conf
    echo 'alignak_backend_port="5000"' >> /etc/rc.conf
    # # # Send uWsgi metrics to Graphite
    echo 'alignak_backend_metrics="YES"' >> /etc/rc.conf
    echo 'alignak_backend_carbon="127.0.0.1:2003 --carbon-root uwsgi -s /tmp/uwsgi.sock"' >> /etc/rc.conf


    # Check all the available configuration variables in the /usr/local/etc/rc.d/alignak-backend file!


    # Alignak-backend
    service alignak-backend status
    service alignak-backend stop
    service alignak-backend start


From source
~~~~~~~~~~~

You can install it from source::

    git clone https://github.com/Alignak-monitoring-contrib/alignak-backend
    cd alignak-backend
    sudo pip install .

You can then apply the same procedures as when instalilng with pip to prepare your system.

For contributors
~~~~~~~~~~~~~~~~

If you want to hack into the codebase (e.g for future contribution), just install like this::

    git clone https://github.com/Alignak-monitoring-contrib/alignak-backend
    cd alignak-backend
    # Install with pip in develop mode
    pip install -e .
