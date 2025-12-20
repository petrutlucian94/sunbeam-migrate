.. _barbican_secret_ref:

Migrating secrets
=================

Barbican resources cannot be retrieved by other projects unless explicitly
allowed through ACLs.

``sunbeam-migrate`` currently expects to identify resources solely based on
their IDs, for which reason cross-project secret migration is not supported.

To migrate these resources, consider using a separate ``sunbeam-migrate`` config
and database for each individual tenant. The admin user user can be temporarily
added as a member of the migrated projects.

.. note::

  When initiating a secret container migration, the corresponding secrets
  will be migrated automatically.

Example
-------

We'll use a batch migration, covering all secrets owned by the current project.

.. code-block:: none

  sunbeam-migrate start-batch \
    --resource-type=secret \
    --all

  2025-12-18 07:42:17,548 INFO Initiating secret migration, resource id: http://192.168.121.204/openstack-barbican/v1/secrets/5079c474-b88e-4cff-bb08-4245aa891986
  2025-12-18 07:42:19,887 INFO Successfully migrated secret resource, destination id: http://192.168.122.206/openstack-barbican/v1/secrets/35973318-6c2a-43e4-94db-798bcbba3d46
  2025-12-18 07:42:19,899 INFO Migration succeeded, cleaning up source secret: http://192.168.121.204/openstack-barbican/v1/secrets/5079c474-b88e-4cff-bb08-4245aa891986
  2025-12-18 07:42:20,744 INFO Initiating secret migration, resource id: http://192.168.121.204/openstack-barbican/v1/secrets/962ec498-c078-433d-a7d8-005a87d5811e
  2025-12-18 07:42:23,078 INFO Successfully migrated secret resource, destination id: http://192.168.122.206/openstack-barbican/v1/secrets/e8a10966-1a7b-4288-9d42-9812b8f010ae
  2025-12-18 07:42:23,082 INFO Migration succeeded, cleaning up source secret: http://192.168.121.204/openstack-barbican/v1/secrets/962ec498-c078-433d-a7d8-005a87d5811e
  2025-12-18 07:42:23,874 INFO Initiating secret migration, resource id: http://192.168.121.204/openstack-barbican/v1/secrets/fb0cb5ca-2e1c-4a14-aa5d-4d66650d7817
  2025-12-18 07:42:25,643 INFO Successfully migrated secret resource, destination id: http://192.168.122.206/openstack-barbican/v1/secrets/46ab1381-6190-45c9-a603-a7eb14ee13c0
  2025-12-18 07:42:25,649 INFO Migration succeeded, cleaning up source secret: http://192.168.121.204/openstack-barbican/v1/secrets/fb0cb5ca-2e1c-4a14-aa5d-4d66650d7817
