#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Resource information of history
"""


def get_name():
    """
    Get name of this resource

    :return: name of this resource
    :rtype: str
    """
    return 'history'


def get_schema():
    """
    Schema structure of this resource

    host/service define the concerned host/service for this history event. If the service is null
    then the vent is an host event. When posting an history the backend will value the host_name
    and service_name fields automatically, this to keep human readable information even when the
    host/service do not exist anymore in the backend or if host/service _id got changed (host
    delated and re-created).

    The type field defines the event type (see the type definition for the allowed events)

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
                'nullable': True
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
                'nullable': True
            },
            'service_name': {
                'type': 'string',
                'regex': '^[^`~!$%^&*"|\'<>?,()=]+$'
            },
            'user': {
                'type': 'objectid',
                'data_relation': {
                    'resource': 'user',
                    'embeddable': True
                },
                'nullable': True
            },
            'user_name': {
                'type': 'string',
                'regex': '^[^`~!$%^&*"|\'<>?,()=]+$'
            },
            'type': {
                'type': 'string',
                'required': True,
                'allowed': [
                    # WebUI user comment
                    "webui.comment",

                    # Check result
                    "check.result",

                    # Request to force a check
                    "check.request",
                    "check.requested",

                    # Add acknowledge
                    "ack.add",
                    # Set acknowledge
                    "ack.processed",
                    # Delete acknowledge
                    "ack.delete",

                    # Add downtime
                    "downtime.add",
                    # Set downtime
                    "downtime.processed",
                    # Delete downtime
                    "downtime.delete"

                    # timeperiod transition
                    "monitoring.timeperiod_transition",
                    # alert
                    "monitoring.alert",
                    # event handler
                    "monitoring.event_handler",
                    # flapping start / stop
                    "monitoring.flapping_start",
                    "monitoring.flapping_stop",
                    # downtime start / cancel / end
                    "monitoring.downtime_start",
                    "monitoring.downtime_cancelled",
                    "monitoring.downtime_end",
                    # acknowledge
                    "monitoring.acknowledge",
                    # notification
                    "monitoring.notification",
                ],
                'default': 'check.result'
            },
            'message': {
                'type': 'string',
                'default': ''
            },
            'logcheckresult': {
                'type': 'objectid',
                'data_relation': {
                    'resource': 'logcheckresult',
                    'embeddable': True
                },
                'required': False,
            },
            '_realm': {
                'type': 'objectid',
                'data_relation': {
                    'resource': 'realm',
                    'embeddable': True
                },
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
