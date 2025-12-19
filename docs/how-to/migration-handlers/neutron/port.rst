Migrating ports
===============

Neutron ports would usually be migrated as associated resources of instances
and the migration would cascade to networks, subnets and security groups.

However, ``sunbeam-migrate`` allows migrating individual ports explicitly.

.. note::

  Batch port migrations are not supported.

The user can configure whether ``sunbeam-migrate`` should preserve the following:

* port fixed IP and MAC addresses
* floating IP, optionally using the exact same address

Example
-------

.. code-block:: none

  sunbeam-migrate start \
    --include-dependencies \
    --resource-type=port \
    8a32a767-45a7-46b3-9c53-441e23db4d86

  2025-12-18 08:24:14,050 INFO Initiating port migration, resource id: 8a32a767-45a7-46b3-9c53-441e23db4d86
  2025-12-18 08:24:14,851 INFO Migrating associated project resource: cd8ee9c22a564b409fb5b778db7c7191
  2025-12-18 08:24:14,853 INFO Initiating project migration, resource id: cd8ee9c22a564b409fb5b778db7c7191
  2025-12-18 08:24:15,453 INFO Migrating associated domain resource: 38da677b7dd944f8bce50bba4342bda6
  2025-12-18 08:24:15,455 INFO Initiating domain migration, resource id: 38da677b7dd944f8bce50bba4342bda6
  2025-12-18 08:24:16,842 WARNING Domain already exists: 6f05f02ce89b4976bb6f06bce3d2a40a admin_domain
  2025-12-18 08:24:16,848 INFO Successfully migrated domain resource, destination id: 6f05f02ce89b4976bb6f06bce3d2a40a
  2025-12-18 08:24:18,738 WARNING Project already exists: e32ef92750b04baea61ef08c8bc8c29e test-1675463962-owner
  2025-12-18 08:24:18,745 INFO Successfully migrated project resource, destination id: e32ef92750b04baea61ef08c8bc8c29e
  2025-12-18 08:24:18,751 INFO Migrating associated network resource: cdb2587f-62eb-49a9-85fa-34379bedb3e8
  2025-12-18 08:24:18,752 INFO Initiating network migration, resource id: cdb2587f-62eb-49a9-85fa-34379bedb3e8
  2025-12-18 08:24:22,435 INFO Successfully migrated network resource, destination id: 2e6f9e1a-1e9f-41ab-852d-b3bbb33c7a40
  2025-12-18 08:24:22,447 INFO Migrating associated subnet resource: 96730ea8-23c6-44ff-9b69-e8e37d4aac9d
  2025-12-18 08:24:22,448 INFO Initiating subnet migration, resource id: 96730ea8-23c6-44ff-9b69-e8e37d4aac9d
  2025-12-18 08:24:25,478 INFO Successfully migrated subnet resource, destination id: 43e79a31-c932-4497-abea-c57acb2a3948
  2025-12-18 08:24:25,487 INFO Migrating associated security-group resource: 87eef12f-ef14-41cd-8893-73e5569cb49f
  2025-12-18 08:24:25,487 INFO Initiating security-group migration, resource id: 87eef12f-ef14-41cd-8893-73e5569cb49f
  2025-12-18 08:24:27,922 INFO Successfully migrated security-group resource, destination id: acd54931-121a-45a4-b82b-837822f1041a
  2025-12-18 08:24:30,736 INFO Successfully migrated port resource, destination id: da07f977-c48b-4938-bdba-7f11c76e92fc
