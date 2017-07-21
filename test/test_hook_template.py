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
        os.environ['ALIGNAK_BACKEND_MONGO_DBNAME'] = 'alignak-backend-templates-test'

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

        headers = {'Content-Type': 'application/json'}
        params = {'username': 'admin', 'password': 'admin', 'action': 'generate'}
        # get token
        response = requests.post(cls.endpoint + '/login', json=params, headers=headers)
        resp = response.json()
        cls.token = resp['token']
        cls.auth = requests.auth.HTTPBasicAuth(cls.token, '')

        # get realms
        response = requests.get(cls.endpoint + '/realm',
                                auth=cls.auth)
        resp = response.json()
        cls.realm_all = resp['_items'][0]['_id']

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
        for resource in ['host', 'service', 'command', 'livestate', 'livesynthesis', 'user']:
            requests.delete(cls.endpoint + '/' + resource, auth=cls.auth)

    def test_host_templates(self):
        """Test host templates

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}
        # Add command
        data = json.loads(open('cfg/command_ping.json').read())
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)
        # Check if command right in backend
        response = requests.get(self.endpoint + '/command', params=sort_id, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 3)
        rc = resp['_items']
        self.assertEqual(rc[2]['name'], "ping")

        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[2]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = self.realm_all
        data['_is_template'] = True
        data['ls_state'] = 'UP'
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        # Check if host right in backend
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(len(resp['_items']), 2)
        self.assertEqual(rh[1]['name'], "srv001")
        host_template_id = rh[1]['_id']
        data = {
            'name': 'host_001',
            '_templates': [host_template_id],
            '_realm': self.realm_all
        }
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[1]['name'], "srv001")
        self.assertEqual(rh[2]['name'], "host_001")
        self.assertEqual(rh[2]['check_command'], rc[2]['_id'])

        schema = host_schema()
        template_fields = {}
        ignore_fields = ['name', 'realm', '_realm', '_overall_state_id',
                         '_template_fields', '_templates', '_is_template',
                         '_templates_with_services']
        for key in schema['schema']:
            if key not in ignore_fields and not key.startswith('ls_'):
                template_fields[key] = host_template_id

        self.assertItemsEqual(rh[2]['_template_fields'], template_fields)

        datal = [{
            'name': 'host_002',
            '_templates': [rh[1]['_id']],
            '_realm': self.realm_all
        }, {
            'name': 'host_003',
            '_templates': [rh[1]['_id']],
            '_realm': self.realm_all
        }]

        requests.post(self.endpoint + '/host', json=datal, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[3]['name'], "host_002")
        self.assertEqual(rh[4]['name'], "host_003")

    def test_host_templates_with_templates(self):
        """Test host templates linked to other templates

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}
        # Add command
        data = json.loads(open('cfg/command_ping.json').read())
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)
        # Check if command right in backend
        response = requests.get(self.endpoint + '/command', params=sort_id, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 3)
        rc = resp['_items']
        self.assertEqual(rc[2]['name'], "ping")

        # Create a template
        data = {
            'name': 'tpl-A',
            'check_command': rc[2]['_id'],
            '_is_template': True,
            'tags': ['tag-1'],
            'customs': {'key1': 'value1'},
            '_realm': self.realm_all
        }
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        # Check if host template is in the backend
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(len(resp['_items']), 2)
        self.assertEqual(rh[1]['name'], "tpl-A")
        self.assertEqual(rh[1]['_template_fields'], {})
        host_template_id = rh[1]['_id']
        # The host template has some specific fields
        self.assertEqual(rh[1]['tags'], ['tag-1'])
        self.assertEqual(rh[1]['customs'], {'key1': 'value1'})

        # Create a service template linked to the newly created host template
        data = {
            'name': 'service-tpl-A',
            'host': host_template_id,
            'check_command': rc[2]['_id'],
            '_is_template': True,
            '_realm': self.realm_all
        }
        ret = requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)
        resp = ret.json()
        self.assertEqual(resp['_status'], 'OK')

        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        # Only 1 service in the backend, and it is the newly created service template
        self.assertEqual(len(rs), 1)
        self.assertEqual(rs[0]['name'], "service-tpl-A")
        self.assertEqual(rs[0]['_is_template'], True)

        # Create a second host template templated from the first one
        data = {
            'name': 'tpl-A.1',
            'check_command': rc[2]['_id'],
            '_is_template': True,
            '_templates': [host_template_id],
            'tags': ['tag-2', 'tag-3'],
            'customs': {'key2': 'value2', 'key3': 'value3'},
            '_realm': self.realm_all
        }
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        # Check if host template is in the backend
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(len(resp['_items']), 3)
        self.assertEqual(rh[1]['name'], "tpl-A")
        self.assertEqual(rh[1]['_template_fields'], {})
        self.assertEqual(rh[2]['name'], "tpl-A.1")
        # The second template has some template fields from its linked template
        # except for some specific fields
        self.assertNotEqual(rh[2]['_template_fields'], {})
        for field in rh[2]['_template_fields']:
            value = rh[2]['_template_fields'][field]
            if field in ['notification_period', 'snapshot_period', 'snapshot_command',
                         'maintenance_period', 'check_period',
                         '_users_delete', '_users_read', '_users_update',
                         'tags', 'customs', 'users', 'usergroups']:
                assert value == 0
            else:
                assert value == host_template_id, "Field %s value is %s" % (field, value)
        # The host template has some specific fields and cumulated fields are not inherited
        self.assertEqual(rh[2]['tags'], ['tag-2', 'tag-3'])
        self.assertEqual(rh[2]['customs'], {'key2': 'value2', 'key3': 'value3'})

        host_template_id = rh[2]['_id']

        # Create a service template linked to the newly created host template
        data = {
            'name': 'service-tpl-B',
            'host': host_template_id,
            'check_command': rc[2]['_id'],
            '_is_template': True,
            '_realm': self.realm_all
        }
        ret = requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)
        resp = ret.json()
        self.assertEqual(resp['_status'], 'OK')

        # Check that no services got created
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        # Now 2 services in the backend, and it is only services templates
        self.assertEqual(len(rs), 2)
        self.assertEqual(rs[0]['name'], "service-tpl-A")
        self.assertEqual(rs[0]['_is_template'], True)
        self.assertEqual(rs[1]['name'], "service-tpl-B")
        self.assertEqual(rs[1]['_is_template'], True)

        # Create an host linked to the second template
        data = {
            'name': 'host-1',
            '_templates': [host_template_id],
            '_realm': self.realm_all
        }
        response = requests.post(self.endpoint + '/host', json=data,
                                 headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[1]['name'], "tpl-A")
        self.assertEqual(rh[2]['name'], "tpl-A.1")
        self.assertEqual(rh[3]['name'], "host-1")
        # The host has some template fields from its linked template
        # except for some specific fields
        self.assertNotEqual(rh[3]['_template_fields'], {})
        for field in rh[3]['_template_fields']:
            value = rh[3]['_template_fields'][field]
            if field in ['notification_period', 'snapshot_period', 'snapshot_command',
                         'maintenance_period', 'check_period',
                         '_users_delete', '_users_read', '_users_update',
                         'tags', 'customs', 'users', 'usergroups']:
                assert value == 0
            else:
                assert value == host_template_id, "Field %s value is %s" % (field, value)

        # The host has some fields that were cumulated from its linked template
        self.assertEqual(rh[3]['tags'], ['tag-1', 'tag-2', 'tag-3'])
        self.assertEqual(rh[3]['customs'], {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'})

        # Check that no services got created
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        # Now 4 services exist in the backend:
        # - the 2 services templates
        # - and the services created because of the templated host creation
        # (one from each host template)
        self.assertEqual(len(rs), 4)
        self.assertEqual(rs[0]['name'], "service-tpl-A")
        self.assertEqual(rs[0]['_is_template'], True)
        self.assertEqual(rs[1]['name'], "service-tpl-B")
        self.assertEqual(rs[1]['_is_template'], True)
        # Services are created almost simultaneously creation order is incertain...
        self.assertIn(rs[2]['name'], ["service-tpl-A", "service-tpl-B"])
        self.assertEqual(rs[2]['_is_template'], False)
        self.assertIn(rs[2]['name'], ["service-tpl-A", "service-tpl-B"])
        self.assertEqual(rs[3]['_is_template'], False)

    def test_host_templates_updates(self):
        """Test when update a host template

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}
        # Add command
        data = json.loads(open('cfg/command_ping.json').read())
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)
        # Check if command right in backend
        response = requests.get(self.endpoint + '/command', params=sort_id, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 3)
        rc = resp['_items']
        self.assertEqual(rc[2]['name'], "ping")

        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[2]['_id']
        data['name'] = 'srv001_tpl'
        if 'realm' in data:
            del data['realm']
        data['_realm'] = self.realm_all
        data['_is_template'] = True
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        # Check if host right in backend
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[1]['name'], "srv001_tpl")
        host_template_id = rh[1]['_id']
        data = {
            'name': 'host_001',
            '_templates': [host_template_id],
            '_realm': self.realm_all
        }
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[1]['name'], "srv001_tpl")
        self.assertEqual(rh[2]['name'], "host_001")
        self.assertEqual(rh[2]['check_command'], rc[2]['_id'])

        datap = {'check_interval': 1}
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': rh[2]['_etag']
        }
        requests.patch(self.endpoint + '/host/' + rh[2]['_id'], json=datap, headers=headers_patch,
                       auth=self.auth)
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[2]['name'], "host_001")
        self.assertEqual(rh[2]['check_interval'], 1)

        # With modification of host update, the PUT method (to update _template_fields modify
        # the _etag and we must see here if patch with wrong etag is right a failure)
        datap = {'check_interval': 50}
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': rh[1]['_etag']
        }
        requests.patch(self.endpoint + '/host/' + rh[2]['_id'], json=datap, headers=headers_patch,
                       auth=self.auth)
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[2]['name'], "host_001")
        self.assertEqual(rh[2]['check_interval'], 1)

        if 'check_interval' in rh[2]['_template_fields']:
            state = False
            self.assertTrue(state, 'check_interval does not be in _template_fields list')

        # update the template
        datap = {'initial_state': 'o'}
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': rh[1]['_etag']
        }
        requests.patch(self.endpoint + '/host/' + rh[1]['_id'], json=datap, headers=headers_patch,
                       auth=self.auth)

        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[1]['initial_state'], "o")
        self.assertEqual(rh[2]['name'], "host_001")
        self.assertEqual(rh[2]['initial_state'], "o")
        if 'initial_state' not in rh[2]['_template_fields']:
            state = False
            self.assertTrue(state, 'initial_state must be in _template_fields list')

        # update the template name
        datap = {'name': 'testhost'}
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': rh[1]['_etag']
        }
        requests.patch(self.endpoint + '/host/' + rh[1]['_id'], json=datap, headers=headers_patch,
                       auth=self.auth)

        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[1]['name'], "testhost")
        self.assertEqual(rh[2]['name'], "host_001")

    def test_service_templates(self):
        """Test service templates

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}

        # Add a command
        data = json.loads(open('cfg/command_ping.json').read())
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)
        # Check if command right in backend
        response = requests.get(self.endpoint + '/command', params=sort_id, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 3)
        rc = resp['_items']
        self.assertEqual(rc[2]['name'], "ping")

        # Add an host
        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[2]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        # Check if host right in backend
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[1]['name'], "srv001")

        # Add an host
        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[2]['_id']
        data['name'] = 'host_001'
        if 'realm' in data:
            del data['realm']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        # Check if host right in backend
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[1]['name'], "srv001")
        self.assertEqual(rh[2]['name'], "host_001")

        # add service template
        data = {
            'name': 'ping',
            'host': rh[1]['_id'],
            'check_command': rc[2]['_id'],
            'business_impact': 4,
            '_is_template': True,
            '_realm': self.realm_all
        }
        requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(rs[0]['name'], "ping")

        data = {
            'host': rh[2]['_id'],
            '_templates': [rs[0]['_id']],
            '_realm': self.realm_all
        }
        requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(rs[0]['name'], "ping")
        self.assertEqual(rs[1]['name'], "ping")
        self.assertEqual(rs[1]['host'], rh[2]['_id'])

    def test_service_templates_with_templates(self):
        """Test service templates linked to other templates

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}

        # Add a command
        data = json.loads(open('cfg/command_ping.json').read())
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)
        # Check if command right in backend
        response = requests.get(self.endpoint + '/command', params=sort_id, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 3)
        rc = resp['_items']
        self.assertEqual(rc[2]['name'], "ping")

        # Create an host
        data = {
            'name': 'host-1',
            '_realm': self.realm_all
        }
        response = requests.post(self.endpoint + '/host', json=data,
                                 headers=headers, auth=self.auth)
        # Check if host right in backend
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[0]['name'], "_dummy")
        self.assertEqual(rh[1]['name'], "host-1")

        # Create a template
        data = {
            'name': 'service-tpl-A',
            'host': rh[0]['_id'],
            'check_command': rc[2]['_id'],
            'business_impact': 4,
            '_is_template': True,
            '_realm': self.realm_all
        }
        ret = requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)
        resp = ret.json()
        self.assertEqual(resp['_status'], 'OK')
        service_template_id = resp['_id']

        # Create a second template templated from the first one
        data = {
            'name': 'service-tpl-A.1',
            'host': rh[0]['_id'],
            'check_command': rc[2]['_id'],
            '_realm': self.realm_all,
            '_is_template': True,
            '_templates': [service_template_id]
        }
        ret = requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)
        resp = ret.json()
        self.assertEqual(resp['_status'], 'OK')

        # Check if templates are in the backend
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(len(resp['_items']), 2)
        self.assertEqual(rs[0]['name'], "service-tpl-A")
        self.assertEqual(rs[0]['_template_fields'], {})
        self.assertEqual(rs[1]['name'], "service-tpl-A.1")
        # The second template has some template fields from its linked template
        # except for some specific fields
        self.assertNotEqual(rs[1]['_template_fields'], {})
        for field in rs[1]['_template_fields']:
            value = rs[1]['_template_fields'][field]
            if field in ['notification_period', 'snapshot_period', 'snapshot_command',
                         'maintenance_period', 'check_period',
                         '_users_delete', '_users_read', '_users_update',
                         'tags', 'customs', 'users', 'usergroups']:
                assert value == 0
            else:
                assert value == service_template_id, "Field %s value is %s" % (field, value)
        service_template_id = rs[1]['_id']

        # Create a service linked to the second template
        data = {
            'name': 'service-1',
            'host': rh[1]['_id'],
            'check_command': rc[2]['_id'],
            '_templates': [service_template_id],
            '_realm': self.realm_all
        }
        response = requests.post(self.endpoint + '/service', json=data,
                                 headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(rs[0]['name'], "service-tpl-A")
        self.assertEqual(rs[1]['name'], "service-tpl-A.1")
        self.assertEqual(rs[2]['name'], "service-1")
        # The user has some template fields from its linked template
        # except for some specific fields
        self.assertNotEqual(rs[2]['_template_fields'], {})
        for field in rs[2]['_template_fields']:
            value = rs[2]['_template_fields'][field]
            if field in ['notification_period', 'snapshot_period', 'snapshot_command',
                         'maintenance_period', 'check_period',
                         '_users_delete', '_users_read', '_users_update',
                         'tags', 'customs', 'users', 'usergroups']:
                assert value == 0
            else:
                assert value == service_template_id, "Field %s value is %s" % (field, value)

    def test_service_templates_updates(self):
        """Test when update service template

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}
        # Add command
        data = json.loads(open('cfg/command_ping.json').read())
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)
        # Check if command right in backend
        response = requests.get(self.endpoint + '/command', params=sort_id, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 3)
        rc = resp['_items']
        self.assertEqual(rc[2]['name'], "ping")

        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[2]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        # Check if host right in backend
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[1]['name'], "srv001")

        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[2]['_id']
        data['name'] = 'host_001'
        if 'realm' in data:
            del data['realm']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        # Check if host right in backend
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[1]['name'], "srv001")
        self.assertEqual(rh[2]['name'], "host_001")

        # add service template
        data = {
            'name': 'ping',
            'host': rh[1]['_id'],
            'check_command': rc[2]['_id'],
            'business_impact': 4,
            '_is_template': True,
            '_realm': self.realm_all
        }
        requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(rs[0]['name'], "ping")

        data = {
            'name': 'ping_test',
            'host': rh[2]['_id'],
            '_templates': [rs[0]['_id']],
            '_realm': self.realm_all
        }
        requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(rs[0]['name'], "ping")
        self.assertEqual(rs[1]['name'], "ping_test")
        self.assertEqual(rs[1]['host'], rh[2]['_id'])

        datap = {'check_interval': 1}
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': rs[1]['_etag']
        }
        requests.patch(self.endpoint + '/service/' + rs[1]['_id'], json=datap,
                       headers=headers_patch, auth=self.auth)

        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(rs[1]['name'], "ping_test")
        self.assertEqual(rs[1]['check_interval'], 1)
        if 'check_interval' in rs[1]['_template_fields']:
            state = False
            self.assertTrue(state, 'check_interval does not be in _template_fields list')

        # update the template
        datap = {'initial_state': 'u'}
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': rs[0]['_etag']
        }
        requests.patch(self.endpoint + '/service/' + rs[0]['_id'], json=datap,
                       headers=headers_patch, auth=self.auth)

        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(rs[0]['initial_state'], "u")
        self.assertEqual(rs[1]['name'], "ping_test")
        self.assertEqual(rs[1]['initial_state'], "u")
        if 'initial_state' not in rs[1]['_template_fields']:
            state = False
            self.assertTrue(state, 'initial_state must be in _template_fields list')

        # update the template name
        datap = {'name': 'ping2'}
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': rs[0]['_etag']
        }
        requests.patch(self.endpoint + '/service/' + rs[0]['_id'], json=datap,
                       headers=headers_patch, auth=self.auth)

        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(rs[0]['name'], "ping2")
        self.assertEqual(rs[1]['name'], "ping_test")

    def test_dummy_host_template(self):
        """Test when using the default _dummy host template

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}

        # Add some commands
        data = json.loads(open('cfg/command_ping.json').read())
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)

        data = json.loads(open('cfg/command_http.json').read())
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)

        # Check command are in the backend
        response = requests.get(self.endpoint + '/command', params=sort_id, auth=self.auth)
        resp = response.json()
        rc = resp['_items']
        self.assertEqual(len(rc), 4)
        self.assertEqual(rc[2]['name'], "ping")
        self.assertEqual(rc[3]['name'], "http")

        # Check _dummy host exists in the backend
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(len(rh), 1)
        self.assertEqual(rh[0]['name'], "_dummy")
        self.assertEqual(rh[0]['_is_template'], True)
        self.assertEqual(rh[0]['_templates_with_services'], False)

        # Check that no services exist in the backend
        params = {'where': json.dumps({'_is_template': False})}
        response = requests.get(self.endpoint + '/service', params=params, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(len(rs), 0)

        # Add services templates, linked to the _dummy host template
        data = {
            'name': 'Ping',
            'host': rh[0]['_id'],
            'check_command': rc[2]['_id'],
            '_is_template': True,
            '_realm': self.realm_all
        }
        requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)
        data = {
            'name': 'Http',
            'host': rh[0]['_id'],
            'check_command': rc[3]['_id'],
            '_is_template': True,
            '_realm': self.realm_all
        }
        requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(len(rs), 2)
        self.assertEqual(rs[0]['name'], "Ping")
        self.assertEqual(rs[0]['_is_template'], True)
        self.assertEqual(rs[1]['name'], "Http")
        self.assertEqual(rs[1]['_is_template'], True)

        # Add an host with host template but with no service templates
        data = {
            'name': 'host_001',
            '_templates': [rh[0]['_id']],
            # No service templating!
            '_templates_with_services': False,
            '_realm': self.realm_all
        }
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(len(rh), 2)
        self.assertEqual(rh[0]['name'], "_dummy")
        self.assertEqual(rh[1]['name'], "host_001")
        self.assertEqual(rh[1]['_is_template'], False)

        # Check that no services exist in the backend
        params = {'where': json.dumps({'_is_template': False})}
        response = requests.get(self.endpoint + '/service', params=params, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(len(rs), 0)

        # Add an host with host template + allow service templates
        data = {
            'name': 'host_002',
            '_templates': [rh[0]['_id']],
            '_templates_with_services': True,
            '_realm': self.realm_all
        }
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(len(rh), 3)
        self.assertEqual(rh[0]['name'], "_dummy")
        self.assertEqual(rh[1]['name'], "host_001")
        self.assertEqual(rh[1]['_is_template'], False)
        self.assertEqual(rh[2]['name'], "host_002")
        self.assertEqual(rh[2]['_is_template'], False)

        # Check that some services now exist in the backend
        params = {'where': json.dumps({'_is_template': False})}
        response = requests.get(self.endpoint + '/service', params=params, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(len(rs), 2)

    # pylint: disable=too-many-locals
    def test_host_services_template(self):
        """Test when use and add / modify / delete (host + service) template

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}
        # Add command
        data = json.loads(open('cfg/command_ping.json').read())
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)

        data = json.loads(open('cfg/command_http.json').read())
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)

        data = json.loads(open('cfg/command_https.json').read())
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)

        data = json.loads(open('cfg/command_ssh.json').read())
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)

        # Check if command right in backend
        response = requests.get(self.endpoint + '/command', params=sort_id, auth=self.auth)
        resp = response.json()
        rc = resp['_items']
        self.assertEqual(len(rc), 6)
        self.assertEqual(rc[2]['name'], "ping")
        self.assertEqual(rc[3]['name'], "http")
        self.assertEqual(rc[4]['name'], "https")
        self.assertEqual(rc[5]['name'], "ssh")

        # Add host templates
        # template template_standard_linux
        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[0]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = self.realm_all
        data['name'] = 'template_standard_linux'
        data['_is_template'] = True
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        # Check if host right in backend
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(len(rh), 2)
        self.assertEqual(rh[1]['name'], "template_standard_linux")

        # template_web based on template standard_linux
        data['name'] = 'template_web'
        data['_templates'] = [rh[1]['_id']]
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        # Check if host right in backend
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(len(rh), 3)
        self.assertEqual(rh[1]['name'], "template_standard_linux")
        self.assertEqual(rh[2]['name'], "template_web")
        # ~~~ Now we have 3 hosts templates ~~~
        # * 0: _dummy
        # * 1: template_standard_linux -> services ping and ssh
        # * 2: template_web -> services ping and ssh AND http and https

        # Add services templates
        data = {
            'name': 'ping',
            'host': rh[1]['_id'],
            'check_command': rc[1]['_id'],
            'business_impact': 4,
            '_is_template': True,
            '_realm': self.realm_all
        }
        requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)
        data['name'] = 'ssh'
        data['check_command'] = rc[3]['_id']
        requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)
        data['name'] = 'http'
        data['host'] = rh[2]['_id']
        data['check_command'] = rc[1]['_id']
        requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)
        data['name'] = 'https'
        data['check_command'] = rc[2]['_id']
        requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(len(rs), 4)
        self.assertEqual(rs[0]['name'], "ping")
        self.assertEqual(rs[1]['name'], "ssh")
        self.assertEqual(rs[2]['name'], "http")
        self.assertEqual(rs[3]['name'], "https")
        # ~~~ Now our 3 hosts templates are linked with services templates ~~~
        # * 0: _dummy
        # * 1: template_standard_linux -> services ping and ssh
        # * 2: template_web -> services http and https (AND ping and ssh from template inheritance)
        # ~~~ Now we have 4 services templates all
        # linked to the template_standard_linux host template ~~~
        # * 0: ping
        # * 1: ssh
        # * 2: http
        # * 3: https

        params = {'where': json.dumps({'host': rh[1]['_id']})}
        response = requests.get(self.endpoint + '/service', params=params, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(len(rs), 2)

        params = {'where': json.dumps({'host': rh[2]['_id']})}
        response = requests.get(self.endpoint + '/service', params=params, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(len(rs), 2)

        # add a host with host template + allow service templates
        data = {
            'name': 'host_001',
            '_templates': [rh[1]['_id'], rh[2]['_id']],
            '_templates_with_services': True,
            '_realm': self.realm_all
        }
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        # add a second host with host template + allow service templates
        data = {
            'name': 'host_002',
            '_templates': [rh[1]['_id'], rh[2]['_id']],
            '_templates_with_services': True,
            '_realm': self.realm_all
        }
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(len(rh), 5)
        self.assertEqual(rh[1]['name'], "template_standard_linux")
        self.assertEqual(rh[2]['name'], "template_web")
        self.assertEqual(rh[3]['name'], "host_001")
        self.assertEqual(rh[4]['name'], "host_002")

        # ~~~ Now we have 3 hosts templates and 2 hosts ~~~
        # * 0: _dummy
        # * 1: template_standard_linux
        # * 2: template_web
        # * 3: host_001
        # * 4: host_002

        # The new hosts have 4 services each
        params = {'where': json.dumps({'host': rh[3]['_id']})}
        response = requests.get(self.endpoint + '/service', params=params, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(len(rs), 4)

        params = {'where': json.dumps({'host': rh[4]['_id']})}
        response = requests.get(self.endpoint + '/service', params=params, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(len(rs), 4)

        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(len(rs), 12)
        # 4 services are the templates
        # 8 are the services of the 2 real hosts
        ref = [
            {
                'name': 'http',
                '_is_template': True
            },
            {
                'name': 'ping',
                '_is_template': True
            },
            {
                'name': 'ssh',
                '_is_template': True
            },
            {
                'name': 'https',
                '_is_template': True
            },
            {
                'name': 'http',
                '_is_template': False
            },
            {
                'name': 'ping',
                '_is_template': False
            },
            {
                'name': 'ssh',
                '_is_template': False
            },
            {
                'name': 'https',
                '_is_template': False
            },
            {
                'name': 'http',
                '_is_template': False
            },
            {
                'name': 'ping',
                '_is_template': False
            },
            {
                'name': 'ssh',
                '_is_template': False
            },
            {
                'name': 'https',
                '_is_template': False
            }
        ]
        service_db = []
        ping_db_template = 0
        ping_db_nottemplate = 0
        num = 0
        for value in rs:
            service_db.append({'name': value['name'], '_is_template': value['_is_template']})
            if value['name'] == "ping":
                if value['_is_template']:
                    ping_db_template = num
                else:
                    ping_db_nottemplate = num
            num += 1

        self.assertItemsEqual(ref, service_db)

        # Now update a service template
        data = {'name': 'ping2'}
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': rs[0]['_etag']
        }
        requests.patch(self.endpoint + '/service/' + rs[0]['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(rs[ping_db_template]['name'], "ping2")
        self.assertEqual(rs[ping_db_nottemplate]['name'], "ping2")

        # Now remove the host template template_web of the host host_001
        data = {'_templates': [rh[1]['_id']]}
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': rh[3]['_etag']
        }
        requests.patch(self.endpoint + '/host/' + rh[3]['_id'], json=data, headers=headers_patch,
                       auth=self.auth)

        # 2 services were removed
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(len(rs), 10)
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[3]['_templates'], [rh[1]['_id']])
        self.assertEqual(rh[4]['_templates'], [rh[1]['_id'], rh[2]['_id']])

        # Now re-add the template template_web of host
        data = {'_templates': [rh[1]['_id'], rh[2]['_id']]}
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': rh[3]['_etag']
        }
        requests.patch(self.endpoint + '/host/' + rh[3]['_id'], json=data, headers=headers_patch,
                       auth=self.auth)

        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[3]['_templates'], [rh[1]['_id'], rh[2]['_id']])

        # 2 services were created
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(len(rs), 12)

        # Now add a new template service
        data = {
            'name': 'ssh_new_method',
            'host': rh[1]['_id'],
            'check_command': rc[0]['_id'],
            'business_impact': 4,
            '_is_template': True,
            '_templates_from_host_template': True,
            '_realm': self.realm_all
        }
        responsep = requests.post(self.endpoint + '/service', json=data, headers=headers,
                                  auth=self.auth)
        ret_new = responsep.json()
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        rs = resp['_items']

        # Both hosts inherit the new service from the standard linux
        self.assertEqual(len(rs), 16)
        self.assertEqual(rs[15]['_templates'][0], ret_new['_id'])
        self.assertFalse(rs[15]['_is_template'])
        self.assertEqual(rs[14]['_templates'][0], ret_new['_id'])
        self.assertFalse(rs[14]['_is_template'])
        self.assertEqual(rs[13]['_templates'][0], ret_new['_id'])
        self.assertFalse(rs[13]['_is_template'])
        self.assertEqual(rs[12]['_templates'], [])
        self.assertTrue(rs[12]['_is_template'])

        # Now delete a template service
        response = requests.get(self.endpoint + '/service/' + ret_new['_id'],
                                params=sort_id, auth=self.auth)
        response = response.json()
        headers_delete = {
            'Content-Type': 'application/json',
            'If-Match': response['_etag']
        }
        requests.delete(self.endpoint + '/service/' + response['_id'],
                        headers=headers_delete, auth=self.auth)
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        service_name = []
        for serv in resp['_items']:
            service_name.append(serv['name'])
        self.assertEqual(len(resp['_items']), 12)
        self.assertItemsEqual(['ping2', 'ssh', 'http', 'https', 'ping2', 'ssh', 'http', 'https',
                               'ping2', 'ssh', 'http', 'https'],
                              service_name)

    def test_user_templates(self):
        """Test user templates

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}
        # Add command
        data = json.loads(open('cfg/command_notification_host.json').read())
        data['_realm'] = self.realm_all
        ret = requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)
        resp = ret.json()
        self.assertEqual(resp['_status'], 'OK', resp)
        host_notif = resp['_id']

        data = json.loads(open('cfg/command_notification_service.json').read())
        data['_realm'] = self.realm_all
        ret = requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)
        resp = ret.json()
        self.assertEqual(resp['_status'], 'OK', resp)
        service_notif = resp['_id']

        # get timeperiods
        response = requests.get(self.endpoint + '/timeperiod', params=sort_id, auth=self.auth)
        resp = response.json()
        rtp = resp['_items']

        data = {
            'name': 'template_user',
            'host_notification_period': rtp[0]['_id'],
            'service_notification_period': rtp[0]['_id'],
            'host_notification_commands': [host_notif],
            'service_notification_commands': [service_notif],
            'can_submit_commands': True,
            '_realm': self.realm_all,
            '_is_template': True
        }
        ret = requests.post(self.endpoint + '/user', json=data, headers=headers, auth=self.auth)
        resp = ret.json()
        self.assertEqual(resp['_status'], 'OK')
        user_template_id = resp['_id']

        # add new user
        data = {
            'name': 'david.durieux',
            '_templates': [user_template_id],
            '_realm': self.realm_all
        }
        ret = requests.post(self.endpoint + '/user', json=data, headers=headers, auth=self.auth)
        resp = ret.json()
        self.assertEqual(resp['_status'], 'OK', resp)

        response = requests.get(self.endpoint + '/user', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[0]['name'], "admin")
        self.assertEqual(rh[1]['name'], "template_user")
        self.assertEqual(rh[2]['name'], "david.durieux")

        schema = user_schema()
        template_fields = {}
        ignore_fields = ['name', 'realm', '_realm', '_template_fields',
                         '_templates', '_is_template',
                         'host_notification_period', 'service_notification_period']
        for key in schema['schema']:
            if key not in ignore_fields:
                template_fields[key] = user_template_id

        self.assertItemsEqual(rh[2]['_template_fields'], template_fields)

        datal = [{
            'name': 'to.to',
            '_templates': [rh[1]['_id']],
            '_realm': self.realm_all
        }, {
            'name': 'ti.ti',
            '_templates': [rh[1]['_id']],
            '_realm': self.realm_all
        }]

        ret = requests.post(self.endpoint + '/user', json=datal, headers=headers, auth=self.auth)
        resp = ret.json()
        self.assertEqual(resp['_status'], 'OK', resp)

        response = requests.get(self.endpoint + '/user', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[3]['name'], "to.to")
        self.assertEqual(rh[4]['name'], "ti.ti")

        # user name is unique, so if we add a user with template but with no user,
        # it will try to use name of user template and give error
        data = {
            '_templates': [user_template_id],
            '_realm': self.realm_all
        }
        ret = requests.post(self.endpoint + '/user', json=data, headers=headers, auth=self.auth)
        resp = ret.json()
        self.assertEqual(resp['_status'], 'ERR', resp)

    def test_user_templates_with_templates(self):
        """Test user templates linked to other templates

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}

        # Add commands
        data = json.loads(open('cfg/command_notification_host.json').read())
        data['_realm'] = self.realm_all
        ret = requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)
        resp = ret.json()
        self.assertEqual(resp['_status'], 'OK', resp)
        host_notif = resp['_id']

        data = json.loads(open('cfg/command_notification_service.json').read())
        data['_realm'] = self.realm_all
        ret = requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)
        resp = ret.json()
        self.assertEqual(resp['_status'], 'OK', resp)
        service_notif = resp['_id']

        # get timeperiods
        response = requests.get(self.endpoint + '/timeperiod', params=sort_id, auth=self.auth)
        resp = response.json()
        rtp = resp['_items']

        # Create a template
        data = {
            'name': 'user-tpl-A',
            'host_notification_period': rtp[0]['_id'],
            'service_notification_period': rtp[0]['_id'],
            'host_notification_commands': [host_notif],
            'service_notification_commands': [service_notif],
            '_realm': self.realm_all,
            '_is_template': True
        }
        ret = requests.post(self.endpoint + '/user', json=data, headers=headers, auth=self.auth)
        resp = ret.json()
        self.assertEqual(resp['_status'], 'OK')
        user_template_id = resp['_id']

        # Create a second template templated from the first one
        data = {
            'name': 'user-tpl-A.1',
            '_realm': self.realm_all,
            '_is_template': True,
            '_templates': [user_template_id]
        }
        ret = requests.post(self.endpoint + '/user', json=data, headers=headers, auth=self.auth)
        resp = ret.json()
        self.assertEqual(resp['_status'], 'OK')

        # Check if templates are in the backend
        response = requests.get(self.endpoint + '/user', params=sort_id, auth=self.auth)
        resp = response.json()
        ru = resp['_items']
        self.assertEqual(len(resp['_items']), 3)
        self.assertEqual(ru[1]['name'], "user-tpl-A")
        self.assertEqual(ru[1]['_template_fields'], {})
        self.assertEqual(ru[2]['name'], "user-tpl-A.1")
        # The second template has some template fields from its linked template
        # except for some specific fields
        self.assertNotEqual(ru[2]['_template_fields'], {})
        for field in ru[2]['_template_fields']:
            value = ru[2]['_template_fields'][field]
            if field in ['_users_delete', '_users_read', '_users_update',
                         'tags', 'customs',
                         'host_notification_commands', 'service_notification_commands']:
                assert value == 0
            else:
                assert value == user_template_id, "Field %s value is %s" % (field, value)
        user_template_id = ru[2]['_id']

        # Create a user linked to the second template
        data = {
            'name': 'user-1',
            '_templates': [user_template_id],
            '_realm': self.realm_all
        }
        response = requests.post(self.endpoint + '/user', json=data,
                                 headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/user', params=sort_id, auth=self.auth)
        resp = response.json()
        ru = resp['_items']
        self.assertEqual(ru[1]['name'], "user-tpl-A")
        self.assertEqual(ru[2]['name'], "user-tpl-A.1")
        self.assertEqual(ru[3]['name'], "user-1")
        # The user has some template fields from its linked template
        # except for some specific fields
        self.assertNotEqual(ru[3]['_template_fields'], {})
        for field in ru[3]['_template_fields']:
            value = ru[3]['_template_fields'][field]
            if field in ['_users_delete', '_users_read', '_users_update',
                         'tags', 'customs',
                         'host_notification_commands', 'service_notification_commands']:
                assert value == 0
            else:
                assert value == user_template_id, "Field %s value is %s" % (field, value)

    def test_user_templates_updates(self):
        """Test when update a user template

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}
        # Add command
        data = json.loads(open('cfg/command_notification_host.json').read())
        data['_realm'] = self.realm_all
        ret = requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)
        resp = ret.json()
        self.assertEqual(resp['_status'], 'OK', resp)
        host_notif = resp['_id']

        data = json.loads(open('cfg/command_notification_service.json').read())
        data['_realm'] = self.realm_all
        ret = requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)
        resp = ret.json()
        self.assertEqual(resp['_status'], 'OK', resp)
        service_notif = resp['_id']

        # get timeperiods
        response = requests.get(self.endpoint + '/timeperiod', params=sort_id, auth=self.auth)
        resp = response.json()
        rtp = resp['_items']

        data = {
            'name': 'template_user',
            'host_notification_period': rtp[0]['_id'],
            'service_notification_period': rtp[0]['_id'],
            'host_notification_commands': [host_notif],
            'service_notification_commands': [service_notif],
            'can_submit_commands': True,
            '_realm': self.realm_all,
            '_is_template': True
        }
        ret = requests.post(self.endpoint + '/user', json=data, headers=headers, auth=self.auth)
        resp = ret.json()
        self.assertEqual(resp['_status'], 'OK', resp)
        user_template_id = resp['_id']

        # add new user
        data = {
            'name': 'david.durieux',
            '_templates': [user_template_id],
            '_realm': self.realm_all
        }
        ret = requests.post(self.endpoint + '/user', json=data, headers=headers, auth=self.auth)
        resp = ret.json()
        self.assertEqual(resp['_status'], 'OK', resp)

        response = requests.get(self.endpoint + '/user', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[1]['name'], "template_user")
        self.assertEqual(rh[2]['name'], "david.durieux")

        # update the user
        datap = {'address1': "Cocorico street"}
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': rh[2]['_etag']
        }
        requests.patch(self.endpoint + '/user/' + rh[2]['_id'], json=datap, headers=headers_patch,
                       auth=self.auth)

        response = requests.get(self.endpoint + '/user', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[1]['address1'], "")
        self.assertEqual(rh[2]['address1'], "Cocorico street")
        if 'address1' in rh[2]['_template_fields']:
            state = False
            self.assertTrue(state, 'address1 must not be in _template_fields list')

        # update the template addresses
        datap = {'address1': "French street", 'address2': "Geronimo"}
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': rh[1]['_etag']
        }
        requests.patch(self.endpoint + '/user/' + rh[1]['_id'], json=datap, headers=headers_patch,
                       auth=self.auth)

        response = requests.get(self.endpoint + '/user', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(rh[1]['address1'], "French street")
        self.assertEqual(rh[2]['address1'], "Cocorico street")
        self.assertEqual(rh[1]['address2'], "Geronimo")
        self.assertEqual(rh[2]['address2'], "Geronimo")
