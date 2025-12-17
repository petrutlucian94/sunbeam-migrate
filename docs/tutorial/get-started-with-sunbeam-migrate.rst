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

Listing migrations
------------------

Use the following command to list the performed migrations:

.. code-block:: none

  sunbeam-migrate list

  +-----------------------------------------------------------------------------------------------------------------------------------------------------------+
  |                                                                         Migrations                                                                        |
  +--------------------------------------+----------+---------------+-----------+--------------------------------------+--------------------------------------+
  |                 UUID                 | Service  | Resource type |   Status  |              Source ID               |            Destination ID            |
  +--------------------------------------+----------+---------------+-----------+--------------------------------------+--------------------------------------+
  | 0209b968-10ae-4770-ac6e-6c454fb4323f |  glance  |     image     | completed | 5f7f24cc-b700-4195-80af-50e61adff91d | e1a526cf-1ac5-4532-a5f8-1069ea585c22 |
  | 3928df33-1d65-4082-9429-7719a37de051 |  glance  |     image     | completed | 19da365c-ddb4-432c-92f2-60b966d347fe | 44659c49-36cd-4ea9-863e-e39916370be0 |
  | 7d3449c3-a542-48d7-ab99-0649dd066976 |  glance  |     image     | completed | f02d3b07-7008-486d-b298-a08b1b1f3e2e | 93df67bc-fb7a-4bfa-89a7-3dbfa859472e |
  | 0984b0c0-a5a0-459d-8132-548ca8e6574f | keystone |     domain    | completed |   38da677b7dd944f8bce50bba4342bda6   |   6f05f02ce89b4976bb6f06bce3d2a40a   |
  | 75261d19-42a0-4b96-9012-b648d2cc10b9 | keystone |    project    | completed |   609c48d29a1b483cb2d8a75bc84abdf7   |   d1872c224487448cbea6408cce156bef   |
  | 7dc686ad-8ba3-476b-b0e5-b3568513a2d6 |  glance  |     image     | completed | 161081e2-6617-471e-b341-c2e7b42201b8 | fa30ed55-22e2-4bd0-8550-1e8f3baaad37 |
  | 08a69ab8-eab6-43b3-9756-6a530eeec09f |  glance  |     image     | completed | 5199e62b-4dac-4a9d-b8b2-7b616e270ea6 | d0accda5-3120-43e2-8bc8-80ef8e701ee4 |
  | 3204f867-0124-4bf1-88ba-bad7c3ec37be | keystone |      user     | completed |   7c58db938ee744c5b14a966a2fb8ed1e   |   2aa41d61e1c94d27b6cdab56c7003b9f   |
  | 66d03194-53de-462e-9812-b12a8962690d | keystone |    project    | completed |   cfc158bad223468c82c6570486113a4d   |   080674ff96894e04a077274bede11b26   |
  | 4fb1e97c-0850-46ff-a4eb-f21bcad03a7a |  glance  |     image     | completed | f4631001-e724-405d-a50c-d1e8cfbf618c | e4453093-2de5-44b1-b3ae-01a050bd2491 |
  | 9465d306-344f-4430-9ed0-3f932a824727 | neutron  |      port     | completed | a21256ea-dc86-4560-ab75-44a53f950ea7 | 1a475258-0a60-443d-acdd-daa303746632 |
  | 558b900b-e8ae-482f-a044-c440058bbf25 |   nova   |    instance   | completed | e54d012c-ff5d-4e26-9a79-6829aa191450 | 4f9e1849-a2d4-4aed-a43c-2158278c6d77 |
  | abd5745d-79ca-4851-bbf3-5fbd76c875a3 |  glance  |     image     | completed | 3f46206f-ee62-4c5f-ab7a-748904b72e59 | 2472ef15-5dc8-43e0-8017-b90d976184c9 |
  | 0c32a114-d944-4675-a6a3-b9410338ff21 |   nova   |     flavor    | completed | f128eb24-47ec-427a-a2a6-ccfbafce105f | 10f6b1f2-72e0-4d76-a245-0ae38d37d078 |
  | 656db9d7-6bbe-4c73-b31e-51fbf785ce18 | neutron  |      port     | completed | 58d59325-ccd8-42c4-9b6f-779335eb20a9 | c2045210-6599-4967-9dce-bc6c9cb84f0a |
  | 507a1504-fb7a-4810-a55b-31fe2875cec2 |   nova   |    instance   | completed | 7d65f412-f074-49e5-bd50-0cfcbad1e982 | 06b84ecf-9635-470a-bf16-91faf3d62102 |
  | 44816873-d770-421e-b50b-8ae9b26a4949 | neutron  |     subnet    | completed | a428d163-5a5b-4c0a-bee2-b0b025464957 | e3803961-6816-47e2-89ac-977affa68eec |
  | cc6b998c-550c-4060-a91b-161dd6ed3d8a | neutron  |    network    | completed | 51af7bff-b5f6-4d1b-95e6-1f540ef91995 | 0a1dd38f-ed68-4b00-b4ef-6466c3694df1 |
  +--------------------------------------+----------+---------------+-----------+--------------------------------------+--------------------------------------+

