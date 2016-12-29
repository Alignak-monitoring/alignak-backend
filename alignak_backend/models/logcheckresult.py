#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Resource information of logcheckresult
"""


def get_name():
    """
    Get name of this resource

    :return: name of this resource
    :rtype: str
    """
    return 'logcheckresult'


def get_schema():
    """
    Schema structure of this resource

    :return: schema dictionary
    :rtype: dict
    """
    return {
        'schema': {
            'host': {
                'type': 'objectid',
                'data_relation': {
                    'resource': 'host',
                    'embeddable': True
                },
                'required': True,
            },
            'host_name': {
                'type': 'string',
                'regex': '^[^`~!$%^&*"|\'<>?,()=]+$'
            },
            'service': {
                'type': 'objectid',
                'data_relation': {
                    'resource': 'service',
                    'embeddable': True
                },
                'required': True,
                'nullable': True
            },
            'service_name': {
                'type': 'string',
                'regex': '^[^`~!$%^&*"|\'<>?,()=]+$'
            },
            'state': {
                'type': 'string',
                'allowed': ["UP", "DOWN", "UNREACHABLE", "OK", "WARNING", "CRITICAL", "UNKNOWN"],
                'required': True,
            },
            'state_type': {
                'type': 'string',
                'allowed': ["HARD", "SOFT"],
                'required': True,
            },
            'state_id': {
                'type': 'integer',
                'default': 0
            },
            'acknowledged': {
                'type': 'boolean',
                'default': False
            },
            'last_check': {
                'type': 'integer',
                'default': 0
            },
            'last_state': {
                'type': 'string',
                'default': 'OK',
                'allowed': ["OK", "WARNING", "CRITICAL", "UNKNOWN", "UP", "DOWN", "UNREACHABLE"]
            },
            'last_state_type': {
                'type': 'string',
                'allowed': ["HARD", "SOFT"],
                'required': True,
            },
            'last_state_id': {
                'type': 'integer',
                'default': 0
            },
            'state_changed': {
                'type': 'boolean',
                'default': False
            },
            'output': {
                'type': 'string',
                'default': ''
            },
            'long_output': {
                'type': 'string',
                'default': ''
            },
            'perf_data': {
                'type': 'string',
                'default': ''
            },
            'latency': {
                'type': 'float',
                'default': 0.0
            },
            'execution_time': {
                'type': 'float',
                'default': 0.0
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
        }
    }
