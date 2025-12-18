Architecture
============

``sunbeam-migrate`` is a tool written in Python that leverages the
`OpenStack SDK`_ to identify OpenStack resources and recreate them on a
destination cloud, also transferring user data.

It models resource hierarchies and ownership, which are automatically
handled during the migration process.

An internal database is used to keep track of the migrated resources.

Migration handlers
------------------

Each supported resource type has a corresponding migration handler,
implementing the ``BaseMigrationHandler`` interface.

The handlers will:

* identify source resources based on a given set of filters
* determine the list of dependencies and member resources
* create new resources on the destination cloud matching the original
  specifications
* perform data migrations
* create and cleanup auxiliary resources used as part of data
  migrations

Migration manager
-----------------

Most of the high level orchestration is performed by the migration manager.

It fetches the appropriate migration handler, creates database entries,
tracks the migration status, handles associated resources and initiates
cleanups on the source side.

Data migration
--------------

``sunbeam-migrate`` transfers user data such as the volume payloads, images,
instance root disks, shared filesystems or Barbican secrets.

Some of those resources need to be temporarily uploaded to Glance in order to
become accessible, which is transparently handled as part of the migration
process.

Transferred images do not get written to disk. Instead, the data is retrieved
and uploaded in chunks that are kept entirely in memory. The same applies to
Barbican secrets.

Shared filesystems are mounted at a configurable location in order to facilitate
the data transfer. ``sunbeam-migrate`` will automatically define access rules
in order to be able to connect to the shares.

Internal database
-----------------

We use an internal Sqlite database to keep track of the migrated resources.
This allows us to easily map remote resources to the original ones and skip
migrations that were already completed.

Users can also register resources that have been migrated without the use
of ``sunbeam-migrate`` by calling the ``register-external`` command. This is
a simple yet powerful feature that allows manually creating resources that
have different specifications than the original ones. The tool will then
use these external resources when referenced by other migrated resources.

.. _resource_hierarchies_ref:

Resource hierarchies
--------------------

``sunbeam-migrate`` can automatically identify and migrate resource dependencies.
We define two types of resource relations:

Dependencies (associated resources)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These resources must be migrated before the parent resources. The user can pass
the ``--include-dependencies`` flag to let the migration cascade the resource
dependencies. If the flag is omitted and there are missing dependencies,
the migration will fail and the user will receive a list of resources that have
to be migrated.

For example, flavors and volumes are Nova instance dependencies. Networks are
subnet dependencies. Projects and users are also considered dependencies if the
multi-tenant mode is enabled.

Member resources
~~~~~~~~~~~~~~~~

"Members" are contained resources that are migrated *after* the parent resource.
These resources are optional and can be migrated using ``--include-members``.
For example, subnets are members of networks.

Member resources may also be migrated separately, after the parent resource was
migrated.

Already existing resources
--------------------------

Some Openstack services allow duplicate or missing resource names, in which case
``sunbeam-migrate`` will ignore existing resources that have the same name.

If a resource has been recreated without the use of ``sunbeam-migrate``, use
the ``register-external`` command to avoid migrating it twice.

For services that guarantee the resource names to be unique (e.g. Keystone
projects of a given domain), ``sunbeam-migrate`` will skip already existing
resources that have the same name and record the corresponding ID in the
internal database.
