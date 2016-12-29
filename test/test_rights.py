#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This test check if rights of users in backend works
"""

import os
import json
import time
import shlex
import subprocess
import requests
import unittest2


class TestRights(unittest2.TestCase):
    """
    This class test the rights in backend
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

        # Add realm
        data = {'name': 'Hoth', "_parent": cls.realmAll_id}
        response = requests.post(cls.endpoint + '/realm', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.hoth = resp['_id']

        data = {'name': 'Sluis', "_parent": cls.realmAll_id}
        response = requests.post(cls.endpoint + '/realm', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.sluis = resp['_id']

        data = {'name': 'Dagobah', "_parent": cls.sluis}
        response = requests.post(cls.endpoint + '/realm', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.dagobah = resp['_id']

        # Add users
        # User 1
        data = {'name': 'user1', 'password': 'test', 'back_role_super_admin': False,
                'host_notification_period': cls.user_admin['host_notification_period'],
                'service_notification_period': cls.user_admin['service_notification_period'],
                '_realm': cls.realmAll_id}
        response = requests.post(cls.endpoint + '/user', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.user1_id = resp['_id']
        data = {'user': resp['_id'], 'realm': cls.sluis, 'resource': 'command', 'crud': ['read'],
                'sub_realm': True}
        requests.post(cls.endpoint + '/userrestrictrole', json=data, headers=headers,
                      auth=cls.auth)

        # User 2
        data = {'name': 'user2', 'password': 'test', 'back_role_super_admin': False,
                'host_notification_period': cls.user_admin['host_notification_period'],
                'service_notification_period': cls.user_admin['service_notification_period'],
                '_realm': cls.realmAll_id}
        response = requests.post(cls.endpoint + '/user', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.user2_id = resp['_id']
        data = {'user': resp['_id'], 'realm': cls.hoth, 'resource': 'command', 'crud': ['read']}
        requests.post(cls.endpoint + '/userrestrictrole', json=data, headers=headers,
                      auth=cls.auth)

        # User 3
        data = {'name': 'user3', 'password': 'test', 'back_role_super_admin': False,
                'host_notification_period': cls.user_admin['host_notification_period'],
                'service_notification_period': cls.user_admin['service_notification_period'],
                '_realm': cls.realmAll_id}
        response = requests.post(cls.endpoint + '/user', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.user3_id = resp['_id']

        # User 4
        data = {'name': 'user4', 'password': 'test', 'back_role_super_admin': False,
                'host_notification_period': cls.user_admin['host_notification_period'],
                'service_notification_period': cls.user_admin['service_notification_period'],
                '_realm': cls.realmAll_id}
        response = requests.post(cls.endpoint + '/user', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.user4_id = resp['_id']
        data = {'user': resp['_id'], 'realm': cls.sluis, 'resource': 'command',
                'crud': ['custom']}
        requests.post(cls.endpoint + '/userrestrictrole', json=data, headers=headers,
                      auth=cls.auth)

        # User 5
        data = {'name': 'user5', 'password': 'test', 'back_role_super_admin': False,
                'host_notification_period': cls.user_admin['host_notification_period'],
                'service_notification_period': cls.user_admin['service_notification_period'],
                '_realm': cls.realmAll_id}
        response = requests.post(cls.endpoint + '/user', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.user5_id = resp['_id']
        data = {'user': resp['_id'], 'realm': cls.sluis, 'resource': '*', 'crud': ['read']}
        requests.post(cls.endpoint + '/userrestrictrole', json=data, headers=headers,
                      auth=cls.auth)

        # User 6
        data = {'name': 'user6', 'password': 'test', 'back_role_super_admin': False,
                'host_notification_period': cls.user_admin['host_notification_period'],
                'service_notification_period': cls.user_admin['service_notification_period'],
                '_realm': cls.realmAll_id}
        response = requests.post(cls.endpoint + '/user', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.user6_id = resp['_id']
        data = {'user': resp['_id'], 'realm': cls.sluis, 'resource': '*', 'crud': ['read'],
                'sub_realm': True}
        requests.post(cls.endpoint + '/userrestrictrole', json=data, headers=headers,
                      auth=cls.auth)

    @classmethod
    def tearDownClass(cls):
        """
        Kill uwsgi

        :return: None
        """
        subprocess.call(['uwsgi', '--stop', '/tmp/uwsgi.pid'])
        time.sleep(2)

    def test_roles(self):
        """
        Test roles to different users to see if they get the right commands

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
        data['_users_read'] = [self.user4_id]
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)
        # Check if command right in backend
        response = requests.get(self.endpoint + '/command', params=sort_id, auth=self.auth)
        resp = response.json()
        self.assertEqual(resp['_items'][2]['name'], "ping1")

        data['_sub_realm'] = False
        data['name'] = 'ping2'
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)

        data['_realm'] = self.sluis
        data['_sub_realm'] = False
        data['name'] = 'ping3'
        data['_users_read'] = [self.user4_id]
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)

        data['_realm'] = self.dagobah
        data['_sub_realm'] = False
        data['name'] = 'ping4'
        data['_users_read'] = [self.user4_id]
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)

        data['_realm'] = self.hoth
        data['_sub_realm'] = False
        data['name'] = 'ping5'
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)

        params = {'username': 'user1', 'password': 'test', 'action': 'generate'}
        # get token user 1
        response = requests.post(self.endpoint + '/login', json=params, headers=headers)
        resp = response.json()
        user1_auth = requests.auth.HTTPBasicAuth(resp['token'], '')

        params = {'username': 'user2', 'password': 'test', 'action': 'generate'}
        # get token user 2
        response = requests.post(self.endpoint + '/login', json=params, headers=headers)
        resp = response.json()
        user2_auth = requests.auth.HTTPBasicAuth(resp['token'], '')

        params = {'username': 'user3', 'password': 'test', 'action': 'generate'}
        # get token user 3
        response = requests.post(self.endpoint + '/login', json=params, headers=headers)
        resp = response.json()
        user3_auth = requests.auth.HTTPBasicAuth(resp['token'], '')

        params = {'username': 'user4', 'password': 'test', 'action': 'generate'}
        # get token user 4
        response = requests.post(self.endpoint + '/login', json=params, headers=headers)
        resp = response.json()
        user4_auth = requests.auth.HTTPBasicAuth(resp['token'], '')

        params = {'username': 'user5', 'password': 'test', 'action': 'generate'}
        # get token user 5
        response = requests.post(self.endpoint + '/login', json=params, headers=headers)
        resp = response.json()
        user5_auth = requests.auth.HTTPBasicAuth(resp['token'], '')

        params = {'username': 'user6', 'password': 'test', 'action': 'generate'}
        # get token user 5
        response = requests.post(self.endpoint + '/login', json=params, headers=headers)
        resp = response.json()
        user6_auth = requests.auth.HTTPBasicAuth(resp['token'], '')

        response = requests.get(self.endpoint + '/command', params={'sort': "name"},
                                auth=user1_auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 5)
        self.assertEqual(resp['_meta']['total'], 5)

        response = requests.get(self.endpoint + '/command', params={'sort': "name"},
                                auth=user2_auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 4)
        self.assertEqual(resp['_meta']['total'], 4)

        response = requests.get(self.endpoint + '/command', params={'sort': "name"},
                                auth=user3_auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 0)
        self.assertEqual(resp['_meta']['total'], 0)

        response = requests.get(self.endpoint + '/command', params={'sort': "name"},
                                auth=user4_auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 1)
        self.assertEqual(resp['_meta']['total'], 1)

        response = requests.get(self.endpoint + '/command', params={'sort': "name"},
                                auth=user5_auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 4)
        self.assertEqual(resp['_meta']['total'], 4)

        # Check user5 with realms
        response = requests.get(self.endpoint + '/realm', params={'sort': "name"},
                                auth=user5_auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 1)
        self.assertEqual(resp['_meta']['total'], 1)
        self.assertEqual('Sluis', resp['_items'][0]['name'])

        # Check user6 with realms, must have 2 realms : Sluis and Dagobah
        response = requests.get(self.endpoint + '/realm', params={'sort': "name"},
                                auth=user6_auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 2)
        self.assertEqual(resp['_meta']['total'], 2)
        self.assertEqual('Dagobah', resp['_items'][0]['name'])
        self.assertEqual('Sluis', resp['_items'][1]['name'])
