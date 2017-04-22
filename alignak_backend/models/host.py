#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Resource information of host
"""


def get_name(friendly=False):
    """Get name of this resource

    :return: name of this resource
    :rtype: str
    """
    if friendly:  # pragma: no cover
        return "Monitored host"
    return 'host'


def get_doc():  # pragma: no cover
    """Get documentation of this resource

    :return: rst string
    :rtype: str
    """
    return """
    The ``host`` model is used to represent a monitored host.

    An host may be a router, a server, a workstation, ... that you want to be monitored by your
    Alignak framework.
    """


def get_schema():
    """Schema structure of this resource

    :return: schema dictionary
    :rtype: dict
    """
    return {
        'schema': {
            # Importation source
            'imported_from': {
                "title": "Imported from",
                "comment": "Item importation source (alignak-backend-import, ...)",
                'type': 'string',
                'default': 'unknown'
            },
            'definition_order': {
                "title": "Definition order",
                "comment": "Priority level if several elements have the same name",
                'type': 'integer',
                'default': 100
            },

            # Old and to be deprecated stuff...
            'display_name': {
                "title": "Display name",
                "comment": "Old Nagios stuff. To be deprecated",
                'skill_level': 2,
                'type': 'string',
                'default': ''
            },
            'icon_image': {
                "comment": "Old Nagios stuff. To be deprecated",
                'skill_level': 2,
                'type': 'string',
                'default': ''
            },
            'icon_image_alt': {
                "comment": "Old Nagios stuff. To be deprecated",
                'skill_level': 2,
                'type': 'string',
                'default': ''
            },
            'icon_set': {
                "comment": "Old Nagios stuff. To be deprecated",
                'skill_level': 2,
                'type': 'string',
                'default': ''
            },
            'vrml_image': {
                "comment": "Old Nagios stuff. To be deprecated",
                'skill_level': 2,
                'type': 'string',
                'default': ''
            },
            'statusmap_image': {
                "comment": "Old Nagios stuff. To be deprecated",
                'skill_level': 2,
                'type': 'string',
                'default': ''
            },
            '2d_coords': {
                "comment": "Old Nagios stuff. To be deprecated",
                'skill_level': 2,
                'type': 'string',
                'default': ''
            },
            '3d_coords': {
                "comment": "Old Nagios stuff. To be deprecated",
                'skill_level': 2,
                'type': 'string',
                'default': ''
            },
            'custom_views': {
                'type': 'list',
                'default': []
            },

            # todo: To be deprecated
            'failure_prediction_enabled': {
                "title": "Failure prediction",
                "comment": "Nagios legacy property not used in Alignak",
                'skill_level': 2,
                'type': 'boolean',
                'default': False
            },
            'obsess_over_host': {
                "title": "Obsessive check",
                "comment": "Nagios legacy property not used in Alignak",
                'skill_level': 2,
                'type': 'boolean',
                'default': False
            },
            'trending_policies': {
                "title": "Trending policies",
                "comment": "To be explained (see #113)",
                'skill_level': 2,
                'type': 'list',
                'default': []
            },

            # Identity
            'name': {
                "title": "Host name",
                "comment": "Unique host name",
                'type': 'string',
                'required': True,
                'empty': False,
                'unique': True,
                'regex': '^[^`~!$%^&*"|\'<>?,()=]+$',
                'dependencies': ['check_command']
            },
            'business_impact': {
                "title": "Business impact",
                "comment": "The business impact level indicates the level of importance of this "
                           "element. The highest value the most important is the elemen.",
                'type': 'integer',
                'default': 2
            },
            'alias': {
                "title": "Alias",
                "comment": "Element friendly name used by the Web User Interface.",
                'type': 'string',
                'default': ''
            },
            'notes': {
                "title": "Notes",
                "comment": "Element notes. Free text to store element information.",
                'type': 'string',
                'default': ''
            },
            'notes_url': {
                "title": "Notes URL",
                "comment": "Element notes URL. Displayed in the Web UI as some URL to be "
                           "navigatesd. Note that a very specific text format must be used for "
                           "this field, see the Web UI documentation.",
                'type': 'string',
                'default': ''
            },
            'action_url': {
                "title": "Actions URL",
                "comment": "Element actions URL. Displayed in the Web UI as some available "
                           "actions. Note that a very specific text format must be used for "
                           "this field, see the Web UI documentation.",
                'type': 'string',
                'default': ''
            },
            'tags': {
                "title": "Tags",
                "comment": "List of tags for this element. Intended to set tags by the Web UI",
                'type': 'list',
                'schema': {
                    'type': 'string',
                },
                'default': []
            },
            'customs': {
                "title": "Custom variables",
                "comment": "",
                'type': 'dict',
                'default': {}
            },

            # Host specific
            'location': {
                "title": "Location",
                "comment": "Element GPS coordinates",
                'type': 'point',
                'default': {"type": "Point", "coordinates": [46.3613628, 6.5394704]}
            },
            'parents': {
                "title": "Parents",
                "comment": "Elements which this element depends of. "
                           "Used to define the network hierarchy.",
                'skill_level': 1,
                'type': 'list',
                'schema': {
                    'type': 'objectid',
                    'data_relation': {
                        'resource': 'host',
                        'embeddable': True,
                    }
                },
                'default': []
            },
            'address': {
                "title": "Host address (IPv4)",
                "comment": "",
                'type': 'string',
                'default': ''
            },
            'address6': {
                "title": "Host address (IPv6)",
                "comment": "",
                'type': 'string',
                'default': ''
            },

            # Maintenance period
            'maintenance_period': {
                "title": "Maintenance period",
                "comment": "The maintenance period of an host is a time period that defines "
                           "an equivalent of scheduled downtimes for the host.",
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
                "title": "Initial state",
                "comment": "Alignak sets this default state until a check happen",
                'skill_level': 1,
                'type': 'string',
                'minlength': 1,
                'maxlength': 1,
                'default': 'x',
                'allowed': ["o", "d", "x"]
            },
            'check_period': {
                "title": "Check period",
                "comment": "Time period during which active / passive checks can be made.",
                'type': 'objectid',
                'data_relation': {
                    'resource': 'timeperiod',
                    'embeddable': True
                }
            },

            'time_to_orphanage': {
                "title": "Time to orphanage",
                "comment": "To be clearly understood and documented...",
                'skill_level': 2,
                'type': 'integer',
                'default': 300
            },

            # active checks
            'active_checks_enabled': {
                "title": "Active checks enabled",
                "comment": "",
                'type': 'boolean',
                'default': True
            },
            'check_command': {
                "title": "Check command",
                "comment": "Command that will be executed to check if the element is ok.",
                'type': 'objectid',
                'data_relation': {
                    'resource': 'command',
                    'embeddable': True
                },
                'nullable': True
            },
            'check_command_args': {
                "title": "Check command arguments",
                "comment": "",
                'type': 'string',
                'default': ''
            },
            'max_check_attempts': {
                "title": "Maximum check attempts",
                "comment": "Active checks only. Number of times the check command will be "
                           "executed if it returns a state other than Ok. Setting this value "
                           "to 1 will raise an alert without any retry.",
                'skill_level': 1,
                'type': 'integer',
                'default': 1
            },
            'check_interval': {
                "title": "Check interval",
                "comment": "Active checks only. Number of minutes between the periodical checks.",
                'skill_level': 1,
                'type': 'integer',
                'default': 5
            },
            'retry_interval': {
                "title": "Retry interval",
                "comment": "Active checks only. Number of minutes to wait before scheduling a "
                           "re-check. Checks are rescheduled at the retry interval when they have "
                           "changed to a non-ok state. Once it has been retried max_check_attempts "
                           "times without a change in its status, it will revert to being "
                           "scheduled at its check_interval period.",
                'skill_level': 1,
                'type': 'integer',
                'default': 0
            },

            # passive checks
            'passive_checks_enabled': {
                "title": "Passive checks enabled",
                "comment": "",
                'type': 'boolean',
                'default': True
            },
            'check_freshness': {
                "title": "Check freshness",
                "comment": "Passive checks only. If the freshness check is enabled, and no "
                           "passive check has been received since freshness_threshold seconds, "
                           "the state will be forced to freshness_state.",
                'type': 'boolean',
                'default': False
            },
            'freshness_threshold': {
                "title": "Freshness threshold",
                "comment": "Passive checks only. Number of seconds for the freshness check to "
                           "force the freshness_state. If this value is set to 0, Alignak will "
                           "use a default value (3600 seconds)",
                'type': 'integer',
                'default': 0
            },
            'freshness_state': {
                "title": "Freshness state",
                "comment": "Passive checks only. The state that will be forced by Alignak when "
                           "the freshness check fails.",
                'type': 'string',
                'default': 'x',
                'allowed': ["o", "d", "x"]
            },

            # event handlers
            'event_handler_enabled': {
                "title": "Event handler enabled",
                'skill_level': 1,
                'type': 'boolean',
                'default': False
            },
            'event_handler': {
                "title": "Event handler",
                "comment": "Command that should run whenever a change in the element state is "
                           "detected.",
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
                "title": "Event handler arguments",
                "comment": "",
                'skill_level': 1,
                'type': 'string',
                'default': ''
            },

            # flapping
            'flap_detection_enabled': {
                "title": "Flapping detection enabled",
                "comment": "Flapping occurs when an element changes state too frequently, "
                           "resulting in a storm of problem and recovery notifications. "
                           "Once an element is detected as flapping, all its notifications "
                           "are blocked.",
                'skill_level': 2,
                'type': 'boolean',
                'default': True
            },
            'flap_detection_options': {
                "title": "Flapping detection options",
                "comment": "States involved in the flapping detection logic.",
                'skill_level': 2,
                'type': 'list',
                'default': ['o', 'd', 'x'],
                'allowed': ['o', 'd', 'x']
            },
            'low_flap_threshold': {
                "title": "Low flapping threshold",
                'skill_level': 2,
                'type': 'integer',
                'default': 25
            },
            'high_flap_threshold': {
                "title": "High flapping threshold",
                'skill_level': 2,
                'type': 'integer',
                'default': 50
            },

            # performance data
            'process_perf_data': {
                "title": "Performance data enabled",
                'skill_level': 1,
                'type': 'boolean',
                'default': True
            },

            # Notification part
            'notifications_enabled': {
                "title": "Notifications enabled",
                'type': 'boolean',
                'default': True
            },
            'notification_period': {
                "title": "Notifications period",
                "comment": "Time period during which notifications can be sent.",
                'type': 'objectid',
                'data_relation': {
                    'resource': 'timeperiod',
                    'embeddable': True
                }
            },
            'notification_options': {
                "title": "Notifications options",
                "comment": "List of the notifications types that can be sent.",
                'type': 'list',
                'default': ['d', 'x', 'r', 'f', 's'],
                'allowed': ['d', 'x', 'r', 'f', 's', 'n']
            },
            'users': {
                "title": "Notifications users",
                "comment": "List of the users that will receive the sent notifications.",
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
                "title": "Notifications users",
                "comment": "List of the users groups that will receive the sent notifications.",
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
                "title": "Notifications interval",
                "comment": "Number of minutes to wait before re-sending the notifications if "
                           "the problem is still present. If you set this value to 0, only one "
                           "notification will be sent out.",
                'type': 'integer',
                'default': 60
            },
            'first_notification_delay': {
                "title": "First notification delay",
                "comment": "Number of minutes to wait before sending out the first problem "
                           "notification when a non-ok state is detected. If you set this value "
                           "to 0, the first notification will be sent-out immediately.",
                'type': 'integer',
                'default': 0
            },

            # stalking
            'stalking_options': {
                "title": "Stalking options",
                "comment": "When enabled for a specific state, Alignak will add an information "
                           "log for each element check even if the state did not changed.",
                'skill_level': 2,
                'type': 'list',
                'default': [],
                'allowed': ['o', 'd', 'x']
            },

            # Alignak daemons
            'poller_tag': {
                "title": "Poller tag",
                "comment": "Set a value for this element checks to be managed by a "
                           "dedicated poller.",
                'skill_level': 1,
                'type': 'string',
                'default': ''
            },
            'reactionner_tag': {
                "title": "Reactionner tag",
                "comment": "Set a value for this element notifications to be managed by a "
                           "dedicated reactionner.",
                'skill_level': 1,
                'type': 'string',
                'default': ''
            },

            # Modulations
            # todo Modulations are not yet implemented in the Alignak backend (see #114, #115, #116)
            'checkmodulations': {
                "title": "Checks modulations",
                "comment": "Not yet implemented (#114).",
                'skill_level': 2,
                'type': 'list',
                'default': []
            },
            'macromodulations': {
                "title": "Macros modulations",
                "comment": "Not yet implemented (#115).",
                'skill_level': 2,
                'type': 'list',
                'default': []
            },
            'resultmodulations': {
                "title": "Results modulations",
                "comment": "Not yet implemented (#116).",
                'skill_level': 2,
                'type': 'list',
                'default': []
            },
            'business_impact_modulations': {
                "title": "Business impact modulations",
                "comment": "Not yet implemented (#116).",
                'skill_level': 2,
                'type': 'list',
                'default': []
            },

            # todo: manage escalations
            'escalations': {
                "title": "Escalations",
                "comment": "List of the escalations applied to this element. Not yet implemented.",
                'skill_level': 2,
                'type': 'list',
                'default': [],
                'schema': {
                    'type': 'objectid',
                    'data_relation': {
                        'resource': 'hostescalation',
                        'embeddable': True,
                    }
                },
            },

            'service_overrides': {
                'skill_level': 2,
                'type': 'list',
                'default': []
            },
            'service_excludes': {
                'skill_level': 2,
                'type': 'list',
                'default': []
            },
            'service_includes': {
                'skill_level': 2,
                'type': 'list',
                'default': []
            },

            # Business rules
            # todo Business rules are not yet implemented (see #146)
            'labels': {
                "title": "BR labels",
                "comment": "Not yet implemented (#146)",
                'skill_level': 2,
                'type': 'list',
                'default': []
            },
            'business_rule_output_template': {
                "title": "BR output template",
                "comment": "Not yet implemented (#146)",
                'skill_level': 2,
                'type': 'string',
                'default': ''
            },
            'business_rule_smart_notifications': {
                "title": "BR smart notifications",
                "comment": "Not yet implemented (#146)",
                'skill_level': 2,
                'type': 'boolean',
                'default': False
            },
            'business_rule_downtime_as_ack': {
                "title": "BR downtime as ack",
                "comment": "Not yet implemented (#146)",
                'skill_level': 2,
                'type': 'boolean',
                'default': False
            },
            'business_rule_host_notification_options': {
                "title": "BR host notification options",
                "comment": "Not yet implemented (#146)",
                'skill_level': 2,
                'type': 'list',
                'default': ['d', 'u', 'r', 'f', 's'],
                'allowed': ['d', 'u', 'r', 'f', 's', 'n']
            },
            'business_rule_service_notification_options': {
                "title": "BR service notification options",
                "comment": "Not yet implemented (#146)",
                'skill_level': 2,
                'type': 'list',
                'default': ['w', 'u', 'c', 'r', 'f', 's'],
                'allowed': ['w', 'u', 'c', 'r', 'f', 's', 'n']
            },

            # Triggers
            'trigger_name': {
                "title": "Trigger name",
                "comment": "To be documented",
                'skill_level': 2,
                'type': 'string',
                'default': ''
            },
            'trigger_broker_raise_enabled': {
                "title": "Trigger broker",
                "comment": "To be documented",
                'skill_level': 2,
                'type': 'boolean',
                'default': False
            },

            # Snapshot
            'snapshot_enabled': {
                "title": "Snapshot enabled",
                'skill_level': 2,
                'type': 'boolean',
                'default': False
            },
            'snapshot_command': {
                "title": "Snapshot command",
                "comment": "Command executed for the snapshot",
                'skill_level': 2,
                'type': 'objectid',
                'data_relation': {
                    'resource': 'command',
                    'embeddable': True
                },
                'nullable': True
            },
            'snapshot_period': {
                "title": "Snapshot period",
                "comment": "Time period when the snapshot feature is active",
                'skill_level': 2,
                'type': 'objectid',
                'data_relation': {
                    'resource': 'timeperiod',
                    'embeddable': True
                },
                'nullable': True
            },
            'snapshot_criteria': {
                "title": "Snapshot criteria",
                "comment": "Execute the snapshot command when the state matches one "
                           "of the criteria",
                'skill_level': 2,
                'type': 'list',
                'default': ['d', 'x']
            },
            'snapshot_interval': {
                "title": "Snapshot interval",
                "comment": "Minimum interval between two snapshots",
                'skill_level': 2,
                'type': 'integer',
                'default': 5
            },

            # Host live state fields are prefixed with ls_
            # Make this field consistent with the initial_state...
            'ls_state': {
                "title": "State",
                "comment": "Current state",
                'type': 'string',
                'default': 'UNREACHABLE',
                'allowed': ["PENDING", "UP", "DOWN", "UNREACHABLE"]
            },
            'ls_state_type': {
                "title": "State type",
                "comment": "Current state type",
                'type': 'string',
                'default': 'HARD',
                'allowed': ["HARD", "SOFT"]
            },
            'ls_state_id': {
                "title": "State identifier",
                "comment": "Current state identifier. "
                           "O: UP, 1: DOWN, 2: UNREACHABLE",
                'type': 'integer',
                'default': 3,
                'allowed': [0, 1, 2, 3]
            },
            'ls_acknowledged': {
                "title": "Acknowledged",
                "comment": "Currently acknowledged",
                'type': 'boolean',
                'default': False
            },
            'ls_acknowledgement_type': {
                "title": "Acknowledgement type",
                "comment": "",
                'type': 'integer',
                'default': 1
            },
            'ls_downtimed': {
                "title": "Downtimed",
                "comment": "Currently downtimed",
                'type': 'boolean',
                'default': False
            },
            'ls_impact': {
                "title": "Impact",
                "comment": "Is an impact?",
                'type': 'boolean',
                'default': False
            },
            'ls_last_check': {
                "title": "Check timestamp",
                "comment": "Last check timestamp",
                'type': 'integer',
                'default': 0
            },
            'ls_last_state': {
                "title": "Last state",
                "comment": "Former state",
                'type': 'string',
                'default': 'UNREACHABLE',
                'allowed': ["PENDING", "UP", "DOWN", "UNREACHABLE"]
            },
            'ls_last_state_type': {
                "title": "Last state type",
                "comment": "Former state type",
                'type': 'string',
                'default': 'HARD',
                'allowed': ["HARD", "SOFT"]
            },
            'ls_last_state_changed': {
                "title": "Last state changed",
                "comment": "Last state changed timestamp",
                'type': 'integer',
                'default': 0
            },
            'ls_next_check': {
                "title": "Next check",
                "comment": "Next check timestamp",
                'type': 'integer',
                'default': 0
            },

            'ls_output': {
                "title": "Output",
                "comment": "Last check output",
                'type': 'string',
                'default': ''
            },
            'ls_long_output': {
                "title": "Long output",
                "comment": "Last check long output",
                'type': 'string',
                'default': ''
            },
            'ls_perf_data': {
                "title": "Performance data",
                "comment": "Last check performance data",
                'type': 'string',
                'default': ''
            },

            'ls_current_attempt': {
                "title": "Current attempt number",
                "comment": "",
                'type': 'integer',
                'default': 0
            },
            'ls_max_attempts': {
                "title": "Maximum attempts",
                "comment": "",
                'type': 'integer',
                'default': 0
            },
            'ls_latency': {
                "title": "Latency",
                "comment": "Last check latency",
                'type': 'float',
                'default': 0.0
            },
            'ls_execution_time': {
                "title": "Execution time",
                "comment": "Last check execution time",
                'type': 'float',
                'default': 0.0
            },

            'ls_passive_check': {
                "title": "Check type",
                "comment": "Last check was active or passive?",
                'type': 'boolean',
                'default': False
            },

            # todo - Attempt number - difference with ls_current_attemp?
            'ls_attempt': {
                "title": "Current attempt number",
                "comment": "",
                'type': 'integer',
                'default': 0
            },

            # Last time hard state changed
            'ls_last_hard_state_changed': {
                "title": "Last time hard state changed",
                "comment": "Last time this element hard state has changed.",
                'type': 'integer',
                'default': 0
            },

            # Last time in the corresponding state
            'ls_last_time_up': {
                "title": "Last time up",
                "comment": "Last time this element was Up.",
                'type': 'integer',
                'default': 0
            },
            'ls_last_time_down': {
                "title": "Last time down",
                "comment": "Last time this element was Down.",
                'type': 'integer',
                'default': 0
            },
            'ls_last_time_unknown': {
                "title": "Last time unknown",
                "comment": "Last time this element was Unknown.",
                'type': 'integer',
                'default': 0
            },
            'ls_last_time_unreachable': {
                "title": "Last time unreachable",
                "comment": "Last time this element was Unreachable.",
                'type': 'integer',
                'default': 0
            },

            'ls_grafana': {
                "title": "Grafana available",
                "comment": "This element has a Grafana panel available",
                'type': 'boolean',
                'default': False
            },
            'ls_grafana_panelid': {
                "title": "Grafana identifier",
                "comment": "Grafana panel identifier",
                'type': 'integer',
                'default': 0
            },

            'ls_last_notification': {
                "title": "Last notification sent",
                "comment": "",
                'type': 'integer',
                'default': 0
            },

            # Host computed overall state identifier
            '_overall_state_id': {
                "title": "Element overall state",
                "comment": "The overall state is a synthesis state that considers the element "
                           "state, its acknowledgement, its downtime and its children states.",
                'type': 'integer',
                'default': 3
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

            # Templates
            '_is_template': {
                "title": "Template",
                "comment": "Indicate if this element is a template or a real element",
                'type': 'boolean',
                'default': False
            },
            '_templates': {
                "title": "Templates",
                "comment": "List of templates this element is linked to.",
                'type': 'list',
                'schema': {
                    'type': 'objectid',
                    'data_relation': {
                        'resource': 'host',
                        'embeddable': True,
                    }
                },
                'default': []
            },
            '_templates_with_services': {
                "title": "Template services",
                "comment": "If this element is a template, when a new element is created based "
                           "upon this template, it will also inherit from the linked services "
                           "templates of this template.",
                'type': 'boolean',
                'default': True
            },
            '_template_fields': {
                "title": "Template fields",
                "comment": "If this element is not a template, this field contains the list of "
                           "the fields linked to the templates this element is linked to",
                'type': 'dict',
                'default': {}
            },
        }
    }
