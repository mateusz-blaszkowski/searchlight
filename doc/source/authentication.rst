..
      Copyright 2010 OpenStack Foundation
      All Rights Reserved.
      c) Copyright 2015 Hewlett-Packard Development Company, L.P.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

Keystone Authentication
=======================

Searchlight should be integrated with keystone. Setting this up is
relatively straightforward, as the keystone distribution includes the
necessary middleware. Once you have installed keystone and edited your
configuration files, users will need to have an authenticated keystone token
in all API requests. The keystone integration will allow both active denial
of requests from unauthenticated users and will also allow proper search
result filtering.

.. DANGER::
   If the API is not configured with keystone, all data indexed by
   searchlight is at risk of being accessed by unauthorized users.


Configuring the searchlight services to use keystone
----------------------------------------------------

Keystone is integrated with searchlight through the use of middleware.
The default configuration files for the Searchlight API use a single piece of
middleware called ``unauthenticated-context``, which generates a request
context containing blank authentication information. In order to configure
Searchlight to use Keystone, the ``authtoken`` and ``context`` middleware
must be deployed in place of the ``unauthenticated-context`` middleware.
The ``authtoken`` middleware performs the authentication token validation
and retrieves actual user authentication information. It can be found in
the keystone distribution. For more information, please refer to the Keystone
documentation on the ``auth_token`` middleware:
http://docs.openstack.org/developer/keystonemiddleware/middlewarearchitecture.html

api-paste.ini
`````````````

First, ensure that declarations for the middleware exist in the
``api-paste.ini`` file.  Here is an example for ``authtoken``::

  [pipeline:searchlight-keystone]
  pipeline = authtoken context rootapp

  [filter:authtoken]
  paste.filter_factory = keystonemiddleware.auth_token:filter_factory
  delay_auth_decision = true

searchlight.conf
````````````````

You must then update the main ``searchlight.conf`` configuration file
to enable the keystone application pipeline.

Set ``flavor`` to ``keystone`` in the ``paste_deploy`` group::

  [paste_deploy]
  flavor = keystone

Set ``keystone_authtoken`` options. The following sets the searchlight
service user as the user for performing policy API authentication checks.
The actual options and values in this section will need to be set according
to your environment::

  [keystone_authtoken]
  auth_url = http://127.0.0.1:35357
  auth_plugin = password
  project_domain_id = default
  project_name = service
  user_domain_id = default
  password = <SERVICE_PASSWORD>
  username = searchlight

.. note::
  For development and unit testing, it is recommended to also set
  ``revocation_cache_timeout = 10`` under the ``keystone_authtoken`` group.

Set ``service_credentials`` options. Searchlight plugins may make API calls
to other services to index their data. Prior to doing this, it will get a
valid token based on the integration account credentials::

 [service_credentials]
 # These are needed to make API calls to other services when indexing
 auth_plugin = password
 username = searchlight
 password = <SERVICE_PASSWORD>
 tenant_name = service
 auth_url = http://127.0.0.1:35357

Service integration account
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Some of the above configuration implicitly uses a ``searchlight`` service user.
If you intend to use this user, it must have been created and registered with
keystone. Typically, this is done with the following commands (v3 keystone)::

  $ openstack project create --or-show service --property domain=default
  $ openstack user create searchlight --password <SERVICE_PASSWORD> --project service
  $ openstack role add admin --project service --user searchlight

For more information on keystone service accounts, see:

http://docs.openstack.org/developer/keystone/configuringservices.html#creating-service-users

Policy restriction
==================

Searchlight uses the oslo policy library to allow control over the level of
access a user has based on their authenticated roles. Policy rules are defined
in a configuration file (by default, `etc/policy.json`). By default, all
operations are allowed.

See http://docs.openstack.org/developer/oslo.policy/api.html for details on
rule formatting.

Access to operations
--------------------

It is possible to restrict access to functionality by setting rules for
``query``, ``facets`` or ``plugins_info``. For instance, to restrict facet
listing to administrators and disable plugin information for all users::

    "facets": "role:admin",
    "plugins_info": "!"

Where a request is disallowed on this basis, the user will receive a
403 Forbidden response.

Note that policy rules are applied on the fly; no server restart is required.
Policy rules denying access to operations take precedence over the per-resource
access described below.

Access to resources
-------------------

Perhaps more interesting is restricting access to specific resource types.
For every operation (``query``, ``facets``, ``plugins_info``) it is possible
to set a rule for any resource types. In addition, the `allow` operation acts
as a default for a resource type. To allow access to Server resources only to
administrators, and disallow faceting for that resource type entirely::

    "resource:OS::Nova::Server:allow": "role:admin",
    "resource:OS::Nova::Server:facets": "!",

To restrict queries on Glance images to administrators::

    "resource:OS::Glance::Image:query": "role:admin",

To disable plugin information listing for Glance plugins::

    "resource:OS::Glance::Image:plugins_info": "!",
    "resource:OS::Glance::Metadef:plugins_info": "!",

.. note::

    At current plugins still apply RBAC separately from policy rules. We
    aim to bring the two closer together in a later patch.

When resources are restricted in this way resources will be excluded
from the search (which may result in empty search results). No Forbidden
response will be returned.

.. note::

    It is *not* possible to apply a more restrictive rule with `allow`
    and less restrictive rules with specific operations because of the
    way the policy engine works. Rules can only become more restrictive.

