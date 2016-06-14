# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ironicclient.exc
from oslo_log import log as logging

from searchlight.elasticsearch.plugins import base
from searchlight.elasticsearch.plugins.ironic \
    import serialize_ironic_node
from searchlight import i18n


LOG = logging.getLogger(__name__)
_LW = i18n._LW
_LE = i18n._LE


class NodeHandler(base.NotificationBase):

    def __init__(self, *args, **kwargs):
        super(NodeHandler, self).__init__(*args, **kwargs)

    # TODO: where is it used?
    @classmethod
    def _get_notification_exchanges(cls):
        return ['ironic']

    def get_event_handlers(self):
        return {
            "node.create": self.create_or_update
        }

    def create_or_update(self, payload, timestamp):
        node_id = payload['id']
        try:
            payload = serialize_ironic_node(payload)
            self.index_helper.save_document(
                payload,
                version=self.get_version(payload, timestamp))
        except ironicclient.exceptions.NotFound:
            LOG.warning(_LW("Node %s not found; deleting") % node_id)
            try:
                self.index_helper.delete_document({'_id': node_id})
            except Exception as exc:
                LOG.error(_LE(
                    'Error deleting node %(image_id)s from index: %(exc)s') %
                    {'image_id': node_id, 'exc': exc})
