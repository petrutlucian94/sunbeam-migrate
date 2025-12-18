Migrating users
===============

``sunbeam-migrate`` can migrate Keystone users along with the corresponding
domain, project and roles.

In :doc:`multi-tenant mode<../../../explanation/multitenant-mode>`,
identity resources will be migrated as dependencies of other Openstack resources
(e.g. instances, volumes, networks, etc).

Note that the user password cannot be preserved and will need to be reset on the
destination cloud.

Example
-------

The following example migrates an user and all the dependent resources:

.. code-block:: none

  sunbeam-migrate start \
    --resource-type=user \
    --include-dependencies \
    3ac5f091c2ee46e7aaee3ecd74a8c704

  2025-12-18 15:02:12,285 INFO Initiating user migration, resource id: 3ac5f091c2ee46e7aaee3ecd74a8c704
  2025-12-18 15:02:13,234 INFO Migrating associated domain resource: 9443251d042a4fba995ff0293a82acfa
  2025-12-18 15:02:13,235 INFO Initiating domain migration, resource id: 9443251d042a4fba995ff0293a82acfa
  2025-12-18 15:02:15,029 INFO Successfully migrated domain resource, destination id: a512bf1f391b4c9cab24047c1aa0c41e
  2025-12-18 14:58:53,614 INFO Migrating associated project resource: 96f865b917074c49b8c20378fddce79d
  2025-12-18 14:58:53,615 INFO Initiating project migration, resource id: 96f865b917074c49b8c20378fddce79d
  2025-12-18 14:58:56,032 INFO Successfully migrated project resource, destination id: 82c74fbf994d418785693613b12d9855
  2025-12-18 14:58:57,220 INFO Migrating associated role resource: 5bf07c37d906408aaaf7f9ab695f3b8e
  2025-12-18 14:58:57,222 INFO Initiating role migration, resource id: 5bf07c37d906408aaaf7f9ab695f3b8e
  2025-12-18 14:58:59,654 INFO Successfully migrated role resource, destination id: ffe6794e39904fa6952b0ea613a4d6a9
  2025-12-18 14:58:59,668 INFO Migrating associated role resource: 4f254f35c43c45fda5f09874b742d1aa
  2025-12-18 14:58:59,668 INFO Initiating role migration, resource id: 4f254f35c43c45fda5f09874b742d1aa
  2025-12-18 14:59:02,843 INFO Successfully migrated role resource, destination id: 8d1af15bb8e04166b15ba9ff2d77644e
  2025-12-18 14:59:05,845 INFO Recreated project role assignment: user 961b6ff0ed1e44e8beba4cf8b73a0ddb, role ffe6794e39904fa6952b0ea613a4d6a9, project 82c74fbf994d418785693613b12d9855
  2025-12-18 14:59:06,518 INFO Recreated domain role assignment: user 961b6ff0ed1e44e8beba4cf8b73a0ddb, role 8d1af15bb8e04166b15ba9ff2d77644e, domain 9596f3d3d90149f39ea3c27c52d8b78d
  2025-12-18 14:59:06,522 INFO Successfully migrated user resource, destination id: 961b6ff0ed1e44e8beba4cf8b73a0ddb
