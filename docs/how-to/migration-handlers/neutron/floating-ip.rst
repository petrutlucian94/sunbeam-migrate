Migrating floating IPs
======================

Neutron floating IPs would usually be migrated as associated resources of
load balancers or Neutron ports.

However, ``sunbeam-migrate`` allows migrating individual floating IPs
explicitly.

The migration will cascade to the corresponding networks, subnets and routers
referenced by the floating IP.

Example:

.. code-block:: none

    sunbeam-migrate start \
      --include-dependencies \
      --resource-type=floating-ip \
      a7d143ad-c936-4f0f-9bbd-10e3ae30a162

  2025-12-18 08:51:19,118 INFO Initiating floating-ip migration, resource id: a7d143ad-c936-4f0f-9bbd-10e3ae30a162
  2025-12-18 08:51:20,498 INFO Migrating associated project resource: 379a5eb90759482ca62002860b3b7327
  2025-12-18 08:51:20,500 INFO Initiating project migration, resource id: 379a5eb90759482ca62002860b3b7327
  2025-12-18 08:51:21,143 INFO Migrating associated domain resource: 38da677b7dd944f8bce50bba4342bda6
  2025-12-18 08:51:21,145 INFO Initiating domain migration, resource id: 38da677b7dd944f8bce50bba4342bda6
  2025-12-18 08:51:22,620 WARNING Domain already exists: 6f05f02ce89b4976bb6f06bce3d2a40a admin_domain
  2025-12-18 08:51:22,627 INFO Successfully migrated domain resource, destination id: 6f05f02ce89b4976bb6f06bce3d2a40a
  2025-12-18 08:51:24,558 WARNING Project already exists: fc9010055a7a4f8bbfadd7799cbcb5b9 test-1380874626-owner
  2025-12-18 08:51:24,563 INFO Successfully migrated project resource, destination id: fc9010055a7a4f8bbfadd7799cbcb5b9
  2025-12-18 08:51:24,569 INFO Migrating associated network resource: 3a8e13bd-9900-4c21-ba79-36917d47cf75
  2025-12-18 08:51:24,570 INFO Initiating network migration, resource id: 3a8e13bd-9900-4c21-ba79-36917d47cf75
  2025-12-18 08:51:28,072 INFO Successfully migrated network resource, destination id: 1d46d880-a6ca-4888-9933-c806dc826e52
  2025-12-18 08:51:28,078 INFO Migrating associated subnet resource: c61b08f4-febb-4a41-9c59-69e1082ed919
  2025-12-18 08:51:28,079 INFO Initiating subnet migration, resource id: c61b08f4-febb-4a41-9c59-69e1082ed919
  2025-12-18 08:51:31,282 INFO Successfully migrated subnet resource, destination id: 9bacf7a7-e657-45be-9963-48c3aa90e102
  2025-12-18 08:51:35,003 INFO Successfully migrated floating-ip resource, destination id: 657e3845-8cb9-474b-91dc-628840fb001d
  2025-12-18 08:51:35,018 INFO Migration succeeded, cleaning up source floating-ip: a7d143ad-c936-4f0f-9bbd-10e3ae30a162
