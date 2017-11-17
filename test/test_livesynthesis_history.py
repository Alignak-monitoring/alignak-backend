#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This test verify the retention (history) of livesynthesis
"""

import os
import json
import time
import shlex
import subprocess
import copy
from datetime import datetime, timedelta
import requests
import unittest2
from eve.utils import date_to_str


class TestHookLivesynthesis(unittest2.TestCase):
    """
    This class test the hooks used to update livesynthesis resource
    """
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        # pylint: disable=too-many-locals
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
        os.environ['ALIGNAK_BACKEND_CONFIGURATION_FILE'] = \
            'test_livesynthesis_history_settings.json'

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

        # Add a new realm
        data = {"name": "All A", "_parent": cls.realm_all}
        response = requests.post(cls.endpoint + '/realm', json=data, headers=headers,
                                 auth=cls.auth)
        resp = response.json()
        cls.realm_all_a = resp['_id']

        # Add command
        data = json.loads(open('cfg/command_ping.json').read())
        data['_realm'] = cls.realm_all
        requests.post(cls.endpoint + '/command', json=data, headers=headers, auth=cls.auth)
        # Check if command right in backend
        response = requests.get(cls.endpoint + '/command', auth=cls.auth)
        resp = response.json()
        rc = resp['_items']

        # Add hosts
        data = json.loads(open('cfg/host_srv001.json').read())
        data['check_command'] = rc[0]['_id']
        if 'realm' in data:
            del data['realm']
        hosts = [
            {'name': 'srv001', '_realm': cls.realm_all},
            {'name': 'srv002', '_realm': cls.realm_all},
            {'name': 'srv003', '_realm': cls.realm_all},
            {'name': 'srv004', '_realm': cls.realm_all_a},
            {'name': 'srv005', '_realm': cls.realm_all_a},
            {'name': 'srv006', '_realm': cls.realm_all_a},
        ]
        myhostsid = {}
        myservicesid = {}
        myetags = {}
        for host in hosts:
            data['name'] = host['name']
            data['_realm'] = host['_realm']
            ret = requests.post(cls.endpoint + '/host', json=data, headers=headers, auth=cls.auth)
            resp = ret.json()
            myhostsid[host['name']] = resp['_id']
            myetags[host['name']] = resp['_etag']
            # add services
            for name in ['ping', 'ssh']:
                datas = json.loads(open('cfg/service_srv001_ping.json').read())
                datas['host'] = myhostsid[host['name']]
                datas['check_command'] = rc[0]['_id']
                datas['_realm'] = host['_realm']
                datas['name'] = name
                ret = requests.post(cls.endpoint + '/service', json=datas, headers=headers,
                                    auth=cls.auth)
                resp = ret.json()
                if host['name'] not in myservicesid:
                    myservicesid[host['name']] = {}
                myservicesid[host['name']][name] = resp['_id']
                myetags[host['name'] + '.' + name] = resp['_etag']

        sort_id = {'sort': '_id'}

        # get the 2 livesynthesis
        response = requests.get(cls.endpoint + '/livesynthesis', params=sort_id, auth=cls.auth)
        resp = response.json()
        rl = resp['_items']
        assert len(rl) == 2
        cls.ls_all = resp['_items'][0]['_id']
        cls.ls_all_a = resp['_items'][1]['_id']

        insert = 0

        # add in mongo some retention elements
        for item in rl:
            for i in range(15, 20):
                data = copy.deepcopy(item)
                data['livesynthesis'] = item['_id']
                for prop in ['_id', '_etag', '_created', '_updated', '_links', 'history',
                             '_realm']:
                    if prop in data:
                        del data[prop]
                data['_created'] = date_to_str(datetime.utcnow() - timedelta(seconds=60 * i))
                jsondata = shlex.split('mongo %s --eval "db.livesynthesisretention.insert'
                                       '("' % os.environ['ALIGNAK_BACKEND_MONGO_DBNAME'])
                jsondata[-1] = jsondata[-1] + json.dumps(data, separators=(',', ':')) + ")"
                jsondata[-1] = jsondata[-1].replace('"' + item['_id'] + '"',
                                                    "ObjectId('%s')" % item['_id'])
                insert += 1
                # print("insert %d" % insert)
                exit_code = subprocess.call(jsondata)
                assert exit_code == 0

        # update ls_* in services and hosts
        data = {
            'ls_state': 'DOWN',
            'ls_state_type': 'HARD',
            'ls_acknowledged': False,
            'ls_downtimed': False
        }
        for host in ['srv003', 'srv004', 'srv005']:
            response = requests.get(cls.endpoint + '/host',
                                    params={'where': json.dumps({'name': host})}, auth=cls.auth)
            resp = response.json()
            host_etag = resp['_items'][0]['_etag']
            myetags[host] = host_etag
            host_id = resp['_items'][0]['_id']
            headers_patch = {
                'Content-Type': 'application/json',
                'If-Match': host_etag
            }
            ret = requests.patch(cls.endpoint + '/host/' + host_id, json=data,
                                 headers=headers_patch, auth=cls.auth)
            resp = ret.json()
            assert resp['_status'] == 'OK'
            myetags[host] = resp['_etag']
            # update services on this host to be unreachable
            for service_name in ['ping', 'ssh']:
                response = requests.get(cls.endpoint + '/service',
                                        params={'where': json.dumps({'host': host_id,
                                                                     'name': service_name})},
                                        auth=cls.auth)
                resp = response.json()
                datas = {
                    'ls_state': 'UNREACHABLE',
                    'ls_state_type': 'HARD'
                }
                headers_patch = {
                    'Content-Type': 'application/json',
                    'If-Match': resp['_items'][0]['_etag']
                }
                ret = requests.patch(cls.endpoint + '/service/' + resp['_items'][0]['_id'],
                                     json=datas, headers=headers_patch, auth=cls.auth)
                resp = ret.json()
                assert resp['_status'] == 'OK'
                myetags[host + '.' + service_name] = resp['_etag']

        datas = {
            'ls_state': 'CRITICAL',
            'ls_state_type': 'HARD',
            'ls_acknowledged': False,
            'ls_downtimed': False
        }
        response = requests.get(cls.endpoint + '/service',
                                params={'where': json.dumps({'host': myhostsid['srv002'],
                                                             'name': 'ssh'})},
                                auth=cls.auth)
        resp = response.json()
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': resp['_items'][0]['_etag']
        }
        ret = requests.patch(cls.endpoint + '/service/' + myservicesid['srv002']['ssh'],
                             json=datas, headers=headers_patch, auth=cls.auth)
        resp = ret.json()
        assert resp['_status'] == 'OK'
        myetags['srv002.ssh'] = resp['_etag']

        response = requests.get(cls.endpoint + '/service',
                                params={'where': json.dumps({'host': myhostsid['srv006'],
                                                             'name': 'ping'})},
                                auth=cls.auth)
        resp = response.json()
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': resp['_items'][0]['_etag']
        }
        ret = requests.patch(cls.endpoint + '/service/' + myservicesid['srv006']['ping'],
                             json=datas, headers=headers_patch, auth=cls.auth)
        resp = ret.json()
        assert resp['_status'] == 'OK'
        myetags['srv006.ping'] = resp['_etag']

        datas = {
            'ls_state': 'WARNING',
            'ls_state_type': 'HARD',
            'ls_acknowledged': True,
            'ls_downtimed': False
        }
        response = requests.get(cls.endpoint + '/service',
                                params={'where': json.dumps({'host': myhostsid['srv002'],
                                                             'name': 'ping'})},
                                auth=cls.auth)
        resp = response.json()
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': resp['_items'][0]['_etag']
        }
        ret = requests.patch(cls.endpoint + '/service/' + myservicesid['srv002']['ping'],
                             json=datas, headers=headers_patch, auth=cls.auth)
        resp = ret.json()
        assert resp['_status'] == 'OK'
        myetags['srv002.ping'] = resp['_etag']

        response = requests.get(cls.endpoint + '/livesynthesis', params=sort_id, auth=cls.auth)
        resp = response.json()
        rl = resp['_items']
        for item in rl:
            for i in range(2, 15):
                data = copy.deepcopy(item)
                data['livesynthesis'] = item['_id']
                for prop in ['_id', '_etag', '_created', '_updated', '_links', 'history',
                             '_realm']:
                    if prop in data:
                        del data[prop]
                data['_created'] = date_to_str(datetime.utcnow() - timedelta(seconds=60 * i))
                jsondata = shlex.split(
                    'mongo %s --eval "db.livesynthesisretention.insert("' % os.environ[
                        'ALIGNAK_BACKEND_MONGO_DBNAME'])
                jsondata[-1] = jsondata[-1] + json.dumps(data, separators=(',', ':')) + ")"
                jsondata[-1] = jsondata[-1].replace('"' + item['_id'] + '"',
                                                    "ObjectId('%s')" % item['_id'])
                insert += 1
                # print("insert %d" % insert)
                exit_code = subprocess.call(jsondata)
                assert exit_code == 0

        datas = {
            'ls_state': 'CRITICAL',
            'ls_state_type': 'HARD',
            'ls_acknowledged': False,
            'ls_downtimed': False
        }
        response = requests.get(cls.endpoint + '/service',
                                params={'where': json.dumps({'host': myhostsid['srv001'],
                                                             'name': 'ssh'})},
                                auth=cls.auth)
        resp = response.json()
        headers_patch = {
            'Content-Type': 'application/json',
            'If-Match': resp['_items'][0]['_etag']
        }
        ret = requests.patch(cls.endpoint + '/service/' + myservicesid['srv001']['ssh'],
                             json=datas, headers=headers_patch, auth=cls.auth)
        resp = ret.json()
        assert resp['_status'] == 'OK'
        myetags['srv001.ssh'] = resp['_etag']

        response = requests.get(cls.endpoint + '/livesynthesis', params=sort_id, auth=cls.auth)
        resp = response.json()
        rl = resp['_items']
        for item in rl:
            for i in range(1, 2):
                data = copy.deepcopy(item)
                data['livesynthesis'] = item['_id']
                for prop in ['_id', '_etag', '_created', '_updated', '_links', 'history',
                             '_realm']:
                    if prop in data:
                        del data[prop]
                data['_created'] = date_to_str(datetime.utcnow() - timedelta(seconds=60 * i))
                jsondata = shlex.split(
                    'mongo %s --eval "db.livesynthesisretention.insert("' % os.environ[
                        'ALIGNAK_BACKEND_MONGO_DBNAME'])
                jsondata[-1] = jsondata[-1] + json.dumps(data, separators=(',', ':')) + ")"
                jsondata[-1] = jsondata[-1].replace('"' + item['_id'] + '"',
                                                    "ObjectId('%s')" % item['_id'])
                insert += 1
                # print("insert %d" % insert)
                exit_code = subprocess.call(jsondata)
                assert exit_code == 0

    @classmethod
    def tearDownClass(cls):
        """
        Kill uwsgi

        :return: None
        """
        subprocess.call(['uwsgi', '--stop', '/tmp/uwsgi.pid'])
        time.sleep(2)

    def test_01_get_history_realm_all(self):
        """
        Test get all resources and one item have all history in the response

        :return: None
        """
        response = requests.get(self.endpoint + '/livesynthesis/' + self.ls_all, auth=self.auth)
        resp = response.json()
        ref = {
            u'hosts_total': 3,
            u'hosts_not_monitored': 0,
            u'hosts_up_hard': 0,
            u'hosts_up_soft': 0,
            u'hosts_down_hard': 1,
            u'hosts_down_soft': 0,
            u'hosts_unreachable_hard': 2,
            u'hosts_unreachable_soft': 0,
            u'hosts_acknowledged': 0,
            u'hosts_in_downtime': 0,
            u'hosts_flapping': 0,
            u'hosts_business_impact': 0,
            u'services_total': 6,
            u'services_not_monitored': 0,
            u'services_ok_hard': 0,
            u'services_ok_soft': 0,
            u'services_warning_hard': 0,
            u'services_warning_soft': 0,
            u'services_critical_hard': 2,
            u'services_critical_soft': 0,
            u'services_unknown_hard': 1,
            u'services_unknown_soft': 0,
            u'services_unreachable_hard': 2,
            u'services_unreachable_soft': 0,
            u'services_acknowledged': 1,
            u'services_in_downtime': 0,
            u'services_flapping': 0,
            u'services_business_impact': 0
        }
        for prop in copy.copy(resp):
            if prop.startswith('_'):
                del resp[prop]
        self.assertItemsEqual(ref, resp)
        self.assertEqual(ref, resp)

        # get livesynthesis realm All with history
        response = requests.get(self.endpoint + '/livesynthesis/' + self.ls_all,
                                params={'history': 1}, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['history']), 19)
        ref_middle = {
            u'hosts_total': 3,
            u'hosts_not_monitored': 0,
            u'hosts_up_hard': 0,
            u'hosts_up_soft': 0,
            u'hosts_down_hard': 1,
            u'hosts_down_soft': 0,
            u'hosts_unreachable_hard': 2,
            u'hosts_unreachable_soft': 0,
            u'hosts_acknowledged': 0,
            u'hosts_in_downtime': 0,
            u'hosts_flapping': 0,
            u'hosts_business_impact': 0,
            u'services_total': 6,
            u'services_not_monitored': 0,
            u'services_ok_hard': 0,
            u'services_ok_soft': 0,
            u'services_warning_hard': 0,
            u'services_warning_soft': 0,
            u'services_critical_hard': 1,
            u'services_critical_soft': 0,
            u'services_unknown_hard': 2,
            u'services_unknown_soft': 0,
            u'services_unreachable_hard': 2,
            u'services_unreachable_soft': 0,
            u'services_acknowledged': 1,
            u'services_in_downtime': 0,
            u'services_flapping': 0,
            u'services_business_impact': 0
        }
        ref_old = {
            u'hosts_total': 3,
            u'hosts_not_monitored': 0,
            u'hosts_up_hard': 0,
            u'hosts_up_soft': 0,
            u'hosts_down_hard': 0,
            u'hosts_down_soft': 0,
            u'hosts_unreachable_hard': 3,
            u'hosts_unreachable_soft': 0,
            u'hosts_acknowledged': 0,
            u'hosts_in_downtime': 0,
            u'hosts_flapping': 0,
            u'hosts_business_impact': 0,
            u'services_total': 6,
            u'services_not_monitored': 0,
            u'services_ok_hard': 0,
            u'services_ok_soft': 0,
            u'services_warning_hard': 0,
            u'services_warning_soft': 0,
            u'services_critical_hard': 0,
            u'services_critical_soft': 0,
            u'services_unknown_hard': 6,
            u'services_unknown_soft': 0,
            u'services_unreachable_hard': 0,
            u'services_unreachable_soft': 0,
            u'services_acknowledged': 0,
            u'services_in_downtime': 0,
            u'services_flapping': 0,
            u'services_business_impact': 0
        }
        del resp['history'][0]['_created']
        self.assertEqual(resp['history'][0], ref)
        for i in range(2, 15):
            del resp['history'][(i - 1)]['_created']
            self.assertEqual(resp['history'][(i - 1)], ref_middle)
        for i in range(15, 20):
            del resp['history'][(i - 1)]['_created']
            self.assertEqual(resp['history'][(i - 1)], ref_old)

    def test_02_get_history_realm_all_a(self):
        """
        Test get all resources and one item have all history in the response

        :return: None
        """
        response = requests.get(self.endpoint + '/livesynthesis/' + self.ls_all_a, auth=self.auth)
        resp = response.json()
        ref = {
            u'hosts_total': 3,
            u'hosts_not_monitored': 0,
            u'hosts_up_hard': 0,
            u'hosts_up_soft': 0,
            u'hosts_down_hard': 2,
            u'hosts_down_soft': 0,
            u'hosts_unreachable_hard': 1,
            u'hosts_unreachable_soft': 0,
            u'hosts_acknowledged': 0,
            u'hosts_in_downtime': 0,
            u'hosts_flapping': 0,
            u'hosts_business_impact': 0,
            u'services_total': 6,
            u'services_not_monitored': 0,
            u'services_ok_hard': 0,
            u'services_ok_soft': 0,
            u'services_warning_hard': 0,
            u'services_warning_soft': 0,
            u'services_critical_hard': 1,
            u'services_critical_soft': 0,
            u'services_unknown_hard': 1,
            u'services_unknown_soft': 0,
            u'services_unreachable_hard': 4,
            u'services_unreachable_soft': 0,
            u'services_acknowledged': 0,
            u'services_in_downtime': 0,
            u'services_flapping': 0,
            u'services_business_impact': 0
        }
        for prop in copy.copy(resp):
            if prop.startswith('_'):
                del resp[prop]
        self.assertItemsEqual(ref, resp)
        self.assertEqual(ref, resp)

        # get livesynthesis realm All with history
        response = requests.get(self.endpoint + '/livesynthesis/' + self.ls_all_a,
                                params={'history': 1}, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['history']), 19)
        ref_middle = {
            u'hosts_total': 3,
            u'hosts_not_monitored': 0,
            u'hosts_up_hard': 0,
            u'hosts_up_soft': 0,
            u'hosts_down_hard': 2,
            u'hosts_down_soft': 0,
            u'hosts_unreachable_hard': 1,
            u'hosts_unreachable_soft': 0,
            u'hosts_acknowledged': 0,
            u'hosts_in_downtime': 0,
            u'hosts_flapping': 0,
            u'hosts_business_impact': 0,
            u'services_total': 6,
            u'services_not_monitored': 0,
            u'services_ok_hard': 0,
            u'services_ok_soft': 0,
            u'services_warning_hard': 0,
            u'services_warning_soft': 0,
            u'services_critical_hard': 1,
            u'services_critical_soft': 0,
            u'services_unknown_hard': 1,
            u'services_unknown_soft': 0,
            u'services_unreachable_hard': 4,
            u'services_unreachable_soft': 0,
            u'services_acknowledged': 0,
            u'services_in_downtime': 0,
            u'services_flapping': 0,
            u'services_business_impact': 0
        }
        ref_old = {
            u'hosts_total': 3,
            u'hosts_not_monitored': 0,
            u'hosts_up_hard': 0,
            u'hosts_up_soft': 0,
            u'hosts_down_hard': 0,
            u'hosts_down_soft': 0,
            u'hosts_unreachable_hard': 3,
            u'hosts_unreachable_soft': 0,
            u'hosts_acknowledged': 0,
            u'hosts_in_downtime': 0,
            u'hosts_flapping': 0,
            u'hosts_business_impact': 0,
            u'services_total': 6,
            u'services_not_monitored': 0,
            u'services_ok_hard': 0,
            u'services_ok_soft': 0,
            u'services_warning_hard': 0,
            u'services_warning_soft': 0,
            u'services_critical_hard': 0,
            u'services_critical_soft': 0,
            u'services_unknown_hard': 6,
            u'services_unknown_soft': 0,
            u'services_unreachable_hard': 0,
            u'services_unreachable_soft': 0,
            u'services_acknowledged': 0,
            u'services_in_downtime': 0,
            u'services_flapping': 0,
            u'services_business_impact': 0
        }
        del resp['history'][0]['_created']
        self.assertEqual(resp['history'][0], ref)
        for i in range(2, 15):
            del resp['history'][(i - 1)]['_created']
            self.assertEqual(resp['history'][(i - 1)], ref_middle)
        for i in range(15, 20):
            del resp['history'][(i - 1)]['_created']
            self.assertEqual(resp['history'][(i - 1)], ref_old)

    def test_03_get_concatenation(self):
        """
        Test get item give concatenation of all livesynthesis in children realm

        :return: None
        """
        response = requests.get(self.endpoint + '/livesynthesis/' + self.ls_all,
                                params={'concatenation': 1}, auth=self.auth)
        resp = response.json()
        ref = {
            u'hosts_total': 6,
            u'hosts_not_monitored': 0,
            u'hosts_up_hard': 0,
            u'hosts_up_soft': 0,
            u'hosts_down_hard': 3,
            u'hosts_down_soft': 0,
            u'hosts_unreachable_hard': 3,
            u'hosts_unreachable_soft': 0,
            u'hosts_acknowledged': 0,
            u'hosts_in_downtime': 0,
            u'hosts_flapping': 0,
            u'hosts_business_impact': 0,
            u'services_total': 12,
            u'services_not_monitored': 0,
            u'services_ok_hard': 0,
            u'services_ok_soft': 0,
            u'services_warning_hard': 0,
            u'services_warning_soft': 0,
            u'services_critical_hard': 3,
            u'services_critical_soft': 0,
            u'services_unknown_hard': 2,
            u'services_unknown_soft': 0,
            u'services_unreachable_hard': 6,
            u'services_unreachable_soft': 0,
            u'services_acknowledged': 1,
            u'services_in_downtime': 0,
            u'services_flapping': 0,
            u'services_business_impact': 0
        }
        for prop in copy.copy(resp):
            if prop.startswith('_'):
                del resp[prop]
        self.assertItemsEqual(ref, resp)
        self.assertEqual(ref, resp)

    def test_04_get_history_concatenation(self):
        """
        Test get item give concatenation of all livesynthesis in children realm +
        concatenated history

        :return: None
        """
        response = requests.get(self.endpoint + '/livesynthesis/' + self.ls_all,
                                params={'concatenation': 1, 'history': 1}, auth=self.auth)
        resp = response.json()
        ref = {
            u'hosts_total': 6,
            u'hosts_not_monitored': 0,
            u'hosts_up_hard': 0,
            u'hosts_up_soft': 0,
            u'hosts_down_hard': 3,
            u'hosts_down_soft': 0,
            u'hosts_unreachable_hard': 3,
            u'hosts_unreachable_soft': 0,
            u'hosts_acknowledged': 0,
            u'hosts_in_downtime': 0,
            u'hosts_flapping': 0,
            u'hosts_business_impact': 0,
            u'services_total': 12,
            u'services_not_monitored': 0,
            u'services_ok_hard': 0,
            u'services_ok_soft': 0,
            u'services_warning_hard': 0,
            u'services_warning_soft': 0,
            u'services_critical_hard': 3,
            u'services_critical_soft': 0,
            u'services_unknown_hard': 2,
            u'services_unknown_soft': 0,
            u'services_unreachable_hard': 6,
            u'services_unreachable_soft': 0,
            u'services_acknowledged': 1,
            u'services_in_downtime': 0,
            u'services_flapping': 0,
            u'services_business_impact': 0
        }
        ref_middle = {
            u'hosts_total': 6,
            u'hosts_not_monitored': 0,
            u'hosts_up_hard': 0,
            u'hosts_up_soft': 0,
            u'hosts_down_hard': 3,
            u'hosts_down_soft': 0,
            u'hosts_unreachable_hard': 3,
            u'hosts_unreachable_soft': 0,
            u'hosts_acknowledged': 0,
            u'hosts_in_downtime': 0,
            u'hosts_flapping': 0,
            u'hosts_business_impact': 0,
            u'services_total': 12,
            u'services_not_monitored': 0,
            u'services_ok_hard': 0,
            u'services_ok_soft': 0,
            u'services_warning_hard': 0,
            u'services_warning_soft': 0,
            u'services_critical_hard': 2,
            u'services_critical_soft': 0,
            u'services_unknown_hard': 3,
            u'services_unknown_soft': 0,
            u'services_unreachable_hard': 6,
            u'services_unreachable_soft': 0,
            u'services_acknowledged': 1,
            u'services_in_downtime': 0,
            u'services_flapping': 0,
            u'services_business_impact': 0
        }
        ref_old = {
            u'hosts_total': 6,
            u'hosts_not_monitored': 0,
            u'hosts_up_hard': 0,
            u'hosts_up_soft': 0,
            u'hosts_down_hard': 0,
            u'hosts_down_soft': 0,
            u'hosts_unreachable_hard': 6,
            u'hosts_unreachable_soft': 0,
            u'hosts_acknowledged': 0,
            u'hosts_in_downtime': 0,
            u'hosts_flapping': 0,
            u'hosts_business_impact': 0,
            u'services_total': 12,
            u'services_not_monitored': 0,
            u'services_ok_hard': 0,
            u'services_ok_soft': 0,
            u'services_warning_hard': 0,
            u'services_warning_soft': 0,
            u'services_critical_hard': 0,
            u'services_critical_soft': 0,
            u'services_unknown_hard': 12,
            u'services_unknown_soft': 0,
            u'services_unreachable_hard': 0,
            u'services_unreachable_soft': 0,
            u'services_acknowledged': 0,
            u'services_in_downtime': 0,
            u'services_flapping': 0,
            u'services_business_impact': 0
        }
        del resp['history'][0]['_created']
        self.assertEqual(resp['history'][0], ref)
        for i in range(2, 15):
            del resp['history'][(i - 1)]['_created']
            self.assertEqual(resp['history'][(i - 1)], ref_middle)
        for i in range(15, 20):
            del resp['history'][(i - 1)]['_created']
            self.assertEqual(resp['history'][(i - 1)], ref_old)

    def test_05_get_concatenation_restrict_user(self):
        # pylint: disable=too-many-locals
        """
        Test get item give concatenation of all livesynthesis when have restricted account

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        # get user admin
        response = requests.get(self.endpoint + '/user', auth=self.auth)
        resp = response.json()
        user_admin = resp['_items'][0]

        # Add users
        # User 1 - realm All with sub-realms
        data = {'name': 'user1', 'password': 'test', 'back_role_super_admin': False,
                '_realm': self.realm_all, '_sub_realm': True}
        requests.post(self.endpoint + '/user', json=data, headers=headers, auth=self.auth)
        # User 2 - realm All with no sub-realms
        data = {'name': 'user2', 'password': 'test', 'back_role_super_admin': False,
                '_realm': self.realm_all, '_sub_realm': False}
        requests.post(self.endpoint + '/user', json=data, headers=headers, auth=self.auth)

        params = {'username': 'user1', 'password': 'test', 'action': 'generate'}
        # get token user 1
        response = requests.post(self.endpoint + '/login', json=params, headers=headers)
        resp = response.json()
        user1_auth = requests.auth.HTTPBasicAuth(resp['token'], '')

        params = {'username': 'user2', 'password': 'test', 'action': 'generate'}
        # get token user 2
        response = requests.post(self.endpoint + '/login', json=params, headers=headers)
        resp = response.json()
        user2_auth = requests.auth.HTTPBasicAuth(resp['token'], '')

        # get livesynthesis concatenation with user 1 (restrictrole + subrealm)
        response = requests.get(self.endpoint + '/livesynthesis/' + self.ls_all,
                                params={'concatenation': 1}, auth=user1_auth)
        resp = response.json()
        ref = {
            u'hosts_total': 6,
            u'hosts_not_monitored': 0,
            u'hosts_up_hard': 0,
            u'hosts_up_soft': 0,
            u'hosts_down_hard': 3,
            u'hosts_down_soft': 0,
            u'hosts_unreachable_hard': 3,
            u'hosts_unreachable_soft': 0,
            u'hosts_acknowledged': 0,
            u'hosts_in_downtime': 0,
            u'hosts_flapping': 0,
            u'hosts_business_impact': 0,
            u'services_total': 12,
            u'services_not_monitored': 0,
            u'services_ok_hard': 0,
            u'services_ok_soft': 0,
            u'services_warning_hard': 0,
            u'services_warning_soft': 0,
            u'services_critical_hard': 3,
            u'services_critical_soft': 0,
            u'services_unknown_hard': 2,
            u'services_unknown_soft': 0,
            u'services_unreachable_hard': 6,
            u'services_unreachable_soft': 0,
            u'services_acknowledged': 1,
            u'services_in_downtime': 0,
            u'services_flapping': 0,
            u'services_business_impact': 0
        }
        for prop in copy.copy(resp):
            if prop.startswith('_'):
                del resp[prop]
        self.assertItemsEqual(ref, resp)
        self.assertEqual(ref, resp)

        # get livesynthesis concatenation with user 2 (restrictrole + no subrealm)
        response = requests.get(self.endpoint + '/livesynthesis/' + self.ls_all,
                                params={'concatenation': 1}, auth=user2_auth)
        resp = response.json()
        ref = {
            u'hosts_total': 3,
            u'hosts_not_monitored': 0,
            u'hosts_up_hard': 0,
            u'hosts_up_soft': 0,
            u'hosts_down_hard': 1,
            u'hosts_down_soft': 0,
            u'hosts_unreachable_hard': 2,
            u'hosts_unreachable_soft': 0,
            u'hosts_acknowledged': 0,
            u'hosts_in_downtime': 0,
            u'hosts_flapping': 0,
            u'hosts_business_impact': 0,
            u'services_total': 6,
            u'services_not_monitored': 0,
            u'services_ok_hard': 0,
            u'services_ok_soft': 0,
            u'services_warning_hard': 0,
            u'services_warning_soft': 0,
            u'services_critical_hard': 2,
            u'services_critical_soft': 0,
            u'services_unknown_hard': 1,
            u'services_unknown_soft': 0,
            u'services_unreachable_hard': 2,
            u'services_unreachable_soft': 0,
            u'services_acknowledged': 1,
            u'services_in_downtime': 0,
            u'services_flapping': 0,
            u'services_business_impact': 0
        }
        for prop in copy.copy(resp):
            if prop.startswith('_'):
                del resp[prop]
        self.assertItemsEqual(ref, resp)
        self.assertEqual(ref, resp)

        # test with user have restricted read on livesynthesis

        # User 3
        data = {'name': 'user3', 'password': 'test', 'back_role_super_admin': False,
                'host_notification_period': user_admin['host_notification_period'],
                'service_notification_period': user_admin['service_notification_period'],
                '_realm': self.realm_all}
        response = requests.post(self.endpoint + '/user', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        user3_id = resp['_id']
        data = {'user': resp['_id'], 'realm': self.realm_all, 'resource': '*', 'crud': ['custom'],
                'sub_realm': True}
        requests.post(self.endpoint + '/userrestrictrole', json=data, headers=headers,
                      auth=self.auth)
        params = {'username': 'user3', 'password': 'test', 'action': 'generate'}
        # get token user 3
        response = requests.post(self.endpoint + '/login', json=params, headers=headers)
        resp = response.json()
        user3_auth = requests.auth.HTTPBasicAuth(resp['token'], '')

        response = requests.get(self.endpoint + '/livesynthesis', auth=self.auth)
        resp = response.json()
        for item in resp['_items']:
            headers_patch = {
                'Content-Type': 'application/json',
                'If-Match': item['_etag']
            }
            datap = {'_users_read': [user3_id]}
            ret = requests.patch(self.endpoint + '/livesynthesis/' + item['_id'], json=datap,
                                 headers=headers_patch, auth=self.auth)
            resp = ret.json()
            assert resp['_status'] == 'OK'

        response = requests.get(self.endpoint + '/livesynthesis/' + self.ls_all,
                                params={'concatenation': 1}, auth=user3_auth)
        resp = response.json()
        ref = {
            u'hosts_total': 6,
            u'hosts_not_monitored': 0,
            u'hosts_up_hard': 0,
            u'hosts_up_soft': 0,
            u'hosts_down_hard': 3,
            u'hosts_down_soft': 0,
            u'hosts_unreachable_hard': 3,
            u'hosts_unreachable_soft': 0,
            u'hosts_acknowledged': 0,
            u'hosts_in_downtime': 0,
            u'hosts_flapping': 0,
            u'hosts_business_impact': 0,
            u'services_total': 12,
            u'services_not_monitored': 0,
            u'services_ok_hard': 0,
            u'services_ok_soft': 0,
            u'services_warning_hard': 0,
            u'services_warning_soft': 0,
            u'services_critical_hard': 3,
            u'services_critical_soft': 0,
            u'services_unknown_hard': 2,
            u'services_unknown_soft': 0,
            u'services_unreachable_hard': 6,
            u'services_unreachable_soft': 0,
            u'services_acknowledged': 1,
            u'services_in_downtime': 0,
            u'services_flapping': 0,
            u'services_business_impact': 0
        }
        for prop in copy.copy(resp):
            if prop.startswith('_'):
                del resp[prop]
        self.assertItemsEqual(ref, resp)
        self.assertEqual(ref, resp)

    def test_06_cron_retention(self):
        """
        Test the cron create new entry in retention and delete old values

        :return: None
        """
        response = requests.get(self.endpoint + '/livesynthesis/' + self.ls_all,
                                params={'history': 1}, auth=self.auth)
        resp = response.json()
        history_count = len(resp['history'])
        last_history_date = resp['history'][0]['_created']

        response = requests.get(self.endpoint + '/cron_livesynthesis_history')
        resp = response.json()

        response = requests.get(self.endpoint + '/livesynthesis/' + self.ls_all,
                                params={'history': 1}, auth=self.auth)
        resp = response.json()
        self.assertEqual(len(resp['history']), (history_count + 1))
        self.assertGreater(resp['history'][0]['_created'], last_history_date)
