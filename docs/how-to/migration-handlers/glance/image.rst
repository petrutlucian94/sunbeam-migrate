Migrating images
================

The image migration handler is an essential part of the ``sunbeam-migration``
tool since it's also used to transfer Nova instance and Cinder volume data.

Transferred images do not get written to disk. Instead, the data is retrieved
and uploaded in chunks that are kept entirely in memory. The same applies to
Barbican secrets.

The chunk size can be configured through the ``image_transfer_chunk_size``
setting, defaulting to 32MB.

Example
-------

The following example migrates an image and removes it from the source cloud:

.. code-block:: none

    sunbeam-migrate start \
      --include-dependencies \
      --resource-type=image \
      --cleanup-source \
      08d44d29-94fb-4ccd-8828-082471648dce

  2025-12-18 09:16:34,568 INFO Initiating image migration, resource id: 08d44d29-94fb-4ccd-8828-082471648dce
  2025-12-18 09:16:35,378 INFO Migrating associated project resource: a37bddfe63dc4c19bf981ee971c1ef5d
  2025-12-18 09:16:35,379 INFO Initiating project migration, resource id: a37bddfe63dc4c19bf981ee971c1ef5d
  2025-12-18 09:16:35,957 INFO Migrating associated domain resource: 38da677b7dd944f8bce50bba4342bda6
  2025-12-18 09:16:35,958 INFO Initiating domain migration, resource id: 38da677b7dd944f8bce50bba4342bda6
  2025-12-18 09:16:37,456 WARNING Domain already exists: 6f05f02ce89b4976bb6f06bce3d2a40a admin_domain
  2025-12-18 09:16:37,464 INFO Successfully migrated domain resource, destination id: 6f05f02ce89b4976bb6f06bce3d2a40a
  2025-12-18 09:16:39,413 WARNING Project already exists: ba010cba17534749b67dd8d5efc95f84 test-3514969242-owner
  2025-12-18 09:16:39,425 INFO Successfully migrated project resource, destination id: ba010cba17534749b67dd8d5efc95f84
  2025-12-18 09:16:43,216 INFO Successfully migrated image resource, destination id: c0cf38bd-0887-4962-86f9-8d502659e666
  2025-12-18 09:16:43,225 INFO Migration succeeded, cleaning up source image: 08d44d29-94fb-4ccd-8828-082471648dce

