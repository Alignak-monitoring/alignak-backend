#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This test check the hostgroups and the tree feature of hostgroups (children)
"""

from __future__ import print_function
import os
import json
import time
from calendar import timegm
from datetime import datetime, timedelta
import shlex
import subprocess
import copy
import requests
import unittest2


class TestActions(unittest2.TestCase):
    """This class test actions features"""

    @classmethod
    def setUpClass(cls):
        """This method:
          * delete mongodb database
          * start the backend with uwsgi
          * log in the backend and get the token
          * get the hostgroup

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

        # Get default realm
        response = requests.get(cls.endpoint + '/realm', auth=cls.auth)
        resp = response.json()
        cls.realm_all = resp['_items'][0]['_id']

        # Get admin user
        response = requests.get(cls.endpoint + '/user', {"name": "admin"}, auth=cls.auth)
        resp = response.json()
        cls.user_admin_id = resp['_items'][0]['_id']
        cls.user_admin = resp['_items'][0]

    @classmethod
    def tearDownClass(cls):
        """
        Kill uwsgi

        :return: None
        """
        subprocess.call(['uwsgi', '--stop', '/tmp/uwsgi.pid'])
        time.sleep(2)

    @classmethod
    def setUp(cls):
        """
        Create/update resources in backend

        :return: None
        """
        headers = {'Content-Type': 'application/json'}

        # Add command
        data = json.loads(open('cfg/command_ping.json').read())
        data['_realm'] = cls.realm_all
        requests.post(cls.endpoint + '/command', json=data, headers=headers, auth=cls.auth)
        response = requests.get(cls.endpoint + '/command?where={"name":"ping"}', auth=cls.auth)
        resp = response.json()
        rc = resp['_items']

        # Add an host
        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[0]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = cls.realm_all
        response = requests.post(cls.endpoint + '/host', json=data, headers=headers, auth=cls.auth)
        resp = response.json()
        response = requests.get(cls.endpoint + '/host?where={"name":"srv001"}', auth=cls.auth)
        resp = response.json()
        rh = resp['_items']

        # Add a service
        data = json.loads(open('cfg/service_srv001_ping.json').read())
        data['host'] = rh[0]['_id']
        data['check_command'] = rc[0]['_id']
        data['_realm'] = cls.realm_all
        requests.post(cls.endpoint + '/service', json=data, headers=headers, auth=cls.auth)

    @classmethod
    def tearDown(cls):
        """
        Delete resources in backend

        :return: None
        """
        response = requests.get(cls.endpoint + '/host', auth=cls.auth)
        resp = response.json()
        for host in resp['_items']:
            if host['name'] in ['srv001']:
                headers = {'If-Match': host['_etag']}
                response = requests.delete(cls.endpoint + '/host/' + host['_id'],
                                           headers=headers, auth=cls.auth)

        for resource in ['service', 'command', 'history',
                         'actionacknowledge', 'actiondowntime', 'actionforcecheck']:
            requests.delete(cls.endpoint + '/' + resource, auth=cls.auth)

    def test_action_acknowledge_host(self):
        # pylint: disable=too-many-locals
        """Test actions: acknowledge host

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}

        # No existing acknowledges
        response = requests.get(
            self.endpoint + '/actionacknowledge', params=sort_id, auth=self.auth
        )
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 0)

        # Get hosts in the backend
        response = requests.get(self.endpoint + '/host', params={'sort': 'name'}, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(len(rh), 2)
        self.assertEqual(rh[0]['name'], "_dummy")
        self.assertEqual(rh[1]['name'], "srv001")
        self.assertEqual(rh[1]['_realm'], self.realm_all)
        self.assertEqual(rh[1]['_sub_realm'], True)

        # -------------------------------------------
        # Add an acknowledge
        data = {
            "action": "add",
            "host": rh[1]['_id'],
            "service": None,
            "sticky": True,
            "persistent": True,
            "notify": True,
            "user": self.user_admin_id,
            "comment": "User comment",
            "_realm": self.realm_all
        }
        response = requests.post(
            self.endpoint + '/actionacknowledge', json=data, headers=headers, auth=self.auth
        )
        resp = response.json()
        self.assertEqual(resp['_status'], 'OK')

        # Get acknowledge
        response = requests.get(
            self.endpoint + '/actionacknowledge', params=sort_id, auth=self.auth
        )
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 1)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['service'], None)
        self.assertEqual(re[0]['action'], 'add')
        self.assertEqual(re[0]['notified'], False)
        self.assertEqual(re[0]['processed'], False)
        self.assertEqual(re[0]['comment'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        # Get history
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 1)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['host_name'], rh[1]['name'])
        self.assertEqual(re[0]['service'], None)
        self.assertEqual(re[0]['service_name'], '')
        self.assertEqual(re[0]['type'], "ack.add")
        self.assertEqual(re[0]['message'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        # -------------------------------------------
        # Delete an acknowledge
        data = {
            "action": "delete",
            "host": rh[1]['_id'],
            "service": None,
            "user": self.user_admin_id,
            "comment": "User comment (delete)",
            "_realm": self.realm_all
        }
        response = requests.post(
            self.endpoint + '/actionacknowledge', json=data, headers=headers, auth=self.auth
        )
        resp = response.json()

        # Get acknowledge
        response = requests.get(
            self.endpoint + '/actionacknowledge', params=sort_id, auth=self.auth
        )
        resp = response.json()
        re = resp['_items']
        ack_id = re[0]['_id']
        ack_etag = re[0]['_etag']
        self.assertEqual(len(re), 2)

        self.assertEqual(re[0]['action'], 'add')
        self.assertEqual(re[0]['processed'], False)
        self.assertEqual(re[0]['comment'], "User comment")
        self.assertEqual(re[1]['action'], 'delete')
        self.assertEqual(re[1]['processed'], False)
        self.assertEqual(re[1]['comment'], "User comment (delete)")

        # Get history
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 2)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['host_name'], rh[1]['name'])
        self.assertEqual(re[0]['service'], None)
        self.assertEqual(re[0]['service_name'], '')
        self.assertEqual(re[0]['type'], "ack.add")
        self.assertEqual(re[0]['message'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], rh[1]['name'])
        self.assertEqual(re[1]['service'], None)
        self.assertEqual(re[1]['service_name'], '')
        self.assertEqual(re[1]['type'], "ack.delete")
        self.assertEqual(re[1]['message'], "User comment (delete)")
        self.assertEqual(re[1]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[1]['_sub_realm'], rh[1]['_sub_realm'])

        # -------------------------------------------
        # Update an acknowledge (processed)
        data = {'processed': True}
        headers = {
            'Content-Type': 'application/json',
            'If-Match': ack_etag
        }
        response = requests.patch(self.endpoint + '/actionacknowledge/' + ack_id, json=data,
                                  headers=headers, auth=self.auth)
        self.assertEqual(response.status_code, 200)
        resp = response.json()

        # Get history
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 3)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['host_name'], rh[1]['name'])
        self.assertEqual(re[0]['service'], None)
        self.assertEqual(re[0]['service_name'], '')
        self.assertEqual(re[0]['type'], "ack.add")
        self.assertEqual(re[0]['message'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], rh[1]['name'])
        self.assertEqual(re[1]['service'], None)
        self.assertEqual(re[1]['service_name'], '')
        self.assertEqual(re[1]['type'], "ack.delete")
        self.assertEqual(re[1]['message'], "User comment (delete)")
        self.assertEqual(re[1]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[1]['_sub_realm'], rh[1]['_sub_realm'])

        # One more event
        self.assertEqual(re[2]['host'], rh[1]['_id'])
        self.assertEqual(re[2]['host_name'], rh[1]['name'])
        self.assertEqual(re[2]['service'], None)
        self.assertEqual(re[2]['service_name'], '')
        self.assertEqual(re[2]['type'], "ack.processed")
        self.assertEqual(re[2]['message'], "User comment")
        self.assertEqual(re[2]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[2]['_sub_realm'], rh[1]['_sub_realm'])

    def test_action_acknowledge_service(self):
        # pylint: disable=too-many-locals
        """Test actions: acknowledge service

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}

        # No existing acknowledges
        response = requests.get(
            self.endpoint + '/actionacknowledge', params=sort_id, auth=self.auth
        )
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 0)

        # Get hosts in the backend
        response = requests.get(self.endpoint + '/host', params={'sort': 'name'}, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(len(rh), 2)
        self.assertEqual(rh[0]['name'], "_dummy")
        self.assertEqual(rh[1]['name'], "srv001")
        self.assertEqual(rh[1]['_realm'], self.realm_all)
        self.assertEqual(rh[1]['_sub_realm'], True)

        # Get service in the backend
        response = requests.get(self.endpoint + '/service', auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(rs[0]['name'], "ping")

        # -------------------------------------------
        # Add an acknowledge
        data = {
            "action": "add",
            "host": rh[1]['_id'],
            "service": rs[0]['_id'],
            "sticky": True,
            "persistent": True,
            "notify": True,
            "user": self.user_admin_id,
            "comment": "User comment",
            "_realm": self.realm_all
        }
        response = requests.post(
            self.endpoint + '/actionacknowledge', json=data, headers=headers, auth=self.auth
        )
        resp = response.json()
        self.assertEqual(resp['_status'], 'OK')

        # Get acknowledge
        response = requests.get(
            self.endpoint + '/actionacknowledge', params=sort_id, auth=self.auth
        )
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 1)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['service'], rs[0]['_id'])
        self.assertEqual(re[0]['action'], 'add')
        self.assertEqual(re[0]['notified'], False)
        self.assertEqual(re[0]['processed'], False)
        self.assertEqual(re[0]['comment'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        # Get history
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 1)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['host_name'], rh[1]['name'])
        self.assertEqual(re[0]['service'], rs[0]['_id'])
        self.assertEqual(re[0]['service_name'], rs[0]['name'])
        self.assertEqual(re[0]['type'], "ack.add")
        self.assertEqual(re[0]['message'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        # -------------------------------------------
        # Delete an acknowledge
        data = {
            "action": "delete",
            "host": rh[1]['_id'],
            "service": rs[0]['_id'],
            "user": self.user_admin_id,
            "comment": "User comment (delete)",
            "_realm": self.realm_all
        }
        response = requests.post(
            self.endpoint + '/actionacknowledge', json=data, headers=headers, auth=self.auth
        )
        resp = response.json()

        # Get acknowledge
        response = requests.get(
            self.endpoint + '/actionacknowledge', params=sort_id, auth=self.auth
        )
        resp = response.json()
        re = resp['_items']
        ack_id = re[0]['_id']
        ack_etag = re[0]['_etag']
        self.assertEqual(len(re), 2)

        self.assertEqual(re[0]['action'], 'add')
        self.assertEqual(re[0]['processed'], False)
        self.assertEqual(re[0]['comment'], "User comment")
        self.assertEqual(re[1]['action'], 'delete')
        self.assertEqual(re[1]['processed'], False)
        self.assertEqual(re[1]['comment'], "User comment (delete)")

        # Get history
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 2)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['host_name'], rh[1]['name'])
        self.assertEqual(re[0]['service'], rs[0]['_id'])
        self.assertEqual(re[0]['service_name'], rs[0]['name'])
        self.assertEqual(re[0]['type'], "ack.add")
        self.assertEqual(re[0]['message'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], rh[1]['name'])
        self.assertEqual(re[1]['service'], rs[0]['_id'])
        self.assertEqual(re[1]['service_name'], rs[0]['name'])
        self.assertEqual(re[1]['type'], "ack.delete")
        self.assertEqual(re[1]['message'], "User comment (delete)")
        self.assertEqual(re[1]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[1]['_sub_realm'], rh[1]['_sub_realm'])

        # -------------------------------------------
        # Update an acknowledge (processed)
        data = {'processed': True}
        headers = {
            'Content-Type': 'application/json',
            'If-Match': ack_etag
        }
        response = requests.patch(self.endpoint + '/actionacknowledge/' + ack_id, json=data,
                                  headers=headers, auth=self.auth)
        self.assertEqual(response.status_code, 200)
        resp = response.json()

        # Get history
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 3)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['host_name'], rh[1]['name'])
        self.assertEqual(re[0]['service'], rs[0]['_id'])
        self.assertEqual(re[0]['service_name'], rs[0]['name'])
        self.assertEqual(re[0]['type'], "ack.add")
        self.assertEqual(re[0]['message'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], rh[1]['name'])
        self.assertEqual(re[1]['service'], rs[0]['_id'])
        self.assertEqual(re[1]['service_name'], rs[0]['name'])
        self.assertEqual(re[1]['type'], "ack.delete")
        self.assertEqual(re[1]['message'], "User comment (delete)")
        self.assertEqual(re[1]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[1]['_sub_realm'], rh[1]['_sub_realm'])

        # One more event
        self.assertEqual(re[2]['host'], rh[1]['_id'])
        self.assertEqual(re[2]['host_name'], rh[1]['name'])
        self.assertEqual(re[2]['service'], rs[0]['_id'])
        self.assertEqual(re[2]['service_name'], rs[0]['name'])
        self.assertEqual(re[2]['type'], "ack.processed")
        self.assertEqual(re[2]['message'], "User comment")
        self.assertEqual(re[2]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[2]['_sub_realm'], rh[1]['_sub_realm'])

    def test_action_downtime_host(self):
        # pylint: disable=too-many-locals
        """Test actions: downtime service

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}

        # No existing downtimes
        response = requests.get(
            self.endpoint + '/actiondowntime', params=sort_id, auth=self.auth
        )
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 0)

        # Get hosts in the backend
        response = requests.get(self.endpoint + '/host', params={'sort': 'name'}, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(len(rh), 2)
        self.assertEqual(rh[0]['name'], "_dummy")
        self.assertEqual(rh[1]['name'], "srv001")
        self.assertEqual(rh[1]['_realm'], self.realm_all)
        self.assertEqual(rh[1]['_sub_realm'], True)

        # -------------------------------------------
        # Add a downtime
        now = datetime.utcnow()
        later = now + timedelta(days=2, hours=4, minutes=3, seconds=12)
        now = timegm(now.timetuple())
        later = timegm(later.timetuple())
        print("Now: %s, %s" % (now, later))
        data = {
            "action": "add",
            "host": rh[1]['_id'],
            "service": None,
            "start_time": now,
            "end_time": later,
            "fixed": True,
            "user": self.user_admin_id,
            "comment": "User comment",
            "_realm": self.realm_all
        }
        response = requests.post(
            self.endpoint + '/actiondowntime', json=data, headers=headers, auth=self.auth
        )
        print(response)
        resp = response.json()
        print(resp)
        self.assertEqual(resp['_status'], 'OK')

        # Get downtime
        response = requests.get(
            self.endpoint + '/actiondowntime', params=sort_id, auth=self.auth
        )
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 1)

        self.assertEqual(re[0]['action'], 'add')
        self.assertEqual(re[0]['processed'], False)
        self.assertEqual(re[0]['notified'], False)
        self.assertEqual(re[0]['processed'], False)
        self.assertEqual(re[0]['comment'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        # Get history
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 1)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['host_name'], rh[1]['name'])
        self.assertEqual(re[0]['service'], None)
        self.assertEqual(re[0]['service_name'], '')
        self.assertEqual(re[0]['type'], "downtime.add")
        self.assertEqual(re[0]['message'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        # -------------------------------------------
        # Delete a downtime
        data = {
            "action": "delete",
            "host": rh[1]['_id'],
            "service": None,
            "user": self.user_admin_id,
            "comment": "User comment (delete)",
            "_realm": self.realm_all
        }
        response = requests.post(
            self.endpoint + '/actiondowntime', json=data, headers=headers, auth=self.auth
        )
        resp = response.json()
        print(resp)

        # Get downtime
        response = requests.get(
            self.endpoint + '/actiondowntime', params=sort_id, auth=self.auth
        )
        resp = response.json()
        re = resp['_items']
        dwn_id = re[0]['_id']
        dwn_etag = re[0]['_etag']
        self.assertEqual(len(re), 2)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['action'], 'add')
        self.assertEqual(re[0]['processed'], False)
        self.assertEqual(re[0]['comment'], "User comment")

        self.assertEqual(re[1]['action'], 'delete')
        self.assertEqual(re[1]['processed'], False)
        self.assertEqual(re[1]['comment'], "User comment (delete)")

        # Get history
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 2)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['host_name'], rh[1]['name'])
        self.assertEqual(re[0]['service'], None)
        self.assertEqual(re[0]['service_name'], '')
        self.assertEqual(re[0]['type'], "downtime.add")
        self.assertEqual(re[0]['message'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], rh[1]['name'])
        self.assertEqual(re[1]['service'], None)
        self.assertEqual(re[1]['service_name'], '')
        self.assertEqual(re[1]['type'], "downtime.delete")
        self.assertEqual(re[1]['message'], "User comment (delete)")
        self.assertEqual(re[1]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[1]['_sub_realm'], rh[1]['_sub_realm'])

        # -------------------------------------------
        # Update a downtime (processed)
        data = {'processed': True}
        headers = {
            'Content-Type': 'application/json',
            'If-Match': dwn_etag
        }
        print("Downtime: %s" % self.endpoint + '/actiondowntime/' + dwn_id)
        response = requests.patch(self.endpoint + '/actiondowntime/' + dwn_id, json=data,
                                  headers=headers, auth=self.auth)
        # self.assertEqual(response.status_code, 200)
        resp = response.json()

        # Get history
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 3)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['host_name'], rh[1]['name'])
        self.assertEqual(re[0]['service'], None)
        self.assertEqual(re[0]['service_name'], '')
        self.assertEqual(re[0]['type'], "downtime.add")
        self.assertEqual(re[0]['message'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], rh[1]['name'])
        self.assertEqual(re[1]['service'], None)
        self.assertEqual(re[1]['service_name'], '')
        self.assertEqual(re[1]['type'], "downtime.delete")
        self.assertEqual(re[1]['message'], "User comment (delete)")
        self.assertEqual(re[1]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[1]['_sub_realm'], rh[1]['_sub_realm'])

        # One more event
        self.assertEqual(re[2]['host'], rh[1]['_id'])
        self.assertEqual(re[2]['host_name'], rh[1]['name'])
        self.assertEqual(re[2]['service'], None)
        self.assertEqual(re[2]['service_name'], '')
        self.assertEqual(re[2]['type'], "downtime.processed")
        self.assertEqual(re[2]['message'], "User comment")
        self.assertEqual(re[2]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[2]['_sub_realm'], rh[1]['_sub_realm'])

    def test_action_downtime_service(self):
        # pylint: disable=too-many-locals
        """Test actions: downtime service

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}

        # No existing downtimes
        response = requests.get(
            self.endpoint + '/actiondowntime', params=sort_id, auth=self.auth
        )
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 0)

        # Get hosts in the backend
        response = requests.get(self.endpoint + '/host', params={'sort': 'name'}, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(len(rh), 2)
        self.assertEqual(rh[0]['name'], "_dummy")
        self.assertEqual(rh[1]['name'], "srv001")
        self.assertEqual(rh[1]['_realm'], self.realm_all)
        self.assertEqual(rh[1]['_sub_realm'], True)

        # Get service in the backend
        response = requests.get(self.endpoint + '/service', auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(rs[0]['name'], "ping")

        # -------------------------------------------
        # Add a downtime
        now = datetime.utcnow()
        later = now + timedelta(days=2, hours=4, minutes=3, seconds=12)
        now = timegm(now.timetuple())
        later = timegm(later.timetuple())
        print("Now: %s, %s" % (now, later))
        data = {
            "action": "add",
            "host": rh[1]['_id'],
            "service": rs[0]['_id'],
            "start_time": now,
            "end_time": later,
            "fixed": True,
            "user": self.user_admin_id,
            "comment": "User comment",
            "_realm": self.realm_all
        }
        response = requests.post(
            self.endpoint + '/actiondowntime', json=data, headers=headers, auth=self.auth
        )
        print(response)
        resp = response.json()
        print(resp)
        self.assertEqual(resp['_status'], 'OK')

        # Get downtime
        response = requests.get(
            self.endpoint + '/actiondowntime', params=sort_id, auth=self.auth
        )
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 1)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['action'], 'add')
        self.assertEqual(re[0]['notified'], False)
        self.assertEqual(re[0]['processed'], False)
        self.assertEqual(re[0]['comment'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        # Get history
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 1)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['host_name'], rh[1]['name'])
        self.assertEqual(re[0]['service'], rs[0]['_id'])
        self.assertEqual(re[0]['service_name'], rs[0]['name'])
        self.assertEqual(re[0]['type'], "downtime.add")
        self.assertEqual(re[0]['message'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        # -------------------------------------------
        # Delete a downtime
        data = {
            "action": "delete",
            "host": rh[1]['_id'],
            "service": rs[0]['_id'],
            "user": self.user_admin_id,
            "comment": "User comment (delete)",
            "_realm": self.realm_all
        }
        response = requests.post(
            self.endpoint + '/actiondowntime', json=data, headers=headers, auth=self.auth
        )
        resp = response.json()
        print(resp)

        # Get downtime
        response = requests.get(
            self.endpoint + '/actiondowntime', params=sort_id, auth=self.auth
        )
        resp = response.json()
        re = resp['_items']
        dwn_id = re[0]['_id']
        dwn_etag = re[0]['_etag']
        self.assertEqual(len(re), 2)

        self.assertEqual(re[0]['action'], 'add')
        self.assertEqual(re[0]['processed'], False)
        self.assertEqual(re[0]['comment'], "User comment")

        self.assertEqual(re[1]['action'], 'delete')
        self.assertEqual(re[1]['processed'], False)
        self.assertEqual(re[1]['comment'], "User comment (delete)")

        # Get history
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 2)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['host_name'], rh[1]['name'])
        self.assertEqual(re[0]['service'], rs[0]['_id'])
        self.assertEqual(re[0]['service_name'], rs[0]['name'])
        self.assertEqual(re[0]['type'], "downtime.add")
        self.assertEqual(re[0]['message'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], rh[1]['name'])
        self.assertEqual(re[1]['service'], rs[0]['_id'])
        self.assertEqual(re[1]['service_name'], rs[0]['name'])
        self.assertEqual(re[1]['type'], "downtime.delete")
        self.assertEqual(re[1]['message'], "User comment (delete)")
        self.assertEqual(re[1]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[1]['_sub_realm'], rh[1]['_sub_realm'])
        self.assertEqual(re[1]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[1]['_sub_realm'], rh[1]['_sub_realm'])

        # -------------------------------------------
        # Update a downtime (processed)
        data = {'processed': True}
        headers = {
            'Content-Type': 'application/json',
            'If-Match': dwn_etag
        }
        print("Downtime: %s" % self.endpoint + '/actiondowntime/' + dwn_id)
        response = requests.patch(self.endpoint + '/actiondowntime/' + dwn_id, json=data,
                                  headers=headers, auth=self.auth)
        # self.assertEqual(response.status_code, 200)
        resp = response.json()

        # Get history
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 3)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['host_name'], rh[1]['name'])
        self.assertEqual(re[0]['service'], rs[0]['_id'])
        self.assertEqual(re[0]['service_name'], rs[0]['name'])
        self.assertEqual(re[0]['type'], "downtime.add")
        self.assertEqual(re[0]['message'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], rh[1]['name'])
        self.assertEqual(re[1]['service'], rs[0]['_id'])
        self.assertEqual(re[1]['service_name'], rs[0]['name'])
        self.assertEqual(re[1]['type'], "downtime.delete")
        self.assertEqual(re[1]['message'], "User comment (delete)")
        self.assertEqual(re[1]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[1]['_sub_realm'], rh[1]['_sub_realm'])

        # One more event
        self.assertEqual(re[2]['host'], rh[1]['_id'])
        self.assertEqual(re[2]['host_name'], rh[1]['name'])
        self.assertEqual(re[2]['service'], rs[0]['_id'])
        self.assertEqual(re[2]['service_name'], rs[0]['name'])
        self.assertEqual(re[2]['type'], "downtime.processed")
        self.assertEqual(re[2]['message'], "User comment")
        self.assertEqual(re[2]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[2]['_sub_realm'], rh[1]['_sub_realm'])

    def test_action_forcecheck_host(self):
        # pylint: disable=too-many-locals
        """Test actions: forcecheck service

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}

        # No existing forcechecks
        response = requests.get(
            self.endpoint + '/actionforcecheck', params=sort_id, auth=self.auth
        )
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 0)

        # Get hosts in the backend
        response = requests.get(self.endpoint + '/host', params={'sort': 'name'}, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(len(rh), 2)
        self.assertEqual(rh[0]['name'], "_dummy")
        self.assertEqual(rh[1]['name'], "srv001")
        self.assertEqual(rh[1]['_realm'], self.realm_all)
        self.assertEqual(rh[1]['_sub_realm'], True)

        # -------------------------------------------
        # Add a forcecheck
        data = {
            "host": rh[1]['_id'],
            "service": None,
            "user": self.user_admin_id,
            "comment": "User comment",
            "_realm": self.realm_all
        }
        response = requests.post(
            self.endpoint + '/actionforcecheck', json=data, headers=headers, auth=self.auth
        )
        resp = response.json()
        self.assertEqual(resp['_status'], 'OK')

        # Get forcecheck
        response = requests.get(
            self.endpoint + '/actionforcecheck', params=sort_id, auth=self.auth
        )
        resp = response.json()
        re = resp['_items']
        fck_id = re[0]['_id']
        fck_etag = re[0]['_etag']
        self.assertEqual(len(re), 1)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['processed'], False)
        self.assertEqual(re[0]['comment'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        # Get history
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 1)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['service'], None)
        self.assertEqual(re[0]['type'], "check.request")
        self.assertEqual(re[0]['message'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        # -------------------------------------------
        # Update an forcecheck (processed)
        data = {'processed': True}
        headers = {
            'Content-Type': 'application/json',
            'If-Match': fck_etag
        }
        response = requests.patch(self.endpoint + '/actionforcecheck/' + fck_id, json=data,
                                  headers=headers, auth=self.auth)
        self.assertEqual(response.status_code, 200)
        resp = response.json()

        # Get history
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 2)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['host_name'], rh[1]['name'])
        self.assertEqual(re[0]['service'], None)
        self.assertEqual(re[0]['service_name'], '')
        self.assertEqual(re[0]['type'], "check.request")
        self.assertEqual(re[0]['message'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], rh[1]['name'])
        self.assertEqual(re[1]['service'], None)
        self.assertEqual(re[1]['service_name'], '')
        self.assertEqual(re[1]['type'], "check.requested")
        self.assertEqual(re[1]['message'], "User comment")
        self.assertEqual(re[1]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[1]['_sub_realm'], rh[1]['_sub_realm'])

    def test_action_forcecheck_service(self):
        # pylint: disable=too-many-locals
        """Test actions: forcecheck service

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}

        # No existing forcechecks
        response = requests.get(
            self.endpoint + '/actionforcecheck', params=sort_id, auth=self.auth
        )
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 0)

        # Get hosts in the backend
        response = requests.get(self.endpoint + '/host', params={'sort': 'name'}, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(len(rh), 2)
        self.assertEqual(rh[0]['name'], "_dummy")
        self.assertEqual(rh[1]['name'], "srv001")
        self.assertEqual(rh[1]['_realm'], self.realm_all)
        self.assertEqual(rh[1]['_sub_realm'], True)

        # Get service in the backend
        response = requests.get(self.endpoint + '/service', auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(rs[0]['name'], "ping")

        # -------------------------------------------
        # Add a forcecheck
        data = {
            "host": rh[1]['_id'],
            "service": rs[0]['_id'],
            "user": self.user_admin_id,
            "comment": "User comment",
            "_realm": self.realm_all
        }
        response = requests.post(
            self.endpoint + '/actionforcecheck', json=data, headers=headers, auth=self.auth
        )
        resp = response.json()
        self.assertEqual(resp['_status'], 'OK')

        # Get forcecheck
        response = requests.get(
            self.endpoint + '/actionforcecheck', params=sort_id, auth=self.auth
        )
        resp = response.json()
        re = resp['_items']
        fck_id = re[0]['_id']
        fck_etag = re[0]['_etag']
        self.assertEqual(len(re), 1)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['processed'], False)
        self.assertEqual(re[0]['comment'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        # Get history
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 1)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['service'], rs[0]['_id'])
        self.assertEqual(re[0]['type'], "check.request")
        self.assertEqual(re[0]['message'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        # -------------------------------------------
        # Update an forcecheck (processed)
        data = {'processed': True}
        headers = {
            'Content-Type': 'application/json',
            'If-Match': fck_etag
        }
        response = requests.patch(self.endpoint + '/actionforcecheck/' + fck_id, json=data,
                                  headers=headers, auth=self.auth)
        self.assertEqual(response.status_code, 200)
        resp = response.json()

        # Get history
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 2)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['host_name'], rh[1]['name'])
        self.assertEqual(re[0]['service'], rs[0]['_id'])
        self.assertEqual(re[0]['service_name'], rs[0]['name'])
        self.assertEqual(re[0]['type'], "check.request")
        self.assertEqual(re[0]['message'], "User comment")
        self.assertEqual(re[0]['_realm'], rh[1]['_realm'])
        self.assertEqual(re[0]['_sub_realm'], rh[1]['_sub_realm'])

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], rh[1]['name'])
        self.assertEqual(re[1]['service'], rs[0]['_id'])
        self.assertEqual(re[1]['service_name'], rs[0]['name'])
        self.assertEqual(re[1]['type'], "check.requested")
        self.assertEqual(re[1]['message'], "User comment")

    def test_history_comment(self):
        """
        Test history: add user comment

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}

        # No existing forcechecks
        response = requests.get(
            self.endpoint + '/history', params=sort_id, auth=self.auth
        )
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 0)

        # Get hosts in the backend
        response = requests.get(self.endpoint + '/host', params={'sort': 'name'}, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(len(rh), 2)
        self.assertEqual(rh[0]['name'], "_dummy")
        self.assertEqual(rh[1]['name'], "srv001")

        # Get service in the backend
        response = requests.get(self.endpoint + '/service', auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(rs[0]['name'], "ping")

        # -------------------------------------------
        # Add an history comment
        data = {
            "host": rh[1]['_id'],
            "service": rs[0]['_id'],
            "user": self.user_admin_id,
            "type": "webui.comment",
            "message": "User comment",
            "_realm": self.realm_all
        }
        response = requests.post(
            self.endpoint + '/history', json=data, headers=headers, auth=self.auth
        )
        resp = response.json()
        self.assertEqual(resp['_status'], 'OK')

        # Get history
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 1)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['host_name'], rh[1]['name'])
        self.assertEqual(re[0]['service'], rs[0]['_id'])
        self.assertEqual(re[0]['service_name'], rs[0]['name'])
        self.assertEqual(re[0]['user'], self.user_admin_id)
        self.assertEqual(re[0]['user_name'], 'admin')
        self.assertEqual(re[0]['type'], "webui.comment")
        self.assertEqual(re[0]['message'], "User comment")
        self.assertEqual(re[0]['_realm'], self.realm_all)

        # -------------------------------------------
        # Add an history comment - host_name, service_name and user_name
        data = {
            "host_name": rh[1]['name'],
            "service_name": rs[0]['name'],
            "user_name": "admin",
            "type": "webui.comment",
            "message": "User comment 2",
        }
        response = requests.post(
            self.endpoint + '/history', json=data, headers=headers, auth=self.auth
        )
        resp = response.json()
        self.assertEqual(resp['_status'], 'OK')

        # Get history
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 2)
        print("History 0: %s" % re[0])
        print("History 1: %s" % re[1])

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], 'srv001')
        self.assertEqual(re[1]['service'], rs[0]['_id'])
        self.assertEqual(re[1]['service_name'], rs[0]['name'])
        self.assertEqual(re[1]['user'], self.user_admin_id)
        self.assertEqual(re[1]['user_name'], 'admin')
        self.assertEqual(re[1]['type'], "webui.comment")
        self.assertEqual(re[1]['message'], "User comment 2")
        self.assertEqual(re[1]['_realm'], self.realm_all)

    def test_actions_not_allowed(self):
        """
        Test post/update/delete actions when not have the right 'can_submit_commands' in user
        resource

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        # create a new user
        data = {'name': 'user1', 'password': 'test', 'back_role_super_admin': True,
                'host_notification_period': self.user_admin['host_notification_period'],
                'service_notification_period': self.user_admin['service_notification_period'],
                '_realm': self.realm_all}
        requests.post(self.endpoint + '/user', json=data, headers=headers, auth=self.auth)

        params = {'username': 'user1', 'password': 'test', 'action': 'generate'}
        # get token user 1
        response = requests.post(self.endpoint + '/login', json=params, headers=headers)
        resp = response.json()
        user1_auth = requests.auth.HTTPBasicAuth(resp['token'], '')

        # get host
        response = requests.get(self.endpoint + '/host', params={'sort': 'name'}, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertEqual(len(rh), 2)
        self.assertEqual(rh[0]['name'], "_dummy")
        self.assertEqual(rh[1]['name'], "srv001")

        # try post a new action
        data = {
            "action": "add",
            "host": rh[1]['_id'],
            "service": None,
            "sticky": True,
            "persistent": True,
            "notify": True,
            "user": self.user_admin_id,
            "comment": "User comment",
            "_realm": self.realm_all
        }
        response = requests.post(
            self.endpoint + '/actionacknowledge', json=data, headers=headers, auth=user1_auth
        )
        assert response.status_code == 403

        # add a new action
        response = requests.post(
            self.endpoint + '/actionacknowledge', json=data, headers=headers, auth=self.auth
        )
        assert response.status_code == 201
        resp = response.json()
        self.assertEqual(resp['_status'], 'OK')

        # try update action
        data = {'persistent': False}
        headers = {
            'Content-Type': 'application/json',
            'If-Match': resp['_etag']
        }
        response = requests.patch(self.endpoint + '/actionacknowledge/' + resp['_id'], json=data,
                                  headers=headers, auth=user1_auth)
        assert response.status_code == 403

        # try delete action
        headers_delete = {
            'Content-Type': 'application/json',
            'If-Match': resp['_etag']
        }
        response = requests.delete(self.endpoint + '/actionacknowledge/' + resp['_id'],
                                   headers=headers_delete, auth=user1_auth)
        assert response.status_code == 403
