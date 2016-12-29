#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Resource information of influxdb
"""


def get_name():
    """
    Get name of this resource

    :return: name of this resource
    :rtype: str
    """
    return 'influxdb'


def get_schema():
    """
    Schema structure of this resource

    :return: schema dictionary
    :rtype: dict
    """
    return {
        'schema': {
            'name': {
                'type': 'string',
                'required': True,
                'empty': False,
                'unique': True,
            },
            'address': {
                'type': 'string',
                'required': True,
                'empty': False,
            },
            'port': {
                'type': 'integer',
                'default': 8086,
                'empty': False,
            },
            'database': {
                'type': 'string',
                'required': True,
                'empty': False,
                'default': 'alignak'
            },
            'login': {
                'type': 'string',
                'required': True,
                'empty': False,
            },
            'password': {
                'type': 'string',
                'required': True,
                'empty': False,
            },
            'grafana': {
                'type': 'objectid',
                'data_relation': {
                    'resource': 'grafana',
                    'embeddable': True
                },
                'nullable': True,
                'default': None
            },
            '_realm': {
                'type': 'objectid',
                'data_relation': {
                    'resource': 'realm',
                    'embeddable': True
                },
                'required': True,
            },
            '_sub_realm': {
                'type': 'boolean',
                'default': False
            },
            '_users_read': {
                'type': 'list',
                'schema': {
                    'type': 'objectid',
                    'data_relation': {
                        'resource': 'user',
                        'embeddable': True,
                    }
                },
            },
            '_users_update': {
                'type': 'list',
                'schema': {
                    'type': 'objectid',
                    'data_relation': {
                        'resource': 'user',
                        'embeddable': True,
                    }
                },
            },
            '_users_delete': {
                'type': 'list',
                'schema': {
                    'type': 'objectid',
                    'data_relation': {
                        'resource': 'user',
                        'embeddable': True,
                    }
                }
            }
        }
    }
