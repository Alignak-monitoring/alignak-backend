#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This test check preparation of timeseries
"""

import time
import os
import copy
import shlex
import json
import subprocess
import requests
import requests_mock
import unittest2
from bson.objectid import ObjectId
from alignak_backend.timeseries import Timeseries


class TestTimeseries(unittest2.TestCase):
    """
    This class test timeseries preparation
    """

    maxDiff = None

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

        # add more realms
        data = {"name": "All A", "_parent": cls.realm_all}
        response = requests.post(cls.endpoint + '/realm', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.realm_all_A = copy.copy(resp['_id'])

        data = {"name": "All A1", "_parent": cls.realm_all_A}
        response = requests.post(cls.endpoint + '/realm', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.realm_all_A1 = copy.copy(resp['_id'])

        data = {"name": "All B", "_parent": cls.realm_all}
        response = requests.post(cls.endpoint + '/realm', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.realm_all_B = copy.copy(resp['_id'])

        data = {"name": "All B1", "_parent": cls.realm_all_B}
        response = requests.post(cls.endpoint + '/realm', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.realm_all_B1 = copy.copy(resp['_id'])

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

    def test_prepare_data(self):
        """
        Prepare timeseries from a web perfdata

        :return: None
        """
        item = {
            'host': 'srv001',
            'service': 'check_xxx',
            'state': 'OK',
            'state_type': 'HARD',
            'state_id': 0,
            'acknowledged': False,
            'last_check': int(time.time()),
            'last_state': 'OK',
            'output': 'NGINX OK -  0.161 sec. response time, Active: 25 (Writing: 3 Reading: 0 '
                      'Waiting: 22) ReqPerSec: 58.000 ConnPerSec: 1.200 ReqPerConn: 4.466',
            'long_output': '',
            'perf_data': 'Writing=3;;;; Reading=0;;;; Waiting=22;;;; Active=25;1000;2000;; '
                         'ReqPerSec=58.000000;100;200;; ConnPerSec=1.200000;200;300;; '
                         'ReqPerConn=4.465602;;;; rta=0.083000ms;10.000000;15.000000;0.000000',
            '_realm': 'All.Propieres'
        }

        ret = Timeseries.prepare_data(item)
        reference = {
            'data': [
                {
                    'name': 'ReqPerConn',
                    'value': 4.465602,
                },
                {
                    'name': 'Writing',
                    'value': 3
                },
                {
                    'name': 'Waiting',
                    'value': 22
                },
                {
                    'name': 'ConnPerSec',
                    'value': 1.2
                },
                {
                    'name': 'ConnPerSec_warning',
                    'value': 200
                },
                {
                    'name': 'ConnPerSec_critical',
                    'value': 300
                },
                {
                    'name': 'Active',
                    'value': 25
                },
                {
                    'name': 'Active_warning',
                    'value': 1000
                },
                {
                    'name': 'Active_critical',
                    'value': 2000
                },
                {
                    'name': 'ReqPerSec',
                    'value': 58
                },
                {
                    'name': 'ReqPerSec_warning',
                    'value': 100
                },
                {
                    'name': 'ReqPerSec_critical',
                    'value': 200
                },
                {
                    'name': 'Reading',
                    'value': 0
                },
                {
                    'name': 'rta',
                    'value': 0.083
                },
                {
                    'name': 'rta_warning',
                    'value': 10
                },
                {
                    'name': 'rta_critical',
                    'value': 15
                }
            ]
        }
        self.assertItemsEqual(reference['data'], ret['data'])

    def test_prepare_data_special(self):
        """
        Prepare timeseries from a special perfdata, with
        * name instead numerical value
        * name composed by: string.timestamp

        :return: None
        """
        item = {
            'host': 'srv001',
            'service': 'check_xxx',
            'state': 'OK',
            'state_type': 'HARD',
            'state_id': 0,
            'acknowledged': False,
            'last_check': int(time.time()),
            'last_state': 'OK',
            'output': 'em0:UP (0.0Mbps/0.0Mbps/0.0/0.0/0.0/0.0) (1 UP): OK',
            'long_output': '',
            'perf_data': "cache_descr_names=em0 cache_descr_time=1475663830 "
                         "em0_out_octet.1475670730'=86608341539",
            '_realm': 'All.Propieres'
        }

        ret = Timeseries.prepare_data(item)
        reference = {
            'data': [
                {
                    'name': 'cache_descr_time',
                    'value': 1475663830
                },
                {
                    'name': 'em0_out_octet',
                    'value': 86608341539
                }
            ]
        }
        self.assertItemsEqual(reference['data'], ret['data'])

    def test_generate_realm_prefix(self):
        """
        Test generate realm prefix when have many levels

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        data = {
            'name': 'realm A',
            '_parent': self.realm_all
        }
        response = requests.post(self.endpoint + '/realm', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        realm_a = resp['_id']

        data = {
            'name': 'realm B',
            '_parent': self.realm_all
        }
        response = requests.post(self.endpoint + '/realm', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        realm_b = resp['_id']

        data = {
            'name': 'realm A1',
            '_parent': realm_a
        }
        response = requests.post(self.endpoint + '/realm', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        realm_a1 = resp['_id']

        from alignak_backend.app import app
        with app.test_request_context():
            prefix = Timeseries.get_realms_prefix(ObjectId(self.realm_all))
            self.assertEqual(prefix, 'All')
            prefix = Timeseries.get_realms_prefix(ObjectId(realm_a))
            self.assertEqual(prefix, 'All.realm A')
            prefix = Timeseries.get_realms_prefix(ObjectId(realm_b))
            self.assertEqual(prefix, 'All.realm B')
            prefix = Timeseries.get_realms_prefix(ObjectId(realm_a1))
            self.assertEqual(prefix, 'All.realm A.realm A1')

    def test_timeseries_realm_all_sub(self):
        # pylint: disable=too-many-locals
        """
        Test with 2 graphites + 1 infuxdb in realm All + sub_realm true.
        We send data in timeseries class and catch the request to graphite and influxdb.

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        # add graphite 001
        data = {
            'name': 'graphite 001',
            'carbon_address': '192.168.0.101',
            'graphite_address': '192.168.0.101',
            'prefix': '',
            '_realm': self.realm_all,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/graphite', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        graphite_001 = resp['_id']

        # add graphite 002
        data = {
            'name': 'graphite 002',
            'carbon_address': '192.168.0.102',
            'graphite_address': '192.168.0.102',
            'prefix': '',
            '_realm': self.realm_all,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/graphite', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        graphite_002 = resp['_id']

        # add influxdb 001
        data = {
            'name': 'influxdb 001',
            'address': '192.168.0.103',
            'login': 'alignak',
            'password': 'alignak',
            'database': 'alignak',
            '_realm': self.realm_all,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/influxdb', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        influxdb_001 = resp['_id']

        # Add command
        data = json.loads(open('cfg/command_ping.json').read())
        data['_realm'] = self.realm_all
        data['_sub_realm'] = True
        data['name'] = 'ping1'
        response = requests.post(self.endpoint + '/command', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        command_ping = resp['_id']

        # add host in realm All
        data = {
            'name': 'srv001',
            'address': '127.0.0.1',
            'check_command': command_ping,
            '_realm': self.realm_all
        }
        response = requests.post(self.endpoint + '/host', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        host_001 = resp['_id']

        # add host in realm All A
        data = {
            'name': 'srv002',
            'address': '127.0.0.1',
            'check_command': command_ping,
            '_realm': self.realm_all_A
        }
        response = requests.post(self.endpoint + '/host', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        host_002 = resp['_id']

        # add host in realm All A1
        data = {
            'name': 'srv003',
            'address': '127.0.0.1',
            'check_command': command_ping,
            '_realm': self.realm_all_A1
        }
        response = requests.post(self.endpoint + '/host', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        host_003 = resp['_id']

        # add logcheckresult of host001
        item = {
            'host': ObjectId(host_001),
            'host_name': 'srv001',
            'service': None,
            'service_name': '',
            'state': 'OK',
            'state_type': 'HARD',
            'state_id': 0,
            'acknowledged': False,
            'last_check': int(time.time()),
            'last_state': 'OK',
            'output': 'PING OK - Packet loss = 0%, RTA = 0.08 ms',
            'long_output': '',
            'perf_data': "rta=74.827003ms;100.000000;110.000000;0.000000 pl=0%;10;;0",
            '_realm': ObjectId(self.realm_all)
        }
        from alignak_backend.app import app, current_app
        with app.test_request_context():
            # test with timeseries not available, it must be quick (< 3 seconds), because have
            # 2 graphites and 1 influx, so (2 + 1) * 1 second timeout * 2 (code execution between
            # each tries send to timeseries)
            time_begin = time.time()
            Timeseries.after_inserted_logcheckresult([item])
            execution_time = time.time() - time_begin
            assert execution_time < 6

            # check data in timeseriesretention
            timeseriesretention_db = current_app.data.driver.db['timeseriesretention']
            retentions = timeseriesretention_db.find()
            retention_data = []
            for retention in retentions:
                retention_data.append({
                    'realm': retention['realm'],
                    'name': retention['name'],
                    'service': retention['service'],
                    'graphite': retention['graphite'],
                    'influxdb': retention['influxdb'],
                    'host': retention['host'],
                    'value': retention['value']
                })
            ref = [
                {'realm': u'All', 'name': u'rta', 'service': u'',
                 'graphite': ObjectId(graphite_001), 'influxdb': None, 'host': u'srv001',
                 'value': 75},
                {'realm': u'All', 'name': u'rta_warning', 'service': u'',
                 'graphite': ObjectId(graphite_001), 'influxdb': None, 'host': u'srv001',
                 'value': 100},
                {'realm': u'All', 'name': u'rta_critical', 'service': u'',
                 'graphite': ObjectId(graphite_001), 'influxdb': None, 'host': u'srv001',
                 'value': 110},

                {'realm': u'All', 'name': u'pl', 'service': u'',
                 'graphite': ObjectId(graphite_001), 'influxdb': None, 'host': u'srv001',
                 'value': 0},
                {'realm': u'All', 'name': u'pl_warning', 'service': u'',
                 'graphite': ObjectId(graphite_001), 'influxdb': None, 'host': u'srv001',
                 'value': 10},

                {'realm': u'All', 'name': u'rta', 'service': u'',
                 'graphite': ObjectId(graphite_002), 'influxdb': None, 'host': u'srv001',
                 'value': 75},
                {'realm': u'All', 'name': u'rta_warning', 'service': u'',
                 'graphite': ObjectId(graphite_002), 'influxdb': None, 'host': u'srv001',
                 'value': 100},
                {'realm': u'All', 'name': u'rta_critical', 'service': u'',
                 'graphite': ObjectId(graphite_002), 'influxdb': None, 'host': u'srv001',
                 'value': 110},

                {'realm': u'All', 'name': u'pl', 'service': u'',
                 'graphite': ObjectId(graphite_002), 'influxdb': None, 'host': u'srv001',
                 'value': 0},
                {'realm': u'All', 'name': u'pl_warning', 'service': u'',
                 'graphite': ObjectId(graphite_002), 'influxdb': None, 'host': u'srv001',
                 'value': 10},

                {'realm': u'All', 'name': u'rta', 'service': u'', 'graphite': None,
                 'influxdb': ObjectId(influxdb_001), 'host': u'srv001', 'value': 75},
                {'realm': u'All', 'name': u'rta_warning', 'service': u'', 'graphite': None,
                 'influxdb': ObjectId(influxdb_001), 'host': u'srv001', 'value': 100},
                {'realm': u'All', 'name': u'rta_critical', 'service': u'', 'graphite': None,
                 'influxdb': ObjectId(influxdb_001), 'host': u'srv001', 'value': 110},

                {'realm': u'All', 'name': u'pl', 'service': u'', 'graphite': None,
                 'influxdb': ObjectId(influxdb_001), 'host': u'srv001', 'value': 0},
                {'realm': u'All', 'name': u'pl_warning', 'service': u'', 'graphite': None,
                 'influxdb': ObjectId(influxdb_001), 'host': u'srv001', 'value': 10},
            ]
            self.assertItemsEqual(ref, retention_data)
            timeseriesretention_db.drop()

        # === Test now with a host in realm All A1 ===
        # add logcheckresult of host003
        item = {
            'host': ObjectId(host_003),
            'host_name': 'srv003',
            'service': None,
            'service_name': '',
            'state': 'OK',
            'state_type': 'HARD',
            'state_id': 0,
            'acknowledged': False,
            'last_check': int(time.time()),
            'last_state': 'OK',
            'output': 'PING OK - Packet loss = 0%, RTA = 0.08 ms',
            'long_output': '',
            'perf_data': "rta=32.02453ms;100.000000;110.000000;0.000000 pl=0%;10;;0",
            '_realm': ObjectId(self.realm_all_A1)
        }
        with app.test_request_context():
            # test with timeseries not available, it must be quick (< 3 seconds), because have
            # 2 graphites and 1 influx, so (2 + 1) * 1 second timeout * 2 (code execution between
            # each tries send to timeseries)
            time_begin = time.time()
            Timeseries.after_inserted_logcheckresult([item])
            execution_time = time.time() - time_begin
            assert execution_time < 6

            # check data in timeseriesretention
            timeseriesretention_db = current_app.data.driver.db['timeseriesretention']
            retentions = timeseriesretention_db.find()
            retention_data = []
            for retention in retentions:
                retention_data.append({
                    'realm': retention['realm'],
                    'name': retention['name'],
                    'service': retention['service'],
                    'graphite': retention['graphite'],
                    'influxdb': retention['influxdb'],
                    'host': retention['host'],
                    'value': retention['value']
                })
            ref = [
                {'realm': u'All.All A.All A1', 'name': u'rta', 'service': u'',
                 'graphite': ObjectId(graphite_001), 'influxdb': None, 'host': u'srv003',
                 'value': 32},
                {'realm': u'All.All A.All A1', 'name': u'rta_warning', 'service': u'',
                 'graphite': ObjectId(graphite_001), 'influxdb': None, 'host': u'srv003',
                 'value': 100},
                {'realm': u'All.All A.All A1', 'name': u'rta_critical', 'service': u'',
                 'graphite': ObjectId(graphite_001), 'influxdb': None, 'host': u'srv003',
                 'value': 110},

                {'realm': u'All.All A.All A1', 'name': u'pl', 'service': u'',
                 'graphite': ObjectId(graphite_001), 'influxdb': None, 'host': u'srv003',
                 'value': 0},
                {'realm': u'All.All A.All A1', 'name': u'pl_warning', 'service': u'',
                 'graphite': ObjectId(graphite_001), 'influxdb': None, 'host': u'srv003',
                 'value': 10},

                {'realm': u'All.All A.All A1', 'name': u'rta', 'service': u'',
                 'graphite': ObjectId(graphite_002), 'influxdb': None, 'host': u'srv003',
                 'value': 32},
                {'realm': u'All.All A.All A1', 'name': u'rta_warning', 'service': u'',
                 'graphite': ObjectId(graphite_002), 'influxdb': None, 'host': u'srv003',
                 'value': 100},
                {'realm': u'All.All A.All A1', 'name': u'rta_critical', 'service': u'',
                 'graphite': ObjectId(graphite_002), 'influxdb': None, 'host': u'srv003',
                 'value': 110},

                {'realm': u'All.All A.All A1', 'name': u'pl', 'service': u'',
                 'graphite': ObjectId(graphite_002), 'influxdb': None, 'host': u'srv003',
                 'value': 0},
                {'realm': u'All.All A.All A1', 'name': u'pl_warning', 'service': u'',
                 'graphite': ObjectId(graphite_002), 'influxdb': None, 'host': u'srv003',
                 'value': 10},

                {'realm': u'All.All A.All A1', 'name': u'rta', 'service': u'', 'graphite': None,
                 'influxdb': ObjectId(influxdb_001), 'host': u'srv003', 'value': 32},
                {'realm': u'All.All A.All A1', 'name': u'rta_warning', 'service': u'',
                 'graphite': None, 'influxdb': ObjectId(influxdb_001), 'host': u'srv003',
                 'value': 100},
                {'realm': u'All.All A.All A1', 'name': u'rta_critical', 'service': u'',
                 'graphite': None, 'influxdb': ObjectId(influxdb_001), 'host': u'srv003',
                 'value': 110},

                {'realm': u'All.All A.All A1', 'name': u'pl', 'service': u'', 'graphite': None,
                 'influxdb': ObjectId(influxdb_001), 'host': u'srv003', 'value': 0},
                {'realm': u'All.All A.All A1', 'name': u'pl_warning', 'service': u'',
                 'graphite': None, 'influxdb': ObjectId(influxdb_001), 'host': u'srv003',
                 'value': 10},
            ]
            self.assertItemsEqual(ref, retention_data)
            timeseriesretention_db.drop()

        # === We will have too a graphite in realm all A + sub_realm false ===
        # add graphite 003
        data = {
            'name': 'graphite 003',
            'carbon_address': '192.168.0.104',
            'graphite_address': '192.168.0.104',
            'prefix': '',
            '_realm': self.realm_all_A,
            '_sub_realm': False
        }
        response = requests.post(self.endpoint + '/graphite', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        graphite_003 = resp['_id']

        # Test now with a host in realm All A1
        # add logcheckresult of host003
        item = {
            'host': ObjectId(host_003),
            'host_name': 'srv003',
            'service': None,
            'service_name': '',
            'state': 'OK',
            'state_type': 'HARD',
            'state_id': 0,
            'acknowledged': False,
            'last_check': int(time.time()),
            'last_state': 'OK',
            'output': 'PING OK - Packet loss = 0%, RTA = 0.08 ms',
            'long_output': '',
            'perf_data': "rta=32.02453ms;100.000000;110.000000;0.000000 pl=0%;10;;0",
            '_realm': ObjectId(self.realm_all_A1)
        }
        with app.test_request_context():
            # test with timeseries not available, it must be quick (< 3 seconds), because have
            # 2 graphites and 1 influx, so (2 + 1) * 1 second timeout * 2 (code execution between
            # each tries send to timeseries)
            time_begin = time.time()
            Timeseries.after_inserted_logcheckresult([item])
            execution_time = time.time() - time_begin
            assert execution_time < 6

            # check data in timeseriesretention
            timeseriesretention_db = current_app.data.driver.db['timeseriesretention']
            retentions = timeseriesretention_db.find()
            retention_data = []
            for retention in retentions:
                retention_data.append({
                    'realm': retention['realm'],
                    'name': retention['name'],
                    'service': retention['service'],
                    'graphite': retention['graphite'],
                    'influxdb': retention['influxdb'],
                    'host': retention['host'],
                    'value': retention['value']
                })
            ref = [
                {'realm': u'All.All A.All A1', 'name': u'rta', 'service': u'',
                 'graphite': ObjectId(graphite_001), 'influxdb': None, 'host': u'srv003',
                 'value': 32},
                {'realm': u'All.All A.All A1', 'name': u'rta_warning', 'service': u'',
                 'graphite': ObjectId(graphite_001), 'influxdb': None, 'host': u'srv003',
                 'value': 100},
                {'realm': u'All.All A.All A1', 'name': u'rta_critical', 'service': u'',
                 'graphite': ObjectId(graphite_001), 'influxdb': None, 'host': u'srv003',
                 'value': 110},

                {'realm': u'All.All A.All A1', 'name': u'pl', 'service': u'',
                 'graphite': ObjectId(graphite_001), 'influxdb': None, 'host': u'srv003',
                 'value': 0},
                {'realm': u'All.All A.All A1', 'name': u'pl_warning', 'service': u'',
                 'graphite': ObjectId(graphite_001), 'influxdb': None, 'host': u'srv003',
                 'value': 10},

                {'realm': u'All.All A.All A1', 'name': u'rta', 'service': u'',
                 'graphite': ObjectId(graphite_002), 'influxdb': None, 'host': u'srv003',
                 'value': 32},
                {'realm': u'All.All A.All A1', 'name': u'rta_warning', 'service': u'',
                 'graphite': ObjectId(graphite_002), 'influxdb': None, 'host': u'srv003',
                 'value': 100},
                {'realm': u'All.All A.All A1', 'name': u'rta_critical', 'service': u'',
                 'graphite': ObjectId(graphite_002), 'influxdb': None, 'host': u'srv003',
                 'value': 110},

                {'realm': u'All.All A.All A1', 'name': u'pl', 'service': u'',
                 'graphite': ObjectId(graphite_002), 'influxdb': None, 'host': u'srv003',
                 'value': 0},
                {'realm': u'All.All A.All A1', 'name': u'pl_warning', 'service': u'',
                 'graphite': ObjectId(graphite_002), 'influxdb': None, 'host': u'srv003',
                 'value': 10},

                {'realm': u'All.All A.All A1', 'name': u'rta', 'service': u'', 'graphite': None,
                 'influxdb': ObjectId(influxdb_001), 'host': u'srv003', 'value': 32},
                {'realm': u'All.All A.All A1', 'name': u'rta_warning', 'service': u'',
                 'graphite': None, 'influxdb': ObjectId(influxdb_001), 'host': u'srv003',
                 'value': 100},
                {'realm': u'All.All A.All A1', 'name': u'rta_critical', 'service': u'',
                 'graphite': None, 'influxdb': ObjectId(influxdb_001), 'host': u'srv003',
                 'value': 110},

                {'realm': u'All.All A.All A1', 'name': u'pl', 'service': u'', 'graphite': None,
                 'influxdb': ObjectId(influxdb_001), 'host': u'srv003', 'value': 0},
                {'realm': u'All.All A.All A1', 'name': u'pl_warning', 'service': u'',
                 'graphite': None, 'influxdb': ObjectId(influxdb_001), 'host': u'srv003',
                 'value': 10},
            ]
            self.assertItemsEqual(ref, retention_data)
            timeseriesretention_db.drop()

            # Test now with a host in realm All A
            # add logcheckresult of host002
            item = {
                'host': ObjectId(host_002),
                'host_name': 'srv002',
                'service': None,
                'service_name': '',
                'state': 'OK',
                'state_type': 'HARD',
                'state_id': 0,
                'acknowledged': False,
                'last_check': int(time.time()),
                'last_state': 'OK',
                'output': 'PING OK - Packet loss = 0%, RTA = 0.08 ms',
                'long_output': '',
                'perf_data': "rta=32.02453ms;100.000000;110.000000;0.000000 pl=0%;10;;0",
                '_realm': ObjectId(self.realm_all_A)
            }
            with app.test_request_context():
                # test with timeseries not available, it must be quick (< 3 seconds), because have
                # 3 graphites and 1 influx, so (3 + 1) * 1 second timeout * 2 (code execution
                # between each tries send to timeseries)
                time_begin = time.time()
                Timeseries.after_inserted_logcheckresult([item])
                execution_time = time.time() - time_begin
                assert execution_time < 8

                # check data in timeseriesretention
                timeseriesretention_db = current_app.data.driver.db['timeseriesretention']
                retentions = timeseriesretention_db.find()
                retention_data = []
                for retention in retentions:
                    retention_data.append({
                        'realm': retention['realm'],
                        'name': retention['name'],
                        'service': retention['service'],
                        # 'timestamp': retention['timestamp'],
                        'graphite': retention['graphite'],
                        'influxdb': retention['influxdb'],
                        'host': retention['host'],
                        'value': retention['value']
                    })
                ref = [
                    {'realm': u'All.All A', 'name': u'rta', 'service': u'',
                     'graphite': ObjectId(graphite_003), 'influxdb': None, 'host': u'srv002',
                     'value': 32},
                    {'realm': u'All.All A', 'name': u'rta_warning', 'service': u'',
                     'graphite': ObjectId(graphite_003), 'influxdb': None, 'host': u'srv002',
                     'value': 100},
                    {'realm': u'All.All A', 'name': u'rta_critical', 'service': u'',
                     'graphite': ObjectId(graphite_003), 'influxdb': None, 'host': u'srv002',
                     'value': 110},

                    {'realm': u'All.All A', 'name': u'pl', 'service': u'',
                     'graphite': ObjectId(graphite_003), 'influxdb': None, 'host': u'srv002',
                     'value': 0},
                    {'realm': u'All.All A', 'name': u'pl_warning', 'service': u'',
                     'graphite': ObjectId(graphite_003), 'influxdb': None, 'host': u'srv002',
                     'value': 10},

                    {'realm': u'All.All A', 'name': u'rta', 'service': u'',
                     'graphite': ObjectId(graphite_001), 'influxdb': None, 'host': u'srv002',
                     'value': 32},
                    {'realm': u'All.All A', 'name': u'rta_warning', 'service': u'',
                     'graphite': ObjectId(graphite_001), 'influxdb': None, 'host': u'srv002',
                     'value': 100},
                    {'realm': u'All.All A', 'name': u'rta_critical', 'service': u'',
                     'graphite': ObjectId(graphite_001), 'influxdb': None, 'host': u'srv002',
                     'value': 110},

                    {'realm': u'All.All A', 'name': u'pl', 'service': u'',
                     'graphite': ObjectId(graphite_001), 'influxdb': None, 'host': u'srv002',
                     'value': 0},
                    {'realm': u'All.All A', 'name': u'pl_warning', 'service': u'',
                     'graphite': ObjectId(graphite_001), 'influxdb': None, 'host': u'srv002',
                     'value': 10},

                    {'realm': u'All.All A', 'name': u'rta', 'service': u'',
                     'graphite': ObjectId(graphite_002), 'influxdb': None, 'host': u'srv002',
                     'value': 32},
                    {'realm': u'All.All A', 'name': u'rta_warning', 'service': u'',
                     'graphite': ObjectId(graphite_002), 'influxdb': None, 'host': u'srv002',
                     'value': 100},
                    {'realm': u'All.All A', 'name': u'rta_critical', 'service': u'',
                     'graphite': ObjectId(graphite_002), 'influxdb': None, 'host': u'srv002',
                     'value': 110},

                    {'realm': u'All.All A', 'name': u'pl', 'service': u'',
                     'graphite': ObjectId(graphite_002), 'influxdb': None, 'host': u'srv002',
                     'value': 0},
                    {'realm': u'All.All A', 'name': u'pl_warning', 'service': u'',
                     'graphite': ObjectId(graphite_002), 'influxdb': None, 'host': u'srv002',
                     'value': 10},

                    {'realm': u'All.All A', 'name': u'rta', 'service': u'', 'graphite': None,
                     'influxdb': ObjectId(influxdb_001), 'host': u'srv002', 'value': 32},
                    {'realm': u'All.All A', 'name': u'rta_warning', 'service': u'',
                     'graphite': None, 'influxdb': ObjectId(influxdb_001), 'host': u'srv002',
                     'value': 100},
                    {'realm': u'All.All A', 'name': u'rta_critical', 'service': u'',
                     'graphite': None, 'influxdb': ObjectId(influxdb_001), 'host': u'srv002',
                     'value': 110},

                    {'realm': u'All.All A', 'name': u'pl', 'service': u'', 'graphite': None,
                     'influxdb': ObjectId(influxdb_001), 'host': u'srv002', 'value': 0},
                    {'realm': u'All.All A', 'name': u'pl_warning', 'service': u'',
                     'graphite': None, 'influxdb': ObjectId(influxdb_001), 'host': u'srv002',
                     'value': 10},
                ]
                self.assertItemsEqual(ref, retention_data)
                timeseriesretention_db.drop()
