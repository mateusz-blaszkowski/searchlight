# Copyright 2015 Hewlett-Packard Corporation
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

import copy
from elasticsearch import exceptions as es_exc
from elasticsearch import helpers
import logging
from oslo_utils import fnmatch
import six

from searchlight.elasticsearch import ROLE_USER_FIELD
from searchlight import i18n

# Refer to ROLE_USER_FIELD
ADMIN_ID_SUFFIX = "_ADMIN"
USER_ID_SUFFIX = "_USER"

# String from Alias Failure Exception. See _is_multiple_alias_exception().
ALIAS_EXCEPTION_STRING = "has more than one indices associated with it"

DOC_VALUE_TYPES = ('long', 'integer', 'short', 'boolean', 'byte',
                   'double', 'float', 'date', 'binary', 'geo_point', 'ip')

LOG = logging.getLogger(__name__)
_LW = i18n._LW
_LE = i18n._LE


class IndexingHelper(object):
    """Class to abstract away some of the details of indexing documents
    including versioning, parent-child links and separation by role.

    Role separation is reasonably simple; documents with admin-only fields
    will be indexed twice, once for admins and once for normal users, with some
    fields excluded for the second case. The document IDs use the suffixes
    defined in ADMIN_ID_SUFFIX and USER_ID_SUFFIX.

    In the case of parent child relationships things are more complicated. The
    ids in that case follow these rules:
    * parent is role separated
      * child is role separated: the _USER and _ADMIN docs each refer to a
            parent with the same suffix
      * child is NOT separated: this case is not encouraged, but where it
            exists the child documents will use the _USER parent document as
            their _parent to avoid security issues with has_parent query
            fishing
    * parent is not role separated
      * child is role separated: both child docs will use the parent id
            without any prefix
      * child is not role separated: the simple case; no suffix in either
            case
    """

    def __init__(self, plugin):
        self.plugin = plugin

        # Retain some state here for convenience
        self.engine = self.plugin.engine
        self.alias_name = plugin.alias_name_listener
        self.document_type = plugin.document_type

    @property
    def index_chunk_size(self):
        return 200

    def _index_alias_multiple_indexes_bulk(self, documents=None, actions=None,
                                           versions=None):
        """A bulk operation failed by trying to access an alias that has
           multiple indexes. To rememdy this we will need to iterate on all
           indexes within the alias and retry the bulk operation individually.
        """
        indexes = self.engine.indices.get_alias(index=self.alias_name)
        for index_name in indexes:
            try:
                if documents:
                    result = helpers.bulk(
                        client=self.engine,
                        index=index_name,
                        doc_type=self.document_type,
                        chunk_size=self.index_chunk_size,
                        actions=self._prepare_actions(documents,
                                                      versions))
                if actions:
                    result = helpers.bulk(
                        client=self.engine,
                        index=index_name,
                        doc_type=self.document_type,
                        chunk_size=self.index_chunk_size,
                        actions=actions)
                LOG.debug("Indexing result: %s", result)
            except Exception as e:
                # Log the error and continue to the next index.
                format_msg = {
                    'doc': self.document_type,
                    'msg': str(e)
                }
                LOG.error(_LE("Failed Indexing %(doc)s: %(msg)s") % format_msg)

    def _index_alias_multiple_indexes_get(self, doc_id, routing=None):
        """Getting a document from an alias with multiple indexes will fail.
           We need to retrive it from one of the indexes. We will choose
           the latest index. Since the indexes are named with a timestamp,
           a reverse sort will bring the latest to the front.
        """
        indexes = self.engine.indices.get_alias(index=self.alias_name)
        index_list = indexes.keys()
        index_list.sort(reverse=True)
        try:
            if routing:
                return self.engine.get(
                    index=index_list[0],
                    doc_type=self.document_type,
                    id=doc_id,
                    routing=routing
                )
            else:
                return self.engine.get(
                    index=index_list[0],
                    doc_type=self.document_type,
                    id=doc_id
                )
        except Exception as e:
            format_msg = {
                'doc': self.document_type,
                'msg': str(e)
            }
            LOG.error(_LE("Failed Indexing %(doc)s: %(msg)s") % format_msg)

    def save_document(self, document, version=None):
        if version:
            self.save_documents([document], [version])
        else:
            self.save_documents([document])

    def save_documents(self, documents, versions=None, index=None):
        """Send list of serialized documents into search engine.

           Warning: Index vs Alias usage.
           Listeners [plugins/*/notification_handlers.py]:
           When the plugin listeners are indexing documents, we will want
           to use the normal ES alias for their resource group. In this case
           the index parameter will not be set. Listeners are by far the most
           common usage case.

           Re-Indexing [plugins/base.py::initial_indexing()]:
           When we are re-indexing we will want to use the new ES index.
           Bypassing the alias means we will not send duplicate documents
           to the old index. In this case the index will be set. Re-indexing
           is an event that will rarely happen.
        """
        if not index:
            use_index = self.alias_name
        else:
            use_index = index

        try:
            result = helpers.bulk(
                client=self.engine,
                index=use_index,
                doc_type=self.document_type,
                chunk_size=self.index_chunk_size,
                actions=self._prepare_actions(documents, versions))
        except helpers.BulkIndexError as e:
            err_msg = []
            for err in e.errors:
                if "VersionConflict" not in err['index']['error']:
                    raise e
                err_msg.append("id %(_id)s: %(error)s" % err['index'])
            LOG.warning(_LW('Version conflict %s') % ';'.join(err_msg))
            result = 0
        except es_exc.RequestError as e:
            if _is_multiple_alias_exception(e):
                LOG.error(_LE("Alias [%(a)s] with multiple indexes error") %
                          {'a': self.alias_name})
                self._index_alias_multiple_indexes_bulk(documents=documents,
                                                        versions=versions)

            result = 0
        LOG.debug("Indexing result: %s", result)

    def delete_document(self, document):
        """'document' must contain an '_id', but can include '_parent',
        '_version' and '_routing', each of which will be passed to
        the bulk helper
        """
        self.delete_documents([document])

    def delete_documents(self, metadocs, override_role_separation=False):
        """Each metadoc should be a dict with at an _id, and if
         applicable, a _parent. override_role_separation will treat the _ids
         and _parents in the documents as their actual indexed values
         rather than determining role separation
         """
        def _get_delete_action(doc, id_suffix=''):
            action = {'_op_type': 'delete', '_id': doc['_id'] + id_suffix}

            if doc.get('_version'):
                action['_version'] = doc['_version']
                action['_version_type'] = 'external'

            parent_entity_id = doc.get('_parent')
            if parent_entity_id:
                if (not override_role_separation and
                        self.plugin.parent_plugin.requires_role_separation):
                    # Default to _USER; defaulting to _ADMIN causes a
                    # security issue because of potential fishing queries
                    parent_entity_id += (id_suffix or USER_ID_SUFFIX)
                action['_parent'] = parent_entity_id
            if '_routing' in doc:
                action['_routing'] = doc['_routing']
            return action

        actions = []
        for metadoc in metadocs:
            if (not override_role_separation and
                    self.plugin.requires_role_separation):
                actions.extend([
                    _get_delete_action(metadoc, ADMIN_ID_SUFFIX),
                    _get_delete_action(metadoc, USER_ID_SUFFIX)])
            else:
                actions.append(_get_delete_action(metadoc))

        try:
            helpers.bulk(
                client=self.plugin.engine,
                index=self.alias_name,
                doc_type=self.document_type,
                actions=actions
            )
        except helpers.BulkIndexError as exc:
            exc_payload = exc.errors
            doc_ids = ', '.join(e['delete']['_id'] for e in exc_payload)

            if all(e['delete']['status'] == 404 for e in exc_payload):
                LOG.warning(
                    _LW("Error deleting %(doc_type)s %(ids)s; "
                        "already deleted") %
                    {"doc_type": self.plugin.document_type, "ids": doc_ids})

            elif all(e['delete']['status'] == 409 for e in exc_payload):
                # This *should* never happen. If it does, something has gone
                # wrong but leaving this here for now
                LOG.warning(
                    _LW("Error deleting %(doc_type)s %(ids)s; newer versions "
                        "of some documents have been indexed") %
                    {"doc_type": self.plugin.document_type, "ids": doc_ids})
            else:
                raise
        except es_exc.RequestError as e:
            if _is_multiple_alias_exception(e):
                LOG.error(_LE("Alias [%(a)s] with multiple indexes error") %
                          {'a': self.alias_name})
                self._index_alias_multiple_indexes_bulk(actions=actions)

    def delete_documents_with_parent(self, parent_id, version=None):
        # This is equivalent in result to _parent: parent_id but offers
        # a significant performance boost because of the implementation
        # of _parent filtering
        parent_type = self.plugin.parent_plugin_type()

        # It's easier to retrieve the actual parent id here because otherwise
        # we have to figure out role separation. _parent is (in 1.x) not
        # return by default and has to be requested in 'fields'
        query = {
            'fields': ['_parent', '_routing']
        }

        if (self.plugin.parent_plugin and
                self.plugin.parent_plugin.requires_role_separation):
            # There will be documents with the _USER suffix; there may also
            # be those with _ADMIN suffixes if this plugin type is separated
            full_parent_ids = [
                '%s#%s%s' % (parent_type, parent_id, ADMIN_ID_SUFFIX),
                '%s#%s%s' % (parent_type, parent_id, USER_ID_SUFFIX)
            ]
            query['query'] = {'terms': {'_parent': full_parent_ids}}
        else:
            full_parent_id = '%s#%s' % (parent_type, parent_id)
            query['query'] = {'term': {'_parent': full_parent_id}}

        documents = helpers.scan(
            client=self.engine,
            index=self.alias_name,
            doc_type=self.document_type,
            query=query)

        to_delete = [
            {'_id': doc['_id'], '_parent': doc['fields']['_parent'],
             '_routing': doc['fields']['_routing']}
            if '_routing' in doc['fields']
            else {'_id': doc['_id'], '_parent': doc['fields']['_parent']}
            for doc in documents]

        # Use the parent version tag; we're instructing elasticsearch to mark
        # all the deleted child documents as 'don't apply updates received
        # after 'version' so the fact that they don't match the child
        # 'updated_at' fields is irrelevant
        if version:
            for action in to_delete:
                action['_version'] = version

        self.delete_documents(to_delete, override_role_separation=True)

    def get_document(self, doc_id, for_admin=False, routing=None):
        if self.plugin.requires_role_separation:
            doc_id += (ADMIN_ID_SUFFIX if for_admin else USER_ID_SUFFIX)

        try:
            if routing:
                return self.engine.get(
                    index=self.alias_name,
                    doc_type=self.document_type,
                    id=doc_id,
                    routing=routing
                )
            else:
                return self.engine.get(
                    index=self.alias_name,
                    doc_type=self.document_type,
                    id=doc_id
                )
        except es_exc.RequestError:
            # TODO(ricka) Verify this is the IllegalArgument exception.
            LOG.error(_LE("Alias [%(alias)s] with multiple indexes error") %
                      {'alias': self.alias_name})
            #
            return self._index_alias_multiple_indexes_get(
                doc_id=doc_id, routing=routing)

    def update_document(self, document, doc_id, update_as_script):
        """Updates are a little simpler than inserts because the documents
        already exist. Note that scripted updates are not filtered in the same
        way as partial document updates. Script updates should be passed as
        a dict {"script": .., "parameters": ..}. Partial document updates
        should be the raw document.
        """
        def _get_update_action(source, id_suffix=''):
            action = {'_id': doc_id + id_suffix, '_op_type': 'update'}
            if update_as_script:
                action.update(source)
            else:
                action['doc'] = source

            routing_field = self.plugin.routing_field
            if routing_field:
                action['_routing'] = source[routing_field]

            return action

        if self.plugin.requires_role_separation:
            user_doc = (self._remove_admin_fields(document)
                        if update_as_script else document)
            actions = [_get_update_action(document, ADMIN_ID_SUFFIX),
                       _get_update_action(user_doc, USER_ID_SUFFIX)]
        else:
            actions = [_get_update_action(document)]
        try:
            result = helpers.bulk(
                client=self.engine,
                index=self.alias_name,
                doc_type=self.document_type,
                chunk_size=self.index_chunk_size,
                actions=actions)
            LOG.debug("Update result: %s", result)
        except es_exc.RequestError as e:
            if _is_multiple_alias_exception(e):
                LOG.error(_LE("Alias [%(a)s] with multiple indexes error") %
                          {'a': self.alias_name})
                self._index_alias_multiple_indexes_bulk(actions=actions)

    def _prepare_actions(self, documents, versions=None):
        """Returns a generator of indexable 'actions'. If the plugin requires
        role-based separation, two actions will be yielded per document,
        otherwise one. _id and USER_ROLE_FIELD are set as appropriate
        """
        def _get_index_action(source, version=None, id_suffix=''):
            """Return an 'action' the ES bulk indexer understands"""
            action = {
                '_id': source[self.plugin.get_document_id_field()] + id_suffix,
                '_source': source,
                '_op_type': 'index'
            }
            if version:
                action['_version_type'] = 'external'
                action['_version'] = version

            parent_field = self.plugin.get_parent_id_field()
            routing_field = self.plugin.routing_field
            if parent_field:
                parent_id = source[parent_field]
                if self.plugin.parent_plugin.requires_role_separation:
                    # Default to _USER; defaulting to _ADMIN causes a
                    # security issue because of potential fishing queries
                    parent_id += (id_suffix or USER_ID_SUFFIX)
                action['_parent'] = parent_id
            if routing_field:
                action['_routing'] = source[routing_field]
            return action

        for index, document in enumerate(documents):
            # Although elasticsearch copies the input when indexing, it's
            # easier from a debugging and testing perspective not to meddle
            # with the input, so make a copy
            document = copy.deepcopy(document)
            version = versions[index] if versions else None
            if self.plugin.requires_role_separation:
                LOG.debug("Applying role separation to %s id %s" %
                          (self.plugin.name,
                           document[self.plugin.get_document_id_field()]))
                document[ROLE_USER_FIELD] = 'admin'
                yield _get_index_action(document,
                                        version=version,
                                        id_suffix=ADMIN_ID_SUFFIX)

                user_doc = self._remove_admin_fields(document)
                user_doc[ROLE_USER_FIELD] = 'user'
                yield _get_index_action(user_doc,
                                        version=version,
                                        id_suffix=USER_ID_SUFFIX)

            else:
                LOG.debug("Not applying role separation to %s id %s" %
                          (self.plugin.name,
                           document[self.plugin.get_document_id_field()]))
                document[ROLE_USER_FIELD] = ['user', 'admin']
                yield _get_index_action(document, version=version)

    def _remove_admin_fields(self, document):
        """Prior to indexing, remove any fields that shouldn't be indexed
        and available to users who do not have administrative privileges.
        Returns a copy of the document even if there's nothing to remove.
        """
        sanitized_document = {}
        for k, v in six.iteritems(document):
            # Only return a field if it doesn't have ANY matches against
            # admin_only_fields
            if not any(fnmatch.fnmatch(k, field)
                       for field in self.plugin.admin_only_fields):
                sanitized_document[k] = v

        return sanitized_document

    @classmethod
    def apply_doc_values(cls, mapping):
        """Sets 'doc_values' on fields in a mapping which allows queries to be
        run on fields directly off disk, saving memory in analysis operations.
        Currently all fields with the exception of analyzed strings can be set
        as doc_values. Elasticsearch 2.x will make doc_values the default.
        """
        def apply_doc_values(field_def):
            if field_def.get('type', 'object') in ('nested', 'object'):
                for _, nested_def in six.iteritems(field_def['properties']):
                    apply_doc_values(nested_def)
            else:
                if 'doc_values' not in field_def:
                    if field_def['type'] in DOC_VALUE_TYPES:
                        field_def['doc_values'] = True
                    elif (field_def['type'] == 'string' and
                          field_def.get('index', '') == 'not_analyzed'):
                        field_def['doc_values'] = True

                for _, multidef in six.iteritems(field_def.get('fields', {})):
                    apply_doc_values(multidef)

        # Check dynamic templates. These are a list of dicts each with a single
        # key (the template name) and a mapping definition
        for dynamic_template in mapping.get('dynamic_templates', []):
            for dyn_field, dyn_mapping in six.iteritems(dynamic_template):
                apply_doc_values(dyn_mapping['mapping'])

        for field, definition in six.iteritems(mapping['properties']):
            apply_doc_values(definition)


def _is_multiple_alias_exception(e):
    """Verify that this exception is specifically the IllegalArgument
       exception when there are multiple indexes for an alias. There
       is no clean way of verifying this is the case. There are multiple
       ES RequestError exceptions that return a 400 IllegalArgument.
       In this particular case, we are expecting a message in the
       exception like this:

           ElasticsearchIllegalArgumentException[Alias [alias] has more
           than one indices associated with it [[idx1, idx2]], can't
           execute a single index op]

       We will be dirty and parse the exception message. We need to
       check the validity of ALIAS_EXCPTION_STRING in future
       ElasticSearch versions.
    """
    if ALIAS_EXCEPTION_STRING in getattr(e, 'error', ''):
        # Elasticsearch 1.x
        return True

    # ES 2 - the error info's in e.info.error.reason
    exc_info_error = getattr(e, 'info', {}).get('error', {})
    if ALIAS_EXCEPTION_STRING in exc_info_error.get('reason', ''):
        return True

    return False
