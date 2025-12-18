Migrating share types
=====================

By default, ``sunbeam-migrate`` will make an exact copy of the migrated share
type.

These can be migrated individually or as associated resources of Manila shares.

Mismatching share types
------------------------

The source share type specifications may not be applicable to the destination cloud.

If ``preserve_share_type`` is disabled, ``sunbeam-migrate`` will skip migrating
the share type and use the default type instead.

Users may also recreate share types manually and register them using the
``register-external`` command. Migrated shares will then use the manually
created share types.

Example
-------

The following example migrates a share type:

.. code-block:: none

  sunbeam-migrate start \
    --resource-type=share-type \
    fb65ae1f-45a9-400d-b935-f1c9412533b5

  2025-12-18 13:36:25,209 INFO Initiating share-type migration, resource id: fb65ae1f-45a9-400d-b935-f1c9412533b5
  2025-12-18 13:36:27,808 INFO Successfully migrated share-type resource, destination id: c555d880-5bff-471f-b7f8-e17a0a6e4a5f
