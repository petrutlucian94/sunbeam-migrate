Migrating subnets
=================

The corresponding network needs to be migrated first, which can be handled
manually or using the ``--include-dependencies`` flag:

.. code-block:: none

  sunbeam-migrate start \
    --resource-type=subnet \
    --include-dependencies \
    9040a40d-d875-4260-927c-f83f60ec4d8c

  2025-11-24 12:23:31,286 INFO Initiating subnet migration, resource id: 9040a40d-d875-4260-927c-f83f60ec4d8c
  2025-11-24 12:23:33,150 INFO Migrating associated network resource: bd0c1019-3d1b-4f64-86c4-c4c0e04a6a36
  2025-11-24 12:23:33,150 INFO Initiating network migration, resource id: bd0c1019-3d1b-4f64-86c4-c4c0e04a6a36
  2025-11-24 12:23:37,982 INFO Successfully migrated resource, destination id: 7798eb6e-7d57-40bf-b434-a0c0c51c219f
  2025-11-24 12:23:46,536 INFO Successfully migrated resource, destination id: 2c4491d1-035a-43a6-9f89-74751eabebfa

Resulting migrations:

.. code-block:: none

  sunbeam-migrate list

  +----------------------------------------------------------------------------------------------------------------------------------------------------------+
  |                                                                        Migrations                                                                        |
  +--------------------------------------+---------+---------------+-----------+--------------------------------------+--------------------------------------+
  |                 UUID                 | Service | Resource type |   Status  |              Source ID               |            Destination ID            |
  +--------------------------------------+---------+---------------+-----------+--------------------------------------+--------------------------------------+
  | ffeaa9ec-e9de-497f-acb1-8792fd29781f | neutron |    network    | completed | bd0c1019-3d1b-4f64-86c4-c4c0e04a6a36 | 7798eb6e-7d57-40bf-b434-a0c0c51c219f |
  | 9ead5fa8-0d3f-4ab6-9bc3-c4dc55a79199 | neutron |     subnet    | completed | 9040a40d-d875-4260-927c-f83f60ec4d8c | 2c4491d1-035a-43a6-9f89-74751eabebfa |
  +--------------------------------------+---------+---------------+-----------+--------------------------------------+--------------------------------------+

.. note:: Subnets may also be migrated automatically as network members.
