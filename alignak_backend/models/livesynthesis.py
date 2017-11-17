#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Resource information of livestate synthesis
"""


def get_name(friendly=False):
    """Get name of this resource

    :return: name of this resource
    :rtype: str
    """
    if friendly:  # pragma: no cover
        return 'Alignak live state synthesis'
    return 'livesynthesis'


def get_doc():  # pragma: no cover
    """Get documentation of this resource

    :return: rst string
    :rtype: str
    """
    return """
    The ``livesynthesis`` model is maintained by the Alignak backend to get an easy overview of
    the monitored system state.

    For hosts and services, the live synthesis stores values computed from the real
    live state, each time an element state is updated:
    - a counter containing the number of host/service not monitored (no active nor
    passive checks enabled)
    - a counter containing the number of host/service in each state
    - a counter containing the number of host/service acknowledged
    - a counter containing the number of host/service in downtime
    - a counter containing the number of host/service flapping
    - the maximum business impact of the host/service in the state
    """


def get_schema():
    """Schema structure of this resource

    :return: schema dictionary
    :rtype: dict
    """
    return {
        'schema': {
            'schema_version': {
                'type': 'integer',
                'default': 2,
            },
            'hosts_total': {
                'schema_version': 1,
                'title': 'Hosts count',
                'type': 'integer',
                'default': 0,
            },
            'hosts_not_monitored': {
                'schema_version': 2,
                'title': 'Hosts not monitored',
                'type': 'integer',
                'default': 0,
            },
            'hosts_up_hard': {
                'schema_version': 1,
                'title': 'Hosts Up hard',
                'type': 'integer',
                'default': 0,
            },
            'hosts_up_soft': {
                'schema_version': 1,
                'title': 'Hosts Up soft',
                'type': 'integer',
                'default': 0,
            },
            'hosts_down_hard': {
                'schema_version': 1,
                'title': 'Hosts Down hard',
                'type': 'integer',
                'default': 0,
            },
            'hosts_down_soft': {
                'schema_version': 1,
                'title': 'Hosts Down soft',
                'type': 'integer',
                'default': 0,
            },
            'hosts_unreachable_hard': {
                'schema_version': 1,
                'title': 'Hosts Unreachable hard',
                'type': 'integer',
                'default': 0,
            },
            'hosts_unreachable_soft': {
                'schema_version': 1,
                'title': 'Hosts Unreachable soft',
                'type': 'integer',
                'default': 0,
            },
            'hosts_acknowledged': {
                'schema_version': 1,
                'title': 'Hosts ackowledged',
                'type': 'integer',
                'default': 0
            },
            'hosts_in_downtime': {
                'schema_version': 1,
                'title': 'Hosts in downtime',
                'type': 'integer',
                'default': 0
            },
            'hosts_flapping': {
                'schema_version': 1,
                'title': 'Hosts flapping',
                'type': 'integer',
                'default': 0
            },
            'hosts_business_impact': {
                'schema_version': 1,
                'title': 'Hosts business impact',
                'type': 'integer',
                'default': 0
            },

            'services_total': {
                'schema_version': 1,
                'title': 'Services count',
                'type': 'integer',
                'default': 0,
            },
            'services_not_monitored': {
                'schema_version': 2,
                'title': 'Services not monitored',
                'type': 'integer',
                'default': 0,
            },
            'services_ok_hard': {
                'schema_version': 1,
                'title': 'Services Ok hard',
                'type': 'integer',
                'default': 0,
            },
            'services_ok_soft': {
                'schema_version': 1,
                'title': 'Services Ok soft',
                'type': 'integer',
                'default': 0,
            },
            'services_warning_hard': {
                'schema_version': 1,
                'title': 'Services Warning hard',
                'type': 'integer',
                'default': 0,
            },
            'services_warning_soft': {
                'schema_version': 1,
                'title': 'Services Warning soft',
                'type': 'integer',
                'default': 0,
            },
            'services_critical_hard': {
                'schema_version': 1,
                'title': 'Services Critical hard',
                'type': 'integer',
                'default': 0,
            },
            'services_critical_soft': {
                'schema_version': 1,
                'title': 'Services Criticl soft',
                'type': 'integer',
                'default': 0,
            },
            'services_unknown_hard': {
                'schema_version': 1,
                'title': 'Services Unknown hard',
                'type': 'integer',
                'default': 0,
            },
            'services_unknown_soft': {
                'schema_version': 1,
                'title': 'Services Unknown soft',
                'type': 'integer',
                'default': 0,
            },
            'services_unreachable_hard': {
                'schema_version': 1,
                'title': 'Services Unreachable hard',
                'type': 'integer',
                'default': 0,
            },
            'services_unreachable_soft': {
                'schema_version': 1,
                'title': 'Services Unreachable soft',
                'type': 'integer',
                'default': 0,
            },
            'services_acknowledged': {
                'schema_version': 1,
                'title': 'Services acknowledged',
                'type': 'integer',
                'default': 0
            },
            'services_in_downtime': {
                'schema_version': 1,
                'title': 'Services in downtime',
                'type': 'integer',
                'default': 0
            },
            'services_flapping': {
                'schema_version': 1,
                'title': 'Services flapping',
                'type': 'integer',
                'default': 0
            },
            'services_business_impact': {
                'schema_version': 1,
                'title': 'Services business impact',
                'type': 'integer',
                'default': 0
            },

            # Realm
            '_realm': {
                'schema_version': 1,
                'title': 'Realm',
                'comment': 'Realm this element belongs to.',
                'type': 'objectid',
                'data_relation': {
                    'resource': 'realm',
                    'embeddable': True
                },
                'required': True,
            },
            '_sub_realm': {
                'schema_version': 1,
                'title': 'Sub-realms',
                'comment': 'Is this element visible in the sub-realms of its realm?',
                'type': 'boolean',
                'default': True
            },

            # Users CRUD permissions
            '_users_read': {
                'schema_version': 1,
                'type': 'list',
                'schema': {
                    'type': 'objectid',
                    'data_relation': {
                        'resource': 'user',
                        'embeddable': True,
                    }
                },
            },
        },
        'schema_deleted': {}
    }
