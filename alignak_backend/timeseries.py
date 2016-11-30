#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    ``alignak_backend.timeseries`` module

    This module manages the timeseries carbon / influxdb
"""
from __future__ import print_function
import re
from flask import current_app, g
from influxdb import InfluxDBClient

from eve.methods.post import post_internal
from alignak_backend.carboniface import CarbonIface
from alignak_backend.perfdata import PerfDatas


class Timeseries(object):
    """
        Timeseries class
    """

    @staticmethod
    def after_inserted_logcheckresult(items):
        """
        Called by EVE HOOK (app.on_inserted_logcheckresult)

        :param items: List of logcheckresult inserted
        :type items: list
        :return: None
        """
        host_db = current_app.data.driver.db['host']
        service_db = current_app.data.driver.db['service']
        for dummy, item in enumerate(items):
            ts = Timeseries.prepare_data(item)
            host_info = host_db.find_one({'_id': item['host']})
            item_realm = host_info['_realm']
            service = ''
            if item['service'] is not None:
                service_info = service_db.find_one({'_id': item['service']})
                service = service_info['name']
                item_realm = service_info['_realm']
            send_data = []
            for d in ts['data']:
                send_data.append(
                    {
                        "name": d['name'],
                        "realm": Timeseries.get_realms_prefix(item['_realm']),
                        "host": host_info['name'],
                        "service": service,
                        "value": int(round(d['value'])),
                        "timestamp": item['last_check']
                    }
                )
            Timeseries.send_to_timeseries_db(send_data, item_realm)

    @staticmethod
    def prepare_data(item):
        """
        Split and prepare perfdata to after send to timeseries database

        :param item: fields added in mongo (logcheckresult)
        :type item: dict
        :return:
        """
        data_timeseries = {
            'data': [],
        }

        perfdata = PerfDatas(item['perf_data'])
        for measurement in perfdata.metrics:
            fields = perfdata.metrics[measurement].__dict__
            # case we have .timestamp in the name
            m = re.search(r'^(.*)\.[\d]{10}$', fields['name'])
            if m:
                fields['name'] = m.group(1)

            if fields['value'] is not None:
                data_timeseries['data'].append(
                    {
                        'name': fields['name'],
                        'value': fields['value']
                    }
                )
            if fields['warning'] is not None:
                data_timeseries['data'].append(
                    {
                        'name': fields['name'] + '_warning',
                        'value': fields['warning']
                    }
                )
            if fields['critical'] is not None:
                data_timeseries['data'].append(
                    {
                        'name': fields['name'] + '_critical',
                        'value': fields['critical']
                    }
                )
        return data_timeseries

    @staticmethod
    def get_realms_prefix(realm_id):
        """
        Get realm path since first level

        :param realm_id: id of the realm
        :type realm_id: str
        :return: realms name separed by .
        :rtype: str
        """
        prefix_realm = ''
        realm_db = current_app.data.driver.db['realm']
        realm_info = realm_db.find_one({'_id': realm_id})
        if len(realm_info['_tree_parents']) > 0:
            realms = realm_db.find({'_id': {"$in": realm_info['_tree_parents']}}).sort("_level")
            for realm in realms:
                prefix_realm += realm['name'] + "."
        prefix_realm += realm_info['name']
        return prefix_realm

    @staticmethod
    def send_to_timeseries_db(data, item_realm):
        """
        Send perfdata to timeseries databases, if not available, add temporary in mongo (retention)

        data must have this structure:
        [
            {
                "name": "",
                "realm"; "",
                "host": "",
                "service": "",
                "value": 000,
                "timestamp": 000
            }
        ]

        :param data: Information of data to send to carbon / influxdb
        :type data: list
        :param item_realm: id of the realm
        :type item_realm: str
        :return: None
        """
        graphite_db = current_app.data.driver.db['graphite']
        influxdb_db = current_app.data.driver.db['influxdb']
        realm_db = current_app.data.driver.db['realm']

        searches = [{'_realm': item_realm}]
        realm_info = realm_db.find_one({'_id': item_realm})
        for realm in realm_info['_tree_parents']:
            searches.append({'_realm': realm, '_sub_realm': True})

        # get graphite servers to send
        for search in searches:
            graphites = graphite_db.find(search)
            for graphite in graphites:
                if not Timeseries.send_to_timeseries_graphite(data, graphite):
                    for perf in data:
                        perf['graphite'] = graphite['_id']
                    post_internal('timeseriesretention', data)
                    for perf in data:
                        del perf['graphite']

        # get influxdb servers to send
        for search in searches:
            influxdbs = influxdb_db.find(search)
            for influxdb in influxdbs:
                if not Timeseries.send_to_timeseries_influxdb(data, influxdb):
                    for perf in data:
                        perf['influxdb'] = influxdb['_id']
                    post_internal('timeseriesretention', data)
                    for perf in data:
                        del perf['influxdb']

    @staticmethod
    def send_to_timeseries_graphite(data, graphite):
        """
        Send perfdata to graphite/carbon timeseries database

        :param data: list of perfdata to send to graphite / carbon
        :type data: list
        :param graphite: graphite properties dictionary
        :type graphite: dict
        :return: True if successful or not have graphite configured, otherwise False
        :rtype: bool
        """
        send_data = []
        for d in data:
            if d['service'] == '':
                prefix = '.'.join([d['realm'], d['host']])
            else:
                prefix = '.'.join([d['realm'], d['host'], d['service']])
            # manage prefix of graphite server
            if graphite['prefix'] != '':
                prefix = graphite['prefix'] + prefix
            send_data.append(('.'.join([prefix, d['name']]),
                              (int(d['timestamp']), d['value'])))
        carbon = CarbonIface(graphite['carbon_address'], graphite['carbon_port'])
        try:
            carbon.send_data(send_data)
            return True
        except:  # pylint: disable=W0702
            return False

    @staticmethod
    def send_to_timeseries_influxdb(data, influxdb):
        """
        Send perfdata to influxdb timeseries database

        :param data: list of perfdata to send to influxdb
        :type data: list
        :param influxdb: influxdb properties dictionary
        :type influxdb: dict
        :return: True if successful or not have influxdb configured, otherwise False
        :rtype: bool
        """
        json_body = []
        for d in data:
            json_body.append({
                "measurement": str(d['name']),
                "tags": {
                    "host": d['host'],
                    "service": d['service'],
                    "realm": '.'.join(d['realm'])
                },
                "time": d['timestamp'] * 1000000000,
                "fields": {
                    "value": float(d['value'])
                }
            })
        influxdbs = InfluxDBClient(influxdb['address'], influxdb['port'], influxdb['login'],
                                   influxdb['password'], influxdb['database'], timeout=1)
        try:
            influxdbs.write_points(json_body)
            return True
        except:  # pylint: disable=W0702
            return False