Each migration is identified through an UUID. We can obtain more details about
a given migration like so:

.. code-block:: none

  sunbeam-migrate show 0209b968-10ae-4770-ac6e-6c454fb4323f

  +----------------------------------------------------------+
  |                        Migration                         |
  +-------------------+--------------------------------------+
  |       Field       |                Value                 |
  +-------------------+--------------------------------------+
  |        Uuid       | 0209b968-10ae-4770-ac6e-6c454fb4323f |
  |     Created at    |      2025-12-16 14:15:08.361107      |
  |     Updated at    |      2025-12-16 14:15:17.140378      |
  |      Service      |                glance                |
  |   Resource type   |                image                 |
  |    Source cloud   |             source-admin             |
  | Destination cloud |          destination-admin           |
  |     Source id     | 5f7f24cc-b700-4195-80af-50e61adff91d |
  |   Destination id  | e1a526cf-1ac5-4532-a5f8-1069ea585c22 |
  |       Status      |              completed               |
  |   Error message   |                 None                 |
  |      Archived     |                False                 |
  |   Source removed  |                False                 |
  |      External     |                False                 |
  +-------------------+--------------------------------------+

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

Migration handlers
------------------

Run the following command to see the list of migration handlers and how they
define resource relations:

.. code-block:: none

  sunbeam-migrate capabilities

  +-------------------------------------------------------------------------------------------------------------------------------------------+
  |                                                             Migration handlers                                                            |
  +-----------+---------------------+-----------------------+--------------------------------------------------------+------------------------+
  |  Service  |    Resource type    | Member resource types |               Associated resource types                | Batch resource filters |
  +-----------+---------------------+-----------------------+--------------------------------------------------------+------------------------+
  |  Barbican |        secret       |           -           |                           -                            |           -            |
  |  Barbican |   secret-container  |           -           |                         secret                         |           -            |
  |   Cinder  |        volume       |           -           |               volume-type, project, user               |       project_id       |
  |   Cinder  |     volume-type     |           -           |                           -                            |           -            |
  | Designate |       dns-zone      |           -           |                        project                         |       project_id       |
  |   Glance  |        image        |           -           |                        project                         |       project_id       |
  |  Keystone |        domain       |     project, user     |                           -                            |           -            |
  |  Keystone |       project       |          user         |                         domain                         |       domain_id        |
  |  Keystone |         role        |           -           |                         domain                         |       domain_id        |
  |  Keystone |         user        |           -           |                 domain, project, role                  |       domain_id        |
  |   Manila  |        share        |           -           |                  share-type, project                   |       project_id       |
  |   Manila  |      share-type     |           -           |                           -                            |           -            |
  |  Neutron  |     floating-ip     |           -           |            network, subnet, router, project            |       project_id       |
  |  Neutron  |       network       |         subnet        |                        project                         |       project_id       |
  |  Neutron  |         port        |           -           |        network, subnet, security-group, project        |           -            |
  |  Neutron  |        router       |         subnet        |                network, subnet, project                |       project_id       |
  |  Neutron  |    security-group   |  security-group-rule  |                        project                         |       project_id       |
  |  Neutron  | security-group-rule |           -           |                security-group, project                 |       project_id       |
  |  Neutron  |        subnet       |           -           |                    network, project                    |       project_id       |
  |    Nova   |        flavor       |           -           |                           -                            |           -            |
  |    Nova   |       instance      |           -           | image, volume, flavor, keypair, network, port, project |       project_id       |
  |    Nova   |       keypair       |           -           |                           -                            |           -            |
  |  Octavia  |    load-balancer    |           -           |         network, subnet, floating-ip, project          |       project_id       |
  +-----------+---------------------+-----------------------+--------------------------------------------------------+------------------------+

We can also specify the resource type like so:

.. code-block:: none

  sunbeam-migrate capabilities --resource-type=instance

  +------------------------------------------------------------------------------------+
  |                                 Migration handler                                  |
  +---------------------------+--------------------------------------------------------+
  |          Property         |                         Value                          |
  +---------------------------+--------------------------------------------------------+
  |          Service          |                          Nova                          |
  |       Resource type       |                        instance                        |
  |   Member resource types   |                           -                            |
  | Associated resource types | image, volume, flavor, keypair, network, port, project |
  |   Batch resource filters  |                       project_id                       |
  +---------------------------+--------------------------------------------------------+

Registering external migrations
-------------------------------

``sunbeam-migrate`` normally creates exact copies of the migrated resources.
This isn't always desired.

Let's take volume types for example. The extra specs may contain backend
specific properties that are not applicable on the destination cloud
(e.g. backend name, pool name or other storage backend settings).

Users can recreate the volume type manually on the destination cloud and then
use the ``register-external`` command to register the migration.

Subsequent volume migrations will automatically use the manually created volume type.

.. code-block:: none

  sunbeam-migrate register-external \
    --resource-type volume-type \
    f104d538-a2f0-4897-92ea-9887bfb1c926 \
    491481cd-d9d0-4639-afe4-d5f07223f4db

  sunbeam-migrate show fd91c637-7b91-4fb6-9bd6-afb84c9d79a1

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
