# Copyright (c) 2016 Hewlett-Packard Enterprise Development Company, L.P.
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


BLACKLISTED_FIELDS = set((u'links', u'manager', '_loaded', '_info'))


def serialize_cinder_volume(volume):
    """volume can be an id or a 'volume' object from cinderclient"""
    if isinstance(volume, six.string_types):
        cinder_client = openstack_clients.get_cinderclient()
        volume = cinder_client.volumes.get(volume)

    LOG.debug("Serializing volume %s for project %s",
              volume.id, volume.user_id)

    serialized = {k: v for k, v in six.iteritems(volume.__dict__)
                  if k not in BLACKLISTED_FIELDS}

    project_id = serialized.get('os-vol-tenant-attr:tenant_id')
    if 'tenant_id' not in serialized:
        serialized['tenant_id'] = project_id
    if 'project_id' not in serialized:
        serialized['project_id'] = project_id

    return serialized


def serialize_cinder_snapshot(snapshot):
    """snapshot can be an id or a 'Snapshot' object from cinderclient"""
    if isinstance(snapshot, six.string_types):
        cinder_client = openstack_clients.get_cinderclient()
        snapshot = cinder_client.volume_snapshots.get(snapshot)

    project_id = getattr(snapshot,
                         'os-extended-snapshot-attributes:project_id')
    LOG.debug("Serializing snapshot %s for project %s",
              snapshot.id, project_id)

    serialized = {k: v for k, v in six.iteritems(snapshot.__dict__)
                  if k not in BLACKLISTED_FIELDS}

    if 'tenant_id' not in serialized:
        serialized['tenant_id'] = project_id
    if 'project_id' not in serialized:
        serialized['project_id'] = project_id

    return serialized
