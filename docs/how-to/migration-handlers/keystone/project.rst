Migrating projects
==================

Project migrations will include the corresponding Keystone domain.
If ``--include-members`` is provided, associated users will be migrated as
well.

In :doc:`multi-tenant mode<../../../explanation/multitenant-mode>`,
identity resources will be migrated as dependencies of other Openstack resources
(e.g. instances, volumes, networks, etc). A project may also be moved as a
Keystone user dependency.

Example
-------

The following example migrates an user and all the dependent resources:

.. code-block:: none

  sunbeam-migrate start \
    --resource-type=project \
    --include-dependencies \
    29d1557e93fe45fdb0d35dc61670f0a6

  2025-12-18 15:19:55,438 INFO Initiating project migration, resource id: 29d1557e93fe45fdb0d35dc61670f0a6
  2025-12-18 15:19:56,292 INFO Migrating associated domain resource: 81a61689eff544acafb642022d02ff2f
  2025-12-18 15:19:56,293 INFO Initiating domain migration, resource id: 81a61689eff544acafb642022d02ff2f
  2025-12-18 15:19:57,907 INFO Successfully migrated domain resource, destination id: ff3c741e93f9488a9ea89eda65b20160
  2025-12-18 15:20:01,089 INFO Successfully migrated project resource, destination id: 07346762799a4befa944aa5971b820ad
