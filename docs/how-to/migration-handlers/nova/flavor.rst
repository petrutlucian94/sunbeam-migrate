Migrating flavors
=================

Nova flavors determine the amount of allocated resources and other
characteristics of Nova instances.

Flavors can be migrated individually or as Nova instance
:ref:`dependencies <resource_hierarchies_ref>`.

If the flavor properties are not applicable on the destination cloud,
users may choose to recreate it manually and then
:doc:`register the external migration <../../operations/external-migrations>`
in ``sunbeam-migrate``.

Note that if the flavor already exists on the destination side, the migration
will be skipped and the destination flavor ID will be recorded in the
``sunbeam-migrate`` database.

Example
-------

.. code-block:: none

  sunbeam-migrate start \
    --resource-type=flavor \
    c6156098-6ff7-4af3-8d75-94cf61b341cd

  2025-12-18 11:30:37,176 INFO Initiating flavor migration, resource id: c6156098-6ff7-4af3-8d75-94cf61b341cd
  2025-12-18 11:30:40,900 INFO Successfully migrated flavor resource, destination id: ce0cb7ae-b572-4e47-920a-f6cf5727a2d9
