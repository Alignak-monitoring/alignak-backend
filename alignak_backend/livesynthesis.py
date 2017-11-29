#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    ``alignak_backend.livesynthesis`` module

    This module manages the livesynthesis
"""
from __future__ import print_function
import os
import pymongo
from flask import current_app, g, request
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
        if 'ALIGNAK_BACKEND_PRINT' in os.environ:
            print("LS - Recalculating...")
        livesynthesis = current_app.data.driver.db['livesynthesis']
        realmsdrv = current_app.data.driver.db['realm']
        allrealms = realmsdrv.find()
        for _, realm in enumerate(allrealms):
            live_current = livesynthesis.find_one({'_realm': realm['_id']})
            if live_current is None:
                if 'ALIGNAK_BACKEND_PRINT' in os.environ:
                    print("     new LS for realm %s" % realm['name'])
                data = {
                    'hosts_total': 0,
                    'hosts_not_monitored': 0,
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
                    'services_not_monitored': 0,
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
            data = {'hosts_total': hosts_count}

            data['hosts_not_monitored'] = hosts.find({
                '_is_template': False,
                'active_checks_enabled': False, 'passive_checks_enabled': False,
                '_realm': realm['_id']
            }).count()
            data['hosts_up_hard'] = hosts.find({
                '_is_template': False,
                '$or': [{'active_checks_enabled': True}, {'passive_checks_enabled': True}],
                'ls_state': 'UP', 'ls_state_type': 'HARD',
                'ls_acknowledged': False, '_realm': realm['_id']
            }).count()
            data['hosts_down_hard'] = hosts.find({
                '_is_template': False,
                '$or': [{'active_checks_enabled': True}, {'passive_checks_enabled': True}],
                'ls_state': 'DOWN', 'ls_state_type': 'HARD',
                'ls_acknowledged': False, '_realm': realm['_id']
            }).count()
            data['hosts_unreachable_hard'] = hosts.find({
                '_is_template': False,
                '$or': [{'active_checks_enabled': True}, {'passive_checks_enabled': True}],
                'ls_state': 'UNREACHABLE', 'ls_state_type': 'HARD',
                'ls_acknowledged': False, '_realm': realm['_id']
            }).count()

            data['hosts_up_soft'] = hosts.find({
                '_is_template': False,
                '$or': [{'active_checks_enabled': True}, {'passive_checks_enabled': True}],
                'ls_state': 'UP', 'ls_state_type': 'SOFT',
                'ls_acknowledged': False, '_realm': realm['_id']
            }).count()
            data['hosts_down_soft'] = hosts.find({
                '_is_template': False,
                '$or': [{'active_checks_enabled': True}, {'passive_checks_enabled': True}],
                'ls_state': 'DOWN', 'ls_state_type': 'SOFT',
                'ls_acknowledged': False, '_realm': realm['_id']
            }).count()
            data['hosts_unreachable_soft'] = hosts.find({
                '_is_template': False,
                '$or': [{'active_checks_enabled': True}, {'passive_checks_enabled': True}],
                'ls_state': 'UNREACHABLE', 'ls_state_type': 'SOFT',
                'ls_acknowledged': False, '_realm': realm['_id']
            }).count()

            data['hosts_acknowledged'] = hosts.find({
                '_is_template': False,
                '$or': [{'active_checks_enabled': True}, {'passive_checks_enabled': True}],
                'ls_acknowledged': True, '_realm': realm['_id']
            }).count()
            data['hosts_in_downtime'] = hosts.find({
                '_is_template': False,
                '$or': [{'active_checks_enabled': True}, {'passive_checks_enabled': True}],
                'ls_downtimed': True, '_realm': realm['_id']
            }).count()

            if 'ALIGNAK_BACKEND_PRINT' in os.environ:
                print("     realm %s, hosts LS: %s" % (realm['name'], data))

            lookup = {"_id": live_current['_id']}
            patch_internal('livesynthesis', data, False, False, **lookup)

            # Update services live synthesis
            services = current_app.data.driver.db['service']
            services_count = services.find({'_is_template': False, '_realm': realm['_id']}).count()
            data = {'services_total': services_count}

            data['services_not_monitored'] = services.find({
                '_is_template': False,
                'active_checks_enabled': False, 'passive_checks_enabled': False,
                '_realm': realm['_id']
            }).count()
            data['services_ok_hard'] = services.find({
                '_is_template': False,
                '$or': [{'active_checks_enabled': True}, {'passive_checks_enabled': True}],
                'ls_state': 'OK', 'ls_state_type': 'HARD',
                'ls_acknowledged': False, '_realm': realm['_id']
            }).count()
            data['services_warning_hard'] = services.find({
                '_is_template': False,
                '$or': [{'active_checks_enabled': True}, {'passive_checks_enabled': True}],
                'ls_state': 'WARNING', 'ls_state_type': 'HARD',
                'ls_acknowledged': False, '_realm': realm['_id']
            }).count()
            data['services_critical_hard'] = services.find({
                '_is_template': False,
                '$or': [{'active_checks_enabled': True}, {'passive_checks_enabled': True}],
                'ls_state': 'CRITICAL', 'ls_state_type': 'HARD',
                'ls_acknowledged': False, '_realm': realm['_id']
            }).count()
            data['services_unknown_hard'] = services.find({
                '_is_template': False,
                '$or': [{'active_checks_enabled': True}, {'passive_checks_enabled': True}],
                'ls_state': 'UNKNOWN', 'ls_state_type': 'HARD',
                'ls_acknowledged': False, '_realm': realm['_id']
            }).count()
            data['services_unreachable_hard'] = services.find({
                '_is_template': False,
                '$or': [{'active_checks_enabled': True}, {'passive_checks_enabled': True}],
                'ls_state': 'UNREACHABLE', 'ls_state_type': 'HARD',
                'ls_acknowledged': False, '_realm': realm['_id']
            }).count()

            data['services_ok_soft'] = services.find({
                '_is_template': False,
                '$or': [{'active_checks_enabled': True}, {'passive_checks_enabled': True}],
                'ls_state': 'OK', 'ls_state_type': 'SOFT',
                'ls_acknowledged': False, '_realm': realm['_id']
            }).count()
            data['services_warning_soft'] = services.find({
                '_is_template': False,
                '$or': [{'active_checks_enabled': True}, {'passive_checks_enabled': True}],
                'ls_state': 'WARNING', 'ls_state_type': 'SOFT',
                'ls_acknowledged': False, '_realm': realm['_id']
            }).count()
            data['services_critical_soft'] = services.find({
                '_is_template': False,
                '$or': [{'active_checks_enabled': True}, {'passive_checks_enabled': True}],
                'ls_state': 'CRITICAL', 'ls_state_type': 'SOFT',
                'ls_acknowledged': False, '_realm': realm['_id']
            }).count()
            data['services_unknown_soft'] = services.find({
                '_is_template': False,
                '$or': [{'active_checks_enabled': True}, {'passive_checks_enabled': True}],
                'ls_state': 'UNKNOWN', 'ls_state_type': 'SOFT',
                'ls_acknowledged': False, '_realm': realm['_id']
            }).count()
            data['services_unreachable_soft'] = services.find({
                '_is_template': False,
                '$or': [{'active_checks_enabled': True}, {'passive_checks_enabled': True}],
                'ls_state': 'UNREACHABLE', 'ls_state_type': 'SOFT',
                'ls_acknowledged': False, '_realm': realm['_id']
            }).count()

            data['services_acknowledged'] = services.find({
                '_is_template': False,
                '$or': [{'active_checks_enabled': True}, {'passive_checks_enabled': True}],
                'ls_acknowledged': True, '_realm': realm['_id']
            }).count()
            data['services_in_downtime'] = services.find({
                '_is_template': False,
                '$or': [{'active_checks_enabled': True}, {'passive_checks_enabled': True}],
                'ls_downtimed': True, '_realm': realm['_id']
            }).count()

            if 'ALIGNAK_BACKEND_PRINT' in os.environ:
                print("     realm %s, services LS: %s" % (realm['name'], data))

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
                if not item['active_checks_enabled'] and not item['passive_checks_enabled']:
                    data = {"$inc": {"%s_not_monitored" % typecheck: 1,
                                     "%s_total" % typecheck: 1}}
                else:
                    data = {"$inc": {"%s_%s_%s" % (typecheck, item['ls_state'].lower(),
                                                   item['ls_state_type'].lower()): 1,
                                     "%s_total" % typecheck: 1}}
                if 'ALIGNAK_BACKEND_PRINT' in os.environ:
                    print("LS - inserted host %s: %s..." % (item['name'], data))
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
                if not item['active_checks_enabled'] and not item['passive_checks_enabled']:
                    data = {"$inc": {"%s_not_monitored" % typecheck: 1,
                                     "%s_total" % typecheck: 1}}
                else:
                    data = {"$inc": {"%s_%s_%s" % (typecheck, item['ls_state'].lower(),
                                                   item['ls_state_type'].lower()): 1,
                                     "%s_total" % typecheck: 1}}
                if 'ALIGNAK_BACKEND_PRINT' in os.environ:
                    print("LS - inserted service %s: %s..." % (item['name'], data))
                current_app.data.driver.db.livesynthesis.update({'_id': live_current['_id']}, data)

    @staticmethod
    def on_updated_host(updated, original):
        """
            What to do when an host live state is updated ...

            If the host monitored state is changing, recalculate the live synthesis, else
            simply update the livesynthesis
        """
        if original['_is_template']:
            return

        # If the host is not monitored and we do not change its monitoring state
        if not original['active_checks_enabled'] and not original['passive_checks_enabled'] \
                and 'active_checks_enabled' not in updated \
                and 'passive_checks_enabled' not in updated:
            return

        minus, plus = Livesynthesis.livesynthesis_to_update('hosts', updated, original)
        if minus is not False:
            livesynthesis_db = current_app.data.driver.db['livesynthesis']
            live_current = livesynthesis_db.find_one({'_realm': original['_realm']})
            if live_current is None or 'not_monitored' in minus or 'not_monitored' in plus:
                ls = Livesynthesis()
                ls.recalculate()
            else:
                data = {"$inc": {minus: -1}}
                if plus is not False:
                    data = {"$inc": {minus: -1, plus: 1}}
                if 'ALIGNAK_BACKEND_PRINT' in os.environ:
                    print("LS - updated host %s: %s..." % (original['name'], data))
                current_app.data.driver.db.livesynthesis.update({'_id': live_current['_id']}, data)

    @staticmethod
    def on_updated_service(updated, original):
        """
            What to do when a service live state is updated ...

            If the service monitored state is changing, recalculate the live synthesis, else
            simply update the livesynthesis
        """
        if original['_is_template']:
            return

        # If the service is not monitored and we do not change its monitoring state
        if not original['active_checks_enabled'] and not original['passive_checks_enabled'] \
                and 'active_checks_enabled' not in updated \
                and 'passive_checks_enabled' not in updated:
            return

        minus, plus = Livesynthesis.livesynthesis_to_update('services', updated, original)
        if minus is not False:
            livesynthesis_db = current_app.data.driver.db['livesynthesis']
            live_current = livesynthesis_db.find_one({'_realm': original['_realm']})
            if live_current is None \
                    or (not isinstance(minus, bool) and 'not_monitored' in minus) \
                    or (not isinstance(plus, bool) and 'not_monitored' in plus):
                ls = Livesynthesis()
                ls.recalculate()
            else:
                data = {"$inc": {minus: -1}}
                if plus is not False:
                    data = {"$inc": {minus: -1, plus: 1}}
                if 'ALIGNAK_BACKEND_PRINT' in os.environ:
                    print("LS - updated service %s: %s..." % (original['name'], data))
                current_app.data.driver.db.livesynthesis.update({'_id': live_current['_id']}, data)

    @staticmethod
    def on_deleted_host(item):
        """When delete an host, decrement livesynthesis

        :param item: fields of the item deleted
        :type item: dict
        :return: None
        """
        if item['_is_template']:
            return

        livesynthesis_db = current_app.data.driver.db['livesynthesis']
        live_current = livesynthesis_db.find_one({'_realm': item['_realm']})
        if live_current is None:
            ls = Livesynthesis()
            ls.recalculate()
        else:
            minus = Livesynthesis.livesynthesis_to_delete('hosts', item)
            data = {"$inc": {minus: -1, 'hosts_total': -1}}
            if 'ALIGNAK_BACKEND_PRINT' in os.environ:
                print("LS - Deleted host %s: %s" % (item['name'], data))
            current_app.data.driver.db.livesynthesis.update({'_id': live_current['_id']}, data)

    @staticmethod
    def on_deleted_resource_host():
        """When delete all host (delete the resource 'host'), simply recalcule livestate

        :return: None
        """
        if 'ALIGNAK_BACKEND_PRINT' in os.environ:
            print("LS - Deleted all hosts...")
        ls = Livesynthesis()
        ls.recalculate()

    @staticmethod
    def on_deleted_service(item):
        """When delete a service, decrement livesynthesis

        :param item: fields of the item deleted
        :type item: dict
        :return: None
        """
        if item['_is_template']:
            return

        livesynthesis_db = current_app.data.driver.db['livesynthesis']
        live_current = livesynthesis_db.find_one({'_realm': item['_realm']})
        if live_current is None:
            ls = Livesynthesis()
            ls.recalculate()
        else:
            minus = Livesynthesis.livesynthesis_to_delete('services', item)
            data = {"$inc": {minus: -1, 'services_total': -1}}
            if 'ALIGNAK_BACKEND_PRINT' in os.environ:
                print("LS - Deleted service %s: %s" % (item['name'], data))
            current_app.data.driver.db.livesynthesis.update({'_id': live_current['_id']}, data)

    @staticmethod
    def on_deleted_resource_service():
        """When delete all services (delete the resource 'service'), simply recalcule livestate

        :return: None
        """
        if 'ALIGNAK_BACKEND_PRINT' in os.environ:
            print("LS - Deleted all services...")
        # the most simple method is to recalculate the livesynthesis
        ls = Livesynthesis()
        ls.recalculate()

    @staticmethod
    def livesynthesis_to_delete(type_check, item):
        """Detect when type of livestate decrement

        :param type_check: hosts | services
        :type type_check: str
        :param item: fields of the item (the host | the service)
        :type item: dict
        :return: the livesynthesis field to decrement
        :rtype: str
        """
        if not item['active_checks_enabled'] and not item['passive_checks_enabled']:
            minus = "%s_not_monitored" % (type_check)
        else:
            minus = "%s_%s_%s" % (type_check, item['ls_state'].lower(),
                                  item['ls_state_type'].lower())

        # Acknowledgement modification
        if item['ls_acknowledged']:
            minus = "%s_acknowledged" % (type_check)

        # Downtime modification
        if item['ls_downtimed']:
            minus = "%s_in_downtime" % (type_check)
        if 'ALIGNAK_BACKEND_PRINT' in os.environ:
            print("LS - Deleting %s..." % minus)
        return minus

    @staticmethod
    def livesynthesis_to_update(type_check, updated, original):
        """
        Define fields counters to minus and plus (or nothing to do)

        :param type_check:
        :param updated:
        :param original:
        :return: list with field name (minus, plus)
        :rtype: list
        """

        # State modification
        # pylint: disable=too-many-boolean-expressions
        if 'active_checks_enabled' not in updated and 'passive_checks_enabled' not in updated \
                and 'ls_state' not in updated and 'ls_state_type' not in updated \
                and 'ls_acknowledged' not in updated and 'ls_downtimed' not in updated:
            return False, False

        if 'ALIGNAK_BACKEND_PRINT' in os.environ:
            print("LS - updating: %s" % updated)
        plus = False
        minus = "%s_%s_%s" % (type_check, original['ls_state'].lower(),
                              original['ls_state_type'].lower())

        if 'active_checks_enabled' in updated or 'passive_checks_enabled' in updated:
            # From not monitored to monitored
            if not original['active_checks_enabled'] and not original['passive_checks_enabled']:
                if 'active_checks_enabled' in updated and updated['active_checks_enabled'] \
                        or 'passive_checks_enabled' in updated \
                        and updated['passive_checks_enabled']:
                    minus = "%s_not_monitored" % (type_check)

            # From monitored to not monitored
            if original['active_checks_enabled'] or original['passive_checks_enabled']:
                if 'active_checks_enabled' in updated and not updated['active_checks_enabled'] \
                        or 'passive_checks_enabled' in updated \
                        and not updated['passive_checks_enabled']:
                    plus = "%s_not_monitored" % (type_check)
        elif 'ls_state' in updated and 'ls_state_type' not in updated:
            plus = "%s_%s_%s" % (type_check, updated['ls_state'].lower(),
                                 original['ls_state_type'].lower())
        elif 'ls_state' not in updated and 'ls_state_type' in updated:
            plus = "%s_%s_%s" % (type_check, original['ls_state'].lower(),
                                 updated['ls_state_type'].lower())
        elif 'ls_state' not in updated and 'ls_state_type' not in updated:
            if 'ls_acknowledged' in updated and not updated['ls_acknowledged'] \
                    or 'ls_downtimed' in updated and not updated['ls_downtimed']:
                plus = "%s_%s_%s" % (type_check, original['ls_state'].lower(),
                                     original['ls_state_type'].lower())
        else:
            # so have 'state' and 'state_type' in updated
            plus = "%s_%s_%s" % (type_check, updated['ls_state'].lower(),
                                 updated['ls_state_type'].lower())

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

        if 'ALIGNAK_BACKEND_PRINT' in os.environ:
            print("     updating: -%s / +%s" % (minus, plus))
        if minus == plus:
            return False, False

        return minus, plus

    @staticmethod
    def on_fetched_item_history(response):
        # pylint: disable=too-many-locals
        """
        Add to response some more information.
        We manage the 2 special parameters:
         * history
         * concatenation

        :param response: the response
        :type response: dict
        :return: None
        """
        realm_drv = current_app.data.driver.db['realm']
        livesynthesis_db = current_app.data.driver.db['livesynthesis']
        livesynthesisretention_db = current_app.data.driver.db['livesynthesisretention']

        history = request.args.get('history')
        concatenation = request.args.get('concatenation')

        if 'ALIGNAK_BACKEND_PRINT' in os.environ:
            print("LS - History: %s / %s" % (history, concatenation))
        if concatenation is not None:
            # get the realm the user have access
            realm = realm_drv.find_one({'_id': response['_realm']})
            livesynthesis_id = []
            if g.get('back_role_super_admin', False):
                # no restrictions, we are admin
                livesynthesis = livesynthesis_db.find({'_realm': {'$in': realm['_all_children']}})
                for lives in livesynthesis:
                    livesynthesis_id.append(lives['_id'])
                    for prop in [x for x in lives if not x.startswith('_')]:
                        response[prop] += lives[prop]

            else:
                resources_get = g.get('resources_get', {})
                livesynthesis_access = resources_get['livesynthesis']
                custom_resources = g.get('resources_get_custom', {})
                if 'livesynthesis' in custom_resources:
                    livesynthesis_access.extend(custom_resources['livesynthesis'])
                livesynthesis = livesynthesis_db.find({'_realm': {'$in': livesynthesis_access}})
                for lives in livesynthesis:
                    if lives['_id'] != response['_id']:
                        livesynthesis_id.append(lives['_id'])
                        for prop in [x for x in lives if not x.startswith('_')]:
                            response[prop] += lives[prop]

        if history is not None:
            response['history'] = []
            lsretentions = livesynthesisretention_db.find({'livesynthesis': response['_id']}).sort(
                '_created', pymongo.DESCENDING)
            for lsretention in lsretentions:
                for prop in ['livesynthesis', '_id', '_updated', '_etag']:
                    if prop in lsretention:
                        del lsretention[prop]
                for prop in lsretention:
                    if not prop == '_created':
                        lsretention[prop] = int(lsretention[prop])
                response['history'].append(lsretention)
            if concatenation is not None:
                for ls_id in livesynthesis_id:
                    lsretentions = livesynthesisretention_db.find({'livesynthesis': ls_id}).sort(
                        '_created', pymongo.DESCENDING)
                num = 0
                for lsretention in lsretentions:
                    for prop in lsretention:
                        if not prop.startswith('_') and prop != 'livesynthesis':
                            response['history'][num][prop] += lsretention[prop]
                    num += 1

        if 'ALIGNAK_BACKEND_PRINT' in os.environ:
            if 'history' in response:
                print("LS - History: %s" % response['history'])
            else:
                print("LS - History: no history!")
