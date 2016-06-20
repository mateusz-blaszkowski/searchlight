# Copyright (c) 2015 Hewlett-Packard Development Company, L.P.
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

import logging
import six

from searchlight.elasticsearch.plugins import openstack_clients
from searchlight import i18n

LOG = logging.getLogger(__name__)
_ = i18n._
_LW = i18n._LW


def serialize_ironic_node(node):

    # If we're being asked to index an ID, retrieve the full node information
    if isinstance(node, six.text_type):
        # TODO: test this
        ironic_client = openstack_clients.get_ironicclient()
        node = ironic_client.node.get(node)

    document = node.to_dict()
    return _ignore_node_fields(document)


def serialize_ironic_port(port):

    # If we're being asked to index an ID, retrieve the full node information
    if isinstance(port, six.text_type):
        # TODO: test this
        ironic_client = openstack_clients.get_ironicclient()
        port = ironic_client.port.get(port)

    document = port.to_dict()
    return _ignore_port_fields(document)


def _ignore_port_fields(document):
    fields_to_ignore = ['links']
    document = {k: v for k, v in document.iteritems()
                if k not in fields_to_ignore}
    return document


def _ignore_node_fields(document):

    instance_info = document.get('instance_info', {})
    driver_info = document.get('driver_info', {})

    # TODO: track Ironic ports as separate objects
    fields_to_ignore = ['instance_info', 'links', 'clean_step', 'ports',
                        'driver_internal_info']
    instance_fields_to_ignore = ['configdrive', 'image_url']
    driver_info_fields_to_ignore = ['ipmi_password']

    document = {k: v for k, v in document.iteritems()
                if k not in fields_to_ignore}
    document['instance_info'] = {k: v for k, v in instance_info.iteritems()
                                 if k not in instance_fields_to_ignore}
    document['driver_info'] = {k: v for k, v in driver_info.iteritems()
                               if k not in driver_info_fields_to_ignore}

    return document
