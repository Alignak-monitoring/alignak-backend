#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    ``alignak_backend.template`` module

    This module manages the templates (host / services)
"""
from __future__ import print_function
from copy import deepcopy
from future.utils import iteritems
from flask import current_app, g, request, abort
from eve.methods.post import post_internal
from eve.methods.patch import patch_internal
from eve.methods.put import put_internal
from eve.methods.delete import deleteitem_internal
from bson.objectid import ObjectId
from alignak_backend.models.host import get_schema as host_schema
from alignak_backend.models.service import get_schema as service_schema


class Template(object):
    """
        Template class
    """

    @staticmethod
    def pre_post_host(user_request):
        """
        Called by EVE HOOK (app.on_pre_POST_host)

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
        """
        Called by EVE HOOK (app.on_update_host)

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
            ignore_schema_fields = ['realm', '_template_fields', '_templates',
                                    '_is_template',
                                    '_templates_with_services']
            template_fields = original['_template_fields']
            do_put = False
            for (field_name, _) in iteritems(updates):
                if field_name not in ignore_schema_fields:
                    if field_name in template_fields:
                        del template_fields[field_name]
                        do_put = True
            if do_put:
                lookup = {"_id": original['_id']}
                putdata = deepcopy(original)
                putdata['_template_fields'] = template_fields
                del putdata['_etag']
                del putdata['_updated']
                del putdata['_created']
                response = put_internal('host', putdata, False, False, **lookup)
                updates['_etag'] = response[0]['_etag']
                original['_etag'] = response[0]['_etag']

    @staticmethod
    def on_updated_host(updates, original):
        """
        Called by EVE HOOK (app.on_updated_host)

        After host updated,
        if host is a template, report value of fields updated on host used this template
        if host is not template, add or remove services templates if _templates changed

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
            # We must update all host use this template
            host_db = current_app.data.driver.db['host']
            hosts = host_db.find({'_templates': original['_id']})
            for host in hosts:
                Template.update_host_use_template(host, updates)
        else:
            if '_templates'in updates and updates['_templates'] != original['_templates']:
                if original['_templates_with_services']:
                    service_db = current_app.data.driver.db['service']
                    # Get all services of this host
                    myservices = service_db.find({'_is_template': False,
                                                  'host': original['_id']})
                    myservices_template_id = []
                    myservices_bis = {}
                    for myservice in myservices:
                        myservices_template_id.append(myservice['_templates'][0])
                        myservices_bis[myservice['_templates'][0]] = myservice

                    services = {}
                    service_template_id = []
                    # loop on host templates and add into services the service are templates
                    for hostid in updates['_templates']:
                        services_template = service_db.find({'_is_template': True,
                                                             'host': hostid})
                        for srv in services_template:
                            services[srv['name']] = Template.prepare_service_to_post(srv,
                                                                                     original[
                                                                                         '_id'])
                            service_template_id.append(services[srv['name']]['_templates'][0])
                    services_to_add = list(set(service_template_id) - set(myservices_template_id))
                    services_to_del = list(set(myservices_template_id) - set(service_template_id))
                    for (_, service) in iteritems(services):
                        if service['_templates'][0] in services_to_add:
                            post_internal('service', [service])
                    for template_id in services_to_del:
                        if template_id in myservices_bis:
                            lookup = {"_id": myservices_bis[template_id]['_id']}
                            deleteitem_internal('service', False, False, **lookup)

    @staticmethod
    def on_inserted_host(items):
        """
        Called by EVE HOOK (app.on_inserted_host)

        After host inserted, if it use a template (or templates) and the the host use template
        with services, we add templates services to this host

        :param items: list of hosts
        :type items: list
        :return: None
        """
        service_db = current_app.data.driver.db['service']
        for _, item in enumerate(items):
            if item['_templates'] != [] and item['_templates_with_services']:
                # Try to add services
                services = {}
                # loop on host templates and collect services that are templates
                for hostid in item['_templates']:
                    services_template = service_db.find({'_is_template': True, 'host': hostid})
                    for srv in services_template:
                        services[srv['name']] = Template.prepare_service_to_post(srv, item['_id'])

                # when ok, and if some exist, add all services to this host
                template_services = [services[k] for k in services]
                if template_services:
                    post_internal('service', template_services)

    @staticmethod
    def on_inserted_service(items):
        """
        Called by EVE HOOK (app.on_inserted_service)

        After service inserted, if it is a template and the host linked is a template with services
        we add the service in all hosts have this host in template

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
                    {'_templates': hostid, '_templates_with_services': True})
                for hs in hosts:
                    services.append(Template.prepare_service_to_post(deepcopy(item), hs['_id']))
        if services != []:
            post_internal('service', services)

    @staticmethod
    def on_deleted_item_service(item):
        """
        Called by EVE HOOK (app.on_deleted_item_service)

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
        """
        Called by EVE HOOK (app.on_pre_POST_service)

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
        """
        Called by EVE HOOK (app.on_update_service)

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
        if not original['_is_template']:
            ignore_schema_fields = ['realm', '_template_fields', '_templates',
                                    '_is_template',
                                    '_templates_from_host_template']
            template_fields = original['_template_fields']
            do_put = False
            for (field_name, _) in iteritems(updates):
                if field_name not in ignore_schema_fields:
                    if field_name in template_fields:
                        del template_fields[field_name]
                        do_put = True
            if do_put:
                lookup = {"_id": original['_id']}
                putdata = deepcopy(original)
                putdata['_template_fields'] = template_fields
                del putdata['_etag']
                del putdata['_updated']
                del putdata['_created']
                response = put_internal('service', putdata, False, False, **lookup)
                updates['_etag'] = response[0]['_etag']
                original['_etag'] = response[0]['_etag']

    @staticmethod
    def on_updated_service(updates, original):
        """
        Called by EVE HOOK (app.on_updated_service)

        After service updated, if service is a template, report value of fields updated on
        service used this template

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
            # We must update all service use this template
            service_db = current_app.data.driver.db['service']
            services = service_db.find({'_templates': original['_id']})
            for service in services:
                Template.update_service_use_template(service, updates)

    @staticmethod
    def fill_template_host(item):
        """
        Prepare fields of host with fields of host templates

        :param item: field name / values of the host
        :type item: dict
        :return: None
        """
        host = current_app.data.driver.db['host']
        ignore_fields = ['_id', '_etag', '_updated', '_created', '_template_fields', '_templates',
                         '_is_template', 'realm', '_templates_with_services']
        fields_not_update = []
        for (field_name, field_value) in iteritems(item):
            fields_not_update.append(field_name)
        item['_template_fields'] = {}
        if ('_is_template' not in item or not item['_is_template']) \
                and '_templates' in item and item['_templates'] != []:
            for host_template in item['_templates']:
                hosts = host.find_one({'_id': ObjectId(host_template)})
                if hosts is not None:
                    for (field_name, field_value) in iteritems(hosts):
                        if field_name not in fields_not_update \
                                and field_name not in ignore_fields:
                            item[field_name] = field_value
                            item['_template_fields'][field_name] = host_template
            schema = host_schema()
            ignore_schema_fields = ['realm', '_template_fields', '_templates', '_is_template',
                                    '_templates_with_services']
            for key in schema['schema']:
                if key not in ignore_schema_fields:
                    if key not in item:
                        item['_template_fields'][key] = 0

    @staticmethod
    def update_host_use_template(host, fields):
        """
        This update (patch) host with values of template

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
        if len(to_patch) > 0:
            g.ignore_hook_patch = True
            lookup = {"_id": host['_id']}
            patch_internal('host', to_patch, False, False, **lookup)

    @staticmethod
    def fill_template_service(item):
        """
        Prepare fields of service with fields of service templates

        :param item: field name / values of the service
        :type item: dict
        :return: None
        """
        service = current_app.data.driver.db['service']
        ignore_fields = ['_id', '_etag', '_updated', '_created', '_template_fields', '_templates',
                         '_is_template', '_realm', 'host', '_templates_from_host_template']
        fields_not_update = []
        for (field_name, field_value) in iteritems(item):
            fields_not_update.append(field_name)
        item['_template_fields'] = {}
        if ('_is_template' not in item or not item['_is_template']) \
                and '_templates' in item and item['_templates'] != []:
            for service_template in item['_templates']:
                services = service.find_one({'_id': ObjectId(service_template)})
                if services is not None:
                    for (field_name, field_value) in iteritems(services):
                        if field_name not in fields_not_update \
                                and field_name not in ignore_fields:
                            item[field_name] = field_value
                            item['_template_fields'][field_name] = service_template
            schema = service_schema()
            ignore_schema_fields = ['_realm', '_template_fields', '_templates', '_is_template',
                                    '_templates_from_host_template']
            for key in schema['schema']:
                if key not in ignore_schema_fields:
                    if key not in item:
                        item['_template_fields'][key] = 0

    @staticmethod
    def update_service_use_template(service, fields):
        """
        This update (patch) service with values of template

        :param service: fields / values of the service
        :type service: dict
        :param fields: fields updated in the template service
        :type fields: dict
        :return: None
        """
        service_db = current_app.data.driver.db['service']
        template_fields = {}
        for template_id in service['_templates']:
            temp = service_db.find_one({'_id': template_id})
            for (name, value) in iteritems(temp):
                template_fields[name] = value
        to_patch = {}
        for (name, value) in iteritems(fields):
            if name in service['_template_fields']:
                to_patch[name] = template_fields[name]
        if len(to_patch) > 0:
            g.ignore_hook_patch = True
            lookup = {"_id": service['_id']}
            patch_internal('service', to_patch, False, False, **lookup)

    @staticmethod
    def prepare_service_to_post(item, hostid):
        """
        Prepare a service linked with a service template in case the host is in template host +
        services

        :param item: the service template source
        :type item: dict
        :param hostid: the id of the host where put this new service
        :type hostid: str
        :return: The service with right fields
        :rtype: dict
        """
        ignore_schema_fields = ['_realm', '_template_fields', '_templates',
                                '_is_template', '_templates_from_host_template']
        schema = service_schema()
        item['host'] = hostid
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
        item['_template_fields'] = {}
        for key in schema['schema']:
            if item not in ignore_schema_fields:
                item['_template_fields'][key] = 0
        return item
