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

    def get_document_id_field(self):
        return 'uuid'

    @property
    def facets_with_options(self):
        return ('driver')

    def _get_rbac_field_filters(self, request_context):
        return []

    def get_mapping(self):
        return {
            'dynamic': True,
            'properties': {
                'uuid': {'type': 'string', 'index': 'not_analyzed'},
                'driver': {'type': 'string', 'index': 'not_analyzed'}
            }
        }

    def get_objects(self):
        from searchlight.elasticsearch.plugins import openstack_clients
        return openstack_clients.get_ironicclient().node.list(detail=True)

    def serialize(self, obj):
        return serialize_ironic_node(obj)
