.. _getting_started_ref:

Getting started with Sunbeam Migrate
====================================

.. include:: ../how-to/install.rst

Configuration
-------------

``sunbeam-migrate`` receives a YAML configuration file that defines:

* the source and destination cloud
* credentials used to identify and migrate resources
* internal Sqlite database location
* timeouts
* whether to preserve certain resource properties (e.g. volume types,
  availability zones, network segmentation IDs, MAC addresses, etc)
* multi-tenant mode

See the :ref:`configuration reference<config_ref>` for the full list of
``sunbeam-migrate`` options.

Let's define a minimal configuration file:

.. code-block:: bash

  export SUNBEAM_MIGRATE_CONFIG=~/migrate-config.yaml
  cat > $SUNBEAM_MIGRATE_CONFIG <<EOF
  log_level: info
  cloud_config_file: /home/ubuntu/cloud-config.yaml
  source_cloud_name: source-admin
  destination_cloud_name: destination-admin
  database_file: /home/ubuntu/.local/share/sunbeam-migrate/sqlite.db
  multitenant_mode: true
  EOF

If multi-tenant mode is enabled, the tool will automatically migrate the project
and user that owns a given resource, ensuring that the destination resource will
be owned by the same tenant. It also allows migrating resources owned by other
projects.

Note that the multi-tenant mode requires admin privileges.

Next we are going to specify the Openstack credentials using a standard
`clouds yaml`_ file:

.. code-block:: bash

  cat > /home/ubuntu/cloud-config.yaml <<EOF
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

Make sure to fill in the right OpenStack credentials and Keystone addresses.
The cloud names must match the ones specified in the ``sunbeam-migrate``
configuration file.

By using the ``SUNBEAM_MIGRATE_CONFIG`` environment variable, we no longer
have to specify it every time we run a ``sunbeam-migrate`` command.

Migrating resources
-------------------

For the purpose of this tutorial, we are going to create and migrate a few
Glance images.

.. code-block:: bash

  export OS_CLIENT_CONFIG_FILE=/home/ubuntu/cloud-config.yaml

  dd if=/dev/urandom of=/tmp/test-image bs=$(( 1024 * 1024 )) count=4

  for idx in `seq 1 3`; do
    openstack --os-cloud source-admin \
      image create \
      --disk-format=raw \
      --container-format=bare \
      test-image-$idx < /tmp/test-image
  done

We can now move one of those images using the following command. Make sure to
specify the correct image ID.

.. code-block:: none

  sunbeam-migrate start \
    --resource-type=image \
    --include-dependencies \
    --cleanup-source \
    161081e2-6617-471e-b341-c2e7b42201b8

  2025-12-16 13:47:33,129 INFO Initiating image migration, resource id: 161081e2-6617-471e-b341-c2e7b42201b8
  2025-12-16 13:47:33,914 INFO Migrating associated project resource: 609c48d29a1b483cb2d8a75bc84abdf7
  2025-12-16 13:47:33,915 INFO Initiating project migration, resource id: 609c48d29a1b483cb2d8a75bc84abdf7
  2025-12-16 13:47:34,464 INFO Migrating associated domain resource: 38da677b7dd944f8bce50bba4342bda6
  2025-12-16 13:47:34,465 INFO Initiating domain migration, resource id: 38da677b7dd944f8bce50bba4342bda6
  2025-12-16 13:47:35,897 WARNING Domain already exists: 6f05f02ce89b4976bb6f06bce3d2a40a admin_domain
  2025-12-16 13:47:35,906 INFO Successfully migrated domain resource, destination id: 6f05f02ce89b4976bb6f06bce3d2a40a
  2025-12-16 13:47:37,894 WARNING Project already exists: d1872c224487448cbea6408cce156bef admin
  2025-12-16 13:47:37,899 INFO Successfully migrated project resource, destination id: d1872c224487448cbea6408cce156bef
  2025-12-16 13:47:41,290 INFO Successfully migrated image resource, destination id: fa30ed55-22e2-4bd0-8550-1e8f3baaad37
  2025-12-16 13:47:41,295 INFO Migration succeeded, cleaning up source image: 161081e2-6617-471e-b341-c2e7b42201b8

``sunbeam-migrate`` can automatically identify and migrate resource dependencies.
For example, flavors and volumes are Nova instance dependencies. Networks are
subnet dependencies. Projects and users are also considered dependencies if the
multi-tenant mode is enabled.

If the ``--include-dependencies`` flag is specified, the migration will cascade
to resource dependencies. If the flag is unset and there are missing dependencies,
the migration will fail and the user will receive a list of resources that have
to be migrated.

"Members" are contained resources that are migrated *after* the parent resource.
These resources are optional and can be migrated using ``--include-members``.
For example, subnets are members of networks.

Member resources may also be migrated separately, after the parent resource was
migrated.

Getting back to our example, you may have noticed the ``--cleanup-source`` flag.
If set, the resource(s) are automatically removed from the source cloud if the
migration succeeds. This does not apply to shared dependencies, such as volume
types or flavors.

