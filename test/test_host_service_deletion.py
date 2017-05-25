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


class TestHostServiceDeletion(unittest2.TestCase):
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
        for resource in ['host', 'service']:
            requests.delete(cls.endpoint + '/' + resource, auth=cls.auth)

    def test_host_create_delete(self):
        """Create a new host with default check command and realm.

        Then deletes this host to confirm it is deleted

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
        # host was created with only a name information... and not marked as deleted ;)

        # Get the newly created host
        response = requests.get(self.endpoint + '/host/' + resp['_id'], auth=self.auth)
        self.assertEqual(response.status_code, 200)
        host = response.json()
        self.assertEqual(host['name'], "host_1")
        self.assertEqual(host['_realm'], self.realm_all)
        self.assertEqual(host['check_command'], self.default_host_check_command)

        # Delete the host
        headers_delete = {
            'Content-Type': 'application/json',
            'If-Match': host['_etag']
        }
        response = requests.delete(self.endpoint + '/host/' + host['_id'],
                                   headers=headers_delete, auth=self.auth)
        self.assertEqual(response.status_code, 204)

        # Get the newly created host - that is now deleted!
        response = requests.get(self.endpoint + '/host/' + resp['_id'], auth=self.auth)
        # Returns 404 not found !
        self.assertEqual(response.status_code, 404)

    def test_templated_host_create_delete(self):
        """Create a new host from a template

        Then deletes this host to confirm it is deleted

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        # Create an host template
        data = {
            'name': 'tpl_1',
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

        # Delete the host
        headers_delete = {
            'Content-Type': 'application/json',
            'If-Match': host['_etag']
        }
        response = requests.delete(self.endpoint + '/host/' + host['_id'],
                                   headers=headers_delete, auth=self.auth)
        self.assertEqual(response.status_code, 204)

        # Get the newly created host - that is now deleted!
        response = requests.get(self.endpoint + '/host/' + resp['_id'], auth=self.auth)
        # Returns 404 not found !
        self.assertEqual(response.status_code, 404)

    def test_service_create_delete(self):
        """Create a new service with default check command and realm

        Then delete the service and confirm it is deleted

        :return: None
        """
        headers = {'Content-Type': 'application/json'}

        # create the host
        data = {'name': 'host_1'}
        resp = requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        resp = resp.json()
        assert '_id' in resp
        assert '_created' in resp
        assert '_updated' in resp

        # Create a service without template
        data = {
            'host': resp['_id'],
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
        self.assertEqual(response.status_code, 200)
        service = response.json()
        self.assertEqual(service['name'], "service_3")
        self.assertEqual(service['_realm'], self.realm_all)
        self.assertEqual(service['check_command'], self.default_service_check_command)

        # Delete the service
        headers_delete = {
            'Content-Type': 'application/json',
            'If-Match': service['_etag']
        }
        response = requests.delete(self.endpoint + '/service/' + service['_id'],
                                   headers=headers_delete, auth=self.auth)
        self.assertEqual(response.status_code, 204)

        # Get the newly created service - that is now deleted!
        response = requests.get(self.endpoint + '/service/' + resp['_id'], auth=self.auth)
        # Returns 404 not found !
        self.assertEqual(response.status_code, 404)

    def test_host_service_create_delete(self):
        """Create a new host with default check command and realm.

        Create a new service with default check command and realm attached to this host

        Then deletes the host to confirm it is deleted and its service is also deleted

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
        # host was created with only a name information... and not marked as deleted ;)

        # Get the newly created host
        response = requests.get(self.endpoint + '/host/' + resp['_id'], auth=self.auth)
        self.assertEqual(response.status_code, 200)
        host = response.json()
        self.assertEqual(host['name'], "host_1")
        self.assertEqual(host['_realm'], self.realm_all)
        self.assertEqual(host['check_command'], self.default_host_check_command)

        # Create a service without template
        data = {
            'host': host['_id'],
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
        self.assertEqual(response.status_code, 200)
        service = response.json()
        self.assertEqual(service['name'], "service_3")
        self.assertEqual(service['_realm'], self.realm_all)
        self.assertEqual(service['check_command'], self.default_service_check_command)
        self.assertEqual(service['host'], host['_id'])

        # Get the host
        response = requests.get(self.endpoint + '/host/' + host['_id'], auth=self.auth)
        self.assertEqual(response.status_code, 200)
        host = response.json()

        # Delete the host
        headers_delete = {
            'Content-Type': 'application/json',
            'If-Match': host['_etag']
        }
        response = requests.delete(self.endpoint + '/host/' + host['_id'],
                                   headers=headers_delete, auth=self.auth)
        self.assertEqual(response.status_code, 204)

        # Get the newly created host - that is now deleted!
        response = requests.get(self.endpoint + '/host/' + resp['_id'], auth=self.auth)
        # Returns 404 not found !
        self.assertEqual(response.status_code, 404)

        # Get the recently created service - that is now deleted!
        response = requests.get(self.endpoint + '/service/' + resp['_id'], auth=self.auth)
        # Returns 404 not found !
        self.assertEqual(response.status_code, 404)
