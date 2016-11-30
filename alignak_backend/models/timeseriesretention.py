#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Resource information of timeseriesretention
"""


def get_name():
    """
    Get name of this resource

    :return: name of this resource
    :rtype: str
    """
    return 'timeseriesretention'


def get_schema():
    """
    Schema structure of this resource

    :return: schema dictionary
    :rtype: dict
    """
    return {
        'internal_resource': True,
        'schema': {
            'name': {
                'type': 'string',
                'required': True,
            },
            'realm': {
                'type': 'string',
                'required': True,
            },
            'host': {
                'type': 'string',
                'required': True,
            },
            'service': {
                'type': 'string',
                'required': True,
            },
            'value': {
                'type': 'integer',
                'required': True,
            },
            'timestamp': {
                'type': 'integer',
                'required': True,
            },
            'graphite': {
                'type': 'objectid',
                'data_relation': {
                    'resource': 'graphite',
                    'embeddable': True
                },
                'nullable': True,
                'default': None
            },
            'influxdb': {
                'type': 'objectid',
                'data_relation': {
                    'resource': 'influxdb',
                    'embeddable': True
                },
                'nullable': True,
                'default': None
            },
        }
    }
