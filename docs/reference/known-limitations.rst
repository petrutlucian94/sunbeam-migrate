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

To migrate these resources, consider using a separate ``sunbeam-migrate`` config
and database for each individual tenant. The admin user user can be temporarily
added as a member of the migrated projects.

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
before initiating a migration or using ``fsfreeze`` manually. The same applies if
the instance has volumes attached.

At the same time, ``sunbeam-migrate`` will pass the ``Force`` flag when uploading
volumes to Glance. This is required in order to allow attached volumes to be
uploaded. Most Cinder volume drivers support this but if your backend does not
allow it, consider temporarily detaching the migrated volumes.

Instance ports
--------------

Instance ports are created using the Neutron API in order to preserve
certain properties that are not exposed by Nova (e.g. port MAC address or
VNIC type). However, this means that Nova will not delete these ports when
the instance is destroyed.

Glance uploads
--------------

``sunbeam-migrate`` relies on Glance uploads to transfer instance and volume
data. Make sure that the Glance services have enough storage capacity to
accommodate this.

Manila share types
------------------

At the moment, ``sunbeam-migrate`` can only access NFS share exports. Other
export types such as ``cephfs`` are unsupported.

This limitation also applies to Sunbeam, which only allows CephFS shares
exported through NFS.

Load balancer limitations
-------------------------

HTTP load balancers cannot be used with Sunbeam at the time of writing since it
relies on the OVN backend and cannot leverage Octavia "amphora" instances.

This isn't a limitation of the migration tool itself, but something to be aware
of when migrating to Sunbeam.

Openstack releases
------------------

The Openstack APIs have stabilized over the past few years and special
consideration was given to backwards compatibility, especially with the
introduction of `microversions`_.

``sunbeam-migrate`` is expected to work with any Openstack release starting
with Openstack Zed.

Note however that most of the testing was performed using Openstack 2024.1
(Caracal) and 2025.1 (Epoxy).
