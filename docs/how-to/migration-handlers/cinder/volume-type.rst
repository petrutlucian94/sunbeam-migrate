Migrating volume types
======================

By default, ``sunbeam-migrate`` will make an exact copy of the migrated volume
type.

These can be migrated individually or as associated resources of Cinder volumes.

Mismatching volume types
------------------------

The source volume type specifications may not be applicable to the destination cloud.

If ``preserve_volume_type`` is disabled, ``sunbeam-migrate`` will skip migrating
the volume type and use the default volume type instead.

Users may also recreate volume types manually and register them using the
``register-external`` command. Migrated volumes will then use the manually
created volume types.

Example
-------

The following example migrates a volume type:

.. code-block:: none

  sunbeam-migrate start \
    --resource-type=volume-type \
    fb65ae1f-45a9-400d-b935-f1c9412533b5

  2025-12-18 13:36:25,209 INFO Initiating volume-type migration, resource id: fb65ae1f-45a9-400d-b935-f1c9412533b5
  2025-12-18 13:36:27,808 INFO Successfully migrated volume-type resource, destination id: c555d880-5bff-471f-b7f8-e17a0a6e4a5f
