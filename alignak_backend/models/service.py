#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Resource information of service
"""


def get_name(friendly=False):
    """Get name of this resource

    :return: name of this resource
    :rtype: str
    """
    if friendly:  # pragma: no cover
        return 'Monitored service'
    return 'service'


def get_doc():  # pragma: no cover
    """Get documentation of this resource

    :return: rst string
    :rtype: str
    """
    return """
    The ``service`` model is used to represent a monitored service.

    A service is a monitored feature attached to an host.and monitored by your
    Alignak framework.
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
            # Importation source
            'imported_from': {
                'schema_version': 1,
                'title': 'Imported from',
                'comment': 'Item importation source (alignak-backend-import, ...)',
                'type': 'string',
                'default': 'unknown'
            },
            'definition_order': {
                'schema_version': 1,
                'title': 'Definition order',
                'comment': 'Priority level if several elements have the same name',
                'type': 'integer',
                'default': 100
            },

            # Old and to be deprecated stuff...
            'display_name': {
                'schema_version': 1,
                'title': 'Display name',
                'comment': 'Old Nagios stuff. To be deprecated',
                'skill_level': 2,
                'type': 'string',
                'default': ''
            },
            'icon_image': {
                'schema_version': 1,
                'comment': 'Old Nagios stuff. To be deprecated',
                'type': 'string',
                'skill_level': 2,
                'default': ''
            },
            'icon_image_alt': {
                'schema_version': 1,
                'comment': 'Old Nagios stuff. To be deprecated',
                'type': 'string',
                'skill_level': 2,
                'default': ''
            },
            'icon_set': {
                'schema_version': 1,
                'comment': 'Old Nagios stuff. To be deprecated',
                'type': 'string',
                'skill_level': 2,
                'default': ''
            },
            'custom_views': {
                'schema_version': 1,
                'type': 'list',
                'skill_level': 2,
                'default': []
            },

            # todo: To be deprecated
            'trending_policies': {
                'schema_version': 1,
                'title': 'Trending policies',
                'comment': 'To be explained (see #113)',
                'skill_level': 2,
                'type': 'list',
                'default': []
            },
            # Thanks to the backend templating, the duplicate_foreach is no more necessary...
            'duplicate_foreach': {
                'schema_version': 1,
                'title': 'Duplicate for each',
                'comment': 'To be deprecated. Shinken stuff...',
                'skill_level': 2,
                'type': 'string',
                'default': ''
            },
            # Thanks to the backend templating, the hostgroups is no more necessary...
            'hostgroups': {
                'schema_version': 1,
                'skill_level': 2,
                'type': 'list',
                'schema': {
                    'type': 'objectid',
                    'data_relation': {
                        'resource': 'hostgroup',
                        'embeddable': True,
                    }
                },
                'default': []
            },
            # todo: What is it?
            'default_value': {
                'schema_version': 1,
                'skill_level': 2,
                'type': 'string',
                'default': ''
            },
            # todo: this field does not seem to be used anywhere :/
            'parallelize_check': {
                'schema_version': 1,
                'skill_level': 2,
                'type': 'boolean',
                'default': True
            },
            # todo: this field does not seem to be used anywhere :/
            'merge_host_users': {
                'schema_version': 1,
                'type': 'boolean',
                'default': False
            },

            # Identity
            'name': {
                'schema_version': 1,
                'title': 'Service name',
                'comment': 'Service name (eg. service_description)',
                'type': 'string',
                'required': True,
                'empty': False,
                'regex': '^[^`~!$%^&*"|\'<>?,()=]+$',
                'dependencies': ['host', 'check_command']
            },
            'business_impact': {
                'schema_version': 1,
                'title': 'Business impact',
                'comment': 'The business impact level indicates the level of importance of this '
                           'element. The highest value the most important is the element.',
                'type': 'integer',
                'default': 2,
                'allowed': [0, 1, 2, 3, 4, 5]
            },
            'alias': {
                'schema_version': 1,
                'title': 'Alias',
                'comment': 'Element friendly name used by the Web User Interface.',
                'type': 'string',
                'default': ''
            },
            'notes': {
                'schema_version': 1,
                'title': 'Notes',
                'comment': 'Element notes. Free text to store element information.',
                'type': 'string',
                'default': ''
            },
            'notes_url': {
                'schema_version': 1,
                'title': 'Notes URL',
                'comment': 'Element notes URL. Displayed in the Web UI as some URL to be '
                           'navigatesd. Note that a very specific text format must be used for '
                           'this field, see the Web UI documentation.',
                'type': 'string',
                'default': ''
            },
            'action_url': {
                'schema_version': 1,
                'title': 'Actions URL',
                'comment': 'Element actions URL. Displayed in the Web UI as some available '
                           'actions. Note that a very specific text format must be used for '
                           'this field, see the Web UI documentation.',
                'type': 'string',
                'default': ''
            },
            'tags': {
                'schema_version': 1,
                'title': 'Tags',
                'comment': 'List of tags for this element. Intended to set tags by the Web UI',
                'type': 'list',
                'schema': {
                    'type': 'string',
                },
                'default': []
            },
            'customs': {
                'schema_version': 1,
                'title': 'Custom variables',
                'comment': '',
                'type': 'dict',
                'default': {}
            },

            # Service specific
            'host': {
                'schema_version': 1,
                'title': 'Linked host',
                'comment': 'Host the service is linked to',
                'type': 'objectid',
                'data_relation': {
                    'resource': 'host',
                    'embeddable': True
                },
                'nullable': True
            },
            'aggregation': {
                'schema_version': 1,
                'title': 'Aggregation',
                'comment': 'Group the services is belonging to. Used for the Web UI tree view.',
                'type': 'string',
                'default': ''
            },
            'host_dependency_enabled': {
                'schema_version': 1,
                'title': 'Aggregation',
                'comment': 'Unset this to remove the dependency between this service and its '
                           'parent host. Used for volatile services that need notification '
                           'related to itself and not depend on the host notifications.',
                'skill_level': 2,
                'type': 'boolean',
                'default': True
            },
            'service_dependencies': {
                'schema_version': 1,
                'title': 'Dependencies',
                'comment': 'List of the services that this service is dependent of for '
                           'notifications. A default service_dependency will exist with '
                           'default values (notification_failure_criteria as "u,c,w" '
                           'and no dependency_period). ',
                'skill_level': 1,
                'type': 'list',
                'schema': {
                    'type': 'objectid',
                    'data_relation': {
                        'resource': 'service',
                        'embeddable': True,
                    }
                },
                'default': []
            },
            'is_volatile': {
                'schema_version': 1,
                'title': 'Volatile',
                'comment': 'To make it simple, volatile services ignore the hard state transition '
                           'and they always notify when they are in a non ok state. '
                           'For more information, read the Alignak documentation about this '
                           'type of services.',
                'skill_level': 2,
                'type': 'boolean',
                'default': False
            },

            # Maintenance period
            'maintenance_period': {
                'schema_version': 1,
                'title': 'Maintenance period',
                'comment': 'The maintenance period of a service is a time period that defines '
                           'an equivalent of scheduled downtimes for the service.',
                'skill_level': 2,
                'type': 'objectid',
                'data_relation': {
                    'resource': 'timeperiod',
                    'embeddable': True
                },
                'nullable': True
            },

            # Check part
            'initial_state': {
                'schema_version': 1,
                'title': 'Initial state',
                'comment': 'Alignak sets this default state until a check happen',
                'skill_level': 1,
                'type': 'string',
                'minlength': 1,
                'maxlength': 1,
                'default': 'x',
                'allowed': ['o', 'w', 'c', 'u', 'x']
            },
            'check_period': {
                'schema_version': 1,
                'title': 'Check period',
                'comment': 'Time period during which active / passive checks can be made.',
                'type': 'objectid',
                'data_relation': {
                    'resource': 'timeperiod',
                    'embeddable': True
                }
            },

            'time_to_orphanage': {
                'schema_version': 1,
                'title': 'Time to orphanage',
                'comment': 'To be clearly understood and documented...',
                'skill_level': 2,
                'type': 'integer',
                'default': 300
            },

            # active checks
            'active_checks_enabled': {
                'schema_version': 1,
                'title': 'Active checks enabled',
                'comment': '',
                'type': 'boolean',
                'default': True
            },
            'check_command': {
                'schema_version': 1,
                'title': 'Check command',
                'comment': 'Command that will be executed to check if the element is ok.',
                'type': 'objectid',
                'data_relation': {
                    'resource': 'command',
                    'embeddable': True
                },
                'nullable': True
            },
            'check_command_args': {
                'schema_version': 1,
                'title': 'Check command arguments',
                'comment': 'Separate arguments with !. For example, if your have 2 arguments, '
                           'enter test1!test2',
                'type': 'string',
                'default': ''
            },
            'max_check_attempts': {
                'schema_version': 1,
                'title': 'Maximum check attempts',
                'comment': 'Active checks only. Number of times the check command will be '
                           'executed if it returns a state other than Ok. Setting this value '
                           'to 1 will raise an alert without any retry.',
                'skill_level': 1,
                'type': 'integer',
                'default': 1
            },
            'check_interval': {
                'schema_version': 1,
                'title': 'Check interval',
                'comment': 'Active checks only. Number of minutes between the periodical checks.',
                'skill_level': 1,
                'type': 'integer',
                'default': 5
            },
            'retry_interval': {
                'schema_version': 1,
                'title': 'Retry interval',
                'comment': 'Active checks only. Number of minutes to wait before scheduling a '
                           're-check. Checks are rescheduled at the retry interval when they have '
                           'changed to a non-ok state. Once it has been retried max_check_attempts '
                           'times without a change in its status, it will revert to being '
                           'scheduled at its check_interval period.',
                'skill_level': 1,
                'type': 'integer',
                'default': 0
            },

            # passive checks
            'passive_checks_enabled': {
                'schema_version': 1,
                'title': 'Passive checks enabled',
                'comment': '',
                'type': 'boolean',
                'default': True
            },
            'check_freshness': {
                'schema_version': 1,
                'title': 'Check freshness',
                'comment': 'Passive checks only. If the freshness check is enabled, and no '
                           'passive check has been received since freshness_threshold seconds, '
                           'the state will be forced to freshness_state.',
                'type': 'boolean',
                'default': False
            },
            'freshness_threshold': {
                'schema_version': 1,
                'title': 'Freshness threshold',
                'comment': 'Passive checks only. Number of seconds for the freshness check to '
                           'force the freshness_state. If this value is set to 0, Alignak will '
                           'use a default value (3600 seconds)',
                'type': 'integer',
                'default': 0
            },
            'freshness_state': {
                'schema_version': 1,
                'title': 'Freshness state',
                'comment': 'Passive checks only. The state that will be forced by Alignak when '
                           'the freshness check fails.',
                'type': 'string',
                'default': 'x',
                'allowed': ['o', 'w', 'c', 'u', 'x']
            },

            # event handlers
            'event_handler_enabled': {
                'schema_version': 1,
                'title': 'Event handler enabled',
                'skill_level': 1,
                'type': 'boolean',
                'default': False
            },
            'event_handler': {
                'schema_version': 1,
                'title': 'Event handler',
                'comment': 'Command that should run whenever a change in the element state is '
                           'detected.',
                'skill_level': 1,
                'type': 'objectid',
                'data_relation': {
                    'resource': 'command',
                    'embeddable': True
                },
                'nullable': True,
                'default': None
            },
            'event_handler_args': {
                'schema_version': 1,
                'title': 'Event handler arguments',
                'comment': '',
                'type': 'string',
                'default': ''
            },

            # flapping
            'flap_detection_enabled': {
                'schema_version': 1,
                'title': 'Flapping detection enabled',
                'comment': 'Flapping occurs when an element changes state too frequently, '
                           'resulting in a storm of problem and recovery notifications. '
                           'Once an element is detected as flapping, all its notifications '
                           'are blocked.',
                'skill_level': 2,
                'type': 'boolean',
                'default': True
            },
            'flap_detection_options': {
                'schema_version': 1,
                'title': 'Flapping detection options',
                'comment': 'States involved in the flapping detection logic.',
                'skill_level': 2,
                'type': 'list',
                'default': ['o', 'w', 'c', 'u', 'x'],
                'allowed': ['o', 'w', 'c', 'u', 'x']
            },
            'low_flap_threshold': {
                'schema_version': 1,
                'title': 'Low flapping threshold',
                'skill_level': 2,
                'type': 'integer',
                'default': 25
            },
            'high_flap_threshold': {
                'schema_version': 1,
                'title': 'High flapping threshold',
                'skill_level': 2,
                'type': 'integer',
                'default': 50
            },

            # performance data
            'process_perf_data': {
                'schema_version': 1,
                'title': 'Performance data enabled',
                'skill_level': 1,
                'type': 'boolean',
                'default': True
            },

            # Notification part
            'notifications_enabled': {
                'schema_version': 1,
                'title': 'Notifications enabled',
                'type': 'boolean',
                'default': True
            },
            'notification_period': {
                'schema_version': 1,
                'title': 'Notifications period',
                'comment': 'Time period during which notifications can be sent.',
                'type': 'objectid',
                'data_relation': {
                    'resource': 'timeperiod',
                    'embeddable': True
                }
            },
            'notification_options': {
                'schema_version': 1,
                'title': 'Notifications options',
                'comment': 'List of the notifications types that can be sent.',
                'type': 'list',
                'default': ['w', 'u', 'c', 'r', 'f', 's', 'x'],
                'allowed': ['w', 'u', 'c', 'r', 'f', 's', 'x', 'n']
            },
            'users': {
                'schema_version': 1,
                'title': 'Notifications users',
                'comment': 'List of the users that will receive the sent notifications.',
                'type': 'list',
                'schema': {
                    'type': 'objectid',
                    'data_relation': {
                        'resource': 'user',
                        'embeddable': True,
                    }
                },
                'default': []
            },
            'usergroups': {
                'schema_version': 1,
                'title': 'Notifications users groups',
                'comment': 'List of the users groups that will receive the sent notifications.',
                'type': 'list',
                'schema': {
                    'type': 'objectid',
                    'data_relation': {
                        'resource': 'usergroup',
                        'embeddable': True,
                    }
                },
                'default': []
            },
            'notification_interval': {
                'schema_version': 1,
                'title': 'Notifications interval',
                'comment': 'Number of minutes to wait before re-sending the notifications if '
                           'the problem is still present. If you set this value to 0, only one '
                           'notification will be sent out.',
                'type': 'integer',
                'default': 60
            },
            'first_notification_delay': {
                'schema_version': 1,
                'title': 'First notification delay',
                'comment': 'Number of minutes to wait before sending out the first problem '
                           'notification when a non-ok state is detected. If you set this value '
                           'to 0, the first notification will be sent-out immediately.',
                'type': 'integer',
                'default': 0
            },

            # stalking
            'stalking_options': {
                'schema_version': 1,
                'title': 'Stalking options',
                'comment': 'When enabled for a specific state, Alignak will add an information '
                           'log for each element check even if the state did not changed.',
                'skill_level': 2,
                'type': 'list',
                'default': [],
                'allowed': ['o', 'w', 'u', 'c', 'x']
            },

            # Alignak daemons
            'poller_tag': {
                'schema_version': 1,
                'title': 'Poller tag',
                'comment': 'Set a value for this element checks to be managed by a '
                           'dedicated poller.',
                'skill_level': 1,
                'type': 'string',
                'default': ''
            },
            'reactionner_tag': {
                'schema_version': 1,
                'title': 'Reactionner tag',
                'comment': 'Set a value for this element notifications to be managed by a '
                           'dedicated reactionner.',
                'skill_level': 1,
                'type': 'string',
                'default': ''
            },

            # Modulations
            # todo Modulations are not yet implemented in the Alignak backend (see #114, #115, #116)
            'checkmodulations': {
                'schema_version': 1,
                'title': 'Checks modulations',
                'comment': 'Not yet implemented (#114).',
                'skill_level': 2,
                'type': 'list',
                'default': []
            },
            'macromodulations': {
                'schema_version': 1,
                'title': 'Macros modulations',
                'comment': 'Not yet implemented (#115).',
                'skill_level': 2,
                'type': 'list',
                'default': []
            },
            'resultmodulations': {
                'schema_version': 1,
                'title': 'Results modulations',
                'comment': 'Not yet implemented (#116).',
                'skill_level': 2,
                'type': 'list',
                'default': []
            },
            'business_impact_modulations': {
                'schema_version': 1,
                'title': 'Business impact modulations',
                'comment': 'Not yet implemented (#116).',
                'skill_level': 2,
                'type': 'list',
                'default': []
            },

            # todo: manage escalations
            'escalations': {
                'schema_version': 1,
                'title': 'Escalations',
                'comment': 'List of the escalations applied to this element. Not yet implemented.',
                'skill_level': 2,
                'type': 'list',
                'schema': {
                    'type': 'objectid',
                    'data_relation': {
                        'resource': 'serviceescalation',
                        'embeddable': True,
                    }
                },
                'default': []
            },

            # Business rules
            # todo Business rules are not yet implemented (see #146)
            'labels': {
                'schema_version': 1,
                'title': 'BR labels',
                'comment': 'Not yet implemented (#146)',
                'skill_level': 2,
                'type': 'list',
                'default': []
            },
            'business_rule_output_template': {
                'schema_version': 1,
                'title': 'BR output template',
                'comment': 'Not yet implemented (#146)',
                'skill_level': 2,
                'type': 'string',
                'default': ''
            },
            'business_rule_smart_notifications': {
                'schema_version': 1,
                'title': 'BR smart notifications',
                'comment': 'Not yet implemented (#146)',
                'skill_level': 2,
                'type': 'boolean',
                'default': False
            },
            'business_rule_downtime_as_ack': {
                'schema_version': 1,
                'title': 'BR downtime as ack',
                'comment': 'Not yet implemented (#146)',
                'skill_level': 2,
                'type': 'boolean',
                'default': False
            },
            'business_rule_host_notification_options': {
                'schema_version': 1,
                'title': 'BR host notification options',
                'comment': 'Not yet implemented (#146)',
                'skill_level': 2,
                'type': 'list',
                'default': ['d', 'u', 'r', 'f', 's'],
                'allowed': ['d', 'u', 'r', 'f', 's', 'n']
            },
            'business_rule_service_notification_options': {
                'schema_version': 1,
                'title': 'BR service notification options',
                'comment': 'Not yet implemented (#146)',
                'skill_level': 2,
                'type': 'list',
                'default': ['w', 'u', 'c', 'r', 'f', 's'],
                'allowed': ['w', 'u', 'c', 'r', 'f', 's', 'n']
            },

            # Triggers
            'trigger_name': {
                'schema_version': 1,
                'title': 'Trigger name',
                'comment': 'To be documented',
                'skill_level': 2,
                'type': 'string',
                'default': ''
            },
            'trigger_broker_raise_enabled': {
                'schema_version': 1,
                'title': 'Trigger broker',
                'comment': 'To be documented',
                'skill_level': 2,
                'type': 'boolean',
                'default': False
            },

            # Snapshot
            'snapshot_enabled': {
                'schema_version': 1,
                'title': 'Snapshot enabled',
                'skill_level': 2,
                'type': 'boolean',
                'default': False
            },
            'snapshot_command': {
                'schema_version': 1,
                'title': 'Snapshot command',
                'comment': 'Command executed for the snapshot',
                'skill_level': 2,
                'type': 'objectid',
                'data_relation': {
                    'resource': 'command',
                    'embeddable': True
                },
                'nullable': True
            },
            'snapshot_period': {
                'schema_version': 1,
                'title': 'Snapshot period',
                'comment': 'Time period when the snapshot feature is active',
                'skill_level': 2,
                'type': 'objectid',
                'data_relation': {
                    'resource': 'timeperiod',
                    'embeddable': True
                },
                'nullable': True
            },
            'snapshot_criteria': {
                'schema_version': 1,
                'title': 'Snapshot criteria',
                'comment': 'Execute the snapshot command when the state matches one '
                           'of the criteria',
                'skill_level': 2,
                'type': 'list',
                'default': ['w', 'c', 'x']
            },
            'snapshot_interval': {
                'schema_version': 1,
                'title': 'Snapshot interval',
                'comment': 'Minimum interval between two snapshots',
                'skill_level': 2,
                'type': 'integer',
                'default': 5
            },

            # Service live state fields are prefixed with ls_
            # Make this field consistent with the initial_state...
            'ls_state': {
                'schema_version': 1,
                'title': 'State',
                'comment': 'Current state',
                'type': 'string',
                'default': 'UNKNOWN',
                'allowed': ['OK', 'WARNING', 'CRITICAL', 'UNKNOWN', 'UNREACHABLE']
            },
            'ls_state_type': {
                'schema_version': 1,
                'title': 'State type',
                'comment': 'Current state type',
                'type': 'string',
                'default': 'HARD',
                'allowed': ['HARD', 'SOFT']
            },
            'ls_state_id': {
                'schema_version': 1,
                'title': 'State identifier',
                'comment': 'Current state identifier. '
                           'O: OK, 1: WARNING, 2: CRITICAL, 3: UNKNOWN, 4: UNREACHABLE',
                'type': 'integer',
                'default': 3,
                'allowed': [0, 1, 2, 3, 4]
            },
            'ls_acknowledged': {
                'schema_version': 1,
                'title': 'Acknowledged',
                'comment': 'Currently acknowledged',
                'type': 'boolean',
                'default': False
            },
            'ls_acknowledgement_type': {
                'schema_version': 1,
                'title': 'Acknowledgement type',
                'comment': '',
                'type': 'integer',
                'default': 1
            },
            'ls_downtimed': {
                'schema_version': 1,
                'title': 'Downtimed',
                'comment': 'Currently downtimed',
                'type': 'boolean',
                'default': False
            },
            'ls_last_check': {
                'schema_version': 1,
                'title': 'Last check time',
                'comment': 'Last check timestamp',
                'type': 'integer',
                'default': 0
            },
            'ls_last_state': {
                'schema_version': 1,
                'title': 'Last state',
                'comment': 'Former state',
                'type': 'string',
                'default': 'UNKNOWN',
                'allowed': ['OK', 'WARNING', 'CRITICAL', 'UNKNOWN', 'UNREACHABLE']
            },
            'ls_last_state_type': {
                'schema_version': 1,
                'title': 'Last state type',
                'comment': 'Former state type',
                'type': 'string',
                'default': 'HARD',
                'allowed': ['HARD', 'SOFT']
            },
            'ls_last_state_changed': {
                'schema_version': 1,
                'title': 'Last state changed',
                'comment': 'Last state changed timestamp',
                'type': 'integer',
                'default': 0
            },

            # Not in the service LCR
            'ls_next_check': {
                'schema_version': 1,
                'title': 'Next check',
                'comment': 'Next check timestamp',
                'type': 'integer',
                'default': 0
            },

            'ls_output': {
                'schema_version': 1,
                'title': 'Output',
                'comment': 'Last check output',
                'type': 'string',
                'default': ''
            },
            'ls_long_output': {
                'schema_version': 1,
                'title': 'Long output',
                'comment': 'Last check long output',
                'type': 'string',
                'default': ''
            },
            'ls_perf_data': {
                'schema_version': 1,
                'title': 'Performance data',
                'comment': 'Last check performance data',
                'type': 'string',
                'default': ''
            },

            'ls_current_attempt': {
                'schema_version': 1,
                'title': 'Current attempt number',
                'comment': '',
                'type': 'integer',
                'default': 0
            },
            'ls_max_attempts': {
                'schema_version': 1,
                'title': 'Maximum attempts',
                'comment': '',
                'type': 'integer',
                'default': 0
            },
            'ls_latency': {
                'schema_version': 1,
                'title': 'Latency',
                'comment': 'Last check latency',
                'type': 'float',
                'default': 0.0
            },
            'ls_execution_time': {
                'schema_version': 1,
                'title': 'Execution time',
                'comment': 'Last check execution time',
                'type': 'float',
                'default': 0.0
            },

            'ls_passive_check': {
                'schema_version': 1,
                'title': 'Check type',
                'comment': 'Last check was active or passive?',
                'type': 'boolean',
                'default': False
            },

            # Last time state changed
            'ls_state_changed': {
                'schema_version': 2,
                'title': 'Last time state changed',
                'comment': 'Last time this element state has changed.',
                'type': 'integer',
                'default': 0
            },
            'ls_last_hard_state_changed': {
                'schema_version': 1,
                'title': 'Last time hard state changed',
                'comment': 'Last time this element hard state has changed.',
                'type': 'integer',
                'default': 0
            },

            # Last time in the corresponding state
            'ls_last_time_ok': {
                'schema_version': 1,
                'title': 'Last time ok',
                'comment': 'Last time this element was Ok.',
                'type': 'integer',
                'default': 0
            },
            'ls_last_time_warning': {
                'schema_version': 1,
                'title': 'Last time warning',
                'comment': 'Last time this element was Warning.',
                'type': 'integer',
                'default': 0
            },
            'ls_last_time_critical': {
                'schema_version': 1,
                'title': 'Last time critical',
                'comment': 'Last time this element was Unknown.',
                'type': 'integer',
                'default': 0
            },
            'ls_last_time_unknown': {
                'schema_version': 1,
                'title': 'Last time unknown',
                'comment': 'Last time this element was Unknown.',
                'type': 'integer',
                'default': 0
            },
            'ls_last_time_unreachable': {
                'schema_version': 1,
                'title': 'Last time unreachable',
                'comment': 'Last time this element was Unreachable.',
                'type': 'integer',
                'default': 0
            },

            'ls_grafana': {
                'schema_version': 1,
                'title': 'Grafana available',
                'comment': 'This element has a Grafana panel available',
                'type': 'boolean',
                'default': False
            },
            'ls_grafana_panelid': {
                'schema_version': 1,
                'title': 'Grafana identifier',
                'comment': 'Grafana panel identifier',
                'type': 'integer',
                'default': 0
            },

            'ls_last_notification': {
                'schema_version': 1,
                'title': 'Last notification sent',
                'comment': '',
                'type': 'integer',
                'default': 0
            },

            # Service computed overall state identifier
            '_overall_state_id': {
                'schema_version': 1,
                'title': 'Element overall state',
                'comment': 'The overall state is a synthesis state that considers the element '
                           'state, its acknowledgement and its downtime.',
                'type': 'integer',
                'default': 3
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
            '_users_update': {
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
            '_users_delete': {
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

            # Templates
            '_is_template': {
                'schema_version': 1,
                'title': 'Template',
                'comment': 'Indicate if this element is a template or a real element',
                'type': 'boolean',
                'default': False
            },
            '_templates': {
                'schema_version': 1,
                'title': 'Templates',
                'comment': 'List of templates this element is linked to.',
                'type': 'list',
                'schema': {
                    'type': 'objectid',
                    'data_relation': {
                        'resource': 'service',
                        'embeddable': True,
                    }
                },
                'default': []
            },
            '_templates_from_host_template': {
                'schema_version': 1,
                'title': 'Template from host',
                'comment': 'This element was created as a service from an host template.',
                'type': 'boolean',
                'default': False
            },
            '_template_fields': {
                'schema_version': 1,
                'title': 'Template fields',
                'comment': 'If this element is not a template, this field contains the list of '
                           'the fields linked to the templates this element is linked to',
                'type': 'list',
                'default': []
            }
        },
        'schema_deleted': {
            'ls_impact': {
                'schema_version': 1,
                'title': 'Impact',
                'comment': 'Is an impact?',
                'type': 'boolean',
                'default': False
            },
            'ls_attempt': {
                'schema_version': 1,
                'title': 'Current attempt number',
                'comment': '',
                'type': 'integer',
                'default': 0
            }
        }
    }
