#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This test check grafana and create dashboard + graphs
"""

from __future__ import print_function
import os
import json
import time
import shlex
import subprocess
import requests
import unittest2
from bson.objectid import ObjectId
from alignak_backend.carboniface import CarbonIface
from alignak_backend.timeseries import Timeseries
from alignak_backend.grafana import Grafana
from alignak_backend.perfdata import PerfDatas


class TestGrafana(unittest2.TestCase):
    """
    This class test grafana dashboard and graphs
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

        cls.graphite = '10.0.20.16'
        cls.carbon = '10.0.20.16'
        cls.grafana = '10.0.20.17'
        cls.grafana_port = '3000'
        cls.grafana_key = \
            'eyJrIjoiYU1ielpjTTU5VEdkYlpIaEwwVXpUQUNrNFpzWmtGYmIiLCJuIjoiYWRtaW4iLCJpZCI6MX0='

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
        Delete resources in backend

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
        data['ls_last_check'] = int(time.time())
        data['ls_perf_data'] = "rta=14.581000ms;1000.000000;3000.000000;0.000000 pl=0%;100;100;0"
        response = requests.post(cls.endpoint + '/host', json=data, headers=headers, auth=cls.auth)
        resp = response.json()
        print(resp)
        response = requests.get(cls.endpoint + '/host', auth=cls.auth)
        resp = response.json()
        print(resp)
        rh = resp['_items']
        cls.host_srv001 = rh[0]['_id']

        # Add a service
        data = json.loads(open('cfg/service_srv001_ping.json').read())
        data['host'] = rh[0]['_id']
        data['check_command'] = rc[0]['_id']
        data['_realm'] = cls.realm_all
        data['name'] = 'load'
        data['ls_last_check'] = int(time.time())
        data['ls_perf_data'] = "load1=0.360;15.000;30.000;0; load5=0.420;10.000;25.000;0; " \
                               "load15=0.340;5.000;20.000;0;"
        response = requests.post(cls.endpoint + '/service', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.host_srv001_srv = resp['_id']

        # delete grafana dashboard
        headers = {"Authorization": "Bearer " + cls.grafana_key}
        response = requests.get('http://' + cls.grafana + ':' + cls.grafana_port + '/api/search',
                                headers=headers)
        resp = response.json()
        for dashboard in resp:
            requests.delete('http://' + cls.grafana + ':' + cls.grafana_port + '/api/dashboards/'
                            + dashboard['uri'], headers=headers)

        # delete grafana datasource
        response = requests.get('http://' + cls.grafana + ':' + cls.grafana_port +
                                '/api/datasources', headers=headers)
        resp = response.json()
        for datasource in resp:
            requests.delete('http://' + cls.grafana + ':' + cls.grafana_port + '/api/datasources/'
                            + str(datasource['id']), headers=headers)

    @classmethod
    def tearDown(cls):
        """
        Delete resources in backend

        :return: None
        """
        for resource in ['host', 'service', 'command', 'history',
                         'actionacknowledge', 'actiondowntime', 'actionforcecheck']:
            requests.delete(cls.endpoint + '/' + resource, auth=cls.auth)

    def test_create_dashboard_graphite(self):
        """
        Create dashboard into grafana with datasource graphite

        :return: None
        """
        from alignak_backend.app import app, current_app
        with app.test_request_context():
            app.config['GRAPHITE_HOST'] = self.graphite
            app.config['CARBON_HOST'] = self.carbon
            app.config['GRAFANA_HOST'] = self.grafana
            app.config['GRAFANA_POST'] = self.grafana_port
            app.config['GRAFANA_APIKEY'] = self.grafana_key

            # Add in carbon/graphite
            items = [
                {
                    'host': ObjectId(self.host_srv001),
                    'service': None,
                    'state': 'UP',
                    'state_type': 'HARD',
                    'state_id': 0,
                    'last_check': int(time.time()),
                    'output': 'interessing',
                    'perf_data': 'rta=14.581000ms;1000.000000;3000.000000;0.000000 pl=0%;100;100;0',
                    '_realm': ObjectId(self.realm_all)
                },
                {
                    'host': ObjectId(self.host_srv001),
                    'service': ObjectId(self.host_srv001_srv),
                    'state': 'OK',
                    'state_type': 'HARD',
                    'state_id': 0,
                    'last_check': int(time.time()),
                    'output': 'interessing',
                    'perf_data': 'load1=0.360;15.000;30.000;0; load5=0.420;10.000;25.000;0; '
                                 'load15=0.340;5.000;20.000;0;',
                    '_realm': ObjectId(self.realm_all)
                }
            ]
            Timeseries.after_inserted_logcheckresult(items)

            # Grafana
            hosts_db = current_app.data.driver.db['host']
            grafana = Grafana()
            self.assertEqual(grafana.datasource, 'graphite')
            hosts = hosts_db.find({'ls_grafana': False})
            for host in hosts:
                if 'ls_perf_data' in host and host['ls_perf_data']:
                    grafana.create_dashboard(host['_id'])
