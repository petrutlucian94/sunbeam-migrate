Migrating volumes
=================

``sunbeam-migrate`` can be used to migrate Cinder volumes along with
the corresponding volume types.

In order to access the volume data, ``sunbeam-migrate`` temporarily uploads
them to Glance.

While it may not be the most efficient Cinder volume migration method, it's
the most simple and portable approach: it can work with any Cinder backend and
Cinder release. Furthermore, it doesn't require additional configuration or packages.

Alternative approaches
----------------------

Here are a few other approaches that have been considered and may be implemented
as alternative volume migration mechanisms in future releases. Users may pick
one of these through config options.

Using the Cinder migration API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Cinder has a volume migration API, however the source and destination backends
must be part of the same Openstack cloud.

The "os-brick" library
~~~~~~~~~~~~~~~~~~~~~~

The "os-brick" library can be used to connect the source and destination
volumes locally, allowing the payload to be copied over (for example
using ``dd``).

This implies that both storage backends must be accessible. Also, it may
require additional packages and configuration (e.g. iSCSI initiator,
Ceph client etc).

Backend specific mechanisms
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ceph RBD images can be live migrated between Ceph clusters. Again, this implies
that both storage backends must be directly accessible and it will require
additional configuration and packages.

Shared storage backend
~~~~~~~~~~~~~~~~~~~~~~

In this scenario, both clouds are connected to the the same storage backend and
it's a matter of importing the volume on the destination side.

Sunbeam can be extended to join an existing Ceph cluster instead of creating a
new cluster during bootstrap. The Ceph data would be copied over through OSD
rebalancing, allowing the old nodes to be decommissioned.

Volume types
------------

The source volume type specifications may not be applicable to the destination cloud.

If ``preserve_volume_type`` is disabled, ``sunbeam-migrate`` will skip migrating
the volume type and use the default volume type instead.

Users may also recreate volume types manually and register it using the
``register-external`` command. Migrated volumes will then use the manually
created volume type.

Example
-------

The following example migrates a volume and removes it from the source cloud:

.. code-block:: none

  sunbeam-migrate start \
    --include-dependencies \
    --resource-type=volume \
    --cleanup-source \
    cea7caec-d20c-4560-b524-0306cd55aca9

  2025-12-18 13:30:02,738 INFO Initiating volume migration, resource id: cea7caec-d20c-4560-b524-0306cd55aca9
  2025-12-18 13:30:04,588 INFO Migrating associated project resource: c1007fbc056d4bc98dec25b1ed3078a9
  2025-12-18 13:30:04,589 INFO Initiating project migration, resource id: c1007fbc056d4bc98dec25b1ed3078a9
  2025-12-18 13:30:05,167 INFO Migrating associated domain resource: 38da677b7dd944f8bce50bba4342bda6
  2025-12-18 13:30:05,168 INFO Initiating domain migration, resource id: 38da677b7dd944f8bce50bba4342bda6
  2025-12-18 13:30:06,670 WARNING Domain already exists: 6f05f02ce89b4976bb6f06bce3d2a40a admin_domain
  2025-12-18 13:30:06,678 INFO Successfully migrated domain resource, destination id: 6f05f02ce89b4976bb6f06bce3d2a40a
  2025-12-18 13:30:08,713 WARNING Project already exists: c7c88956255a4f86aa13b9733241f499 test-1367222979-owner
  2025-12-18 13:30:08,716 INFO Successfully migrated project resource, destination id: c7c88956255a4f86aa13b9733241f499
  2025-12-18 13:30:08,723 INFO Migrating associated user resource: b411e9b1ea31439295fc3c0c277035ef
  2025-12-18 13:30:08,724 INFO Initiating user migration, resource id: b411e9b1ea31439295fc3c0c277035ef
  2025-12-18 13:30:09,484 INFO Migrating associated role resource: 780b01296c634963af1f6ee548995045
  2025-12-18 13:30:09,485 INFO Initiating role migration, resource id: 780b01296c634963af1f6ee548995045
  2025-12-18 13:30:11,506 WARNING Role already exists: 9b7da5e38e1a45468a1736f8f46a61b3 member
  2025-12-18 13:30:11,512 INFO Successfully migrated role resource, destination id: 9b7da5e38e1a45468a1736f8f46a61b3
  2025-12-18 13:30:11,523 INFO Migrating associated role resource: c768787e58ff4f0599d2e42fce417e46
  2025-12-18 13:30:11,524 INFO Initiating role migration, resource id: c768787e58ff4f0599d2e42fce417e46
  2025-12-18 13:30:13,419 WARNING Role already exists: c1c6d0be0a0c4f3394b705490ad875b6 admin
  2025-12-18 13:30:13,425 INFO Successfully migrated role resource, destination id: c1c6d0be0a0c4f3394b705490ad875b6
  2025-12-18 13:30:15,504 WARNING User already exists: 387eaaafbf1948298a184f8fb1fa1895 test-1367222979-owner
  2025-12-18 13:30:15,513 INFO Successfully migrated user resource, destination id: 387eaaafbf1948298a184f8fb1fa1895
  2025-12-18 13:30:15,527 INFO Migrating associated volume-type resource: 8c6db56f-8352-41a7-bba6-69d6cada309d
  2025-12-18 13:30:15,528 INFO Initiating volume-type migration, resource id: 8c6db56f-8352-41a7-bba6-69d6cada309d
  2025-12-18 13:30:19,006 INFO Successfully migrated volume-type resource, destination id: e149fac1-93da-4ff1-baa4-47b634e8db91
  2025-12-18 13:30:24,680 INFO Uploading cea7caec-d20c-4560-b524-0306cd55aca9 volume to image: volmigr-cea7caec-d20c-4560-b524-0306cd55aca9-728497667
  2025-12-18 13:30:26,510 INFO Waiting for volume upload to complete. Image id: bc669293-7452-41a1-93f0-37a277c06327
  2025-12-18 13:30:37,322 INFO Finished uploading source volume to Glance.
  2025-12-18 13:30:37,359 INFO Initiating image migration, resource id: bc669293-7452-41a1-93f0-37a277c06327
  2025-12-18 13:30:49,581 INFO Successfully migrated image resource, destination id: c4c0009c-46d4-4a14-961d-ad97478553ea
  2025-12-18 13:30:49,587 INFO Migration succeeded, cleaning up source image: bc669293-7452-41a1-93f0-37a277c06327
  2025-12-18 13:30:54,675 INFO Waiting for volume provisioning: 2eda0433-3d5b-47c4-b119-3ad98894e5be
  2025-12-18 13:31:06,871 INFO Deleting temporary image on source side: bc669293-7452-41a1-93f0-37a277c06327
  2025-12-18 13:31:06,948 INFO Deleting temporary image on the destination side: c4c0009c-46d4-4a14-961d-ad97478553ea
  2025-12-18 13:31:07,867 INFO Successfully migrated volume resource, destination id: 2eda0433-3d5b-47c4-b119-3ad98894e5be
  2025-12-18 13:31:07,872 INFO Migration succeeded, cleaning up source volume: cea7caec-d20c-4560-b524-0306cd55aca9
