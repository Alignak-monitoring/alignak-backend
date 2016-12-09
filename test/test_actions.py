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
    """
    This class test hostgroups and tree feature
    """

    @classmethod
    def setUpClass(cls):
        """
        This method:
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

        # Get default realm
        response = requests.get(cls.endpoint + '/realm', auth=cls.auth)
        resp = response.json()
        cls.realm_all = resp['_items'][0]['_id']

        # Get admin user
        response = requests.get(cls.endpoint + '/user', {"name": "admin"}, auth=cls.auth)
        resp = response.json()
        cls.user_admin = resp['_items'][0]['_id']

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
        response = requests.get(cls.endpoint + '/command', auth=cls.auth)
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
        print(resp)
        response = requests.get(cls.endpoint + '/host', auth=cls.auth)
        resp = response.json()
        print(resp)
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

        # -------------------------------------------
        # Add an acknowledge
        data = {
            "action": "add",
            "host": rh[1]['_id'],
            "service": None,
            "sticky": True,
            "persistent": True,
            "notify": True,
            "user": self.user_admin,
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
        self.assertEqual(re[0]['processed'], False)
        self.assertEqual(re[0]['comment'], "User comment")

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

        # -------------------------------------------
        # Delete an acknowledge
        data = {
            "action": "delete",
            "host": rh[1]['_id'],
            "service": None,
            "user": self.user_admin,
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

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], rh[1]['name'])
        self.assertEqual(re[1]['service'], None)
        self.assertEqual(re[1]['service_name'], '')
        self.assertEqual(re[1]['type'], "ack.delete")
        self.assertEqual(re[1]['message'], "User comment (delete)")

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

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], rh[1]['name'])
        self.assertEqual(re[1]['service'], None)
        self.assertEqual(re[1]['service_name'], '')
        self.assertEqual(re[1]['type'], "ack.delete")
        self.assertEqual(re[1]['message'], "User comment (delete)")

        # One more event
        self.assertEqual(re[2]['host'], rh[1]['_id'])
        self.assertEqual(re[2]['host_name'], rh[1]['name'])
        self.assertEqual(re[2]['service'], None)
        self.assertEqual(re[2]['service_name'], '')
        self.assertEqual(re[2]['type'], "ack.processed")
        self.assertEqual(re[2]['message'], "User comment")

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
            "user": self.user_admin,
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
        self.assertEqual(re[0]['processed'], False)
        self.assertEqual(re[0]['comment'], "User comment")

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

        # -------------------------------------------
        # Delete an acknowledge
        data = {
            "action": "delete",
            "host": rh[1]['_id'],
            "service": rs[0]['_id'],
            "user": self.user_admin,
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

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], rh[1]['name'])
        self.assertEqual(re[1]['service'], rs[0]['_id'])
        self.assertEqual(re[1]['service_name'], rs[0]['name'])
        self.assertEqual(re[1]['type'], "ack.delete")
        self.assertEqual(re[1]['message'], "User comment (delete)")

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

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], rh[1]['name'])
        self.assertEqual(re[1]['service'], rs[0]['_id'])
        self.assertEqual(re[1]['service_name'], rs[0]['name'])
        self.assertEqual(re[1]['type'], "ack.delete")
        self.assertEqual(re[1]['message'], "User comment (delete)")

        # One more event
        self.assertEqual(re[2]['host'], rh[1]['_id'])
        self.assertEqual(re[2]['host_name'], rh[1]['name'])
        self.assertEqual(re[2]['service'], rs[0]['_id'])
        self.assertEqual(re[2]['service_name'], rs[0]['name'])
        self.assertEqual(re[2]['type'], "ack.processed")
        self.assertEqual(re[2]['message'], "User comment")

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
            "user": self.user_admin,
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
        self.assertEqual(re[0]['comment'], "User comment")

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

        # -------------------------------------------
        # Delete a downtime
        data = {
            "action": "delete",
            "host": rh[1]['_id'],
            "service": None,
            "user": self.user_admin,
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
        self.assertEqual(re[0]['service'], None)
        self.assertEqual(re[0]['service_name'], '')
        self.assertEqual(re[0]['type'], "downtime.add")
        self.assertEqual(re[0]['message'], "User comment")

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], rh[1]['name'])
        self.assertEqual(re[1]['service'], None)
        self.assertEqual(re[1]['service_name'], '')
        self.assertEqual(re[1]['type'], "downtime.delete")
        self.assertEqual(re[1]['message'], "User comment (delete)")

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

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], rh[1]['name'])
        self.assertEqual(re[1]['service'], None)
        self.assertEqual(re[1]['service_name'], '')
        self.assertEqual(re[1]['type'], "downtime.delete")
        self.assertEqual(re[1]['message'], "User comment (delete)")

        # One more event
        self.assertEqual(re[2]['host'], rh[1]['_id'])
        self.assertEqual(re[2]['host_name'], rh[1]['name'])
        self.assertEqual(re[2]['service'], None)
        self.assertEqual(re[2]['service_name'], '')
        self.assertEqual(re[2]['type'], "downtime.processed")
        self.assertEqual(re[2]['message'], "User comment")

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
            "user": self.user_admin,
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
        self.assertEqual(re[0]['comment'], "User comment")

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

        # -------------------------------------------
        # Delete a downtime
        data = {
            "action": "delete",
            "host": rh[1]['_id'],
            "service": rs[0]['_id'],
            "user": self.user_admin,
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

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], rh[1]['name'])
        self.assertEqual(re[1]['service'], rs[0]['_id'])
        self.assertEqual(re[1]['service_name'], rs[0]['name'])
        self.assertEqual(re[1]['type'], "downtime.delete")
        self.assertEqual(re[1]['message'], "User comment (delete)")

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

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], rh[1]['name'])
        self.assertEqual(re[1]['service'], rs[0]['_id'])
        self.assertEqual(re[1]['service_name'], rs[0]['name'])
        self.assertEqual(re[1]['type'], "downtime.delete")
        self.assertEqual(re[1]['message'], "User comment (delete)")

        # One more event
        self.assertEqual(re[2]['host'], rh[1]['_id'])
        self.assertEqual(re[2]['host_name'], rh[1]['name'])
        self.assertEqual(re[2]['service'], rs[0]['_id'])
        self.assertEqual(re[2]['service_name'], rs[0]['name'])
        self.assertEqual(re[2]['type'], "downtime.processed")
        self.assertEqual(re[2]['message'], "User comment")

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

        # -------------------------------------------
        # Add a forcecheck
        data = {
            "host": rh[1]['_id'],
            "service": None,
            "user": self.user_admin,
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

        self.assertEqual(re[0]['processed'], False)
        self.assertEqual(re[0]['comment'], "User comment")

        # Get history
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 1)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['service'], None)
        self.assertEqual(re[0]['type'], "check.request")
        self.assertEqual(re[0]['message'], "User comment")

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

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], rh[1]['name'])
        self.assertEqual(re[1]['service'], None)
        self.assertEqual(re[1]['service_name'], '')
        self.assertEqual(re[1]['type'], "check.requested")
        self.assertEqual(re[1]['message'], "User comment")

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
            "user": self.user_admin,
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

        self.assertEqual(re[0]['processed'], False)
        self.assertEqual(re[0]['comment'], "User comment")

        # Get history
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 1)

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['service'], rs[0]['_id'])
        self.assertEqual(re[0]['type'], "check.request")
        self.assertEqual(re[0]['message'], "User comment")

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
            "user": self.user_admin,
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
        self.assertEqual(re[0]['user'], self.user_admin)
        self.assertEqual(re[0]['user_name'], 'admin')
        self.assertEqual(re[0]['type'], "webui.comment")
        self.assertEqual(re[0]['message'], "User comment")
        self.assertEqual(re[0]['_realm'], self.realm_all)

        # -------------------------------------------
        # Add an history comment - host_name, service_name and user_name
        data = {
            "host_name": rh[0]['name'],
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

        self.assertEqual(re[1]['host'], rh[0]['_id'])
        self.assertEqual(re[1]['host_name'], rh[0]['name'])
        self.assertEqual(re[1]['service'], rs[0]['_id'])
        self.assertEqual(re[1]['service_name'], rs[0]['name'])
        self.assertEqual(re[1]['user'], self.user_admin)
        self.assertEqual(re[1]['user_name'], 'admin')
        self.assertEqual(re[1]['type'], "webui.comment")
        self.assertEqual(re[1]['message'], "User comment 2")
        self.assertEqual(re[1]['_realm'], self.realm_all)
