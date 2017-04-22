#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Resource information of logcheckresult
"""


def get_name(friendly=False):
    """Get name of this resource

    :return: name of this resource
    :rtype: str
    """
    if friendly:  # pragma: no cover
        return "Check result log"
    return 'logcheckresult'


def get_doc():  # pragma: no cover
    """Get documentation of this resource

    :return: rst string
    :rtype: str
    """
    return """
    The ``logcheckresult`` model is used to maintain a log of the received checks results.

    The Alignak backend stores all the checks results it receives to keep a full log of the system
    checks results.
    """


def get_schema():
    """Schema structure of this resource

    :return: schema dictionary
    :rtype: dict
    """
    return {
        'schema': {
            'host': {
                "title": "Concerned host",
                'type': 'objectid',
                'data_relation': {
                    'resource': 'host',
                    'embeddable': True
                },
                'required': True,
            },
            'host_name': {
                "title": "Host name",
                "comment": "The backend stores the host name. This allows to keep "
                           "an information about the concerned host even if it "
                           "has been deleted from the backend.",
                'type': 'string',
                'regex': '^[^`~!$%^&*"|\'<>?,()=]+$'
            },
            'service': {
                "title": "Concerned service",
                "comment": "If not set, this check result is an host check",
                'type': 'objectid',
                'data_relation': {
                    'resource': 'service',
                    'embeddable': True
                },
                'required': True,
                'nullable': True
            },
            'service_name': {
                "title": "Service name",
                "comment": "The backend stores the service name. This allows to keep "
                           "an information about the concerned service even if it "
                           "has been deleted from the backend.",
                'type': 'string',
                'regex': '^[^`~!$%^&*"|\'<>?,()=]+$'
            },
            'state': {
                "title": "State",
                'type': 'string',
                'allowed': ["PENDING",
                            "UP", "DOWN", "UNREACHABLE",
                            "OK", "WARNING", "CRITICAL", "UNKNOWN"],
                'required': True,
            },
            'state_type': {
                "title": "State type",
                'type': 'string',
                'allowed': ["HARD", "SOFT"],
                'required': True,
            },
            'state_id': {
                "title": "State identifier",
                'type': 'integer',
                'default': 0
            },
            'passive_check': {
                "title": "Passive check",
                'type': 'boolean',
                'default': False
            },
            'acknowledged': {
                "title": "Acknowledged",
                'type': 'boolean',
                'default': False
            },
            'acknowledgement_type': {
                "title": "Acknowledgement type",
                'type': 'integer',
                'default': 1
            },
            'downtimed': {
                "title": "Downtimed",
                'type': 'boolean',
                'default': False
            },
            'last_check': {
                "title": "Check timestamp",
                'type': 'integer',
                'default': 0
            },
            'last_state': {
                "title": "Last state",
                'type': 'string',
                'default': 'OK',
                'allowed': ["PENDING",
                            "UP", "DOWN", "UNREACHABLE",
                            "OK", "WARNING", "CRITICAL", "UNKNOWN"],
            },
            'last_state_type': {
                "title": "Last state type",
                'type': 'string',
                'allowed': ["HARD", "SOFT"],
                'required': True,
            },
            'last_state_id': {
                "title": "Last state identifier",
                'type': 'integer',
                'default': 0
            },
            'last_state_changed': {
                "title": "Last state changed",
                'type': 'integer',
                'default': 0
            },
            'state_changed': {
                "title": "State changed",
                'type': 'boolean',
                'default': False
            },
            'output': {
                "title": "Output",
                'type': 'string',
                'default': ''
            },
            'long_output': {
                "title": "Long output",
                'type': 'string',
                'default': ''
            },
            'perf_data': {
                "title": "Performance data",
                'type': 'string',
                'default': ''
            },
            'latency': {
                "title": "Latency",
                'type': 'float',
                'default': 0.0
            },
            'execution_time': {
                "title": "Execution time",
                'type': 'float',
                'default': 0.0
            },

            # Realm
            '_realm': {
                "title": "Realm",
                "comment": "Realm this element belongs to.",
                'type': 'objectid',
                'data_relation': {
                    'resource': 'realm',
                    'embeddable': True
                },
                'required': True,
            },
            '_sub_realm': {
                "title": "Sub-realms",
                "comment": "Is this element visible in the sub-realms of its realm?",
                'type': 'boolean',
                'default': True
            },

            # Users CRUD permissions
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
