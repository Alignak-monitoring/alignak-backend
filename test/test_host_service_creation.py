#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This test verify the usage of hosts and services templates
"""

import os
import json
import time
import shlex
import subprocess
import requests
import unittest2
from alignak_backend.models.host import get_schema as host_schema
from alignak_backend.models.user import get_schema as user_schema


class TestHookTemplate(unittest2.TestCase):
    """
    This class test the hooks used for hosts and services templates
    """

    maxDiff = None

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

        cls.p = subprocess.Popen(['uwsgi', '--plugin', 'python', '-w', 'alignak_backend.app:app',
                                  '--socket', '0.0.0.0:5000',
                                  '--protocol=http', '--enable-threads', '--pidfile',
                                  '/tmp/uwsgi.pid'])
        time.sleep(3)

        cls.endpoint = 'http://127.0.0.1:5000'

        # Login as admin
        headers = {'Content-Type': 'application/json'}
        params = {'username': 'admin', 'password': 'admin', 'action': 'generate'}
        response = requests.post(cls.endpoint + '/login', json=params, headers=headers)
        resp = response.json()
        cls.token = resp['token']
        cls.auth = requests.auth.HTTPBasicAuth(cls.token, '')

        # Get user admin
        response = requests.get(cls.endpoint + '/user', auth=cls.auth)
        resp = response.json()
        cls.user_admin = resp['_items'][0]

        # Get default realm
        response = requests.get(cls.endpoint + '/realm', auth=cls.auth,
                                params={'where': json.dumps({'name': 'All'})})
        resp = response.json()
        cls.realm_all = resp['_items'][0]['_id']

        # Create a sub-realm
        data = {"name": "All A", "_parent": cls.realm_all}
        response = requests.post(cls.endpoint + '/realm', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.sub_realm = resp['_id']

        # Add a user in the new sub-realm
        data = {'name': 'user1', 'password': 'test', '_realm': cls.sub_realm,
                'host_notification_period': cls.user_admin['host_notification_period'],
                'service_notification_period': cls.user_admin['service_notification_period']}
        response = requests.post(cls.endpoint + '/user', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.user1_id = resp['_id']

        # Get the user rights
        params = {'where': json.dumps({'user': cls.user1_id})}
        response = requests.get(cls.endpoint + '/userrestrictrole', params=params, auth=cls.auth)
        resp = response.json()
        assert len(resp['_items']) == 1
        assert resp['_items'][0]['crud'] == ['read']

        # Set user rights (update...)
        headers = {'Content-Type': 'application/json', 'If-Match': resp['_items'][0]['_etag']}
        data = {'resource': '*', 'crud': ['read', 'create']}
        response = requests.patch(cls.endpoint + '/userrestrictrole/' + resp['_items'][0]['_id'],
                                  json=data, headers=headers, auth=cls.auth)
        assert response.status_code == 200

        # Get the user rights to confirm update
        params = {'where': json.dumps({'user': cls.user1_id})}
        response = requests.get(cls.endpoint + '/userrestrictrole', params=params, auth=cls.auth)
        resp = response.json()
        assert len(resp['_items']) == 1
        assert resp['_items'][0]['crud'] == ['read', 'create']

        params = {'username': 'user1', 'password': 'test', 'action': 'generate'}
        response = requests.post(cls.endpoint + '/login', json=params, headers=headers)
        resp = response.json()
        cls.token1 = resp['token']
        cls.auth1 = requests.auth.HTTPBasicAuth(cls.token1, '')

        # Get default host
        response = requests.get(cls.endpoint + '/host', auth=cls.auth,
                                params={'where': json.dumps({'name': '_dummy'})})
        resp = response.json()
        cls.default_host = resp['_items'][0]['_id']

        # Get default host check_command
        response = requests.get(cls.endpoint + '/command', auth=cls.auth,
                                params={'where': json.dumps({'name': '_internal_host_up'})})
        resp = response.json()
        cls.default_host_check_command = resp['_items'][0]['_id']

        # Get default service check_command
        response = requests.get(cls.endpoint + '/command', auth=cls.auth,
                                params={'where': json.dumps({'name': '_echo'})})
        resp = response.json()
        cls.default_service_check_command = resp['_items'][0]['_id']

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
        Delete resources after each test

        :return: None
        """
        for resource in ['host', 'service', 'command', 'livesynthesis']:
            response = requests.delete(cls.endpoint + '/' + resource, auth=cls.auth)
            assert response.status_code == 204

    def test_host_default_check_command(self):
        """Create a new host with default check command and realm

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        # Create an host without template
        data = {'name': 'host_1'}
        resp = requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        resp = resp.json()
        assert '_id' in resp
        assert '_created' in resp
        assert '_updated' in resp
        # host was created with only a name information...

        # Get the newly created host
        response = requests.get(self.endpoint + '/host/' + resp['_id'], auth=self.auth)
        host = response.json()
        self.assertEqual(host['name'], "host_1")
        self.assertEqual(host['_realm'], self.realm_all)
        self.assertEqual(host['check_command'], self.default_host_check_command)

        # Add a check command
        data = json.loads(open('cfg/command_ping.json').read())
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)

        # Check command exists in the backend
        response = requests.get(self.endpoint + '/command', auth=self.auth,
                                params={'where': json.dumps({'name': 'ping'})})
        resp = response.json()
        cmd = resp['_items'][0]
        self.assertEqual(cmd['name'], "ping")

        # Create an host template
        data = {
            'name': 'tpl_1',
            'check_command': cmd['_id'],
            '_is_template': True
        }
        resp = requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        resp = resp.json()
        assert '_id' in resp
        assert '_created' in resp
        assert '_updated' in resp

        # Get the newly created host
        response = requests.get(self.endpoint + '/host/' + resp['_id'], auth=self.auth)
        tpl = response.json()
        self.assertEqual(tpl['name'], "tpl_1")
        self.assertEqual(tpl['_realm'], self.realm_all)
        self.assertEqual(tpl['check_command'], cmd['_id'])

        # Create an host inheriting from the new template
        data = {
            'name': 'host_2',
            '_templates': [tpl['_id']]
        }
        resp = requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        resp = resp.json()
        assert '_id' in resp
        assert '_created' in resp
        assert '_updated' in resp

        # Get the newly created host
        response = requests.get(self.endpoint + '/host/' + resp['_id'], auth=self.auth)
        host = response.json()
        self.assertEqual(host['name'], "host_2")
        self.assertEqual(host['_realm'], self.realm_all)
        self.assertEqual(host['_templates'], [tpl['_id']])
        self.assertEqual(host['check_command'], cmd['_id'])

    def test_host_default_check_command_non_admin(self):
        """Create a new host with default check command and realm as a non-admin user

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        # Create an host without template
        data = {'name': 'host_3'}
        resp = requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth1)
        resp = resp.json()
        assert '_id' in resp
        assert '_created' in resp
        assert '_updated' in resp
        # host was created with only a name information...

        # Get the newly created host
        response = requests.get(self.endpoint + '/host/' + resp['_id'], auth=self.auth1)
        host = response.json()
        self.assertEqual(host['name'], "host_3")
        self.assertEqual(host['_realm'], self.sub_realm)
        self.assertEqual(host['check_command'], self.default_host_check_command)

    def test_service_default_check_command(self):
        """Create a new service with default check command and realm

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        # create a host
        data = {
            'name': 'host_1',
            '_templates': [self.default_host]
        }
        response = requests.post(self.endpoint + '/host', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        host1_id = resp['_id']

        # Create a service without template
        data = {
            'host': host1_id,
            'name': 'service_3'
        }
        resp = requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)
        resp = resp.json()
        assert '_id' in resp
        assert '_created' in resp
        assert '_updated' in resp
        # service was created with only an host and a name information...

        # Get the newly created service
        response = requests.get(self.endpoint + '/service/' + resp['_id'], auth=self.auth)
        service = response.json()
        self.assertEqual(service['name'], "service_3")
        self.assertEqual(service['_realm'], self.realm_all)
        self.assertEqual(service['check_command'], self.default_service_check_command)

        # Add a check command
        data = json.loads(open('cfg/command_ping.json').read())
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)

        # Check command exists in the backend
        response = requests.get(self.endpoint + '/command', auth=self.auth,
                                params={'where': json.dumps({'name': 'ping'})})
        resp = response.json()
        cmd = resp['_items'][0]
        self.assertEqual(cmd['name'], "ping")

        # Create an host template
        data = {
            'name': 'tpl_2',
            'check_command': cmd['_id'],
            '_is_template': True
        }
        resp = requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        resp = resp.json()
        assert '_id' in resp
        assert '_created' in resp
        assert '_updated' in resp
        host_tpl_id = resp['_id']

        # Create a service template
        data = {
            'host': host_tpl_id,
            'name': 'tpl_svc_1',
            'check_command': cmd['_id'],
            '_is_template': True
        }
        resp = requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)
        resp = resp.json()
        assert '_id' in resp
        assert '_created' in resp
        assert '_updated' in resp

        # Get the newly created service template
        response = requests.get(self.endpoint + '/service/' + resp['_id'], auth=self.auth)
        tpl = response.json()
        self.assertEqual(tpl['name'], "tpl_svc_1")
        self.assertEqual(tpl['check_command'], cmd['_id'])
        self.assertEqual(tpl['host'], host_tpl_id)

        # Create a service inheriting from the new template
        data = {
            'host': host1_id,
            'name': 'service_2',
            '_templates': [tpl['_id']]
        }
        resp = requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)
        resp = resp.json()
        assert '_id' in resp
        assert '_created' in resp
        assert '_updated' in resp

        # Get the newly created service
        response = requests.get(self.endpoint + '/service/' + resp['_id'], auth=self.auth)
        service = response.json()
        self.assertEqual(service['name'], "service_2")
        self.assertEqual(service['_templates'], [tpl['_id']])
        self.assertEqual(service['check_command'], cmd['_id'])

    def test_service_default_check_command_non_admin(self):
        """Create a new service with default check command and realm

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        # Create an host without template
        data = {'name': 'host_3'}
        resp = requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth1)
        resp = resp.json()
        assert '_id' in resp
        assert '_created' in resp
        assert '_updated' in resp

        # Create a service without template
        data = {
            'host': resp['_id'],
            'name': 'service_2'
        }
        resp = requests.post(self.endpoint + '/service', json=data, headers=headers,
                             auth=self.auth1)
        resp = resp.json()
        assert '_id' in resp
        assert '_created' in resp
        assert '_updated' in resp
        # service was created with only an host and a name information...

        # Get the newly created service
        response = requests.get(self.endpoint + '/service/' + resp['_id'], auth=self.auth1)
        service = response.json()
        self.assertEqual(service['name'], "service_2")
        self.assertEqual(service['_realm'], self.sub_realm)
        self.assertEqual(service['check_command'], self.default_service_check_command)
