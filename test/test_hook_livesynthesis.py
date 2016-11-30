#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This test verify the different hooks used in the backend to update livesynthesis
"""

import os
import json
import time
import shlex
import subprocess
import copy
import requests
import unittest2
from alignak_backend.livesynthesis import Livesynthesis


class TestHookLivesynthesis(unittest2.TestCase):
    """
    This class test the hooks used to update livesynthesis resource
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
        Delete resources in backend

        :return: None
        """
        for resource in ['host', 'service', 'command', 'livestate', 'livesynthesis']:
            requests.delete(cls.endpoint + '/' + resource, auth=cls.auth)

        response = requests.get(cls.endpoint + '/realm', auth=cls.auth)
        resp = response.json()
        for realm in resp['_items']:
            if realm['name'] in ['All A', 'All B']:
                headers = {'If-Match': realm['_etag']}
                response = requests.delete(cls.endpoint + '/realm/' + realm['_id'], headers=headers,
                                           auth=cls.auth)

    def test_add_host(self):
        """
        Test livesynthesis when add a host

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
        rc = resp['_items']

        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[0]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        # Check if livesynthesis right created
        response = requests.get(self.endpoint + '/livesynthesis', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['hosts_total'], 1)
        self.assertEqual(r[0]['hosts_up_hard'], 0)
        self.assertEqual(r[0]['hosts_up_soft'], 0)
        self.assertEqual(r[0]['hosts_down_hard'], 0)
        self.assertEqual(r[0]['hosts_down_soft'], 0)
        self.assertEqual(r[0]['hosts_unreachable_hard'], 1)
        self.assertEqual(r[0]['hosts_unreachable_soft'], 0)
        self.assertEqual(r[0]['hosts_acknowledged'], 0)
        self.assertEqual(r[0]['hosts_in_downtime'], 0)
        self.assertEqual(r[0]['services_total'], 0)
        self.assertEqual(r[0]['services_ok_hard'], 0)
        self.assertEqual(r[0]['services_ok_soft'], 0)
        self.assertEqual(r[0]['services_warning_hard'], 0)
        self.assertEqual(r[0]['services_warning_soft'], 0)
        self.assertEqual(r[0]['services_critical_hard'], 0)
        self.assertEqual(r[0]['services_critical_soft'], 0)
        self.assertEqual(r[0]['services_unknown_hard'], 0)
        self.assertEqual(r[0]['services_unknown_soft'], 0)
        self.assertEqual(r[0]['services_unreachable_hard'], 0)
        self.assertEqual(r[0]['services_unreachable_soft'], 0)
        self.assertEqual(r[0]['services_acknowledged'], 0)
        self.assertEqual(r[0]['services_in_downtime'], 0)

    def test_add_host_template(self):
        """
        Test livesynthesis when add a host

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
        rc = resp['_items']

        data = json.loads(open('cfg/host_template.json').read())
        data['check_command'] = rc[0]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        # No livesynthesis should be created for an host template
        response = requests.get(self.endpoint + '/livesynthesis', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 0)

    def test_add_service(self):
        """
        Test livesynthesis when add a service

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
        rc = resp['_items']

        # add host
        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[0]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']

        # Add service
        data = json.loads(open('cfg/service_srv001_ping.json').read())
        data['host'] = rh[0]['_id']
        data['check_command'] = rc[0]['_id']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)

        # Check if livesynthesis right created
        response = requests.get(self.endpoint + '/livesynthesis', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['hosts_total'], 1)
        self.assertEqual(r[0]['hosts_up_hard'], 0)
        self.assertEqual(r[0]['hosts_up_soft'], 0)
        self.assertEqual(r[0]['hosts_down_hard'], 0)
        self.assertEqual(r[0]['hosts_down_soft'], 0)
        self.assertEqual(r[0]['hosts_unreachable_hard'], 1)
        self.assertEqual(r[0]['hosts_unreachable_soft'], 0)
        self.assertEqual(r[0]['hosts_acknowledged'], 0)
        self.assertEqual(r[0]['hosts_in_downtime'], 0)
        self.assertEqual(r[0]['services_total'], 1)
        self.assertEqual(r[0]['services_ok_hard'], 0)
        self.assertEqual(r[0]['services_ok_soft'], 0)
        self.assertEqual(r[0]['services_warning_hard'], 0)
        self.assertEqual(r[0]['services_warning_soft'], 0)
        self.assertEqual(r[0]['services_critical_hard'], 0)
        self.assertEqual(r[0]['services_critical_soft'], 0)
        self.assertEqual(r[0]['services_unknown_hard'], 1)
        self.assertEqual(r[0]['services_unknown_soft'], 0)
        self.assertEqual(r[0]['services_unreachable_hard'], 0)
        self.assertEqual(r[0]['services_unreachable_soft'], 0)
        self.assertEqual(r[0]['services_acknowledged'], 0)
        self.assertEqual(r[0]['services_in_downtime'], 0)

    def test_update_host(self):
        """
        Test livesynthesis when updating live state of an host

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
        rc = resp['_items']

        # Add host
        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[0]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']

        # Add service
        data = json.loads(open('cfg/service_srv001_ping.json').read())
        data['host'] = rh[0]['_id']
        data['check_command'] = rc[0]['_id']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)

        # Get host
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        ls_host = copy.copy(r[0])
        updated_field = ls_host['_updated']

        # Get initial live synthesis
        response = requests.get(self.endpoint + '/livesynthesis', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['hosts_total'], 1)
        self.assertEqual(r[0]['hosts_up_hard'], 0)
        self.assertEqual(r[0]['hosts_up_soft'], 0)
        self.assertEqual(r[0]['hosts_down_hard'], 0)
        self.assertEqual(r[0]['hosts_down_soft'], 0)
        self.assertEqual(r[0]['hosts_unreachable_hard'], 1)
        self.assertEqual(r[0]['hosts_unreachable_soft'], 0)
        self.assertEqual(r[0]['hosts_acknowledged'], 0)
        self.assertEqual(r[0]['hosts_in_downtime'], 0)
        self.assertEqual(r[0]['services_total'], 1)
        self.assertEqual(r[0]['services_ok_hard'], 0)
        self.assertEqual(r[0]['services_ok_soft'], 0)
        self.assertEqual(r[0]['services_warning_hard'], 0)
        self.assertEqual(r[0]['services_warning_soft'], 0)
        self.assertEqual(r[0]['services_critical_hard'], 0)
        self.assertEqual(r[0]['services_critical_soft'], 0)
        self.assertEqual(r[0]['services_unknown_hard'], 1)
        self.assertEqual(r[0]['services_unknown_soft'], 0)
        self.assertEqual(r[0]['services_unreachable_hard'], 0)
        self.assertEqual(r[0]['services_unreachable_soft'], 0)
        self.assertEqual(r[0]['services_acknowledged'], 0)
        self.assertEqual(r[0]['services_in_downtime'], 0)

        # Update something else than the live state for an host
        time.sleep(1)
        data = {
            'alias': 'Updated alias',
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_host['_etag']
        }
        requests.patch(self.endpoint + '/host/' + ls_host['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(
            self.endpoint + '/host/' + ls_host['_id'], params=sort_id, auth=self.auth
        )
        resp = response.json()
        ls_host = resp
        # _updated field must have changed...
        self.assertNotEqual(updated_field, ls_host['_updated'])
        updated_field = ls_host['_updated']

        # Update live state for an host
        # => DOWN SOFT
        time.sleep(1)
        data = {
            'ls_state': 'DOWN',
            'ls_state_id': 1,
            'ls_state_type': 'SOFT',
            'ls_last_check': 1465685852,
            'ls_last_state': 'UP',
            'ls_last_state_type': 'HARD',
            'ls_output': 'CRITICAL - Plugin timed out after 10 seconds',
            'ls_long_output': '',
            'ls_perf_data': '',
            'ls_acknowledged': False,
            'ls_execution_time': 10.0598139763,
            'ls_latency': 1.3571469784
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_host['_etag']
        }
        requests.patch(self.endpoint + '/host/' + ls_host['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(
            self.endpoint + '/host/' + ls_host['_id'], params=sort_id, auth=self.auth
        )
        resp = response.json()
        ls_host = resp
        # _updated field did not changed...
        self.assertEqual(updated_field, ls_host['_updated'])

        response = requests.get(self.endpoint + '/livesynthesis', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['hosts_total'], 1)
        self.assertEqual(r[0]['hosts_up_hard'], 0)
        self.assertEqual(r[0]['hosts_up_soft'], 0)
        self.assertEqual(r[0]['hosts_down_hard'], 0)
        self.assertEqual(r[0]['hosts_down_soft'], 1)
        self.assertEqual(r[0]['hosts_unreachable_hard'], 0)
        self.assertEqual(r[0]['hosts_unreachable_soft'], 0)
        self.assertEqual(r[0]['hosts_acknowledged'], 0)
        self.assertEqual(r[0]['hosts_in_downtime'], 0)
        self.assertEqual(r[0]['services_total'], 1)
        self.assertEqual(r[0]['services_ok_hard'], 0)
        self.assertEqual(r[0]['services_ok_soft'], 0)
        self.assertEqual(r[0]['services_warning_hard'], 0)
        self.assertEqual(r[0]['services_warning_soft'], 0)
        self.assertEqual(r[0]['services_critical_hard'], 0)
        self.assertEqual(r[0]['services_critical_soft'], 0)
        self.assertEqual(r[0]['services_unknown_hard'], 1)
        self.assertEqual(r[0]['services_unknown_soft'], 0)
        self.assertEqual(r[0]['services_unreachable_hard'], 0)
        self.assertEqual(r[0]['services_unreachable_soft'], 0)
        self.assertEqual(r[0]['services_acknowledged'], 0)
        self.assertEqual(r[0]['services_in_downtime'], 0)

        # => DOWN HARD
        time.sleep(1)
        data = {
            'ls_state': 'DOWN',
            'ls_state_id': 1,
            'ls_state_type': 'HARD',
            'ls_last_check': 1465685913,
            'ls_last_state': 'DOWN',
            'ls_last_state_type': 'SOFT',
            'ls_output': 'CRITICAL - Plugin timed out after 10 seconds',
            'ls_long_output': '',
            'ls_perf_data': '',
            'ls_acknowledged': False,
            'ls_execution_time': 10.0842711926,
            'ls_latency': 2.0673139095
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_host['_etag']
        }
        requests.patch(self.endpoint + '/host/' + ls_host['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        ls_host = copy.copy(r[0])
        # _updated field did not changed...
        self.assertEqual(updated_field, ls_host['_updated'])

        response = requests.get(self.endpoint + '/livesynthesis', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['hosts_total'], 1)
        self.assertEqual(r[0]['hosts_up_hard'], 0)
        self.assertEqual(r[0]['hosts_up_soft'], 0)
        self.assertEqual(r[0]['hosts_down_hard'], 1)
        self.assertEqual(r[0]['hosts_down_soft'], 0)
        self.assertEqual(r[0]['hosts_unreachable_hard'], 0)
        self.assertEqual(r[0]['hosts_unreachable_soft'], 0)
        self.assertEqual(r[0]['hosts_acknowledged'], 0)
        self.assertEqual(r[0]['hosts_in_downtime'], 0)
        self.assertEqual(r[0]['services_total'], 1)
        self.assertEqual(r[0]['services_ok_hard'], 0)
        self.assertEqual(r[0]['services_ok_soft'], 0)
        self.assertEqual(r[0]['services_warning_hard'], 0)
        self.assertEqual(r[0]['services_warning_soft'], 0)
        self.assertEqual(r[0]['services_critical_hard'], 0)
        self.assertEqual(r[0]['services_critical_soft'], 0)
        self.assertEqual(r[0]['services_unknown_hard'], 1)
        self.assertEqual(r[0]['services_unknown_soft'], 0)
        self.assertEqual(r[0]['services_unreachable_hard'], 0)
        self.assertEqual(r[0]['services_unreachable_soft'], 0)
        self.assertEqual(r[0]['services_acknowledged'], 0)
        self.assertEqual(r[0]['services_in_downtime'], 0)

        # => last_(state|state_type) are changed
        time.sleep(1)
        data = {
            'ls_state': 'DOWN',
            'ls_state_id': 1,
            'ls_state_type': 'HARD',
            'ls_last_check': 1465685971,
            'ls_last_state': 'DOWN',
            'ls_last_state_type': 'HARD',
            'ls_output': 'CRITICAL - Plugin timed out after 10 seconds',
            'ls_long_output': '',
            'ls_perf_data': '',
            'ls_acknowledged': False,
            'ls_execution_time': 10.1046719551,
            'ls_latency': 0.926582098
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_host['_etag']
        }
        requests.patch(self.endpoint + '/host/' + ls_host['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        ls_host = copy.copy(r[0])
        # _updated field did not changed...
        self.assertEqual(updated_field, ls_host['_updated'])

        response = requests.get(self.endpoint + '/livesynthesis', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['hosts_total'], 1)
        self.assertEqual(r[0]['hosts_up_hard'], 0)
        self.assertEqual(r[0]['hosts_up_soft'], 0)
        self.assertEqual(r[0]['hosts_down_hard'], 1)
        self.assertEqual(r[0]['hosts_down_soft'], 0)
        self.assertEqual(r[0]['hosts_unreachable_hard'], 0)
        self.assertEqual(r[0]['hosts_unreachable_soft'], 0)
        self.assertEqual(r[0]['hosts_acknowledged'], 0)
        self.assertEqual(r[0]['hosts_in_downtime'], 0)
        self.assertEqual(r[0]['services_total'], 1)
        self.assertEqual(r[0]['services_ok_hard'], 0)
        self.assertEqual(r[0]['services_ok_soft'], 0)
        self.assertEqual(r[0]['services_warning_hard'], 0)
        self.assertEqual(r[0]['services_warning_soft'], 0)
        self.assertEqual(r[0]['services_critical_hard'], 0)
        self.assertEqual(r[0]['services_critical_soft'], 0)
        self.assertEqual(r[0]['services_unknown_hard'], 1)
        self.assertEqual(r[0]['services_unknown_soft'], 0)
        self.assertEqual(r[0]['services_unreachable_hard'], 0)
        self.assertEqual(r[0]['services_unreachable_soft'], 0)
        self.assertEqual(r[0]['services_acknowledged'], 0)
        self.assertEqual(r[0]['services_in_downtime'], 0)

        # we acknowledge the host
        time.sleep(1)
        data = {
            'ls_state': 'DOWN',
            'ls_state_id': 1,
            'ls_state_type': 'HARD',
            'ls_last_check': 1465686371,
            'ls_last_state': 'DOWN',
            'ls_last_state_type': 'HARD',
            'ls_output': 'CRITICAL - Plugin timed out after 10 seconds',
            'ls_long_output': '',
            'ls_perf_data': '',
            'ls_acknowledged': True,
            'ls_execution_time': 10.1046719551,
            'ls_latency': 0.926582098
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_host['_etag']
        }
        requests.patch(self.endpoint + '/host/' + ls_host['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        ls_host = copy.copy(r[0])
        # _updated field did not changed...
        self.assertEqual(updated_field, ls_host['_updated'])

        response = requests.get(self.endpoint + '/livesynthesis', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['hosts_total'], 1)
        self.assertEqual(r[0]['hosts_up_hard'], 0)
        self.assertEqual(r[0]['hosts_up_soft'], 0)
        self.assertEqual(r[0]['hosts_down_hard'], 0)
        self.assertEqual(r[0]['hosts_down_soft'], 0)
        self.assertEqual(r[0]['hosts_unreachable_hard'], 0)
        self.assertEqual(r[0]['hosts_unreachable_soft'], 0)
        self.assertEqual(r[0]['hosts_acknowledged'], 1)
        self.assertEqual(r[0]['hosts_in_downtime'], 0)
        self.assertEqual(r[0]['services_total'], 1)
        self.assertEqual(r[0]['services_ok_hard'], 0)
        self.assertEqual(r[0]['services_ok_soft'], 0)
        self.assertEqual(r[0]['services_warning_hard'], 0)
        self.assertEqual(r[0]['services_warning_soft'], 0)
        self.assertEqual(r[0]['services_critical_hard'], 0)
        self.assertEqual(r[0]['services_critical_soft'], 0)
        self.assertEqual(r[0]['services_unknown_hard'], 1)
        self.assertEqual(r[0]['services_unknown_soft'], 0)
        self.assertEqual(r[0]['services_unreachable_hard'], 0)
        self.assertEqual(r[0]['services_unreachable_soft'], 0)
        self.assertEqual(r[0]['services_acknowledged'], 0)
        self.assertEqual(r[0]['services_in_downtime'], 0)

        # remove acknowledge
        time.sleep(1)
        data = {
            'ls_state': 'DOWN',
            'ls_state_id': 1,
            'ls_state_type': 'HARD',
            'ls_last_check': 1465686371,
            'ls_last_state': 'DOWN',
            'ls_last_state_type': 'HARD',
            'ls_output': 'CRITICAL - Plugin timed out after 10 seconds',
            'ls_long_output': '',
            'ls_perf_data': '',
            'ls_acknowledged': False,
            'ls_execution_time': 10.1046719551,
            'ls_latency': 0.926582098
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_host['_etag']
        }
        requests.patch(self.endpoint + '/host/' + ls_host['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        ls_host = copy.copy(r[0])
        # _updated field did not changed...
        self.assertEqual(updated_field, ls_host['_updated'])

        response = requests.get(self.endpoint + '/livesynthesis', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['hosts_total'], 1)
        self.assertEqual(r[0]['hosts_up_hard'], 0)
        self.assertEqual(r[0]['hosts_up_soft'], 0)
        self.assertEqual(r[0]['hosts_down_hard'], 1)
        self.assertEqual(r[0]['hosts_down_soft'], 0)
        self.assertEqual(r[0]['hosts_unreachable_hard'], 0)
        self.assertEqual(r[0]['hosts_unreachable_soft'], 0)
        self.assertEqual(r[0]['hosts_acknowledged'], 0)
        self.assertEqual(r[0]['hosts_in_downtime'], 0)
        self.assertEqual(r[0]['services_total'], 1)
        self.assertEqual(r[0]['services_ok_hard'], 0)
        self.assertEqual(r[0]['services_ok_soft'], 0)
        self.assertEqual(r[0]['services_warning_hard'], 0)
        self.assertEqual(r[0]['services_warning_soft'], 0)
        self.assertEqual(r[0]['services_critical_hard'], 0)
        self.assertEqual(r[0]['services_critical_soft'], 0)
        self.assertEqual(r[0]['services_unknown_hard'], 1)
        self.assertEqual(r[0]['services_unknown_soft'], 0)
        self.assertEqual(r[0]['services_unreachable_hard'], 0)
        self.assertEqual(r[0]['services_unreachable_soft'], 0)
        self.assertEqual(r[0]['services_acknowledged'], 0)
        self.assertEqual(r[0]['services_in_downtime'], 0)

        # we downtime the host
        time.sleep(1)
        data = {
            'ls_state': 'DOWN',
            'ls_state_id': 1,
            'ls_state_type': 'HARD',
            'ls_last_check': 1465686371,
            'ls_last_state': 'DOWN',
            'ls_last_state_type': 'HARD',
            'ls_output': 'CRITICAL - Plugin timed out after 10 seconds',
            'ls_long_output': '',
            'ls_perf_data': '',
            'ls_acknowledged': False,
            'ls_downtimed': True,
            'ls_execution_time': 10.1046719551,
            'ls_latency': 0.926582098
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_host['_etag']
        }
        requests.patch(self.endpoint + '/host/' + ls_host['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        ls_host = copy.copy(r[0])
        # _updated field did not changed...
        self.assertEqual(updated_field, ls_host['_updated'])

        response = requests.get(self.endpoint + '/livesynthesis', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['hosts_total'], 1)
        self.assertEqual(r[0]['hosts_up_hard'], 0)
        self.assertEqual(r[0]['hosts_up_soft'], 0)
        self.assertEqual(r[0]['hosts_down_hard'], 0)
        self.assertEqual(r[0]['hosts_down_soft'], 0)
        self.assertEqual(r[0]['hosts_unreachable_hard'], 0)
        self.assertEqual(r[0]['hosts_unreachable_soft'], 0)
        self.assertEqual(r[0]['hosts_acknowledged'], 0)
        self.assertEqual(r[0]['hosts_in_downtime'], 1)
        self.assertEqual(r[0]['services_total'], 1)
        self.assertEqual(r[0]['services_ok_hard'], 0)
        self.assertEqual(r[0]['services_ok_soft'], 0)
        self.assertEqual(r[0]['services_warning_hard'], 0)
        self.assertEqual(r[0]['services_warning_soft'], 0)
        self.assertEqual(r[0]['services_critical_hard'], 0)
        self.assertEqual(r[0]['services_critical_soft'], 0)
        self.assertEqual(r[0]['services_unknown_hard'], 1)
        self.assertEqual(r[0]['services_unknown_soft'], 0)
        self.assertEqual(r[0]['services_unreachable_hard'], 0)
        self.assertEqual(r[0]['services_unreachable_soft'], 0)
        self.assertEqual(r[0]['services_acknowledged'], 0)
        self.assertEqual(r[0]['services_in_downtime'], 0)

        # remove downtime
        time.sleep(1)
        data = {
            'ls_state': 'DOWN',
            'ls_state_id': 1,
            'ls_state_type': 'HARD',
            'ls_last_check': 1465686371,
            'ls_last_state': 'DOWN',
            'ls_last_state_type': 'HARD',
            'ls_output': 'CRITICAL - Plugin timed out after 10 seconds',
            'ls_long_output': '',
            'ls_perf_data': '',
            'ls_acknowledged': False,
            'ls_downtimed': False,
            'ls_execution_time': 10.1046719551,
            'ls_latency': 0.926582098
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_host['_etag']
        }
        requests.patch(self.endpoint + '/host/' + ls_host['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        ls_host = copy.copy(r[0])
        # _updated field did not changed...
        self.assertEqual(updated_field, ls_host['_updated'])

        response = requests.get(self.endpoint + '/livesynthesis', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['hosts_total'], 1)
        self.assertEqual(r[0]['hosts_up_hard'], 0)
        self.assertEqual(r[0]['hosts_up_soft'], 0)
        self.assertEqual(r[0]['hosts_down_hard'], 1)
        self.assertEqual(r[0]['hosts_down_soft'], 0)
        self.assertEqual(r[0]['hosts_unreachable_hard'], 0)
        self.assertEqual(r[0]['hosts_unreachable_soft'], 0)
        self.assertEqual(r[0]['hosts_acknowledged'], 0)
        self.assertEqual(r[0]['hosts_in_downtime'], 0)
        self.assertEqual(r[0]['services_total'], 1)
        self.assertEqual(r[0]['services_ok_hard'], 0)
        self.assertEqual(r[0]['services_ok_soft'], 0)
        self.assertEqual(r[0]['services_warning_hard'], 0)
        self.assertEqual(r[0]['services_warning_soft'], 0)
        self.assertEqual(r[0]['services_critical_hard'], 0)
        self.assertEqual(r[0]['services_critical_soft'], 0)
        self.assertEqual(r[0]['services_unknown_hard'], 1)
        self.assertEqual(r[0]['services_unknown_soft'], 0)
        self.assertEqual(r[0]['services_unreachable_hard'], 0)
        self.assertEqual(r[0]['services_unreachable_soft'], 0)
        self.assertEqual(r[0]['services_acknowledged'], 0)
        self.assertEqual(r[0]['services_in_downtime'], 0)

    def test_update_service(self):
        """
        Test livesynthesis when updating live state of a service

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
        rc = resp['_items']

        # Add host
        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[0]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']

        # Add service
        data = json.loads(open('cfg/service_srv001_ping.json').read())
        data['host'] = rh[0]['_id']
        data['check_command'] = rc[0]['_id']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)

        # Get service
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        ls_service = copy.copy(r[0])
        updated_field = ls_service['_updated']

        # Get initial live synthesis
        response = requests.get(self.endpoint + '/livesynthesis', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['hosts_total'], 1)
        self.assertEqual(r[0]['hosts_up_hard'], 0)
        self.assertEqual(r[0]['hosts_up_soft'], 0)
        self.assertEqual(r[0]['hosts_down_hard'], 0)
        self.assertEqual(r[0]['hosts_down_soft'], 0)
        self.assertEqual(r[0]['hosts_unreachable_hard'], 1)
        self.assertEqual(r[0]['hosts_unreachable_soft'], 0)
        self.assertEqual(r[0]['hosts_acknowledged'], 0)
        self.assertEqual(r[0]['services_total'], 1)
        self.assertEqual(r[0]['services_ok_hard'], 0)
        self.assertEqual(r[0]['services_ok_soft'], 0)
        self.assertEqual(r[0]['services_warning_hard'], 0)
        self.assertEqual(r[0]['services_warning_soft'], 0)
        self.assertEqual(r[0]['services_critical_hard'], 0)
        self.assertEqual(r[0]['services_critical_soft'], 0)
        self.assertEqual(r[0]['services_unknown_hard'], 1)
        self.assertEqual(r[0]['services_unknown_soft'], 0)
        self.assertEqual(r[0]['services_unreachable_hard'], 0)
        self.assertEqual(r[0]['services_unreachable_soft'], 0)
        self.assertEqual(r[0]['services_acknowledged'], 0)
        self.assertEqual(r[0]['services_in_downtime'], 0)

        # Update something else than the live state for a service
        time.sleep(1)
        data = {
            'alias': 'Updated alias',
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_service['_etag']
        }
        requests.patch(self.endpoint + '/service/' + ls_service['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(
            self.endpoint + '/service/' + ls_service['_id'], params=sort_id, auth=self.auth
        )
        resp = response.json()
        ls_service = resp
        # _updated field did not changed...
        self.assertNotEqual(updated_field, ls_service['_updated'])
        updated_field = ls_service['_updated']

        # Update live state for a service
        # => DOWN SOFT
        time.sleep(1)
        data = {
            'ls_state': 'CRITICAL',
            'ls_state_id': 1,
            'ls_state_type': 'SOFT',
            'ls_last_check': 1465685852,
            'ls_last_state': 'OK',
            'ls_last_state_type': 'HARD',
            'ls_output': 'CRITICAL - Plugin timed out after 10 seconds',
            'ls_long_output': '',
            'ls_perf_data': '',
            'ls_acknowledged': False,
            'ls_execution_time': 10.0598139763,
            'ls_latency': 1.3571469784
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_service['_etag']
        }
        requests.patch(self.endpoint + '/service/' + ls_service['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(
            self.endpoint + '/service/' + ls_service['_id'], params=sort_id, auth=self.auth
        )
        resp = response.json()
        ls_service = resp
        # _updated field did not changed...
        self.assertEqual(updated_field, ls_service['_updated'])

        response = requests.get(self.endpoint + '/livesynthesis', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['hosts_total'], 1)
        self.assertEqual(r[0]['hosts_up_hard'], 0)
        self.assertEqual(r[0]['hosts_up_soft'], 0)
        self.assertEqual(r[0]['hosts_down_hard'], 0)
        self.assertEqual(r[0]['hosts_down_soft'], 0)
        self.assertEqual(r[0]['hosts_unreachable_hard'], 1)
        self.assertEqual(r[0]['hosts_unreachable_soft'], 0)
        self.assertEqual(r[0]['hosts_acknowledged'], 0)
        self.assertEqual(r[0]['services_total'], 1)
        self.assertEqual(r[0]['services_ok_hard'], 0)
        self.assertEqual(r[0]['services_ok_soft'], 0)
        self.assertEqual(r[0]['services_warning_hard'], 0)
        self.assertEqual(r[0]['services_warning_soft'], 0)
        self.assertEqual(r[0]['services_critical_hard'], 0)
        self.assertEqual(r[0]['services_critical_soft'], 1)
        self.assertEqual(r[0]['services_unknown_hard'], 0)
        self.assertEqual(r[0]['services_unknown_soft'], 0)
        self.assertEqual(r[0]['services_unreachable_hard'], 0)
        self.assertEqual(r[0]['services_unreachable_soft'], 0)
        self.assertEqual(r[0]['services_acknowledged'], 0)
        self.assertEqual(r[0]['services_in_downtime'], 0)

        # => DOWN HARD
        time.sleep(1)
        data = {
            'ls_state': 'CRITICAL',
            'ls_state_id': 1,
            'ls_state_type': 'HARD',
            'ls_last_check': 1465685913,
            'ls_last_state': 'DOWN',
            'ls_last_state_type': 'SOFT',
            'ls_output': 'CRITICAL - Plugin timed out after 10 seconds',
            'ls_long_output': '',
            'ls_perf_data': '',
            'ls_acknowledged': False,
            'ls_execution_time': 10.0842711926,
            'ls_latency': 2.0673139095
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_service['_etag']
        }
        requests.patch(self.endpoint + '/service/' + ls_service['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        ls_service = copy.copy(r[0])
        # _updated field did not changed...
        self.assertEqual(updated_field, ls_service['_updated'])

        response = requests.get(self.endpoint + '/livesynthesis', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['hosts_total'], 1)
        self.assertEqual(r[0]['hosts_up_hard'], 0)
        self.assertEqual(r[0]['hosts_up_soft'], 0)
        self.assertEqual(r[0]['hosts_down_hard'], 0)
        self.assertEqual(r[0]['hosts_down_soft'], 0)
        self.assertEqual(r[0]['hosts_unreachable_hard'], 1)
        self.assertEqual(r[0]['hosts_unreachable_soft'], 0)
        self.assertEqual(r[0]['hosts_acknowledged'], 0)
        self.assertEqual(r[0]['services_total'], 1)
        self.assertEqual(r[0]['services_ok_hard'], 0)
        self.assertEqual(r[0]['services_ok_soft'], 0)
        self.assertEqual(r[0]['services_warning_hard'], 0)
        self.assertEqual(r[0]['services_warning_soft'], 0)
        self.assertEqual(r[0]['services_critical_hard'], 1)
        self.assertEqual(r[0]['services_critical_soft'], 0)
        self.assertEqual(r[0]['services_unknown_hard'], 0)
        self.assertEqual(r[0]['services_unknown_soft'], 0)
        self.assertEqual(r[0]['services_unreachable_hard'], 0)
        self.assertEqual(r[0]['services_unreachable_soft'], 0)
        self.assertEqual(r[0]['services_acknowledged'], 0)
        self.assertEqual(r[0]['services_in_downtime'], 0)

        # => last_(state|state_type) are changed
        time.sleep(1)
        data = {
            'ls_state': 'CRITICAL',
            'ls_state_id': 1,
            'ls_state_type': 'HARD',
            'ls_last_check': 1465685971,
            'ls_last_state': 'CRITICAL',
            'ls_last_state_type': 'HARD',
            'ls_output': 'CRITICAL - Plugin timed out after 10 seconds',
            'ls_long_output': '',
            'ls_perf_data': '',
            'ls_acknowledged': False,
            'ls_execution_time': 10.1046719551,
            'ls_latency': 0.926582098
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_service['_etag']
        }
        requests.patch(self.endpoint + '/service/' + ls_service['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        ls_service = copy.copy(r[0])
        # _updated field did not changed...
        self.assertEqual(updated_field, ls_service['_updated'])

        response = requests.get(self.endpoint + '/livesynthesis', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['hosts_total'], 1)
        self.assertEqual(r[0]['hosts_up_hard'], 0)
        self.assertEqual(r[0]['hosts_up_soft'], 0)
        self.assertEqual(r[0]['hosts_down_hard'], 0)
        self.assertEqual(r[0]['hosts_down_soft'], 0)
        self.assertEqual(r[0]['hosts_unreachable_hard'], 1)
        self.assertEqual(r[0]['hosts_unreachable_soft'], 0)
        self.assertEqual(r[0]['hosts_acknowledged'], 0)
        self.assertEqual(r[0]['services_total'], 1)
        self.assertEqual(r[0]['services_ok_hard'], 0)
        self.assertEqual(r[0]['services_ok_soft'], 0)
        self.assertEqual(r[0]['services_warning_hard'], 0)
        self.assertEqual(r[0]['services_warning_soft'], 0)
        self.assertEqual(r[0]['services_critical_hard'], 1)
        self.assertEqual(r[0]['services_critical_soft'], 0)
        self.assertEqual(r[0]['services_unknown_hard'], 0)
        self.assertEqual(r[0]['services_unknown_soft'], 0)
        self.assertEqual(r[0]['services_unreachable_hard'], 0)
        self.assertEqual(r[0]['services_unreachable_soft'], 0)
        self.assertEqual(r[0]['services_acknowledged'], 0)
        self.assertEqual(r[0]['services_in_downtime'], 0)

        # we acknowledge the service
        time.sleep(1)
        data = {
            'ls_state': 'CRITICAL',
            'ls_state_id': 1,
            'ls_state_type': 'HARD',
            'ls_last_check': 1465686371,
            'ls_last_state': 'CRITICAL',
            'ls_last_state_type': 'HARD',
            'ls_output': 'CRITICAL - Plugin timed out after 10 seconds',
            'ls_long_output': '',
            'ls_perf_data': '',
            'ls_acknowledged': True,
            'ls_execution_time': 10.1046719551,
            'ls_latency': 0.926582098
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_service['_etag']
        }
        requests.patch(self.endpoint + '/service/' + ls_service['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        ls_service = copy.copy(r[0])
        # _updated field did not changed...
        self.assertEqual(updated_field, ls_service['_updated'])

        response = requests.get(self.endpoint + '/livesynthesis', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['hosts_total'], 1)
        self.assertEqual(r[0]['hosts_up_hard'], 0)
        self.assertEqual(r[0]['hosts_up_soft'], 0)
        self.assertEqual(r[0]['hosts_down_hard'], 0)
        self.assertEqual(r[0]['hosts_down_soft'], 0)
        self.assertEqual(r[0]['hosts_unreachable_hard'], 1)
        self.assertEqual(r[0]['hosts_unreachable_soft'], 0)
        self.assertEqual(r[0]['hosts_acknowledged'], 0)
        self.assertEqual(r[0]['services_total'], 1)
        self.assertEqual(r[0]['services_ok_hard'], 0)
        self.assertEqual(r[0]['services_ok_soft'], 0)
        self.assertEqual(r[0]['services_warning_hard'], 0)
        self.assertEqual(r[0]['services_warning_soft'], 0)
        self.assertEqual(r[0]['services_critical_hard'], 0)
        self.assertEqual(r[0]['services_critical_soft'], 0)
        self.assertEqual(r[0]['services_unknown_hard'], 0)
        self.assertEqual(r[0]['services_unknown_soft'], 0)
        self.assertEqual(r[0]['services_unreachable_hard'], 0)
        self.assertEqual(r[0]['services_unreachable_soft'], 0)
        self.assertEqual(r[0]['services_acknowledged'], 1)
        self.assertEqual(r[0]['services_in_downtime'], 0)

        # remove acknowledge
        time.sleep(1)
        data = {
            'ls_state': 'CRITICAL',
            'ls_state_id': 1,
            'ls_state_type': 'HARD',
            'ls_last_check': 1465686371,
            'ls_last_state': 'CRITICAL',
            'ls_last_state_type': 'HARD',
            'ls_output': 'CRITICAL - Plugin timed out after 10 seconds',
            'ls_long_output': '',
            'ls_perf_data': '',
            'ls_acknowledged': False,
            'ls_execution_time': 10.1046719551,
            'ls_latency': 0.926582098
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_service['_etag']
        }
        requests.patch(self.endpoint + '/service/' + ls_service['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        ls_service = copy.copy(r[0])
        # _updated field did not changed...
        self.assertEqual(updated_field, ls_service['_updated'])

        response = requests.get(self.endpoint + '/livesynthesis', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['hosts_total'], 1)
        self.assertEqual(r[0]['hosts_up_hard'], 0)
        self.assertEqual(r[0]['hosts_up_soft'], 0)
        self.assertEqual(r[0]['hosts_down_hard'], 0)
        self.assertEqual(r[0]['hosts_down_soft'], 0)
        self.assertEqual(r[0]['hosts_unreachable_hard'], 1)
        self.assertEqual(r[0]['hosts_unreachable_soft'], 0)
        self.assertEqual(r[0]['hosts_acknowledged'], 0)
        self.assertEqual(r[0]['services_total'], 1)
        self.assertEqual(r[0]['services_ok_hard'], 0)
        self.assertEqual(r[0]['services_ok_soft'], 0)
        self.assertEqual(r[0]['services_warning_hard'], 0)
        self.assertEqual(r[0]['services_warning_soft'], 0)
        self.assertEqual(r[0]['services_critical_hard'], 1)
        self.assertEqual(r[0]['services_critical_soft'], 0)
        self.assertEqual(r[0]['services_unknown_hard'], 0)
        self.assertEqual(r[0]['services_unknown_soft'], 0)
        self.assertEqual(r[0]['services_unreachable_hard'], 0)
        self.assertEqual(r[0]['services_unreachable_soft'], 0)
        self.assertEqual(r[0]['services_acknowledged'], 0)
        self.assertEqual(r[0]['services_in_downtime'], 0)

        # we downtime the service
        time.sleep(1)
        data = {
            'ls_state': 'CRITICAL',
            'ls_state_id': 1,
            'ls_state_type': 'HARD',
            'ls_last_check': 1465686371,
            'ls_last_state': 'CRITICAL',
            'ls_last_state_type': 'HARD',
            'ls_output': 'CRITICAL - Plugin timed out after 10 seconds',
            'ls_long_output': '',
            'ls_perf_data': '',
            'ls_acknowledged': False,
            'ls_downtimed': True,
            'ls_execution_time': 10.1046719551,
            'ls_latency': 0.926582098
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_service['_etag']
        }
        requests.patch(self.endpoint + '/service/' + ls_service['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        ls_service = copy.copy(r[0])
        # _updated field did not changed...
        self.assertEqual(updated_field, ls_service['_updated'])

        response = requests.get(self.endpoint + '/livesynthesis', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['hosts_total'], 1)
        self.assertEqual(r[0]['hosts_up_hard'], 0)
        self.assertEqual(r[0]['hosts_up_soft'], 0)
        self.assertEqual(r[0]['hosts_down_hard'], 0)
        self.assertEqual(r[0]['hosts_down_soft'], 0)
        self.assertEqual(r[0]['hosts_unreachable_hard'], 1)
        self.assertEqual(r[0]['hosts_unreachable_soft'], 0)
        self.assertEqual(r[0]['hosts_acknowledged'], 0)
        self.assertEqual(r[0]['hosts_in_downtime'], 0)
        self.assertEqual(r[0]['services_total'], 1)
        self.assertEqual(r[0]['services_ok_hard'], 0)
        self.assertEqual(r[0]['services_ok_soft'], 0)
        self.assertEqual(r[0]['services_warning_hard'], 0)
        self.assertEqual(r[0]['services_warning_soft'], 0)
        self.assertEqual(r[0]['services_critical_hard'], 0)
        self.assertEqual(r[0]['services_critical_soft'], 0)
        self.assertEqual(r[0]['services_unknown_hard'], 0)
        self.assertEqual(r[0]['services_unknown_soft'], 0)
        self.assertEqual(r[0]['services_unreachable_hard'], 0)
        self.assertEqual(r[0]['services_unreachable_soft'], 0)
        self.assertEqual(r[0]['services_acknowledged'], 0)
        self.assertEqual(r[0]['services_in_downtime'], 1)

        # remove downtime
        time.sleep(1)
        data = {
            'ls_state': 'CRITICAL',
            'ls_state_id': 1,
            'ls_state_type': 'HARD',
            'ls_last_check': 1465686371,
            'ls_last_state': 'CRITICAL',
            'ls_last_state_type': 'HARD',
            'ls_output': 'CRITICAL - Plugin timed out after 10 seconds',
            'ls_long_output': '',
            'ls_perf_data': '',
            'ls_acknowledged': False,
            'ls_downtimed': False,
            'ls_execution_time': 10.1046719551,
            'ls_latency': 0.926582098
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_service['_etag']
        }
        requests.patch(self.endpoint + '/service/' + ls_service['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        ls_service = copy.copy(r[0])
        # _updated field did not changed...
        self.assertEqual(updated_field, ls_service['_updated'])

        response = requests.get(self.endpoint + '/livesynthesis', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['hosts_total'], 1)
        self.assertEqual(r[0]['hosts_up_hard'], 0)
        self.assertEqual(r[0]['hosts_up_soft'], 0)
        self.assertEqual(r[0]['hosts_down_hard'], 0)
        self.assertEqual(r[0]['hosts_down_soft'], 0)
        self.assertEqual(r[0]['hosts_unreachable_hard'], 1)
        self.assertEqual(r[0]['hosts_unreachable_soft'], 0)
        self.assertEqual(r[0]['hosts_acknowledged'], 0)
        self.assertEqual(r[0]['hosts_in_downtime'], 0)
        self.assertEqual(r[0]['services_total'], 1)
        self.assertEqual(r[0]['services_ok_hard'], 0)
        self.assertEqual(r[0]['services_ok_soft'], 0)
        self.assertEqual(r[0]['services_warning_hard'], 0)
        self.assertEqual(r[0]['services_warning_soft'], 0)
        self.assertEqual(r[0]['services_critical_hard'], 1)
        self.assertEqual(r[0]['services_critical_soft'], 0)
        self.assertEqual(r[0]['services_unknown_hard'], 0)
        self.assertEqual(r[0]['services_unknown_soft'], 0)
        self.assertEqual(r[0]['services_unreachable_hard'], 0)
        self.assertEqual(r[0]['services_unreachable_soft'], 0)
        self.assertEqual(r[0]['services_acknowledged'], 0)
        self.assertEqual(r[0]['services_in_downtime'], 0)

    def test_hosts_update(self):
        """
        Test all scenarii

        :return: None
        """
        # scenario 1
        original = {
            'ls_state': 'UP',
            'ls_state_type': 'HARD',
        }
        updated = {
            'ls_state': 'DOWN',
            'ls_state_type': 'SOFT'
        }
        minus, plus = Livesynthesis.livesynthesis_to_update('hosts', updated, original)
        self.assertEqual(minus, 'hosts_up_hard')
        self.assertEqual(plus, 'hosts_down_soft')

        # scenario 2
        original = {
            'ls_state': 'UP',
            'ls_state_type': 'SOFT',
        }
        updated = {
            'ls_state': 'DOWN',
        }
        minus, plus = Livesynthesis.livesynthesis_to_update('hosts', updated, original)
        self.assertEqual(minus, 'hosts_up_soft')
        self.assertEqual(plus, 'hosts_down_soft')

        # scenario 3
        original = {
            'ls_state': 'UP',
            'ls_state_type': 'SOFT',
        }
        updated = {
            'ls_state_type': 'HARD',
        }
        minus, plus = Livesynthesis.livesynthesis_to_update('hosts', updated, original)
        self.assertEqual(minus, 'hosts_up_soft')
        self.assertEqual(plus, 'hosts_up_hard')

        # scenario 4
        original = {
            'ls_state': 'UP',
            'ls_state_type': 'SOFT',
        }
        updated = {
        }
        minus, plus = Livesynthesis.livesynthesis_to_update('hosts', updated, original)
        self.assertFalse(minus)
        self.assertFalse(plus)

    def test_realms(self):
        """
        Test livesynthesis create / update with realm management

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}
        # * Add sub_realms A
        data = {"name": "All A", "_parent": self.realm_all}
        response = requests.post(self.endpoint + '/realm', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        realmAll_A_id = copy.copy(resp['_id'])

        # * Add sub_realms B
        data = {"name": "All B", "_parent": self.realm_all}
        response = requests.post(self.endpoint + '/realm', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        realmAll_B_id = copy.copy(resp['_id'])

        # Add command
        data = json.loads(open('cfg/command_ping.json').read())
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)
        # Check if command right in backend
        response = requests.get(self.endpoint + '/command', params=sort_id, auth=self.auth)
        resp = response.json()
        rc = resp['_items']

        # add host in realm All
        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[0]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = self.realm_all
        data['name'] = 'srv001_realmall'
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']

        # Add service
        data = json.loads(open('cfg/service_srv001_ping.json').read())
        data['host'] = rh[0]['_id']
        data['check_command'] = rc[0]['_id']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)

        # add host in realm All A
        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[0]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = realmAll_A_id
        data['name'] = 'srv001_realmallA'
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']

        # Add service
        data = json.loads(open('cfg/service_srv001_ping.json').read())
        data['host'] = rh[0]['_id']
        data['check_command'] = rc[0]['_id']
        data['_realm'] = realmAll_A_id
        requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)

        # add host in realm All B
        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[0]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = realmAll_B_id
        data['name'] = 'srv001_realmallB'
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']

        # Add service
        data = json.loads(open('cfg/service_srv001_ping.json').read())
        data['host'] = rh[0]['_id']
        data['check_command'] = rc[0]['_id']
        data['_realm'] = realmAll_B_id
        requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 3)

        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 3)

        # Now check the livesynthesis (will have 3 entries, one for each realm)
        response = requests.get(self.endpoint + '/livesynthesis', params={'sort': '_realm'},
                                auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 3)
        self.assertEqual(r[0]['_realm'], self.realm_all)
        self.assertEqual(r[1]['_realm'], realmAll_A_id)
        self.assertEqual(r[2]['_realm'], realmAll_B_id)
        for index in range(0, 3):
            self.assertEqual(r[index]['hosts_total'], 1)
            self.assertEqual(r[index]['hosts_up_hard'], 0)
            self.assertEqual(r[index]['hosts_up_soft'], 0)
            self.assertEqual(r[index]['hosts_down_hard'], 0)
            self.assertEqual(r[index]['hosts_down_soft'], 0)
            self.assertEqual(r[index]['hosts_unreachable_hard'], 1)
            self.assertEqual(r[index]['hosts_unreachable_soft'], 0)
            self.assertEqual(r[index]['hosts_acknowledged'], 0)
            self.assertEqual(r[index]['services_total'], 1)
            self.assertEqual(r[index]['services_ok_hard'], 0)
            self.assertEqual(r[index]['services_ok_soft'], 0)
            self.assertEqual(r[index]['services_warning_hard'], 0)
            self.assertEqual(r[index]['services_warning_soft'], 0)
            self.assertEqual(r[index]['services_critical_hard'], 0)
            self.assertEqual(r[index]['services_critical_soft'], 0)
            self.assertEqual(r[index]['services_unknown_hard'], 1)
            self.assertEqual(r[index]['services_unknown_soft'], 0)
            self.assertEqual(r[index]['services_unreachable_hard'], 0)
            self.assertEqual(r[index]['services_unreachable_soft'], 0)

        # update livestate host srv001_realmallA down
        # => DOWN SOFT
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        for host in r:
            if host['_realm'] == realmAll_A_id:
                data = {
                    'ls_state': 'DOWN',
                    'ls_state_id': 1,
                    'ls_state_type': 'SOFT',
                    'ls_last_check': 1465685852,
                    'ls_last_state': 'UP',
                    'ls_last_state_type': 'HARD',
                    'ls_output': 'CRITICAL - Plugin timed out after 10 seconds',
                    'ls_long_output': '',
                    'ls_perf_data': '',
                    'ls_acknowledged': False,
                    'ls_execution_time': 10.0598139763,
                    'ls_latency': 1.3571469784
                }
                headers_patch = {
                    'Content-Type': 'application/json',
                    'If-Match': host['_etag']
                }
                requests.patch(self.endpoint + '/host/' + host['_id'], json=data,
                               headers=headers_patch, auth=self.auth)

                response = requests.get(
                    self.endpoint + '/host/' + host['_id'], params=sort_id, auth=self.auth
                )
                resp = response.json()
                self.assertEqual(resp['_realm'], realmAll_A_id)
                self.assertEqual(resp['ls_state'], 'DOWN')
                self.assertEqual(resp['ls_state_type'], 'SOFT')

        response = requests.get(self.endpoint + '/livesynthesis', params={'sort': '_realm'},
                                auth=self.auth)
        resp = response.json()
        r = resp['_items']
        self.assertEqual(len(r), 3)
        self.assertEqual(r[0]['_realm'], self.realm_all)
        self.assertEqual(r[1]['_realm'], realmAll_A_id)
        self.assertEqual(r[2]['_realm'], realmAll_B_id)
        for ls in r:
            if ls['_realm'] == realmAll_A_id:
                self.assertEqual(ls['hosts_total'], 1)
                self.assertEqual(ls['hosts_up_hard'], 0)
                self.assertEqual(ls['hosts_up_soft'], 0)
                self.assertEqual(ls['hosts_down_hard'], 0)
                self.assertEqual(ls['hosts_down_soft'], 1)
                self.assertEqual(ls['hosts_unreachable_hard'], 0)
                self.assertEqual(ls['hosts_unreachable_soft'], 0)
                self.assertEqual(ls['hosts_acknowledged'], 0)
                self.assertEqual(ls['services_total'], 1)
                self.assertEqual(ls['services_ok_hard'], 0)
                self.assertEqual(ls['services_ok_soft'], 0)
                self.assertEqual(ls['services_warning_hard'], 0)
                self.assertEqual(ls['services_warning_soft'], 0)
                self.assertEqual(ls['services_critical_hard'], 0)
                self.assertEqual(ls['services_critical_soft'], 0)
                self.assertEqual(ls['services_unknown_hard'], 1)
                self.assertEqual(ls['services_unknown_soft'], 0)
                self.assertEqual(ls['services_unreachable_hard'], 0)
                self.assertEqual(ls['services_unreachable_soft'], 0)
            else:
                self.assertEqual(ls['hosts_total'], 1)
                self.assertEqual(ls['hosts_up_hard'], 0)
                self.assertEqual(ls['hosts_up_soft'], 0)
                self.assertEqual(ls['hosts_down_hard'], 0)
                self.assertEqual(ls['hosts_down_soft'], 0)
                self.assertEqual(ls['hosts_unreachable_hard'], 1)
                self.assertEqual(ls['hosts_unreachable_soft'], 0)
                self.assertEqual(ls['hosts_acknowledged'], 0)
                self.assertEqual(ls['services_total'], 1)
                self.assertEqual(ls['services_ok_hard'], 0)
                self.assertEqual(ls['services_ok_soft'], 0)
                self.assertEqual(ls['services_warning_hard'], 0)
                self.assertEqual(ls['services_warning_soft'], 0)
                self.assertEqual(ls['services_critical_hard'], 0)
                self.assertEqual(ls['services_critical_soft'], 0)
                self.assertEqual(ls['services_unknown_hard'], 1)
                self.assertEqual(ls['services_unknown_soft'], 0)
                self.assertEqual(ls['services_unreachable_hard'], 0)
                self.assertEqual(ls['services_unreachable_soft'], 0)
