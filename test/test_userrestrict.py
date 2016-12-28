#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This test check the userrestrict (uipref)
"""

import os
import json
import time
import shlex
import subprocess
import requests
import unittest2


class TestUserrestrict(unittest2.TestCase):
    """
    This class test the userrestrict (uipref)
    """

    @classmethod
    def setUpClass(cls):
        """
        This method:
          * delete mongodb database
          * start the backend with uwsgi
          * log in the backend and get the token
          * get the realm

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
        # get user admin
        response = requests.get(cls.endpoint + '/user',
                                auth=cls.auth)
        resp = response.json()
        cls.user_admin = resp['_items'][0]

        # get realms
        response = requests.get(cls.endpoint + '/realm',
                                auth=cls.auth)
        resp = response.json()
        cls.realmAll_id = resp['_items'][0]['_id']

        # Add users
        data = {'name': 'user1', 'password': 'test', 'back_role_super_admin': True,
                'host_notification_period': cls.user_admin['host_notification_period'],
                'service_notification_period': cls.user_admin['service_notification_period'],
                '_realm': cls.realmAll_id}
        response = requests.post(cls.endpoint + '/user', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.user1_id = resp['_id']

        headers = {'Content-Type': 'application/json'}
        params = {'username': 'user1', 'password': 'test', 'action': 'generate'}
        # get token
        response = requests.post(cls.endpoint + '/login', json=params, headers=headers)
        resp = response.json()
        cls.token_user1 = resp['token']
        cls.auth_user1 = requests.auth.HTTPBasicAuth(cls.token_user1, '')

    @classmethod
    def tearDownClass(cls):
        """
        Kill uwsgi

        :return: None
        """
        subprocess.call(['uwsgi', '--stop', '/tmp/uwsgi.pid'])
        time.sleep(2)

    def test_not_userrestrict_command(self):
        """
        Test not have userrestrict on commands

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}
        # Add command
        data = json.loads(open('cfg/command_ping.json').read())
        data['_users_read'] = [self.user1_id]
        data['_realm'] = self.realmAll_id
        data['_sub_realm'] = True
        data['name'] = 'ping1'
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)
        # Check if command right in backend
        response = requests.get(self.endpoint + '/command', params=sort_id, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 3)
        self.assertEqual(resp['_items'][2]['name'], "ping1")

        response = requests.get(self.endpoint + '/command', params=sort_id, auth=self.auth_user1)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 3)
        self.assertEqual(resp['_items'][2]['name'], "ping1")
