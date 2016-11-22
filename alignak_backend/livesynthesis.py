#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    ``alignak_backend.livesynthesis`` module

    This module manages the livesynthesis
"""
from __future__ import print_function
from flask import current_app, g, request, abort, jsonify
from eve.methods.patch import patch_internal


class Livesynthesis(object):
    """
        Livesynthesis class
    """
    @staticmethod
    def recalculate():
        """
            Recalculate all the live synthesis counters
        """
        livesynthesis = current_app.data.driver.db['livesynthesis']
        realmsdrv = current_app.data.driver.db['realm']
        allrealms = realmsdrv.find()
        for _, realm in enumerate(allrealms):
            live_current = livesynthesis.find_one({'_realm': realm['_id']})
            if live_current is None:
                data = {
                    'hosts_total': 0,
                    'hosts_up_hard': 0,
                    'hosts_up_soft': 0,
                    'hosts_down_hard': 0,
                    'hosts_down_soft': 0,
                    'hosts_unreachable_hard': 0,
                    'hosts_unreachable_soft': 0,
                    'hosts_acknowledged': 0,
                    'hosts_in_downtime': 0,
                    'hosts_flapping': 0,
                    'hosts_business_impact': 0,
                    'services_total': 0,
                    'services_ok_hard': 0,
                    'services_ok_soft': 0,
                    'services_warning_hard': 0,
                    'services_warning_soft': 0,
                    'services_critical_hard': 0,
                    'services_critical_soft': 0,
                    'services_unreachable_hard': 0,
                    'services_unreachable_soft': 0,
                    'services_unknown_hard': 0,
                    'services_unknown_soft': 0,
                    'services_acknowledged': 0,
                    'services_in_downtime': 0,
                    'services_flapping': 0,
                    'services_business_impact': 0,
                    '_realm': realm['_id']
                }
                livesynthesis.insert(data)
                live_current = livesynthesis.find_one({'_realm': realm['_id']})

            # Update hosts live synthesis
            hosts = current_app.data.driver.db['host']
            hosts_count = hosts.find({'_is_template': False, '_realm': realm['_id']}).count()
            if live_current['hosts_total'] != hosts_count:
                data = {"hosts_total": hosts_count}

                data['hosts_up_hard'] = hosts.find({
                    '_is_template': False,
                    "ls_state": "UP", "ls_state_type": "HARD",
                    "ls_acknowledged": False, "_realm": realm["_id"]
                }).count()
                data['hosts_down_hard'] = hosts.find({
                    '_is_template': False,
                    "ls_state": "DOWN", "ls_state_type": "HARD",
                    "ls_acknowledged": False, "_realm": realm["_id"]
                }).count()
                data['hosts_unreachable_hard'] = hosts.find({
                    '_is_template': False,
                    "ls_state": "UNREACHABLE", "ls_state_type": "HARD",
                    "ls_acknowledged": False, "_realm": realm["_id"]
                }).count()

                data['hosts_up_soft'] = hosts.find({
                    '_is_template': False,
                    "ls_state": "UP", "ls_state_type": "SOFT",
                    "ls_acknowledged": False, "_realm": realm["_id"]
                }).count()
                data['hosts_down_soft'] = hosts.find({
                    '_is_template': False,
                    "ls_state": "DOWN", "ls_state_type": "SOFT",
                    "ls_acknowledged": False, "_realm": realm["_id"]
                }).count()
                data['hosts_unreachable_soft'] = hosts.find({
                    '_is_template': False,
                    "ls_state": "UNREACHABLE", "ls_state_type": "SOFT",
                    "ls_acknowledged": False, "_realm": realm["_id"]
                }).count()

                data['hosts_acknowledged'] = hosts.find({
                    '_is_template': False,
                    'ls_acknowledged': True, "_realm": realm["_id"]
                }).count()
                data['hosts_in_downtime'] = hosts.find({
                    '_is_template': False, 'ls_downtimed': True, "_realm": realm["_id"]
                }).count()

                lookup = {"_id": live_current['_id']}
                patch_internal('livesynthesis', data, False, False, **lookup)

            # Update services live synthesis
            services = current_app.data.driver.db['service']
            services_count = services.find({'_is_template': False, '_realm': realm['_id']}).count()
            if live_current['services_total'] != services_count:
                data = {"services_total": services_count}

                data['services_ok_hard'] = services.find({
                    '_is_template': False,
                    "ls_state": "OK", "ls_state_type": "HARD",
                    "ls_acknowledged": False, "_realm": realm["_id"]
                }).count()
                data['services_warning_hard'] = services.find({
                    '_is_template': False,
                    "ls_state": "WARNING", "ls_state_type": "HARD",
                    "ls_acknowledged": False, "_realm": realm["_id"]
                }).count()
                data['services_critical_hard'] = services.find({
                    '_is_template': False,
                    "ls_state": "CRITICAL", "ls_state_type": "HARD",
                    "ls_acknowledged": False, "_realm": realm["_id"]
                }).count()
                data['services_unknown_hard'] = services.find({
                    '_is_template': False,
                    "ls_state": "UNKNOWN", "ls_state_type": "HARD",
                    "ls_acknowledged": False, "_realm": realm["_id"]
                }).count()
                data['services_unreachable_hard'] = services.find({
                    '_is_template': False,
                    "ls_state": "UNREACHABLE", "ls_state_type": "HARD",
                    "ls_acknowledged": False, "_realm": realm["_id"]
                }).count()

                data['services_ok_soft'] = services.find({
                    '_is_template': False,
                    "ls_state": "OK", "ls_state_type": "SOFT",
                    "ls_acknowledged": False, "_realm": realm["_id"]
                }).count()
                data['services_warning_soft'] = services.find({
                    '_is_template': False,
                    "ls_state": "WARNING", "ls_state_type": "SOFT",
                    "ls_acknowledged": False, "_realm": realm["_id"]
                }).count()
                data['services_critical_soft'] = services.find({
                    '_is_template': False,
                    "ls_state": "CRITICAL", "ls_state_type": "SOFT",
                    "ls_acknowledged": False, "_realm": realm["_id"]
                }).count()
                data['services_unknown_soft'] = services.find({
                    '_is_template': False,
                    "ls_state": "UNKNOWN", "ls_state_type": "SOFT",
                    "ls_acknowledged": False, "_realm": realm["_id"]
                }).count()
                data['services_unreachable_soft'] = services.find({
                    '_is_template': False,
                    "ls_state": "UNREACHABLE", "ls_state_type": "SOFT",
                    "ls_acknowledged": False, "_realm": realm["_id"]
                }).count()

                data['services_acknowledged'] = services.find({
                    '_is_template': False,
                    "ls_acknowledged": True, "_realm": realm["_id"]
                }).count()
                data['services_in_downtime'] = services.find({
                    '_is_template': False,
                    "ls_downtimed": True, "_realm": realm["_id"]
                }).count()
                lookup = {"_id": live_current['_id']}
                patch_internal('livesynthesis', data, False, False, **lookup)

    @staticmethod
    def on_inserted_host(items):
        """
            What to do when an host is inserted in the backend ...
        """
        livesynthesis_db = current_app.data.driver.db['livesynthesis']
        for _, item in enumerate(items):
            if item['_is_template']:
                continue

            live_current = livesynthesis_db.find_one({'_realm': item['_realm']})
            if live_current is None:
                ls = Livesynthesis()
                ls.recalculate()
            else:
                typecheck = 'hosts'
                data = {"$inc": {"%s_%s_%s" % (typecheck, item['ls_state'].lower(),
                                               item['ls_state_type'].lower()): 1,
                                 "%s_total" % (typecheck): 1}}
                current_app.data.driver.db.livesynthesis.update({'_id': live_current['_id']}, data)

    @staticmethod
    def on_inserted_service(items):
        """
            What to do when a service is inserted in the backend ...
        """
        livesynthesis_db = current_app.data.driver.db['livesynthesis']
        for _, item in enumerate(items):
            if item['_is_template']:
                continue

            live_current = livesynthesis_db.find_one({'_realm': item['_realm']})
            if live_current is None:
                ls = Livesynthesis()
                ls.recalculate()
            else:
                typecheck = 'services'
                data = {"$inc": {"%s_%s_%s" % (typecheck, item['ls_state'].lower(),
                                               item['ls_state_type'].lower()): 1,
                                 "%s_total" % (typecheck): 1}}
                current_app.data.driver.db.livesynthesis.update({'_id': live_current['_id']}, data)

    @staticmethod
    def on_updated_host(updated, original):
        """
            What to do when an host live state is updated ...
        """
        if original['_is_template']:
            return

        minus, plus = Livesynthesis.livesynthesis_to_update('hosts', updated, original)
        if minus:
            livesynthesis_db = current_app.data.driver.db['livesynthesis']
            live_current = livesynthesis_db.find_one({'_realm': original['_realm']})
            if live_current is None:
                ls = Livesynthesis()
                ls.recalculate()
            data = {"$inc": {minus: -1, plus: 1}}
            current_app.data.driver.db.livesynthesis.update({'_id': live_current['_id']}, data)

    @staticmethod
    def on_updated_service(updated, original):
        """
            What to do when a service live state is updated ...
        """
        if original['_is_template']:
            return

        minus, plus = Livesynthesis.livesynthesis_to_update('services', updated, original)
        if minus:
            livesynthesis_db = current_app.data.driver.db['livesynthesis']
            live_current = livesynthesis_db.find_one({'_realm': original['_realm']})
            if live_current is None:
                ls = Livesynthesis()
                ls.recalculate()
            data = {"$inc": {minus: -1, plus: 1}}
            current_app.data.driver.db.livesynthesis.update({'_id': live_current['_id']}, data)

    @staticmethod
    def livesynthesis_to_update(type_check, updated, original):
        """
        Define fields counters to minus and plus (or nothing to do)

        :param updated:
        :param original:
        :return: list with field name (minus, plus)
        :rtype: list
        """

        # State modification
        if 'ls_state' not in updated and 'ls_state_type' not in updated:
            return False, False
        elif 'ls_state' in updated and 'ls_state_type' not in updated:
            plus = "%s_%s_%s" % (type_check, updated['ls_state'].lower(),
                                 original['ls_state_type'].lower())
        elif 'ls_state' not in updated and 'ls_state_type' in updated:
            plus = "%s_%s_%s" % (type_check, original['ls_state'].lower(),
                                 updated['ls_state_type'].lower())
        else:
            # so have 'state' and 'state_type' in updated
            plus = "%s_%s_%s" % (type_check, updated['ls_state'].lower(),
                                 updated['ls_state_type'].lower())

        minus = "%s_%s_%s" % (type_check, original['ls_state'].lower(),
                              original['ls_state_type'].lower())

        # Acknowledgement modification
        if 'ls_acknowledged' in updated and updated['ls_acknowledged'] \
                and not original['ls_acknowledged']:
            plus = "%s_acknowledged" % (type_check)
        elif 'ls_acknowledged' in updated and not updated['ls_acknowledged'] \
                and original['ls_acknowledged']:
            minus = "%s_acknowledged" % (type_check)
        elif 'ls_acknowledged' in original and original['ls_acknowledged']:
            return False, False

        # Downtime modification
        if 'ls_downtimed' in updated and updated['ls_downtimed'] \
                and not original['ls_downtimed']:
            plus = "%s_in_downtime" % (type_check)
        elif 'ls_downtimed' in updated and not updated['ls_downtimed'] \
                and original['ls_downtimed']:
            minus = "%s_in_downtime" % (type_check)
        elif 'ls_downtimed' in original and original['ls_downtimed']:
            return False, False

        if minus == plus:
            return False, False

        return minus, plus
