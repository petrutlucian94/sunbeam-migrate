# sunbeam-migrate
A tool that facilitates the migration from Charmed Openstack to Sunbeam.

## Documentation

* Main page: https://sunbeam-migrate.readthedocs.io
* Tutorial: https://sunbeam-migrate.readthedocs.io/en/latest/tutorial/get-started-with-sunbeam-migrate/
* Migration handlers: https://sunbeam-migrate.readthedocs.io/en/latest/how-to/migration-handlers/

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
* Migrate share access rules (configurable)
* Cross-tenant keypair and secret migrations
  * The keypairs do not have an unique ID. Cross-tenant requests must include
    the keypair name and the project/user ID, even get/list.
  * We'd need to include the owner information along with the resource id in:
    * `get_source_resource_ids` -> may return a `Resource` object
    * `perform_individual_migration`
    * `get_associated_resources`
    * The migration `start` command
    * internal database queries and Openstack requests that currently rely
      solely on the resource ID
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
