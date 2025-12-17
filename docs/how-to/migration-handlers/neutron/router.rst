Migrating Routers
=================

When migrating Neutron routers, use ``--include-dependencies`` to include the
external gateway network. Note that it can also be migrated separately.

Other subnets connected to the router can be automatically covered using
``--include-members``.

.. note:: Consider passing ``--include-dependencies`` if the multi-tenant mode
is enabled in order to automatically recreate the Keystone resources.

.. code-block:: none

  sunbeam-migrate start \
    --resource-type=router \
    --include-dependencies \
    --include-members \
    897e4a69-c808-4065-9450-b1231b255c22

  2025-12-03 14:02:16,129 INFO Initiating router migration, resource id: 897e4a69-c808-4065-9450-b1231b255c22
  2025-12-03 14:02:18,660 INFO Migrating associated network resource: 9b546631-356b-4ad2-bdf4-90f173e6e64c
  2025-12-03 14:02:18,660 INFO Initiating network migration, resource id: 9b546631-356b-4ad2-bdf4-90f173e6e64c
  2025-12-03 14:02:24,826 INFO Successfully migrated resource, destination id: ea6c6e3c-57d7-410a-a3ec-cb149a723640
  2025-12-03 14:02:25,40 INFO Migrating member subnet resource: 08eb4817-fdc9-459d-8b41-37112a5dbd87
  2025-12-03 14:02:25,41 INFO Initiating subnet migration, resource id: 08eb4817-fdc9-459d-8b41-37112a5dbd87
  2025-12-03 14:02:34,757 INFO Successfully migrated resource, destination id: 9a1765de-4bd8-4d1a-a8bd-a522cdd3e719
  2025-12-03 14:02:34,792 INFO Associated resource subnet 08eb4817-fdc9-459d-8b41-37112a5dbd87 already completed (migration e737a596-f648-4c0b-8973-7bbe22fc1b5e), skipping duplicate migration
  2025-12-03 14:02:45,463 INFO Successfully migrated resource, destination id: 9fbe72d1-5316-4b2d-bf6d-1bae8fda990b
  2025-12-03 14:02:45,886 INFO Migrating member subnet resource: 940b789e-cf85-4dad-ae7d-26d120eeff7f
  2025-12-03 14:02:45,887 INFO Initiating subnet migration, resource id: 940b789e-cf85-4dad-ae7d-26d120eeff7f
  2025-12-03 14:02:47,778 INFO Migrating associated network resource: bd0c1019-3d1b-4f64-86c4-c4c0e04a6a36
  2025-12-03 14:02:47,778 INFO Initiating network migration, resource id: bd0c1019-3d1b-4f64-86c4-c4c0e04a6a36
  2025-12-03 14:02:53,37 INFO Successfully migrated resource, destination id: 88b5fcbf-c2c3-4d68-9dba-e1decd97ea32
  2025-12-03 14:02:53,338 INFO Migrating member subnet resource: 9040a40d-d875-4260-927c-f83f60ec4d8c
  2025-12-03 14:02:53,338 INFO Initiating subnet migration, resource id: 9040a40d-d875-4260-927c-f83f60ec4d8c
  2025-12-03 14:03:03,328 INFO Successfully migrated resource, destination id: e0aa3f2d-1dc7-4ffe-b4b8-45868a88e651
  2025-12-03 14:03:03,363 INFO Member resource subnet 940b789e-cf85-4dad-ae7d-26d120eeff7f already in progress (migration 8fbae0f1-02cb-4ec7-b94b-c750f9a35a4a), skipping duplicate migration
  2025-12-03 14:03:14,926 INFO Successfully migrated resource, destination id: b12d2ce5-f0bc-4a01-b93c-784f02639c7e
  2025-12-03 14:03:14,944 INFO Attaching internal subnet 940b789e-cf85-4dad-ae7d-26d120eeff7f (dest b12d2ce5-f0bc-4a01-b93c-784f02639c7e) to router 9fbe72d1-5316-4b2d-bf6d-1bae8fda990b
