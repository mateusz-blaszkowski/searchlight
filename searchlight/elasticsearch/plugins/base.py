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

import abc

from elasticsearch import helpers
import six

import searchlight.elasticsearch


@six.add_metaclass(abc.ABCMeta)
class IndexBase(object):
    chunk_size = 200

    def __init__(self):
        self.engine = searchlight.elasticsearch.get_api()
        self.index_name = self.get_index_name()
        self.document_type = self.get_document_type()
        self.document_id_field = self.get_document_id_field()
        self.name = "%s-%s" % (self.index_name, self.document_type)

    def initial_indexing(self, clear=True):
        """Comprehensively install search engine index and put data into it."""
        if clear:
            # First delete the doc type
            self.clear_data()

        self.setup_index()
        self.setup_mapping()
        self.setup_data()

    def clear_data(self):
        type_exists = (self.engine.indices.exists(self.index_name) and
                       self.engine.indices.exists_type(self.index_name,
                                                       self.document_type))
        if type_exists:
            self.engine.indices.delete_mapping(self.index_name,
                                               self.document_type)

    def setup_index(self):
        """Create the index if it doesn't exist and update its settings."""
        index_exists = self.engine.indices.exists(self.index_name)
        if not index_exists:
            self.engine.indices.create(index=self.index_name)

        index_settings = self.get_settings()
        if index_settings:
            self.engine.indices.put_settings(index=self.index_name,
                                             body=index_settings)

        return index_exists

    def setup_mapping(self):
        """Update index document mapping."""
        index_mapping = self.get_mapping()

        if index_mapping:
            self.engine.indices.put_mapping(index=self.index_name,
                                            doc_type=self.document_type,
                                            body=index_mapping)

    def setup_data(self):
        """Insert all objects from database into search engine."""
        object_list = self.get_objects()
        documents = []
        for obj in object_list:
            document = self.serialize(obj)
            documents.append(document)

        self.save_documents(documents)

    def save_documents(self, documents):
        """Send list of serialized documents into search engine."""
        actions = []
        for document in documents:
            parent_field = self.get_parent_id_field()
            action = {
                '_id': document.get(self.document_id_field),
                '_source': document,
            }
            if parent_field:
                action['_parent'] = document[parent_field]

            actions.append(action)

        helpers.bulk(
            client=self.engine,
            index=self.index_name,
            doc_type=self.document_type,
            chunk_size=self.chunk_size,
            actions=actions)

    @abc.abstractmethod
    def get_objects(self):
        """Get list of all objects which will be indexed into search engine."""

    @abc.abstractmethod
    def serialize(self, obj):
        """Serialize database object into valid search engine document."""

    def get_document_id_field(self):
        """Whatever document field should be treated as the id. This field
        should also be mapped to _id in the elasticsearch mapping
        """
        return "id"

    def get_parent_id_field(self):
        """Whatever field should be treated as the parent id. This is required
        for plugins with _parent definitions in their mappings. Documents to be
        indexed should contain this field.
        """
        return None

    @abc.abstractmethod
    def get_index_name(self):
        """Get name of the index."""

    @abc.abstractmethod
    def get_document_type(self):
        """Get name of the document type."""

    @abc.abstractmethod
    def get_rbac_filter(self, request_context):
        """Get rbac filter as es json filter dsl."""

    def filter_result(self, result, request_context):
        """Filter the outgoing search result."""
        return result

    def get_settings(self):
        """Get an index settings."""
        return {}

    def get_mapping(self):
        """Get an index mapping."""
        return {}

    def get_notification_handler(self):
        """Get the notification handler which implements NotificationBase."""
        return None

    def get_notification_supported_events(self):
        """Get the list of suppported event types."""
        return []

    def get_notification_topics_exchanges(self):
        """"Get the set of topics and exchanges."""
        return set()


@six.add_metaclass(abc.ABCMeta)
class NotificationBase(object):

    def __init__(self, engine, index_name, document_type):
        self.engine = engine
        self.index_name = index_name
        self.document_type = document_type

    @abc.abstractmethod
    def process(self, ctxt, publisher_id, event_type, payload, metadata):
        """Process the incoming notification message."""
