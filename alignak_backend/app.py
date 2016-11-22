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
import traceback
import uuid
from collections import OrderedDict

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
from future.utils import iteritems
from werkzeug.security import check_password_hash, generate_password_hash

import alignak_backend.log
from alignak_backend import manifest
from alignak_backend.grafana import Grafana
from alignak_backend.livesynthesis import Livesynthesis
from alignak_backend.models import register_models
from alignak_backend.template import Template
from alignak_backend.timeseries import Timeseries

_subcommands = OrderedDict()


def register_command(description):
    """Register commands usable from command line"""
    def decorate(f):
        """Create decorator to be used for functions"""
        _subcommands[f.__name__] = (description, f)
        return f
    return decorate


class MyTokenAuth(TokenAuth):
    """
    Class to manage authentication
    """
    children_realms = {}
    parent_realms = {}

    """Authentication token class"""
    def check_auth(self, token, allowed_roles, resource, method):
        """
        Check if account exist and get roles for this user

        :param token: token for auth
        :type username: str
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
            # get children of realms for rights
            realmsdrv = current_app.data.driver.db['realm']
            allrealms = realmsdrv.find()
            self.children_realms = {}
            self.parent_realms = {}
            for realm in allrealms:
                self.children_realms[realm['_id']] = realm['_all_children']
                self.parent_realms[realm['_id']] = realm['_tree_parents']

            g.back_role_super_admin = user['back_role_super_admin']
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
                # print("User role: %s" % rights)
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
            # print("Read allowed: %s" % g.resources_get)
            for resource in g.resources_get:
                g.resources_get[resource] = list(set(g.resources_get[resource]))
                if resource in g.resources_get_custom:
                    g.resources_get_custom[resource] = list(set(g.resources_get_custom[resource]))
                g.resources_get_parents[resource] = [item for item in get_parents[resource]
                                                     if item not in g.resources_get[resource]]
            for resource in g.resources_post:
                g.resources_post[resource] = list(set(g.resources_post[resource]))
            for resource in g.resources_patch:
                g.resources_patch[resource] = list(set(g.resources_patch[resource]))
            for resource in g.resources_delete:
                g.resources_delete[resource] = list(set(g.resources_delete[resource]))
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
        :type resource_list: dict
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
    def _validate_title(self, title, field, value):
        """Validate 'title' field (always valid)"""
        return


def pre_get(resource, user_request, lookup):
    """
    Hook before get data. Add filter depend on roles of user

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
    # Only in case not super-admin
    if resource not in ['user']:
        # get all resources we can have rights in read
        resources_get = g.get('resources_get', {})
        resources_get_parents = g.get('resources_get_parents', {})
        resources_get_custom = g.get('resources_get_custom', {})
        users_id = g.get('users_id', {})

        if resource not in resources_get and resource not in resources_get_custom:
            lookup["_id"] = 0
        else:
            if resource not in resources_get:
                resources_get[resource] = []
            if resource not in resources_get_parents:
                resources_get_parents[resource] = []
            if resource not in resources_get_custom:
                resources_get_custom[resource] = []
            lookup['$or'] = [{'_realm': {'$in': resources_get[resource]}},
                             {'$and': [{'_sub_realm': True},
                                       {'_realm': {'$in': resources_get_parents[resource]}}]},
                             {'$and': [{'_users_read': users_id},
                                       {'_realm': {'$in': resources_get_custom[resource]}}]}]


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
        data = {
            'host': item['host'],
            'host_name': item['host_name'],
            'service': item['service'],
            'service_name': item['service_name'],
            'user': None,
            'type': 'check.result',
            'message': '',
            'logcheckresult': item['_id']
        }
        post_internal("history", data, True)


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

    :param updates: modified fields
    :type updates: dict
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

    :param updates: modified fields
    :type updates: dict
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
        print("Created new history for forcecheck: %s" % data)


