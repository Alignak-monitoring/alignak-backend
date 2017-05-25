#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    ``alignak_backend.app`` module

    This module manages the backend, its configuration and starts the backend

    Default date format is:
        '%a, %d %b %Y %H:%M:%S GMT'
"""

from __future__ import print_function

import json
import os
import re
import sys
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timedelta
from future.utils import iteritems

from eve import Eve
from eve.auth import TokenAuth
from eve.io.mongo import Validator
from eve.methods.delete import deleteitem_internal
from eve.methods.patch import patch_internal
from eve.methods.post import post_internal
from eve.utils import debug_error_message
from eve_swagger import swagger
from flask import current_app, g, request, abort, jsonify, make_response, send_from_directory, \
    redirect
from flask_apscheduler import APScheduler
from flask_bootstrap import Bootstrap
from werkzeug.security import check_password_hash, generate_password_hash
from bson.objectid import ObjectId

import alignak_backend
from alignak_backend import manifest
from alignak_backend.grafana import Grafana
from alignak_backend.livesynthesis import Livesynthesis
from alignak_backend.models import register_models
from alignak_backend.template import Template
from alignak_backend.timeseries import Timeseries

_subcommands = OrderedDict()


class MyTokenAuth(TokenAuth):
    """
    Class to manage authentication
    """
    children_realms = {}
    parent_realms = {}

    """Authentication token class"""
    def check_auth(self, token, allowed_roles, resource, method):
        # pylint: disable=too-many-locals
        """
        Check if account exist and get roles for this user

        :param token: token for auth
        :type token: str
        :param allowed_roles:
        :type allowed_roles:
        :param resource: name of the resource requested by user
        :type resource: str
        :param method: method used: GET | POST | PATCH | DELETE
        :type method: str
        :return: True if user exist and password is ok or if no roles defined, otherwise False
        :rtype: bool
        """
        user = current_app.data.driver.db['user'].find_one({'token': token})
        if user:
            # We get all resources we have in the backend for the userrestrictrole with *
            resource_list = list(current_app.config['DOMAIN'])

            g.updateRealm = False
            g.updateGroup = False
            g.user_realm = user['_realm']

            # get children of realms for rights
            realmsdrv = current_app.data.driver.db['realm']
            allrealms = realmsdrv.find()
            self.children_realms = {}
            self.parent_realms = {}
            for realm in allrealms:
                self.children_realms[realm['_id']] = realm['_all_children']
                self.parent_realms[realm['_id']] = realm['_tree_parents']

            g.back_role_super_admin = user['back_role_super_admin']
            g.can_submit_commands = user['can_submit_commands']
            userrestrictroles = current_app.data.driver.db['userrestrictrole']
            userrestrictrole = userrestrictroles.find({'user': user['_id']})
            g.resources_get = {}
            g.resources_get_parents = {}
            get_parents = {}
            g.resources_get_custom = {}
            g.resources_post = {}
            g.resources_post_parents = {}
            g.resources_patch = {}
            g.resources_patch_parents = {}
            g.resources_patch_custom = {}
            g.resources_delete = {}
            g.resources_delete_parents = {}
            g.resources_delete_custom = {}
            for rights in userrestrictrole:
                self.add_resources_realms('read', rights, False, g.resources_get, resource_list,
                                          get_parents)
                self.add_resources_realms('read', rights, True, g.resources_get_custom,
                                          resource_list)
                self.add_resources_realms('create', rights, False, g.resources_post, resource_list)
                self.add_resources_realms('update', rights, False, g.resources_patch,
                                          resource_list)
                self.add_resources_realms('update', rights, True, g.resources_patch_custom,
                                          resource_list)
                self.add_resources_realms('delete', rights, False, g.resources_delete,
                                          resource_list)
                self.add_resources_realms('delete', rights, True, g.resources_delete_custom,
                                          resource_list)
            for res in g.resources_get:
                g.resources_get[res] = list(set(g.resources_get[res]))
                if res in g.resources_get_custom:
                    g.resources_get_custom[res] = list(set(g.resources_get_custom[res]))
                g.resources_get_parents[res] = [item for item in get_parents[res]
                                                if item not in g.resources_get[res]]
            for res in g.resources_post:
                g.resources_post[res] = list(set(g.resources_post[res]))
            for res in g.resources_patch:
                g.resources_patch[res] = list(set(g.resources_patch[res]))
            for res in g.resources_delete:
                g.resources_delete[res] = list(set(g.resources_delete[res]))
            g.users_id = user['_id']
            self.set_request_auth_value(user['_id'])
        return user

    def add_resources_realms(self, right, data, custom, resource, resource_list, parents=None):
        """
        Add realms found for rights. it's used to fill rights when connect to app

        :param right: right in list: create, read, update, delete
        :type right: str
        :param data: data (one record) from userrestrictrole (from mongo)
        :type data: dict
        :param custom: True if it's a custom right, otherwise False
        :type custom: bool
        :param resource: variable where store realm rights
        :type resource: dict
        :param resource_list: list of all resources of the backend
        :type resource_list: list
        :param parents: variable where store parents realms (required only for read right)
        :type parents: dict or None
        :return: None
        """
        # pylint: disable=too-many-arguments
        search_field = right
        if custom:
            search_field = 'custom'
        if data['resource'] == '*':
            my_resources = resource_list
        else:
            my_resources = [data['resource']]
        if search_field in data['crud']:
            for my_resource in my_resources:
                if my_resource not in resource:
                    resource[my_resource] = []
                if right == 'read' and not custom and my_resource not in parents:
                    parents[my_resource] = []
                resource[my_resource].append(data['realm'])
                if right == 'read' and not custom:
                    parents[my_resource].extend(self.parent_realms[data['realm']])
                if data['sub_realm']:
                    resource[my_resource].extend(self.children_realms[data['realm']])


class MyValidator(Validator):
    """Specific validator for data model fields types extension"""
    # pylint: disable=unused-argument
    def _validate_skill_level(self, skill_level, field, value):
        """Validate 'skill_level' field (always valid)"""
        return

    # pylint: disable=unused-argument
    def _validate_title(self, title, field, value):
        """Validate 'title' field (always valid)"""
        return

    # pylint: disable=unused-argument
    def _validate_comment(self, comment, field, value):
        """Validate 'comment' field (always valid)"""
        return


# Hooks used to check user's rights
def pre_get(resource, user_request, lookup):
    """Hook before get data. Add filter depend on roles of user

    :param resource: name of the resource requested by user
    :type resource: str
    :param user_request: request of the user
    :type user_request: object
    :param lookup: values to get (filter in the request)
    :type lookup: dict
    :return: None
    """
    # pylint: disable=unused-argument
    if g.get('back_role_super_admin', False):
        return

    # Only if not super-admin
    if resource not in ['user']:
        # Get all resources we can have rights for reading
        resources_get = g.get('resources_get', {})
        resources_get_parents = g.get('resources_get_parents', {})
        resources_get_custom = g.get('resources_get_custom', {})
        users_id = g.get('users_id', {})

        if resource not in resources_get and resource not in resources_get_custom:
            lookup["_id"] = ''
        else:
            if resource not in resources_get:
                resources_get[resource] = []
            if resource not in resources_get_parents:
                resources_get_parents[resource] = []
            if resource not in resources_get_custom:
                resources_get_custom[resource] = []
            if resource in ['realm']:
                lookup['$or'] = [{'_id': {'$in': resources_get[resource]}}]
            else:
                lookup['$or'] = [{'_realm': {'$in': resources_get[resource]}},
                                 {'$and': [{'_sub_realm': True},
                                           {'_realm': {'$in': resources_get_parents[resource]}}]},
                                 {'$and': [{'_users_read': users_id},
                                           {'_realm': {'$in': resources_get_custom[resource]}}]}]


def pre_post(resource, user_request):
    """Hook before get posting data.

    Check if the user restrictions match the request

    :param resource: name of the resource requested by user
    :type resource: str
    :param user_request: request of the user
    :type user_request: object
    :return: None
    """
    # pylint: disable=unused-argument
    if g.get('back_role_super_admin', False):
        return

    # Only for some resources ...
    if resource not in ['user', 'actionacknowledge', 'actiondowntime', 'actionforcecheck']:
        # Get all resources we can have rights for creation
        resources_post = g.get('resources_post', {})
        resources_post_custom = g.get('resources_post_custom', {})

        if resource not in resources_post and resource not in resources_post_custom:
            abort(401, description='Not allowed to POST on this endpoint / resource.')


def pre_patch(resource, user_request, lookup):
    """Hook before updating data.

    Check if the user restrictions match the request

    :param resource: name of the resource requested by user
    :type resource: str
    :param user_request: request of the user
    :type user_request: object
    :param lookup: values to get (filter in the request)
    :type lookup: dict
    :return: None
    """
    # pylint: disable=unused-argument
    if g.get('back_role_super_admin', False):
        return

    # Only for some resources ...
    if resource not in ['user', 'actionacknowledge', 'actiondowntime', 'actionforcecheck']:
        # Get all resources we can have rights for updating
        resources_patch = g.get('resources_patch', {})
        resources_patch_parents = g.get('resources_patch_parents', {})
        resources_patch_custom = g.get('resources_patch_custom', {})
        users_id = g.get('users_id', {})

        if resource not in resources_patch and resource not in resources_patch_custom:
            abort(401, description='Not allowed to PATCH on this endpoint / resource.')
        else:
            if resource not in resources_patch:
                resources_patch[resource] = []
            if resource not in resources_patch_parents:
                resources_patch_parents[resource] = []
            if resource not in resources_patch_custom:
                resources_patch_custom[resource] = []
            if resource in ['realm']:
                lookup['$or'] = [{'_id': {'$in': resources_patch[resource]}}]
            else:
                lookup['$or'] = [{'_realm': {'$in': resources_patch[resource]}},
                                 {'$and': [{'_sub_realm': True},
                                           {'_realm': {'$in': resources_patch_parents[resource]}}]},
                                 {'$and': [{'_users_update': users_id},
                                           {'_realm': {'$in': resources_patch_custom[resource]}}]}]


def pre_delete(resource, user_request, lookup):
    """Hook before deleting data.

    Check if the user restrictions match the request

    :param resource: name of the resource requested by user
    :type resource: str
    :param user_request: request of the user
    :type user_request: object
    :param lookup: values to get (filter in the request)
    :type lookup: dict
    :return: None
    """
    # pylint: disable=unused-argument
    if g.get('back_role_super_admin', False):
        return

    # Only if not super-admin
    if resource not in ['user']:
        # Get all resources we can have rights for delation
        resources_delete = g.get('resources_delete', {})
        resources_delete_parents = g.get('resources_delete_parents', {})
        resources_delete_custom = g.get('resources_delete_custom', {})
        users_id = g.get('users_id', {})

        print("delete: %s" % (resources_delete))
        if resource not in resources_delete and resource not in resources_delete_custom:
            abort(401, description='Not allowed to DELETE on this endpoint / resource.')
        else:
            if resource not in resources_delete:
                resources_delete[resource] = []
            if resource not in resources_delete_parents:
                resources_delete_parents[resource] = []
            if resource not in resources_delete_custom:
                resources_delete_custom[resource] = []
            if resource in ['realm']:
                lookup['$or'] = [{'_id': {'$in': resources_delete[resource]}}]
            else:
                lookup['$or'] = [{'_realm': {'$in': resources_delete[resource]}},
                                 {'$and': [{'_sub_realm': True},
                                           {'_realm': {
                                               '$in': resources_delete_parents[resource]}}]},
                                 {'$and': [{'_users_delete': users_id},
                                           {'_realm': {
                                               '$in': resources_delete_custom[resource]}}]}]


# Escalations
def pre_hostescalation_post(items):
    """Hook before adding new serviceescalation element

    If no escalation_period is provided then the 24x7 default TP will be used.

    :param items: provided serviceescalation elements
    :type items: list of dict
    :return: None
    """
    for dummy, item in enumerate(items):
        if 'escalation_period' not in item:
            tps = app.data.driver.db['timeperiod']
            tp_always = tps.find_one({'name': '24x7'})
            item['escalation_period'] = tp_always['_id']


def pre_serviceescalation_post(items):
    """Hook before adding new serviceescalation element

    If no escalation_period is provided then the 24x7 default TP will be used.

    :param items: provided serviceescalation elements
    :type items: list of dict
    :return: None
    """
    for dummy, item in enumerate(items):
        if 'escalation_period' not in item:
            tps = app.data.driver.db['timeperiod']
            tp_always = tps.find_one({'name': '24x7'})
            item['escalation_period'] = tp_always['_id']


# History
def pre_history_post(items):
    """
    Hook before adding new history element

    If host _id is not provided, search for an host with host_name. Same for service and user.

    :param items: history fields
    :type items: dict
    :return: None
    """
    hosts_drv = current_app.data.driver.db['host']
    services_drv = current_app.data.driver.db['service']
    users_drv = current_app.data.driver.db['user']
    for dummy, item in enumerate(items):
        if 'host' in item and item['host']:
            host = hosts_drv.find_one({'_id': item['host']})
            if host:
                item['host_name'] = host['name']
            else:
                continue
        elif 'host_name' in item and item['host_name']:
            host = hosts_drv.find_one({'name': item['host_name']})
            if host:
                item['host'] = host['_id']
            else:
                continue
        else:
            continue

        host = hosts_drv.find_one({'_id': item['host']})
        # Set _realm as host's _realm
        item['_realm'] = host['_realm']
        item['_sub_realm'] = host['_sub_realm']

        # Find service and service_name
        if 'service' in item and item['service']:
            service = services_drv.find_one({'_id': item['service']})
            if service:
                item['service_name'] = service['name']
        elif 'service_name' in item and item['service_name']:
            service = services_drv.find_one({'host': item['host'], 'name': item['service_name']})
            if service:
                item['service'] = service['_id']

        # Find user and user_name
        if 'user' in item and item['user']:
            user = users_drv.find_one({'_id': item['user']})
            if user:
                item['user_name'] = user['name']
        elif 'user_name' in item and item['user_name']:
            user = users_drv.find_one({'name': item['user_name']})
            if user:
                item['user'] = user['_id']
        else:
            item['user_name'] = 'Alignak'
            item['user'] = None


# Log checks results
def pre_logcheckresult_post(items):
    """
    Hook before adding new forcecheck

    :param items: logcheckresult fields
    :type items: dict
    :return: None
    """
    hosts_drv = current_app.data.driver.db['host']
    services_drv = current_app.data.driver.db['service']
    for dummy, item in enumerate(items):
        # Set _realm as host's _realm
        host = hosts_drv.find_one({'_id': item['host']})
        item['_realm'] = host['_realm']
        item['host_name'] = host['name']

        # Find service_name
        if item['service'] and 'service_name' not in item:
            service = services_drv.find_one({'_id': item['service']})
            item['service_name'] = service['name']
        else:
            item['service_name'] = ''


def after_insert_logcheckresult(items):
    """
    Hook after logcheckresult inserted.

    :param items: realm fields
    :type items: dict
    :return: None
    """
    for dummy, item in enumerate(items):
        # Create an history event for the new forcecheck
        message = "%s[%s] (%s/%s): %s" % (item['state'], item['state_type'],
                                          item['acknowledged'], item['downtimed'],
                                          item['output'])
        data = {
            'host': item['host'],
            'host_name': item['host_name'],
            'service': item['service'],
            'service_name': item['service_name'],
            'user': None,
            'type': 'check.result',
            'message': message,
            'logcheckresult': item['_id']
        }
        post_internal("history", data, True)


def pre_post_action_right(actrequestp):
    """Deny post on action* endpoint if the logged-in user do not have can_submit_commands

    :param actrequestp:
    :return:
    """
    # pylint: disable=unused-argument
    if not g.get('can_submit_commands', False):
        abort(403)


def pre_submit_action_right(actrequest, lookup):
    # pylint: disable=unused-argument
    """Deny patch or delete action* endpoint if the logged-in user do not have can_submit_commands

    :param actrequest:
    :param lookup:
    :return:
    """
    if not g.get('can_submit_commands', False):
        abort(403)


# Actions acknowledge
def pre_actionacknowledge_post(items):
    """
    Hook before adding new acknowledge

    :param items: actionacknowledge fields
    :type items: dict
    :return: None
    """
    hosts_drv = current_app.data.driver.db['host']
    for dummy, item in enumerate(items):
        # Set _realm as host's _realm
        host = hosts_drv.find_one({'_id': item['host']})
        item['_realm'] = host['_realm']
        item['_sub_realm'] = host['_sub_realm']


def after_insert_actionacknowledge(items):
    """
    Hook after action acknowledge inserted.

    :param items: realm fields
    :type items: dict
    :return: None
    """
    hosts_drv = current_app.data.driver.db['host']
    services_drv = current_app.data.driver.db['service']
    for dummy, item in enumerate(items):
        # Get concerned host
        host = hosts_drv.find_one({'_id': item['host']})
        service_name = ''
        if item['service']:
            service = services_drv.find_one({'_id': item['service']})
            service_name = service['name']

        # Create an history event for the new acknowledge
        data = {
            'host': item['host'],
            'host_name': host['name'],
            'service': item['service'],
            'service_name': service_name,
            'user': item['user'],
            'type': 'ack.' + item['action'],
            'message': item['comment']
        }
        post_internal("history", data, True)


def after_update_actionacknowledge(updated, original):
    """
    Hook update on actionacknowledge

    :param updated: modified fields
    :type updated: dict
    :param original: original fields
    :type original: dict
    :return: None
    """
    if 'processed' in updated and updated['processed']:
        hosts_drv = current_app.data.driver.db['host']
        services_drv = current_app.data.driver.db['service']

        # Get concerned host
        host = hosts_drv.find_one({'_id': original['host']})
        service_name = ''
        if original['service']:
            service = services_drv.find_one({'_id': original['service']})
            service_name = service['name']

        # Create an history event for the changed acknowledge
        data = {
            'host': original['host'],
            'host_name': host['name'],
            'service': original['service'],
            'service_name': service_name,
            'user': original['user'],
            'type': 'ack.processed',
            'message': original['comment'],
            'content': {
            }
        }
        post_internal("history", data, True)


# Actions downtime
def pre_actiondowntime_post(items):
    """
    Hook before adding new downtime

    :param items: actiondowntime fields
    :type items: dict
    :return: None
    """
    hosts_drv = current_app.data.driver.db['host']
    for dummy, item in enumerate(items):
        # Set _realm as host's _realm
        host = hosts_drv.find_one({'_id': item['host']})
        item['_realm'] = host['_realm']
        item['_sub_realm'] = host['_sub_realm']


def after_insert_actiondowntime(items):
    """
    Hook after action downtime inserted.

    :param items: realm fields
    :type items: dict
    :return: None
    """
    hosts_drv = current_app.data.driver.db['host']
    services_drv = current_app.data.driver.db['service']
    for dummy, item in enumerate(items):
        # Get concerned host
        host = hosts_drv.find_one({'_id': item['host']})
        service_name = ''
        if item['service']:
            service = services_drv.find_one({'_id': item['service']})
            service_name = service['name']

        # Create an history event for the new downtime
        data = {
            'host': item['host'],
            'host_name': host['name'],
            'service': item['service'],
            'service_name': service_name,
            'user': item['user'],
            'type': 'downtime.' + item['action'],
            'message': item['comment']
        }
        post_internal("history", data, True)


def after_update_actiondowntime(updated, original):
    """
    Hook update on actiondowntime

    :param updated: modified fields
    :type updated: dict
    :param original: original fields
    :type original: dict
    :return: None
    """
    if 'processed' in updated and updated['processed']:
        hosts_drv = current_app.data.driver.db['host']
        services_drv = current_app.data.driver.db['service']

        # Get concerned host
        host = hosts_drv.find_one({'_id': original['host']})
        service_name = ''
        if original['service']:
            service = services_drv.find_one({'_id': original['service']})
            service_name = service['name']

        # Create an history event for the changed downtime
        data = {
            'host': original['host'],
            'host_name': host['name'],
            'service': original['service'],
            'service_name': service_name,
            'user': original['user'],
            'type': 'downtime.processed',
            'message': original['comment'],
            'content': {
            }
        }
        post_internal("history", data, True)


# Actions forcecheck
def pre_actionforcecheck_post(items):
    """
    Hook before adding new forcecheck

    :param items: actionforcecheck fields
    :type items: dict
    :return: None
    """
    hosts_drv = current_app.data.driver.db['host']
    for dummy, item in enumerate(items):
        # Set _realm as host's _realm
        host = hosts_drv.find_one({'_id': item['host']})
        item['_realm'] = host['_realm']
        item['_sub_realm'] = host['_sub_realm']


def after_insert_actionforcecheck(items):
    """
    Hook after action forcecheck inserted.

    :param items: realm fields
    :type items: dict
    :return: None
    """
    hosts_drv = current_app.data.driver.db['host']
    services_drv = current_app.data.driver.db['service']
    for dummy, item in enumerate(items):
        # Get concerned host
        host = hosts_drv.find_one({'_id': item['host']})
        service_name = ''
        if item['service']:
            service = services_drv.find_one({'_id': item['service']})
            service_name = service['name']

        # Create an history event for the new forcecheck
        data = {
            'host': item['host'],
            'host_name': host['name'],
            'service': item['service'],
            'service_name': service_name,
            'user': item['user'],
            'type': 'check.request',
            'message': item['comment']
        }
        post_internal("history", data, True)


def after_update_actionforcecheck(updated, original):
    """
    Hook update on actionforcecheck

    :param updated: modified fields
    :type updated: dict
    :param original: original fields
    :type original: dict
    :return: None
    """
    if 'processed' in updated and updated['processed']:
        hosts_drv = current_app.data.driver.db['host']
        services_drv = current_app.data.driver.db['service']

        # Get concerned host
        host = hosts_drv.find_one({'_id': original['host']})
        service_name = ''
        if original['service']:
            service = services_drv.find_one({'_id': original['service']})
            service_name = service['name']

        # Create an history event for the changed forcecheck
        data = {
            'host': original['host'],
            'host_name': host['name'],
            'service': original['service'],
            'service_name': service_name,
            'user': original['user'],
            'type': 'check.requested',
            'message': original['comment'],
            'content': {
            }
        }
        post_internal("history", data, True)


# Hosts groups
def pre_hostgroup_post(items):
    """
    Hook before adding a new hostgroup

    Manage hostgroup level and parents tree.

    :param items: hostgroup fields
    :type items: dict
    :return: None
    """
    hgs_drv = current_app.data.driver.db['hostgroup']
    for dummy, item in enumerate(items):
        # Default parent
        if '_parent' not in item:
            # Use default hostgroup as a parent
            def_hg = hgs_drv.find_one({'name': 'All'})
            if def_hg:
                item['_parent'] = def_hg['_id']

        # Compute _level
        parent_hg = hgs_drv.find_one({'_id': item['_parent']})
        item['_level'] = parent_hg['_level'] + 1

        # Add parent in _tree_parents
        item['_tree_parents'] = parent_hg['_tree_parents']
        item['_tree_parents'].append(parent_hg['_id'])


def pre_hostgroup_patch(updates, original):
    """
    Hook before updating existing hostgroup

    :param updates: modified fields
    :type updates: dict
    :param original: original fields
    :type original: dict
    :return: None
    """
    if not g.updateGroup:
        if '_tree_parents' in updates:
            abort(make_response("Updating _tree_parents is forbidden", 412))

    if '_parent' in updates and updates['_parent'] != original['_parent']:
        hgs_drv = current_app.data.driver.db['hostgroup']

        # Find parent
        parent_hg = hgs_drv.find_one({'_id': updates['_parent']})
        if not parent_hg:
            abort(make_response("Error: parent not found: %s" % updates['_parent'], 412))

        # Compute _level
        updates['_level'] = parent_hg['_level'] + 1

        # Add parent in _tree_parents
        updates['_tree_parents'] = parent_hg['_tree_parents']
        updates['_tree_parents'].append(parent_hg['_id'])


# Services groups
def pre_servicegroup_post(items):
    """
    Hook before adding a new servicegroup

    Manage servicegroup level and parents tree.

    :param items: servicegroup fields
    :type items: dict
    :return: None
    """
    sgs_drv = current_app.data.driver.db['servicegroup']
    for dummy, item in enumerate(items):
        # Default parent
        if '_parent' not in item:
            # Use default servicegroup as a parent
            def_sg = sgs_drv.find_one({'name': 'All'})
            if def_sg:
                item['_parent'] = def_sg['_id']

        # Compute _level
        parent_sg = sgs_drv.find_one({'_id': item['_parent']})
        item['_level'] = parent_sg['_level'] + 1

        # Add parent in _tree_parents
        item['_tree_parents'] = parent_sg['_tree_parents']
        item['_tree_parents'].append(parent_sg['_id'])


def pre_servicegroup_patch(updates, original):
    """
    Hook before updating existing servicegroup

    :param updates: modified fields
    :type updates: dict
    :param original: original fields
    :type original: dict
    :return: None
    """
    if not g.updateGroup:
        if '_tree_parents' in updates:
            abort(make_response("Updating _tree_parents is forbidden", 412))

    if '_parent' in updates and updates['_parent'] != original['_parent']:
        sgs_drv = current_app.data.driver.db['servicegroup']

        # Find parent
        parent_sg = sgs_drv.find_one({'_id': updates['_parent']})
        if not parent_sg:
            abort(make_response("Error: parent not found: %s" % updates['_parent'], 412))

        # Compute _level
        updates['_level'] = parent_sg['_level'] + 1

        # Add parent in _tree_parents
        updates['_tree_parents'] = parent_sg['_tree_parents']
        updates['_tree_parents'].append(parent_sg['_id'])


# Users groups
def pre_usergroup_post(items):
    """
    Hook before adding a new usergroup

    Manage usergroup level and parents tree.

    :param items: usergroup fields
    :type items: dict
    :return: None
    """
    ugs_drv = current_app.data.driver.db['usergroup']
    for dummy, item in enumerate(items):
        # Default parent
        if '_parent' not in item:
            # Use default usergroup as a parent
            def_ug = ugs_drv.find_one({'name': 'All'})
            if def_ug:
                item['_parent'] = def_ug['_id']

        # Compute _level
        parent_ug = ugs_drv.find_one({'_id': item['_parent']})
        item['_level'] = parent_ug['_level'] + 1

        # Add parent in _tree_parents
        item['_tree_parents'] = parent_ug['_tree_parents']
        item['_tree_parents'].append(parent_ug['_id'])


def pre_usergroup_patch(updates, original):
    """
    Hook before updating existing usergroup

    :param updates: modified fields
    :type updates: dict
    :param original: original fields
    :type original: dict
    :return: None
    """
    if not g.updateGroup:
        if '_tree_parents' in updates:
            abort(make_response("Updating _tree_parents is forbidden", 412))

    if '_parent' in updates and updates['_parent'] != original['_parent']:
        ugs_drv = current_app.data.driver.db['usergroup']

        # Find parent
        parent_ug = ugs_drv.find_one({'_id': updates['_parent']})
        if not parent_ug:
            abort(make_response("Error: parent not found: %s" % updates['_parent'], 412))

        # Compute _level
        updates['_level'] = parent_ug['_level'] + 1

        # Add parent in _tree_parents
        updates['_tree_parents'] = parent_ug['_tree_parents']
        updates['_tree_parents'].append(parent_ug['_id'])


# Time series
def pre_timeseries_post(items):
    """
    We can't have more than 1 timeseries database (graphite, influx) linked to the same
    grafana in the same realm

    :param items:
    :type items: dict
    :return: None
    """
    graphite_drv = current_app.data.driver.db['graphite']
    influxdb_drv = current_app.data.driver.db['influxdb']
    realm_drv = current_app.data.driver.db['realm']
    for dummy, item in enumerate(items):
        if 'grafana' in item and item['grafana'] is not None:
            # search graphite with grafana id in this realm
            if graphite_drv.find(
                    {'_realm': item['_realm'], 'grafana': item['grafana']}).count() > 0:
                abort(make_response("A timeserie is yet attached to grafana in this realm", 412))
            # search influxdb with grafana id in this realm
            if influxdb_drv.find(
                    {'_realm': item['_realm'], 'grafana': item['grafana']}).count() > 0:
                abort(make_response("A timeserie is yet attached to grafana in this realm", 412))
            # get parent realms
            tsrealms = realm_drv.find_one({'_id': item['_realm']})
            if graphite_drv.find(
                    {'_realm': {'$in': tsrealms['_tree_parents']}, 'grafana': item['grafana'],
                     '_sub_realm': True}).count() > 0:
                abort(make_response("A timeserie is yet attached to grafana in parent realm", 412))
            if influxdb_drv.find(
                    {'_realm': {'$in': tsrealms['_tree_parents']}, 'grafana': item['grafana'],
                     '_sub_realm': True}).count() > 0:
                abort(make_response("A timeserie is yet attached to grafana in parent realm", 412))


# Realms
def pre_realm_post(items):
    """
    Hook before adding new realm

    :param items: realm fields
    :type items: dict
    :return: None
    """
    realmsdrv = current_app.data.driver.db['realm']
    for dummy, item in enumerate(items):
        # Default parent
        if '_parent' not in item:
            # Use default realm as a parent
            dr = realmsdrv.find_one({'name': 'All'})
            item['_parent'] = dr['_id']

        # Compute _level
        parent_realm = realmsdrv.find_one({'_id': item['_parent']})
        item['_level'] = parent_realm['_level'] + 1

        # Add parent in _tree_parents
        item['_tree_parents'] = parent_realm['_tree_parents']
        item['_tree_parents'].append(parent_realm['_id'])


def pre_realm_patch(updates, original):
    """
    Hook before updating existing realm

    :param updates: modified fields
    :type updates: dict
    :param original: original fields
    :type original: dict
    :return: None
    """
    if not g.updateRealm:
        if '_tree_parents' in updates:
            abort(make_response("Updating _tree_parents is forbidden", 412))
        if '_children' in updates:
            abort(make_response("Updating _children is forbidden", 412))
        if '_all_children' in updates:
            abort(make_response("Updating _all_children is forbidden", 412))

    if '_parent' in updates and updates['_parent'] != original['_parent']:
        realmsdrv = current_app.data.driver.db['realm']

        # Add self reference in new parent children tree
        parent = realmsdrv.find_one({'_id': updates['_parent']})
        if original['_id'] not in parent['_children']:
            parent['_children'].append(original['_id'])
        lookup = {"_id": parent['_id']}
        g.updateRealm = True
        patch_internal('realm', {"_children": parent['_children']}, False, False,
                       **lookup)
        g.updateRealm = False

        # Delete self reference in former parent children tree
        if original['_tree_parents']:
            parent = realmsdrv.find_one({'_id': original['_tree_parents'][-1]})
            if original['_id'] in parent['_children']:
                parent['_children'].remove(original['_id'])
            lookup = {"_id": parent['_id']}
            g.updateRealm = True
            patch_internal('realm', {"_children": parent['_children']}, False, False,
                           **lookup)
            g.updateRealm = False

        updates['_level'] = parent['_level'] + 1
        updates['_tree_parents'] = original['_tree_parents']
        if original['_parent'] in original['_tree_parents']:
            updates['_tree_parents'].remove(original['_parent'])
        if updates['_parent'] not in original['_tree_parents']:
            updates['_tree_parents'].append(updates['_parent'])


def after_insert_realm(items):
    """
    Hook after realm inserted. It calculate/update tree parents and children

    :param items: realm fields
    :type items: dict
    :return: None
    """
    # pylint: disable=unused-argument
    for dummy, item in enumerate(items):
        # update _children fields on all parents
        realmsdrv = current_app.data.driver.db['realm']
        parent = realmsdrv.find_one({'_id': item['_parent']})
        parent['_children'].append(item['_id'])
        parent['_all_children'].append(item['_id'])
        lookup = {"_id": parent['_id']}
        g.updateRealm = True
        patch_internal('realm', {
            "_children": parent['_children'],
            "_all_children": parent['_all_children']
        }, False, False, **lookup)
        g.updateRealm = False


def after_update_realm(updated, original):
    """
    Hook update tree children on realm parent after update tree children realm

    :param updated: modified fields
    :type updated: dict
    :param original: original fields
    :type original: dict
    :return: None
    """
    if g.updateRealm:
        if '_all_children' in updated and updated['_all_children'] != original['_all_children']:
            s = set(original['_all_children'])
            diff = [x for x in updated['_all_children'] if x not in s]
            added_children = (diff != [])
            if not added_children:
                s = set(updated['_all_children'])
                diff = [x for x in original['_all_children'] if x not in s]

            realmsdrv = current_app.data.driver.db['realm']
            parent = realmsdrv.find_one({'_id': original['_parent']})
            if not parent:
                return

            for d in diff:
                if added_children:
                    if d not in parent['_all_children']:
                        parent['_all_children'].append(d)
                else:
                    if d in parent['_all_children']:
                        parent['_all_children'].remove(d)
            lookup = {"_id": parent['_id']}
            g.updateRealm = True
            patch_internal('realm', {
                "_all_children": parent['_all_children']
            }, False, False, **lookup)
            g.updateRealm = False


def pre_delete_realm(item):
    """
    Hook before deleting a realm. Denies deletion if realm has child / children

    :param item: fields of the item / record
    :type item: dict
    :return: None
    """
    if item['_children']:
        abort(409, description=debug_error_message("Item have children, so can't delete it"))


def after_delete_realm(item):
    """
    Hook after realm deletion. Update tree children of parent realm

    :param item: fields of the item / record
    :type item: dict
    :return: None
    """
    realmsdrv = current_app.data.driver.db['realm']
    if item['_tree_parents']:
        parent = realmsdrv.find_one({'_id': item['_tree_parents'][-1]})
        if item['_id'] in parent['_children']:
            parent['_children'].remove(item['_id'])
        if item['_id'] in parent['_all_children']:
            parent['_all_children'].remove(item['_id'])
        lookup = {"_id": parent['_id']}
        g.updateRealm = True
        patch_internal('realm', {
            "_children": parent['_children'],
            "_all_children": parent['_children']
        }, False, False, **lookup)
        g.updateRealm = False


def after_delete_resource_realm():
    """
    We deleted all resource realm, so define _children and _all_children of realm All to []

    :return: None
    """
    realmsdrv = current_app.data.driver.db['realm']
    realmall = realmsdrv.find_one({'_level': 0})
    lookup = {"_id": realmall['_id']}
    g.updateRealm = True
    patch_internal('realm', {
        '_children': [],
        '_all_children': []
    }, False, False, **lookup)
    g.updateRealm = False


# Hosts deletion
def pre_delete_host(item):
    """Hook before deleting an host.
    Searches for the host services and deletes them

    :param item: fields of the item / record
    :type item: dict
    :return: None
    """
    print("Deleting host: %s" % item['name'])
    services_drv = current_app.data.driver.db['service']
    services = services_drv.find({'host': item['_id']})
    for service in services:
        print("Deleting service: %s/%s" % (item['name'], service['name']))
        lookup = {"_id": service['_id']}
        deleteitem_internal('service', False, False, **lookup)


def after_delete_host(item):
    """Hook after host deletion. Update tree children of parent host

    :param item: fields of the item / record
    :type item: dict
    :return: None
    """
    print("Deleted host: %s" % item['name'])


# Alignak
def pre_alignak_patch(updates, original):
    # pylint: disable=unused-argument
    """Hook before updating an alignak element.

    When updating an alignak, if only the running data are updated, do not change the
    _updated field.

    :param updates: list of alignak fields to update
    :type updates: dict
    :param original: list of original fields
    :type original: dict
    :return: None
    """
    for key in updates:
        if key not in ['_updated', 'last_alive', 'last_command_check', 'last_log_rotation']:
            break
    else:
        # Only the running fields were updated, do not change _updated field
        del updates['_updated']


# Hosts/ services
def pre_host_patch(updates, original):
    """
    Hook before updating an host element.

    When updating an host, if only the live state is updated, do not change the
    _updated field and compute the new host overall state..

    Compute the host overall state identifier, including:
    - the acknowledged state
    - the downtime state

    The worst state is (prioritized):
    - an host down (4)
    - an host unreachable (3)
    - an host downtimed (2)
    - an host acknowledged (1)
    - an host up (0)

    If the host overall state is <= 2, then the host overall state is the maximum value
    of the host overall state and all the host services overall states.

    The overall state of an host is:
    - 0 if the host is UP and all its services are OK
    - 1 if the host is DOWN or UNREACHABLE and acknowledged or
        at least one of its services is acknowledged and
        no other services are WARNING or CRITICAL
    - 2 if the host is DOWN or UNREACHABLE and in a scheduled downtime or
        at least one of its services is in a scheduled downtime and no
        other services are WARNING or CRITICAL
    - 3 if the host is UNREACHABLE or
        at least one of its services is WARNING
    - 4 if the host is DOWN or
        at least one of its services is CRITICAL

    The _updated field is used by the Alignak arbiter to reload the configuration and we need to
    avoid reloading when the live state is updated.

    :param updates: list of host fields to update
    :type updates: dict
    :param original: list of original fields
    :type original: dict
    :return: None
    """
    for key in updates:
        if key in ['_realm']:
            services_drv = current_app.data.driver.db['service']
            services = services_drv.find({'host': original['_id']})
            for service in services:
                lookup = {"_id": service['_id']}
                patch_internal('service', {"_realm": updates['_realm']}, False, False, **lookup)

        if key not in ['_overall_state_id', '_updated', '_realm'] and not key.startswith('ls_'):
            break
    else:
        # We updated the host live state, compute the new overall state, or
        # We updated some host services live state, compute the new overall state
        if ('_overall_state_id' in updates and updates['_overall_state_id'] == -1) or \
                ('ls_state_type' in updates and updates['ls_state_type'] == 'HARD'):

            overall_state = 0

            acknowledged = original['ls_acknowledged']
            if 'ls_acknowledged' in updates:
                acknowledged = updates['ls_acknowledged']

            downtimed = original['ls_downtimed']
            if 'ls_downtimed' in updates:
                downtimed = updates['ls_downtimed']

            state = original['ls_state']
            if 'ls_state' in updates:
                state = updates['ls_state']
            state = state.upper()

            if acknowledged:
                overall_state = 1
            elif downtimed:
                overall_state = 2
            else:
                if state == 'UNREACHABLE':
                    overall_state = 3
                elif state == 'DOWN':
                    overall_state = 4

            if overall_state <= 2:
                services_drv = current_app.data.driver.db['service']
                services = services_drv.find({'host': original['_id']})
                for service in services:
                    if service['ls_state_type'] == 'HARD':
                        overall_state = max(overall_state, service['_overall_state_id'])

            # Get the host services overall states
            updates['_overall_state_id'] = overall_state

        # Only some live state fields, do not change _updated field
        del updates['_updated']


def after_insert_host(items):
    """
    Hook after host inserted.

    :param items: host fields
    :type items: dict
    :return: None
    """
    etags = {}
    for dummy, item in enumerate(items):
        overall_state = 0

        acknowledged = item['ls_acknowledged']
        downtimed = item['ls_downtimed']
        state = item['ls_state']
        state = state.upper()

        if acknowledged:
            overall_state = 1
        elif downtimed:
            overall_state = 2
        else:
            if state == 'UNREACHABLE':
                overall_state = 3
            elif state == 'DOWN':
                overall_state = 4

        # Do not care about services... when inserting an host,
        # services are not yet existing for this host!

        # Host overall was computed, update the host overall state
        lookup = {"_id": item['_id']}
        (_, _, etag, _) = patch_internal('host', {"_overall_state_id": overall_state}, False, False,
                                         **lookup)
        etags[item['_etag']] = etag
    if etags:
        g.replace_etags = etags


def pre_service_patch(updates, original):
    """
    Hook before updating a service element.

    When updating a service, if only the live state is updated, do not change the
    _updated field and compute the new service overall state..

    Compute the service overall state identifier, including:
    - the acknowledged state
    - the downtime state

    The worst state is (prioritized):
    - a service critical or unreachable (4)
    - a service warning or unknown (3)
    - a service downtimed (2)
    - a service acknowledged (1)
    - a service ok (0)

    *Note* that services in unknown state are considered as warning, and unreachable ones
    are considered as critical!

    The _updated field is used by the Alignak arbiter to reload the configuration and we need to
    avoid reloading when the live state is updated.

    :param updates: list of host fields to update
    :type updates: dict
    :param original: list of original fields
    :type original: dict
    :return: None
    """
    # Allow update because it must be done when inserting a service
    # if '_overall_state_id' in updates:
    #     abort(make_response("Updating _overall_state_id for a service is forbidden", 412))

    for key in updates:
        if key not in ['_overall_state_id', '_updated', '_realm'] and not key.startswith('ls_'):
            break
    else:
        # pylint: disable=too-many-boolean-expressions
        if 'ls_state_type' in updates and updates['ls_state_type'] == 'HARD':
            # We updated the service live state, compute the new overall state
            if 'ls_state' in updates or 'ls_acknowledged' in updates or 'ls_downtimed' in updates:
                overall_state = 0

                acknowledged = original['ls_acknowledged']
                if 'ls_acknowledged' in updates:
                    acknowledged = updates['ls_acknowledged']

                downtimed = original['ls_downtimed']
                if 'ls_downtimed' in updates:
                    downtimed = updates['ls_downtimed']

                state = original['ls_state']
                if 'ls_state' in updates:
                    state = updates['ls_state']
                state = state.upper()

                if acknowledged:
                    overall_state = 1
                elif downtimed:
                    overall_state = 2
                else:
                    if state == 'WARNING':
                        overall_state = 3
                    elif state == 'CRITICAL':
                        overall_state = 4
                    elif state == 'UNKNOWN':
                        overall_state = 3
                    elif state == 'UNREACHABLE':
                        overall_state = 4

                updates['_overall_state_id'] = overall_state

        # Only updated some live state fields, do not change _updated field
        del updates['_updated']


def after_insert_service(items):
    """
    Hook after service inserted.

    :param items: host fields
    :type items: dict
    :return: None
    """
    etags = {}
    for dummy, item in enumerate(items):
        overall_state = 0

        acknowledged = item['ls_acknowledged']
        downtimed = item['ls_downtimed']
        state = item['ls_state']
        state = state.upper()

        if acknowledged:
            overall_state = 1
        elif downtimed:
            overall_state = 2
        else:
            if state == 'WARNING':
                overall_state = 3
            elif state == 'CRITICAL':
                overall_state = 4
            elif state == 'UNKNOWN':
                overall_state = 3
            elif state == 'UNREACHABLE':
                overall_state = 4

        # Service overall was computed, update the service overall state
        lookup = {"_id": item['_id']}
        (_, _, etag, _) = patch_internal('service', {"_overall_state_id": overall_state}, False,
                                         False, **lookup)
        etags[item['_etag']] = etag
    if etags:
        g.replace_etags = etags


def update_etag(myrequest, payload):
    """In case POST item database hook use patch_internal, we update the new _etag in the
    response

    :param myrequest:
    :param payload:
    :return: None
    """
    # pylint: disable=unused-argument
    if not g.get('replace_etags', {}):
        return
    else:
        for idx, resp in enumerate(payload.response):
            resp = resp.decode('UTF-8')
            for old_etag, new_etag in iteritems(g.replace_etags):
                resp = resp.replace(old_etag, new_etag)
            payload.response[idx] = resp
        del g.replace_etags


def after_updated_service(updated, original):
    """
    Hook called after a service got updated

    :param updated: updated fields
    :type updated: dict
    :param original: original fields
    :type original: dict
    :return: None
    """
    if '_overall_state_id' in updated:
        # Service overall was updated, we should update its host overall state
        lookup = {"_id": original['host']}
        patch_internal('host', {"_overall_state_id": -1}, False, False, **lookup)


# Users
def pre_user_post(items):
    """
    Hook before insert.
    When add user, hash the backend password of the user and generate a token
    If no host/service notification periods are provided, use the default 'Never' TP

    :param items: list of items (list because can use bulk)
    :type items: list
    :return: None
    """
    for key, item in enumerate(items):
        if 'password' in item:
            items[key]['password'] = generate_password_hash(item['password'])
        if 'token' in item:
            items[key]['token'] = generate_token()


def pre_user_patch(updates, original):
    """
    Hook before update.

    When updating user:
    - hash the backend password of the user if one tries to change it
    - generate the user token if a token (even empty) is provided

    If only the user preferences are updated do not change the _updated field (see comment in the
    pre_host_patch).

    :param updates: list of user fields to update
    :type updates: dict
    :param original: list of original fields
    :type original: dict
    :return: None
    """
    # pylint: disable=unused-argument
    if 'password' in updates:
        updates['password'] = generate_password_hash(updates['password'])
    if 'token' in updates:
        updates['token'] = generate_token()
    # Special case, we don't want update _updated field when update ui_preferences field
    if len(updates) == 2 and 'ui_preferences' in updates:
        del updates['_updated']


def after_insert_user(items):
    """
    Hook after a user was inserted.

    :param items: user fields
    :type items: dict
    :return: None
    """
    for dummy, item in enumerate(items):
        if 'back_role_super_admin' in item and item['back_role_super_admin']:
            # Allow full rights for the user on its realm
            post_internal("userrestrictrole", {
                "user": item['_id'],
                "realm": item['_realm'],
                "sub_realm": item['_sub_realm'],
                "resource": '*',
                "crud": ['create', 'read', 'update', 'delete']
            }, True)
        else:
            # Allow read right for the user on its realm
            post_internal("userrestrictrole", {
                "user": item['_id'],
                "realm": item['_realm'],
                "sub_realm": item['_sub_realm'],
                "resource": '*',
                "crud": ['read']
            }, True)


def pre_service_post(items):
    """Check before add service.
    We deny in case try add a service (not template) on a template host

    :param items: list of items (list because can use bulk)
    :type items: list
    :return: None
    """
    hostdb = current_app.data.driver.db['host']
    for key, _ in enumerate(items):
        # return error if try add service (not template) on host template
        if '_is_template' not in items[key] or not items[key]['_is_template']:
            the_host = hostdb.find_one({'_id': ObjectId(items[key]['host'])})
            if the_host['_is_template']:
                abort(make_response("Add a non template service on a template host is forbidden",
                                    412))


def keep_default_items_resource(resource, delete_request, lookup):
    """
    Keep default items, so do not delete them...

    :return: None
    """
    # pylint: disable=unused-argument
    if '_id' not in lookup:
        if resource == 'timeperiod':
            lookup['name'] = {'$nin': ['24x7', 'Never']}
        elif resource in ['realm', 'usergroup', 'hostgroup', 'servicegroup', ]:
            lookup['name'] = {'$nin': ['All']}
        elif resource == 'command':
            lookup['name'] = {'$nin': ['_internal_host_up', '_echo']}
        elif resource == 'host':
            lookup['name'] = {'$nin': ['_dummy']}
        elif resource == 'user':
            lookup['name'] = {'$nin': ['admin']}


def keep_default_items_item(resource, item):
    """
    Before deleting an item, we check if it's a default item, if yes return 412 error, otherwise
    Eve delete it

    :param resource: name of the resource
    :type resource: str
    :param item: all fields / values of the item to delete
    :type item: dict
    :return:
    """
    if resource == 'timeperiod':
        if item['name'] in ['24x7', 'Never']:
            abort(make_response("This item is a default item and is protected", 412))
    elif resource in ['realm', 'usergroup', 'hostgroup', 'servicegroup', ]:
        if item['name'] == 'All':
            abort(make_response("This item is a default item and is protected", 412))
    elif resource == 'command':
        if item['name'] in ['_internal_host_up', '_echo']:
            abort(make_response("This item is a default item and is protected", 412))
    elif resource == 'host':
        if item['name'] == '_dummy':
            abort(make_response("This item is a default item and is protected", 412))
    elif resource == 'user':
        if item['name'] == 'admin':
            abort(make_response("This item is a default item and is protected", 412))


def on_fetched_resource_tree(resource_name, response):
    """
    Update _parent and _tree_parents of tree resources when have restricted rights.
    Here we have the answer when get all items of a resource

    :param resource_name: name of the resource
    :type resource_name: string
    :param response: response of the get
    :type response: dict
    :return: None
    """
    if resource_name not in ['realm', 'usergroup', 'hostgroup', 'servicegroup']:
        return
    if g.get('back_role_super_admin', False):
        return
    for resp in response['_items']:
        on_fetched_item_tree(resource_name, resp)


def on_fetched_item_tree(resource_name, itemresp):
    """
    Update _parent and _tree_parents of tree resources when have restricted rights.
    Here we have the answer when get an item of a resource

    :param resource_name: name of the resource
    :type resource_name: string
    :param itemresp: response of the get
    :type itemresp: dict
    :return: None
    """
    if resource_name not in ['realm', 'usergroup', 'hostgroup', 'servicegroup']:
        return
    if g.get('back_role_super_admin', False):
        return
    resources_get = g.get('resources_get', {})
    # check _parent
    if not itemresp['_parent'] in resources_get['realm']:
        itemresp['_parent'] = None
    # check _tree_parents
    for realm_id in itemresp['_tree_parents']:
        if realm_id not in resources_get['realm']:
            itemresp['_tree_parents'].remove(realm_id)


def generate_token():
    """
    Generate a user token

    :return: user token
    """
    t = int(time.time() * 1000)
    return str(t) + '-' + str(uuid.uuid4())


# Backend configuration
def get_settings(prev_settings):
    """
    Get settings of application from config file to update/complete previously existing settings

    :param prev_settings: previous settings
    :type prev_settings: dict
    :return: None
    """
    settings_filenames = [
        '/usr/local/etc/alignak-backend/settings.json',
        '/etc/alignak-backend/settings.json',
        'etc/alignak-backend/settings.json',
        os.path.abspath('./etc/settings.json'),
        os.path.abspath('../etc/settings.json'),
        os.path.abspath('./settings.json')
    ]

    # Configuration file name in environment
    if os.environ.get('ALIGNAK_BACKEND_CONFIGURATION_FILE'):
        settings_filenames = [os.environ.get('ALIGNAK_BACKEND_CONFIGURATION_FILE')]

    comment_re = re.compile(
        r'(^)?[^\S\n]*/(?:\*(.*?)\*/[^\S\n]*|/[^\n]*)($)?',
        re.DOTALL | re.MULTILINE
    )
    for filename in settings_filenames:
        if os.path.isfile(filename):
            with open(filename) as stream:
                content = ''.join(stream.readlines())
                # Looking for comments
                match = comment_re.search(content)
                while match:
                    # single line comment
                    content = content[:match.start()] + content[match.end():]
                    match = comment_re.search(content)

                conf = json.loads(content)
                for key, value in iteritems(conf):
                    if key.startswith('RATE_LIMIT_') and value is not None:
                        prev_settings[key] = tuple(value)
                    else:
                        prev_settings[key] = value
                print("Using settings file: %s" % filename)
                return


print("--------------------------------------------------------------------------------")
print("%s, version %s" % (manifest['name'], manifest['version']))
print("Copyright %s" % manifest['copyright'])
print("License %s" % manifest['license'])
print("--------------------------------------------------------------------------------")

print("Doc: %s" % manifest['doc'])
print("Release notes: %s" % manifest['release'])
print("--------------------------------------------------------------------------------")

# Application configuration
settings = {}
settings['X_DOMAINS'] = '*'
settings['X_HEADERS'] = (
    'Authorization, If-Match,'
    ' X-HTTP-Method-Override, Content-Type, Cache-Control, Pragma'
)
settings['PAGINATION_LIMIT'] = 50
settings['PAGINATION_DEFAULT'] = 25
settings['AUTH_FIELD'] = None

settings['MONGO_HOST'] = 'localhost'
settings['MONGO_PORT'] = 27017
settings['MONGO_DBNAME'] = 'alignak-backend'

settings['RESOURCE_METHODS'] = ['GET', 'POST', 'DELETE']
settings['ITEM_METHODS'] = ['GET', 'PATCH', 'DELETE']
settings['XML'] = False
# Allow $regex in filtering ...
# Default is ['$where', '$regex']
settings['MONGO_QUERY_BLACKLIST'] = ['$where']

# Flask specific options; default is to listen only on locahost ...
settings['HOST'] = '127.0.0.1'
settings['PORT'] = 5000
settings['SERVER_NAME'] = None
settings['DEBUG'] = False

settings['SCHEDULER_TIMESERIES_ACTIVE'] = False
settings['SCHEDULER_GRAFANA_ACTIVE'] = False
settings['SCHEDULER_LIVESYNTHESIS_HISTORY'] = 0
settings['SCHEDULER_TIMEZONE'] = 'Etc/GMT'
settings['JOBS'] = []

# Read configuration file to update/complete the configuration
get_settings(settings)

if os.environ.get('ALIGNAK_BACKEND_MONGO_DBNAME'):
    settings['MONGO_DBNAME'] = os.environ.get('ALIGNAK_BACKEND_MONGO_DBNAME')

# scheduler config
jobs = []

if settings['SCHEDULER_TIMESERIES_ACTIVE']:
    jobs.append(
        {
            'id': 'cron_cache',
            'func': 'alignak_backend.scheduler:cron_cache',
            'args': (),
            'trigger': 'interval',
            'seconds': 10
        }
    )
if settings['SCHEDULER_GRAFANA_ACTIVE']:
    jobs.append(
        {
            'id': 'cron_grafana',
            'func': 'alignak_backend.scheduler:cron_grafana',
            'args': (),
            'trigger': 'interval',
            'seconds': 120
        }
    )
if settings['SCHEDULER_LIVESYNTHESIS_HISTORY'] > 0:
    jobs.append(
        {
            'id': 'cron_livesynthesis_history',
            'func': 'alignak_backend.scheduler:cron_livesynthesis_history',
            'args': (),
            'trigger': 'interval',
            'seconds': 60
        }
    )

if jobs:
    settings['JOBS'] = jobs

print("Application settings: %s" % settings)

# Add model schema to the configuration
settings['DOMAIN'] = register_models()

base_path = os.path.dirname(os.path.abspath(alignak_backend.__file__))

app = Eve(
    settings=settings,
    validator=MyValidator,
    auth=MyTokenAuth,
    static_folder=base_path
)
# hooks pre-init
app.on_pre_GET += pre_get
app.on_pre_POST += pre_post
app.on_pre_PATCH += pre_patch
app.on_pre_DELETE += pre_delete
app.on_insert_user += pre_user_post
app.on_update_user += pre_user_patch
app.on_inserted_user += after_insert_user
app.on_inserted_host += after_insert_host
app.on_post_POST_host += update_etag
app.on_inserted_service += after_insert_service
app.on_post_POST_service += update_etag
app.on_update_host += pre_host_patch
app.on_update_service += pre_service_patch
app.on_updated_service += after_updated_service
app.on_delete_item_host += pre_delete_host
app.on_deleted_item_host += after_delete_host
app.on_delete_item_realm += pre_delete_realm
app.on_deleted_item_realm += after_delete_realm
app.on_deleted_resource_realm += after_delete_resource_realm
app.on_update_realm += pre_realm_patch
app.on_update_usergroup += pre_usergroup_patch
app.on_update_hostgroup += pre_hostgroup_patch
app.on_update_servicegroup += pre_servicegroup_patch
app.on_insert_graphite += pre_timeseries_post
app.on_insert_influxdb += pre_timeseries_post
app.on_update_alignak += pre_alignak_patch
# check right on submit actions
app.on_pre_POST_actionacknowledge += pre_post_action_right
app.on_pre_POST_actiondowntime += pre_post_action_right
app.on_pre_POST_actionforcecheck += pre_post_action_right
app.on_pre_PATCH_actionacknowledge += pre_submit_action_right
app.on_pre_PATCH_actiondowntime += pre_submit_action_right
app.on_pre_PATCH_actionforcecheck += pre_submit_action_right
app.on_pre_DELETE_actionacknowledge += pre_submit_action_right
app.on_pre_DELETE_actiondowntime += pre_submit_action_right
app.on_pre_DELETE_actionforcecheck += pre_submit_action_right

# docs api
Bootstrap(app)
app.register_blueprint(swagger)
app.config['SWAGGER_INFO'] = {
    'title': manifest['name'],
    'version': manifest['version'],
    'description': manifest['description'],
    'contact': {
        'name': manifest['author']
    },
    'license': {
        'name': manifest['license']
    }
}
app.config['ENABLE_HOOK_DESCRIPTION'] = True

# Create default backend elements
with app.test_request_context():
    # Create default realm if not defined
    realms = app.data.driver.db['realm']
    default_realm = realms.find_one({'name': 'All'})
    if not default_realm:
        post_internal("realm", {"name": "All", "_parent": None, "_level": 0, 'default': True},
                      True)
        default_realm = realms.find_one({'name': 'All'})
        print("Created top level realm: %s" % default_realm)
    # Create default usergroup if not defined
    ugs = app.data.driver.db['usergroup']
    default_ug = ugs.find_one({'name': 'All'})
    if not default_ug:
        post_internal("usergroup", {
            "name": "All", "alias": "All users", "_parent": None, "_level": 0,
            "_realm": default_realm['_id'], "_sub_realm": True
        }, True)
        default_ug = ugs.find_one({'name': 'All'})
        print("Created top level usergroup: %s" % default_ug)
    # Create default hostgroup if not defined
    hgs = app.data.driver.db['hostgroup']
    default_hg = hgs.find_one({'name': 'All'})
    if not default_hg:
        post_internal("hostgroup", {
            "name": "All", "alias": "All hosts", "_parent": None, "_level": 0,
            "_realm": default_realm['_id'], "_sub_realm": True
        }, True)
        default_hg = hgs.find_one({'name': 'All'})
        print("Created top level hostgroup: %s" % default_hg)
    # Create default servicegroup if not defined
    sgs = app.data.driver.db['servicegroup']
    default_sg = sgs.find_one({'name': 'All'})
    if not default_sg:
        post_internal("servicegroup", {
            "name": "All", "alias": "All services", "_parent": None, "_level": 0,
            "_realm": default_realm['_id'], "_sub_realm": True
        }, True)
        default_sg = sgs.find_one({'name': 'All'})
        print("Created top level servicegroup: %s" % default_sg)
    # Create default timeperiods if not defined
    timeperiods = app.data.driver.db['timeperiod']
    always = timeperiods.find_one({'name': '24x7'})
    if not always:
        post_internal("timeperiod", {"name": "24x7",
                                     "alias": "All time default 24x7",
                                     "_realm": default_realm['_id'], "_sub_realm": True,
                                     "is_active": True,
                                     "dateranges": [{u'monday': u'00:00-24:00'},
                                                    {u'tuesday': u'00:00-24:00'},
                                                    {u'wednesday': u'00:00-24:00'},
                                                    {u'thursday': u'00:00-24:00'},
                                                    {u'friday': u'00:00-24:00'},
                                                    {u'saturday': u'00:00-24:00'},
                                                    {u'sunday': u'00:00-24:00'}]}, True)
        always = timeperiods.find_one({'name': '24x7'})
        print("Created default Always timeperiod: %s" % always)
    never = timeperiods.find_one({'name': 'Never'})
    if not never:
        post_internal("timeperiod", {"name": "Never",
                                     "alias": "No time is a good time",
                                     "_realm": default_realm['_id'], "_sub_realm": True,
                                     "is_active": True}, True)
        never = timeperiods.find_one({'name': 'Never'})
        print("Created default Never timeperiod: %s" % never)

    # Create default commands if not defined
    commands = app.data.driver.db['command']
    internal_host_up_command = commands.find_one({'name': '_internal_host_up'})
    if not internal_host_up_command:
        post_internal("command", {
            "name": "_internal_host_up",
            "alias": "Host/service is always UP/OK",
            "command_line": "_internal_host_up",
            "_realm": default_realm['_id'],
            "_sub_realm": True
        }, True)
        internal_host_up_command = commands.find_one({'name': '_internal_host_up'})
        print("Created default Always UP command: %s" % internal_host_up_command)
    echo_command = commands.find_one({'name': '_echo'})
    if not echo_command:
        post_internal("command", {
            "name": "_echo",
            "alias": "Host/service is always UP/OK",
            "command_line": "_echo",
            "_realm": default_realm['_id'],
            "_sub_realm": True
        }, True)
        echo_command = commands.find_one({'name': '_echo'})
        print("Created default Echo command: %s" % echo_command)

    # Create dummy host if not defined
    hs = app.data.driver.db['host']
    dummy_host = hs.find_one({'name': '_dummy'})
    if not dummy_host:
        post_internal("host", {
            "name": "_dummy",
            "alias": "Dummy host for services templates",
            "check_command": internal_host_up_command['_id'],
            "_realm": default_realm['_id'],
            "_is_template": True,
            '_templates_with_services': False,
            "_sub_realm": True
        }, True)
        dummy_host = hs.find_one({'name': '_dummy'})
        print("Created dummy host: %s" % dummy_host)

    # Create default username/user if not defined
    try:
        users = app.data.driver.db['user']
    except Exception as e:
        sys.exit("[ERROR] Impossible to connect to MongoDB (%s)" % e)
    super_admin_user = users.find_one({'back_role_super_admin': True})
    if not super_admin_user:
        post_internal("user", {"name": "admin", "alias": "Administrator",
                               "password": "admin",
                               "back_role_super_admin": True,
                               "is_admin": True,
                               "can_update_livestate": True,
                               "can_submit_commands": True,
                               "skill_level": 2,
                               "host_notifications_enabled": False,
                               "host_notification_period": always["_id"],
                               "service_notifications_enabled": False,
                               "service_notification_period": always["_id"],
                               "_realm": default_realm["_id"], "_sub_realm": True}, True)
        print("Created super admin user")
        print("===============================================================================")
        print(r"/!\ WARNING /!\ Change the default password according to the documentation: "
              "http://alignak-backend.readthedocs.io/en/latest/run.html#change-default-"
              "admin-password")
        print("===============================================================================")

    # Live synthesis management
    app.on_inserted_host += Livesynthesis.on_inserted_host
    app.on_inserted_service += Livesynthesis.on_inserted_service
    app.on_updated_host += Livesynthesis.on_updated_host
    app.on_updated_service += Livesynthesis.on_updated_service
    app.on_deleted_item_host += Livesynthesis.on_deleted_item_host
    app.on_deleted_item_service += Livesynthesis.on_deleted_item_service
    app.on_deleted_resource_host += Livesynthesis.on_deleted_resource_host
    app.on_deleted_resource_host += Livesynthesis.on_deleted_resource_service
    app.on_fetched_item_livesynthesis += Livesynthesis.on_fetched_item_history

    # Templates management
    app.on_pre_POST_host += Template.pre_post_host
    app.on_update_host += Template.on_update_host
    app.on_updated_host += Template.on_updated_host

    app.on_inserted_host += Template.on_inserted_host
    app.on_inserted_service += Template.on_inserted_service
    app.on_deleted_item_service += Template.on_deleted_item_service

    app.on_pre_POST_service += Template.pre_post_service
    app.on_update_service += Template.on_update_service
    app.on_updated_service += Template.on_updated_service

    app.on_pre_POST_user += Template.pre_post_user
    app.on_update_user += Template.on_update_user
    app.on_updated_user += Template.on_updated_user

    # Initial livesynthesis
    Livesynthesis.recalculate()

# hooks post-init
app.on_insert_realm += pre_realm_post
app.on_inserted_realm += after_insert_realm
app.on_updated_realm += after_update_realm

app.on_insert_usergroup += pre_usergroup_post
app.on_insert_hostgroup += pre_hostgroup_post
app.on_insert_servicegroup += pre_servicegroup_post

app.on_insert_actionacknowledge += pre_actionacknowledge_post
app.on_inserted_actionacknowledge += after_insert_actionacknowledge
app.on_updated_actionacknowledge += after_update_actionacknowledge

app.on_insert_actiondowntime += pre_actiondowntime_post
app.on_inserted_actiondowntime += after_insert_actiondowntime
app.on_updated_actiondowntime += after_update_actiondowntime

app.on_insert_actionforcecheck += pre_actionforcecheck_post
app.on_inserted_actionforcecheck += after_insert_actionforcecheck
app.on_updated_actionforcecheck += after_update_actionforcecheck

app.on_insert_history += pre_history_post

app.on_insert_hostescalation += pre_hostescalation_post
app.on_insert_serviceescalation += pre_serviceescalation_post

app.on_insert_logcheckresult += pre_logcheckresult_post
app.on_inserted_logcheckresult += after_insert_logcheckresult

app.on_pre_DELETE += keep_default_items_resource
app.on_delete_item += keep_default_items_item

app.on_insert_service += pre_service_post

# hook for tree resources
app.on_fetched_resource += on_fetched_resource_tree
app.on_fetched_item += on_fetched_item_tree

with app.test_request_context():
    app.on_inserted_logcheckresult += Timeseries.after_inserted_logcheckresult

# Start scheduler (internal cron)
if settings['JOBS']:
    with app.test_request_context():
        scheduler = APScheduler()
        scheduler.init_app(app)
        scheduler.start()


@app.route("/login", methods=['POST'])
def login_app():
    """
    Log in to backend
    """
    posted_data = None
    if request.form:
        posted_data = request.form
    else:
        if request.json:
            posted_data = request.json
    if not posted_data:
        abort(401, description='No data provided in the login request')

    if 'username' not in posted_data or 'password' not in posted_data:
        abort(
            401,
            description='Missing credentials in posted data (username and password are mandatory)'
        )
    elif not posted_data['username'] or not posted_data['password']:
        abort(
            401,
            description='Username and password must be provided as credentials for login.'
        )
    else:
        _users = app.data.driver.db['user']
        user = _users.find_one({'name': posted_data['username']})
        if user:
            if check_password_hash(user['password'], posted_data['password']):
                if 'action' in posted_data:
                    if posted_data['action'] == 'generate' or not user['token']:
                        token = generate_token()
                        _users.update({'_id': user['_id']}, {'$set': {'token': token}})
                        return jsonify({'token': token})
                elif not user['token']:
                    token = generate_token()
                    _users.update({'_id': user['_id']}, {'$set': {'token': token}})
                    return jsonify({'token': token})
                return jsonify({'token': user['token']})
        abort(401, description='Please provide proper credentials')


@app.route("/logout", methods=['POST'])
def logout_app():
    """
    Log out from backend
    """
    return 'ok'


@app.route("/backendconfig")
def backend_config():
    """
    Offer route to get the backend config
    """
    my_config = {"PAGINATION_LIMIT": settings['PAGINATION_LIMIT'],
                 "PAGINATION_DEFAULT": settings['PAGINATION_DEFAULT']}
    return jsonify(my_config)


@app.route("/cron_timeseries")
def cron_timeseries():
    """
    Cron used to add perfdata from retention to timeseries databases

    :return: None
    """
    with app.test_request_context():
        timeseriesretention_db = current_app.data.driver.db['timeseriesretention']
        graphite_db = current_app.data.driver.db['graphite']
        influxdb_db = current_app.data.driver.db['influxdb']
        if timeseriesretention_db.find().count() > 0:
            tsc = timeseriesretention_db.find({'graphite': {'$ne': None}})
            for data in tsc:
                graphite = graphite_db.find_one({'_id': data['graphite']})
                if not Timeseries.send_to_timeseries_graphite([data], graphite):
                    break
                lookup = {"_id": data['_id']}
                deleteitem_internal('timeseriesretention', False, False, **lookup)

            tsc = timeseriesretention_db.find({'influxdb': {'$ne': None}})
            for data in tsc:
                influxdb = influxdb_db.find_one({'_id': data['influxdb']})
                if not Timeseries.send_to_timeseries_influxdb([data], influxdb):
                    break
                lookup = {"_id": data['_id']}
                deleteitem_internal('timeseriesretention', False, False, **lookup)


@app.route("/cron_grafana", methods=['GET'])
def cron_grafana(engine='jsonify'):
    """
    Cron used to add / update grafana dashboards

    :return: Number of dashboard created
    :rtype: dict
    """
    # pylint: disable=too-many-nested-blocks
    # pylint: disable=too-many-locals
    try:
        forcegenerate = request.args.get('forcegenerate')
        if request.remote_addr not in settings['IP_CRON']:
            print('Access denied for %s' % request.remote_addr)
            return make_response("Access denied from remote host", 412)
    except Exception:
        forcegenerate = None

    with app.test_request_context():
        resp = {}
        hosts_db = current_app.data.driver.db['host']
        services_db = current_app.data.driver.db['service']
        grafana_db = current_app.data.driver.db['grafana']

        for grafana in grafana_db.find():
            # Create a grafana instance
            graf = Grafana(grafana)
            resp[grafana['name']] = {
                "connection": graf.connection,
                "created_dashboards": []
            }
            if not graf.connection:
                print("[cron_grafana] %s has no connection" % grafana['name'])
                continue

            print("[cron_grafana] Grafana: %s" % grafana['name'])

            search = {'_is_template': False}
            search['_realm'] = {"$in": graf.realms}
            if len(graf.realms) == 1:
                search['_realm'] = graf.realms[0]

            if forcegenerate is not None:
                print("[cron_grafana] Force regeneration of '%s' dashboards" % grafana['name'])
            else:
                search['ls_grafana'] = False
                search['ls_perf_data'] = {"$ne": ""}
                search['ls_last_check'] = {"$ne": 0}

            hosts = hosts_db.find(search)
            for host in hosts:
                print("[cron_grafana] host: %s" % host['name'])

                # if this host do not have a TS datasource (influxdb, graphite) for grafana,
                # do not try to create a dashboard (test before trying to create...)
                if host['_realm'] not in graf.timeseries:
                    print("[cron_grafana] Host '%s' is not in a timeseries enabled realm"
                          % host['name'])
                    print("[cron_grafana] - host realm: %s" % host['_realm'])
                    print("[cron_grafana] - Grafana TS realms: %s" % graf.timeseries)
                    continue

                created = graf.create_dashboard(host)
                if created:
                    print("[cron_grafana] created a dashboard for '%s'..." % host['name'])
                    if host['name'] not in resp[grafana['name']]['created_dashboards']:
                        resp[grafana['name']]['created_dashboards'].append(host['name'])
                else:
                    print("[cron_grafana] dashboard creation failed for '%s'..." % host['name'])

            if forcegenerate is not None:
                continue

            # manage the cases hosts have new services or hosts that do not have ls_perf_data
            hosts_dashboards = {}
            search = {'ls_grafana': False, '_is_template': False,
                      'ls_perf_data': {"$ne": ""}, 'ls_last_check': {"$ne": 0},
                      '_realm': {"$in": graf.realms}}
            if len(graf.realms) == 1:
                search['_realm'] = graf.realms[0]

            services = services_db.find(search)
            for service in services:
                if service['host'] in hosts_dashboards:
                    continue

                host = hosts_db.find_one({'_id': service['host']})
                if host['_is_template']:
                    continue

                created = graf.create_dashboard(host)
                if created:
                    print("[cron_grafana] created a dashboard for '%s/%s'"
                          % (host['name'], service['name']))
                    resp[grafana['name']]['created_dashboards'].append("%s/%s"
                                                                       % (host['name'],
                                                                          service['name']))
                else:
                    print("[cron_grafana] dashboard creation failed for '%s/%s'"
                          % (host['name'], service['name']))
                hosts_dashboards[service['host']] = True

        if engine == 'jsonify':
            return jsonify(resp)

        return json.dumps(resp)


@app.route('/cron_livesynthesis_history')
def cron_livesynthesis_history():
    """
    Cron used to generate new history line for livesynthesis (+ delete too old entries)

    :return: empty dictionary
    :rtype: dict
    """
    minutes = settings['SCHEDULER_LIVESYNTHESIS_HISTORY']
    with app.test_request_context():
        # for each livesynthesis, add into internal livesynthesisretention endpoint
        livesynthesis_db = current_app.data.driver.db['livesynthesis']
        livesynthesisretention_db = current_app.data.driver.db['livesynthesisretention']
        livesynthesis = livesynthesis_db.find()
        for livesynth in livesynthesis:
            livesynth['livesynthesis'] = livesynth['_id']
            for prop in ['_id', '_created', '_updated', '_realm', '_users_read']:
                if prop in livesynth:
                    del livesynth[prop]
            post_internal("livesynthesisretention", livesynth, True)
            # delete older data
            if minutes > 0:
                items = livesynthesisretention_db.find(
                    {"_created": {"$lt": (datetime.utcnow() - timedelta(seconds=60 * minutes))}})
                for item in items:
                    lookup = {"_id": item['_id']}
                    deleteitem_internal('livesynthesisretention', False, False, **lookup)
        return jsonify({})


@app.route('/docs')
def redir_index():
    """
    Redirect /docs to /docs/index.html

    :return: redirect to endpoint /docs/index.html
    """
    return redirect('/docs/index.html')


@app.route('/docs/<path:path>')
def index(path):
    """
    Deliver static files of swagger-ui folder

    :param path: path + files of swagger-ui to load
    :type path: string
    :return:
    """
    return send_from_directory(base_path, 'swagger-ui/' + path)


def main():
    """Called when this module is started from Python shell"""
    print("--------------------------------------------------------------------------------")
    print("Running `python app.py` is no more supported. Use 'alignak-backend' shell script.")
    print("--------------------------------------------------------------------------------")
    sys.exit(1)

if __name__ == "__main__":
    main()
