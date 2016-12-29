#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This test check the hostgroups and the tree feature of hostgroups (children)
"""

from __future__ import print_function
import os
import time
import shlex
import subprocess
import copy
import requests
import unittest2


class TestGroups(unittest2.TestCase):
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

        # get realms
        response = requests.get(cls.endpoint + '/realm', auth=cls.auth)
        resp = response.json()
        cls.realmAll_id = resp['_items'][0]['_id']

        cls.hgAll_id = None
        cls.sgAll_id = None

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

    def test_add_hostgroup(self):
        # pylint: disable=too-many-locals
        """
        Test add hostgroups

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_name = {'sort': 'name'}
        sort_level = {'sort': '_level'}

        response = requests.get(self.endpoint + '/hostgroup', params=sort_level, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 1)
        self.hgAll_id = resp['_items'][0]['_id']

        # * Add sub_hostgroups
        data = {"name": "All A", "_realm": self.realmAll_id, "_parent": self.hgAll_id}
        response = requests.post(self.endpoint + '/hostgroup', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        hostgroupAll_A_id = copy.copy(resp['_id'])

        response = requests.get(self.endpoint + '/hostgroup', params=sort_level, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 2)

        # ** hostgroup All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_level'], 0)
        # ** hostgroup All A
        self.assertEqual(re[1]['name'], "All A")
        self.assertEqual(re[1]['_parent'], self.hgAll_id)
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.hgAll_id])

        data = {"name": "All B", "_realm": self.realmAll_id, "_parent": self.hgAll_id}
        response = requests.post(self.endpoint + '/hostgroup', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        # hostgroupAll_B_id = copy.copy(resp['_id'])

        response = requests.get(self.endpoint + '/hostgroup', params=sort_level, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 3)

        # ** hostgroup All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_level'], 0)
        # ** hostgroup All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_parent'], self.hgAll_id)
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.hgAll_id])
        # ** hostgroup All B
        self.assertEqual(re[2]['name'], 'All B')
        self.assertEqual(re[2]['_parent'], self.hgAll_id)
        self.assertEqual(re[2]['_level'], 1)
        self.assertEqual(re[2]['_tree_parents'], [self.hgAll_id])

        # Sub hostgroup without _parent
        data = {"name": "All C", "_realm": self.realmAll_id}
        response = requests.post(self.endpoint + '/hostgroup', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        # hostgroupAll_C_id = copy.copy(resp['_id'])

        response = requests.get(self.endpoint + '/hostgroup/' + resp['_id'], auth=self.auth)
        re = response.json()
        self.assertEqual(re['name'], "All C")
        self.assertEqual(re['_parent'], self.hgAll_id)
        self.assertEqual(re['_level'], 1)
        self.assertEqual(re['_tree_parents'], [self.hgAll_id])

        # Get all hostgroups
        response = requests.get(self.endpoint + '/hostgroup', params=sort_level, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 4)

        # ** hostgroup All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_level'], 0)
        # ** hostgroup All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_parent'], self.hgAll_id)
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.hgAll_id])
        # ** hostgroup All B
        self.assertEqual(re[2]['name'], 'All B')
        self.assertEqual(re[2]['_parent'], self.hgAll_id)
        self.assertEqual(re[2]['_level'], 1)
        self.assertEqual(re[2]['_tree_parents'], [self.hgAll_id])
        # ** hostgroup All C
        self.assertEqual(re[3]['name'], 'All C')
        self.assertEqual(re[3]['_parent'], self.hgAll_id)
        self.assertEqual(re[3]['_level'], 1)
        self.assertEqual(re[3]['_tree_parents'], [self.hgAll_id])

        # ** Add sub_sub_hostgroups
        data = {"name": "All A.1", "_realm": self.realmAll_id, "_parent": hostgroupAll_A_id}
        requests.post(self.endpoint + '/hostgroup', json=data, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/hostgroup', params=sort_name, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        for item in re:
            print("Item: %s (%s)" % (item['_id'], item['name']))
        self.assertEqual(re[2]['name'], "All A.1")
        self.assertEqual(re[2]['_parent'], hostgroupAll_A_id)
        self.assertEqual(re[2]['_level'], 2)
        self.assertEqual(re[2]['_tree_parents'], [self.hgAll_id, hostgroupAll_A_id])
        hostgroupAll_A1_id = copy.copy(re[2]['_id'])

        # ** hostgroup All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_level'], 0)
        # ** hostgroup All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_parent'], self.hgAll_id)
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.hgAll_id])
        # ** hostgroup All A.1
        self.assertEqual(re[2]['name'], 'All A.1')
        self.assertEqual(re[2]['_parent'], hostgroupAll_A_id)
        self.assertEqual(re[2]['_level'], 2)
        self.assertEqual(re[2]['_tree_parents'], [self.hgAll_id, hostgroupAll_A_id])
        # ** hostgroup All B
        self.assertEqual(re[3]['name'], 'All B')
        self.assertEqual(re[3]['_parent'], self.hgAll_id)
        self.assertEqual(re[3]['_level'], 1)
        self.assertEqual(re[3]['_tree_parents'], [self.hgAll_id])
        # ** hostgroup All C
        self.assertEqual(re[4]['name'], 'All C')
        self.assertEqual(re[4]['_parent'], self.hgAll_id)
        self.assertEqual(re[4]['_level'], 1)
        self.assertEqual(re[4]['_tree_parents'], [self.hgAll_id])

        # *** Add sub_sub_sub_hostgroups
        data = {"name": "All A.1.a", "_realm": self.realmAll_id, "_parent": hostgroupAll_A1_id}
        requests.post(self.endpoint + '/hostgroup', json=data, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/hostgroup', params=sort_name, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        for item in re:
            print("Item: %s (%s)" % (item['_id'], item['name']))
        self.assertEqual(len(re), 6)

        # ** hostgroup All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_level'], 0)
        # ** hostgroup All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_parent'], self.hgAll_id)
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.hgAll_id])
        # ** hostgroup All A.1
        self.assertEqual(re[2]['name'], 'All A.1')
        self.assertEqual(re[2]['_parent'], hostgroupAll_A_id)
        self.assertEqual(re[2]['_level'], 2)
        self.assertEqual(re[2]['_tree_parents'], [self.hgAll_id, hostgroupAll_A_id])
        # ** hostgroup All A.1.a
        self.assertEqual(re[3]['name'], 'All A.1.a')
        self.assertEqual(re[3]['_parent'], hostgroupAll_A1_id)
        self.assertEqual(re[3]['_level'], 3)
        self.assertEqual(re[3]['_tree_parents'], [
            self.hgAll_id, hostgroupAll_A_id, hostgroupAll_A1_id
        ])
        # ** hostgroup All B
        self.assertEqual(re[4]['name'], 'All B')
        self.assertEqual(re[4]['_parent'], self.hgAll_id)
        self.assertEqual(re[4]['_level'], 1)
        self.assertEqual(re[4]['_tree_parents'], [self.hgAll_id])
        # ** hostgroup All C
        self.assertEqual(re[5]['name'], 'All C')
        self.assertEqual(re[5]['_parent'], self.hgAll_id)
        self.assertEqual(re[5]['_level'], 1)
        self.assertEqual(re[5]['_tree_parents'], [self.hgAll_id])

        # *** Add sub_sub_sub_hostgroups
        data = {"name": "All A.1.b", "_realm": self.realmAll_id, "_parent": hostgroupAll_A1_id}
        requests.post(self.endpoint + '/hostgroup', json=data, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/hostgroup', params=sort_name, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        for item in re:
            print("Item: %s (%s)" % (item['_id'], item['name']))
        self.assertEqual(len(re), 7)

        # ** hostgroup All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_level'], 0)
        # ** hostgroup All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_parent'], self.hgAll_id)
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.hgAll_id])
        # ** hostgroup All A.1
        self.assertEqual(re[2]['name'], 'All A.1')
        self.assertEqual(re[2]['_parent'], hostgroupAll_A_id)
        self.assertEqual(re[2]['_level'], 2)
        self.assertEqual(re[2]['_tree_parents'], [self.hgAll_id, hostgroupAll_A_id])
        # ** hostgroup All A.1.a
        self.assertEqual(re[3]['name'], 'All A.1.a')
        self.assertEqual(re[3]['_parent'], hostgroupAll_A1_id)
        self.assertEqual(re[3]['_level'], 3)
        self.assertEqual(re[3]['_tree_parents'], [
            self.hgAll_id, hostgroupAll_A_id, hostgroupAll_A1_id
        ])
        # ** hostgroup All A.1.b
        self.assertEqual(re[4]['name'], 'All A.1.b')
        self.assertEqual(re[4]['_parent'], hostgroupAll_A1_id)
        self.assertEqual(re[4]['_level'], 3)
        self.assertEqual(re[4]['_tree_parents'], [
            self.hgAll_id, hostgroupAll_A_id, hostgroupAll_A1_id
        ])
        # ** hostgroup All B
        self.assertEqual(re[5]['name'], 'All B')
        self.assertEqual(re[5]['_parent'], self.hgAll_id)
        self.assertEqual(re[5]['_level'], 1)
        self.assertEqual(re[5]['_tree_parents'], [self.hgAll_id])
        # ** hostgroup All C
        self.assertEqual(re[6]['name'], 'All C')
        self.assertEqual(re[6]['_parent'], self.hgAll_id)
        self.assertEqual(re[6]['_level'], 1)
        self.assertEqual(re[6]['_tree_parents'], [self.hgAll_id])

    def test_add_servicegroup(self):
        # pylint: disable=too-many-locals
        """
        Test add servicegroups

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_name = {'sort': 'name'}
        sort_level = {'sort': '_level'}

        response = requests.get(self.endpoint + '/servicegroup', params=sort_level, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 1)
        self.sgAll_id = resp['_items'][0]['_id']

        # * Add sub_servicegroups
        data = {"name": "All A", "_realm": self.realmAll_id, "_parent": self.sgAll_id}
        response = requests.post(self.endpoint + '/servicegroup', json=data, headers=headers,
                                 auth=self.auth)
        print(response)
        resp = response.json()
        print(resp)
        servicegroupAll_A_id = copy.copy(resp['_id'])

        response = requests.get(self.endpoint + '/servicegroup', params=sort_level, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 2)

        # ** servicegroup All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_level'], 0)
        # ** servicegroup All A
        self.assertEqual(re[1]['name'], "All A")
        self.assertEqual(re[1]['_parent'], self.sgAll_id)
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.sgAll_id])

        data = {"name": "All B", "_realm": self.realmAll_id, "_parent": self.sgAll_id}
        response = requests.post(self.endpoint + '/servicegroup', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        # servicegroupAll_B_id = copy.copy(resp['_id'])

        response = requests.get(self.endpoint + '/servicegroup', params=sort_level, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 3)

        # ** servicegroup All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_level'], 0)
        # ** servicegroup All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_parent'], self.sgAll_id)
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.sgAll_id])
        # ** servicegroup All B
        self.assertEqual(re[2]['name'], 'All B')
        self.assertEqual(re[2]['_parent'], self.sgAll_id)
        self.assertEqual(re[2]['_level'], 1)
        self.assertEqual(re[2]['_tree_parents'], [self.sgAll_id])

        # Sub servicegroup without _parent
        data = {"name": "All C", "_realm": self.realmAll_id}
        response = requests.post(self.endpoint + '/servicegroup', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        # servicegroupAll_C_id = copy.copy(resp['_id'])

        response = requests.get(self.endpoint + '/servicegroup/' + resp['_id'], auth=self.auth)
        re = response.json()
        self.assertEqual(re['name'], "All C")
        self.assertEqual(re['_parent'], self.sgAll_id)
        self.assertEqual(re['_level'], 1)
        self.assertEqual(re['_tree_parents'], [self.sgAll_id])

        # Get all servicegroups
        response = requests.get(self.endpoint + '/servicegroup', params=sort_level, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 4)

        # ** servicegroup All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_level'], 0)
        # ** servicegroup All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_parent'], self.sgAll_id)
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.sgAll_id])
        # ** servicegroup All B
        self.assertEqual(re[2]['name'], 'All B')
        self.assertEqual(re[2]['_parent'], self.sgAll_id)
        self.assertEqual(re[2]['_level'], 1)
        self.assertEqual(re[2]['_tree_parents'], [self.sgAll_id])
        # ** servicegroup All C
        self.assertEqual(re[3]['name'], 'All C')
        self.assertEqual(re[3]['_parent'], self.sgAll_id)
        self.assertEqual(re[3]['_level'], 1)
        self.assertEqual(re[3]['_tree_parents'], [self.sgAll_id])

        # ** Add sub_sub_servicegroups
        data = {"name": "All A.1", "_realm": self.realmAll_id, "_parent": servicegroupAll_A_id}
        requests.post(self.endpoint + '/servicegroup', json=data, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/servicegroup', params=sort_name, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        for item in re:
            print("Item: %s (%s)" % (item['_id'], item['name']))
        self.assertEqual(re[2]['name'], "All A.1")
        self.assertEqual(re[2]['_parent'], servicegroupAll_A_id)
        self.assertEqual(re[2]['_level'], 2)
        self.assertEqual(re[2]['_tree_parents'], [self.sgAll_id, servicegroupAll_A_id])
        servicegroupAll_A1_id = copy.copy(re[2]['_id'])

        # ** servicegroup All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_level'], 0)
        # ** servicegroup All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_parent'], self.sgAll_id)
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.sgAll_id])
        # ** servicegroup All A.1
        self.assertEqual(re[2]['name'], 'All A.1')
        self.assertEqual(re[2]['_parent'], servicegroupAll_A_id)
        self.assertEqual(re[2]['_level'], 2)
        self.assertEqual(re[2]['_tree_parents'], [self.sgAll_id, servicegroupAll_A_id])
        # ** servicegroup All B
        self.assertEqual(re[3]['name'], 'All B')
        self.assertEqual(re[3]['_parent'], self.sgAll_id)
        self.assertEqual(re[3]['_level'], 1)
        self.assertEqual(re[3]['_tree_parents'], [self.sgAll_id])
        # ** servicegroup All C
        self.assertEqual(re[4]['name'], 'All C')
        self.assertEqual(re[4]['_parent'], self.sgAll_id)
        self.assertEqual(re[4]['_level'], 1)
        self.assertEqual(re[4]['_tree_parents'], [self.sgAll_id])

        # *** Add sub_sub_sub_servicegroups
        data = {"name": "All A.1.a", "_realm": self.realmAll_id, "_parent": servicegroupAll_A1_id}
        requests.post(self.endpoint + '/servicegroup', json=data, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/servicegroup', params=sort_name, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        for item in re:
            print("Item: %s (%s)" % (item['_id'], item['name']))
        self.assertEqual(len(re), 6)

        # ** servicegroup All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_level'], 0)
        # ** servicegroup All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_parent'], self.sgAll_id)
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.sgAll_id])
        # ** servicegroup All A.1
        self.assertEqual(re[2]['name'], 'All A.1')
        self.assertEqual(re[2]['_parent'], servicegroupAll_A_id)
        self.assertEqual(re[2]['_level'], 2)
        self.assertEqual(re[2]['_tree_parents'], [self.sgAll_id, servicegroupAll_A_id])
        # ** servicegroup All A.1.a
        self.assertEqual(re[3]['name'], 'All A.1.a')
        self.assertEqual(re[3]['_parent'], servicegroupAll_A1_id)
        self.assertEqual(re[3]['_level'], 3)
        self.assertEqual(re[3]['_tree_parents'], [
            self.sgAll_id, servicegroupAll_A_id, servicegroupAll_A1_id
        ])
        # ** servicegroup All B
        self.assertEqual(re[4]['name'], 'All B')
        self.assertEqual(re[4]['_parent'], self.sgAll_id)
        self.assertEqual(re[4]['_level'], 1)
        self.assertEqual(re[4]['_tree_parents'], [self.sgAll_id])
        # ** servicegroup All C
        self.assertEqual(re[5]['name'], 'All C')
        self.assertEqual(re[5]['_parent'], self.sgAll_id)
        self.assertEqual(re[5]['_level'], 1)
        self.assertEqual(re[5]['_tree_parents'], [self.sgAll_id])

        # *** Add sub_sub_sub_servicegroups
        data = {"name": "All A.1.b", "_realm": self.realmAll_id, "_parent": servicegroupAll_A1_id}
        requests.post(self.endpoint + '/servicegroup', json=data, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/servicegroup', params=sort_name, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        for item in re:
            print("Item: %s (%s)" % (item['_id'], item['name']))
        self.assertEqual(len(re), 7)

        # ** servicegroup All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_level'], 0)
        # ** servicegroup All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_parent'], self.sgAll_id)
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.sgAll_id])
        # ** servicegroup All A.1
        self.assertEqual(re[2]['name'], 'All A.1')
        self.assertEqual(re[2]['_parent'], servicegroupAll_A_id)
        self.assertEqual(re[2]['_level'], 2)
        self.assertEqual(re[2]['_tree_parents'], [self.sgAll_id, servicegroupAll_A_id])
        # ** servicegroup All A.1.a
        self.assertEqual(re[3]['name'], 'All A.1.a')
        self.assertEqual(re[3]['_parent'], servicegroupAll_A1_id)
        self.assertEqual(re[3]['_level'], 3)
        self.assertEqual(re[3]['_tree_parents'], [
            self.sgAll_id, servicegroupAll_A_id, servicegroupAll_A1_id
        ])
        # ** servicegroup All A.1.b
        self.assertEqual(re[4]['name'], 'All A.1.b')
        self.assertEqual(re[4]['_parent'], servicegroupAll_A1_id)
        self.assertEqual(re[4]['_level'], 3)
        self.assertEqual(re[4]['_tree_parents'], [
            self.sgAll_id, servicegroupAll_A_id, servicegroupAll_A1_id
        ])
        # ** servicegroup All B
        self.assertEqual(re[5]['name'], 'All B')
        self.assertEqual(re[5]['_parent'], self.sgAll_id)
        self.assertEqual(re[5]['_level'], 1)
        self.assertEqual(re[5]['_tree_parents'], [self.sgAll_id])
        # ** servicegroup All C
        self.assertEqual(re[6]['name'], 'All C')
        self.assertEqual(re[6]['_parent'], self.sgAll_id)
        self.assertEqual(re[6]['_level'], 1)
        self.assertEqual(re[6]['_tree_parents'], [self.sgAll_id])

    def test_add_usergroup(self):
        # pylint: disable=too-many-locals
        """
        Test add usergroups

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_name = {'sort': 'name'}
        sort_level = {'sort': '_level'}

        response = requests.get(self.endpoint + '/usergroup', params=sort_level, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 1)
        self.hgAll_id = resp['_items'][0]['_id']

        # * Add sub_usergroups
        data = {"name": "All A", "_realm": self.realmAll_id, "_parent": self.hgAll_id}
        response = requests.post(self.endpoint + '/usergroup', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        usergroupAll_A_id = copy.copy(resp['_id'])

        response = requests.get(self.endpoint + '/usergroup', params=sort_level, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 2)

        # ** usergroup All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_level'], 0)
        # ** usergroup All A
        self.assertEqual(re[1]['name'], "All A")
        self.assertEqual(re[1]['_parent'], self.hgAll_id)
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.hgAll_id])

        data = {"name": "All B", "_realm": self.realmAll_id, "_parent": self.hgAll_id}
        response = requests.post(self.endpoint + '/usergroup', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        # usergroupAll_B_id = copy.copy(resp['_id'])

        response = requests.get(self.endpoint + '/usergroup', params=sort_level, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 3)

        # ** usergroup All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_level'], 0)
        # ** usergroup All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_parent'], self.hgAll_id)
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.hgAll_id])
        # ** usergroup All B
        self.assertEqual(re[2]['name'], 'All B')
        self.assertEqual(re[2]['_parent'], self.hgAll_id)
        self.assertEqual(re[2]['_level'], 1)
        self.assertEqual(re[2]['_tree_parents'], [self.hgAll_id])

        # Sub usergroup without _parent
        data = {"name": "All C", "_realm": self.realmAll_id}
        response = requests.post(self.endpoint + '/usergroup', json=data, headers=headers,
                                 auth=self.auth)
        resp = response.json()
        # usergroupAll_C_id = copy.copy(resp['_id'])

        response = requests.get(self.endpoint + '/usergroup/' + resp['_id'], auth=self.auth)
        re = response.json()
        self.assertEqual(re['name'], "All C")
        self.assertEqual(re['_parent'], self.hgAll_id)
        self.assertEqual(re['_level'], 1)
        self.assertEqual(re['_tree_parents'], [self.hgAll_id])

        # Get all usergroups
        response = requests.get(self.endpoint + '/usergroup', params=sort_level, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        self.assertEqual(len(re), 4)

        # ** usergroup All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_level'], 0)
        # ** usergroup All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_parent'], self.hgAll_id)
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.hgAll_id])
        # ** usergroup All B
        self.assertEqual(re[2]['name'], 'All B')
        self.assertEqual(re[2]['_parent'], self.hgAll_id)
        self.assertEqual(re[2]['_level'], 1)
        self.assertEqual(re[2]['_tree_parents'], [self.hgAll_id])
        # ** usergroup All C
        self.assertEqual(re[3]['name'], 'All C')
        self.assertEqual(re[3]['_parent'], self.hgAll_id)
        self.assertEqual(re[3]['_level'], 1)
        self.assertEqual(re[3]['_tree_parents'], [self.hgAll_id])

        # ** Add sub_sub_usergroups
        data = {"name": "All A.1", "_realm": self.realmAll_id, "_parent": usergroupAll_A_id}
        requests.post(self.endpoint + '/usergroup', json=data, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/usergroup', params=sort_name, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        for item in re:
            print("Item: %s (%s)" % (item['_id'], item['name']))
        self.assertEqual(re[2]['name'], "All A.1")
        self.assertEqual(re[2]['_parent'], usergroupAll_A_id)
        self.assertEqual(re[2]['_level'], 2)
        self.assertEqual(re[2]['_tree_parents'], [self.hgAll_id, usergroupAll_A_id])
        usergroupAll_A1_id = copy.copy(re[2]['_id'])

        # ** usergroup All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_level'], 0)
        # ** usergroup All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_parent'], self.hgAll_id)
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.hgAll_id])
        # ** usergroup All A.1
        self.assertEqual(re[2]['name'], 'All A.1')
        self.assertEqual(re[2]['_parent'], usergroupAll_A_id)
        self.assertEqual(re[2]['_level'], 2)
        self.assertEqual(re[2]['_tree_parents'], [self.hgAll_id, usergroupAll_A_id])
        # ** usergroup All B
        self.assertEqual(re[3]['name'], 'All B')
        self.assertEqual(re[3]['_parent'], self.hgAll_id)
        self.assertEqual(re[3]['_level'], 1)
        self.assertEqual(re[3]['_tree_parents'], [self.hgAll_id])
        # ** usergroup All C
        self.assertEqual(re[4]['name'], 'All C')
        self.assertEqual(re[4]['_parent'], self.hgAll_id)
        self.assertEqual(re[4]['_level'], 1)
        self.assertEqual(re[4]['_tree_parents'], [self.hgAll_id])

        # *** Add sub_sub_sub_usergroups
        data = {"name": "All A.1.a", "_realm": self.realmAll_id, "_parent": usergroupAll_A1_id}
        requests.post(self.endpoint + '/usergroup', json=data, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/usergroup', params=sort_name, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        for item in re:
            print("Item: %s (%s)" % (item['_id'], item['name']))
        self.assertEqual(len(re), 6)

        # ** usergroup All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_level'], 0)
        # ** usergroup All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_parent'], self.hgAll_id)
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.hgAll_id])
        # ** usergroup All A.1
        self.assertEqual(re[2]['name'], 'All A.1')
        self.assertEqual(re[2]['_parent'], usergroupAll_A_id)
        self.assertEqual(re[2]['_level'], 2)
        self.assertEqual(re[2]['_tree_parents'], [self.hgAll_id, usergroupAll_A_id])
        # ** usergroup All A.1.a
        self.assertEqual(re[3]['name'], 'All A.1.a')
        self.assertEqual(re[3]['_parent'], usergroupAll_A1_id)
        self.assertEqual(re[3]['_level'], 3)
        self.assertEqual(re[3]['_tree_parents'], [
            self.hgAll_id, usergroupAll_A_id, usergroupAll_A1_id
        ])
        # ** usergroup All B
        self.assertEqual(re[4]['name'], 'All B')
        self.assertEqual(re[4]['_parent'], self.hgAll_id)
        self.assertEqual(re[4]['_level'], 1)
        self.assertEqual(re[4]['_tree_parents'], [self.hgAll_id])
        # ** usergroup All C
        self.assertEqual(re[5]['name'], 'All C')
        self.assertEqual(re[5]['_parent'], self.hgAll_id)
        self.assertEqual(re[5]['_level'], 1)
        self.assertEqual(re[5]['_tree_parents'], [self.hgAll_id])

        # *** Add sub_sub_sub_usergroups
        data = {"name": "All A.1.b", "_realm": self.realmAll_id, "_parent": usergroupAll_A1_id}
        requests.post(self.endpoint + '/usergroup', json=data, headers=headers, auth=self.auth)

        response = requests.get(self.endpoint + '/usergroup', params=sort_name, auth=self.auth)
        resp = response.json()
        re = resp['_items']
        for item in re:
            print("Item: %s (%s)" % (item['_id'], item['name']))
        self.assertEqual(len(re), 7)

        # ** usergroup All
        self.assertEqual(re[0]['name'], 'All')
        self.assertEqual(re[0]['_tree_parents'], [])
        self.assertEqual(re[0]['_level'], 0)
        # ** usergroup All A
        self.assertEqual(re[1]['name'], 'All A')
        self.assertEqual(re[1]['_parent'], self.hgAll_id)
        self.assertEqual(re[1]['_level'], 1)
        self.assertEqual(re[1]['_tree_parents'], [self.hgAll_id])
        # ** usergroup All A.1
        self.assertEqual(re[2]['name'], 'All A.1')
        self.assertEqual(re[2]['_parent'], usergroupAll_A_id)
        self.assertEqual(re[2]['_level'], 2)
        self.assertEqual(re[2]['_tree_parents'], [self.hgAll_id, usergroupAll_A_id])
        # ** usergroup All A.1.a
        self.assertEqual(re[3]['name'], 'All A.1.a')
        self.assertEqual(re[3]['_parent'], usergroupAll_A1_id)
        self.assertEqual(re[3]['_level'], 3)
        self.assertEqual(re[3]['_tree_parents'], [
            self.hgAll_id, usergroupAll_A_id, usergroupAll_A1_id
        ])
        # ** usergroup All A.1.b
        self.assertEqual(re[4]['name'], 'All A.1.b')
        self.assertEqual(re[4]['_parent'], usergroupAll_A1_id)
        self.assertEqual(re[4]['_level'], 3)
        self.assertEqual(re[4]['_tree_parents'], [
            self.hgAll_id, usergroupAll_A_id, usergroupAll_A1_id
        ])
        # ** usergroup All B
        self.assertEqual(re[5]['name'], 'All B')
        self.assertEqual(re[5]['_parent'], self.hgAll_id)
        self.assertEqual(re[5]['_level'], 1)
        self.assertEqual(re[5]['_tree_parents'], [self.hgAll_id])
        # ** usergroup All C
        self.assertEqual(re[6]['name'], 'All C')
        self.assertEqual(re[6]['_parent'], self.hgAll_id)
        self.assertEqual(re[6]['_level'], 1)
        self.assertEqual(re[6]['_tree_parents'], [self.hgAll_id])
