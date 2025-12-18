Migrating keypairs
==================

Nova keypairs are among the very few Openstack resources that do not have an
UUID. Instead, we need to identify them by name, which is not globally unique.

For this reason, cross-project keypair migration is not supported for the time
being.

To migrate keypairs owned by other projects, consider using a separate
``sunbeam-migrate`` config and database for each individual tenant.
The admin user can be temporarily added as a member of the migrated projects.

Example
-------

This example showcases a keypair migration:

.. code-block:: none

  sunbeam-migrate start \
    --resource-type=keypair \
    --cleanup-source \
    test-335612855

  2025-12-18 07:22:26,828 INFO Initiating keypair migration, resource id: test-741308786
  2025-12-18 07:22:30,925 INFO Successfully migrated keypair resource, destination id: test-741308786
  2025-12-18 07:22:30,930 INFO Migration succeeded, cleaning up source keypair: test-741308786
