# sunbeam-migrate
A tool that facilitates the migration from Charmed Openstack to Sunbeam.

## Examples

Prepare the sunbeam-migrate configuration:

```
$ export SUNBEAM_MIGRATE_CONFIG=~/migrate-config.yaml
$ cat > $SUNBEAM_MIGRATE_CONFIG <<EOF
log_level: info
cloud_config_file: /home/ubuntu/cloud-config.yaml
source_cloud_name: source-admin
destination_cloud_name: destination-admin
database_file: /home/ubuntu/.local/share/sunbeam-migrate/sqlite.db
EOF
```

Define the clouds.yaml file:

```
$ cat > /home/ubuntu/cloud-config.yaml <<EOF
clouds:
  source-admin:
    auth:
      auth_url: https://public.source.local/openstack-keystone/v3
      password: ***
      project_domain_name: admin_domain
      project_name: admin
      user_domain_name: admin_domain
      username: admin
    cacert: /home/ubuntu/sunbeam-ca/sunbeam-source-ca.pem
  destination-admin:
    auth:
      auth_url: https://public.destination.local/openstack-keystone/v3
      password: ***
      project_domain_name: admin_domain
      project_name: admin
      user_domain_name: admin_domain
      username: admin
    cacert: /home/ubuntu/sunbeam-ca/sunbeam-destination-ca.pem
EOF
```

Get migration handler capabilities:

```
$ sunbeam-migrate capabilities
+-----------------------------------------------------------------------------------------------------------------------+
|                                                   Migration handlers                                                  |
+----------+---------------------+-----------------------+---------------------------+------------------------+---------+
| Service  |    Resource type    | Member resource types | Associated resource types | Batch resource filters |  Ready  |
+----------+---------------------+-----------------------+---------------------------+------------------------+---------+
| Barbican |        secret       |           -           |             -             |        owner_id        | partial |
| Barbican |   secret-container  |           -           |           secret          |        owner_id        | partial |
|  Glance  |        image        |           -           |             -             |        owner_id        | partial |
| Neutron  |       network       |         subnet        |             -             |        owner_id        |  no-op  |
| Neutron  |    security-group   |  security-group-rule  |             -             |        owner_id        |  no-op  |
| Neutron  | security-group-rule |           -           |       security-group      |        owner_id        |  no-op  |
| Neutron  |        subnet       |           -           |          network          |        owner_id        |  no-op  |
+----------+---------------------+-----------------------+---------------------------+------------------------+---------+

$ sunbeam-migrate capabilities --resource-type=subnet
+--------------------------------------+
|          Migration handler           |
+---------------------------+----------+
|          Property         |  Value   |
+---------------------------+----------+
|          Service          | Neutron  |
|       Resource type       |  subnet  |
|   Member resource types   |    -     |
| Associated resource types | network  |
|   Batch resource filters  | owner_id |
|         Readiness         |  no-op   |
+---------------------------+----------+
```

Migrate a single image:

```
$ sunbeam-migrate start --resource-type=image 041ea0f1-93e8-4073-bfc1-ca961beec725
2025-11-12 14:29:43,482 INFO Initiating image migration, resource id: 041ea0f1-93e8-4073-bfc1-ca961beec725
2025-11-12 14:29:50,454 INFO Successfully migrated resource, destination id: aa83c834-3872-437e-9266-02b6eb4d4ff8
```

Migrate all images that match the specified filters, trying a dry-run first:

```
$ sunbeam-migrate start-batch --resource-type=image  --dry-run --filter "owner-id:516ddfe184c84f77889b33f027716e89"
2025-11-12 14:30:28,299 INFO DRY-RUN: image migration, resource id: 01c58135-8330-4792-a1ec-2277ec56eec9
2025-11-12 14:30:28,300 INFO Resource already migrated, skipping: 041ea0f1-93e8-4073-bfc1-ca961beec725. Migration: 1ab1d02c-f8f6-49df-bcd5-91e374e264ff

$ sunbeam-migrate start-batch --resource-type=image --filter "owner-id:516ddfe184c84f77889b33f027716e89"
2025-11-12 14:32:26,574 INFO Initiating image migration, resource id: 01c58135-8330-4792-a1ec-2277ec56eec9
2025-11-12 14:32:28,965 INFO Successfully migrated resource, destination id: 52d30bf9-0782-4244-beab-20065a5ce090
2025-11-12 14:32:28,970 INFO Resource already migrated, skipping: 041ea0f1-93e8-4073-bfc1-ca961beec725. Migration: 1ab1d02c-f8f6-49df-bcd5-91e374e264ff.

$ sunbeam-migrate start-batch --resource-type=image --filter "owner-id:516ddfe184c84f77889b33f027716e89"
2025-11-12 14:32:58,658 INFO Resource already migrated, skipping: 01c58135-8330-4792-a1ec-2277ec56eec9. Migration: 678a340a-f812-4aa2-acef-3d1aca2f4830.
2025-11-12 14:32:58,659 INFO Resource already migrated, skipping: 041ea0f1-93e8-4073-bfc1-ca961beec725. Migration: 1ab1d02c-f8f6-49df-bcd5-91e374e264ff
```

