#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This test check if recalculate livesynthesis on start backend is ok
"""

import os
import json
import time
import shlex
import subprocess
import requests
import unittest2


class TestRecalculateLivesynthesis(unittest2.TestCase):
    """
    This class test the recalculate livesynthesis on start backend
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
        time.sleep(1)

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

    def test_recalculate(self):
        """
        Test if recalculate works when delete livesynthesis resource and restart backend

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
        self.assertEqual(rc[2]['name'], "ping")

        # Add host template
        data = json.loads(open('cfg/host_template.json').read())
        data['check_command'] = rc[2]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = self.realm_all
        # data['_is_template'] = True
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertTrue(rh[1]['_is_template'])

        # Add host
        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[2]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = self.realm_all
        # data['_is_template'] = False
        requests.post(self.endpoint + '/host', json=data, headers=headers, auth=self.auth)
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        resp = response.json()
        rh = resp['_items']
        self.assertFalse(rh[2]['_is_template'])

        # Add service
        data = json.loads(open('cfg/service_srv001_ping.json').read())
        data['host'] = rh[2]['_id']
        data['check_command'] = rc[1]['_id']
        data['_realm'] = self.realm_all
        requests.post(self.endpoint + '/service', json=data, headers=headers, auth=self.auth)
        # Check if service right in backend
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        resp = response.json()
        rs = resp['_items']
        self.assertEqual(rs[0]['name'], "ping")
        self.assertFalse(rs[0]['_is_template'])

        requests.delete(self.endpoint + '/livesynthesis', auth=self.auth)
        self.p.kill()
        time.sleep(3)
        self.p = subprocess.Popen(['uwsgi', '--plugin', 'python', '-w', 'alignakbackend:app',
                                   '--socket', '0.0.0.0:5000',
                                   '--protocol=http', '--enable-threads', '--pidfile',
                                   '/tmp/uwsgi.pid'])
        time.sleep(3)

        # Check if livestate right recalculate
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
        self.assertEqual(r[0]['services_acknowledged'], 0)
        self.assertEqual(r[0]['services_in_downtime'], 0)