Users may choose to cleanup the resources separately through the
``sunbeam-migrate cleanup-source`` command, which we are going to showcase
:ref:`a bit later<cleanup_source_command>`.

Batch migrations
----------------

``sunbeam-migrate`` can also move a group of resources that match a given
filter.

The following command migrates all the images of a given project. We'll do a
dry run first:

.. code-block:: none

  sunbeam-migrate start-batch \
    --resource-type=image \
    --filter "project-id:609c48d29a1b483cb2d8a75bc84abdf7" \
    --dry-run

  2025-12-16 14:14:17,851 INFO DRY-RUN: image migration, resource id: f02d3b07-7008-486d-b298-a08b1b1f3e2e, cleanup source: False
  2025-12-16 14:14:17,852 INFO DRY-RUN: image migration, resource id: 19da365c-ddb4-432c-92f2-60b966d347fe, cleanup source: False
  2025-12-16 14:14:17,853 INFO DRY-RUN: image migration, resource id: 5f7f24cc-b700-4195-80af-50e61adff91d, cleanup source: False

Now without the ``--dry-run`` flag:

.. code-block:: none

  sunbeam-migrate start-batch \
                --resource-type=image \
                --filter "project-id:609c48d29a1b483cb2d8a75bc84abdf7"

  2025-12-16 14:15:01,646 INFO Initiating image migration, resource id: f02d3b07-7008-486d-b298-a08b1b1f3e2e
  2025-12-16 14:15:05,329 INFO Successfully migrated image resource, destination id: 93df67bc-fb7a-4bfa-89a7-3dbfa859472e
  2025-12-16 14:15:05,334 INFO Initiating image migration, resource id: 19da365c-ddb4-432c-92f2-60b966d347fe
  2025-12-16 14:15:08,354 INFO Successfully migrated image resource, destination id: 44659c49-36cd-4ea9-863e-e39916370be0
  2025-12-16 14:15:08,360 INFO Initiating image migration, resource id: 5f7f24cc-b700-4195-80af-50e61adff91d
  2025-12-16 14:15:17,138 INFO Successfully migrated image resource, destination id: e1a526cf-1ac5-4532-a5f8-1069ea585c22

If we repeat the command, already migrated resources will be skipped:

.. code-block:: none

  sunbeam-migrate start-batch \
                --resource-type=image \
                --filter "project-id:609c48d29a1b483cb2d8a75bc84abdf7"

  2025-12-16 14:20:43,414 INFO Resource already migrated, skipping: f02d3b07-7008-486d-b298-a08b1b1f3e2e. Migration: 7d3449c3-a542-48d7-ab99-0649dd066976.
  2025-12-16 14:20:43,415 INFO Resource already migrated, skipping: 19da365c-ddb4-432c-92f2-60b966d347fe. Migration: 3928df33-1d65-4082-9429-7719a37de051.
  2025-12-16 14:20:43,415 INFO Resource already migrated, skipping: 5f7f24cc-b700-4195-80af-50e61adff91d. Migration: 0209b968-10ae-4770-ac6e-6c454fb4323f.

.. include:: ../how-to/operations/list.rst

Cleaning up migrations
----------------------

.. _cleanup_source_command:

Migrated resources are removed from the source cloud automatically if the
``--cleanup-source`` flag is specified.

Alternatively, users may want to remove the original resources at a later time,
after validating the migrations on the destination cloud.

Use the ``cleanup-source`` command like so:

.. code-block:: none

  sunbeam-migrate cleanup-source --resource-type=image

  2025-12-16 14:33:32,897 INFO Migration succeeded, cleaning up source image: 5f7f24cc-b700-4195-80af-50e61adff91d
  2025-12-16 14:33:34,575 INFO Migration succeeded, cleaning up source image: 19da365c-ddb4-432c-92f2-60b966d347fe
  2025-12-16 14:33:35,539 INFO Migration succeeded, cleaning up source image: f02d3b07-7008-486d-b298-a08b1b1f3e2e
  2025-12-16 14:33:36,527 INFO Migration succeeded, cleaning up source image: 5199e62b-4dac-4a9d-b8b2-7b616e270ea6

This removes all the source images that have been successfully migrated. Note
that it also allows filtering by resource id or service type.

.. code-block:: none

  sunbeam-migrate cleanup-source -h

  Usage: sunbeam-migrate cleanup-source [OPTIONS]

    Cleanup the source after successful migrations.

    Receives optional filters that specify which resources to clean up.

  Options:
    --service TEXT        Filter by service name
    --resource-type TEXT  Filter by resource type
    --source-id TEXT      Filter by source resource id.
    --all                 Cleanup all succeeded migrations.
    --dry-run             Dry run: only log the resources to be deleted.
    -h, --help            Show this message and exit.

.. include:: ../how-to/operations/capabilities.rst

.. include:: ../how-to/operations/external-migrations.rst