Listing migrations:

```
$ sunbeam-migrate list
+----------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                                        Migrations                                                                        |
+--------------------------------------+---------+---------------+-----------+--------------------------------------+--------------------------------------+
|                 UUID                 | Service | Resource type |   Status  |              Source ID               |            Destination ID            |
+--------------------------------------+---------+---------------+-----------+--------------------------------------+--------------------------------------+
| 1ab1d02c-f8f6-49df-bcd5-91e374e264ff |  glance |     image     | completed | 041ea0f1-93e8-4073-bfc1-ca961beec725 | aa83c834-3872-437e-9266-02b6eb4d4ff8 |
| 678a340a-f812-4aa2-acef-3d1aca2f4830 |  glance |     image     | completed | 01c58135-8330-4792-a1ec-2277ec56eec9 | 52d30bf9-0782-4244-beab-20065a5ce090 |
+--------------------------------------+---------+---------------+-----------+--------------------------------------+--------------------------------------+
```

Showing migration details:

```
$ sunbeam-migrate show 1ab1d02c-f8f6-49df-bcd5-91e374e264ff
+----------------------------------------------------------+
|                        Migration                         |
+-------------------+--------------------------------------+
|       Field       |                Value                 |
+-------------------+--------------------------------------+
|        Uuid       | 1ab1d02c-f8f6-49df-bcd5-91e374e264ff |
|     Created at    |      2025-11-12 14:29:43.486869      |
|     Updated at    |      2025-11-12 14:29:50.458527      |
|      Service      |                glance                |
|   Resource type   |                image                 |
|    Source cloud   |             source-admin             |
| Destination cloud |          destination-admin           |
|     Source id     | 041ea0f1-93e8-4073-bfc1-ca961beec725 |
|   Destination id  | aa83c834-3872-437e-9266-02b6eb4d4ff8 |
|       Status      |              completed               |
|   Error message   |                 None                 |
+-------------------+--------------------------------------+
```

Cleanup the source resource if the migration succeeds:

```
$ sunbeam-migrate start \
  --resource-type=image \
  --cleanup-source ff25220e-4adb-432c-88d3-92188c0d3cb6
```

The source cleanup can also be performed later, after inspecting the migrated resources.

```
# Do a dry run first.
$ sunbeam-migrate cleanup-source --resource-type=image --dry-run
2025-11-13 14:37:43,677 INFO DRY-RUN: migration succeeded, cleaning up source image: 42970672-7594-44ee-97f4-2074b40565e8
2025-11-13 14:37:43,677 INFO DRY-RUN: migration succeeded, cleaning up source image: 5333693c-80bf-43b7-b2e2-61178c68c48f
2025-11-13 14:37:43,678 INFO DRY-RUN: migration succeeded, cleaning up source image: 693b8c44-7d6b-484f-8576-4d365c3dfa92

$ sunbeam-migrate cleanup-source --resource-type=image 
2025-11-13 14:37:49,905 INFO Migration succeeded, cleaning up source image: 42970672-7594-44ee-97f4-2074b40565e8
2025-11-13 14:37:51,861 INFO Migration succeeded, cleaning up source image: 5333693c-80bf-43b7-b2e2-61178c68c48f
2025-11-13 14:37:52,152 INFO Migration succeeded, cleaning up source image: 693b8c44-7d6b-484f-8576-4d365c3dfa92
```

Creating and migrating Barbican secrets and containers:

