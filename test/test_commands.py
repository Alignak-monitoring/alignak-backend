#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This test check the commands
"""

from __future__ import print_function
import os
import time
import shlex
import subprocess
import copy
import requests
import unittest2


class TestGroups(unittest2.TestCase):
    """
    This class test hostgroups and tree feature
    """

    @classmethod
    def setUpClass(cls):
        """
        This method:
          * deletes mongodb database
          * starts the backend with uwsgi
          * logs in the backend and get the token
          * gets the hostgroup

        :return: None
        """
        # Set test mode for Alignak backend
        os.environ['TEST_ALIGNAK_BACKEND'] = '1'
        os.environ['ALIGNAK_BACKEND_MONGO_DBNAME'] = 'alignak-backend-test'

        # Delete used mongo DBs
        exit_code = subprocess.call(
            shlex.split(
                'mongo %s --eval "db.dropDatabase()"' % os.environ['ALIGNAK_BACKEND_MONGO_DBNAME'])
        )
        assert exit_code == 0

        cls.p = subprocess.Popen(['uwsgi', '--plugin', 'python', '-w', 'alignakbackend:app',
                                  '--socket', '0.0.0.0:5000',
                                  '--protocol=http', '--enable-threads', '--pidfile',
                                  '/tmp/uwsgi.pid'])
        time.sleep(3)

        cls.endpoint = 'http://127.0.0.1:5000'

        headers = {'Content-Type': 'application/json'}
        params = {'username': 'admin', 'password': 'admin', 'action': 'generate'}
        # get token
        response = requests.post(cls.endpoint + '/login', json=params, headers=headers)
        resp = response.json()
        cls.token = resp['token']
        cls.auth = requests.auth.HTTPBasicAuth(cls.token, '')

    @classmethod
    def tearDownClass(cls):
        """
        Kill uwsgi

        :return: None
        """
        subprocess.call(['uwsgi', '--stop', '/tmp/uwsgi.pid'])
        time.sleep(2)

    @classmethod
    def tearDown(cls):
        """
        Delete resources in backend

        :return: None
        """
        for resource in ['host', 'service', 'command', 'livestate', 'livesynthesis']:
            requests.delete(cls.endpoint + '/' + resource, auth=cls.auth)

    def test_default_commands(self):
        """
        Default commands exist ..
        :return:
        """

        # get commands
        response = requests.get(self.endpoint + '/command', auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 2)
        for item in resp['_items']:
            self.assertIn(item['name'], ['_echo', '_internal_host_up'])
