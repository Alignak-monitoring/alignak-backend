#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This test verify the usage of hosts and services templates
"""

from __future__ import print_function
import os
import json
import time
import shlex
import subprocess
import requests
import unittest2


class TestTemplatesUpdate(unittest2.TestCase):
    """
    This class test the templates management for hosts and services templates
    """

    maxDiff = None

    @classmethod
    def setUpClass(cls):
        """This method:
          * deletes mongodb database
          * starts the backend with uwsgi
          * logs in the backend and get the token
          * get the main realm

        :return: None
        """
        # Set test mode for Alignak backend
        os.environ['TEST_ALIGNAK_BACKEND'] = '1'
        os.environ['ALIGNAK_BACKEND_MONGO_DBNAME'] = 'alignak-backend-templates-test'

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

        # Get realm All
        params = {'where': json.dumps({'default': True})}
        response = requests.get(cls.endpoint + '/realm', auth=cls.auth)
        resp = response.json()
        cls.realm_all = resp['_items'][0]
        cls.realm_all_id = resp['_items'][0]['_id']

        # Get main admin users
        params = {'where': json.dumps({'name': 'admin'})}
        response = requests.get(cls.endpoint + '/user', params=params, auth=cls.auth)
        resp = response.json()
        cls.user_admin = resp['_items'][0]
        cls.user_admin_id = resp['_items'][0]['_id']

        # Get TP 24x7
        params = {'where': json.dumps({'name': '24x7'})}
        response = requests.get(cls.endpoint + '/timeperiod', params=params, auth=cls.auth)
        resp = response.json()
        cls.tp_24_7 = resp['_items'][0]
        cls.tp_24_7_id = resp['_items'][0]['_id']

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
        Delete resources after each test

        :return: None
        """
        for resource in ['host', 'service', 'command']:
            requests.delete(cls.endpoint + '/' + resource, auth=cls.auth)

    def _create_templates(self):
        """Create hosts and services templates - from the linux-nrpe pack

        :return: None
        """
        headers = {'Content-Type': 'application/json'}
        sort_id = {'sort': '_id'}
        cfg_folder = 'cfg/pack-linux-nrpe/'

        # Add some commands
        items = json.loads(open(cfg_folder + 'commands.json').read())
        for item in items:
            item['_realm'] = self.realm_all_id
            response = requests.post(self.endpoint + '/command', json=item,
                                     headers=headers, auth=self.auth)
            assert response.status_code == 201

        # Check in the backend
        response = requests.get(self.endpoint + '/command', params=sort_id, auth=self.auth)
        items = response.json()
        items = items['_items']
        for item in items:
            print("Command: %s" % item['name'])
        assert len(items) == 6

        # Add some hosts templates
        items = json.loads(open(cfg_folder + 'hosts-templates.json').read())
        for item in items:
            item['_realm'] = self.realm_all_id
            item['check_period'] = self.tp_24_7_id
            # Get check command
            params = {'where': json.dumps({'name': item['check_command']})}
            response = requests.get(self.endpoint + '/command', params=params, auth=self.auth)
            resp = response.json()
            item['check_command'] = resp['_items'][0]['_id']

            response = requests.post(self.endpoint + '/host', json=item,
                                     headers=headers, auth=self.auth)
            assert response.status_code == 201

        # Check in the backend
        response = requests.get(self.endpoint + '/host', params=sort_id, auth=self.auth)
        items = response.json()
        hosts = items['_items']
        for host in hosts:
            print("Host: %s" % host['name'])
        assert len(hosts) == 2

        # Add some services templates
        services = json.loads(open(cfg_folder + 'services-templates.json').read())
        # - start with the one that do not have templates
        items = [item for item in services if '_templates' not in item or not item['_templates']]
        for item in items:
            item['_realm'] = self.realm_all_id
            item['check_period'] = self.tp_24_7_id
            if 'host' in item:
                # Get host
                params = {'where': json.dumps({'name': item['host']})}
                response = requests.get(self.endpoint + '/host', params=params, auth=self.auth)
                resp = response.json()
                item['host'] = resp['_items'][0]['_id']
            if 'check_command' in item:
                # Get check command
                params = {'where': json.dumps({'name': item['check_command']})}
                response = requests.get(self.endpoint + '/command', params=params, auth=self.auth)
                resp = response.json()
                item['check_command'] = resp['_items'][0]['_id']

            # item['check_command'] = self.host_check
            response = requests.post(self.endpoint + '/service', json=item,
                                     headers=headers, auth=self.auth)
            assert response.status_code == 201

        # - and then the one that have some templates
        items = [item for item in services if '_templates' in item and item['_templates']]
        for item in items:
            item['_realm'] = self.realm_all_id
            item['check_period'] = self.tp_24_7_id
            if 'host' in item:
                # Get host
                params = {'where': json.dumps({'name': item['host']})}
                response = requests.get(self.endpoint + '/host', params=params, auth=self.auth)
                resp = response.json()
                item['host'] = resp['_items'][0]['_id']
            if 'check_command' in item:
                # Get check command
                params = {'where': json.dumps({'name': item['check_command']})}
                response = requests.get(self.endpoint + '/command', params=params, auth=self.auth)
                resp = response.json()
                item['check_command'] = resp['_items'][0]['_id']
            if '_templates' in item:
                tpls = item.pop('_templates')
                for tpl in tpls:
                    # Get template
                    params = {'where': json.dumps({'name': tpl, '_is_template': True})}
                    response = requests.get(self.endpoint + '/service', params=params,
                                            auth=self.auth)
                    resp = response.json()
                    if '_templates' not in item:
                        item['_templates'] = []
                    item['_templates'].append(resp['_items'][0]['_id'])

            # item['check_command'] = self.host_check
            response = requests.post(self.endpoint + '/service', json=item,
                                     headers=headers, auth=self.auth)
            assert response.status_code == 201

        # Check in the backend
        response = requests.get(self.endpoint + '/service', params=sort_id, auth=self.auth)
        items = response.json()
        services = items['_items']
        for service in services:
            print("Service: %s" % service['name'])
        assert len(services) == 10

        return (hosts, services)

    def _create_host(self, template_name='linux-nrpe', host_name='host-01'):
        """Create an host with templates intheritance

        :return: None
        """
        headers = {'Content-Type': 'application/json'}

        # Get an host template
        params = {'where': json.dumps({'name': template_name})}
        response = requests.get(self.endpoint + '/host', params=params, auth=self.auth)
        items = response.json()
        host_template_id = items['_items'][0]['_id']

        # Create an host based on the template
        data = {
            'name': host_name,
            'alias': 'My templated host',
            '_templates': [host_template_id],
            '_realm': self.realm_all_id
        }
        response = requests.post(self.endpoint + '/host', json=data,
                                 headers=headers, auth=self.auth)
        print("Host creation: %s" % response.content)
        assert response.status_code == 201

        # Get the new host
        params = {'where': json.dumps({'name': host_name})}
        response = requests.get(self.endpoint + '/host', params=params, auth=self.auth)
        items = response.json()
        assert len(items['_items']) == 1
        host = items['_items'][0]
        assert host['name'] == host_name
        assert host['_is_template'] is False

        # Get the new host services
        params = {'where': json.dumps({'host': host['_id']})}
        response = requests.get(self.endpoint + '/service', params=params, auth=self.auth)
        items = response.json()
        # The host has 9 services thanks to template inheritance
        assert len(items['_items']) == 9
        services = items['_items']
        for service in services:
            assert service['_is_template'] is False

        return (host, services)

    def test_host_template_update(self):
        """Test the host template update for inherited fields

        :return: None
        """
        # Create the templates
        (hosts_templates, _) = self._create_templates()

        # Create an host
        (host, services) = self._create_host(template_name='linux-nrpe', host_name='nrpe-01')

        # Find our host template
        my_template = None
        for tpl in hosts_templates:
            if tpl['name'] == 'linux-nrpe':
                # Get the template from the backend to have a fresh _etag
                response = requests.get(self.endpoint + '/host/' + tpl['_id'], auth=self.auth)
                my_template = response.json()
                break

        # Update the host template - a field that has been inherited
        # by the host when it got created and a field that has not been inherited!
        # The `ǹotes` field is set as empty in the template
        # The `check_interval` field is not defined in the template
        data_to_update = {
            'notes': "No more empty!",
            'check_interval': 12
        }
        headers = {'Content-Type': 'application/json', 'If-Match': my_template['_etag']}
        response = requests.patch(self.endpoint + '/host/' + my_template['_id'],
                                  json=data_to_update, headers=headers, auth=self.auth)
        resp = response.json()

        # Get the template from the backend to confirm update
        response = requests.get(self.endpoint + '/host/' + my_template['_id'], auth=self.auth)
        my_new_template = response.json()
        # Compare after update - except for some specific fields...
        my_template['_etag'] = resp['_etag']
        my_template['_updated'] = my_new_template['_updated']
        my_template['_links'] = my_new_template['_links']
        # ... and for the modified field!
        my_template['notes'] = my_new_template['notes']
        my_template['check_interval'] = my_new_template['check_interval']
        self.assertEqual(my_template, my_new_template)

        # Get the inherited host from the backend to confirm update
        response = requests.get(self.endpoint + '/host/' + host['_id'], auth=self.auth)
        my_new_host = response.json()
        # Compare after update - except for some specific fields...
        host['_etag'] = my_new_host['_etag']
        host['_updated'] = my_new_host['_updated']
        host['_links'] = my_new_host['_links']
        # ... and for the modified field!
        host['notes'] = my_new_host['notes']
        host['check_interval'] = my_new_host['check_interval']
        self.assertEqual(host, my_new_host)

        # Get the inherited host services from the backend to confirm they did not got impacted
        for service in services:
            response = requests.get(self.endpoint + '/service/' + service['_id'], auth=self.auth)
            my_new_service = response.json()
            # Compare after update - except for some specific fields...
            service['_etag'] = my_new_service['_etag']
            service['_updated'] = my_new_service['_updated']
            service['_links'] = my_new_service['_links']
            # Must be identical
            self.assertEqual(service, my_new_service)

        # ---
        # When updating a field of an host template all the inherited hosts that did
        # not yet modified this field are impacted
        # ---

    def _check_service_template_update(self, data_to_update):  # pylint: disable=too-many-locals
        """Test the service template update

        :return: None
        """
        # Create the templates
        (hosts_templates, services_templates) = self._create_templates()

        # Create an host
        (host, services) = self._create_host(template_name='linux-nrpe', host_name='nrpe-01')

        # Find our host template
        my_host_template = None
        for tpl in hosts_templates:
            if tpl['name'] == 'linux-nrpe':
                my_host_template = tpl
                break

        # Find our service template
        my_template = None
        for tpl in services_templates:
            # This template inherits from a linux-nrpe-service template
            if tpl['name'] == 'linux_nrpe_version':
                # Get the template from the backend to have a fresh _etag
                response = requests.get(self.endpoint + '/service/' + tpl['_id'], auth=self.auth)
                my_template = response.json()
                break

        # And find the inherited service
        my_service = None
        for service in services:
            # This template inherits from a linux-nrpe-service template
            if service['name'] == 'linux_nrpe_version':
                # Get the service from the backend to have a fresh _etag
                response = requests.get(self.endpoint + '/service/' + service['_id'],
                                        auth=self.auth)
                my_service = response.json()
                break

        if data_to_update is None:
            data_to_update = {}
            for prop in my_template:
                # Exclude Python-Eve specific fields
                if prop in ['_created', '_updated', '_links', '_etag', '_id']:
                    continue
                # Exclude some not -logicial to update fields
                if prop in ['host']:
                    continue
                # if prop in ['_is_template']:
                data_to_update.update({prop: my_template.get(prop)})
            print("Data to update: %s" % data_to_update)

        # Update the service element
        headers = {'Content-Type': 'application/json', 'If-Match': my_template['_etag']}
        response = requests.patch(self.endpoint + '/service/' + my_template['_id'],
                                  json=data_to_update, headers=headers, auth=self.auth)

        # Get the services from the backend to confirm the impacts
        params = {'where': json.dumps({'name': 'linux_nrpe_version'})}
        response = requests.get(self.endpoint + '/service', params=params, auth=self.auth)
        items = response.json()
        # There are 2 services named as 'linux_nrpe_version'
        assert len(items['_items']) == 2
        services = items['_items']
        for service in services:
            if service['_is_template']:
                # The template one is the template we updated

                # Compare after update - except for some specific fields...
                my_template['_etag'] = service['_etag']
                my_template['_updated'] = service['_updated']
                my_template['_links'] = service['_links']
                # ... and for the modified field!
                for prop in data_to_update:
                    my_template[prop] = service[prop]

                self.assertEqual(my_template, service)
                # Service template is still related to its host template
                self.assertEqual(service['host'], my_host_template['_id'])
            else:
                # The not template one is the service inherited on host creation

                # Compare after update - except for some specific fields...
                my_service['_etag'] = service['_etag']
                my_service['_updated'] = service['_updated']
                my_service['_links'] = service['_links']
                # ... and for the modified field!
                for prop in data_to_update:
                    my_service[prop] = service[prop]

                self.assertEqual(my_service, service)
                # Service is still related to its host
                self.assertEqual(service['host'], host['_id'])

        # Get the inherited host from the backend to confirm it did not changed
        response = requests.get(self.endpoint + '/host/' + host['_id'], auth=self.auth)
        my_new_host = response.json()
        # Compare after update - except for some specific fields...
        host['_etag'] = my_new_host['_etag']
        host['_updated'] = my_new_host['_updated']
        host['_links'] = my_new_host['_links']
        self.assertEqual(host, my_new_host)

        # ---
        # When updating a field of a service template all the inherited services that did
        # not yet modified this field are impacted
        # ---

    def test_service_template_update(self):
        """Test the service template update - some few fields

        :return: None
        """
        # Update the service template - a field that has NOT been inherited
        # by the service when it got created!
        # The `aggregation` field is set as 'system' in the template
        # The `check_interval` field is not defined in the template
        data_to_update = {
            'aggregation': "Changed!",
            'check_interval': 12
        }
        self._check_service_template_update(data_to_update)

    def test_service_template_update_unchanged(self):
        """Test the service template update - no changed values

        :return: None
        """
        data_to_update = {}
        self._check_service_template_update(data_to_update)

    def test_service_template_update_is_template(self):
        """Test the service template update - update the _is_template property to True

        :return: None
        """
        # This property is still True because it is for a template...
        # as such all must be left unchanged.
        data_to_update = {
            '_is_template': True
        }
        self._check_service_template_update(data_to_update)

    def test_service_template_update_all_changed(self):  # pylint: disable=too-many-locals
        """Test the service template update - all properties updated

        :return: None
        """
        # Request to update with all the possible data got from the template itself!
        self._check_service_template_update(None)


if __name__ == '__main__':
    unittest2.main()