```
$ cert_ref=`openstack secret store --name root-ca-cert -s certificate --file ~/ca/rootca.crt | grep "Secret href" | awk '{print $5}'`
$ key_ref=`openstack secret store --name root-ca-key -s private --file ~/ca/rootca.key | grep "Secret href" | awk '{print $5}'`

$ openstack secret container create \
  --name root-ca \
  --type certificate \
  --secret "certificate=$cert_ref" \
  --secret "private_key=$key_ref"

$ sunbeam-migrate start-batch --resource-type=secret-container --filter "owner-id:516ddfe184c84f77889b33f027716e89" --include-dependencies
2025-11-17 15:41:47,195 INFO Initiating secret-container migration, resource id: http://10.8.99.203/openstack-barbican/v1/containers/85e2dee5-0b8c-4d7e-a1b7-a634788d49d7
2025-11-17 15:41:48,147 INFO Migrating associated secret resource: http://10.8.99.203/openstack-barbican/v1/secrets/569d75d1-4798-4891-87b7-764b81f403f4
2025-11-17 15:41:48,148 INFO Initiating secret migration, resource id: http://10.8.99.203/openstack-barbican/v1/secrets/569d75d1-4798-4891-87b7-764b81f403f4
2025-11-17 15:41:50,795 INFO Successfully migrated resource, destination id: https://public2.sunbeam.local/openstack-barbican/v1/secrets/cda7e8eb-a993-4dd4-8302-cc2b83096f65
2025-11-17 15:41:50,802 INFO Migrating associated secret resource: http://10.8.99.203/openstack-barbican/v1/secrets/ee818210-2ff5-4a4f-9153-69c3c83b4003
2025-11-17 15:41:50,802 INFO Initiating secret migration, resource id: http://10.8.99.203/openstack-barbican/v1/secrets/ee818210-2ff5-4a4f-9153-69c3c83b4003
2025-11-17 15:41:53,162 INFO Successfully migrated resource, destination id: https://public2.sunbeam.local/openstack-barbican/v1/secrets/29f27a0e-dcd9-481e-a4ca-f764db1cd6df
2025-11-17 15:41:55,863 INFO Successfully migrated resource, destination id: https://public2.sunbeam.local/openstack-barbican/v1/containers/c02de39b-d379-4b4f-9e93-3392fb5bdf22

$ sunbeam-migrate list
+--------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                                          Migrations                                                                          |
+--------------------------------------+----------+------------------+-----------+--------------------------------------+--------------------------------------+
|                 UUID                 | Service  |  Resource type   |   Status  |              Source ID               |            Destination ID            |
+--------------------------------------+----------+------------------+-----------+--------------------------------------+--------------------------------------+
| c2e26b76-ec50-45e1-8b82-ceded96cedb3 | barbican |      secret      | completed | ee818210-2ff5-4a4f-9153-69c3c83b4003 | 29f27a0e-dcd9-481e-a4ca-f764db1cd6df |
| 50921223-33c2-44be-b3f5-17e28f92632d | barbican |      secret      | completed | 569d75d1-4798-4891-87b7-764b81f403f4 | cda7e8eb-a993-4dd4-8302-cc2b83096f65 |
| e45171a5-fcf1-41a2-9e23-83a74b50116e | barbican | secret-container | completed | 85e2dee5-0b8c-4d7e-a1b7-a634788d49d7 | c02de39b-d379-4b4f-9e93-3392fb5bdf22 |
+--------------------------------------+----------+------------------+-----------+--------------------------------------+--------------------------------------+
```

## TODOs

* Automatically migrate dependent/component resources.
  * We could add some flags, making this optional
    * --cascade -> migrate component resources (e.g. network -> subnet)
    * (implemented) --include-dependencies -> e.g. subnet -> network, instance -> volume, etc
* Add new resource handlers.
* Implement manager unit tests
* Consider having a "mappings.yaml" file, allowing a different resource from the destination
  cloud to be used instead of an exact copy of the source resource.
  For example, we might want to use a different set of volume types, flavors or networks,
  matching the specifics of the destination cloud.
  Example:
  ```
  volume-flavors:
    - source-id: <uuid>
      destination-id: <uuid>
  networks:
    - source-id: <uuid>
      destination-id: <uuid>
  ```
* Instead of dry runs, have migration plans similar to Terraform plans. The user could then
  see the resources that are going to be migrated, trigger the migration plan and then check
  the migration status for the specified plan.
  The resource dependencies could be modeled through a tree.

## Functional tests

`sunbeam_migrate/tests/integration` contains integration tests that exercise every supported
migration handler.

The tests receive a configuration file similar to the standard `SUNBEAM_MIGRATE_CONFIG` file,
having a few additional test specific settings.

Use the following to invoke the tests:

```
$ export SUNBEAM_MIGRATE_CONFIG=~/migrate-config-test.yaml
$ cat > $SUNBEAM_MIGRATE_CONFIG <<EOF
log_level: info
cloud_config_file: /home/ubuntu/cloud-config.yaml
source_cloud_name: source-admin
destination_cloud_name: destination-admin
database_file: /home/ubuntu/.local/share/sunbeam-migrate/sqlite.db
skip_project_purge: false
EOF

$ tox -e integration
```

Use the `-k` parameter to specify which test(s) to run:

```
tox -e integration -- -k test_migrate_image_and_cleanup
```
