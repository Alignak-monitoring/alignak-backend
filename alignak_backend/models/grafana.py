#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Resource information of grafana
"""


def get_name():
    """
    Get name of this resource

    :return: name of this resource
    :rtype: str
    """
    return 'grafana'


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
                'empty': False,
                'default': 3000
            },
            'apikey': {
                'type': 'string',
                'required': True,
                'empty': False,
            },
            'timezone': {
                'type': 'string',
                'empty': False,
                'default': 'browser'
            },
            'refresh': {
                'type': 'string',
                'empty': False,
                'default': '1m'
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
