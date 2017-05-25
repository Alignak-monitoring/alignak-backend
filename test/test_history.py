#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This test check the features of history
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


class TestHistory(unittest2.TestCase):
    """This class test history"""

    @classmethod
    def setUpClass(cls):
        """This method:
          * deletes mongodb database
          * starts the backend with uwsgi
          * logs in the backend and get the token
          * gets the default realm and admin user

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
        cls.user_admin = resp['_items'][0]['_id']

    @classmethod
    def tearDownClass(cls):
        """Kill uwsgi

        :return: None
        """
        subprocess.call(['uwsgi', '--stop', '/tmp/uwsgi.pid'])
        time.sleep(2)

    @classmethod
    def setUp(cls):
        """Create/update resources in backend

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
        """Delete resources in backend

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

    def test_history_failures(self):
        """Test history: add an item failure
        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}

        # No existing history items
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
        # Add an history comment, host/service/user not found!
        # Bad host
        data = {
            "host": rs[0]['_id'],
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
        print(resp)
        self.assertEqual(resp['_error']['code'], 422)
        self.assertEqual(resp['_status'], 'ERR')

        # Bad service
        data = {
            "host": rh[0]['_id'],
            "service": rh[0]['_id'],
            "user": self.user_admin,
            "type": "webui.comment",
            "message": "User comment",
            "_realm": self.realm_all
        }
        response = requests.post(
            self.endpoint + '/history', json=data, headers=headers, auth=self.auth
        )
        resp = response.json()
        print(resp)
        self.assertEqual(resp['_error']['code'], 422)
        self.assertEqual(resp['_status'], 'ERR')

        # Bad user
        data = {
            "host": rh[0]['_id'],
            "service": rs[0]['_id'],
            "user": rs[0]['_id'],
            "type": "webui.comment",
            "message": "User comment",
            "_realm": self.realm_all
        }
        response = requests.post(
            self.endpoint + '/history', json=data, headers=headers, auth=self.auth
        )
        resp = response.json()
        print(resp)
        self.assertEqual(resp['_error']['code'], 422)
        self.assertEqual(resp['_status'], 'ERR')

    def test_history_comment(self):
        """Test history: add a comment

        This tests that an history event may be posted with:
        - an host id or name,
        - a service id or name,
        - a user id or name

        Host, service and user may be unknown in the backend for an event concerning
        the whole Alignak

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}

        # No existing history items
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
        # Add an history comment, host/service/user identifier
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
        print("History 0: %s" % re[0])

        self.assertEqual(re[0]['host'], rh[1]['_id'])
        self.assertEqual(re[0]['host_name'], rh[1]['name'])
        self.assertEqual(re[0]['service'], rs[0]['_id'])
        self.assertEqual(re[0]['service_name'], rs[0]['name'])
        self.assertEqual(re[0]['user'], self.user_admin)
        self.assertEqual(re[0]['user_name'], 'admin')
        self.assertEqual(re[0]['type'], "webui.comment")
        self.assertEqual(re[0]['message'], "User comment")
        # History event realm is the host realm
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
        # print("History 0: %s" % re[0])
        print("History 1: %s" % re[1])

        self.assertEqual(re[1]['host'], rh[1]['_id'])
        self.assertEqual(re[1]['host_name'], 'srv001')
        self.assertEqual(re[1]['service'], rs[0]['_id'])
        self.assertEqual(re[1]['service_name'], rs[0]['name'])
        self.assertEqual(re[1]['user'], self.user_admin)
        self.assertEqual(re[1]['user_name'], 'admin')
        self.assertEqual(re[1]['type'], "webui.comment")
        self.assertEqual(re[1]['message'], "User comment 2")
        self.assertEqual(re[1]['_realm'], self.realm_all)

        # -------------------------------------------
        # Add an history comment - host_name, service_name and user_name
        data = {
            "host_name": 'n/a',
            "service_name": 'n/a',
            "user_name": "n/a",
            "type": "webui.comment",
            "message": "User comment 3",
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
        self.assertEqual(len(re), 3)
        # print("History 0: %s" % re[0])
        # print("History 1: %s" % re[1])
        print("History 2: %s" % re[2])

        assert 'host' not in re[2]
        self.assertEqual(re[2]['host_name'], 'n/a')
        assert 'service' not in re[2]
        self.assertEqual(re[2]['service_name'], 'n/a')
        assert 'user' not in re[2]
        self.assertEqual(re[2]['user_name'], 'n/a')
        self.assertEqual(re[2]['type'], "webui.comment")
        self.assertEqual(re[2]['message'], "User comment 3")
        assert '_realm' not in re[2]

    def test_history_events(self):
        """Test history: add all types of events

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}

        # No existing history items
        response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 0)

        count = 0
        allowed = [
            # WebUI user comment
            "webui.comment",

            # Check result
            "check.result",

            # Request to force a check
            "check.request",
            "check.requested",

            # Add acknowledge
            "ack.add",
            # Set acknowledge
            "ack.processed",
            # Delete acknowledge
            "ack.delete",

            # Add downtime
            "downtime.add",
            # Set downtime
            "downtime.processed",
            # Delete downtime
            "downtime.delete",

            # external command
            "monitoring.external_command",

            # timeperiod transition
            "monitoring.timeperiod_transition",
            # alert
            "monitoring.alert",
            # event handler
            "monitoring.event_handler",
            # flapping start / stop
            "monitoring.flapping_start",
            "monitoring.flapping_stop",
            # downtime start / cancel / end
            "monitoring.downtime_start",
            "monitoring.downtime_cancelled",
            "monitoring.downtime_end",
            # acknowledge
            "monitoring.acknowledge",
            # notification
            "monitoring.notification",
        ]
        for event_type in allowed:
            # -------------------------------------------
            # Add an history event
            data = {
                "host_name": 'host',
                "service_name": 'service',
                "user_name": 'alignak',
                "type": event_type,
                "message": "Message: %s" % event_type
            }
            response = requests.post(self.endpoint + '/history', json=data,
                                     headers=headers, auth=self.auth)
            resp = response.json()
            self.assertEqual(resp['_status'], 'OK')

            # Get history
            response = requests.get(self.endpoint + '/history', params=sort_id, auth=self.auth)
            resp = response.json()
            re = resp['_items']
            self.assertEqual(len(re), count + 1)
            print("History event: %s" % re[count])
            assert 'host' not in re[count]
            self.assertEqual(re[count]['host_name'], 'host')
            assert 'service' not in re[count]
            self.assertEqual(re[count]['service_name'], 'service')
            assert 'user' not in re[count]
            self.assertEqual(re[count]['user_name'], 'alignak')
            self.assertEqual(re[count]['type'], event_type)
            self.assertEqual(re[count]['message'], "Message: %s" % event_type)
            assert '_realm' not in re[count]
            count = count + 1
