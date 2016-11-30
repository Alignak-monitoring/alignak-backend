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
import requests_mock
import unittest2
from bson.objectid import ObjectId
from alignak_backend.grafana import Grafana


class TestGrafana(unittest2.TestCase):
    """
    This class test grafana dashboard and panels
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

        data = {"name": "All A", "_parent": cls.realm_all}
        response = requests.post(cls.endpoint + '/realm', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.realmAll_A = resp['_id']

        data = {"name": "All A1", "_parent": cls.realmAll_A}
        response = requests.post(cls.endpoint + '/realm', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.realmAll_A1 = resp['_id']

        data = {"name": "All B", "_parent": cls.realm_all}
        response = requests.post(cls.endpoint + '/realm', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.realmAll_B = resp['_id']

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

        # Add an host in realm A1
        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[0]['_id']
        if 'realm' in data:
            del data['realm']
        data['_realm'] = cls.realmAll_A1
        data['name'] = "srv002"
        data['ls_last_check'] = int(time.time())
        data['ls_perf_data'] = "rta=14.581000ms;1000.000000;3000.000000;0.000000 pl=0%;100;100;0"
        response = requests.post(cls.endpoint + '/host', json=data, headers=headers, auth=cls.auth)
        resp = response.json()
        cls.host_srv002 = resp['_id']

        # Add a service of srv002
        data = json.loads(open('cfg/service_srv001_ping.json').read())
        data['host'] = cls.host_srv002
        data['check_command'] = rc[0]['_id']
        data['_realm'] = cls.realmAll_A1
        data['name'] = 'load'
        data['ls_last_check'] = int(time.time())
        data['ls_perf_data'] = "load1=0.360;15.000;30.000;0; load5=0.420;10.000;25.000;0; " \
                               "load15=0.340;5.000;20.000;0;"
        response = requests.post(cls.endpoint + '/service', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.host_srv002_srv = resp['_id']

    @classmethod
    def tearDown(cls):
        """
        Delete resources in backend

        :return: None
        """
        for resource in ['host', 'service', 'command', 'history',
                         'actionacknowledge', 'actiondowntime', 'actionforcecheck', 'grafana',
                         'graphite', 'influxdb']:
            requests.delete(cls.endpoint + '/' + resource, auth=cls.auth)

    def test_grafana_on_realms(self):
        """We can have more than 1 grafana server on each realm

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        # add a grafana on realm A + subrealm
        data = {
            'name': 'grafana All A+',
            'address': '192.168.0.100',
            'apikey': 'xxxxxxxxxxxx0',
            '_realm': self.realmAll_A,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/grafana', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # add a grafana on realm All
        data = {
            'name': 'grafana All',
            'address': '192.168.0.101',
            'apikey': 'xxxxxxxxxxxx1',
            '_realm': self.realm_all,
            '_sub_realm': False
        }
        response = requests.post(self.endpoint + '/grafana', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        grafana_all = resp['_id']

        # update the grafana on realm All + subrealm
        data = {'_sub_realm': True}
        headers_up = {
            'Content-Type': 'application/json',
            'If-Match': resp['_etag']
        }
        response = requests.patch(self.endpoint + '/grafana/' + grafana_all, json=data,
                                  headers=headers_up, auth=self.auth)
        self.assertEqual('OK', resp['_status'], resp)
        resp = response.json()

        # delete grafana on realm All
        headers_delete = {
            'Content-Type': 'application/json',
            'If-Match': resp['_etag']
        }
        response = requests.delete(self.endpoint + '/grafana/' + resp['_id'],
                                   headers=headers_delete, auth=self.auth)
        self.assertEqual(response.status_code, 204)

        response = requests.get(self.endpoint + '/grafana', auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['_items']), 1)

        # add grafana on realm All + subrealm
        data = {
            'name': 'grafana All',
            'address': '192.168.0.101',
            'apikey': 'xxxxxxxxxxxx1',
            '_realm': self.realm_all,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/grafana', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

    def test_2_graphites_same_realm(self):
        """Test 2 graphite on same realm, but only one can be affected to grafana on same realm

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        # Add grafana All + subrealms
        data = {
            'name': 'grafana All',
            'address': '192.168.0.101',
            'apikey': 'xxxxxxxxxxxx1',
            '_realm': self.realm_all,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/grafana', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        grafana_all = resp['_id']

        # Add graphite_A in realm A associate to grafana
        data = {
            'name': 'graphite A sub',
            'carbon_address': '192.168.0.102',
            'graphite_address': '192.168.0.102',
            'prefix': 'my_A_sub',
            'grafana': grafana_all,
            '_realm': self.realmAll_A,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/graphite', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        # Add graphite_B in realm A associate to grafana, so graphite_A not linked
        data = {
            'name': 'graphite B',
            'carbon_address': '192.168.0.101',
            'graphite_address': '192.168.0.101',
            'prefix': 'my_B',
            'grafana': grafana_all,
            '_realm': self.realmAll_A
        }
        response = requests.post(self.endpoint + '/graphite', json=data, headers=headers,
                                 auth=self.auth)
        assert response.status_code == 412

        # todo try add in realm A1
        data = {
            'name': 'graphite B',
            'carbon_address': '192.168.0.101',
            'graphite_address': '192.168.0.101',
            'prefix': 'my_B',
            'grafana': grafana_all,
            '_realm': self.realmAll_A1
        }
        requests.post(self.endpoint + '/graphite', json=data, headers=headers, auth=self.auth)

    def test_create_dashboard_panels_graphite(self):
        # pylint: disable=too-many-locals
        """
        Create dashboard into grafana with datasource graphite

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        # Create grafana in realm All + subrealm
        data = {
            'name': 'grafana All',
            'address': '192.168.0.101',
            'apikey': 'xxxxxxxxxxxx1',
            '_realm': self.realm_all,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/grafana', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        grafana_all = resp['_id']

        # Create a graphite in All B linked to grafana
        data = {
            'name': 'graphite B',
            'carbon_address': '192.168.0.101',
            'graphite_address': '192.168.0.101',
            'prefix': 'my_B',
            'grafana': grafana_all,
            '_realm': self.realmAll_B
        }
        response = requests.post(self.endpoint + '/graphite', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        graphite_B = resp['_id']

        # Create a graphite in All A + subrealm liked to grafana
        data = {
            'name': 'graphite A sub',
            'carbon_address': '192.168.0.102',
            'graphite_address': '192.168.0.102',
            'prefix': 'my_A_sub',
            'grafana': grafana_all,
            '_realm': self.realmAll_A,
            '_sub_realm': True
        }
        response = requests.post(self.endpoint + '/graphite', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)
        graphite_A_sub = resp['_id']

        # test grafana class and code to create dashboard in grafana
        from alignak_backend.app import app, current_app
        with app.app_context():
            grafana_db = current_app.data.driver.db['grafana']
            grafanas = grafana_db.find()
            for grafana in grafanas:
                with requests_mock.mock() as mockreq:
                    ret = [{"id": 1, "orgId": 1, "name": graphite_B,
                            "type": "grafana-simple-json-datasource",
                            "typeLogoUrl": "public/plugins/grafana-simple-json-datasource/src/img/"
                                           "simpleJson_logo.svg",
                            "access": "proxy", "url": "http://127.0.0.1/glpi090/apirest.php",
                            "password": "", "user": "", "database": "", "basicAuth": True,
                            "basicAuthUser": "", "basicAuthPassword": "", "withCredentials": False,
                            "isDefault": True}]
                    mockreq.get('http://192.168.0.101:3000/api/datasources', json=ret)
                    mockreq.post('http://192.168.0.101:3000/api/datasources', json='true')
                    graf = Grafana(grafana)
                    assert len(graf.timeseries) == 3
                    assert sorted([ObjectId(self.realmAll_B), ObjectId(self.realmAll_A),
                                   ObjectId(self.realmAll_A1)]) == sorted(graf.timeseries.keys())
                    assert graf.timeseries[ObjectId(self.realmAll_A)]['_id'] == ObjectId(
                        graphite_A_sub)
                    assert graf.timeseries[ObjectId(self.realmAll_A1)]['_id'] == ObjectId(
                        graphite_A_sub)
                    assert graf.timeseries[ObjectId(self.realmAll_B)]['_id'] == ObjectId(
                        graphite_B)
                history = mockreq.request_history
                methods = {'POST': 0, 'GET': 0}
                for h in history:
                    methods[h.method] += 1
                assert {'POST': 1, 'GET': 1} == methods

                # create a dashboard for a host
                with app.test_request_context():
                    with requests_mock.mock() as mockreq:
                        ret = [{"id": 1, "orgId": 1, "name": graphite_B,
                                "type": "grafana-simple-json-datasource",
                                "typeLogoUrl": "public/plugins/grafana-simple-json-datasource/src/"
                                               "img/simpleJson_logo.svg",
                                "access": "proxy", "url": "http://127.0.0.1/glpi090/apirest.php",
                                "password": "", "user": "", "database": "", "basicAuth": True,
                                "basicAuthUser": "", "basicAuthPassword": "",
                                "withCredentials": False, "isDefault": True},
                               {"id": 2, "orgId": 1, "name": graphite_A_sub,
                                "type": "grafana-simple-json-datasource",
                                "typeLogoUrl": "public/plugins/grafana-simple-json-datasource/src/"
                                               "img/simpleJson_logo.svg",
                                "access": "proxy", "url": "http://127.0.0.1/glpi090/apirest.php",
                                "password": "", "user": "", "database": "", "basicAuth": True,
                                "basicAuthUser": "", "basicAuthPassword": "",
                                "withCredentials": False, "isDefault": False}]
                        mockreq.get('http://192.168.0.101:3000/api/datasources', json=ret)
                        mockreq.post('http://192.168.0.101:3000/api/datasources/db', json='true')
                        mockreq.post('http://192.168.0.101:3000/api/dashboards/db', json='true')
                        graf = Grafana(grafana)
                        assert not graf.create_dashboard(ObjectId(self.host_srv001))
                        assert graf.create_dashboard(ObjectId(self.host_srv002))
                        history = mockreq.request_history
                        methods = {'POST': 0, 'GET': 0}
                        for h in history:
                            methods[h.method] += 1
                            if h.method == 'POST':
                                dash = h.json()
                                assert len(dash['dashboard']['rows']) == 2
                        assert {'POST': 1, 'GET': 1} == methods
                    # check host and the service are tagged grafana and have the id
                    host_db = current_app.data.driver.db['host']
                    host002 = host_db.find_one({'_id': ObjectId(self.host_srv002)})
                    assert host002['ls_grafana']
                    assert host002['ls_grafana_panelid'] == 1
                    service_db = current_app.data.driver.db['service']
                    srv002 = service_db.find_one({'_id': ObjectId(self.host_srv002_srv)})
                    assert srv002['ls_grafana']
                    assert srv002['ls_grafana_panelid'] == 2
