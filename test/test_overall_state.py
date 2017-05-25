#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This test checks the overall state update
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


class TestOverallState(unittest2.TestCase):
    """This class test the overall stat update"""

    @classmethod
    def setUpClass(cls):
        """This method:
          * deletes mongodb database
          * starts the backend with uwsgi
          * logs in the backend and get the token
          * gets the realm

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
        """Kill uwsgi

        :return: None
        """
        subprocess.call(['uwsgi', '--stop', '/tmp/uwsgi.pid'])
        time.sleep(2)

    @classmethod
    def setUp(cls):
        """Delete resources in backend

        :return: None
        """
        for resource in ['host', 'service', 'command', 'livesynthesis']:
            requests.delete(cls.endpoint + '/' + resource, auth=cls.auth)

    def test_create_host(self):
        """Test host overall state computation when creating an host

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}

        # ---
        # Add command
        data = json.loads(open('cfg/command_ping.json').read())
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)
        # Check if command right in backend
        response = requests.get(self.endpoint + '/command', params=sort_id, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 3)
        rc = resp['_items']

        # ---
        # Add host with some live state data
        data = {
            'name': 'fake_host-1', 'check_command': rc[2]['_id'], '_realm': self.realm_all,
            'ls_state': 'DOWN', 'ls_acknowledged': False, 'ls_downtimed': False
        }
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)

        params = {'where': json.dumps({'name': 'fake_host-1'})}
        response = requests.get(self.endpoint + '/host', params=params, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 1)
        rh = resp['_items']
        # On host insertion, _overall_state_id field is 4, because host is DOWN
        self.assertEqual(4, rh[0]['_overall_state_id'])

        data = {
            'name': 'fake_host-2', 'check_command': rc[2]['_id'], '_realm': self.realm_all,
            'ls_state': 'UNREACHABLE', 'ls_acknowledged': False, 'ls_downtimed': False
        }
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)

        params = {'where': json.dumps({'name': 'fake_host-2'})}
        response = requests.get(self.endpoint + '/host', params=params, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 1)
        rh = resp['_items']
        # On host insertion, _overall_state_id field is 3, because host is UNREACHABLE
        self.assertEqual(3, rh[0]['_overall_state_id'])

        data = {
            'name': 'fake_host-3', 'check_command': rc[2]['_id'], '_realm': self.realm_all,
            'ls_state': 'DOWN', 'ls_acknowledged': False, 'ls_downtimed': True
        }
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)

        params = {'where': json.dumps({'name': 'fake_host-3'})}
        response = requests.get(self.endpoint + '/host', params=params, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 1)
        rh = resp['_items']
        # On host insertion, _overall_state_id field is 2, because host is downtimed
        self.assertEqual(2, rh[0]['_overall_state_id'])

        data = {
            'name': 'fake_host-4', 'check_command': rc[2]['_id'], '_realm': self.realm_all,
            'ls_state': 'UNREACHABLE', 'ls_acknowledged': True, 'ls_downtimed': False
        }
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)

        params = {'where': json.dumps({'name': 'fake_host-4'})}
        response = requests.get(self.endpoint + '/host', params=params, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 1)
        rh = resp['_items']
        # On host insertion, _overall_state_id field is 1, because host is acknowledged
        self.assertEqual(1, rh[0]['_overall_state_id'])

        # ---
        # Add host with default data
        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[2]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        params = {'sort': '_id', 'where': json.dumps({'_is_template': True})}
        response = requests.get(self.endpoint + '/host', params=params, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 1)
        rh = resp['_items']
        # On host insertion, _overall_state_id field is 3, because host is UNREACHABLE
        self.assertEqual(3, rh[0]['_overall_state_id'])

    def test_update_host(self):  # pylint: disable=too-many-locals
        """Test host overall state computation when updating live state of an host

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}

        # ---
        # Add command
        data = json.loads(open('cfg/command_ping.json').read())
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/command', json=data, headers=headers, auth=self.auth)
        # Check if command right in backend
        response = requests.get(self.endpoint + '/command', params=sort_id, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 3)
        rc = resp['_items']

        # ---
        # Add host with default data
        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[2]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        params = {'where': json.dumps({'name': 'srv001'})}
        response = requests.get(self.endpoint + '/host', params=params, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 1)
        rh = resp['_items']
        # On host insertion, _overall_state_id field is 3, because host is UNREACHABLE
        self.assertEqual(3, rh[0]['_overall_state_id'])
        updated = rh[0]['_updated']

        # Add service 1
        data = json.loads(open('cfg/service_srv001_ping.json').read())
        data['host'] = rh[0]['_id']
        data['check_command'] = rc[2]['_id']
        data['_realm'] = self.realm_all
        response = requests.post(self.endpoint + '/service', json=data,
                                 headers=headers, auth=self.auth)
        response = response.json()
        response = requests.get(
            self.endpoint + '/service/' + response['_id'], params=sort_id, auth=self.auth
        )
        ls_service = response.json()
        # On service insertion, _overall_state_id field is 3, because service is UNKNOWN
        self.assertEqual(3, ls_service['_overall_state_id'])

        # Check host
        response = requests.get(self.endpoint + '/host', params=params, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 1)
        rh = resp['_items']
        # Host _overall_state_id did not changed
        self.assertEqual(3, rh[0]['_overall_state_id'])
        new_updated = rh[0]['_updated']
        self.assertEqual(updated, new_updated)

        # Add service 2
        data = json.loads(open('cfg/service_srv002_ping.json').read())
        data['host'] = rh[0]['_id']
        data['check_command'] = rc[2]['_id']
        data['_realm'] = self.realm_all
        response = requests.post(self.endpoint + '/service', json=data,
                                 headers=headers, auth=self.auth)
        responsep = response.json()
        response = requests.get(
            self.endpoint + '/service/' + responsep['_id'], params=sort_id, auth=self.auth
        )
        ls_service = response.json()
        # be sure the _etag return by post is same when get it
        self.assertEqual(responsep['_etag'], ls_service['_etag'])

        # On service insertion, _overall_state_id field is 3, because service is UNKNOWN
        self.assertEqual(3, ls_service['_overall_state_id'])

        # Check host
        response = requests.get(self.endpoint + '/host', params=params, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 1)
        rh = resp['_items']
        # Host _overall_state_id did not changed
        self.assertEqual(3, rh[0]['_overall_state_id'])
        new_updated = rh[0]['_updated']
        self.assertEqual(updated, new_updated)

        # Get all services
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']

        for service in r:
            # Update live state for the service
            # => OK HARD (anyway, only consider HARD state!)
            time.sleep(0.1)
            data = {
                'ls_state': 'OK',
                'ls_state_id': 0,
                'ls_state_type': 'HARD'
            }
            headers_patch = {
                'Content-Type': 'application/json',
                'If-Match': service['_etag']
            }
            requests.patch(self.endpoint + '/service/' + service['_id'], json=data,
                           headers=headers_patch, auth=self.auth)
            response = requests.get(
                self.endpoint + '/service/' + service['_id'], params=sort_id, auth=self.auth
            )
            ls_service = response.json()
            # On service insertion, _overall_state_id field is 3, because service is UNKNOWN
            self.assertEqual(0, ls_service['_overall_state_id'])

        # Get host
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        ls_host = copy.copy(r[1])

        # Initial overall state
        response = requests.get(self.endpoint + '/host/' + ls_host['_id'],
                                params=sort_id, auth=self.auth)
        ls_host = response.json()
        # _overall_state_id field is 3 (unreachable)
        self.assertEqual(3, ls_host['_overall_state_id'])
        new_updated = ls_host['_updated']
        self.assertEqual(updated, new_updated)

        # Update live state for an host
        # => UP SOFT (will fail because we only care about HARD state!)
        time.sleep(0.1)
        data = {
            'ls_state': 'UP',
            'ls_state_id': 0,
            'ls_state_type': 'SOFT',
            'ls_acknowledged': False,
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_host['_etag']
        }
        requests.patch(self.endpoint + '/host/' + ls_host['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(self.endpoint + '/host/' + ls_host['_id'],
                                params=sort_id, auth=self.auth)
        ls_host = response.json()
        # _overall_state_id field did not changed!
        self.assertEqual(3, ls_host['_overall_state_id'])
        new_updated = ls_host['_updated']
        self.assertEqual(updated, new_updated)

        # Update live state for an host
        # => UP HARD (only care about HARD state!)
        time.sleep(0.1)
        data = {
            'ls_state': 'UP',
            'ls_state_id': 0,
            'ls_state_type': 'HARD',
            'ls_acknowledged': False,
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_host['_etag']
        }
        requests.patch(self.endpoint + '/host/' + ls_host['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(self.endpoint + '/host/' + ls_host['_id'],
                                params=sort_id, auth=self.auth)
        ls_host = response.json()
        # _overall_state_id field is 0 (host up)
        self.assertEqual(0, ls_host['_overall_state_id'])
        new_updated = ls_host['_updated']
        self.assertEqual(updated, new_updated)

        # Update live state for an host
        # => UNREACHABLE HARD (only care about HARD state!)
        time.sleep(0.1)
        data = {
            'ls_state': 'UNREACHABLE',
            'ls_state_id': 3,
            'ls_state_type': 'HARD',
            'ls_acknowledged': False,
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_host['_etag']
        }
        requests.patch(self.endpoint + '/host/' + ls_host['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(self.endpoint + '/host/' + ls_host['_id'],
                                params=sort_id, auth=self.auth)
        ls_host = response.json()
        # _overall_state_id field is 3 (host unreachable)
        self.assertEqual(3, ls_host['_overall_state_id'])
        new_updated = ls_host['_updated']
        self.assertEqual(updated, new_updated)

        # Update live state for an host
        # => DOWN HARD (only care about HARD state!)
        time.sleep(0.1)
        data = {
            'ls_state': 'DOWN',
            'ls_state_id': 1,
            'ls_state_type': 'HARD',
            'ls_acknowledged': False,
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_host['_etag']
        }
        requests.patch(self.endpoint + '/host/' + ls_host['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(self.endpoint + '/host/' + ls_host['_id'],
                                params=sort_id, auth=self.auth)
        ls_host = response.json()
        # _overall_state_id field is 4 (host down)
        self.assertEqual(4, ls_host['_overall_state_id'])
        new_updated = ls_host['_updated']
        self.assertEqual(updated, new_updated)

        # we acknowledge the host
        time.sleep(0.1)
        data = {
            'ls_state': 'DOWN',
            'ls_state_id': 1,
            'ls_state_type': 'HARD',
            'ls_acknowledged': True,
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_host['_etag']
        }
        requests.patch(self.endpoint + '/host/' + ls_host['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(self.endpoint + '/host/' + ls_host['_id'],
                                params=sort_id, auth=self.auth)
        ls_host = response.json()
        # _overall_state_id field is 1 (host down and ack)
        self.assertEqual(1, ls_host['_overall_state_id'])
        new_updated = ls_host['_updated']
        self.assertEqual(updated, new_updated)

        # we downtime the host
        time.sleep(0.1)
        data = {
            'ls_state': 'DOWN',
            'ls_state_id': 1,
            'ls_state_type': 'HARD',
            'ls_acknowledged': False,
            'ls_downtimed': True,
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_host['_etag']
        }
        requests.patch(self.endpoint + '/host/' + ls_host['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(self.endpoint + '/host/' + ls_host['_id'],
                                params=sort_id, auth=self.auth)
        ls_host = response.json()
        # _overall_state_id field is 2 (host down and downtimed)
        self.assertEqual(2, ls_host['_overall_state_id'])
        new_updated = ls_host['_updated']
        self.assertEqual(updated, new_updated)

    def test_update_host_and_services(self):
        """Test host overall state computation when updating live state of an host and its services

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

        # Add host
        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[2]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 2)
        rh = resp['_items']

        # Add service 1
        data = json.loads(open('cfg/service_srv001_ping.json').read())
        data['host'] = rh[1]['_id']
        data['check_command'] = rc[2]['_id']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)

        # Add service 2
        data = json.loads(open('cfg/service_srv002_ping.json').read())
        data['host'] = rh[1]['_id']
        data['check_command'] = rc[2]['_id']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)

        # Get all services
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        service_1 = copy.copy(r[0])

        # Update live state for the service 1
        # => OK HARD (anyway, only consider HARD state!)
        time.sleep(0.1)
        data = {
            'ls_state': 'OK',
            'ls_state_id': 0,
            'ls_state_type': 'HARD'
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': service_1['_etag']
        }
        requests.patch(self.endpoint + '/service/' + service_1['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(
            self.endpoint + '/service/' + service_1['_id'], params=sort_id, auth=self.auth
        )
        service_1 = response.json()
        # _overall_state_id field is 0
        self.assertEqual(0, service_1['_overall_state_id'])

        service_2 = copy.copy(r[1])

        # Update live state for the service 2
        # => OK HARD (anyway, only consider HARD state!)
        time.sleep(0.1)
        data = {
            'ls_state': 'OK',
            'ls_state_id': 0,
            'ls_state_type': 'HARD'
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': service_2['_etag']
        }
        requests.patch(self.endpoint + '/service/' + service_2['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(
            self.endpoint + '/service/' + service_2['_id'], params=sort_id, auth=self.auth
        )
        service_2 = response.json()
        # _overall_state_id field is 0
        self.assertEqual(0, service_2['_overall_state_id'])

        # Get host
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        ls_host = copy.copy(r[1])

        # Initial overall state
        response = requests.get(self.endpoint + '/host/' + ls_host['_id'],
                                params=sort_id, auth=self.auth)
        ls_host = response.json()
        # _overall_state_id field is 3 (unreachable)
        self.assertEqual(3, ls_host['_overall_state_id'])
        updated = ls_host['_updated']

        # Update live state for an host
        # => UP HARD (only care about HARD state!)
        time.sleep(0.1)
        data = {
            'ls_state': 'UP',
            'ls_state_id': 0,
            'ls_state_type': 'HARD',
            'ls_acknowledged': False,
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_host['_etag']
        }
        requests.patch(self.endpoint + '/host/' + ls_host['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(self.endpoint + '/host/' + ls_host['_id'],
                                params=sort_id, auth=self.auth)
        ls_host = response.json()
        # _overall_state_id field is 0 (host up)
        self.assertEqual(0, ls_host['_overall_state_id'])
        new_updated = ls_host['_updated']
        self.assertEqual(updated, new_updated)

        # -----
        # Now, we will update the host services and check the host overall state
        # -----

        # Service 1 is OK
        time.sleep(0.1)
        data = {
            'ls_state': 'OK',
            'ls_state_id': 0,
            'ls_state_type': 'HARD',
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': service_1['_etag']
        }
        requests.patch(self.endpoint + '/service/' + service_1['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(
            self.endpoint + '/service/' + service_1['_id'], params=sort_id, auth=self.auth
        )
        service_1 = response.json()
        # _overall_state_id field is 0
        self.assertEqual(0, service_1['_overall_state_id'])

        # Service 2 is WARNING
        time.sleep(0.1)
        data = {
            'ls_state': 'WARNING',
            'ls_state_id': 1,
            'ls_state_type': 'HARD',
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': service_2['_etag']
        }
        requests.patch(self.endpoint + '/service/' + service_2['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(
            self.endpoint + '/service/' + service_2['_id'], params=sort_id, auth=self.auth
        )
        service_2 = response.json()
        # _overall_state_id field is 3
        self.assertEqual(3, service_2['_overall_state_id'])

        # ---
        # Host overall state should be 3 because a service is warning and not ack!
        response = requests.get(self.endpoint + '/host/' + ls_host['_id'],
                                params=sort_id, auth=self.auth)
        ls_host = response.json()
        self.assertEqual(3, ls_host['_overall_state_id'])
        new_updated = ls_host['_updated']
        self.assertEqual(updated, new_updated)

        # Service 2 is still WARNING but ack
        time.sleep(0.1)
        data = {
            'ls_state': 'WARNING',
            'ls_state_id': 1,
            'ls_state_type': 'HARD',
            'ls_acknowledged': True
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': service_2['_etag']
        }
        requests.patch(self.endpoint + '/service/' + service_2['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(
            self.endpoint + '/service/' + service_2['_id'], params=sort_id, auth=self.auth
        )
        service_2 = response.json()
        # _overall_state_id field is 1
        self.assertEqual(1, service_2['_overall_state_id'])

        # ---
        # Host overall state should be 1 because a service is warning but it is ack!
        response = requests.get(self.endpoint + '/host/' + ls_host['_id'],
                                params=sort_id, auth=self.auth)
        ls_host = response.json()
        self.assertEqual(1, ls_host['_overall_state_id'])

        # Service 1 goes CRITICAL
        time.sleep(0.1)
        data = {
            'ls_state': 'CRITICAL',
            'ls_state_id': 1,
            'ls_state_type': 'HARD',
            'ls_acknowledged': False
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': service_1['_etag']
        }
        requests.patch(self.endpoint + '/service/' + service_1['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(
            self.endpoint + '/service/' + service_1['_id'], params=sort_id, auth=self.auth
        )
        service_1 = response.json()
        # _overall_state_id field is 4
        self.assertEqual(4, service_1['_overall_state_id'])

        # ---
        # Host overall state should be 4 because a service is critical and not ack!
        response = requests.get(self.endpoint + '/host/' + ls_host['_id'],
                                params=sort_id, auth=self.auth)
        ls_host = response.json()
        self.assertEqual(4, ls_host['_overall_state_id'])
        new_updated = ls_host['_updated']
        self.assertEqual(updated, new_updated)

        # Service 1 is downtimed
        time.sleep(0.1)
        data = {
            'ls_state': 'CRITICAL',
            'ls_state_id': 1,
            'ls_state_type': 'HARD',
            'ls_downtimed': True
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': service_1['_etag']
        }
        requests.patch(self.endpoint + '/service/' + service_1['_id'], json=data,
                       headers=headers_patch, auth=self.auth)
        response = requests.get(
            self.endpoint + '/service/' + service_1['_id'], params=sort_id, auth=self.auth
        )
        service_1 = response.json()
        # _overall_state_id field is 2
        self.assertEqual(2, service_1['_overall_state_id'])

        # ---
        # Host overall state should be 2 because a service is critical but it is downtimed!
        response = requests.get(self.endpoint + '/host/' + ls_host['_id'],
                                params=sort_id, auth=self.auth)
        ls_host = response.json()
        self.assertEqual(2, ls_host['_overall_state_id'])
        new_updated = ls_host['_updated']
        self.assertEqual(updated, new_updated)

    def test_create_service(self):
        """Test service overall state computation when creating a service

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}

        # Add command
        data = json.loads(open('cfg/command_ping.json').read())
        data['_realm'] = self.realm_all
        response = requests.post(self.endpoint + '/command', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

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
        response = requests.post(self.endpoint + '/host', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']

        # Get host
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        ls_host = copy.copy(r[1])

        # Update live state for the host
        # => UP HARD
        time.sleep(0.1)
        data = {
            'ls_state': 'UP',
            'ls_state_id': 0,
            'ls_state_type': 'HARD',
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_host['_etag']
        }
        response = requests.patch(self.endpoint + '/host/' + ls_host['_id'], json=data,
                                  headers=headers_patch, auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # Add service
        data = {
            'host': rh[1]['_id'], 'check_command': rc[0]['_id'], '_realm': self.realm_all,
            'name': 'fake_service-1', 'ls_state': 'CRITICAL',
            'ls_state_type': 'HARD', 'ls_acknowledged': False, 'ls_downtimed': False
        }
        response = requests.post(self.endpoint + '/service', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # Get service
        params = {'where': json.dumps({'name': 'fake_service-1'})}
        response = requests.get(self.endpoint + '/service', params=params, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 1)
        rs = resp['_items']
        # On service insertion, _overall_state_id field is 4, because service is CRITICAL
        self.assertEqual(4, rs[0]['_overall_state_id'])

        # Add service
        data = {
            'host': rh[1]['_id'], 'check_command': rc[0]['_id'], '_realm': self.realm_all,
            'name': 'fake_service-2', 'ls_state': 'UNREACHABLE',
            'ls_state_type': 'HARD', 'ls_acknowledged': False, 'ls_downtimed': False
        }
        response = requests.post(self.endpoint + '/service', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # Get service
        params = {'where': json.dumps({'name': 'fake_service-2'})}
        response = requests.get(self.endpoint + '/service', params=params, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 1)
        rs = resp['_items']
        # On service insertion, _overall_state_id field is 4, because service is UNREACHABLE
        self.assertEqual(4, rs[0]['_overall_state_id'])

        # Add service
        data = {
            'host': rh[1]['_id'], 'check_command': rc[0]['_id'], '_realm': self.realm_all,
            'name': 'fake_service-3', 'ls_state': 'UNKNOWN',
            'ls_state_type': 'HARD', 'ls_acknowledged': False, 'ls_downtimed': False
        }
        response = requests.post(self.endpoint + '/service', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # Get service
        params = {'where': json.dumps({'name': 'fake_service-3'})}
        response = requests.get(self.endpoint + '/service', params=params, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 1)
        rs = resp['_items']
        # On service insertion, _overall_state_id field is 4, because service is UNKNOWN
        self.assertEqual(3, rs[0]['_overall_state_id'])

        # Add service
        data = {
            'host': rh[1]['_id'], 'check_command': rc[0]['_id'], '_realm': self.realm_all,
            'name': 'fake_service-4', 'ls_state': 'WARNING',
            'ls_state_type': 'HARD', 'ls_acknowledged': False, 'ls_downtimed': False
        }
        response = requests.post(self.endpoint + '/service', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # Get service
        params = {'where': json.dumps({'name': 'fake_service-4'})}
        response = requests.get(self.endpoint + '/service', params=params, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 1)
        rs = resp['_items']
        # On service insertion, _overall_state_id field is 4, because service is WARNING
        self.assertEqual(3, rs[0]['_overall_state_id'])

        # Add service
        data = {
            'host': rh[1]['_id'], 'check_command': rc[0]['_id'], '_realm': self.realm_all,
            'name': 'fake_service-5', 'ls_state': 'OK',
            'ls_state_type': 'HARD', 'ls_acknowledged': False, 'ls_downtimed': False
        }
        response = requests.post(self.endpoint + '/service', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # Get service
        params = {'where': json.dumps({'name': 'fake_service-5'})}
        response = requests.get(self.endpoint + '/service', params=params, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 1)
        rs = resp['_items']
        # On service insertion, _overall_state_id field is 4, because service is OK
        self.assertEqual(0, rs[0]['_overall_state_id'])

        # Add service
        data = {
            'host': rh[1]['_id'], 'check_command': rc[0]['_id'], '_realm': self.realm_all,
            'name': 'fake_service-6', 'ls_state': 'CRITICAL',
            'ls_state_type': 'HARD', 'ls_acknowledged': False, 'ls_downtimed': True
        }
        response = requests.post(self.endpoint + '/service', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # Get service
        params = {'where': json.dumps({'name': 'fake_service-6'})}
        response = requests.get(self.endpoint + '/service', params=params, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 1)
        rs = resp['_items']
        # On service insertion, _overall_state_id field is 4, because service is downtimed
        self.assertEqual(2, rs[0]['_overall_state_id'])

        # Add service
        data = {
            'host': rh[1]['_id'], 'check_command': rc[0]['_id'], '_realm': self.realm_all,
            'name': 'fake_service-7', 'ls_state': 'CRITICAL',
            'ls_state_type': 'HARD', 'ls_acknowledged': True, 'ls_downtimed': False
        }
        response = requests.post(self.endpoint + '/service', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # Get service
        params = {'where': json.dumps({'name': 'fake_service-7'})}
        response = requests.get(self.endpoint + '/service', params=params, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 1)
        rs = resp['_items']
        # On service insertion, _overall_state_id field is 4, because service is acknowledged
        self.assertEqual(1, rs[0]['_overall_state_id'])

    def test_update_service(self):
        """Test service overall state computation when updating live state of a service

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

        # Add host
        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[2]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 2)
        rh = resp['_items']

        # Add service
        data = json.loads(open('cfg/service_srv001_ping.json').read())
        data['host'] = rh[1]['_id']
        data['check_command'] = rc[2]['_id']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)

        # Get host
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        ls_host = copy.copy(r[1])

        # Update live state for the host
        # => UP HARD
        time.sleep(0.1)
        data = {
            'ls_state': 'UP',
            'ls_state_id': 0,
            'ls_state_type': 'HARD',
        }
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': ls_host['_etag']
        }
        requests.patch(self.endpoint + '/host/' + ls_host['_id'], json=data,
                       headers=headers_patch, auth=self.auth)

        # Get service
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        r = resp['_items']
        ls_service = copy.copy(r[0])

        # ---------
        # Update live state for a service
        # => OK HARD (only care about HARD state!)
        time.sleep(0.1)
        data = {
            'ls_state': 'OK',
            'ls_state_id': 0,
            'ls_state_type': 'HARD',
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
        ls_service = response.json()
        # _overall_state_id field is 0
        self.assertEqual(0, ls_service['_overall_state_id'])

        # Get host overall state
        response = requests.get(
            self.endpoint + '/host/' + ls_host['_id'], params=sort_id, auth=self.auth
        )
        ls_host = response.json()
        # _overall_state_id field is 0
        self.assertEqual(0, ls_host['_overall_state_id'])

        # => WARNING HARD (only care about HARD state!)
        time.sleep(0.1)
        data = {
            'ls_state': 'WARNING',
            'ls_state_id': 1,
            'ls_state_type': 'HARD',
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
        ls_service = response.json()
        # _overall_state_id field is 3
        self.assertEqual(3, ls_service['_overall_state_id'])

        # Get host overall state
        response = requests.get(
            self.endpoint + '/host/' + ls_host['_id'], params=sort_id, auth=self.auth
        )
        ls_host = response.json()
        # _overall_state_id field is 3 (at least one service is warning not ack)
        self.assertEqual(3, ls_host['_overall_state_id'])

        # => CRITICAL HARD (only care about HARD state!)
        time.sleep(0.1)
        data = {
            'ls_state': 'CRITICAL',
            'ls_state_id': 2,
            'ls_state_type': 'HARD',
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
        ls_service = response.json()
        # _overall_state_id field is 4
        self.assertEqual(4, ls_service['_overall_state_id'])

        # Get host overall state
        response = requests.get(
            self.endpoint + '/host/' + ls_host['_id'], params=sort_id, auth=self.auth
        )
        ls_host = response.json()
        # _overall_state_id field is 4 (at least one service is critical not ack)
        self.assertEqual(4, ls_host['_overall_state_id'])

        # => UNKNOWN HARD (only care about HARD state!)
        time.sleep(0.1)
        data = {
            'ls_state': 'UNKNOWN',
            'ls_state_id': 3,
            'ls_state_type': 'HARD',
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
        ls_service = response.json()
        # _overall_state_id field is 3
        self.assertEqual(3, ls_service['_overall_state_id'])

        # Get host overall state
        response = requests.get(
            self.endpoint + '/host/' + ls_host['_id'], params=sort_id, auth=self.auth
        )
        ls_host = response.json()
        # _overall_state_id field is 3 (at least one service is unknown not ack)
        self.assertEqual(3, ls_host['_overall_state_id'])

        # => UNREACHABLE HARD (only care about HARD state!)
        time.sleep(0.1)
        data = {
            'ls_state': 'UNREACHABLE',
            'ls_state_id': 4,
            'ls_state_type': 'HARD',
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
        ls_service = response.json()
        # _overall_state_id field is 4
        self.assertEqual(4, ls_service['_overall_state_id'])

        # Get host overall state
        response = requests.get(
            self.endpoint + '/host/' + ls_host['_id'], params=sort_id, auth=self.auth
        )
        ls_host = response.json()
        # _overall_state_id field is 3 (at least one service is unreachable not ack)
        self.assertEqual(4, ls_host['_overall_state_id'])

        # => CRITICAL HARD (only care about HARD state!)
        # AND we acknowledge the service
        time.sleep(0.1)
        data = {
            'ls_state': 'CRITICAL',
            'ls_state_id': 2,
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
        response = requests.get(
            self.endpoint + '/service/' + ls_service['_id'], params=sort_id, auth=self.auth
        )
        ls_service = response.json()
        # _overall_state_id field is 1
        self.assertEqual(1, ls_service['_overall_state_id'])

        # Get host overall state
        response = requests.get(
            self.endpoint + '/host/' + ls_host['_id'], params=sort_id, auth=self.auth
        )
        ls_host = response.json()
        # _overall_state_id field is 1 (at least one service is problem and ack)
        self.assertEqual(1, ls_host['_overall_state_id'])

        # => CRITICAL HARD (only care about HARD state!)
        # AND we downtime the service
        time.sleep(0.1)
        data = {
            'ls_state': 'CRITICAL',
            'ls_state_id': 2,
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
        response = requests.get(
            self.endpoint + '/service/' + ls_service['_id'], params=sort_id, auth=self.auth
        )
        ls_service = response.json()
        # _overall_state_id field is 2
        self.assertEqual(2, ls_service['_overall_state_id'])

        # Get host overall state
        response = requests.get(
            self.endpoint + '/host/' + ls_host['_id'], params=sort_id, auth=self.auth
        )
        ls_host = response.json()
        # _overall_state_id field is 2 (at least one service is problem and downtimed)
        self.assertEqual(2, ls_host['_overall_state_id'])
