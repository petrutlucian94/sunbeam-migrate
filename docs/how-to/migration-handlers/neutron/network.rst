Migrating networks
==================

Use the following command to migrate a network and all its belonging subnets.

.. note::

  Consider passing ``--include-dependencies`` if the multi-tenant mode
  is enabled in order to automatically recreate the Keystone resources.

.. code-block:: none

  sunbeam-migrate start \
    --resource-type=network \
    --include-members \
    bd0c1019-3d1b-4f64-86c4-c4c0e04a6a36

  2025-11-24 12:15:24,799 INFO Initiating network migration, resource id: bd0c1019-3d1b-4f64-86c4-c4c0e04a6a36
  2025-11-24 12:15:30,702 INFO Migrating member subnet resource: 9040a40d-d875-4260-927c-f83f60ec4d8c
  2025-11-24 12:15:30,704 INFO Initiating subnet migration, resource id: 9040a40d-d875-4260-927c-f83f60ec4d8c
  2025-11-24 12:15:39,575 INFO Successfully migrated resource, destination id: 07f0c904-956f-47b8-84ce-bf751e4dfdad
  2025-11-24 12:15:39,578 INFO Migrating member subnet resource: 940b789e-cf85-4dad-ae7d-26d120eeff7f
  2025-11-24 12:15:39,578 INFO Initiating subnet migration, resource id: 940b789e-cf85-4dad-ae7d-26d120eeff7f
  2025-11-24 12:15:48,779 INFO Successfully migrated resource, destination id: 8df27647-c76f-43c2-9f53-20599873569b
  2025-11-24 12:15:48,782 INFO Successfully migrated resource, destination id: 29c3ab49-5208-4e62-8399-c2ed09be6988

In order to avoid conflicts on the destination cloud, the network segmentation
ID will not be preserved (e.g. VLAN or tunnel VNI). This behavior can be
modified using the ``preserve_network_segmentation_id`` setting.

.. note:: Networks may also be migrated automatically as subnet dependencies.
