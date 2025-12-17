Migrating secret containers
===========================

This example creates and migrates a certificate secret container along
with the referenced secrets.

.. code-block:: bash

  cert_ref=`openstack secret store --name root-ca-cert -s certificate --file ~/ca/rootca.crt | grep "Secret href" | awk '{print $5}'`
  key_ref=`openstack secret store --name root-ca-key -s private --file ~/ca/rootca.key | grep "Secret href" | awk '{print $5}'`

  openstack secret container create \
    --name root-ca \
    --type certificate \
    --secret "certificate=$cert_ref" \
    --secret "private_key=$key_ref"

We'll use a batch migration, covering all secret containers owned by a given
project.

.. code-block:: none

  sunbeam-migrate start-batch \
    --resource-type=secret-container \
    --filter "project-id:516ddfe184c84f77889b33f027716e89" \
    --include-dependencies

  2025-11-17 15:41:47,195 INFO Initiating secret-container migration, resource id: http://10.8.99.203/openstack-barbican/v1/containers/85e2dee5-0b8c-4d7e-a1b7-a634788d49d7
  2025-11-17 15:41:48,147 INFO Migrating associated secret resource: http://10.8.99.203/openstack-barbican/v1/secrets/569d75d1-4798-4891-87b7-764b81f403f4
  2025-11-17 15:41:48,148 INFO Initiating secret migration, resource id: http://10.8.99.203/openstack-barbican/v1/secrets/569d75d1-4798-4891-87b7-764b81f403f4
  2025-11-17 15:41:50,795 INFO Successfully migrated resource, destination id: https://public2.sunbeam.local/openstack-barbican/v1/secrets/cda7e8eb-a993-4dd4-8302-cc2b83096f65
  2025-11-17 15:41:50,802 INFO Migrating associated secret resource: http://10.8.99.203/openstack-barbican/v1/secrets/ee818210-2ff5-4a4f-9153-69c3c83b4003
  2025-11-17 15:41:50,802 INFO Initiating secret migration, resource id: http://10.8.99.203/openstack-barbican/v1/secrets/ee818210-2ff5-4a4f-9153-69c3c83b4003
  2025-11-17 15:41:53,162 INFO Successfully migrated resource, destination id: https://public2.sunbeam.local/openstack-barbican/v1/secrets/29f27a0e-dcd9-481e-a4ca-f764db1cd6df
  2025-11-17 15:41:55,863 INFO Successfully migrated resource, destination id: https://public2.sunbeam.local/openstack-barbican/v1/containers/c02de39b-d379-4b4f-9e93-3392fb5bdf22

``--include-dependencies`` was needed since the secrets are dependent resources
that must exist before the secret container gets created, which only holds
secret references. Furthermore, ``--include-dependencies`` should be passed
in multi-tenant mode to automatically migrate Keystone resources.

Resulting resources:

.. code-block:: none

  sunbeam-migrate list
  +--------------------------------------------------------------------------------------------------------------------------------------------------------------+
  |                                                                          Migrations                                                                          |
  +--------------------------------------+----------+------------------+-----------+--------------------------------------+--------------------------------------+
  |                 UUID                 | Service  |  Resource type   |   Status  |              Source ID               |            Destination ID            |
  +--------------------------------------+----------+------------------+-----------+--------------------------------------+--------------------------------------+
  | c2e26b76-ec50-45e1-8b82-ceded96cedb3 | barbican |      secret      | completed | ee818210-2ff5-4a4f-9153-69c3c83b4003 | 29f27a0e-dcd9-481e-a4ca-f764db1cd6df |
  | 50921223-33c2-44be-b3f5-17e28f92632d | barbican |      secret      | completed | 569d75d1-4798-4891-87b7-764b81f403f4 | cda7e8eb-a993-4dd4-8302-cc2b83096f65 |
  | e45171a5-fcf1-41a2-9e23-83a74b50116e | barbican | secret-container | completed | 85e2dee5-0b8c-4d7e-a1b7-a634788d49d7 | c02de39b-d379-4b4f-9e93-3392fb5bdf22 |
  +--------------------------------------+----------+------------------+-----------+--------------------------------------+--------------------------------------+
