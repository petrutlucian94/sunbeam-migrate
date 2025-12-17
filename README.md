# sunbeam-migrate
A tool that facilitates the migration from Charmed Openstack to Sunbeam.

## Documentation

* Main page: https://sunbeam-migrate.readthedocs.io
* Tutorial: https://sunbeam-migrate.readthedocs.io/en/latest/tutorial/get-started-with-sunbeam-migrate/

## Examples

<!-- TODO: move the following to the docs. -->

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

## Migrating Load Balancers

Octavia load balancers are being migrated along with all their components: listeners, pools, members, and health monitors. Use `--include-dependencies` to automatically migrate the VIP network and subnet.

```
$ sunbeam-migrate start --resource-type=load-balancer f76d0bf1-bbb9-45cb-94d5-a7cbc7647bbd --include-dependencies
2025-12-05 14:44:59,67 INFO Initiating load-balancer migration, resource id: f76d0bf1-bbb9-45cb-94d5-a7cbc7647bbd
2025-12-05 14:45:01,478 INFO Migrating associated subnet resource: dfa7fa45-efb1-477b-8d91-64e7c02a93e8
2025-12-05 14:45:01,486 INFO Initiating subnet migration, resource id: dfa7fa45-efb1-477b-8d91-64e7c02a93e8
2025-12-05 14:45:03,633 INFO Migrating associated network resource: 72505950-631c-4c6a-b52e-e5ee4c227aeb
2025-12-05 14:45:03,634 INFO Initiating network migration, resource id: 72505950-631c-4c6a-b52e-e5ee4c227aeb
2025-12-05 14:45:09,123 INFO Successfully migrated resource, destination id: 8caee94f-0c0f-47a8-8641-f7dfba9927e0
2025-12-05 14:45:16,816 INFO Successfully migrated resource, destination id: e6235058-dea0-4bd4-9108-4f1098d680e5
2025-12-05 14:45:16,819 INFO Associated resource network 72505950-631c-4c6a-b52e-e5ee4c227aeb already completed (migration dfc323a6-17ed-46f9-8227-c513f3c1192a), skipping duplicate migration
2025-12-05 14:45:20,178 INFO Gathering load balancer components from source: f76d0bf1-bbb9-45cb-94d5-a7cbc7647bbd
2025-12-05 14:45:29,515 INFO Created load balancer 97e19b30-f194-4341-ad3a-aa8cec9b7002 on destination (source: f76d0bf1-bbb9-45cb-94d5-a7cbc7647bbd)
2025-12-05 14:45:36,568 INFO Created listener e28c6562-cb9c-4c96-9743-d151ddb482df on destination (source: 9b900e12-af9f-4765-9d89-dda878adf237)
2025-12-05 14:45:42,436 INFO Created pool aefc5bb6-fda1-4fb2-a9b6-17bb4c27c328 on destination (source: ef2feeae-e2a0-4f2f-a20f-fe5dfd4ddcb2)
2025-12-05 14:45:48,210 INFO Created health monitor 99df81df-9d1f-4904-8431-fd72706b4d03 on destination (source: c7d07146-bf1b-4fd4-9ccf-00d6e6a2e6e4)
2025-12-05 14:45:57,151 INFO Created member bbe5c728-4e08-4469-85f9-78dd134a0696 in pool aefc5bb6-fda1-4fb2-a9b6-17bb4c27c328 on destination (source: 3f8bd027-5c88-482e-8864-be355ac6654e)
2025-12-05 14:46:05,279 INFO Created member 0acee607-7c59-4cf9-9381-468a0f3d119c in pool aefc5bb6-fda1-4fb2-a9b6-17bb4c27c328 on destination (source: 74badb77-f27e-4104-bcba-b2404c661bf5)
2025-12-05 14:46:10,617 INFO Successfully migrated resource, destination id: 97e19b30-f194-4341-ad3a-aa8cec9b7002
```

The migration process:
1. **Gathers components** from the source load balancer (listeners, pools, members, health monitors)
2. **Creates the load balancer** on the destination with the VIP settings
3. **Creates listeners** one by one, waiting for the LB to be ACTIVE between operations
4. **Creates pools** associated with each listener
5. **Creates health monitors** for pools that have them
6. **Creates members** in each pool with their subnet mappings


## Migrating DNS zones and records

Designate zones can be migrated with `--resource-type=dns-zone`. The handler recreates the DNS zone with all of its recordsets on the destination.

```
$ sunbeam-migrate start --resource-type=dns-zone 68cfff5c-02dd-44b6-a436-b87d82f2a1d6
2025-12-15 15:42:58,313 INFO Initiating dns-zone migration, resource id: 68cfff5c-02dd-44b6-a436-b87d82f2a1d6
2025-12-15 15:43:11,744 INFO Creating zone test.example.com. on destination
2025-12-15 15:43:12,883 INFO Created zone test.example.com. on destination (id: d8e32ae7-1363-4900-98a1-abb0409884e4)
2025-12-15 15:43:12,884 INFO Copying recordsets from source zone 68cfff5c-02dd-44b6-a436-b87d82f2a1d6 to destination zone d8e32ae7-1363-4900-98a1-abb0409884e4
2025-12-15 15:43:13,219 INFO Copying recordset: note.test.example.com. (TXT)
2025-12-15 15:43:14,656 INFO Created recordset: note.test.example.com. (TXT)
2025-12-15 15:43:14,688 INFO Successfully migrated dns-zone resource, destination id: d8e32ae7-1363-4900-98a1-abb0409884e4
```


## Potential future improvements

* Add new resource migration handlers.
* Implement manager unit tests
* Instead of dry runs, have migration plans similar to Terraform plans. The user could then
  see the resources that are going to be migrated, trigger the migration plan and then check
  the migration status for the specified plan.
  The resource dependencies could be modeled through a tree.
* Propagate the dry run to linked resources.
* Allow skipping properties that may cause conflicts on the destination cloud:
  * ~~net segmentation id~~
  * ~~mac addresses~~
  * instance fixed IPs
  * floating IPs
    * can be skipped completely or just the actual address
  * router IP
* Attach floating ips to instance ports
* Cross-tenant keypair and secret migrations
  * The keypairs do not have an unique ID. Cross-tenant requests must include
    the keypair name and the project/user ID, even get/list.
  * We'd need to include the owner information along with the resource id in:
    * `get_source_resource_ids` -> may return a `Resource` object
    * `perform_individual_migration`
    * `get_associated_resources`
    * The migration `start` command
  * We have a similar situation with Barbican secrets and secret containers,
    where we aren't normally allowed to retrieve secrets owned by other projects.

## Functional tests

`sunbeam_migrate/tests/integration` contains integration tests that exercise every supported
migration handler.

The following requirements must be installed first:

```
sudo apt-get update
sudo apt-get install -y tox nfs-common
sudo snap install --classic astral-uv
```

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
preserve_volume_type: true

# settings used by the integration tests
skip_project_purge: true
image_id:  334ad443-352f-475b-8c9b-f16825455a3f
flavor_id: f128eb24-47ec-427a-a2a6-ccfbafce105f
EOF

$ tox -e integration
```

Use the `-k` parameter to specify which test(s) to run:

```
tox -e integration -- -k test_migrate_image_and_cleanup
```

A set of temporary credentials will be created for every test module. If multi-tenant
mode is enabled, the tests will use one tenant for creating the test resources
(the resource owner) and a separate tenant for initiating the migration (called "requester").
