#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    ``alignak_backend.template`` module

    This module manages the templates (host / services / users)
"""
from __future__ import print_function
from copy import deepcopy
from future.utils import iteritems
from flask import current_app, g, abort, make_response
from eve.methods.post import post_internal
from eve.methods.patch import patch_internal
from eve.methods.delete import deleteitem_internal
from bson.objectid import ObjectId
from alignak_backend.models.host import get_schema as host_schema
from alignak_backend.models.service import get_schema as service_schema
from alignak_backend.models.user import get_schema as user_schema


class Template(object):  # pylint: disable=too-many-public-methods
    """Template class    """

    @staticmethod
    def pre_post_host(user_request):
        """Called by EVE HOOK (app.on_pre_POST_host)

        If we use templates, we fill fields with template values

        :param user_request: request of the user
        :type user_request: object
        :return: None
        """
        if isinstance(user_request.json, dict):
            Template.fill_template_host(user_request.json)
        else:
            for i in user_request.json:
                Template.fill_template_host(i)

    @staticmethod
    def on_update_host(updates, original):
        """Called by EVE HOOK (app.on_update_host)

        On update host, if not template, remove in '_template_fields' fields in updates because
        we update these fields, so they are now not dependant of template

        :param updates: modified fields
        :type updates: dict
        :param original: original fields
        :type original: dict
        :return: None
        """
        if g.get('ignore_hook_patch', False):
            return
        if not original['_is_template']:
            # case the host is not a template
            template_fields = original['_template_fields']
            do_patch = False
            for (field_name, _) in iteritems(updates):
                if field_name in template_fields:
                    template_fields.remove(field_name)
                    do_patch = True
            if do_patch:
                lookup = {"_id": original['_id']}
                to_patch = {"_template_fields": template_fields}
                response = patch_internal('host', to_patch, False, False, **lookup)
                updates['_etag'] = response[0]['_etag']
                original['_etag'] = response[0]['_etag']

    @staticmethod
    def get_host_template_services(host, templates_with_services=True, templates=None):
        """Recursively get all the services from an host templates hierarchy

        First get the services from the host templates of the current host template. And then
        get the services of the current host template.

        :param host: a new host to create, whare to attache the found services
        :type host: host
        :param templates: list of templates to search services into
        :type host: host
        :param templates_with_services: create the services linked with the hosts templates
        :type templates_with_services: bool
        :param templates: list of templates
        :type templates: list
        :return: list of the services to create
        """
        services = {}
        host_drv = current_app.data.driver.db['host']
        service_srv = current_app.data.driver.db['service']

        for host_template_id in templates:
            host_tpl = host_drv.find_one({'_id': host_template_id})
            if host_tpl['_templates']:
                services.update(Template.get_host_template_services(host,
                                                                    templates_with_services,
                                                                    host_tpl['_templates']))

            if templates_with_services:
                my_template_services = service_srv.find({'_is_template': True,
                                                         'host': host_tpl['_id']})
                for srv in my_template_services:
                    services[srv['name']] = Template.prepare_service_to_post(srv, host)

        return services

    @staticmethod
    def on_updated_host(updates, original):
        """Called by EVE HOOK (app.on_updated_host)

        After host updated,
        if host is a template, report value of fields updated on host used this template
        if host is not template, add or remove services templates if _templates changed

        :param updates: modified fields
        :type updates: dict
        :param original: original fields
        :type original: dict
        :return: None
        """
        # pylint: disable=too-many-locals, too-many-nested-blocks
        if g.get('ignore_hook_patch', False):
            g.ignore_hook_patch = False
            return
        if original['_is_template']:
            # We must update all host using this template
            host_db = current_app.data.driver.db['host']
            hosts = host_db.find({'_templates': original['_id']})
            for host in hosts:
                Template.update_host_use_template(host, updates)
        else:
            if '_templates' in updates and updates['_templates'] != original['_templates']:
                if original['_templates_with_services']:
                    service_db = current_app.data.driver.db['service']

                    # Get all the real services of this host
                    myservices = service_db.find({'_is_template': False, 'host': original['_id']})
                    myservices_template_id = []
                    myservices_bis = {}
                    for myservice in myservices:
                        # Consider all the service templates... not only the first one!
                        for template_srv in myservice['_templates']:
                            myservices_template_id.append(template_srv)
                            myservices_bis[template_srv] = myservice

                    # Find services templates in the update
                    services = Template.get_host_template_services(original, True,
                                                                   updates['_templates'])
                    service_template_id = []
                    for service_name in services:
                        service = services[service_name]
                        for template_srv_id in service['_templates']:
                            service_template_id.append(template_srv_id)

                    # Compare servies to add/delete
                    services_to_add = list(set(service_template_id) - set(myservices_template_id))
                    services_to_del = list(set(myservices_template_id) - set(service_template_id))
                    for service_name in services:
                        service = services[service_name]
                        for template_srv_id in service['_templates']:
                            if template_srv_id in services_to_add:
                                post_internal('service', [service])
                    for template_id in services_to_del:
                        if template_id in myservices_bis:
                            lookup = {"_id": myservices_bis[template_id]['_id']}
                            deleteitem_internal('service', False, False, **lookup)

    @staticmethod
    def on_inserted_host(items):
        """Called by EVE HOOK (app.on_inserted_host)

        After host inserted, if it use a template (or templates) and the the host use template
        with services, we add templates services to this host

        :param items: list of hosts
        :type items: list
        :return: None
        """
        for _, item in enumerate(items):
            if not item['_is_template'] and item['_templates'] != [] \
                    and item['_templates_with_services']:

                # Recursively get the services from the host template
                services = Template.get_host_template_services(item,
                                                               item['_templates_with_services'],
                                                               item['_templates'])

                # when ok, and if some exist, add all services to this host
                template_services = [services[k] for k in services]
                if template_services:
                    post_internal('service', template_services)

    @staticmethod
    def on_inserted_service(items):
        """Called by EVE HOOK (app.on_inserted_service)

        After service inserted, if it is a template and the host linked is a template with services
        we add the service in all hosts having this host as template

        :param items: List of services
        :type items: list
        :return: None
        """
        host_db = current_app.data.driver.db['host']
        services = []
        for _, item in enumerate(items):
            if item['_templates_from_host_template'] and item['_is_template']:
                # case where this service is template host+service, so add this service on all
                # hosts
                # use the host template and have _templates_with_services=True
                hostid = item['host']
                hosts = host_db.find(
                    {'_templates': hostid, '_templates_with_services': True, '_is_template': False})
                for hs in hosts:
                    services.append(Template.prepare_service_to_post(deepcopy(item), hs))
        if services != []:
            post_internal('service', services)

    @staticmethod
    def on_deleted_item_service(item):
        """Called by EVE HOOK (app.on_deleted_item_service)

        After deleted a template service, we delete all services are linked to this template

        :param item: service dict
        :type item: dict
        :return: None
        """
        service_db = current_app.data.driver.db['service']
        if item['_is_template']:
            services = service_db.find({'_templates': item['_id']})
            for service in services:
                lookup = {"_id": service['_id']}
                deleteitem_internal('service', False, False, **lookup)

    @staticmethod
    def pre_post_service(user_request):
        """Called by EVE HOOK (app.on_pre_POST_service)

        If we use templates, we fill fields with template values

        :param user_request: request of the user
        :type user_request: object
        :return: None
        """
        if isinstance(user_request.json, dict):
            Template.fill_template_service(user_request.json)
        else:
            for i in user_request.json:
                Template.fill_template_service(i)

    @staticmethod
    def on_update_service(updates, original):
        """Called by EVE HOOK (app.on_update_service)

        On update service, if not template, remove in '_template_fields' fields in updates because
        we update these fields, so they are now not dependant of template

        :param updates: modified fields
        :type updates: dict
        :param original: original fields
        :type original: dict
        :return: None
        """
        if g.get('ignore_hook_patch', False):
            return
        # check if not modified the _is_template field
        if '_is_template' in updates and not updates['_is_template'] and original['_is_template']:
            abort(make_response("Change a service template to not template is forbidden", 412))
        # manage services not template
        if not original['_is_template']:
            template_fields = original['_template_fields']
            do_patch = False
            for (field_name, _) in iteritems(updates):
                if field_name in template_fields:
                    template_fields.remove(field_name)
                    do_patch = True
            if do_patch:
                lookup = {"_id": original['_id']}
                to_patch = {"_template_fields": template_fields}
                response = patch_internal('service', to_patch, False, False, **lookup)
                updates['_etag'] = response[0]['_etag']
                original['_etag'] = response[0]['_etag']

    @staticmethod
    def on_updated_service(updates, original):
        """Called by EVE HOOK (app.on_updated_service)

        After a service got updated, if this service is a template, report value of the updated
        fields in the services using this template

        :param updates: modified fields
        :type updates: dict
        :param original: original fields
        :type original: dict
        :return: None
        """
        if g.get('ignore_hook_patch', False):
            g.ignore_hook_patch = False
            return
        if original['_is_template']:
            # We must update all the services that use this template
            service_db = current_app.data.driver.db['service']
            services = service_db.find({'_templates': original['_id']})
            for service in services:
                Template.update_service_use_template(service, updates)

    @staticmethod
    def pre_post_user(user_request):
        """Called by EVE HOOK (app.on_pre_POST_user)

        If we use templates, we fill fields with template values

        :param user_request: request of the user
        :type user_request: object
        :return: None
        """
        users_request = user_request.json
        if isinstance(user_request.json, dict):
            users_request = [user_request.json]

        for user in users_request:
            # not fill in case the user use a template
            if '_templates' not in user or not user['_templates']:
                if 'host_notification_period' not in user:
                    tp_drv = current_app.data.driver.db['timeperiod']
                    tp = tp_drv.find_one({'name': 'Never'})
                    user['host_notification_period'] = tp['_id']
                if 'service_notification_period' not in user:
                    tp_drv = current_app.data.driver.db['timeperiod']
                    tp = tp_drv.find_one({'name': 'Never'})
                    user['service_notification_period'] = tp['_id']
            Template.fill_template_user(user)

    @staticmethod
    def on_update_user(updates, original):
        """Called by EVE HOOK (app.on_update_user)

        On update user, if not template, remove in '_template_fields' fields in updates because
        we update these fields, so they are now not dependant of template

        :param updates: modified fields
        :type updates: dict
        :param original: original fields
        :type original: dict
        :return: None
        """
        if g.get('ignore_hook_patch', False):
            return
        if not original['_is_template']:
            template_fields = original['_template_fields']
            do_patch = False
            for (field_name, _) in iteritems(updates):
                if field_name in template_fields:
                    template_fields.remove(field_name)
                    do_patch = True
            if do_patch:
                lookup = {"_id": original['_id']}
                to_patch = {"_template_fields": template_fields}
                response = patch_internal('user', to_patch, False, False, **lookup)
                updates['_etag'] = response[0]['_etag']
                original['_etag'] = response[0]['_etag']

    @staticmethod
    def on_updated_user(updates, original):
        """Called by EVE HOOK (app.on_updated_user)

        After user updated,
        if user is a template, report value of fields updated on user used this template
        if user is not template, add or remove services templates if _templates changed

        :param updates: modified fields
        :type updates: dict
        :param original: original fields
        :type original: dict
        :return: None
        """
        # pylint: disable=too-many-locals
        if g.get('ignore_hook_patch', False):
            g.ignore_hook_patch = False
            return
        if original['_is_template']:
            # We must update all user use this template
            user_db = current_app.data.driver.db['user']
            users = user_db.find({'_templates': original['_id']})
            for user in users:
                Template.update_user_use_template(user, updates)

    @staticmethod
    def get_inherited_fields(item, fields, tpl_type='host'):
        """Get the required fields from all the host templates hierarchy

        :param item: the first template item to search for
        :type item: dict
        :param fields: a dictionary with the fields to cumulate
        :type fields: dict
        :param tpl_type: the template type (host, service or user)
        :type tpl_type: str
        :return: None
        """
        db_drv = current_app.data.driver.db[tpl_type]

        # Cumulable fields exist in the item?
        for (field_name, field_value) in iteritems(item):
            if field_name not in fields:
                continue
            if isinstance(field_value, dict):
                fields[field_name].update(field_value)
            elif isinstance(field_value, list):
                fields[field_name][:0] = field_value

        # If some more templates are to get searched
        if '_templates' in item and item['_templates']:
            for tpl_id in item['_templates']:
                template = db_drv.find_one({'_id': ObjectId(tpl_id)})
                Template.get_inherited_fields(template, fields, tpl_type)

    @staticmethod
    def fill_template_host(item):  # pylint: disable=too-many-locals
        """Prepare fields of host with fields of host templates. The field _template_fields will
        contain all fields filled by templates

        :param item: field name / values of the host
        :type item: dict
        :return: None
        """
        host_drv = current_app.data.driver.db['host']
        # The fields which values may be cumulated:
        cumulated_fields = {'tags': [], 'customs': {}, 'users': [], 'usergroups': []}
        # The fields which must be ignored:
        not_updated_fields = []
        for (field_name, field_value) in iteritems(item):
            not_updated_fields.append(field_name)
        item['_template_fields'] = []

        # Whether host is a template or not...
        is_a_template = False
        if '_is_template' in item:
            is_a_template = item['_is_template']

        if '_templates' in item and item['_templates']:
            for host_template in item['_templates']:
                if not ObjectId.is_valid(host_template):
                    abort(make_response(
                        "The template '%s' is not at the right format" % host_template, 412))
                host = host_drv.find_one({'_id': ObjectId(host_template)})
                if host is None:
                    continue
                for (field_name, field_value) in iteritems(host):
                    if field_name not in not_updated_fields \
                            and field_name not in cumulated_fields \
                            and not field_name.startswith('_') \
                            and not field_name.startswith('ls_'):
                        item[field_name] = field_value
                        item['_template_fields'].append(field_name)

            # Cumulate fields only if item is not a template
            if not is_a_template:
                Template.get_inherited_fields(item, cumulated_fields, tpl_type='host')
                for (field_name, field_value) in iteritems(cumulated_fields):
                    if isinstance(field_value, dict):
                        item[field_name] = field_value
                    elif isinstance(field_value, list):
                        seen = set()
                        seen_add = seen.add
                        item[field_name] = [x for x in field_value
                                            if not (x in seen or seen_add(x))]
                    item['_template_fields'].append(field_name)

            schema = host_schema()
            for key in schema['schema']:
                if not key.startswith('_') and not key.startswith('ls_'):
                    if key not in item:
                        item['_template_fields'].append(key)

        if 'check_command' not in item:
            # Get default host check commands
            commands = current_app.data.driver.db['command']
            default_host_check_command = commands.find_one({'name': '_internal_host_up'})
            item['check_command'] = default_host_check_command['_id']

        if '_realm' not in item:
            # Get default logged-in user realm
            if g.get('user_realm', None):
                item['_realm'] = g.get('user_realm')

    @staticmethod
    def update_host_use_template(host, fields):
        """This update (patch) host with values of template

        :param host: fields / values of the host
        :type host: dict
        :param fields: fields updated in the template host
        :type fields: dict
        :return: None
        """
        host_db = current_app.data.driver.db['host']
        template_fields = {}
        for template_id in host['_templates']:
            temp = host_db.find_one({'_id': template_id})
            for (name, value) in iteritems(temp):
                template_fields[name] = value
        to_patch = {}
        for (name, value) in iteritems(fields):
            if name in host['_template_fields']:
                to_patch[name] = template_fields[name]
        if to_patch:
            g.ignore_hook_patch = True
            lookup = {"_id": host['_id']}
            patch_internal('host', to_patch, False, False, **lookup)

    @staticmethod
    def fill_template_service(item):  # pylint: disable=too-many-locals
        """Prepare fields of service with fields of service templates

        :param item: field name / values of the service
        :type item: dict
        :return: None
        """
        service_drv = current_app.data.driver.db['service']
        # The fields which values may be cumulated:
        cumulated_fields = {'tags': [], 'customs': {}, 'users': [], 'usergroups': []}
        # The fields which must be ignored:
        not_updated_fields = []

        for (field_name, field_value) in iteritems(item):
            not_updated_fields.append(field_name)
        item['_template_fields'] = []

        # Whether service is a template or not...
        is_a_template = False
        if '_is_template' in item:
            is_a_template = item['_is_template']

        if '_templates' in item and item['_templates'] != []:
            for service_template in item['_templates']:
                if not ObjectId.is_valid(service_template):
                    abort(make_response(
                        "The template '%s' is not at the right format" % service_template, 412))
                service = service_drv.find_one({'_id': ObjectId(service_template)})
                if service is not None:
                    for (field_name, field_value) in iteritems(service):
                        if field_name not in not_updated_fields \
                                and field_name not in cumulated_fields \
                                and not field_name.startswith('_') \
                                and not field_name.startswith('ls_'):
                            item[field_name] = field_value
                            item['_template_fields'].append(field_name)

            # Cumulate fields only if item is not a template
            if not is_a_template:
                Template.get_inherited_fields(item, cumulated_fields, tpl_type='service')
                for (field_name, field_value) in iteritems(cumulated_fields):
                    if isinstance(field_value, dict):
                        item[field_name] = field_value
                    elif isinstance(field_value, list):
                        seen = set()
                        seen_add = seen.add
                        item[field_name] = [x for x in field_value
                                            if not (x in seen or seen_add(x))]
                    item['_template_fields'].append(field_name)

            schema = service_schema()
            for key in schema['schema']:
                if not key.startswith('_') and not key.startswith('ls_'):
                    if key not in item:
                        item['_template_fields'].append(key)

            # we must never have 'host' in the _template_fields
            if 'host' in item['_template_fields']:
                item['_template_fields'].remove('host')

        if 'check_command' not in item:
            # Get default service check commands
            commands = current_app.data.driver.db['command']
            default_service_check_command = commands.find_one({'name': '_echo'})
            item['check_command'] = default_service_check_command['_id']

        if '_realm' not in item:
            # Get default logged-in user realm
            if g.get('user_realm', None):
                item['_realm'] = g.get('user_realm')

    @staticmethod
    def update_service_use_template(service, fields):
        """This update (patch) service with values of template

        :param service: fields / values of the service
        :type service: dict
        :param fields: fields updated in the template service
        :type fields: dict
        :return: None
        """
        service_db = current_app.data.driver.db['service']

        # Get the field values from the service templates
        template_fields = {}
        for template_id in service['_templates']:
            temp = service_db.find_one({'_id': template_id})
            for (name, value) in iteritems(temp):
                template_fields[name] = value
        to_patch = {}
        for (name, value) in iteritems(fields):
            if name in service['_template_fields']:
                to_patch[name] = template_fields[name]
        if to_patch:
            g.ignore_hook_patch = True
            lookup = {"_id": service['_id']}
            patch_internal('service', to_patch, False, False, **lookup)

    @staticmethod
    def prepare_service_to_post(item, host):
        """Prepare a service linked with a service template in case the host is in template host +
        services

        :param item: the service template source
        :type item: dict
        :param host: the host where put this new service
        :type host: Host
        :return: The service with right fields
        :rtype: dict
        """
        schema = service_schema()
        item['host'] = host['_id']
        item['_realm'] = host['_realm']
        item['_templates'] = [item['_id']]
        del item['_etag']
        del item['_id']
        del item['_created']
        del item['_updated']
        if '_status' in item:
            del item['_status']
        if '_links' in item:
            del item['_links']
        item['_is_template'] = False
        item['_templates_from_host_template'] = True
        item['_template_fields'] = []
        for key in schema['schema']:
            if not key.startswith('_') and not key.startswith('ls_'):
                item['_template_fields'].append(key)
        # we must never have 'host' in the _template_fields
        if 'host' in item['_template_fields']:
            item['_template_fields'].remove('host')
        return item

    @staticmethod
    def fill_template_user(item):  # pylint: disable=too-many-locals
        """Prepare fields of user with fields of user templates

        :param item: field name / values of the user
        :type item: dict
        :return: None
        """
        user_drv = current_app.data.driver.db['user']
        # The fields which values may be cumulated:
        cumulated_fields = {'tags': [], 'customs': {},
                            'host_notification_commands': [], 'service_notification_commands': []}
        # The fields which must be ignored:
        not_updated_fields = []
        for (field_name, field_value) in iteritems(item):
            not_updated_fields.append(field_name)
        item['_template_fields'] = []

        # Whether user is a template or not...
        is_a_template = False
        if '_is_template' in item:
            is_a_template = item['_is_template']

        if '_templates' in item and item['_templates']:
            for user_template in item['_templates']:
                if not ObjectId.is_valid(user_template):
                    abort(make_response(
                        "The template '%s' is not at the right format" % user_template, 412))
                user = user_drv.find_one({'_id': ObjectId(user_template)})
                if user is not None:
                    for (field_name, field_value) in iteritems(user):
                        if field_name not in not_updated_fields \
                                and field_name not in cumulated_fields \
                                and not field_name.startswith('_'):
                            item[field_name] = field_value
                            item['_template_fields'].append(field_name)

            # Cumulate fields only if item is not a template
            if not is_a_template:
                Template.get_inherited_fields(item, cumulated_fields, tpl_type='user')
                for (field_name, field_value) in iteritems(cumulated_fields):
                    if isinstance(field_value, dict):
                        item[field_name] = field_value
                    elif isinstance(field_value, list):
                        seen = set()
                        seen_add = seen.add
                        item[field_name] = [x for x in field_value
                                            if not (x in seen or seen_add(x))]
                    item['_template_fields'].append(field_name)

            schema = user_schema()
            for key in schema['schema']:
                if not key.startswith('_'):
                    if key not in item:
                        item['_template_fields'].append(key)

    @staticmethod
    def update_user_use_template(user, fields):
        """This update (patch) user with values of template

        :param user: fields / values of the user
        :type user: dict
        :param fields: fields updated in the template user
        :type fields: dict
        :return: None
        """
        user_db = current_app.data.driver.db['user']
        template_fields = {}
        for template_id in user['_templates']:
            temp = user_db.find_one({'_id': template_id})
            for (name, value) in iteritems(temp):
                template_fields[name] = value
        to_patch = {}
        for (name, value) in iteritems(fields):
            if name in user['_template_fields']:
                to_patch[name] = template_fields[name]
        if to_patch:
            g.ignore_hook_patch = True
            lookup = {"_id": user['_id']}
            patch_internal('user', to_patch, False, False, **lookup)
