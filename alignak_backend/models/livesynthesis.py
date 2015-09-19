#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Resource information of livestate synthesis
"""


def get_name():
    """
    Get name of this resource

    :return: name of this resource
    :rtype: str
    """
    return 'livesynthesis'


def get_schema():
    """
    Schema structure of this resource

    For an element type and a state, store values computed from the hosts/services livestate:
    - a counter containing the number of element_type in the state
    - a percentage of element_type in the state
    - a counter containing the number of element_type in the state and acknowledged
    - a counter containing the number of element_type in the state and in downtime
    - a counter containing the number of element_type in the state and flapping
    - the maximum business impact of the element_type in the state

    :return: schema dictionnary
    :rtype: dict
    """
    return {
        'schema': {
            'hosts_total': {
                'type': 'int',
                'default': 0,
            },
            'hosts_up': {
                'type': 'int',
                'default': 0,
            },
            'hosts_down': {
                'type': 'int',
                'default': 0,
            },
            'hosts_unreachable': {
                'type': 'int',
                'default': 0,
            },
            'hosts_unknown': {
                'type': 'int',
                'default': 0,
            },
            'hosts_acknowledged': {
                'type': 'int',
                'default': 0
            },
            'hosts_in_downtime': {
                'type': 'int',
                'default': 0
            },
            'hosts_flapping': {
                'type': 'int',
                'default': 0
            },
            'hosts_business_impact': {
                'type': 'int',
                'default': 0
            },
            'services_total': {
                'type': 'int',
                'default': 0,
            },
            'services_ok': {
                'type': 'int',
                'default': 0,
            },
            'services_warning': {
                'type': 'int',
                'default': 0,
            },
            'services_critical': {
                'type': 'int',
                'default': 0,
            },
            'services_unknown': {
                'type': 'int',
                'default': 0,
            },
            'services_acknowledged': {
                'type': 'int',
                'default': 0
            },
            'services_in_downtime': {
                'type': 'int',
                'default': 0
            },
            'services_flapping': {
                'type': 'int',
                'default': 0
            },
            'services_business_impact': {
                'type': 'int',
                'default': 0
            },
            '_brotherhood': {
                'type': 'objectid',
                'data_relation': {
                    'resource': 'brotherhood',
                    'embeddable': True,
                },
            },
            '_users_read': {
                'type': 'list',
                'schema': {
                    'type': 'objectid',
                    'data_relation': {
                        'resource': 'contact',
                        'embeddable': True,
                    }
                },
            }
        }
    }
