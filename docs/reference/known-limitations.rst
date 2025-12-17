.. _Known limitations:

Known limitations
=================

This document describes the known limitations of the ``sunbeam-migrate`` project.

Multi-tenant limitations
------------------------

``sunbeam-migrate`` currently identifies migrated resources based on UUIDs.

Nova keypairs do not have an UUID, while Barbican secrets cannot be accessed
by other projects, unless allowed through ACL rules.

For this reason, keypairs and secrets do not support multi-tenant mode for the
moment. This would require extending ``sunbeam-migrate`` to receive the owner
project id along with the resource ID and use project scoped sessions, basically
impersonating the owner of those resources.

Preserving UUIDs
----------------

The original resource UUIDs will not be preserved on the destination cloud.

Keystone and Glance are among the very few Openstack services that allow
specifying an explicit UUID when creating resources.

However, users can call ``sunbeam-migrate list`` to obtain the source and
destination IDs for every migrated resource.

Instance snapshots
------------------

In order to migrate the user data, Nova instances and Cinder volumes are
temporarily uploaded to Glance.

During instance snapshots, Nova will try to freeze the guest filesystems
in order to ensure the consistency of the snapshot. See the `Nova quiesce spec`_
for more details.

If the guest VM does not support this mechanism, consider stopping the instance
before initiating a migration.

At the same time, ``sunbeam-migrate`` will pass the ``Force`` flag when uploading
volumes to Glance. This is required in order to allow attached volumes to be
uploaded. Most Cinder volume drivers support this but if your backend does not
allow it, consider temporarily detaching the migrated volumes.