def after_update_actionforcecheck(updated, original):
    """
    Hook update on actionforcecheck

    :param updates: modified fields
    :type updates: dict
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
        print("Created new history for forcecheck: %s" % data)


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
        parent = hgs_drv.find_one({'_id': updates['_parent']})
        if not parent:
            abort(make_response("Error: parent not found: %s" % updates['_parent'], 412))

        updates['_level'] = parent['_level'] + 1
        updates['_tree_parents'] = original['_tree_parents']
        if original['_parent'] in original['_tree_parents']:
            updates['_tree_parents'].remove(original['_parent'])
        if updates['_parent'] not in original['_tree_parents']:
            updates['_tree_parents'].append(updates['_parent'])


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
        parent = sgs_drv.find_one({'_id': updates['_parent']})
        if not parent:
            abort(make_response("Error: parent not found: %s" % updates['_parent'], 412))

        updates['_level'] = parent['_level'] + 1
        updates['_tree_parents'] = original['_tree_parents']
        if original['_parent'] in original['_tree_parents']:
            updates['_tree_parents'].remove(original['_parent'])
        if updates['_parent'] not in original['_tree_parents']:
            updates['_tree_parents'].append(updates['_parent'])


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
        parent = ugs_drv.find_one({'_id': updates['_parent']})
        if not parent:
            abort(make_response("Error: parent not found: %s" % updates['_parent'], 412))

        updates['_level'] = parent['_level'] + 1
        updates['_tree_parents'] = original['_tree_parents']
        if original['_parent'] in original['_tree_parents']:
            updates['_tree_parents'].remove(original['_parent'])
        if updates['_parent'] not in original['_tree_parents']:
            updates['_tree_parents'].append(updates['_parent'])


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
        if len(original['_tree_parents']) > 0:
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

    :param updates: modified fields
    :type updates: dict
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
    if len(item['_children']) > 0:
        abort(409, description=debug_error_message("Item have children, so can't delete it"))


def after_delete_realm(item):
    """
    Hook after realm deletion. Update tree children of parent realm

    :param item: fields of the item / record
    :type item: dict
    :return: None
    """
    realmsdrv = current_app.data.driver.db['realm']
    if len(item['_tree_parents']) > 0:
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


# Hosts/ services
def pre_host_service_patch(updates, original):
    """
    Hook before update.
    When updating an host or service, if only the live state is updated, do not change the
    _updated field.

    The _updated field is used by the Alignak arbiter to reload the configuration and we need to
    avoid reloading when the live state is updated.

    :param updates: list of host fields to update
    :type updates: dict
    :param original: list of original fields
    :type original: dict
    :return: None
    """
    # pylint: disable=unused-argument

    for key in updates:
        if key not in ['_updated', '_realm'] and not key.startswith('ls_'):
            break
    else:
        # Only some live state fields, do not change _updated field
        del updates['_updated']


# Users
def pre_user_post(items):
    """
    Hook before insert.
    When add user, hash the backend password of the user

    :param items: list of items (list because can use bulk)
    :type items: list
    :return: None
    """
    for key, item in enumerate(items):
        if 'password' in item:
            items[key]['password'] = generate_password_hash(item['password'])


def pre_user_patch(updates, original):
    """
    Hook before update.

    When updating user, hash the backend password of the user if one try to change it
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
    # Special case, we don't want update _updated field when update ui_preferences field
    if len(updates) == 2 and 'ui_preferences' in updates:
        del updates['_updated']


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
        os.path.abspath('./etc/settings.json'),
        os.path.abspath('../etc/settings.json'),
        os.path.abspath('./settings.json')
    ]

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
    ' X-HTTP-Method-Override, Content-Type'
)
settings['PAGINATION_LIMIT'] = 50
settings['PAGINATION_DEFAULT'] = 25

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
settings['SCHEDULER_TIMEZONE'] = 'Etc/GMT'
settings['JOBS'] = []

settings['GRAPHITE_HOST'] = ''
settings['GRAPHITE_PORT'] = 8080
settings['CARBON_HOST'] = ''
settings['CARBON_PORT'] = 2004

settings['INFLUXDB_HOST'] = ''
settings['INFLUXDB_PORT'] = 8086
settings['INFLUXDB_LOGIN'] = 'root'
settings['INFLUXDB_PASSWORD'] = 'root'
settings['INFLUXDB_DATABASE'] = 'alignak'

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
if settings['SCHEDULER_GRAFANA_ACTIVE'] and settings['GRAFANA_HOST'] is not None:
    jobs.append(
        {
            'id': 'cron_grafana',
            'func': 'alignak_backend.scheduler:cron_grafana',
            'args': (),
            'trigger': 'interval',
            'seconds': 120
        }
    )
