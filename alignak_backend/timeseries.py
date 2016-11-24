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
            service = ''
            if item['service'] is not None:
                service_info = service_db.find_one({'_id': item['service']})
                service = service_info['name']
            send_data = []
            for d in ts['data']:
                send_data.append(
                    {
                        "name": d['value']['name'],
                        "realm": Timeseries.get_realms_prefix(item['_realm']),
                        "host": host_info['name'],
                        "service": service,
                        "value": d['value']['value'],
                        "timestamp": item['last_check']
                    }
                )
            Timeseries.send_to_timeseries_db(send_data)

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
                        'value': fields
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
    def send_to_timeseries_db(data):
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
        :return: None
        """
        to_graphite_cache = False
        to_influx_cache = False

        if not Timeseries.send_to_timeseries_graphite(data):
            to_graphite_cache = True

        if not Timeseries.send_to_timeseries_influxdb(data):
            to_influx_cache = True

        if to_graphite_cache or to_influx_cache:
            for d in data:
                d['for_graphite'] = to_graphite_cache
                d['for_influxdb'] = to_influx_cache
            if len(data) > 0:
                post_internal('timeseriesretention', data)

    @staticmethod
    def send_to_timeseries_graphite(data):
        """
        Send perfdata to graphite/carbon timeseries database

        :param data: list of perfdata to send to graphite / carbon
        :type data: list
        :return: True if successful or not have graphite configured, otherwise False
        :rtype: bool
        """
        host = current_app.config.get('CARBON_HOST')
        if host == '':
            return True
        port = current_app.config.get('CARBON_PORT')
        cprefix = current_app.config.get('CARBON_PREFIX')
        send_data = []
        for d in data:
            if d['service'] == '':
                prefix = '.'.join([d['realm'], d['host']])
            else:
                prefix = '.'.join([d['realm'], d['host'], d['service']])
            if cprefix is not "":
                prefix = '.'.join([cprefix, prefix])
            send_data.append(('.'.join([prefix, d['name']]),
                              (int(d['timestamp']), d['value'])))
        carbon = CarbonIface(host, port)
        try:
            carbon.send_data(send_data)
            return True
        except:  # pylint: disable=W0702
            return False

    @staticmethod
    def send_to_timeseries_influxdb(data):
        """
        Send perfdata to influxdb timeseries database

        :param data: list of perfdata to send to influxdb
        :type data: list
        :return: True if successful or not have influxdb configured, otherwise False
        :rtype: bool
        """
        host = current_app.config.get('INFLUXDB_HOST')
        if host == '':
            return True
        port = current_app.config.get('INFLUXDB_PORT')
        login = current_app.config.get('INFLUXDB_LOGIN')
        password = current_app.config.get('INFLUXDB_PASSWORD')
        database = current_app.config.get('INFLUXDB_DATABASE')
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
        influxdb = InfluxDBClient(host, port, login, password, database)
        try:
            influxdb.write_points(json_body)
            return True
        except:  # pylint: disable=W0702
            return False
