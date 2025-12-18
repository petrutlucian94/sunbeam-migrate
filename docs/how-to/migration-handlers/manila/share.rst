Migrating Manila shares
=======================

``sunbeam-migrate`` can be used to migrate Manila shares along with the user
data.

Share types
-----------

The source share type specification may not apply to the destination cloud.

If ``preserve_share_type`` is disabled, ``sunbeam-migrate`` will skip migrating
the share type and use the default type instead.

Users may also recreate share types manually and register them using the
``register-external`` command. Migrated shares will then use the manually
created share types.

NFS exports
-----------

NFS is currently the only supported export type, which also applies to Sunbeam
at the time of writing.

Shared filesystems are mounted at a configurable location in order to facilitate
the data transfer. The path can be modified using the ``temporary_migration_dir``
setting.

``sunbeam-migrate`` will automatically define access rules, granting itself
share access. Use the ``manila_local_access_ip`` to specify the local IP that
is going to be used to access the Manila shares. If unset, the IP will be
determined automatically using the local routes.

When transferring files, ``sunbeam-migrate`` will preserve the original
timestamps, extended attributes, links and ownership information.

Example
-------

The following command migrates a share and removes it from the source cloud:

.. code-block::
  sunbeam-migrate start \
    --include-dependencies \
    --resource-type=volume \
    --cleanup-source \
    2632f9f6-3310-4900-83fa-28969cfb14e4

  2025-12-18 14:18:02,970 INFO Initiating share migration, resource id: 2632f9f6-3310-4900-83fa-28969cfb14e4
  2025-12-18 14:18:04,093 INFO Migrating associated project resource: 91f0554c6e714599b1248cf10d27fa63
  2025-12-18 14:18:04,094 INFO Initiating project migration, resource id: 91f0554c6e714599b1248cf10d27fa63
  2025-12-18 14:18:04,683 INFO Migrating associated domain resource: 38da677b7dd944f8bce50bba4342bda6
  2025-12-18 14:18:04,688 INFO Initiating domain migration, resource id: 38da677b7dd944f8bce50bba4342bda6
  2025-12-18 14:18:06,239 WARNING Domain already exists: 6f05f02ce89b4976bb6f06bce3d2a40a admin_domain
  2025-12-18 14:18:06,256 INFO Successfully migrated domain resource, destination id: 6f05f02ce89b4976bb6f06bce3d2a40a
  2025-12-18 14:18:08,293 WARNING Project already exists: 5f6f8ecbd84c4aa7a41a742dd6e222e3 test-2901735245-owner
  2025-12-18 14:18:08,299 INFO Successfully migrated project resource, destination id: 5f6f8ecbd84c4aa7a41a742dd6e222e3
  2025-12-18 14:18:08,307 INFO Migrating associated share-type resource: 8556be7e-3fec-44bf-a218-d190b84fceb7
  2025-12-18 14:18:08,308 INFO Initiating share-type migration, resource id: 8556be7e-3fec-44bf-a218-d190b84fceb7
  2025-12-18 14:18:11,097 INFO Successfully migrated share-type resource, destination id: ef236a8d-db6a-4322-b1ae-8e1e6014114a
  2025-12-18 14:18:16,026 INFO Waiting for share provisioning: 7140d15c-bf9d-4b96-b777-71b26721fe52
  2025-12-18 14:18:16,566 INFO Adding temporary share access rule: 2632f9f6-3310-4900-83fa-28969cfb14e4 to ip 192.168.30.1
  2025-12-18 14:18:16,736 INFO Waiting for share access rule to become active.
  2025-12-18 14:18:21,876 INFO Mounting nfs share 192.168.99.206:/volumes/_nogroup/3d1918f6-8f47-4eef-a36f-0b8f1d7ba991/baaa0d5f-4ab0-43e6-820c-ce0672db1e90 to /home/ubuntu/.local/share/sunbeam-migrate/migration_dir/2632f9f6-3310-4900-83fa-28969cfb14e4.1169711895.
  mount.nfs: timeout set for Thu Dec 18 14:20:21 2025
  mount.nfs: trying text-based options 'vers=4.2,addr=192.168.99.206,clientaddr=192.168.30.1'
  2025-12-18 14:18:22,333 INFO Adding temporary share access rule: 7140d15c-bf9d-4b96-b777-71b26721fe52 to ip 192.168.30.1
  2025-12-18 14:18:22,481 INFO Waiting for share access rule to become active.
  2025-12-18 14:18:27,636 INFO Mounting nfs share 192.168.99.207:/volumes/_nogroup/2e31ffb8-a550-4ae1-a2df-102ad0bc3a58/68a0ce16-d6f7-4317-bd7d-c4cd820766f3 to /home/ubuntu/.local/share/sunbeam-migrate/migration_dir/7140d15c-bf9d-4b96-b777-71b26721fe52.2379628710.
  mount.nfs: timeout set for Thu Dec 18 14:20:27 2025
  mount.nfs: trying text-based options 'vers=4.2,addr=192.168.99.207,clientaddr=192.168.30.1'
  2025-12-18 14:18:27,710 INFO Migrating share data: /home/ubuntu/.local/share/sunbeam-migrate/migration_dir/2632f9f6-3310-4900-83fa-28969cfb14e4.1169711895 -> /home/ubuntu/.local/share/sunbeam-migrate/migration_dir/7140d15c-bf9d-4b96-b777-71b26721fe52.2379628710
  2025-12-18 14:18:27,771 INFO Unmounting nfs share: /home/ubuntu/.local/share/sunbeam-migrate/migration_dir/7140d15c-bf9d-4b96-b777-71b26721fe52.2379628710
  2025-12-18 14:18:27,812 INFO Deleting temporary share access rule: 7140d15c-bf9d-4b96-b777-71b26721fe52 to ip 192.168.30.1
  2025-12-18 14:18:28,057 INFO Unmounting nfs share: /home/ubuntu/.local/share/sunbeam-migrate/migration_dir/2632f9f6-3310-4900-83fa-28969cfb14e4.1169711895
  2025-12-18 14:18:28,082 INFO Deleting temporary share access rule: 2632f9f6-3310-4900-83fa-28969cfb14e4 to ip 192.168.30.1
  2025-12-18 14:18:28,313 INFO Successfully migrated share resource, destination id: 7140d15c-bf9d-4b96-b777-71b26721fe52
  2025-12-18 14:18:28,320 INFO Migration succeeded, cleaning up source share: 2632f9f6-3310-4900-83fa-28969cfb14e4
