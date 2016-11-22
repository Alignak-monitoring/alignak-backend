#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Resource information of Alignak daemons
"""


def get_name():
    """
    Get name of this resource

    :return: name of this resource
    :rtype: str
    """
    return 'alignakdaemon'


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
            },
            'address': {
                'type': 'string',
                'required': True,
                'empty': False,
            },
            'port': {
                'type': 'integer',
                'required': True,
                'empty': False,
            },
            'last_check': {
                'type': 'integer',
                'required': True,
                'empty': False,
            },
            'alive': {
                'type': 'boolean',
                'required': True,
                'default': False
            },
            'reachable': {
                'type': 'boolean',
                'required': True,
                'default': False
            },
            'passive': {
                'type': 'boolean',
                'required': True,
                'default': False
            },
            'spare': {
                'type': 'boolean',
                'required': True,
                'default': False
            },
            'type': {
                'type': 'string',
                'required': True,
                'allowed': ['arbiter', 'scheduler', 'poller', 'broker', 'reactionner', 'receiver']
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
                },
            },
        }
    }
