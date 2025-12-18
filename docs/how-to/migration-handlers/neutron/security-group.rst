Migrating security groups
=========================

This example migrates a security group along with all its belonging security
group rules.

.. note::

  Security group rules may reference other security groups (via ``remote_group_id``).
  Consider migrating all security groups before recreating security group rules.
  One simple solution would be to perform a **security group batched migration**
  in two steps: one without ``--include-members`` and then another run with
  ``--include-members``.

.. note::

  Consider passing ``--include-dependencies`` if the multi-tenant mode
  is enabled in order to automatically recreate the Keystone resources.

.. code-block:: none

  sunbeam-migrate start \
    --include-members \
    --resource-type=security-group \
    fcbdfef5-9eb2-4ab9-8fc7-742883b8c511

  2025-11-24 12:15:59,930 INFO Initiating security-group migration, resource id: fcbdfef5-9eb2-4ab9-8fc7-742883b8c511
  2025-11-24 12:16:12,142 INFO Migrating member security-group-rule resource: 373c9707-b234-489b-a904-dd7e0f87a0c4
  2025-11-24 12:16:12,146 INFO Initiating security-group-rule migration, resource id: 373c9707-b234-489b-a904-dd7e0f87a0c4
  2025-11-24 12:16:17,934 INFO Successfully migrated resource, destination id: 194b1948-b29b-41d9-a5c9-152c3d5c9f5a
  2025-11-24 12:16:17,938 INFO Migrating member security-group-rule resource: 940ad646-0353-4f42-b490-453991a8f56e
  2025-11-24 12:16:17,938 INFO Initiating security-group-rule migration, resource id: 940ad646-0353-4f42-b490-453991a8f56e
  2025-11-24 12:16:23,50 INFO Security group rule already exists on destination SG f5a4bbd2-caee-4b1b-8c6d-182c34828e30, reusing rule 14b56726-2073-4c46-a6ad-2a73208efdcc
  2025-11-24 12:16:23,87 INFO Successfully migrated resource, destination id: 14b56726-2073-4c46-a6ad-2a73208efdcc
  2025-11-24 12:16:23,88 INFO Migrating member security-group-rule resource: d532c863-8fb6-4735-b540-c5771bb46bfa
  2025-11-24 12:16:23,88 INFO Initiating security-group-rule migration, resource id: d532c863-8fb6-4735-b540-c5771bb46bfa
  2025-11-24 12:16:28,509 INFO Security group rule already exists on destination SG f5a4bbd2-caee-4b1b-8c6d-182c34828e30, reusing rule 14b56726-2073-4c46-a6ad-2a73208efdcc
  2025-11-24 12:16:28,535 INFO Successfully migrated resource, destination id: 14b56726-2073-4c46-a6ad-2a73208efdcc
  2025-11-24 12:16:28,543 INFO Successfully migrated resource, destination id: f5a4bbd2-caee-4b1b-8c6d-182c34828e30

Resulting migrations:

.. code-block:: none

  sunbeam-migrate list

  +----------------------------------------------------------------------------------------------------------------------------------------------------------------+
  |                                                                           Migrations                                                                           |
  +--------------------------------------+---------+---------------------+-----------+--------------------------------------+--------------------------------------+
  |                 UUID                 | Service |    Resource type    |   Status  |              Source ID               |            Destination ID            |
  +--------------------------------------+---------+---------------------+-----------+--------------------------------------+--------------------------------------+
  | 583173e1-9ff1-470a-a97e-7ecbac3d60ad | neutron | security-group-rule | completed | d532c863-8fb6-4735-b540-c5771bb46bfa | 14b56726-2073-4c46-a6ad-2a73208efdcc |
  | c3271d8c-619b-4da0-b8e4-d97bf887059d | neutron | security-group-rule | completed | 940ad646-0353-4f42-b490-453991a8f56e | 14b56726-2073-4c46-a6ad-2a73208efdcc |
  | 6b43e5e4-298d-4d62-9daf-49cada728bfc | neutron | security-group-rule | completed | 373c9707-b234-489b-a904-dd7e0f87a0c4 | 194b1948-b29b-41d9-a5c9-152c3d5c9f5a |
  | 14632db3-5203-4e02-8bf2-ecdc5a566925 | neutron |    security-group   | completed | fcbdfef5-9eb2-4ab9-8fc7-742883b8c511 | f5a4bbd2-caee-4b1b-8c6d-182c34828e30 |
  | 3c625f6d-c164-4b30-9f9e-bd9aeeed2df0 | neutron |        subnet       | completed | 940b789e-cf85-4dad-ae7d-26d120eeff7f | 8df27647-c76f-43c2-9f53-20599873569b |
  | 2fbd417e-099c-467f-8ae6-334ef887e166 | neutron |        subnet       | completed | 9040a40d-d875-4260-927c-f83f60ec4d8c | 07f0c904-956f-47b8-84ce-bf751e4dfdad |
  | 4af538f6-6d95-449a-a8e0-6d7fd5da708d | neutron |       network       | completed | bd0c1019-3d1b-4f64-86c4-c4c0e04a6a36 | 29c3ab49-5208-4e62-8399-c2ed09be6988 |
  +--------------------------------------+---------+---------------------+-----------+--------------------------------------+--------------------------------------+
