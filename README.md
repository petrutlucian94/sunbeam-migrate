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
+-------------------------------------------------------------------------------------------------------------+
|                                              Migration handlers                                             |
+----------+---------------------+-----------------------+---------------------------+------------------------+
| Service  |    Resource type    | Member resource types | Associated resource types | Batch resource filters |
+----------+---------------------+-----------------------+---------------------------+------------------------+
| Barbican |        secret       |           -           |             -             |        owner_id        |
| Barbican |   secret-container  |           -           |           secret          |        owner_id        |
|  Cinder  |        volume       |           -           |        volume-type        |        owner_id        |
|  Cinder  |     volume-type     |           -           |             -             |           -            |
|  Glance  |        image        |           -           |             -             |        owner_id        |
| Neutron  |       network       |         subnet        |             -             |        owner_id        |
| Neutron  |        router       |         subnet        |      network, subnet      |        owner_id        |
| Neutron  |    security-group   |  security-group-rule  |             -             |        owner_id        |
| Neutron  | security-group-rule |           -           |       security-group      |        owner_id        |
| Neutron  |        subnet       |           -           |          network          |        owner_id        |
|   Nova   |        flavor       |           -           |             -             |           -            |
+----------+---------------------+-----------------------+---------------------------+------------------------+

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
|         Readiness         | partial  |
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

## Migrating Networks and Security Groups

Migrate the network with all subnets by using the `--include-members`:

```
$ sunbeam-migrate start --resource-type=network bd0c1019-3d1b-4f64-86c4-c4c0e04a6a36 --include-members
2025-11-24 12:15:24,799 INFO Initiating network migration, resource id: bd0c1019-3d1b-4f64-86c4-c4c0e04a6a36
2025-11-24 12:15:30,702 INFO Migrating member subnet resource: 9040a40d-d875-4260-927c-f83f60ec4d8c
2025-11-24 12:15:30,704 INFO Initiating subnet migration, resource id: 9040a40d-d875-4260-927c-f83f60ec4d8c
2025-11-24 12:15:39,575 INFO Successfully migrated resource, destination id: 07f0c904-956f-47b8-84ce-bf751e4dfdad
2025-11-24 12:15:39,578 INFO Migrating member subnet resource: 940b789e-cf85-4dad-ae7d-26d120eeff7f
2025-11-24 12:15:39,578 INFO Initiating subnet migration, resource id: 940b789e-cf85-4dad-ae7d-26d120eeff7f
2025-11-24 12:15:48,779 INFO Successfully migrated resource, destination id: 8df27647-c76f-43c2-9f53-20599873569b
2025-11-24 12:15:48,782 INFO Successfully migrated resource, destination id: 29c3ab49-5208-4e62-8399-c2ed09be6988
```

Migrate the security groups with all their security group rules by running:

**NOTE**: Security group rules may reference other security groups (via `remote_group_id`). Ensure all security groups are migrated before migrating rules. One simple workaround would be to perform the **security group batched migration** in two steps: one without `--include-members` and then another run with `--include-members`.

```
$ sunbeam-migrate start --resource-type=security-group fcbdfef5-9eb2-4ab9-8fc7-742883b8c511  --include-members
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
```

```
$ sunbeam-migrate list
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
```

For migrating a subnet, you must migrate the network or run the command with `--include-dependencies`:

```
$ sunbeam-migrate start --resource-type=subnet 9040a40d-d875-4260-927c-f83f60ec4d8c --include-dependencies
2025-11-24 12:23:31,286 INFO Initiating subnet migration, resource id: 9040a40d-d875-4260-927c-f83f60ec4d8c
2025-11-24 12:23:33,150 INFO Migrating associated network resource: bd0c1019-3d1b-4f64-86c4-c4c0e04a6a36
2025-11-24 12:23:33,150 INFO Initiating network migration, resource id: bd0c1019-3d1b-4f64-86c4-c4c0e04a6a36
2025-11-24 12:23:37,982 INFO Successfully migrated resource, destination id: 7798eb6e-7d57-40bf-b434-a0c0c51c219f
2025-11-24 12:23:46,536 INFO Successfully migrated resource, destination id: 2c4491d1-035a-43a6-9f89-74751eabebfa

$ sunbeam-migrate list
+----------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                                        Migrations                                                                        |
+--------------------------------------+---------+---------------+-----------+--------------------------------------+--------------------------------------+
|                 UUID                 | Service | Resource type |   Status  |              Source ID               |            Destination ID            |
+--------------------------------------+---------+---------------+-----------+--------------------------------------+--------------------------------------+
| ffeaa9ec-e9de-497f-acb1-8792fd29781f | neutron |    network    | completed | bd0c1019-3d1b-4f64-86c4-c4c0e04a6a36 | 7798eb6e-7d57-40bf-b434-a0c0c51c219f |
| 9ead5fa8-0d3f-4ab6-9bc3-c4dc55a79199 | neutron |     subnet    | completed | 9040a40d-d875-4260-927c-f83f60ec4d8c | 2c4491d1-035a-43a6-9f89-74751eabebfa |
+--------------------------------------+---------+---------------+-----------+--------------------------------------+--------------------------------------+
```

## Migrating Routers

When migrating Neutron routers, use `--include-dependencies` to include the external gateway network. Note that it can also be migrated separately.

Other subnets connected to the router can be automatically covered using `--include-members`.

```
$ sunbeam-migrate start --resource-type=router 897e4a69-c808-4065-9450-b1231b255c22 --include-dependencies --include-members
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
```


## Registering external migrations

`sunbeam-migrate` normally creates exact copies of the migrated resources. This isn't always
desired.

Let's take volume types for example. The extra specs may contain backend specific properties
that are not applicable on the destination cloud (e.g. backend name, pool name or other
storage backend settings).

Instead, users can recreate the volume type manually on the destination cloud and then use
the `register-external` command to register the migration. Subsequent volume migrations
will automatically use the manually created volume type.

```
$ sunbeam-migrate register-external --resource-type volume-type f104d538-a2f0-4897-92ea-9887bfb1c926 491481cd-d9d0-4639-afe4-d5f07223f4db

$ sunbeam-migrate show fd91c637-7b91-4fb6-9bd6-afb84c9d79a1
+----------------------------------------------------------+
|                        Migration                         |
+-------------------+--------------------------------------+
|       Field       |                Value                 |
+-------------------+--------------------------------------+
|        Uuid       | fd91c637-7b91-4fb6-9bd6-afb84c9d79a1 |
|     Created at    |      2025-12-02 10:44:22.062347      |
|     Updated at    |                 None                 |
|      Service      |                cinder                |
|   Resource type   |             volume-type              |
|    Source cloud   |             source-admin             |
| Destination cloud |          destination-admin           |
|     Source id     | f104d538-a2f0-4897-92ea-9887bfb1c926 |
|   Destination id  | 491481cd-d9d0-4639-afe4-d5f07223f4db |
|       Status      |              completed               |
|   Error message   |                 None                 |
|      Archived     |                False                 |
|   Source removed  |                False                 |
|      External     |                 True                 |
+-------------------+--------------------------------------+
```

## TODOs

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
