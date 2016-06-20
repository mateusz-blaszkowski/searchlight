# Copyright 2015 Intel Corporation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from searchlight.api import policy
from searchlight.common import property_utils
from searchlight.common import resource_types
from searchlight.elasticsearch.plugins import base
from searchlight.elasticsearch.plugins.ironic \
    import nodes_notification_handler
from searchlight.elasticsearch.plugins.ironic \
    import serialize_ironic_node


class NodeIndex(base.IndexBase):
    NotificationHandlerCls = nodes_notification_handler.NodeHandler

    def __init__(self, policy_enforcer=None):
        super(NodeIndex, self).__init__()
        self.policy = policy_enforcer or policy.Enforcer()
        if property_utils.is_property_protection_enabled():
            self.property_rules = property_utils.PropertyRules(self.policy)

    @classmethod
    def get_document_type(cls):
        return resource_types.IRONIC_NODE

    @classmethod
    def get_plugin_name(cls):
        return 'Node'

    def get_document_id_field(self):
        return 'uuid'

    @property
    def facets_with_options(self):
        return ('console_enabled', 'driver', 'driver_info.ipmi_username',
                'extra.health', 'extra.model', 'extra.type',
                'extra.manufacturer', 'maintenance', 'power_state',
                'properties.cpu_arch', 'properties.capabilities',
                'provision_state',
                'extra.interfaces.iface_0.local_link_connection.switch_info',
                'extra.interfaces.iface_0.pxe_enabled',
                'extra.interfaces.iface_1.local_link_connection.switch_info',
                'extra.interfaces.iface_1.pxe_enabled',
                'extra.interfaces.iface_2.local_link_connection.switch_info',
                'extra.interfaces.iface_2.pxe_enabled',
                'extra.interfaces.iface_3.local_link_connection.switch_info',
                'extra.interfaces.iface_3.pxe_enabled',
                'extra.interfaces.iface_4.local_link_connection.switch_info',
                'extra.interfaces.iface_4.pxe_enabled',
                'extra.interfaces.iface_5.local_link_connection.switch_info',
                'extra.interfaces.iface_5.pxe_enabled')

    def _get_rbac_field_filters(self, request_context):
        return []

    def get_mapping(self):
        return {
            'dynamic': True,
            'properties': {
                'clean_step': {'type': 'string'},
                'console_enabled': {'type': 'boolean'},
                'created_at': {'type': 'date'},
                'driver': {'type': 'string', 'index': 'not_analyzed'},
                'driver_info': {
                    'type': 'nested',
                    'properties': {
                        'deploy_kernel': {
                            'type': 'string',
                            'index': 'not_analyzed'
                        },
                        'deploy_ramdisk': {
                            'type': 'string',
                            'index': 'not_analyzed'
                        },
                        'ipmi_address': {
                            'type': 'string'
                        },
                        'ipmi_terminal_port': {
                            'type': 'long'
                        },
                        'ipmi_username': {
                            'type': 'string'
                        }
                    }
                },
                'extra': {
                    'type': 'nested',
                    'properties': {
                        'health': {
                            'type': 'string',
                            'index': 'not_analyzed'
                        },
                        'serial_number': {
                            'type': 'string',
                            'index': 'not_analyzed'
                        },
                        'model': {
                            'type': 'string',
                            'index': 'not_analyzed'
                        },
                        'type': {
                            'type': 'string',
                            'index': 'not_analyzed'
                        },
                        'rack': {
                            'type': 'string',
                            'index': 'not_analyzed'
                        },
                        'unit': {
                            'type': 'string',
                            'index': 'not_analyzed'
                        },
                        'manufacturer': {
                            'type': 'string',
                            'index': 'not_analyzed'
                        },
                        'interfaces': {
                            'type': 'nested',
                            'properties': {
                                'iface_0': {
                                    'type': 'nested',
                                    'properties': {
                                        'pxe_enabled': {'type': 'boolean'},
                                        'address': {'type': 'string'},
                                        'local_link_connection': {
                                            'type': 'nested',
                                            'properties': {
                                                'switch_info': {
                                                    'type': 'string',
                                                    'index': 'not_analyzed'
                                                },
                                                'port_id': {
                                                    'type': 'string',
                                                    'index': 'not_analyzed'
                                                },
                                                'switch_id': {
                                                    'type': 'string',
                                                    'index': 'not_analyzed'
                                                }
                                            }
                                        }
                                    }
                                },
                                'iface_1': {
                                    'type': 'nested',
                                    'properties': {
                                        'pxe_enabled': {'type': 'boolean'},
                                        'address': {'type': 'string'},
                                        'local_link_connection': {
                                            'type': 'nested',
                                            'properties': {
                                                'switch_info': {
                                                    'type': 'string',
                                                    'index': 'not_analyzed'
                                                },
                                                'port_id': {
                                                    'type': 'string',
                                                    'index': 'not_analyzed'
                                                },
                                                'switch_id': {
                                                    'type': 'string',
                                                    'index': 'not_analyzed'
                                                }
                                            }
                                        }
                                    }
                                },
                                'iface_2': {
                                    'type': 'nested',
                                    'properties': {
                                        'pxe_enabled': {'type': 'boolean'},
                                        'address': {'type': 'string'},
                                        'local_link_connection': {
                                            'type': 'nested',
                                            'properties': {
                                                'switch_info': {
                                                    'type': 'string',
                                                    'index': 'not_analyzed'
                                                },
                                                'port_id': {
                                                    'type': 'string',
                                                    'index': 'not_analyzed'
                                                },
                                                'switch_id': {
                                                    'type': 'string',
                                                    'index': 'not_analyzed'
                                                }
                                            }
                                        }
                                    }
                                },
                                'iface_3': {
                                    'type': 'nested',
                                    'properties': {
                                        'pxe_enabled': {'type': 'boolean'},
                                        'address': {'type': 'string'},
                                        'local_link_connection': {
                                            'type': 'nested',
                                            'properties': {
                                                'switch_info': {
                                                    'type': 'string',
                                                    'index': 'not_analyzed'
                                                },
                                                'port_id': {
                                                    'type': 'string',
                                                    'index': 'not_analyzed'
                                                },
                                                'switch_id': {
                                                    'type': 'string',
                                                    'index': 'not_analyzed'
                                                }
                                            }
                                        }
                                    }
                                },
                                'iface_4': {
                                    'type': 'nested',
                                    'properties': {
                                        'pxe_enabled': {'type': 'boolean'},
                                        'address': {'type': 'string'},
                                        'local_link_connection': {
                                            'type': 'nested',
                                            'properties': {
                                                'switch_info': {
                                                    'type': 'string',
                                                    'index': 'not_analyzed'
                                                },
                                                'port_id': {
                                                    'type': 'string',
                                                    'index': 'not_analyzed'
                                                },
                                                'switch_id': {
                                                    'type': 'string',
                                                    'index': 'not_analyzed'
                                                }
                                            }
                                        }
                                    }
                                },
                                'iface_5': {
                                    'type': 'nested',
                                    'properties': {
                                        'pxe_enabled': {'type': 'boolean'},
                                        'address': {'type': 'string'},
                                        'local_link_connection': {
                                            'type': 'nested',
                                            'properties': {
                                                'switch_info': {
                                                    'type': 'string',
                                                    'index': 'not_analyzed'
                                                },
                                                'port_id': {
                                                    'type': 'string',
                                                    'index': 'not_analyzed'
                                                },
                                                'switch_id': {
                                                    'type': 'string',
                                                    'index': 'not_analyzed'
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                'instance_info': {
                    'type': 'nested',
                    'properties': {
                        'display_name': {
                            'type': 'string', 'index': 'not_analyzed'
                        },
                        'image_source': {
                            'type': 'string', 'index': 'not_analyzed'
                        },
                        'image_type': {
                            'type': 'string', 'index': 'not_analyzed'
                        },
                        'local_gb': {'type': 'long'},
                        'memory_mb': {'type': 'long'},
                        'root_gb': {'type': 'long'},
                        'vcpus': {'type': 'long'},
                    }
                },
                'instance_uuid': {'type': 'string', 'index': 'not_analyzed'},
                'last_error': {'type': 'string'},
                'maintenance': {'type': 'boolean'},
                'maintenance_reason': {'type': 'string'},
                'name': {
                    'type': 'string',
                    'fields': {
                        'raw': {'type': 'string', 'index': 'not_analyzed'}
                    }
                },
                'power_state': {'type': 'string', 'index': 'not_analyzed'},
                'properties': {
                    'type': 'nested',
                    'properties': {
                        'cpu_arch': {'type': 'string', 'index': 'not_analyzed'},
                        'cpus': {'type': 'string'},
                        'memory_mb': {'type': 'long'},
                        'local_gb': {'type': 'long'},
                        'capabilities': {'type': 'string'}
                    }
                },
                'provision_state': {'type': 'string', 'index': 'not_analyzed'},
                'provision_updated_at': {'type': 'date'},
                'updated_at': {'type': 'date'},
                'uuid': {'type': 'string', 'index': 'not_analyzed'}
            }
        }

    def get_objects(self):
        return []

    def serialize(self, obj):
        return serialize_ironic_node(obj)
