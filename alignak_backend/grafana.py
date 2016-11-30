#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    ``alignak_backend.grafana`` module

    This module manages the grafana dashboard / graphs
"""
from future.utils import iteritems
import requests
from bson.objectid import ObjectId
from flask import current_app
from eve.methods.patch import patch_internal
from alignak_backend.perfdata import PerfDatas
from alignak_backend.timeseries import Timeseries


class Grafana(object):
    """
        Grafana class
    """
    def __init__(self, data):
        self.api_key = data['apikey']
        self.host = data['address']
        self.port = str(data['port'])
        self.dashboard_template = {'timezone': data['timezone'], 'refresh': data['refresh'],
                                   'schemaVersion': 13}

        # get graphite / influx for each realm of the grafana
        self.timeseries = {}

        graphite_db = current_app.data.driver.db['graphite']
        influxdb_db = current_app.data.driver.db['influxdb']
        realm_db = current_app.data.driver.db['realm']

        graphites = graphite_db.find({'grafana': data['_id']})
        for graphite in graphites:
            graphite['type'] = 'graphite'
            self.timeseries[graphite['_realm']] = graphite
            if graphite['_sub_realm']:
                realm = realm_db.find_one({'_id': graphite['_realm']})
                for child_realm in realm['_all_children']:
                    self.timeseries[child_realm] = graphite

        influxdbs = influxdb_db.find({'grafana': data['_id']})
        for influxdb in influxdbs:
            influxdb['type'] = 'influxdb'
            self.timeseries[influxdb['_realm']] = influxdb
            if influxdb['_sub_realm']:
                realm = realm_db.find_one({'_id': influxdb['_realm']})
                for child_realm in realm['_all_children']:
                    self.timeseries[child_realm] = influxdb
        self.get_datasource()

    def create_dashboard(self, host_id):  # pylint: disable=too-many-locals
        """
        Create / update a dashboard in Grafana

        :param host_id: id of the host
        :type host_id: str
        :return: True if created, otherwise False
        :rtype: bool
        """
        if len(self.datasources) == 0:
            return

        headers = {"Authorization": "Bearer " + self.api_key}

        host_db = current_app.data.driver.db['host']
        service_db = current_app.data.driver.db['service']
        command_db = current_app.data.driver.db['command']

        host = host_db.find_one({'_id': host_id})
        hostname = host['name']
        command = command_db.find_one({'_id': host['check_command']})
        command_name = command['name']

        # if this host not have a datasource (influxdb, graphite) in grafana, not create dashboard
        if host['_realm'] not in self.timeseries:
            return False

        rows = []
        targets = []
        refids = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P',
                  'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
        perfdata = PerfDatas(host['ls_perf_data'])
        num = 0
        for measurement in perfdata.metrics:
            fields = perfdata.metrics[measurement].__dict__
            mytarget = Timeseries.get_realms_prefix(host['_realm']) + '.' + hostname
            mytarget += '.' + fields['name']
            elements = {'measurement': fields['name'], 'refid': refids[num], 'mytarget': mytarget}
            targets.append(self.generate_target(elements, {"host": hostname},
                                                ObjectId(host['_realm'])))
            num += 1
            if fields['warning'] is not None:
                mytarget = Timeseries.get_realms_prefix(host['_realm']) + '.' + hostname
                mytarget += '.' + fields['name'] + '_warning'
                elements = {'measurement': fields['name'] + '_warning', 'refid': refids[num],
                            'mytarget': mytarget}
                targets.append(self.generate_target(elements, {"host": hostname},
                                                    ObjectId(host['_realm'])))
            num += 1
            if fields['critical'] is not None:
                mytarget = Timeseries.get_realms_prefix(host['_realm']) + '.' + hostname
                mytarget += '.' + fields['name'] + '_critical'
                elements = {'measurement': fields['name'] + '_critical', 'refid': refids[num],
                            'mytarget': mytarget}
                targets.append(self.generate_target(elements, {"host": hostname},
                                                    ObjectId(host['_realm'])))
            num += 1

        if len(targets) > 0:
            rows.append(self.generate_row(command_name, targets))
            if host['ls_last_check'] > 0:
                # Update host live state
                data = {
                    "ls_grafana": True,
                    "ls_grafana_panelid": 1
                }
                lookup = {"_id": host['_id']}
                patch_internal('host', data, False, False, **lookup)

        # now get services
        services = service_db.find({'host': host_id})
        for service in services:
            if service['ls_last_check'] > 0:

                perfdata = PerfDatas(service['ls_perf_data'])
                targets = []
                num = 0
                for measurement in perfdata.metrics:
                    fields = perfdata.metrics[measurement].__dict__
                    mytarget = Timeseries.get_realms_prefix(host['_realm']) + '.' + hostname
                    mytarget += '.' + service['name'] + '.' + fields['name']
                    elements = {'measurement': fields['name'], 'refid': refids[num],
                                'mytarget': mytarget}
                    targets.append(self.generate_target(elements,
                                                        {"host": hostname,
                                                         "service": service['name']},
                                                        ObjectId(service['_realm'])))
                    num += 1
                    if fields['warning'] is not None:
                        mytarget = Timeseries.get_realms_prefix(host['_realm']) + '.' + hostname
                        mytarget += '.' + service['name'] + '.' + fields['name'] + "_warning"
                        elements = {'measurement': fields['name'] + "_warning",
                                    'refid': refids[num], 'mytarget': mytarget}
                        targets.append(self.generate_target(elements,
                                                            {"host": hostname,
                                                             "service": service['name']},
                                                            ObjectId(service['_realm'])))
                    num += 1
                    if fields['critical'] is not None:
                        mytarget = Timeseries.get_realms_prefix(host['_realm']) + '.' + hostname
                        mytarget += '.' + service['name'] + '.' + fields['name'] + "_critical"
                        elements = {'measurement': fields['name'] + "_critical",
                                    'refid': refids[num], 'mytarget': mytarget}
                        targets.append(self.generate_target(elements,
                                                            {"host": hostname,
                                                             "service": service['name']},
                                                            ObjectId(service['_realm'])))
                    num += 1

                if len(targets) > 0:
                    rows.append(self.generate_row(service['name'], targets))
                    # Update service live state
                    data = {
                        "ls_grafana": True,
                        "ls_grafana_panelid": len(rows)
                    }
                    lookup = {"_id": service['_id']}
                    patch_internal('service', data, False, False, **lookup)

        self.dashboard_template['id'] = None
        self.dashboard_template['title'] = "host_" + hostname
        self.dashboard_template['rows'] = rows

        data = {
            "dashboard": self.dashboard_template,
            "overwrite": True
        }
        requests.post('http://' + self.host + ':' + self.port + '/api/dashboards/db', json=data,
                      headers=headers)
        return True

    def get_datasource(self):
        """
        Get datasource or create it if not exist

        :return: None
        """
        self.datasources = {}
        headers = {"Authorization": "Bearer " + self.api_key}
        response = requests.get('http://' + self.host + ':' + self.port + '/api/datasources',
                                headers=headers)
        resp = response.json()
        # get all datasource of grafana
        for datasource in iter(resp):
            self.datasources[datasource['name']] = datasource

        # associate the datasource to timeseries data
        for timeserie in self.timeseries.values():
            if str(timeserie['_id']) not in self.datasources:
                # no datasource, create one
                if timeserie['type'] == 'influxdb':
                    data = {
                        "name": str(timeserie['_id']),
                        "type": "influxdb",
                        "typeLogoUrl": "",
                        "access": "proxy",
                        "url": "http://" + timeserie['address'] + ":" + str(timeserie['port']),
                        "password": timeserie['password'],
                        "user": timeserie['login'],
                        "database": timeserie['database'],
                        "basicAuth": False,
                        "basicAuthUser": "",
                        "basicAuthPassword": "",
                        "withCredentials": False,
                        "isDefault": True,
                        "jsonData": {}
                    }
                elif timeserie['type'] == 'graphite':
                    data = {
                        "name": str(timeserie['_id']),
                        "type": "graphite",
                        "access": "proxy",
                        "url": "http://" + timeserie['graphite_address'] + ":" +
                               str(timeserie['graphite_port']),
                        "basicAuth": False,
                        "basicAuthUser": "",
                        "basicAuthPassword": "",
                        "withCredentials": False,
                        "isDefault": True,
                        "jsonData": {}
                    }
                response = requests.post(
                    'http://' + self.host + ':' + self.port + '/api/datasources',
                    json=data, headers=headers)
                resp = response.json()
                self.datasources[str(timeserie['_id'])] = resp

    def generate_target(self, elements, tags, realm):
        # measurement, refid, mytarget):
        """
        Generate target structure for dashboard

        :param elements: dictionary with elements: measurement, refid, mytarget
        :type measurement: dict
        :param tags: list of tags
        :type tags: list
        :param realm: realm _id of the item (host / service)
        :type realm: str
        :return: dictionary / structure of target (cf API Grafana)
        :rtype: dict
        """
        prepare_tags = []
        for key, value in iteritems(tags):
            data = {
                "key": key,
                "operator": "=",
                "value": value
            }
            if len(prepare_tags) > 0:
                data['condition'] = 'AND'
            prepare_tags.append(data)

        return {
            "dsType": self.timeseries[realm]['name'],
            "measurement": elements['measurement'],
            "resultFormat": "time_series",
            "policy": "default",
            "tags": prepare_tags,
            "groupBy": [
                {
                    "type": "time",
                    "params": ["auto"]
                },
                {
                    "type": "fill",
                    "params": ["null"]
                }
            ],
            "select": [
                [
                    {
                        "type": "field",
                        "params": ["value"]
                    },
                    {
                        "type": "mean",
                        "params": []
                    }
                ]
            ],
            "target": elements['mytarget'],
            "refId": elements['refid'],
        }

    def generate_row(self, title, targets):
        """
        Generate a row in dashboard

        :param title: Name of the row / graph
        :type title: str
        :param targets: all targets (all measurements in the row/graph)
        :type targets: dict
        :return: the dictionary of the row
        :rtype: dict
        """
        return {
            "title": "Chart",
            "height": "300px",
            "panels": [
                {
                    "title": title,
                    "type": "graph",
                    "span": 12,
                    "fill": 1,
                    "linewidth": 2,
                    "targets": targets,
                    "tooltip": {
                        "shared": True
                    }
                }
            ]
        }