if len(jobs) > 0:
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
app.on_insert_user += pre_user_post
app.on_update_user += pre_user_patch
app.on_update_host += pre_host_service_patch
app.on_update_service += pre_host_service_patch
app.on_delete_item_realm += pre_delete_realm
app.on_deleted_item_realm += after_delete_realm
app.on_update_realm += pre_realm_patch
app.on_update_usergroup += pre_usergroup_patch
app.on_update_hostgroup += pre_hostgroup_patch
app.on_update_servicegroup += pre_servicegroup_patch

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
                               "can_update_livestate": True,
                               "host_notification_period": always['_id'],
                               "service_notification_period": always['_id'],
                               "_realm": default_realm['_id'], "_sub_realm": True})
        print("Created super admin user")

    # Live synthesis management
    app.on_inserted_host += Livesynthesis.on_inserted_host
    app.on_inserted_service += Livesynthesis.on_inserted_service
    app.on_updated_host += Livesynthesis.on_updated_host
    app.on_updated_service += Livesynthesis.on_updated_service

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

app.on_insert_logcheckresult += pre_logcheckresult_post
app.on_inserted_logcheckresult += after_insert_logcheckresult

with app.test_request_context():
    app.on_inserted_logcheckresult += Timeseries.after_inserted_logcheckresult

# Start scheduler (internal cron)
if len(settings['JOBS']) > 0:
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
                 "PAGINATION_DEFAULT": settings['PAGINATION_DEFAULT'],
                 'metrics': []}
    if settings['GRAPHITE_HOST'] is not None:
        my_config['metrics'].append('graphite')
    if settings['INFLUXDB_HOST'] is not None:
        my_config['metrics'].append('influxdb')
    if settings['GRAFANA_HOST'] is not None:
        my_config['GRAFANA_HOST'] = settings['GRAFANA_HOST']
        my_config['GRAFANA_PORT'] = settings['GRAFANA_PORT']
    return jsonify(my_config)


@app.route("/cron_timeseries")
def cron_timeseries():
    """
    Cron used to add perfdata from retention to timeseries databases

    :return: None
    """
    with app.test_request_context():
        timeseriesretention_db = current_app.data.driver.db['timeseriesretention']
        if timeseriesretention_db.find().count() > 0:
            tsc = timeseriesretention_db.find({'for_graphite': True, 'for_influxdb': False})
            for data in tsc:
                if not Timeseries.send_to_timeseries_graphite([data]):
                    break
                lookup = {"_id": data['_id']}
                deleteitem_internal('timeseriesretention', False, False, **lookup)
            tsc = timeseriesretention_db.find({'for_graphite': False, 'for_influxdb': True})
            for data in tsc:
                if not Timeseries.send_to_timeseries_influxdb([data]):
                    break
                lookup = {"_id": data['_id']}
                deleteitem_internal('timeseriesretention', False, False, **lookup)
            tsc = timeseriesretention_db.find({'for_graphite': True, 'for_influxdb': True})
            for data in tsc:
                graphite_serv = True
                influxdb_serv = True
                if not Timeseries.send_to_timeseries_graphite([data]):
                    graphite_serv = False
                if not Timeseries.send_to_timeseries_influxdb([data]):
                    influxdb_serv = False
                lookup = {"_id": data['_id']}
                if graphite_serv and influxdb_serv:
                    deleteitem_internal('timeseriesretention', False, False, **lookup)
                elif graphite_serv and not influxdb_serv:
                    patch_internal('timeseriesretention', {"for_graphite": False}, False, False,
                                   **lookup)
                elif influxdb_serv and not graphite_serv:
                    patch_internal('timeseriesretention', {"for_influxdb": False}, False, False,
                                   **lookup)


@app.route("/cron_grafana")
def cron_grafana():
    """
    Cron used to add / update grafana dashboards

    :return: None
    """
    with app.test_request_context():
        hosts_db = current_app.data.driver.db['host']
        grafana = Grafana()

        hosts = hosts_db.find({'ls_grafana': False})
        for host in hosts:
            if 'ls_perf_data' in host and host['ls_perf_data']:
                grafana.create_dashboard(host['_id'])


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
    """
        Called when this module is started from shell
    """
    try:
        print("--------------------------------------------------------------------------------")
        print("%s, listening on %s:%d" % (
            manifest['name'], app.config.get('HOST', '127.0.0.1'), app.config.get('PORT', 8090)
        ))
        print("--------------------------------------------------------------------------------")
        app.run(
            host=settings.get('HOST', '127.0.0.1'),
            port=settings.get('PORT', 5000),
            debug=settings.get('DEBUG', False)
        )
    except Exception as e:
        print("Application run failed, exception: %s / %s" % (type(e), str(e)))
        print("Back trace of this kill: %s" % traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
