Migrating domains
=================

Domain migrations will cascade to all the belonging projects, users and roles if
``--include-members`` is set.

Domains can also be migrated as :ref:`dependencies<resource_hierarchies_ref>`
of Keystone projects and users.

In :doc:`multi-tenant mode<../../../explanation/multitenant-mode>`,
identity resources will be migrated as dependencies of other Openstack resources
(e.g. instances, volumes, networks, etc).

Example
-------

The following example recursively migrates a domain:

.. code-block:: none

  sunbeam-migrate start \
    --resource-type=domain \
    --include-members \
    cb0eb78556a14df1bb6220dee836df28

  2025-12-18 14:58:51,102 INFO Initiating domain migration, resource id: cb0eb78556a14df1bb6220dee836df28
  2025-12-18 14:58:53,018 INFO Successfully migrated domain resource, destination id: 9596f3d3d90149f39ea3c27c52d8b78d
  2025-12-18 14:58:53,614 INFO Migrating member project resource: 96f865b917074c49b8c20378fddce79d
  2025-12-18 14:58:53,615 INFO Initiating project migration, resource id: 96f865b917074c49b8c20378fddce79d
  2025-12-18 14:58:56,032 INFO Successfully migrated project resource, destination id: 82c74fbf994d418785693613b12d9855
  2025-12-18 14:58:56,426 INFO Migrating member user resource: 38c19630e64a4eac93fc67ac72a9885a
  2025-12-18 14:58:56,427 INFO Initiating user migration, resource id: 38c19630e64a4eac93fc67ac72a9885a
  2025-12-18 14:58:57,220 INFO Migrating associated role resource: 5bf07c37d906408aaaf7f9ab695f3b8e
  2025-12-18 14:58:57,222 INFO Initiating role migration, resource id: 5bf07c37d906408aaaf7f9ab695f3b8e
  2025-12-18 14:58:59,654 INFO Successfully migrated role resource, destination id: ffe6794e39904fa6952b0ea613a4d6a9
  2025-12-18 14:58:59,668 INFO Migrating associated role resource: 4f254f35c43c45fda5f09874b742d1aa
  2025-12-18 14:58:59,668 INFO Initiating role migration, resource id: 4f254f35c43c45fda5f09874b742d1aa
  2025-12-18 14:59:02,843 INFO Successfully migrated role resource, destination id: 8d1af15bb8e04166b15ba9ff2d77644e
  2025-12-18 14:59:05,845 INFO Recreated project role assignment: user 961b6ff0ed1e44e8beba4cf8b73a0ddb, role ffe6794e39904fa6952b0ea613a4d6a9, project 82c74fbf994d418785693613b12d9855
  2025-12-18 14:59:06,518 INFO Recreated domain role assignment: user 961b6ff0ed1e44e8beba4cf8b73a0ddb, role 8d1af15bb8e04166b15ba9ff2d77644e, domain 9596f3d3d90149f39ea3c27c52d8b78d
  2025-12-18 14:59:06,522 INFO Successfully migrated user resource, destination id: 961b6ff0ed1e44e8beba4cf8b73a0ddb