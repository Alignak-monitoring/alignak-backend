#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This test check the realms and the tree feature of realms (children)
"""

from __future__ import print_function
import os
import time
import shlex
import subprocess
import copy
import requests
import unittest2


class TestRealms(unittest2.TestCase):
    """
    This class test realms and tree feature
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
        cls.realmAll_id = resp['_items'][0]['_id']

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
            if realm['_level'] > 0:
                headers = {'If-Match': realm['_etag']}
                response = requests.delete(cls.endpoint + '/realm/' + realm['_id'], headers=headers,
                                           auth=cls.auth)

    def test_add_realm(self):
        # pylint: disable=too-many-locals
        """
        Test add realms, add children, check than we can't delete a realm if it has children

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_name = {'sort': 'name'}
        sort_level = {'sort': '_level'}

        response = requests.get(self.endpoint + '/realm', params=sort_level, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 1)

        # * Add sub_realms
        data = {"name": "All A", "_parent": self.realmAll_id}
        response = requests.post(self.endpoint + '/realm', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        realmAll_A_id = copy.copy(resp['_id'])

        response = requests.get(self.endpoint + '/realm', params=sort_level, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(re[1]['name'], "All A")
        self.assertEqual(re[1]['_parent'], self.realmAll_id)
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.realmAll_id])
        self.assertEqual(re[1]['_children'], [])

        # ** Realm All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_level'], 0)
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_children'], [realmAll_A_id])
        self.assertEqual(re[0]['_all_children'], [realmAll_A_id])
        # ** Realm All A
        self.assertEqual(re[1]['name'], "All A")
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.realmAll_id])
        self.assertEqual(re[1]['_children'], [])

        data = {"name": "All B", "_parent": self.realmAll_id}
        response = requests.post(self.endpoint + '/realm', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        realmAll_B_id = copy.copy(resp['_id'])

        response = requests.get(self.endpoint + '/realm', params=sort_level, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 3)

        # ** Realm All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_level'], 0)
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_children'], [realmAll_A_id, realmAll_B_id])
        self.assertEqual(re[0]['_all_children'], [realmAll_A_id, realmAll_B_id])
        # ** Realm All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.realmAll_id])
        self.assertEqual(re[1]['_children'], [])
        self.assertEqual(re[1]['_all_children'], [])
        # ** Realm All B
        self.assertEqual(re[2]['name'], 'All B')
        self.assertEqual(re[2]['_level'], 1)
        self.assertEqual(re[2]['_tree_parents'], [self.realmAll_id])
        self.assertEqual(re[2]['_children'], [])
        self.assertEqual(re[2]['_children'], [])

        # Sub realm without _parent
        data = {"name": "All C"}
        response = requests.post(self.endpoint + '/realm', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        realmAll_C_id = copy.copy(resp['_id'])

        response = requests.get(self.endpoint + '/realm/' + resp['_id'], auth=self.auth)
        re = response.json()
        self.assertEqual(re['name'], "All C")
        self.assertEqual(re['_parent'], self.realmAll_id)
        self.assertEqual(re['_level'], 1)
        self.assertEqual(re['_tree_parents'], [self.realmAll_id])
        self.assertEqual(re['_children'], [])

        # Get all realms
        response = requests.get(self.endpoint + '/realm', params=sort_level, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 4)

        # ** Realm All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_level'], 0)
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_children'], [realmAll_A_id, realmAll_B_id, realmAll_C_id])
        self.assertEqual(re[0]['_all_children'], [realmAll_A_id, realmAll_B_id, realmAll_C_id])
        # ** Realm All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.realmAll_id])
        self.assertEqual(re[1]['_children'], [])
        self.assertEqual(re[1]['_all_children'], [])
        # ** Realm All B
        self.assertEqual(re[2]['name'], 'All B')
        self.assertEqual(re[2]['_level'], 1)
        self.assertEqual(re[2]['_tree_parents'], [self.realmAll_id])
        self.assertEqual(re[2]['_children'], [])
        self.assertEqual(re[2]['_all_children'], [])
        # ** Realm All C
        self.assertEqual(re[3]['name'], 'All C')
        self.assertEqual(re[3]['_level'], 1)
        self.assertEqual(re[3]['_tree_parents'], [self.realmAll_id])
        self.assertEqual(re[3]['_children'], [])
        self.assertEqual(re[3]['_all_children'], [])

        # ** Add sub_sub_realms
        data = {"name": "All A1", "_parent": realmAll_A_id}
        requests.post(self.endpoint + '/realm', json=data, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/realm', params=sort_name, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        for item in re:
            print("Item: %s (%s)" % (item['_id'], item['name']))
        self.assertEqual(re[2]['name'], "All A1")
        self.assertEqual(re[2]['_parent'], realmAll_A_id)
        self.assertEqual(re[2]['_level'], 2)
        self.assertEqual(re[2]['_tree_parents'], [self.realmAll_id, realmAll_A_id])
        self.assertEqual(re[2]['_children'], [])
        realmAll_A1_id = copy.copy(re[2]['_id'])

        # ** Realm All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_level'], 0)
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_children'], [realmAll_A_id, realmAll_B_id, realmAll_C_id])
        self.assertEqual(re[0]['_all_children'], [
            realmAll_A_id, realmAll_B_id, realmAll_C_id, realmAll_A1_id
        ])
        # ** Realm All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.realmAll_id])
        self.assertEqual(re[1]['_children'], [realmAll_A1_id])
        self.assertEqual(re[1]['_all_children'], [realmAll_A1_id])
        # ** Realm All A1
        self.assertEqual(re[2]['name'], 'All A1')
        self.assertEqual(re[2]['_level'], 2)
        self.assertEqual(re[2]['_tree_parents'], [self.realmAll_id, realmAll_A_id])
        self.assertEqual(re[2]['_children'], [])
        self.assertEqual(re[2]['_all_children'], [])
        # ** Realm All B
        self.assertEqual(re[3]['name'], 'All B')
        self.assertEqual(re[3]['_level'], 1)
        self.assertEqual(re[3]['_tree_parents'], [self.realmAll_id])
        self.assertEqual(re[3]['_children'], [])
        self.assertEqual(re[3]['_all_children'], [])
        # ** Realm All C
        self.assertEqual(re[4]['name'], 'All C')
        self.assertEqual(re[4]['_level'], 1)
        self.assertEqual(re[4]['_tree_parents'], [self.realmAll_id])
        self.assertEqual(re[4]['_children'], [])
        self.assertEqual(re[4]['_all_children'], [])

        # *** Add sub_sub_sub_realms
        data = {"name": "All A1a", "_parent": realmAll_A1_id}
        requests.post(self.endpoint + '/realm', json=data, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/realm', params=sort_name, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        for item in re:
            print("Item: %s (%s)" % (item['_id'], item['name']))
        self.assertEqual(len(re), 6)
        self.assertEqual(re[3]['name'], "All A1a")
        self.assertEqual(re[3]['_parent'], realmAll_A1_id)
        self.assertEqual(re[3]['_level'], 3)
        self.assertEqual(re[3]['_tree_parents'], [self.realmAll_id, realmAll_A_id, realmAll_A1_id])
        self.assertEqual(re[3]['_children'], [])
        realmAll_A1a_id = copy.copy(re[3]['_id'])
        realmAll_A1a_etag = copy.copy(re[3]['_etag'])

        self.assertEqual(re[2]['name'], "All A1")
        realmAll_A1_etag = copy.copy(re[2]['_etag'])

        # ** Realm All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_level'], 0)
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_children'], [realmAll_A_id, realmAll_B_id, realmAll_C_id])
        self.assertEqual(re[0]['_all_children'], [
            realmAll_A_id, realmAll_B_id, realmAll_C_id, realmAll_A1_id, realmAll_A1a_id
        ])
        # ** Realm All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.realmAll_id])
        self.assertEqual(re[1]['_children'], [realmAll_A1_id])
        self.assertEqual(re[1]['_all_children'], [realmAll_A1_id, realmAll_A1a_id])
        # ** Realm All A1
        self.assertEqual(re[2]['name'], 'All A1')
        self.assertEqual(re[2]['_level'], 2)
        self.assertEqual(re[2]['_tree_parents'], [self.realmAll_id, realmAll_A_id])
        self.assertEqual(re[2]['_children'], [realmAll_A1a_id])
        self.assertEqual(re[2]['_all_children'], [realmAll_A1a_id])
        # ** Realm All A1a
        self.assertEqual(re[3]['name'], 'All A1a')
        self.assertEqual(re[3]['_level'], 3)
        self.assertEqual(re[3]['_tree_parents'], [self.realmAll_id, realmAll_A_id, realmAll_A1_id])
        self.assertEqual(re[3]['_children'], [])
        self.assertEqual(re[3]['_all_children'], [])
        # ** Realm All B
        self.assertEqual(re[4]['name'], 'All B')
        self.assertEqual(re[4]['_level'], 1)
        self.assertEqual(re[4]['_tree_parents'], [self.realmAll_id])
        self.assertEqual(re[4]['_children'], [])
        self.assertEqual(re[4]['_all_children'], [])
        # ** Realm All C
        self.assertEqual(re[5]['name'], 'All C')
        self.assertEqual(re[5]['_level'], 1)
        self.assertEqual(re[5]['_tree_parents'], [self.realmAll_id])
        self.assertEqual(re[5]['_children'], [])
        self.assertEqual(re[5]['_all_children'], [])

        # Delete 'All A1' will not work because it has sub realms
        headers = {'If-Match': realmAll_A1_etag}
        response = requests.delete(self.endpoint + '/realm/' + realmAll_A1_id, headers=headers,
                                   auth=self.auth)
        resp = response.json()
        self.assertEqual(resp['_status'], "ERR")

        # Delete All A1a (can be deleted and remove ref to parents)
        print("Before deletion")
        headers = {'If-Match': realmAll_A1a_etag}
        response = requests.delete(self.endpoint + '/realm/' + realmAll_A1a_id, headers=headers,
                                   auth=self.auth)
        print("Response: %s / %s" % (response, response.content))
        self.assertEqual(response.status_code, 204)

        response = requests.get(self.endpoint + '/realm', params=sort_name, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 5)

        # ** Realm All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_children'], [realmAll_A_id, realmAll_B_id, realmAll_C_id])
        self.assertEqual(re[0]['_all_children'], [
            realmAll_A_id, realmAll_B_id, realmAll_C_id, realmAll_A1_id
        ])
        # ** Realm All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.realmAll_id])
        self.assertEqual(re[1]['_children'], [realmAll_A1_id])
        self.assertEqual(re[1]['_all_children'], [realmAll_A1_id])
        # ** Realm All A1
        self.assertEqual(re[2]['name'], 'All A1')
        self.assertEqual(re[2]['_level'], 2)
        self.assertEqual(re[2]['_tree_parents'], [self.realmAll_id, realmAll_A_id])
        self.assertEqual(re[2]['_children'], [])
        self.assertEqual(re[2]['_all_children'], [])
        # ** Realm All B
        self.assertEqual(re[3]['name'], 'All B')
        self.assertEqual(re[3]['_level'], 1)
        self.assertEqual(re[3]['_tree_parents'], [self.realmAll_id])
        self.assertEqual(re[3]['_children'], [])
        self.assertEqual(re[3]['_all_children'], [])
        # ** Realm All C
        self.assertEqual(re[4]['name'], 'All C')
        self.assertEqual(re[4]['_level'], 1)
        self.assertEqual(re[4]['_tree_parents'], [self.realmAll_id])
        self.assertEqual(re[4]['_children'], [])
        self.assertEqual(re[4]['_all_children'], [])

        # Check that we can't update _tree_parents of a realm manually
        response = requests.get(self.endpoint + '/realm', params={'where': '{"name":"All A1"}'},
                                auth=self.auth)
        resp = response.json()
        re = resp['_items']
        data = {'_tree_parents': []}
        headers = {
            'Content-Type': 'application/json',
            'If-Match': re[0]['_etag']
        }
        response = requests.patch(self.endpoint + '/realm/' + realmAll_A1_id, json=data,
                                  headers=headers, auth=self.auth)
        self.assertEqual(response.status_code, 412)
        self.assertEqual(response.text, 'Updating _tree_parents is forbidden')

        # Check that we can't update _children of a realm manually
        response = requests.get(self.endpoint + '/realm', params={'where': '{"name":"All A1"}'},
                                auth=self.auth)
        resp = response.json()
        re = resp['_items']
        data = {'_children': []}
        headers = {
            'Content-Type': 'application/json',
            'If-Match': re[0]['_etag']
        }
        response = requests.patch(self.endpoint + '/realm/' + realmAll_A1_id, json=data,
                                  headers=headers, auth=self.auth)
        self.assertEqual(response.status_code, 412)
        self.assertEqual(response.text, 'Updating _children is forbidden')

        # Check that we can't update _all_children of a realm manually
        response = requests.get(self.endpoint + '/realm', params={'where': '{"name":"All A1"}'},
                                auth=self.auth)
        resp = response.json()
        re = resp['_items']
        data = {'_all_children': []}
        headers = {
            'Content-Type': 'application/json',
            'If-Match': re[0]['_etag']
        }
        response = requests.patch(self.endpoint + '/realm/' + realmAll_A1_id, json=data,
                                  headers=headers, auth=self.auth)
        self.assertEqual(response.status_code, 412)
        self.assertEqual(response.text, 'Updating _all_children is forbidden')

        # Update realm name
        response = requests.get(self.endpoint + '/realm', params={'where': '{"name":"All A1"}'},
                                auth=self.auth)
        resp = response.json()
        re = resp['_items']
        data = {'name': "All B1"}
        headers = {
            'Content-Type': 'application/json',
            'If-Match': re[0]['_etag']
        }
        response = requests.patch(self.endpoint + '/realm/' + realmAll_A1_id, json=data,
                                  headers=headers, auth=self.auth)
        self.assertEqual(response.status_code, 200)
        resp = response.json()

        response = requests.get(self.endpoint + '/realm/' + realmAll_A1_id, auth=self.auth)
        re = response.json()
        self.assertEqual(re['name'], "All B1")
        self.assertEqual(re['_parent'], realmAll_A_id)
        self.assertEqual(re['_level'], 2)
        self.assertEqual(re['_tree_parents'], [self.realmAll_id, realmAll_A_id])
        self.assertEqual(re['_children'], [])

        # Update realm parent
        response = requests.get(self.endpoint + '/realm', params={'where': '{"name":"All B1"}'},
                                auth=self.auth)
        resp = response.json()
        re = resp['_items']
        data = {'_parent': realmAll_B_id}
        headers = {
            'Content-Type': 'application/json',
            'If-Match': re[0]['_etag']
        }
        response = requests.patch(self.endpoint + '/realm/' + realmAll_A1_id, json=data,
                                  headers=headers, auth=self.auth)
        self.assertEqual(response.status_code, 200)
        resp = response.json()
        realmAll_B1_id = realmAll_A1_id

        response = requests.get(self.endpoint + '/realm', params=sort_level, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        for item in re:
            print("Item: %s (%s)" % (item['_id'], item['name']))

        response = requests.get(self.endpoint + '/realm/' + realmAll_A1_id, auth=self.auth)
        re = response.json()
        self.assertEqual(re['name'], "All B1")
        self.assertEqual(re['_parent'], realmAll_B_id)
        self.assertEqual(re['_level'], 2)
        self.assertEqual(re['_tree_parents'], [self.realmAll_id, realmAll_B_id])
        self.assertEqual(re['_children'], [])

        # Check all realms hierarchy
        response = requests.get(self.endpoint + '/realm', params=sort_name, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 5)

        # ** Realm All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_level'], 0)
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_children'], [realmAll_A_id, realmAll_B_id, realmAll_C_id])
        # ** Realm All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.realmAll_id])
        self.assertEqual(re[1]['_children'], [])
        # ** Realm All B
        self.assertEqual(re[2]['name'], 'All B')
        self.assertEqual(re[2]['_level'], 1)
        self.assertEqual(re[2]['_tree_parents'], [self.realmAll_id])
        self.assertEqual(re[2]['_children'], [realmAll_B1_id])
        # ** Realm All B1
        self.assertEqual(re[3]['name'], 'All B1')
        self.assertEqual(re[3]['_level'], 2)
        self.assertEqual(re[3]['_tree_parents'], [self.realmAll_id, realmAll_B_id])
        self.assertEqual(re[3]['_children'], [])
        # ** Realm All C
        self.assertEqual(re[4]['name'], 'All C')
        self.assertEqual(re[4]['_level'], 1)
        self.assertEqual(re[4]['_tree_parents'], [self.realmAll_id])
        self.assertEqual(re[4]['_children'], [])

    def test_realm_name(self):
        """
        The backend will refuse realm with characters not allowed

        :return: None
        """
        headers = {'Content-Type': 'application/json'}

        data = {"name": "All A.1", "_parent": self.realmAll_id}
        response = requests.post(self.endpoint + '/realm', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('ERR', resp['_status'], resp)

        data = {"name": "All _A", "_parent": self.realmAll_id}
        response = requests.post(self.endpoint + '/realm', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        data = {"name": "All -A", "_parent": self.realmAll_id}
        response = requests.post(self.endpoint + '/realm', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('OK', resp['_status'], resp)

        data = {"name": "All A#1", "_parent": self.realmAll_id}
        response = requests.post(self.endpoint + '/realm', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        self.assertEqual('ERR', resp['_status'], resp)
